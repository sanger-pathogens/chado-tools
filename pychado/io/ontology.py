import copy
from typing import List, Dict
import pronto
from .. import utils
from ..io import iobase
from ..orm import general, cv


class OntologyClient(iobase.IOClient):

    def __init__(self, uri: str, verbose=False):
        """Constructor"""

        # Connect to database
        super().__init__(uri)

        # Set up printer
        self.printer = utils.VerbosePrinter(verbose)
        
        # Initiate counters
        self._db_inserts = 0
        self._cv_inserts = 0
        self._dbxref_inserts = 0
        self._dbxref_updates = 0
        self._cvterm_inserts = 0
        self._cvterm_updates = 0
        self._cvterm_deletes = 0
        self._comment_inserts = 0
        self._comment_updates = 0
        self._comment_deletes = 0
        self._synonym_inserts = 0
        self._synonym_updates = 0
        self._synonym_deletes = 0
        self._crossref_inserts = 0
        self._crossref_updates = 0
        self._crossref_deletes = 0
        self._relationship_inserts = 0
        self._relationship_updates = 0
        self._relationship_deletes = 0

        # Load essentials
        self._comment_term = self._load_comment_term()
        self._relationship_terms = self._load_relationship_terms()
        self._synonym_type_terms = self._load_synonym_type_terms()

    def load(self, filename: str, file_format: str, db_authority: str):
        """Loads CV terms from a file into a database"""

        # Parse the file
        self.printer.print("Parsing ontology file ...")
        ontology = parse_ontology(filename, file_format)                            # type: pronto.Ontology

        # Filter content: Only retain the terms stemming from the database authority of interest
        default_namespace = get_default_namespace(ontology)
        ontology_terms = filter_ontology_by_db(ontology, db_authority)              # type: Dict[str, pronto.Term]
        self.printer.print("Retrieved " + str(len(ontology_terms)) + " terms for database authority " + db_authority)

        # Find/create parent vocabulary and db of ontology terms in file; load dependencies
        default_db_entry = self._handle_db(db_authority)
        default_cv_entry = self._handle_cv(pronto.Term(""), default_namespace)

        # Create global containers to reduce the number of database requests
        all_cvterm_entries = {}                                                     # type: Dict[str, cv.CvTerm]

        # Handle typedefs
        for typedef in ontology.typedefs:                                           # type: pronto.Relationship
            self._handle_typedef(typedef, default_db_entry, default_cv_entry)

        # First loop over all terms retrieved from the file: handle vocabulary, dbxref, CV terms, synonyms, comments
        for term in ontology_terms.values():                                        # type: pronto.Term

            # Insert, update and/or delete entries in various tables
            cv_entry = self._handle_cv(term, default_namespace)
            dbxref_entry = self._handle_dbxref(term, default_db_entry)
            cvterm_entry = self._handle_cvterms(ontology_terms, default_db_entry, dbxref_entry, cv_entry.cv_id)
            self._handle_comments(term, cvterm_entry)
            self._handle_synonyms(term, cvterm_entry)

            # Save CV term in global container
            all_cvterm_entries[term.id] = cvterm_entry

        # Second loop over all terms retrieved from file: cross references and relationships
        for term in ontology_terms.values():                                        # type: pronto.Term

            # Insert, update and/or delete entries in various tables
            self._handle_cross_references(term, all_cvterm_entries[term.id])
            self._handle_relationships(term, all_cvterm_entries[term.id], all_cvterm_entries)

        # Mark obsolete CV terms
        self._mark_obsolete_terms(ontology_terms, default_db_entry)

        # Commit changes
        self.session.commit()
        self._print_statistics()

    def _load_synonym_type_terms(self) -> Dict[str, cv.CvTerm]:
        """Loads CV terms describing tyoes of synonyms"""
        synonym_type_cv = self.query_table(cv.Cv, name="synonym_type").first()
        if not synonym_type_cv:
            raise iobase.DatabaseError("CV 'synonym_type' not present in database")
        synonym_type_cvterms = self.query_table(cv.CvTerm, cv_id=synonym_type_cv.cv_id).all()
        synonym_type_cvterms_dict = utils.list_to_dict(synonym_type_cvterms, "name")
        required_terms = ["exact", "narrow", "broad", "related"]
        for term in required_terms:
            if term not in synonym_type_cvterms_dict:
                raise iobase.DatabaseError("CV term for synonym type '" + term + "' not present in database")
        return synonym_type_cvterms_dict

    def _load_comment_term(self) -> cv.CvTerm:
        """Loads the CV term describing a comment"""
        comment_cvterm = self.query_table(cv.CvTerm, name="comment").first()
        if not comment_cvterm:
            raise iobase.DatabaseError("CV term 'comment' not present in database")
        return comment_cvterm

    def _load_relationship_terms(self) -> Dict[str, cv.CvTerm]:
        """Loads CV terms describing relationships between CV terms"""
        relationship_cv = self.query_table(cv.Cv, name="relationship").first()
        if not relationship_cv:
            raise iobase.DatabaseError("CV 'relationship' not present in database")
        relationship_cvterms = self.query_table(cv.CvTerm, is_relationshiptype=1).all()
        relationship_cvterms_dict = utils.list_to_dict(relationship_cvterms, "name")
        required_terms = ["is_a", "part_of"]
        for term in required_terms:
            if term not in relationship_cvterms_dict:
                raise iobase.DatabaseError("CV term for relationship '" + term + "' not present in database")
        return relationship_cvterms_dict

    def _handle_db(self, db_authority: str) -> general.Db:
        """Returns an entry from the db table"""
        db_entry = self.query_table(general.Db, name=db_authority).first()         # type: general.Db
        if not db_entry:
            db_entry = general.Db(name=db_authority)
            self.add_and_flush(db_entry)
            self.printer.print("Inserted DB '" + db_authority + "'")
            self._db_inserts += 1
        return db_entry

    def _handle_cv(self, term: pronto.Term, default_namespace: str) -> cv.Cv:
        """Inserts a controlled vocabulary in the database, and returns the entry"""

        # Get the namespace of the term from the input file
        namespace = default_namespace
        if "namespace" in term.other:
            namespace = term.other["namespace"][0]
        if not namespace:
            raise iobase.InputFileError("Namespace missing in input file")

        # Get the corresponding CV in the database - create it, if not yet available
        cv_entry = self.query_table(cv.Cv, name=namespace).first()                 # type: cv.Cv
        if not cv_entry:
            cv_entry = cv.Cv(name=namespace)
            self.add_and_flush(cv_entry)
            self.printer.print("Inserted CV '" + namespace + "'")
            self._cv_inserts += 1
        return cv_entry

    def _handle_dbxref(self, term: pronto.Term, default_db: general.Db) -> general.DbxRef:
        """Inserts or updates a database cross reference in the dbxref table, and returns the entry"""

        # Split database cross reference (dbxref) into db, accession, version
        (db_authority, accession, version) = split_dbxref(term.id)

        # Check if the dbxref is already present in the database
        existing_dbxref_entries = self.query_table(general.DbxRef, db_id=default_db.db_id,
                                                   accession=accession).all()          # type: List[general.DbxRef]
        if existing_dbxref_entries:

            # Check if the entries in database and file are identical
            for dbxref_entry in existing_dbxref_entries:                                # type: general.DbxRef
                if dbxref_entry.version == version:
                    break
            else:

                # Update dbxref (version)
                dbxref_entry = existing_dbxref_entries[0]                               # type: general.DbxRef
                dbxref_entry.version = version
                self.printer.print("Updated dbxref '" + term.id + "'")
                self._dbxref_updates += 1
        else:

            # Insert dbxref
            dbxref_entry = general.DbxRef(db_id=default_db.db_id, accession=accession, version=version)
            self.add_and_flush(dbxref_entry)
            self.printer.print("Inserted dbxref '" + term.id + "'")
            self._dbxref_inserts += 1

        # Return the entry
        return dbxref_entry

    def _handle_cvterms(self, ontology_terms: Dict[str, pronto.Term], db_entry: general.Db,
                        dbxref_entry: general.DbxRef, cv_id: int) -> cv.CvTerm:
        """Inserts or updates a CV term in the cvterm table, and makes sure not to violate any UNIQUE constraints"""

        # Check if there is an entry in the input ontology
        dbxref = create_dbxref(db_entry.name, dbxref_entry.accession, dbxref_entry.version)
        if dbxref in ontology_terms:

            # Create a CV term and check if it is unique (if inserted into the database)
            term = ontology_terms[dbxref]                                                   # type: pronto.Term
            cvterm_entry = create_cvterm_entry(term, cv_id, dbxref_entry.dbxref_id)
            if cvterm_entry.is_obsolete:
                self._mark_cvterm_as_obsolete(cvterm_entry)
            (is_unique, existing_cvterm_entry, existing_dbxref_entry) \
                = self._is_cvterm_unique(cvterm_entry)                   # type: bool, cv.CvTerm, general.DbxRef
            if not is_unique:

                # Recursive call to update the existing CV term first
                self._handle_cvterms(ontology_terms, db_entry, existing_dbxref_entry, existing_cvterm_entry.cv_id)

            if is_unique and existing_cvterm_entry:

                # There is a CV term in the database that coincides with the input in terms of cv, name,
                # is_obsolete and dbxref_id. Update if necessary.
                if update_cvterm_properties(existing_cvterm_entry, cvterm_entry):
                    self.printer.print("Updated CV term '" + existing_cvterm_entry.name + "' for dbxref " + term.id)
                    self._cvterm_updates += 1
                return existing_cvterm_entry
            else:

                # There is no CV term in the database that coincides with the input in terms of cv,
                # name and is_obsolete. Check if there is one with the same dbxref.
                existing_cvterm_entry = self.query_table(cv.CvTerm, dbxref_id=cvterm_entry.dbxref_id).first()
                if existing_cvterm_entry:

                    # Update parameters, if necessary
                    if update_cvterm_properties(existing_cvterm_entry, cvterm_entry):
                        self.printer.print("Updated CV term '" + existing_cvterm_entry.name + "' for dbxref " + term.id)
                        self._cvterm_updates += 1
                    return existing_cvterm_entry
                else:

                    # Insert a new CV term
                    self.add_and_flush(cvterm_entry)
                    self.printer.print("Inserted CV term '" + cvterm_entry.name + "' for dbxref " + term.id)
                    self._cvterm_inserts += 1
                    return cvterm_entry
        else:

            # Mark the CV term as obsolete (or "more obsolete")
            existing_cvterm_entry = self.query_table(cv.CvTerm, dbxref_id=dbxref_entry.dbxref_id).first()
            if self._mark_cvterm_as_obsolete(existing_cvterm_entry):
                self.printer.print("Marked CV term '" + existing_cvterm_entry.name + "' as obsolete")
                self._cvterm_deletes += 1
            return existing_cvterm_entry

    def _is_cvterm_unique(self, cvterm_entry: cv.CvTerm) -> (bool, cv.CvTerm, general.DbxRef):
        """Checks if a CV term would fulfill all UNIQUE constraints if inserted into the database"""

        # Check if a CV term with the same properties exists in the database
        confounding_cvterm_entry = self.query_table(cv.CvTerm, cv_id=cvterm_entry.cv_id, name=cvterm_entry.name,
                                                    is_obsolete=cvterm_entry.is_obsolete).first()   # type: cv.CvTerm

        if confounding_cvterm_entry and confounding_cvterm_entry.dbxref_id != cvterm_entry.dbxref_id:

            # There is a CV term with these properties in the database, and its ID differs from the input term
            # -> non-unique
            corresponding_debxref_entry = self.query_table(
                general.DbxRef, dbxref_id=confounding_cvterm_entry.dbxref_id).first()   # type: general.DbxRef
            return False, confounding_cvterm_entry, corresponding_debxref_entry

        elif confounding_cvterm_entry:

            # There is a CV term with these properties in the database, but its ID aligns with the input term -> unique
            return True, confounding_cvterm_entry, None

        else:

            # There is no CV term with these properties in the database -> unique
            return True, None, None

    def _mark_cvterm_as_obsolete(self, cvterm_entry: cv.CvTerm) -> bool:
        """Marks a CV term in the database as obsolete, and makes sure this doesn't violate any UNIQUE constraints"""

        # Create a copy of the CV term entry and mark that as obsolete
        marked = False
        test_cvterm_entry = copy.deepcopy(cvterm_entry)
        if "obsolete" not in test_cvterm_entry.name.lower():
            test_cvterm_entry.name = "obsolete " + test_cvterm_entry.name
        test_cvterm_entry.is_obsolete = 1

        # Check if the changed CV term still fulfills all UNIQUE constraints. If not, increase the is_obsolete parameter
        while not self._is_cvterm_unique(test_cvterm_entry)[0]:
            test_cvterm_entry.is_obsolete += 1

        # Transfer the changed properties to the original CV term
        if test_cvterm_entry != cvterm_entry:
            marked = True
            cvterm_entry.name = test_cvterm_entry.name
            cvterm_entry.is_obsolete = test_cvterm_entry.is_obsolete
        return marked

    def _handle_typedef(self, typedef: pronto.Relationship, default_db: general.Db, default_cv: cv.Cv):
        """Inserts CV terms for relationship ontology terms (so-called "typedefs")"""

        # Check if a relationship CV term with this name already exists
        cvterm_entry = self.query_table(cv.CvTerm, name=typedef.obo_name, is_relationshiptype=1).first()
        if not cvterm_entry:

            # Create dbxref
            dbxref = create_dbxref(default_db.name, typedef.obo_name)
            term = pronto.Term(dbxref, typedef.obo_name)
            dbxref_entry = self._handle_dbxref(term, default_db)

            # Create CV term
            cvterm_entry = cv.CvTerm(cv_id=default_cv.cv_id, dbxref_id=dbxref_entry.dbxref_id,
                                     name=typedef.obo_name, is_relationshiptype=1)
            self.add_and_flush(cvterm_entry)
            self._cvterm_inserts += 1
            self.printer.print("Inserted CV term '" + cvterm_entry.name + "' for dbxref " + dbxref)
        return cvterm_entry

    def _handle_comments(self, term: pronto.Term, cvterm_entry: cv.CvTerm) -> cv.CvTermProp:
        """Inserts, updates or deletes comments to a CV term in the cvtermprop table"""

        # Get existing and new comments, i.e. comments present in database and in input file
        existing_comment_entries = self.query_table(cv.CvTermProp, cvterm_id=cvterm_entry.cvterm_id,
                                                    type_id=self._comment_term.cvterm_id).all()
        comment = extract_comment(term)
        edited_entry = None

        # Update/insert comment, if available
        if comment:

            # Check if there is already a comment to this CV term in the database
            if existing_comment_entries:

                # Check if the comments in database and file are identical
                for cvtermprop_entry in existing_comment_entries:                   # type: cv.CvTermProp
                    if cvtermprop_entry.value == comment:
                        break
                else:

                    # Update comment
                    cvtermprop_entry = existing_comment_entries[0]                  # type: cv.CvTermProp
                    cvtermprop_entry.value = comment
                    self.printer.print("Updated comment '" + cvtermprop_entry.value + "' for CV term '"
                                       + cvterm_entry.name + "'")
                    self._comment_updates += 1
            else:

                # Insert comment
                cvtermprop_entry = cv.CvTermProp(cvterm_id=cvterm_entry.cvterm_id, type_id=self._comment_term.cvterm_id,
                                                 value=comment)
                self.add_and_flush(cvtermprop_entry)
                self.printer.print("Inserted comment '" + cvtermprop_entry.value + "' for CV term '"
                                   + cvterm_entry.name + "'")
                self._comment_inserts += 1
            edited_entry = cvtermprop_entry

        # Delete comments not present in file
        for comment_entry in existing_comment_entries:                              # type: cv.CvTermProp
            if not comment_entry.value or comment_entry.value != comment:

                # Delete comment
                self.session.delete(comment_entry)
                self.printer.print("Deleted comment '" + comment_entry.value + "' for CV term '"
                                   + cvterm_entry.name + "'")
                self._comment_deletes += 1

        return edited_entry

    def _handle_synonyms(self, term: pronto.Term, cvterm_entry: cv.CvTerm) -> List[cv.CvTermSynonym]:
        """Inserts, updates or deletes synonyms to a CV term in the cvtermsynonym table"""

        # Get existing and new synonyms, i.e. synonyms present in database and in input file
        existing_synonyms = self.query_table(cv.CvTermSynonym, cvterm_id=cvterm_entry.cvterm_id).all()
        new_synonyms = extract_synonyms(term)
        edited_entries = []

        # Loop over all synonyms in input file
        for synonym in term.synonyms:                                               # type: pronto.Synonym

            # Extract synonym type
            if synonym.scope.lower() not in self._synonym_type_terms:
                synonym_type_term = ""
                self.printer.print("WARNING: synonym type '" + synonym.scope.lower() + "' not present in database!")
            else:
                synonym_type_term = self._synonym_type_terms[synonym.scope.lower()]

            # Check if the synonym is already present in the database
            matching_synonyms = utils.filter_objects(existing_synonyms,
                                                     synonym=synonym.desc)          # type: List[cv.CvTermSynonym]
            if matching_synonyms:

                # Check if the synonyms in database and file have identical properties (len(matching_synonyms) = 1)
                cvtermsynonym_entry = matching_synonyms[0]                          # type: cv.CvTermSynonym
                if cvtermsynonym_entry.type_id != synonym_type_term.cvterm_id:

                    # Update synonym (type)
                    cvtermsynonym_entry.type_id = synonym_type_term.cvterm_id
                    self.printer.print("Updated synonym '" + cvtermsynonym_entry.synonym + "' for CV term '"
                                       + cvterm_entry.name + "'")
                    self._synonym_updates += 1
            else:

                # Insert synonym
                cvtermsynonym_entry = cv.CvTermSynonym(cvterm_id=cvterm_entry.cvterm_id, synonym=synonym.desc,
                                                       type_id=synonym_type_term.cvterm_id)
                self.add_and_flush(cvtermsynonym_entry)
                self.printer.print("Inserted synonym '" + cvtermsynonym_entry.synonym + "' for CV term '"
                                   + cvterm_entry.name + "'")
                self._synonym_inserts += 1

            edited_entries.append(cvtermsynonym_entry)

        # Delete synonyms not present in file
        for cvtermsynonym_entry in existing_synonyms:                               # type: cv.CvTermSynonym
            if not cvtermsynonym_entry.synonym or cvtermsynonym_entry.synonym not in new_synonyms:

                # Delete synonym
                self.session.delete(cvtermsynonym_entry)
                self.printer.print("Deleted synonym '" + cvtermsynonym_entry.synonym + "' for CV term '"
                                   + cvterm_entry.name + "'")
                self._synonym_deletes += 1

        return edited_entries

    def _handle_cross_references(self, term: pronto.Term, cvterm_entry: cv.CvTerm) -> List[cv.CvTermDbxRef]:
        """Inserts, updates or deletes database cross references to a CV term in the cvterm_dbxref table"""

        # Get existing cross references, i.e. cross references present in database
        existing_crossrefs = self.query_table(cv.CvTermDbxRef, cvterm_id=cvterm_entry.cvterm_id).all()
        edited_entries = []

        # Get cross references present in the file and loop over them
        new_crossrefs = extract_cross_references(term)
        for crossref in new_crossrefs:

            # Obtain the corresponding entry from the dbxref table, insert if not existing
            db_authority = split_dbxref(crossref)[0]
            corresponding_db_entry = self._handle_db(db_authority)
            corresponding_dbxref_entry = self._handle_dbxref(pronto.Term(crossref), corresponding_db_entry)

            # Check if the cross reference is already present in the database
            matching_crossrefs = utils.filter_objects(
                existing_crossrefs, dbxref_id=corresponding_dbxref_entry.dbxref_id)  # type: List[cv.CvTermDbxRef]
            if matching_crossrefs:

                # Save the existing cross reference
                edited_entries.append(matching_crossrefs[0])
            else:

                # Insert cross reference
                cvterm_dbxref_entry = cv.CvTermDbxRef(cvterm_id=cvterm_entry.cvterm_id,
                                                      dbxref_id=corresponding_dbxref_entry.dbxref_id,
                                                      is_for_definition=0)
                self.add_and_flush(cvterm_dbxref_entry)
                self.printer.print("Inserted cross reference '" + crossref + "' for CV term '"
                                   + cvterm_entry.name + "'")
                self._crossref_inserts += 1
                edited_entries.append(cvterm_dbxref_entry)

        # Delete cross references not present in file
        for cvterm_dbxref_entry in existing_crossrefs:                              # type: cv.CvTermDbxRef
            matching_crossrefs = utils.filter_objects(edited_entries, dbxref_id=cvterm_dbxref_entry.dbxref_id)
            if not matching_crossrefs:

                # Delete cross reference
                self.session.delete(cvterm_dbxref_entry)
                self.printer.print("Deleted cross reference with dbxref-ID " + str(cvterm_dbxref_entry.dbxref_id)
                                   + " for CV term '" + cvterm_entry.name + "'")
                self._crossref_deletes += 1

        return edited_entries

    def _handle_relationships(self, term: pronto.Term, subject_cvterm_entry: cv.CvTerm,
                              all_cvterm_entries: Dict[str, cv.CvTerm]) -> List[cv.CvTermRelationship]:
        """Inserts, updates or deletes relationships between CV terms"""

        # Get existing relationships for this subject in the database
        subject_db_authority = split_dbxref(term.id)[0]
        existing_relationships = self.query_table(cv.CvTermRelationship,
                                                  subject_id=subject_cvterm_entry.cvterm_id).all()
        edited_entries = []                                                         # type: List[cv.CvTermRelationship]

        # Loop over all relationships for this subject in the file
        for relationship, object_terms in term.relations.items():          # type: pronto.Relationship, pronto.TermList

            # Get relationship type and corresponding term from database
            relationship_name = relationship.obo_name
            if relationship_name not in self._relationship_terms:
                if relationship_name != "can_be":
                    self.printer.print("WARNING: Relationship term '" + relationship_name + "' not present in database")
                continue
            type_cvterm = self._relationship_terms[relationship_name]                # type: cv.CvTerm

            # Loop over all objects
            for object_term in object_terms:                                        # type: pronto.Term

                # Get corresponding object CV term from database
                if split_dbxref(object_term.id)[0] != subject_db_authority:
                    continue
                if object_term.id not in all_cvterm_entries:
                    self.printer.print("WARNING: CV term for dbxref '" + object_term.id + "' not present in database")
                    continue
                object_cvterm_entry = all_cvterm_entries[object_term.id]            # type: cv.CvTerm

                # Check if the relationship already exists in the database
                matching_relationships = utils.filter_objects(existing_relationships, type_id=type_cvterm.cvterm_id,
                                                              object_id=object_cvterm_entry.cvterm_id)
                if matching_relationships:

                    # Save the existing relationship
                    edited_entries.append(matching_relationships[0])
                else:

                    # Insert relationship
                    cvterm_relationship_entry = cv.CvTermRelationship(subject_id=subject_cvterm_entry.cvterm_id,
                                                                      object_id=object_cvterm_entry.cvterm_id,
                                                                      type_id=type_cvterm.cvterm_id)
                    self.add_and_flush(cvterm_relationship_entry)
                    self.printer.print("Inserted relationship: '" + subject_cvterm_entry.name + "', '"
                                       + relationship_name + "', '" + object_cvterm_entry.name + "'")
                    self._relationship_inserts += 1
                    edited_entries.append(cvterm_relationship_entry)

        # Delete relationships not present in file
        for cvterm_relationship_entry in existing_relationships:                    # type: cv.CvTermRelationship
            matching_relationships = utils.filter_objects(edited_entries, type_id=cvterm_relationship_entry.type_id,
                                                          object_id=cvterm_relationship_entry.object_id)
            if not matching_relationships:

                # Delete relationship
                self.session.delete(cvterm_relationship_entry)
                self.printer.print("Deleted relationship for CV term '" + subject_cvterm_entry.name + "'")
                self._relationship_deletes += 1

        return edited_entries

    def _mark_obsolete_terms(self, ontology_terms: Dict[str, pronto.Term], default_db: general.Db) -> List[cv.CvTerm]:
        """Marks obsolete CV terms in the database"""

        # Loop over all dbxref entries in the database
        existing_entries = self.query_table(general.DbxRef, db_id=default_db.db_id).all()
        marked_entries = []
        for dbxref_entry in existing_entries:                                       # type: general.DbxRef

            # Check if the dbxref is also present in the input file
            dbxref = create_dbxref(default_db.name, dbxref_entry.accession, dbxref_entry.version)
            if dbxref not in ontology_terms:

                # Find the corresponding CV term in the database
                cvterm_entry = self.query_table(cv.CvTerm, dbxref_id=dbxref_entry.dbxref_id,
                                                is_relationshiptype=0).first()      # type: cv.CvTerm
                if not cvterm_entry:
                    continue

                # Mark the CV term as obsolete, if necessary
                if self._mark_cvterm_as_obsolete(cvterm_entry):
                    self.printer.print("Marked CV term '" + cvterm_entry.name + "' as obsolete")
                    marked_entries.append(cvterm_entry)
                    self._cvterm_deletes += 1

        return marked_entries

    def _print_statistics(self):
        """Prints a summary of the changes applied to the database"""
        print("Successfully imported an ontology into the database.")
        print("DBs: " + str(self._db_inserts) + " insertions")
        print("CVs: " + str(self._cv_inserts) + " insertions")
        print("dbxrefs: " + str(self._dbxref_inserts) + " insertions, " + str(self._dbxref_updates) + " updates")
        print("CV terms: " + str(self._cvterm_inserts) + " insertions, " + str(self._cvterm_updates)
              + " updates, " + str(self._cvterm_deletes) + " marked as obsolete")
        print("comments: " + str(self._comment_inserts) + " insertions, " + str(self._comment_updates)
              + " updates, " + str(self._comment_deletes) + " deletions")
        print("synonyms: " + str(self._synonym_inserts) + " insertions, " + str(self._synonym_updates)
              + " updates, " + str(self._synonym_deletes) + " deletions")
        print("cross references: " + str(self._crossref_inserts) + " insertions, " + str(self._crossref_updates)
              + " updates, " + str(self._crossref_deletes) + " deletions")
        print("relationships: " + str(self._relationship_inserts) + " insertions, " + str(self._relationship_updates)
              + " updates, " + str(self._relationship_deletes) + " deletions")

    def _initiate_global_arrays(self, default_db_id: int, comment_id: int) -> (
            List[cv.Cv], List[general.DbxRef], List[cv.CvTerm], List[cv.CvTermProp], List[cv.CvTermSynonym],
            List[cv.CvTermDbxRef], List[cv.CvTermRelationship]):
        """Initiates global arrays that can be used to minimize the number of queries to the database"""

        all_cvs = self.query_table(cv.Cv).all()                                    # type: List[cv.Cv]
        all_dbxrefs = self.query_table(general.DbxRef, db_id=default_db_id).all()  # type: List[general.DbxRef]
        all_cvterms = self.query_table(cv.CvTerm).all()                            # type: List[cv.CvTerm]
        all_comments = self.query_table(cv.CvTermProp, type_id=comment_id).all()   # type: List[cv.CvTermProp]
        all_synonyms = self.query_table(cv.CvTermSynonym).all()                    # type: List[cv.CvTermSynonym]
        all_crossrefs = self.query_table(cv.CvTermDbxRef).all()                    # type: List[cv.CvTermDbxRef]
        all_relationships = self.query_table(cv.CvTermRelationship).all()          # type: List[cv.CvTermRelationship]

        return all_cvs, all_dbxrefs, all_cvterms, all_comments, all_synonyms, all_crossrefs, all_relationships


def parse_ontology(filename: str, file_format="obo") -> pronto.Ontology:
    """Function parsing an OBO/OWL file"""
    if file_format == "owl":
        return pronto.Ontology(filename, parser="OwlXMLParser")
    else:
        return pronto.Ontology(filename, parser="OboParser")


def get_default_namespace(ontology: pronto.Ontology) -> str:
    """Retrieves the default namespace of a given ontology"""
    default_namespace = ""
    if "default-namespace" in ontology.meta:
        default_namespace = ontology.meta["default-namespace"][0]
    return default_namespace


def filter_ontology_by_db(ontology: pronto.Ontology, db_authority: str) -> Dict[str, pronto.Term]:
    """Filters the terms in an ontology, only retaining those stemming from a given database"""
    filtered_terms = {}                                                                 # type: Dict[str, pronto.Term]
    for term in ontology:                                                               # type: pronto.Term
        db = split_dbxref(term.id)[0]
        if db == db_authority:
            filtered_terms[term.id] = term
    return filtered_terms


def extract_comment(term: pronto.Term) -> str:
    """Extracts comments from an ontology term"""
    comment = ""
    if "comment" in term.other:
        comment = term.other["comment"][0]
    return comment


def extract_synonyms(term: pronto.Term) -> List[str]:
    """Extracts synonyms from an ontology term"""
    synonyms = []
    for synonym in term.synonyms:
        synonyms.append(synonym.desc)
    return synonyms


def extract_cross_references(term: pronto.Term) -> List[str]:
    """Extracts cross references from an ontology term"""
    cross_references = []
    if "alt_id" in term.other:
        cross_references.extend(term.other["alt_id"])
    if "xref" in term.other:
        for xref in term.other["xref"]:                                                 # type: str
            cross_references.append(xref.split(" ")[0])
    return cross_references


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
