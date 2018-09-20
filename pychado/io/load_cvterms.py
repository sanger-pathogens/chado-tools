import copy
from typing import List, Dict, Set
import sqlalchemy.orm.query
import pronto
from pychado import utils
from pychado.io import io
from pychado.orm import general, cv


class DatabaseError(Exception):
    pass


class InputFileError(Exception):
    pass

# TODO: read typedefs and add to the database
# TODO: test if minimizing the number of queries can speed up the program without adding too much overhead


def run(filename: str, file_format: str, uri: str, db_authority: str) -> None:
    """Loads CV terms from a file into a database"""

    # Parse the file
    ontology = utils.parse_ontology(filename, file_format)                              # type: pronto.Ontology

    # Filter content: Only retain the terms stemming from the database authority of interest
    default_namespace = get_default_namespace(ontology)
    ontology_terms = filter_ontology_by_db(ontology, db_authority)                      # type: Dict[str, pronto.Term]

    # Connect to database
    engine = sqlalchemy.create_engine(uri)                                              # type: sqlalchemy.engine.Engine
    session_maker = sqlalchemy.orm.sessionmaker(bind=engine)
    session = session_maker()                                                           # type: sqlalchemy.orm.Session

    # Find/create parent vocabulary and db of ontology terms in file; load dependencies
    default_db_entry = io.find_or_create(session, general.Db, name=db_authority)           # type: general.Db
    default_cv_entry = io.find_or_create(session, cv.Cv, name=default_namespace)           # type: cv.Cv
    comment_term, synonym_type_terms, relationship_terms = load_and_check_dependencies(session)

    # Create global containers to reduce the number of database requests
    all_dbxref_entries = {}                                                           # type: Dict[str, general.DbxRef]
    all_cvterm_entries = {}                                                             # type: Dict[str, cv.CvTerm]

    # First loop over all terms retrieved from the file: handle vocabulary, dbxref, CV terms, synonyms, comments
    for accession, term in ontology_terms.items():                                      # type: str, pronto.Term

        # Insert, update and/or delete entries in various tables
        cv_entry = handle_cv(session, term, default_namespace)
        dbxref_entry = handle_dbxref(session, term, default_db_entry)
        cvterm_entry = handle_cvterms_without_conflicts(session, ontology_terms, cv_entry.cv_id, dbxref_entry)
        handle_comments(session, term, cvterm_entry, comment_term.cvterm_id)
        handle_synonyms(session, term, cvterm_entry, synonym_type_terms)

        # Save dbxref and CV term in global containers
        all_dbxref_entries[term.id] = dbxref_entry
        all_cvterm_entries[term.id] = cvterm_entry

    # Second loop over all terms retrieved from file: cross references and relationships
    for accession, term in ontology_terms.items():                                      # type: str, pronto.Term

        # Insert, update and/or delete entries in various tables
        handle_cross_references(session, term, all_cvterm_entries[term.id], all_dbxref_entries[term.id],
                                default_db_entry)
        handle_relationships(session, term, all_cvterm_entries[term.id], relationship_terms, default_db_entry,
                             all_cvterm_entries)

    # Mark obsolete CV terms
    mark_obsolete_terms(session, ontology_terms, default_db_entry)

    # Commit changes
    session.commit()
    session.close()
    engine.dispose()


def split_dbxref(dbxref: str) -> (str, str, str):
    """Splits a database cross reference string in the format db:accession:version into its constituents"""
    split_id = dbxref.split(":")
    if len(split_id) < 2 or len(split_id) > 3:
        raise AttributeError("dbxref must consist of 2 or 3 elements, separated by semicolon")
    db = split_id[0]
    accession = split_id[1]
    version = ""
    if len(split_id) == 3:
        version = split_id[2]
    return db, accession, version


def create_dbxref(db: str, accession: str, version="") -> str:
    """Creates a database cross reference string in the format db:accession:version from the constituents"""
    if not db or not accession:
        raise AttributeError("db and accession must be given for a dbxref")
    dbxref = db + ":" + accession
    if version:
        dbxref = dbxref + ":" + version
    return dbxref


def load_and_check_dependencies(session: sqlalchemy.orm.Session) -> (cv.CvTerm, Dict[str, cv.CvTerm],
                                                                     Dict[str, cv.CvTerm]):
    """Loads basic vocabularies and CV terms that are required for the processing of the data in the input file"""

    # CV term for comments
    comment_term = io.find(session, cv.CvTerm, name="comment").first()                     # type: cv.CvTerm
    if not comment_term:
        raise DatabaseError("CV term for comments not present in database")

    # CV terms for synonym types
    synonym_type_cv = io.find(session, cv.Cv, name="synonym_type").first()                 # type: cv.Cv
    if not synonym_type_cv:
        raise DatabaseError("CV 'synonym_type' not present in database")
    synonym_type_cvterms = io.find(session, cv.CvTerm, cv_id=synonym_type_cv.cv_id).all()  # type: List[cv.CvTerm]
    synonym_type_terms = utils.list_to_dict(synonym_type_cvterms, "name")                  # type: Dict[str, cv.CvTerm]
    required_terms = ["exact", "narrow", "broad", "related"]
    for term in required_terms:
        if term not in synonym_type_terms:
            raise DatabaseError("CV term for synonym type '" + term + "' not present in database")

    # CV terms for relationships
    relationship_cv = io.find(session, cv.Cv, name="relationship").first()                 # type: cv.Cv
    if not relationship_cv:
        print("WARNING: CV 'relationship' not present in database")
    relationship_cvterms = io.find(session, cv.CvTerm, is_relationshiptype=1).all()        # type: List[cv.CvTerm]
    relationship_terms = utils.list_to_dict(relationship_cvterms, "name")                  # type: Dict[str, cv.CvTerm]
    required_terms = ["is_a", "part_of"]
    for term in required_terms:
        if term not in relationship_terms:
            raise DatabaseError("CV term for relationship '" + term + "' not present in database")

    return comment_term, synonym_type_terms, relationship_terms


def get_default_namespace(ontology: pronto.Ontology) -> str:
    """Retrieves the default namespace of a given ontology"""
    default_namespace = ""
    if "default-namespace" in ontology.meta:
        default_namespace = ontology.meta["default-namespace"][0]
    else:
        print("WARNING: Default namespace missing in input file")
    return default_namespace


def filter_ontology_by_db(ontology: pronto.Ontology, db_authority: str) -> Dict[str, pronto.Term]:
    """Filters the terms in an ontology, only retaining those stemming from a given database"""
    filtered_terms = {}                                                                 # type: Dict[str, pronto.Term]
    for term in ontology:                                                               # type: pronto.Term
        (db, accession, _) = split_dbxref(term.id)
        if db == db_authority:
            filtered_terms[accession] = term
    print("Retrieved " + str(len(filtered_terms)) + " terms for database authority " + db_authority)
    return filtered_terms


def initiate_global_arrays(session: sqlalchemy.orm.Session, default_db_id: int, comment_id: int) -> (
        List[cv.Cv], List[general.DbxRef], List[cv.CvTerm], List[cv.CvTermProp], List[cv.CvTermSynonym],
        List[cv.CvTermDbxRef], List[cv.CvTermRelationship]):
    """Initiates global arrays that can be used to minimize the number of queries to the database"""

    all_cvs = io.find(session, cv.Cv).all()                                         # type: List[cv.Cv]
    all_dbxrefs = io.find(session, general.DbxRef, db_id=default_db_id).all()       # type: List[general.DbxRef]
    all_cvterms = io.find(session, cv.CvTerm).all()                                 # type: List[cv.CvTerm]
    all_comments = io.find(session, cv.CvTermProp, type_id=comment_id).all()        # type: List[cv.CvTermProp]
    all_synonyms = io.find(session, cv.CvTermSynonym).all()                         # type: List[cv.CvTermSynonym]
    all_crossrefs = io.find(session, cv.CvTermDbxRef).all()                         # type: List[cv.CvTermDbxRef]
    all_relationships = io.find(session, cv.CvTermRelationship).all()               # type: List[cv.CvTermRelationship]

    return all_cvs, all_dbxrefs, all_cvterms, all_comments, all_synonyms, all_crossrefs, all_relationships


def handle_cv(session: sqlalchemy.orm.Session, term: pronto.Term, default_namespace: str) -> cv.Cv:
    """Inserts a controlled vocabulary in the database, and returns the entry"""

    # Get the namespace of the term from the input file
    namespace = default_namespace
    if "namespace" in term.other:
        namespace = term.other["namespace"][0]
    if not namespace:
        raise InputFileError("Namespace missing in input file")

    # Get the corresponding CV in the database - create it, if not yet available
    cv_entry = io.find_or_create(session, cv.Cv, name=namespace)
    return cv_entry


def handle_dbxref(session: sqlalchemy.orm.Session, term: pronto.Term, default_db: general.Db) -> general.DbxRef:
    """Inserts or updates a database cross reference in the dbxref table, and returns the entry"""

    # Split database cross reference (dbxref) into db, accession, version
    (db_authority, accession, version) = split_dbxref(term.id)

    # Check if the dbxref is already present in the database
    existing_dbxref_entries = io.find(session, general.DbxRef, db_id=default_db.db_id,
                                      accession=accession).all()                        # type: List[general.DbxRef]
    if existing_dbxref_entries:

        # Check if the entries in database and file are identical
        for dbxref_entry in existing_dbxref_entries:                                    # type: general.DbxRef
            if dbxref_entry.version == version:
                break
        else:

            # Update dbxref (version)
            dbxref_entry = existing_dbxref_entries[0]                                   # type: general.DbxRef
            dbxref_entry.version = version
            print("Updated dbxref '" + term.id + "'")
    else:

        # Insert dbxref
        dbxref_entry = general.DbxRef(db_id=default_db.db_id, accession=accession, version=version)
        session.add(dbxref_entry)
        session.flush()
        print("Inserted dbxref '" + term.id + "'")

    # Return the entry
    return dbxref_entry


def handle_cvterms_without_conflicts(session: sqlalchemy.orm.Session, ontology_terms: Dict[str, pronto.Term],
                                     cv_id: int, dbxref_entry: general.DbxRef, force=False) -> cv.CvTerm:
    """Inserts or updates a CV term in the cvterm table, and makes sure not to violate any UNIQUE constraints"""

    # Check if there is an entry in the input ontology
    if dbxref_entry.accession in ontology_terms:

        # Create a CV term and check if it is unique (if inserted into the database)
        term = ontology_terms[dbxref_entry.accession]                                   # type: pronto.Term
        cvterm_entry = create_cvterm_entry(term, cv_id, dbxref_entry.dbxref_id)
        (is_unique, existing_cvterm_entry, existing_dbxref_entry) \
            = is_cvterm_unique(session, cvterm_entry)                   # type: bool, cv.CvTerm, general.DbxRef
        if not is_unique:

            # Recursive call to update the existing CV term first
            handle_cvterms_without_conflicts(session, ontology_terms, existing_cvterm_entry.cv_id,
                                             existing_dbxref_entry, True)

        if is_unique and existing_cvterm_entry:

            # There is a CV term in the database that coincides with the input in terms of cv, name,
            # is_obsolete and dbxref_id. Update if necessary.
            if update_cvterm_properties(existing_cvterm_entry, cvterm_entry):
                print("Updated CV term '" + existing_cvterm_entry.name + "' for dbxref " + term.id)
            elif existing_cvterm_entry.is_obsolete and \
                    mark_cvterm_as_obsolete(session, existing_cvterm_entry, force):
                print("Marked CV term '" + existing_cvterm_entry.name + "' for dbxref " + term.id + " as obsolete")
            return existing_cvterm_entry
        else:

            # There is no CV term in the database that coincides with the input in terms of cv, name and is_obsolete.
            # Check if there is one with the same dbxref.
            existing_cvterm_entry = io.find(session, cv.CvTerm, dbxref_id=cvterm_entry.dbxref_id).first()
            if existing_cvterm_entry:

                # Update parameters, if necessary
                if update_cvterm_properties(existing_cvterm_entry, cvterm_entry):
                    print("Updated CV term '" + existing_cvterm_entry.name + "' for dbxref " + term.id)
                return existing_cvterm_entry
            else:

                # Insert a new CV term
                session.add(cvterm_entry)
                session.flush()
                print("Inserted CV term '" + cvterm_entry.name + "' for dbxref " + term.id)
                return cvterm_entry
    else:

        # Mark the CV term as obsolete (or "more obsolete")
        existing_cvterm_entry = io.find(session, cv.CvTerm, dbxref_id=dbxref_entry.dbxref_id).first()
        if mark_cvterm_as_obsolete(session, existing_cvterm_entry, True):
            print("Marked CV term '" + existing_cvterm_entry.name + "' as obsolete")
        return existing_cvterm_entry


def create_cvterm_entry(term: pronto.Term, cv_id: int, dbxref_id: int) -> cv.CvTerm:
    """Creates a CV term entry for the database from an ontology term"""
    is_obsolete = False
    if "is_obsolete" in term.other and term.other["is_obsolete"][0].lower() == "true":
        is_obsolete = True
    description = None
    if term.desc:
        description = term.desc
    cvterm_entry = cv.CvTerm(cv_id=cv_id, dbxref_id=dbxref_id, name=term.name, definition=description,
                             is_obsolete=int(is_obsolete))
    return cvterm_entry


def is_cvterm_unique(session: sqlalchemy.orm.Session, cvterm_entry: cv.CvTerm) -> (bool, cv.CvTerm, general.DbxRef):
    """Checks if a CV term would fulfill all UNIQUE constraints if inserted into the database"""

    # Check if a CV term with the same properties exists in the database
    confounding_cvterm_entry = io.find(session, cv.CvTerm, cv_id=cvterm_entry.cv_id, name=cvterm_entry.name,
                                       is_obsolete=cvterm_entry.is_obsolete).first()            # type: cv.CvTerm

    if confounding_cvterm_entry and confounding_cvterm_entry.dbxref_id != cvterm_entry.dbxref_id:

        # There is a CV term with these properties in the database, and its ID differs from the input term -> non-unique
        corresponding_debxref_entry = io.find(
            session, general.DbxRef, dbxref_id=confounding_cvterm_entry.dbxref_id).first()      # type: general.DbxRef
        return False, confounding_cvterm_entry, corresponding_debxref_entry

    elif confounding_cvterm_entry:

        # There is a CV term with these properties in the database, but its ID aligns with the input term -> unique
        return True, confounding_cvterm_entry, None

    else:

        # There is no CV term with these properties in the database -> unique
        return True, None, None


def update_cvterm_properties(existing_cvterm_entry: cv.CvTerm, new_cvterm_entry: cv.CvTerm) -> bool:
    """Updates the properties of a CV term in the database"""
    updated = False
    if new_cvterm_entry.cv_id != existing_cvterm_entry.cv_id:
        existing_cvterm_entry.cv_id = new_cvterm_entry.cv_id
        updated = True
    if new_cvterm_entry.name != existing_cvterm_entry.name:
        existing_cvterm_entry.name = new_cvterm_entry.name
        updated = True
    if new_cvterm_entry.definition != existing_cvterm_entry.definition:
        existing_cvterm_entry.definition = new_cvterm_entry.definition
        updated = True
    if new_cvterm_entry.is_obsolete != existing_cvterm_entry.is_obsolete:
        existing_cvterm_entry.is_obsolete = new_cvterm_entry.is_obsolete
        updated = True
    return updated


def mark_cvterm_as_obsolete(session: sqlalchemy.orm.Session, cvterm_entry: cv.CvTerm, force=False) -> bool:
    """Marks a CV term in the database as obsolete, and makes sure this doesn't violate any UNIQUE constraints"""

    # Create a copy of the CV term entry and mark that as obsolete
    marked = False
    test_cvterm_entry = copy.deepcopy(cvterm_entry)
    if "obsolete" not in test_cvterm_entry.name.lower():
        test_cvterm_entry.name = "obsolete " + test_cvterm_entry.name
    if force:
        test_cvterm_entry.is_obsolete += 1
    else:
        test_cvterm_entry.is_obsolete = 1

    # If nothing has changed: Return
    if test_cvterm_entry == cvterm_entry:
        return marked

    # Check if the changed CV term still fulfills all UNIQUE constraints. If not, increase the is_obsolete parameter
    while not is_cvterm_unique(session, test_cvterm_entry):
        test_cvterm_entry.is_obsolete += 1

    # Transfer the changed properties to the original CV term
    if test_cvterm_entry != cvterm_entry:
        marked = True
    cvterm_entry.name = test_cvterm_entry.name
    cvterm_entry.is_obsolete = test_cvterm_entry.is_obsolete
    return marked


def handle_comments(session: sqlalchemy.orm.Session, term: pronto.Term, cvterm_entry: cv.CvTerm,
                    comment_id: int) -> cv.CvTermProp:
    """Inserts, updates or deletes comments to a CV term in the cvtermprop table"""

    # Get existing and new comments, i.e. comments present in database and in input file
    existing_comment_entries = io.find(session, cv.CvTermProp, cvterm_id=cvterm_entry.cvterm_id,
                                       type_id=comment_id).all()                        # type: List[cv.CvTermProp]
    comment = ""
    if "comment" in term.other:
        comment = term.other["comment"][0]                                              # type: str
    edited_entry = None

    # Update/insert comment, if available
    if comment:

        # Check if there is already a comment to this CV term in the database
        if existing_comment_entries:

            # Check if the comments in database and file are identical
            cvtermprop_entry = existing_comment_entries[0]                              # type: cv.CvTermProp
            if cvtermprop_entry.value != comment:

                # Update comment
                cvtermprop_entry.value = comment
                print("Updated comment '" + cvtermprop_entry.value + "' for CV term '" + cvterm_entry.name + "'")
        else:

            # Insert comment
            cvtermprop_entry = cv.CvTermProp(cvterm_id=cvterm_entry.cvterm_id, type_id=comment_id, value=comment)
            session.add(cvtermprop_entry)
            session.flush()
            print("Inserted comment '" + cvtermprop_entry.value + "' for CV term '" + cvterm_entry.name + "'")
        edited_entry = cvtermprop_entry

    # Delete comments not present in file
    for comment_entry in existing_comment_entries:                                      # type: cv.CvTermProp
        if not comment_entry.value or comment_entry.value != comment:

            # Delete comment
            session.delete(comment_entry)
            print("Deleted comment '" + comment_entry.value + "' for CV term '" + cvterm_entry.name + "'")

    return edited_entry


def handle_synonyms(session: sqlalchemy.orm.Session, term: pronto.Term, cvterm_entry: cv.CvTerm,
                    synonym_types: Dict[str, cv.CvTerm]) -> List[cv.CvTermSynonym]:
    """Inserts, updates or deletes synonyms to a CV term in the cvtermsynonym table"""

    # Get existing and new synonyms, i.e. synonyms present in database and in input file
    existing_synonyms = io.find(session, cv.CvTermSynonym, cvterm_id=cvterm_entry.cvterm_id).all()
    new_synonyms = {synonym.desc for synonym in term.synonyms}                          # type: Set[str]
    edited_entries = []

    # Loop over all synonyms in input file
    for synonym in term.synonyms:                                                       # type: pronto.Synonym

        # Extract synonym type
        if synonym.scope.lower() not in synonym_types:
            synonym_type_term = ""
            print("WARNING: synonym type '" + synonym.scope.lower() + "' not present in database!")
        else:
            synonym_type_term = synonym_types[synonym.scope.lower()]

        # Check if the synonym is already present in the database
        matching_synonyms = utils.filter_objects(existing_synonyms,
                                                 synonym=synonym.desc)                  # type: List[cv.CvTermSynonym]
        if matching_synonyms:

            # Check if the synonyms in database and file have identical properties (len(matching_synonyms) = 1)
            cvtermsynonym_entry = matching_synonyms[0]                                  # type: cv.CvTermSynonym
            if cvtermsynonym_entry.type_id != synonym_type_term.cvterm_id:

                # Update synonym (type)
                cvtermsynonym_entry.type_id = synonym_type_term.cvterm_id
                print("Updated synonym '" + cvtermsynonym_entry.synonym + "' for CV term '" + cvterm_entry.name + "'")
        else:

            # Insert synonym
            cvtermsynonym_entry = cv.CvTermSynonym(cvterm_id=cvterm_entry.cvterm_id, synonym=synonym.desc,
                                                   type_id=synonym_type_term.cvterm_id)
            session.add(cvtermsynonym_entry)
            session.flush()
            print("Inserted synonym '" + cvtermsynonym_entry.synonym + "' for CV term '" + cvterm_entry.name + "'")

        edited_entries.append(cvtermsynonym_entry)

    # Delete synonyms not present in file
    for cvtermsynonym_entry in existing_synonyms:                                       # type: cv.CvTermSynonym
        if not cvtermsynonym_entry.synonym or cvtermsynonym_entry.synonym not in new_synonyms:

            # Delete synonym
            session.delete(cvtermsynonym_entry)
            print("Deleted synonym '" + cvtermsynonym_entry.synonym + "' for CV term '" + cvterm_entry.name + "'")

    return edited_entries


def handle_cross_references(session: sqlalchemy.orm.Session, term: pronto.Term, cvterm_entry: cv.CvTerm,
                            defining_dbxref_entry: general.DbxRef, default_db: general.Db) -> List[cv.CvTermDbxRef]:
    """Inserts, updates or deletes database cross references to a CV term in the cvterm_dbxref table"""

    # Get existing cross references, i.e. cross references present in database
    existing_crossrefs = io.find(session, cv.CvTermDbxRef, cvterm_id=cvterm_entry.cvterm_id).all()
    edited_entries = []

    # Get cross references present in the file and loop over them
    defining_dbxref = create_dbxref(default_db.name, defining_dbxref_entry.accession, defining_dbxref_entry.version)
    new_crossrefs = [defining_dbxref]
    if "alt_id" in term.other:
        new_crossrefs.extend(term.other["alt_id"])
    new_crossref_ids = {defining_dbxref_entry.dbxref_id}
    for crossref in new_crossrefs:

        # Check if this is the defining dbxref
        is_for_definition = 0
        if crossref == defining_dbxref:

            # Mark as defining dbxref
            corresponding_dbxref_entry = defining_dbxref_entry
            is_for_definition = 1
        else:

            # Obtain the corresponding entry from the dbxref table
            (db_authority, accession, version) = split_dbxref(crossref)
            if db_authority != default_db.name:
                continue
            corresponding_dbxref_entry = io.find(session, general.DbxRef, db_id=default_db.db_id, accession=accession,
                                                 version=version).first()               # type: general.DbxRef
            if not corresponding_dbxref_entry:

                # Insert dbxref
                corresponding_dbxref_entry = general.DbxRef(db_id=default_db.db_id, accession=accession,
                                                            version=version)
                session.add(corresponding_dbxref_entry)
                session.flush()
                print("Inserted dbxref '" + crossref + "'")

            new_crossref_ids.add(corresponding_dbxref_entry.dbxref_id)

        # Check if the cross reference is already present in the database
        matching_crossrefs = utils.filter_objects(
            existing_crossrefs, dbxref_id=corresponding_dbxref_entry.dbxref_id)         # type: List[cv.CvTermDbxRef]
        if matching_crossrefs:

            # Check if the cross references in database and file have identical properties
            cvterm_dbxref_entry = matching_crossrefs[0]                                 # type: cv.CvTermDbxRef
            if cvterm_dbxref_entry.is_for_definition != is_for_definition:

                # Update cross reference (is_for_definition)
                cvterm_dbxref_entry.is_for_definition = is_for_definition
                print("Updated cross reference '" + crossref + "' for CV term '" + cvterm_entry.name + "'")
        else:

            # Insert cross reference
            cvterm_dbxref_entry = cv.CvTermDbxRef(cvterm_id=cvterm_entry.cvterm_id,
                                                  dbxref_id=corresponding_dbxref_entry.dbxref_id,
                                                  is_for_definition=is_for_definition)
            session.add(cvterm_dbxref_entry)
            session.flush()
            print("Inserted cross reference '" + crossref + "' for CV term '" + cvterm_entry.name + "'")

        edited_entries.append(cvterm_dbxref_entry)

    # Delete cross references not present in file
    for cvterm_dbxref_entry in existing_crossrefs:                                      # type: cv.CvTermDbxRef
        if cvterm_dbxref_entry.dbxref_id not in new_crossref_ids:

            # Delete cross reference
            session.delete(cvterm_dbxref_entry)
            print("Deleted cross reference with ID " + str(cvterm_dbxref_entry.dbxref_id)
                  + " for CV term '" + cvterm_entry.name + "'")

    return edited_entries


def handle_relationships(session: sqlalchemy.orm.Session, term: pronto.Term, subject_term_entry: cv.CvTerm,
                         relationship_terms: Dict[str, cv.CvTerm], default_db: general.Db,
                         all_cvterm_entries: Dict[str, cv.CvTerm]) -> List[cv.CvTermRelationship]:
    """Inserts, updates or deletes relationships between CV terms"""

    # Get existing relationships for this subject in the database
    subject_id = subject_term_entry.cvterm_id
    existing_relationships = io.find(session, cv.CvTermRelationship, subject_id=subject_id).all()
    edited_entries = []                                                             # type: List[cv.CvTermRelationship]

    # Loop over all relationships for this subject in the file
    for relationship, object_terms in term.relations.items():              # type: pronto.Relationship, pronto.TermList

        # Get relationship type and corresponding term from database
        relationship_name = relationship.obo_name
        if relationship_name not in relationship_terms:
            print("WARNING: Relationship term '" + relationship_name + "' not present in database")
            continue
        type_id = relationship_terms[relationship_name].cvterm_id

        # Loop over all objects
        for object_term in object_terms:                                                # type: pronto.Term

            # Get corresponding object term from database
            db_authority = split_dbxref(object_term.id)[0]
            if db_authority != default_db.name:
                continue
            if object_term.id not in all_cvterm_entries:
                print("WARNING: CV term for dbxref '" + object_term.id + "' not present in database")
                continue
            object_id = all_cvterm_entries[object_term.id].cvterm_id

            # Check if the relationship already exists in the database
            matching_relationships = utils.filter_objects(existing_relationships, type_id=type_id, object_id=object_id)
            if matching_relationships:

                # Save the existing relationship
                edited_entries.append(matching_relationships[0])
            else:

                # Insert relationship
                cvterm_relationship_entry = cv.CvTermRelationship(subject_id=subject_id, object_id=object_id,
                                                                  type_id=type_id)
                session.add(cvterm_relationship_entry)
                session.flush()
                print("Inserted relationship: '" + subject_term_entry.name + "', '" + relationship_name + "', '"
                      + object_term.name + "'")
                edited_entries.append(cvterm_relationship_entry)

    # Delete relationships not present in file
    for cvterm_relationship_entry in existing_relationships:                            # type: cv.CvTermRelationship
        matching_relationships = utils.filter_objects(edited_entries, type_id=cvterm_relationship_entry.type_id,
                                                      object_id=cvterm_relationship_entry.object_id)
        if not matching_relationships:

            # Delete relationship
            session.delete(cvterm_relationship_entry)
            print("Deleted relationship for CV term '" + subject_term_entry.name + "'")

    return edited_entries


def mark_obsolete_terms(session: sqlalchemy.orm.Session, ontology_terms: Dict[str, pronto.Term],
                        default_db: general.Db) -> List[cv.CvTerm]:
    """Marks obsolete CV terms in the database"""

    # Loop over all dbxref entries in the database
    existing_entries = io.find(session, general.DbxRef, db_id=default_db.db_id).all()   # type: List[general.DbxRef]
    marked_entries = []
    for dbxref_entry in existing_entries:                                               # type: general.DbxRef

        # Check if the dbxref is also present in the input file
        if dbxref_entry.accession not in ontology_terms:

            # Find the corresponding CV term in the database
            cvterm_entry = io.find(session, cv.CvTerm, dbxref_id=dbxref_entry.dbxref_id).first()  # type: cv.CvTerm
            if not cvterm_entry:
                continue

            # Mark the CV term as obsolete, if necessary
            if mark_cvterm_as_obsolete(session, cvterm_entry):
                print("Marked CV term '" + cvterm_entry.name + "' as obsolete")
                marked_entries.append(cvterm_entry)

    return marked_entries
