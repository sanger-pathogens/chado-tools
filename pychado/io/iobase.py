from typing import List, Dict
import sqlalchemy.orm
from .. import utils, ddl
from ..orm import general, cv, pub, organism, sequence


class DatabaseError(Exception):
    pass


class InputFileError(Exception):
    pass


class IOClient(ddl.DatabaseAccessClient):
    """Base class for read-write access to a database"""

    def __init__(self, uri: str):
        """Constructor - connect to database"""
        super().__init__(uri)
        session_maker = sqlalchemy.orm.sessionmaker(bind=self.engine)
        self.session = session_maker()                                              # type: sqlalchemy.orm.Session

    def __del__(self):
        """Destructor - disconnect from database"""
        self.session.close()
        super().__del__()

    def query_table(self, table, **kwargs) -> sqlalchemy.orm.Query:
        """Creates a query on a database table from given keyword arguments"""
        query = self.session.query(table)
        if kwargs:
            query = query.filter_by(**kwargs)
        return query

    def query_all(self, table, **kwargs):
        """Helper class querying a table and returning all results"""
        return self.query_table(table, **kwargs).all()

    def query_first(self, table, **kwargs):
        """Helper class querying a table and returning the first result"""
        return self.query_table(table, **kwargs).first()

    def add_and_flush(self, obj):
        """Adds an entry to a database table"""
        self.session.add(obj)
        self.session.flush()

    def insert_into_table(self, table, **kwargs):
        """Creates an entry and inserts it into a database table"""
        obj = table(**kwargs)
        self.add_and_flush(obj)
        return obj

    def find_or_insert(self, table, **kwargs):
        """Returns one entry of a database table matching a query. If no matching entry exists, it is created."""
        entry = self.query_first(table, **kwargs)
        if not entry:
            entry = self.insert_into_table(table, **kwargs)
        return entry


class ChadoClient(IOClient):
    """Class for import/export operations on Chado databases"""

    def __init__(self, uri: str, verbose=False):
        """Constructor"""

        # Connect to database
        super().__init__(uri)

        # Set up printer
        self.printer = utils.VerbosePrinter(verbose)

    def query_feature_relationship_by_type(self, subject_id: int, type_ids: List[int]) -> sqlalchemy.orm.Query:
        """Creates a query to select entries with specific 'type_id' from the feature_relationship table"""
        return self.session.query(sequence.FeatureRelationship)\
            .join(cv.CvTerm, sequence.FeatureRelationship.type)\
            .filter(sequence.FeatureRelationship.subject_id == subject_id)\
            .filter(sequence.FeatureRelationship.type_id.in_(type_ids))

    def query_featureprop_by_type(self, feature_id: int, type_ids: List[int]) -> sqlalchemy.orm.Query:
        """Creates a query to select entries with specific 'type_id' from the featureprop table"""
        return self.session.query(sequence.FeatureProp)\
            .filter(sequence.FeatureProp.feature_id == feature_id)\
            .filter(sequence.FeatureProp.type_id.in_(type_ids))

    def query_feature_synonym_by_type(self, feature_id: int, type_ids: List[int]) -> sqlalchemy.orm.Query:
        """Creates a query to select entries related to a specific 'synonym.type_id' from the feature_synonym table"""
        return self.session.query(sequence.FeatureSynonym)\
            .join(sequence.Synonym, sequence.FeatureSynonym.synonym)\
            .filter(sequence.FeatureSynonym.feature_id == feature_id)\
            .filter(sequence.Synonym.type_id.in_(type_ids))

    def query_feature_cvterm_by_ontology(self, feature_id: int, ontology_id: int) -> sqlalchemy.orm.Query:
        """Creates a query to select entries related to a specific 'dbxref.db_id' from the feature_cvterm table"""
        return self.session.query(sequence.FeatureCvTerm)\
            .join(cv.CvTerm, sequence.FeatureCvTerm.cvterm)\
            .join(general.DbxRef, cv.CvTerm.dbxref)\
            .filter(sequence.FeatureCvTerm.feature_id == feature_id)\
            .filter(general.DbxRef.db_id == ontology_id)

    def query_feature_cvterm_by_ontology_and_organism(self, organism_id: int, ontology_id: int
                                                      ) -> sqlalchemy.orm.Query:
        """Creates a query to select ontology terms associated with feature of a given organism"""
        return self.session.query(sequence.FeatureCvTerm)\
            .join(sequence.Feature, sequence.FeatureCvTerm.feature)\
            .join(cv.CvTerm, sequence.FeatureCvTerm.cvterm)\
            .join(general.DbxRef, cv.CvTerm.dbxref)\
            .filter(sequence.Feature.organism_id == organism_id)\
            .filter(general.DbxRef.db_id == ontology_id)

    def query_parent_features(self, subject_id: int, type_ids: List[int]) -> sqlalchemy.orm.Query:
        """Creates a query to select the parent feature(s) of a given feature"""
        return self.session.query(sequence.Feature)\
            .select_from(sequence.FeatureRelationship)\
            .join(sequence.Feature, sequence.FeatureRelationship.object)\
            .filter(sequence.FeatureRelationship.type_id.in_(type_ids))\
            .filter(sequence.FeatureRelationship.subject_id == subject_id)\
            .order_by(sequence.Feature.uniquename)

    def query_child_features(self, object_id: int, type_id: int) -> sqlalchemy.orm.Query:
        """Creates a query to select the child features of a given feature"""
        return self.session.query(sequence.Feature)\
            .select_from(sequence.FeatureRelationship)\
            .join(sequence.Feature, sequence.FeatureRelationship.subject)\
            .filter(sequence.FeatureRelationship.type_id == type_id)\
            .filter(sequence.FeatureRelationship.object_id == object_id)\
            .order_by(sequence.Feature.uniquename)

    def query_features_by_srcfeature(self, sequence_id: int) -> sqlalchemy.orm.Query:
        """Creates a query to select the features located on a given sequence"""
        return self.session.query(sequence.Feature).select_from(sequence.FeatureLoc)\
            .join(sequence.Feature, sequence.FeatureLoc.feature)\
            .filter(sequence.FeatureLoc.srcfeature_id == sequence_id)\
            .order_by(sequence.FeatureLoc.fmin)

    def query_features_by_property_type(self, organism_id: int, type_id: int) -> sqlalchemy.orm.Query:
        """Creates a query to select features of a given organism that have certain properties"""
        return self.session.query(sequence.Feature)\
            .select_from(sequence.FeatureProp)\
            .join(sequence.Feature, sequence.FeatureProp.feature)\
            .filter(sequence.Feature.organism_id == organism_id)\
            .filter(sequence.FeatureProp.type_id == type_id)

    def query_features_by_type(self, organism_id: int, type_ids: List[int]) -> sqlalchemy.orm.Query:
        """Creates a query to select features of a given organism and type"""
        return self.session.query(sequence.Feature)\
            .filter(sequence.Feature.organism_id == organism_id)\
            .filter(sequence.Feature.type_id.in_(type_ids))

    def query_protein_features(self, organism_id: int, gene_type_id: int, part_of_id: int, derives_from_id: int
                               ) -> sqlalchemy.orm.Query:
        """Creates a query to select protein features of a given organism"""
        transcript_feature = sqlalchemy.orm.aliased(sequence.Feature, name="transcript_feature")
        protein_feature = sqlalchemy.orm.aliased(sequence.Feature, name="protein_feature")
        gene_feature = sqlalchemy.orm.aliased(sequence.Feature, name="gene_feature")
        transcript_gene_relationship = sqlalchemy.orm.aliased(
            sequence.FeatureRelationship, name="transcript_gene_relationship")
        protein_transcript_relationship = sqlalchemy.orm.aliased(
            sequence.FeatureRelationship, name="protein_transcript_relationship")
        return self.session.query(protein_feature)\
            .join(protein_transcript_relationship,
                  protein_transcript_relationship.subject_id == protein_feature.feature_id)\
            .join(transcript_feature, protein_transcript_relationship.object)\
            .join(transcript_gene_relationship,
                  transcript_gene_relationship.subject_id == transcript_feature.feature_id)\
            .join(gene_feature, transcript_gene_relationship.object)\
            .filter(protein_feature.organism_id == organism_id)\
            .filter(protein_transcript_relationship.type_id == derives_from_id)\
            .filter(transcript_gene_relationship.type_id == part_of_id)\
            .filter(gene_feature.type_id == gene_type_id)

    def query_feature_properties(self, feature_id: int) -> sqlalchemy.orm.Query:
        """Creates a query to select key-value pairs from the 'featureprop' table"""
        return self.session.query(cv.CvTerm.name, sequence.FeatureProp.value)\
            .select_from(sequence.FeatureProp)\
            .join(cv.CvTerm, sequence.FeatureProp.type)\
            .filter(sequence.FeatureProp.feature_id == feature_id)

    def query_feature_pubs(self, feature_id: int) -> sqlalchemy.orm.Query:
        """Creates a query to select entries from the 'pub' table associated with a given feature"""
        return self.session.query(pub.Pub.uniquename)\
            .select_from(sequence.FeaturePub)\
            .join(pub.Pub, sequence.FeaturePub.pub)\
            .filter(sequence.FeaturePub.feature_id == feature_id)

    def query_feature_dbxrefs(self, feature_id: int) -> sqlalchemy.orm.Query:
        """Creates a query to select dbxrefs associated with a given feature"""
        return self.session.query(general.Db.name, general.DbxRef.accession)\
            .select_from(sequence.FeatureDbxRef)\
            .join(general.DbxRef, sequence.FeatureDbxRef.dbxref)\
            .join(general.Db, general.DbxRef.db)\
            .filter(sequence.FeatureDbxRef.feature_id == feature_id)

    def query_feature_synonyms(self, feature_id: int) -> sqlalchemy.orm.Query:
        """Creates a query to select synonyms associated with a given feature"""
        return self.session.query(cv.CvTerm.name.label("type"), sequence.Synonym.name.label("synonym"))\
            .select_from(sequence.FeatureSynonym)\
            .join(sequence.Synonym, sequence.FeatureSynonym.synonym)\
            .join(cv.CvTerm, sequence.Synonym.type)\
            .filter(sequence.FeatureSynonym.feature_id == feature_id)

    def query_feature_ontology_terms(self, feature_id: int, ontology_id: int) -> sqlalchemy.orm.Query:
        """Creates a query to select ontology terms associated with a given feature"""
        return self.session.query(general.Db.name, general.DbxRef.accession)\
            .select_from(sequence.FeatureCvTerm)\
            .join(cv.CvTerm, sequence.FeatureCvTerm.cvterm)\
            .join(general.DbxRef, cv.CvTerm.dbxref)\
            .join(general.Db, general.DbxRef.db)\
            .filter(sequence.FeatureCvTerm.feature_id == feature_id)\
            .filter(general.Db.db_id == ontology_id)

    def query_feature_cvterm_properties(self, feature_cvterm_id: int) -> sqlalchemy.orm.Query:
        """Creates a query to select key-value pairs from the 'feature_cvtermprop' table"""
        return self.session.query(cv.CvTerm.name, sequence.FeatureCvTermProp.value)\
            .select_from(sequence.FeatureCvTermProp)\
            .join(cv.CvTerm, sequence.FeatureCvTermProp.type)\
            .filter(sequence.FeatureCvTermProp.feature_cvterm_id == feature_cvterm_id)

    def query_feature_cvterm_pubs(self, feature_cvterm_id: int) -> sqlalchemy.orm.Query:
        """Creates a query to select entries from the 'pub' table associated with a given feature_cvterm"""
        return self.session.query(pub.Pub.uniquename)\
            .select_from(sequence.FeatureCvTerm)\
            .join(pub.Pub, sequence.FeatureCvTerm.pub)\
            .filter(sequence.FeatureCvTerm.feature_cvterm_id == feature_cvterm_id)

    def query_feature_cvterm_secondary_pubs(self, feature_cvterm_id: int) -> sqlalchemy.orm.Query:
        """Creates a query to select entries from the 'pub' table associated with a given feature_cvterm"""
        return self.session.query(pub.Pub.uniquename)\
            .select_from(sequence.FeatureCvTermPub)\
            .join(pub.Pub, sequence.FeatureCvTermPub.pub)\
            .filter(sequence.FeatureCvTermPub.feature_cvterm_id == feature_cvterm_id)

    def query_feature_cvterm_dbxrefs(self, feature_cvterm_id: int) -> sqlalchemy.orm.Query:
        """Creates a query to select dbxrefs associated with a given feature_cvterm"""
        return self.session.query(general.Db.name, general.DbxRef.accession)\
            .select_from(sequence.FeatureCvTermDbxRef)\
            .join(general.DbxRef, sequence.FeatureCvTermDbxRef.dbxref)\
            .join(general.Db, general.DbxRef.db)\
            .filter(sequence.FeatureCvTermDbxRef.feature_cvterm_id == feature_cvterm_id)

    def query_feature_cvterm_ontology_terms(self, feature_cvterm_id: int, ontology_id: int
                                            ) -> sqlalchemy.orm.Query:
        """Creates a query to select ontology terms associated with a given feature_cvterm"""
        return self.session.query(general.Db.name, general.DbxRef.accession)\
            .select_from(sequence.FeatureCvTerm)\
            .join(cv.CvTerm, sequence.FeatureCvTerm.cvterm)\
            .join(general.DbxRef, cv.CvTerm.dbxref)\
            .join(general.Db, general.DbxRef.db)\
            .filter(sequence.FeatureCvTerm.feature_cvterm_id == feature_cvterm_id)\
            .filter(general.Db.db_id == ontology_id)

    def query_cvterm_namespace(self, cvterm_id: int) -> sqlalchemy.orm.Query:
        """Creates a query to select the namespace/vocabulary of a CV term"""
        return self.session.query(cv.Cv.name).select_from(cv.CvTerm)\
            .join(cv.Cv, cv.CvTerm.cv)\
            .filter(cv.CvTerm.cvterm_id == cvterm_id)

    def _load_db(self, name: str) -> general.Db:
        """Loads a specific DB"""
        db_entry = self.query_first(general.Db, name=name)
        if not db_entry:
            raise DatabaseError("DB '" + name + "' not present in database")
        return db_entry

    def _load_dbs(self, names: List[str]) -> List[general.Db]:
        """Loads specific DBs"""
        db_entries = []
        for name in names:
            db_entries.append(self._load_db(name))
        return db_entries

    def _load_cvterm(self, term: str) -> cv.CvTerm:
        """Loads a specific CV term"""
        cvterm_entry = self.query_first(cv.CvTerm, name=term)
        if not cvterm_entry:
            raise DatabaseError("CV term '" + term + "' not present in database")
        return cvterm_entry

    def _load_cvterm_from_cv(self, term: str, vocabulary: str) -> cv.CvTerm:
        """Loads a specific CV term from a specific vocabulary"""
        cv_entry = self.query_first(cv.Cv, name=vocabulary)
        if not cv_entry:
            raise DatabaseError("CV '" + vocabulary + "' not present in database")
        cvterm_entry = self.query_first(cv.CvTerm, name=term, cv_id=cv_entry.cv_id)
        if not cvterm_entry:
            raise DatabaseError("CV term '" + term + "' not present in database")
        return cvterm_entry

    def _load_cvterms(self, terms: List[str]) -> List[cv.CvTerm]:
        """Loads specific CV terms"""
        cvterm_entries = []
        for term in terms:
            cvterm_entries.append(self._load_cvterm(term))
        return cvterm_entries

    def _load_terms_from_cv(self, vocabulary: str, relationship=False) -> List[cv.CvTerm]:
        """Loads CV terms from a given vocabulary and returns them in a list"""
        cv_entry = self.query_first(cv.Cv, name=vocabulary)
        if not cv_entry:
            raise DatabaseError("CV '" + vocabulary + "' not present in database")
        cvterm_entries = self.query_all(cv.CvTerm, cv_id=cv_entry.cv_id, is_relationshiptype=int(relationship))
        return cvterm_entries

    def _load_terms_from_cv_dict(self, vocabulary: str, required_terms: List[str], relationship=False
                                 ) -> Dict[str, cv.CvTerm]:
        """Loads CV terms from a given vocabulary and returns them in a dictionary, keyed by name"""
        cvterm_entries = self._load_terms_from_cv(vocabulary, relationship)
        cvterm_entries_dict = utils.list_to_dict(cvterm_entries, "name")
        for term in required_terms:
            if term not in cvterm_entries_dict:
                raise DatabaseError("CV term '" + term + "' not present in database")
        return cvterm_entries_dict

    @staticmethod
    def _extract_cvterm_ids_from_dict(cvterm_dict: Dict[str, cv.CvTerm], terms: List[str]) -> List[int]:
        """Extracts the IDs of CV terms from a given dictionary"""
        ids = []
        for term in terms:
            if term in cvterm_dict:
                ids.append(cvterm_dict[term].cvterm_id)
            else:
                raise DatabaseError("CV term '" + term + "' not present in database")
        return ids

    def _load_pub(self, pub_name: str) -> pub.Pub:
        """Loads a pub entry from the database"""
        pub_entry = self.query_first(pub.Pub, uniquename=pub_name)
        if not pub_entry:
            raise DatabaseError("Pub '" + pub_name + "' not present in database")
        return pub_entry

    def _load_organism(self, organism_name: str) -> organism.Organism:
        """Loads an organism entry from the database"""
        organism_entry = self.query_first(organism.Organism, abbreviation=organism_name)
        if not organism_entry:
            raise DatabaseError("Organism '" + organism_name + "' not present in database")
        return organism_entry

    def _load_feature_names(self, organism_entry: organism.Organism) -> List[str]:
        """Returns the IDs of all features for a given organism present in the database"""
        all_feature_names = []
        for feature_name, in self.session.query(sequence.Feature.uniquename).filter_by(
                organism_id=organism_entry.organism_id):
            all_feature_names.append(feature_name)
        return all_feature_names

    def _handle_organism(self, new_entry: organism.Organism) -> organism.Organism:
        """Inserts or updates an entry in the 'organism' table, and returns it"""

        # Check if the organism is already present in the database
        existing_genus_species_entry = self.query_first(
            organism.Organism, genus=new_entry.genus, species=new_entry.species,
            infraspecific_name=new_entry.infraspecific_name)
        existing_abbreviation_entry = self.query_first(organism.Organism, abbreviation=new_entry.abbreviation)

        if existing_genus_species_entry and existing_abbreviation_entry:

            # Check if the entries in database and file have the same properties, and update if not
            if self.update_organism_properties(existing_genus_species_entry, new_entry):
                self.printer.print("Updated organism '" + existing_genus_species_entry.abbreviation + "'")
            return existing_genus_species_entry

        elif existing_abbreviation_entry:

            # Inconsistent entries - print error message
            self.printer.print("ERROR: An organism with abbreviation '" + new_entry.abbreviation + "' already exists.")
            return existing_abbreviation_entry

        elif existing_genus_species_entry:

            # Inconsistent entries - print error message
            self.printer.print("ERROR: An organism with genus '" + new_entry.genus + "', species '" + new_entry.species
                               + "' and strain '" + new_entry.infraspecific_name + "' already exists.")
            return existing_genus_species_entry

        else:

            # Insert new organism entry
            self.add_and_flush(new_entry)
            self.printer.print("Inserted organism '" + new_entry.abbreviation + "'")
            return new_entry

    def _delete_organism(self, abbreviation: str) -> List[organism.Organism]:
        """Deletes an entry in the 'organism' table"""
        deleted_entries = []
        existing_entry = self.query_first(organism.Organism, abbreviation=abbreviation)
        if existing_entry:
            self.session.delete(existing_entry)
            deleted_entries.append(existing_entry)
            self.printer.print("Organism '" + abbreviation + "' has been deleted from the database.")
        else:
            self.printer.print("Organism '" + abbreviation + "' does not exist.")
        return deleted_entries

    def _handle_organismprop(self, new_entry: organism.OrganismProp, organism_name="", property_name="",
                             ) -> organism.OrganismProp:
        """Inserts or updates an entry in the 'organismprop' table, and returns it"""

        # Check if the organismprop is already present in the database
        existing_entry = self.query_first(organism.OrganismProp, organism_id=new_entry.organism_id,
                                          type_id=new_entry.type_id)
        if existing_entry:

            # Check if the entries in database and file have the same properties, and update if not
            if self.update_organismprop_properties(existing_entry, new_entry):
                self.printer.print("Updated property '" + property_name + "' = '" + new_entry.value
                                   + "' for organism '" + organism_name + "'")
            return existing_entry
        else:

            # Insert new organismprop entry
            self.add_and_flush(new_entry)
            self.printer.print("Inserted property '" + property_name + "' = '" + new_entry.value + "' for organism '"
                               + organism_name + "'")
            return new_entry

    def _handle_organism_dbxref(self, new_entry: organism.OrganismDbxRef, organism_name="", dbxref="",
                                ) -> organism.OrganismDbxRef:
        """Inserts or updates an entry in the 'organism_dbxref' table, and returns it"""

        # Check if the organism_dbxref is already present in the database
        existing_entry = self.query_first(organism.OrganismDbxRef, organism_id=new_entry.organism_id,
                                          dbxref_id=new_entry.dbxref_id)
        if existing_entry:

            # Nothing to update, return existing entry
            return existing_entry
        else:

            # Insert new organism_dbxref entry
            self.add_and_flush(new_entry)
            self.printer.print("Inserted dbxref '" + dbxref + "' for organism '" + organism_name + "'")
            return new_entry

    def _handle_db(self, new_entry: general.Db) -> general.Db:
        """Inserts or updates an entry in the 'db' table, and returns it"""

        # Check if the db is already present in the database
        existing_entry = self.query_first(general.Db, name=new_entry.name)
        if existing_entry:

            # Nothing to update, return existing entry
            return existing_entry
        else:

            # Insert new db entry
            self.add_and_flush(new_entry)
            self.printer.print("Inserted db '" + new_entry.name + "'")
            return new_entry

    def _handle_dbxref(self, new_entry: general.DbxRef, db_authority="") -> general.DbxRef:
        """Inserts or updates an entry in the 'dbxref' table, and returns it"""

        # Check if the dbxref is already present in the database
        existing_entry = self.query_first(general.DbxRef, db_id=new_entry.db_id, accession=new_entry.accession)
        if existing_entry:

            # Nothing to update, return existing entry
            return existing_entry
        else:

            # Insert new db entry
            self.add_and_flush(new_entry)
            self.printer.print("Inserted dbxref '" + db_authority + "." + new_entry.accession + "'")
            return new_entry

    def _handle_cv(self, new_entry: cv.Cv) -> cv.Cv:
        """Inserts or updates an entry in the 'cv' table, and returns it"""

        # Check if the cv is already present in the database
        existing_entry = self.query_first(cv.Cv, name=new_entry.name)
        if existing_entry:

            # Nothing to update, return existing entry
            return existing_entry
        else:

            # Insert new cv entry
            self.add_and_flush(new_entry)
            self.printer.print("Inserted controlled vocabulary '" + new_entry.name + "'")
            return new_entry

    def _handle_cvterm(self, new_entry: cv.CvTerm, vocabulary="") -> cv.CvTerm:
        """Inserts or updates an entry in the 'cvterm' table, and returns it"""

        # Check if the cvterm is already present in the database (look for dbxref)
        existing_entry = self.query_first(cv.CvTerm, dbxref_id=new_entry.dbxref_id)
        if existing_entry:

            # Nothing to update, return existing entry
            return existing_entry
        else:

            # Check if the cvterm is already present in the database (look for cv_id and name)
            existing_entry = self.query_first(cv.CvTerm, cv_id=new_entry.cv_id, name=new_entry.name)
            if existing_entry:

                # Nothing to update, return existing entry
                return existing_entry
            else:

                # Insert new cvterm entry
                self.add_and_flush(new_entry)
                self.printer.print("Inserted term '" + new_entry.name + "' in vocabulary '" + vocabulary + "'")
                return new_entry

    def _handle_feature(self, new_entry: sequence.Feature, organism_name="") -> sequence.Feature:
        """Inserts or updates an entry in the 'feature' table and returns it"""

        # Check if the feature is already present in the database
        existing_entry = self.query_first(sequence.Feature, organism_id=new_entry.organism_id,
                                          uniquename=new_entry.uniquename)
        if existing_entry:

            # Check if the entries in database and file have the same properties, and update if not
            if self.update_feature_properties(existing_entry, new_entry):
                self.printer.print("Updated feature '" + existing_entry.uniquename + "' for organism '"
                                   + organism_name + "'")
            return existing_entry
        else:

            # Insert new feature entry
            self.add_and_flush(new_entry)
            self.printer.print("Inserted feature '" + new_entry.uniquename + "' for organism '" + organism_name + "'")
            return new_entry

    def _handle_featureloc(self, new_entry: sequence.FeatureLoc, feature_name="") -> sequence.FeatureLoc:
        """Inserts or updates an entry in the 'featureloc' table, and returns it"""

        # Check if the featureloc is already present in the database
        existing_entry = self.query_first(sequence.FeatureLoc, feature_id=new_entry.feature_id)
        if existing_entry:

            # Check if the entries in database and file have the same properties, and update if not
            if self.update_featureloc_properties(existing_entry, new_entry):
                self.printer.print("Updated featureloc for feature '" + feature_name + "'")
            return existing_entry
        else:

            # Insert new featureloc entry
            self.add_and_flush(new_entry)
            self.printer.print("Inserted featureloc for feature '" + feature_name + "'")
            return new_entry

    def _handle_featureprop(self, new_entry: sequence.FeatureProp, existing_entries: List[sequence.FeatureProp],
                            property_name="", value="", feature_name="") -> sequence.FeatureProp:
        """Inserts or updates an entry in the 'featureprop' table, and returns it"""

        # Check if the featureprop is already present in the database
        matching_entries = utils.filter_objects(existing_entries, type_id=new_entry.type_id)
        for matching_entry in matching_entries:

            # Check if the entries in database and file have the same properties
            if matching_entry.value == new_entry.value:

                # Nothing to update; return existing entry
                return matching_entry
            else:

                # Adjust 'rank' to avoid a violation of the UNIQUE constraint
                new_entry.rank = max(new_entry.rank, matching_entry.rank+1)
        else:

            # Insert new featureprop entry
            self.add_and_flush(new_entry)
            self.printer.print("Inserted property '" + property_name + "' = '" + value + "' for feature '"
                               + feature_name + "'")
            return new_entry

    def _delete_featureprop(self, new_entries: List[sequence.FeatureProp],
                            existing_entries: List[sequence.FeatureProp], feature_name=""
                            ) -> List[sequence.FeatureProp]:
        """Deletes entries from the 'featureprop' table"""

        # Loop over all entries in the database
        deleted_entries = []
        for existing_entry in existing_entries:

            # Check if the entry is also present in the file
            matching_entries = utils.filter_objects(new_entries, type_id=existing_entry.type_id,
                                                    rank=existing_entry.rank)
            if not matching_entries:

                # Delete the entry from the database
                self.session.delete(existing_entry)
                deleted_entries.append(existing_entry)
                type_entry = self.query_first(cv.CvTerm, cvterm_id=existing_entry.type_id)
                self.printer.print("Deleted property '" + type_entry.name + "' = '" + existing_entry.value
                                   + "' for feature '" + feature_name + "'")

        return deleted_entries

    def _handle_feature_dbxref(self, new_entry: sequence.FeatureDbxRef, existing_entries: List[sequence.FeatureDbxRef],
                               crossref="", feature_name="") -> sequence.FeatureDbxRef:
        """Inserts or updates an entry in the 'feature_dbxref' table, and returns it"""

        # Check if the feature_dbxref is already present in the database
        matching_entries = utils.filter_objects(existing_entries, dbxref_id=new_entry.dbxref_id)
        if matching_entries:

            # Check if the entries in database and file have the same properties (there can only be one)
            matching_entry = matching_entries[0]
            if self.update_feature_dbxref_properties(matching_entry, new_entry):
                self.printer.print("Updated cross reference '" + crossref + "' for feature '" + feature_name + "'")
            return matching_entry
        else:

            # Insert new feature_dbxref entry
            self.add_and_flush(new_entry)
            self.printer.print("Inserted cross reference '" + crossref + "' for feature '" + feature_name + "'")
            return new_entry

    def _delete_feature_dbxref(self, new_entries: List[sequence.FeatureDbxRef],
                               existing_entries: List[sequence.FeatureDbxRef], feature_name=""
                               ) -> List[sequence.FeatureDbxRef]:
        """Deletes entries from the 'feature_dbxref' table"""

        # Loop over all entries in the database
        deleted_entries = []
        for existing_entry in existing_entries:

            # Check if the entry is also present in the file
            matching_entries = utils.filter_objects(new_entries, dbxref_id=existing_entry.dbxref_id)
            if not matching_entries:
                # Delete the entry from the database
                self.session.delete(existing_entry)
                deleted_entries.append(existing_entry)
                dbxref_entry = self.query_first(general.DbxRef, dbxref_id=existing_entry.dbxref_id)
                db_entry = self.query_first(general.Db, db_id=dbxref_entry.db_id)
                crossref = db_entry.name + ":" + dbxref_entry.accession
                self.printer.print("Deleted cross reference '" + crossref + "' for feature '" + feature_name + "'")

        return deleted_entries

    def _handle_feature_cvterm(self, new_entry: sequence.FeatureCvTerm, existing_entries: List[sequence.FeatureCvTerm],
                               term="", feature_name="") -> sequence.FeatureCvTerm:
        """Inserts or updates an entry in the 'feature_cvterm' table, and returns it"""

        # Check if the feature_cvterm is already present in the database
        matching_entries = utils.filter_objects(existing_entries, cvterm_id=new_entry.cvterm_id)
        if matching_entries:

            # Check if the entries in database and file have the same properties, and update if not
            # Note that there are potentially multiple entries (for different pub_ids/ranks). Ignored here.
            matching_entry = matching_entries[0]
            if self.update_feature_cvterm_properties(matching_entry, new_entry):
                self.printer.print("Updated CV term CV term '" + term + "' for feature '" + feature_name + "'")
            return matching_entry
        else:

            # Insert new feature_cvterm entry
            self.add_and_flush(new_entry)
            self.printer.print("Inserted CV term '" + term + "' for feature '" + feature_name + "'")
            return new_entry

    def _delete_feature_cvterm(self, new_entries: List[sequence.FeatureCvTerm],
                               existing_entries: List[sequence.FeatureCvTerm], feature_name=""
                               ) -> List[sequence.FeatureCvTerm]:
        """Deletes entries from the 'feature_cvterm' table"""

        # Loop over all entries in the database
        deleted_entries = []
        for existing_entry in existing_entries:

            # Check if the entry is also present in the file
            matching_entries = utils.filter_objects(new_entries, cvterm_id=existing_entry.cvterm_id,
                                                    pub_id=existing_entry.pub_id, rank=existing_entry.rank)
            if not matching_entries:

                # Delete the entry from the database
                self.session.delete(existing_entry)
                deleted_entries.append(existing_entry)
                cvterm_entry = self.query_first(cv.CvTerm, cvterm_id=existing_entry.cvterm_id)
                self.printer.print("Deleted CV term '" + cvterm_entry.name + "' for feature '" + feature_name + "'")

        return deleted_entries

    def _handle_feature_relationship(self, new_entry: sequence.FeatureRelationship,
                                     existing_entries: List[sequence.FeatureRelationship],
                                     subject_name="", object_name="", type_name="") -> sequence.FeatureRelationship:
        """Inserts or updates an entry in the 'feature_relationship' table, and returns it"""

        # Check if the feature_relationship is already present in the database
        matching_entries = utils.filter_objects(existing_entries, type_id=new_entry.type_id,
                                                object_id=new_entry.object_id)
        if matching_entries:

            # Check if the entries in database and file have the same properties, and update if not
            # Note that there are potentially multiple entries (for different ranks). Ignored here.
            matching_entry = matching_entries[0]
            if self.update_feature_relationship_properties(matching_entry, new_entry):
                self.printer.print("Updated relationship: '" + subject_name + "', '" + type_name + "', '"
                                   + object_name + "'")
            return matching_entry
        else:

            # Insert new feature_relationship entry
            self.add_and_flush(new_entry)
            self.printer.print("Inserted relationship: '" + subject_name + "', '" + type_name + "', '"
                               + object_name + "'")
            return new_entry

    def _delete_feature_relationship(self, new_entries: List[sequence.FeatureRelationship],
                                     existing_entries: List[sequence.FeatureRelationship], subject_name=""
                                     ) -> List[sequence.FeatureRelationship]:
        """Deletes entries from the 'feature_relationship' table"""

        # Loop over all entries in the database
        deleted_entries = []
        for existing_entry in existing_entries:

            # Check if the entry is also present in the file
            matching_entries = utils.filter_objects(new_entries, type_id=existing_entry.type_id,
                                                    object_id=existing_entry.object_id, rank=existing_entry.rank)
            if not matching_entries:

                # Delete the entry from the database
                self.session.delete(existing_entry)
                deleted_entries.append(existing_entry)
                object_entry = self.query_first(sequence.Feature, feature_id=existing_entry.object_id)
                type_entry = self.query_first(cv.CvTerm, cvterm_id=existing_entry.type_id)
                self.printer.print("Deleted relationship: '" + subject_name + "', '" + type_entry.name + "', '"
                                   + object_entry.uniquename + "'")

        return deleted_entries

    def _handle_synonym(self, new_entry: sequence.Synonym) -> sequence.Synonym:
        """Inserts or updates an entry in the 'synonym' table, and returns it"""

        # Check if the synonym is already present in the database
        existing_entry = self.query_first(sequence.Synonym, name=new_entry.name, type_id=new_entry.type_id)
        if existing_entry:

            # Check if the entries in database and file have the same properties, and update if not
            if self.update_synonym_properties(existing_entry, new_entry):
                self.printer.print("Updated synonym '" + existing_entry.name + "'.")
            return existing_entry
        else:

            # Insert a new synonym entry
            self.add_and_flush(new_entry)
            self.printer.print("Inserted synonym '" + new_entry.name + "'.")
            return new_entry

    def _handle_feature_synonym(self, new_entry: sequence.FeatureSynonym,
                                existing_entries: List[sequence.FeatureSynonym], synonym="", feature_name=""
                                ) -> sequence.FeatureSynonym:
        """Inserts or updates an entry in the 'feature_synonym' table, and returns it"""

        # Check if the feature_synonym is already present in the database
        matching_entries = utils.filter_objects(existing_entries, synonym_id=new_entry.synonym_id)
        if matching_entries:

            # Check if the entries in database and file have the same properties, and update if not
            # Note that there are potentially multiple entries (for different pub_ids). Ignored here.
            matching_entry = matching_entries[0]
            if self.update_feature_synonym_properties(matching_entry, new_entry):
                self.printer.print("Updated synonym '" + synonym + "' for feature '" + feature_name + "'")
            return matching_entry
        else:

            # Insert a new feature_synonym entry
            self.add_and_flush(new_entry)
            self.printer.print("Inserted synonym '" + synonym + "' for feature '" + feature_name + "'")
            return new_entry

    def _delete_feature_synonym(self, new_entries: List[sequence.FeatureSynonym],
                                existing_entries: List[sequence.FeatureSynonym], feature_name=""
                                ) -> List[sequence.FeatureSynonym]:
        """Deletes entries from the 'feature_synonym' table"""

        # Loop over all entries in the database
        deleted_entries = []
        for existing_entry in existing_entries:

            # Check if the entry is also present in the file
            matching_entries = utils.filter_objects(new_entries, synonym_id=existing_entry.synonym_id,
                                                    pub_id=existing_entry.pub_id)
            if not matching_entries:

                # Delete the entry from the database
                self.session.delete(existing_entry)
                deleted_entries.append(existing_entry)
                synonym_entry = self.query_first(sequence.Synonym, synonym_id=existing_entry.synonym_id)
                self.printer.print("Deleted synonym '" + synonym_entry.name + "' for feature '" + feature_name + "'")

        return deleted_entries

    def _handle_pub(self, new_entry: pub.Pub) -> pub.Pub:
        """Inserts or updates an entry in the 'pub' table, and returns it"""

        # Check if the publication is already present in the database
        existing_entry = self.query_first(pub.Pub, uniquename=new_entry.uniquename)
        if existing_entry:

            # Check if the entries in database and file have the same properties, and update if not
            if self.update_pub_properties(existing_entry, new_entry):
                self.printer.print("Updated publication '" + new_entry.uniquename + "'")
            return existing_entry
        else:

            # Insert a new feature_synonym entry
            self.add_and_flush(new_entry)
            self.printer.print("Inserted publication '" + new_entry.uniquename + "'")
            return new_entry

    def _handle_feature_pub(self, new_entry: sequence.FeaturePub, existing_entries: List[sequence.FeaturePub],
                            feature_name="", publication="") -> sequence.FeaturePub:
        """Inserts or updates an entry in the 'feature_pub' table, and returns it"""

        # Check if the feature_pub is already present in the database
        matching_entries = utils.filter_objects(existing_entries, pub_id=new_entry.pub_id)
        if matching_entries:

            # Nothing to update, return existing entry
            matching_entry = matching_entries[0]
            return matching_entry
        else:

            # Insert a new feature_pub entry
            self.add_and_flush(new_entry)
            self.printer.print("Inserted publication '" + publication + "' for feature '" + feature_name + "'")
            return new_entry

    def _delete_feature_pub(self, new_entries: List[sequence.FeaturePub],
                            existing_entries: List[sequence.FeaturePub], feature_name="") -> List[sequence.FeaturePub]:
        """Deletes entries from the 'feature_pub' table"""

        # Loop over all entries in the database
        deleted_entries = []
        for existing_entry in existing_entries:

            # Check if the entry is also present in the file
            matching_entries = utils.filter_objects(new_entries, pub_id=existing_entry.pub_id)
            if not matching_entries:

                # Delete the entry from the database
                self.session.delete(existing_entry)
                deleted_entries.append(existing_entry)
                pub_entry = self.query_first(pub.Pub,  pub_id=existing_entry.pub_id)
                self.printer.print("Deleted publication '" + pub_entry.uniquename
                                   + "' for feature '" + feature_name + "'")

        return deleted_entries

    def _handle_feature_cvtermprop(self, new_entry: sequence.FeatureCvTermProp,
                                   existing_entries: List[sequence.FeatureCvTermProp], key="", feature_name=""
                                   ) -> sequence.FeatureCvTermProp:
        """Inserts or updates an entry in the 'feature_cvtermprop' table, and returns it"""

        # Check if the feature_pub is already present in the database
        matching_entries = utils.filter_objects(existing_entries, type_id=new_entry.type_id)
        if matching_entries:

            # Check if the entries in database and file have the same properties, and update if not
            # Nothing to update, return existing entry
            matching_entry = matching_entries[0]
            if self.update_feature_cvtermprop_properties(matching_entry, new_entry):
                self.printer.print("Updated CV term property '" + key + "' = '" + new_entry.value
                                   + "' for feature '" + feature_name + "'")
            return matching_entry
        else:

            # Insert a new feature_cvtermprop entry
            self.add_and_flush(new_entry)
            self.printer.print("Inserted CV term property '" + key + "' = '" + new_entry.value
                               + "' for feature '" + feature_name + "'")
            return new_entry

    def _handle_feature_cvterm_dbxref(self, new_entry: sequence.FeatureCvTermDbxRef,
                                      existing_entries: List[sequence.FeatureCvTermDbxRef], crossref="", feature_name=""
                                      ) -> sequence.FeatureCvTermDbxRef:
        """Inserts or updates an entry in the 'feature_cvterm_dbxref' table, and returns it"""

        # Check if the feature_cvterm_dbxref is already present in the database
        matching_entries = utils.filter_objects(existing_entries, dbxref_id=new_entry.dbxref_id)
        if matching_entries:

            # Nothing to update, return existing entry
            matching_entry = matching_entries[0]
            return matching_entry
        else:

            # Insert a new feature_cvterm_dbxref entry
            self.add_and_flush(new_entry)
            self.printer.print("Inserted CV term cross reference '" + crossref + "' for feature '" + feature_name + "'")
            return new_entry

    def _handle_feature_cvterm_pub(self, new_entry: sequence.FeatureCvTermPub,
                                   existing_entries: List[sequence.FeatureCvTermPub], publication="", feature_name=""
                                   ) -> sequence.FeatureCvTermPub:
        """Inserts or updates an entry in the 'feature_cvterm_pub' table, and returns it"""

        # Check if the feature_cvterm_pub is already present in the database
        matching_entries = utils.filter_objects(existing_entries, pub_id=new_entry.pub_id)
        if matching_entries:

            # Nothing to update, return existing entry
            matching_entry = matching_entries[0]
            return matching_entry
        else:

            # Insert a new feature_cvterm_pub entry
            self.add_and_flush(new_entry)
            self.printer.print("Inserted CV term publication '" + publication + "' for feature '" + feature_name + "'")
            return new_entry

    def _mark_feature_as_obsolete(self, organism_entry: organism.Organism, uniquename: str) -> sequence.Feature:
        """Marks a feature as obsolete"""
        feature_entry = self.query_first(sequence.Feature, organism_id=organism_entry.organism_id,
                                         uniquename=uniquename)
        if not feature_entry.is_obsolete:
            feature_entry.is_obsolete = True
            self.printer.print("Marked feature '" + feature_entry.uniquename + "' as obsolete")
        return feature_entry

    @staticmethod
    def update_organism_properties(existing_entry: organism.Organism, new_entry: organism.Organism) -> bool:
        """Updates the properties of an organism entry in the database"""
        updated = False
        for attribute in ["common_name", "comment", "type_id"]:
            if utils.copy_attribute(existing_entry, new_entry, attribute):
                updated = True
        return updated

    @staticmethod
    def update_organismprop_properties(existing_entry: organism.OrganismProp, new_entry: organism.OrganismProp) -> bool:
        """Updates the properties of an organismprop entry in the database"""
        updated = False
        if utils.copy_attribute(existing_entry, new_entry, "value"):
            updated = True
        return updated

    @staticmethod
    def update_pub_properties(existing_entry: pub.Pub, new_entry: pub.Pub) -> bool:
        """Updates the properties of a pub entry in the database"""
        updated = False
        for attribute in ["title", "volume", "volumetitle", "series_name", "issue", "pyear", "pages", "miniref",
                          "publisher", "pubplace", "is_obsolete"]:
            if utils.copy_attribute(existing_entry, new_entry, attribute):
                updated = True
        return updated

    @staticmethod
    def update_feature_properties(existing_entry: sequence.Feature, new_entry: sequence.Feature) -> bool:
        """Updates the properties of a feature entry in the database"""
        updated = False
        for attribute in ["name", "type_id", "residues", "seqlen", "md5checksum", "is_analysis", "is_obsolete"]:
            if utils.copy_attribute(existing_entry, new_entry, attribute):
                updated = True
        return updated

    @staticmethod
    def update_featureloc_properties(existing_entry: sequence.FeatureLoc, new_entry: sequence.FeatureLoc) -> bool:
        """Updates the properties of a featureloc entry in the database"""
        updated = False
        for attribute in ["fmin", "fmax", "strand", "phase"]:
            if utils.copy_attribute(existing_entry, new_entry, attribute):
                updated = True
        return updated

    @staticmethod
    def update_feature_dbxref_properties(existing_entry: sequence.FeatureDbxRef,
                                         new_entry: sequence.FeatureDbxRef) -> bool:
        """Updates the properties of a feature_dbxref entry in the database"""
        updated = False
        if utils.copy_attribute(existing_entry, new_entry, "is_current"):
            updated = True
        return updated

    @staticmethod
    def update_feature_cvterm_properties(existing_entry: sequence.FeatureCvTerm,
                                         new_entry: sequence.FeatureCvTerm) -> bool:
        """Updates the properties of a feature_cvterm entry in the database"""
        updated = False
        if utils.copy_attribute(existing_entry, new_entry, "is_not"):
            updated = True
        return updated

    @staticmethod
    def update_feature_cvtermprop_properties(existing_entry: sequence.FeatureCvTermProp,
                                             new_entry: sequence.FeatureCvTermProp) -> bool:
        """Updates the properties of a feature_cvtermprop entry in the database"""
        updated = False
        if utils.copy_attribute(existing_entry, new_entry, "value"):
            updated = True
        return updated

    @staticmethod
    def update_feature_relationship_properties(existing_entry: sequence.FeatureRelationship,
                                               new_entry: sequence.FeatureRelationship) -> bool:
        """Updates the properties of a feature_relationship entry in the database"""
        updated = False
        if utils.copy_attribute(existing_entry, new_entry, "value"):
            updated = True
        return updated

    @staticmethod
    def update_synonym_properties(existing_entry: sequence.Synonym, new_entry: sequence.Synonym) -> bool:
        """Updates the properties of a synonym entry in the database"""
        updated = False
        if utils.copy_attribute(existing_entry, new_entry, "synonym_sgml"):
            updated = True
        return updated

    @staticmethod
    def update_feature_synonym_properties(existing_entry: sequence.FeatureSynonym,
                                          new_entry: sequence.FeatureSynonym) -> bool:
        """Updates the properties of a feature_synonym entry in the database"""
        updated = False
        for attribute in ["is_internal", "is_current"]:
            if utils.copy_attribute(existing_entry, new_entry, attribute):
                updated = True
        return updated
