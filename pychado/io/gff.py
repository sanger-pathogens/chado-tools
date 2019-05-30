import os
import tempfile
from typing import List, Dict, Union
import gffutils
from . import iobase, ontology, fasta
from .. import utils
from ..orm import general, cv, organism, pub, sequence


class ArtemisGffAttribute:
    """Helper class for complex GFF attributes in files created by Artemis"""

    def __init__(self):
        """Initializes the object"""
        self.value = ""                      # type: str
        self.list_params = []                # type: List[str]
        self.dict_params = {}                # type: Dict[str, Union[str, int, float, bool]]


class GFFClient(object):
    """Helper class for GFF-related operations"""

    @staticmethod
    def parse_artemis_gff_attribute(attribute: str) -> ArtemisGffAttribute:
        """Function to parse a GFF attribute into its constituents"""
        artemis_attribute = ArtemisGffAttribute()
        elements = attribute.split(";")
        for element in elements:
            if not element:
                continue
            key_value_pair = element.split("=", 1)
            if len(key_value_pair) == 2:
                k = key_value_pair[0]
                v = utils.parse_string(key_value_pair[1])
                artemis_attribute.dict_params[k] = v
            else:
                artemis_attribute.list_params.append(element)
        if artemis_attribute.list_params:
            artemis_attribute.value = artemis_attribute.list_params[0]
        elif "term" in artemis_attribute.dict_params:
            artemis_attribute.value = artemis_attribute.dict_params["term"]
        return artemis_attribute

    @staticmethod
    def convert_strand(strand: str) -> Union[None, int]:
        """Converts the strand from string notation to integer notation"""
        if strand == '+':
            return 1
        elif strand == '-':
            return -1
        else:
            return None

    @staticmethod
    def back_convert_strand(strand: Union[None, int]) -> str:
        """Converts the strand from integer notation to string notation"""
        if strand is None:
            return "."
        elif strand > 0:
            return "+"
        elif strand < 0:
            return "-"
        else:
            return "."

    @staticmethod
    def convert_frame(frame: str) -> Union[None, int]:
        """Converts the frame from string notation to integer notation"""
        try:
            phase = int(frame)
        except ValueError:
            return None
        if phase in [0, 1, 2]:
            return phase
        else:
            return None

    @staticmethod
    def back_convert_frame(phase: Union[None, int]) -> str:
        """Converts the frame from integer notation to string notation"""
        if phase is None:
            return "."
        else:
            return str(phase)

    @staticmethod
    def _transcript_types() -> List[str]:
        """Lists considered transcript types"""
        return ["mrna", "rrna", "trna", "snrna", "ncrna", "scrna", "snorna", "pseudogenic_transcript"]

    @staticmethod
    def _feature_relationship_types() -> List[str]:
        """Lists considered feature_relationship types"""
        return ["part_of", "derives_from"]

    @staticmethod
    def _feature_property_types() -> List[str]:
        """Lists considered featureprop types"""
        return ["comment", "description", "score", "source"]

    @staticmethod
    def _synonym_types() -> List[str]:
        """Lists considered synonym types"""
        return ["alias", "synonym", "previous_systematic_id"]


class GFFImportClient(iobase.ChadoClient, GFFClient):
    """Class for importing genomic data from GFF files into Chado"""

    def __init__(self, uri: str, verbose=False, test_environment=False):
        """Constructor"""

        # Connect to database
        self.uri = uri
        self.verbose = verbose
        self.test_environment = test_environment
        if self.test_environment:
            self.printer = utils.VerbosePrinter(self.verbose)
        else:
            super().__init__(self.uri, self.verbose)

        # Create array for temporary SQLite databases
        self._sqlite_databases = []

        # Load essential database entries
        if not self.test_environment:
            self._load_essentials()

        # Set default values for global options
        self.fresh_load = False
        self.force_purge = False
        self.full_genome = False
        self.full_attributes = False

    def __del__(self):
        """Destructor"""

        # Disconnect from database
        if not self.test_environment:
            super().__del__()

        # Delete temporary SQLite database
        for database in self._sqlite_databases:
            if os.path.exists(database):
                os.remove(database)

    def _load_essentials(self) -> None:
        """Loads essential database entries"""

        self._part_of_term = self._load_cvterm_from_cv("part_of", "relationship")
        self._derives_from_term = self._load_cvterm_from_cv("derives_from", "sequence")
        self._parent_terms = {self._part_of_term.name: self._part_of_term,
                              self._derives_from_term.name: self._derives_from_term}
        self._parent_type_ids = [self._part_of_term.cvterm_id, self._derives_from_term.cvterm_id]

        self._synonym_terms = self._load_terms_from_cv_dict(
            "genedb_synonym_type", self._synonym_types())
        self._synonym_type_ids = self._extract_cvterm_ids_from_dict(
            self._synonym_terms, self._synonym_types())

        self._feature_property_terms = self._load_terms_from_cv_dict(
            "feature_property", self._feature_property_types())
        self._feature_property_type_ids = self._extract_cvterm_ids_from_dict(
            self._feature_property_terms, self._feature_property_types())

        self._sequence_terms = self._load_terms_from_cv_dict(
            "sequence", ["gene", "intron", "exon", "CDS", "mRNA", "chromosome"])
        self._default_pub = self._load_pub("null")

        self._go_db = self._load_db("GO")

    def load(self, filename: str, organism_name: str, fasta_filename: str, sequence_type: str, fresh_load=False,
             force_purge=False, full_genome=False, full_attributes=False):
        """Import data from a GFF3 file into a Chado database"""

        # Update global options
        self.fresh_load = fresh_load
        self.force_purge = force_purge
        self.full_genome = full_genome
        self.full_attributes = full_attributes

        # Check for file existence
        if not os.path.exists(filename):
            raise iobase.InputFileError("Input file '" + filename + "' does not exist.")

        # Remove existing database entries, if applicable
        default_organism = self._load_organism(organism_name)
        self._handle_existing_features(default_organism)

        # Import FASTA sequences, if present
        self._import_fasta(filename, fasta_filename, organism_name, sequence_type)

        # Create temporary SQLite database
        gff_db = self._create_sqlite_db(filename)

        # Initiate global containers
        all_feature_entries = {}

        # Loop over all entries in the gff file
        for gff_record in gff_db.all_features():

            # Insert, update or delete entries in various tables
            self._insert_gff_record_into_database(gff_record, default_organism, all_feature_entries)

        # Mark obsolete features
        if self.full_genome and not self.fresh_load:
            top_level_entries = self._extract_gff_sequence_names(gff_db)
            self._mark_obsolete_features(default_organism, all_feature_entries, top_level_entries)

        # Commit changes
        self.session.commit()

    def _import_fasta(self, gff_file: str, fasta_file: str, organism_name: str, sequence_type: str) -> None:
        """Imports sequences from a FASTA file into the Chado database"""

        # Check if the GFF file contains FASTA sequences
        fasta_is_temporary = False
        if self._has_fasta(gff_file):
            if fasta_file:

                # Error message - only one file with FASTA is permitted
                raise iobase.InputFileError("You cannot provide a GFF file with FASTA sequences "
                                            "plus a separate FASTA file.")
            else:

                # Create a FASTA file containing the sequences in the GFF file
                (fasta_handle, fasta_file) = tempfile.mkstemp(dir=os.getcwd())
                os.close(fasta_handle)
                fasta_is_temporary = True
                self._split_off_fasta(gff_file, fasta_file)

        # Import sequences from FASTA file, if present
        if fasta_file:
            fasta_client = fasta.FastaImportClient(self.uri, self.verbose)
            fasta_client.load(fasta_file, organism_name, sequence_type)

        # Delete temporary file
        if fasta_is_temporary and os.path.exists(fasta_file):
            os.remove(fasta_file)

    @staticmethod
    def _has_fasta(gff_file: str) -> bool:
        """Checks if a GFF file contains a FASTA section"""
        infile = utils.open_file_read(gff_file)
        fasta_started = False
        for line in infile:
            if "##FASTA" in line:
                fasta_started = True
                break
        utils.close(infile)
        return fasta_started

    @staticmethod
    def _split_off_fasta(gff_file: str, fasta_file: str) -> None:
        """Copies the FASTA section from a GFF file into a separate FASTA file"""
        infile = utils.open_file_read(gff_file)
        outfile = utils.open_file_write(fasta_file)
        fasta_started = False
        for line in infile:
            if fasta_started:
                outfile.write(line)
            else:
                if "##FASTA" in line:
                    fasta_started = True
        utils.close(infile)
        utils.close(outfile)

    def _create_sqlite_db(self, filename: str) -> gffutils.FeatureDB:
        """Creates a local SQLite database containing data from a GFF file"""
        database_name = os.path.abspath(filename) + ".sqlitedb"
        self._sqlite_databases.append(database_name)
        gffutils.create_db(filename, database_name, force=True, keep_order=True)
        database = gffutils.FeatureDB(database_name)
        return database

    def _handle_existing_features(self, organism_entry: organism.Organism) -> None:
        """Checks if there are existing features for the organism, and deletes them if required"""

        # Check if this is an import "from scratch". If not, there is no need to take any action
        if not self.fresh_load:
            return

        # Check if the database already contains features for this organism. If not, there is no need to take any action
        existing_features_query = self.query_table(sequence.Feature, organism_id=organism_entry.organism_id)
        if existing_features_query.count() == 0:
            return

        # Check if the '--force' option was used
        if not self.force_purge:

            # Abort the operation
            raise iobase.DatabaseError("The database already contains features for organism '"
                                       + organism_entry.abbreviation + "'. Run without option '--fresh_load' to update"
                                       + " the features or with option '--force' to overwrite everything.")
        else:

            # Delete all existing features for this organism
            self.printer.print("Deleting all features for organism '" + organism_entry.abbreviation + "'")
            existing_features_query.delete()

    def _mark_obsolete_features(self, organism_entry: organism.Organism,
                                all_features: Dict[str, sequence.Feature], top_level_features: List[str]) -> None:
        """Marks features as obsolete"""

        # Loop over all features for the given organism in the database
        for feature_name in self._load_feature_names(organism_entry):

            # Check if the feature is also present in the input file
            if feature_name not in all_features and feature_name not in top_level_features:

                # Mark the feature as obsolete, if necessary
                self._mark_feature_as_obsolete(organism_entry, feature_name)

    def _insert_gff_record_into_database(self, gff_record: gffutils.Feature, organism_entry: organism.Organism,
                                         all_feature_entries: Dict[str, sequence.Feature]):
        """Inserts, updates or deletes entries in various tables"""

        # Insert/update/get entry in the 'feature' tables
        feature_entry = self._handle_child_feature(gff_record, organism_entry)
        if feature_entry:

            # Insert/update/delete entries connected to this 'feature' entry in various tables
            self._handle_location(gff_record, feature_entry)
            self._handle_synonyms(gff_record, feature_entry)
            self._handle_properties(gff_record, feature_entry)
            self._handle_cross_references(gff_record, feature_entry)
            self._handle_ontology_terms(gff_record, feature_entry)
            self._handle_publications(gff_record, feature_entry)
            self._handle_relationships(gff_record, feature_entry, all_feature_entries)

            # Insert/update/delete entries connected to the associated protein (if present) in various tables
            self._handle_protein(gff_record, feature_entry, organism_entry, all_feature_entries)

            # Save 'feature' entry in global array
            self._check_if_gff_attributes_are_recognized(gff_record)
            all_feature_entries[feature_entry.uniquename] = feature_entry

    def _handle_child_feature(self, gff_record: gffutils.Feature, organism_entry: organism.Organism
                              ) -> Union[None, sequence.Feature]:
        """Inserts or updates an entry in the 'feature' table and returns it"""

        # Check if all dependencies are met
        if gff_record.featuretype not in self._sequence_terms:
            self.printer.print("WARNING: Sequence type '" + gff_record.featuretype + "' not present in database")
            return None
        type_entry = self._sequence_terms[gff_record.featuretype]

        # Create a feature object, and update the corresponding table
        new_feature_entry = self._create_feature(gff_record, organism_entry.organism_id, type_entry.cvterm_id)
        feature_entry = self._handle_feature(new_feature_entry, organism_entry.abbreviation)
        return feature_entry

    def _handle_location(self, gff_record: gffutils.Feature, feature_entry: sequence.Feature
                         ) -> Union[None, sequence.FeatureLoc]:
        """Inserts or updates an entry in the 'featureloc' table and returns it"""

        # Ignore if the considered feature is in fact the 'srcfeature'
        if gff_record.seqid == gff_record.id:
            return None

        # Get entry from 'srcfeature' table
        srcfeature_entry = self.query_first(sequence.Feature, organism_id=feature_entry.organism_id,
                                            uniquename=gff_record.seqid)
        if not srcfeature_entry:
            self.printer.print("WARNING: Parent sequence '" + gff_record.seqid + "' not present in database")
            return None

        # Insert/update entry in the 'featureloc' table
        new_featureloc_entry = self._create_featureloc(gff_record, feature_entry.feature_id,
                                                       srcfeature_entry.feature_id)
        featureloc_entry = self._handle_featureloc(new_featureloc_entry, feature_entry.uniquename)
        return featureloc_entry

    def _handle_synonyms(self, gff_record: gffutils.Feature, feature_entry: sequence.Feature
                         ) -> List[sequence.FeatureSynonym]:
        """Inserts, updates and deletes entries in the 'synonym' and 'feature_synonym' tables and returns the latter"""

        # Extract existing synonyms for this feature from the database
        existing_feature_synonyms = self.query_feature_synonym_by_type(
            feature_entry.feature_id, self._synonym_type_ids).all()
        all_feature_synonyms = []

        # Loop over all synonyms for this feature in the GFF record
        synonyms = self._extract_gff_synonyms(gff_record)
        for synonym_type, aliases in synonyms.items():

            # Get database entry for synonym type
            if synonym_type not in self._synonym_terms:
                self.printer.print("WARNING: Synonym type '" + synonym_type + "' not present in database.")
                continue
            type_entry = self._synonym_terms[synonym_type]

            for alias in aliases:

                # Insert/update entry in the 'synonym' table
                new_synonym_entry = sequence.Synonym(name=alias.value, type_id=type_entry.cvterm_id,
                                                     synonym_sgml=alias.value)
                synonym_entry = self._handle_synonym(new_synonym_entry)

                # Insert/update entry in the 'feature_synonym' table
                is_current = None
                if "current" in alias.dict_params:
                    is_current = alias.dict_params["current"]
                new_feature_synonym_entry = sequence.FeatureSynonym(
                    synonym_id=synonym_entry.synonym_id, feature_id=feature_entry.feature_id,
                    pub_id=self._default_pub.pub_id, is_current=is_current)
                feature_synonym_entry = self._handle_feature_synonym(
                    new_feature_synonym_entry, existing_feature_synonyms, alias.value, feature_entry.uniquename)
                existing_feature_synonyms.append(feature_synonym_entry)
                all_feature_synonyms.append(feature_synonym_entry)

        # Delete obsolete entries
        if self.full_attributes:
            self._delete_feature_synonym(all_feature_synonyms, existing_feature_synonyms, feature_entry.uniquename)
        return all_feature_synonyms

    def _handle_publications(self, gff_record: gffutils.Feature, feature_entry: sequence.Feature
                             ) -> List[sequence.FeaturePub]:
        """Inserts, updates and deletes entries in the 'pub' and 'feature_pub' tables and returns the latter"""

        # Extract existing publications for this feature from the database
        existing_feature_pubs = self.query_all(sequence.FeaturePub, feature_id=feature_entry.feature_id)
        all_feature_pubs = []

        # Loop over all publications for this feature in the GFF record
        publications = self._extract_gff_publications(gff_record)
        for publication in publications:

            # Insert/update entry in the 'pub' table
            new_pub_entry = pub.Pub(uniquename=publication, type_id=self._default_pub.type_id)
            pub_entry = self._handle_pub(new_pub_entry)

            # Insert/update entry in the 'feature_pub' table
            new_feature_pub_entry = sequence.FeaturePub(feature_id=feature_entry.feature_id, pub_id=pub_entry.pub_id)
            feature_pub_entry = self._handle_feature_pub(new_feature_pub_entry, existing_feature_pubs,
                                                         feature_entry.uniquename, pub_entry.uniquename)
            existing_feature_pubs.append(feature_pub_entry)
            all_feature_pubs.append(feature_pub_entry)

        # Delete obsolete entries
        if self.full_attributes:
            self._delete_feature_pub(all_feature_pubs, existing_feature_pubs, feature_entry.uniquename)
        return all_feature_pubs

    def _handle_relationships(self, gff_record: gffutils.Feature, subject_entry: sequence.Feature,
                              all_features: Dict[str, sequence.Feature]) -> List[sequence.FeatureRelationship]:
        """Inserts, updates and deletes entries in the 'feature_relationship' table and returns them"""

        # Extract existing relationships for this subject from the database
        existing_feature_relationships = self.query_feature_relationship_by_type(
            subject_entry.feature_id, self._parent_type_ids).all()
        all_feature_relationships = []

        # Loop over all relationships for this feature in the GFF record
        relationships = self._extract_gff_relationships(gff_record)
        for relationship, parents in relationships.items():

            # Get database entry for relationship type
            type_entry = self._parent_terms[relationship]

            for parent in parents:

                # Get database entry for object
                if parent in all_features:
                    object_entry = all_features[parent]
                else:
                    object_entry = self.query_first(sequence.Feature, organism_id=subject_entry.organism_id,
                                                    uniquename=parent)
                if not object_entry:
                    self.printer.print("WARNING: Feature '" + parent +
                                       "' neither present in input file nor in database.")
                    continue

                # Insert/update entry in the 'feature_relationship' table
                new_relationship_entry = sequence.FeatureRelationship(subject_id=subject_entry.feature_id,
                                                                      object_id=object_entry.feature_id,
                                                                      type_id=type_entry.cvterm_id)
                feature_relationship_entry = self._handle_feature_relationship(
                    new_relationship_entry, existing_feature_relationships, subject_entry.uniquename,
                    object_entry.uniquename, type_entry.name)
                existing_feature_relationships.append(feature_relationship_entry)
                all_feature_relationships.append(feature_relationship_entry)

        # Delete obsolete entries
        if self.full_attributes:
            self._delete_feature_relationship(all_feature_relationships, existing_feature_relationships,
                                              subject_entry.uniquename)
        return all_feature_relationships

    def _handle_properties(self, gff_record: gffutils.Feature, feature_entry: sequence.Feature
                           ) -> List[sequence.FeatureProp]:
        """Inserts, updates and deletes entries in the 'featureprop' table and returns them"""

        # Extract existing properties for this feature from the database
        existing_featureprops = self.query_featureprop_by_type(
            feature_entry.feature_id, self._feature_property_type_ids).all()
        all_featureprops = []

        # Loop over all properties of this feature in the GFF record
        props = self._extract_gff_properties(gff_record)
        for prop, values in props.items():
            for value in values:

                # Get database entry for property type from array
                if prop not in self._feature_property_terms:
                    self.printer.print("WARNING: Feature property term '" + prop + "' not present in input file.")
                    continue
                type_entry = self._feature_property_terms[prop]

                # Insert/update entry in the 'feature_relationship' table
                new_featureprop_entry = sequence.FeatureProp(feature_id=feature_entry.feature_id,
                                                             type_id=type_entry.cvterm_id, value=value)
                featureprop_entry = self._handle_featureprop(new_featureprop_entry, existing_featureprops, prop, value,
                                                             feature_entry.uniquename)
                existing_featureprops.append(featureprop_entry)
                all_featureprops.append(featureprop_entry)

        # Delete obsolete entries
        if self.full_attributes:
            self._delete_featureprop(all_featureprops, existing_featureprops, feature_entry.uniquename)
        return all_featureprops

    def _handle_cross_references(self, gff_record: gffutils.Feature, feature_entry: sequence.Feature
                                 ) -> List[sequence.FeatureDbxRef]:
        """Inserts, updates and deletes entries in the 'feature_dbxref' table and returns them"""

        # Extract existing cross references for this feature from the database
        existing_feature_dbxrefs = self.query_all(sequence.FeatureDbxRef, feature_id=feature_entry.feature_id)
        all_feature_dbxrefs = []

        # Loop over all cross references of this feature in the GFF record
        crossrefs = self._extract_gff_crossrefs(gff_record)
        for crossref in crossrefs:

            # Split database cross reference (dbxref) into db, accession, version
            (db_authority, accession, version) = ontology.split_dbxref(crossref)

            # Insert/update entry in the 'db' table
            new_db_entry = general.Db(name=db_authority)
            db_entry = self._handle_db(new_db_entry)

            # Insert/update entry in the 'dbxref' table
            new_dbxref_entry = general.DbxRef(db_id=db_entry.db_id, accession=accession, version=version)
            dbxref_entry = self._handle_dbxref(new_dbxref_entry, db_authority)

            # Insert/update entry in the 'feature_dbxref' table
            new_feature_dbxref_entry = sequence.FeatureDbxRef(feature_id=feature_entry.feature_id,
                                                              dbxref_id=dbxref_entry.dbxref_id)
            feature_dbxref_entry = self._handle_feature_dbxref(new_feature_dbxref_entry, existing_feature_dbxrefs,
                                                               crossref, feature_entry.uniquename)
            existing_feature_dbxrefs.append(feature_dbxref_entry)
            all_feature_dbxrefs.append(feature_dbxref_entry)

        # Delete obsolete entries
        if self.full_attributes:
            self._delete_feature_dbxref(all_feature_dbxrefs, existing_feature_dbxrefs, feature_entry.uniquename)
        return all_feature_dbxrefs

    def _handle_ontology_terms(self, gff_record: gffutils.Feature, feature_entry: sequence.Feature
                               ) -> List[sequence.FeatureCvTerm]:
        """Inserts, updates and deletes entries in the 'feature_cvterm' table and returns them"""

        # Extract existing ontology terms for this feature from the database
        existing_feature_cvterms = self.query_feature_cvterm_by_ontology(
            feature_entry.feature_id, self._go_db.db_id).all()
        all_feature_cvterms = []

        # Loop over all ontology terms of this feature in the GFF record
        ontology_terms = self._extract_gff_ontology_terms(gff_record)
        for ontology_term in ontology_terms:

            # Split database cross reference (dbxref) into db, accession, version
            (db_authority, accession, version) = ontology.split_dbxref(ontology_term)

            # Get entry from 'db' table
            db_entry = self.query_first(general.Db, name=db_authority)
            if not db_entry:
                self.printer.print("WARNING: Ontology '" + db_authority + "' not present in database.")
                continue

            # Get entry from 'dbxref' table
            dbxref_entry = self.query_first(general.DbxRef, db_id=db_entry.db_id, accession=accession)
            if not dbxref_entry:
                self.printer.print("WARNING: Ontology term '" + ontology_term + "' not present in database.")
                continue

            # Get entry from 'cvterm' table
            cvterm_entry = self.query_first(cv.CvTerm, dbxref_id=dbxref_entry.dbxref_id)
            if not cvterm_entry:
                self.printer.print("WARNING: CV term for ontology term '" + ontology_term
                                   + "' not present in database.")
                continue

            # Insert/update entry in the 'feature_cvterm' table
            new_feature_cvterm_entry = sequence.FeatureCvTerm(feature_id=feature_entry.feature_id,
                                                              cvterm_id=cvterm_entry.cvterm_id,
                                                              pub_id=self._default_pub.pub_id)
            feature_cvterm_entry = self._handle_feature_cvterm(new_feature_cvterm_entry, existing_feature_cvterms,
                                                               cvterm_entry.name, feature_entry.uniquename)
            existing_feature_cvterms.append(feature_cvterm_entry)
            all_feature_cvterms.append(feature_cvterm_entry)

        # Delete obsolete entries
        if self.full_attributes:
            self._delete_feature_cvterm(all_feature_cvterms, existing_feature_cvterms, feature_entry.uniquename)
        return all_feature_cvterms

    def _handle_protein(self, gff_record: gffutils.Feature, feature_entry: sequence.Feature,
                        organism_entry: organism.Organism, all_feature_entries: Dict[str, sequence.Feature]):
        """Creates a separate feature in Chado for a protein associated with a GFF feature"""

        # Check if the GFF record is associated with a polypeptide, and if yes extract its name
        protein_source_id = self._extract_protein_source_id(gff_record)
        if not protein_source_id:
            return

        # Get the 'feature' and 'featureloc' entries for the transcript
        if gff_record.featuretype.lower() in self._transcript_types():
            parent_entry = feature_entry
        else:
            parent_entry = self.query_parent_features(
                feature_entry.feature_id,
                [self._parent_terms["part_of"].cvterm_id]).first()                          # type: sequence.Feature
        if parent_entry:
            loc_entry = self.query_first(sequence.FeatureLoc,
                                         feature_id=parent_entry.feature_id)                # type: sequence.FeatureLoc
        else:
            loc_entry = sequence.FeatureLoc(feature_id=0, srcfeature_id=0, fmin=None, fmax=None, strand=None)

        # Create a new GFF record
        protein_feature = gffutils.Feature(seqid=gff_record.seqid, source=gff_record.source,
                                           start=loc_entry.fmin + 1, end=loc_entry.fmax,
                                           strand=self.back_convert_strand(loc_entry.strand),
                                           featuretype="polypeptide", id=protein_source_id,
                                           attributes={"Derives_from": parent_entry.uniquename})

        # Insert, update or delete entries in various tables for this GFF record (Note: recursive call)
        self._insert_gff_record_into_database(protein_feature, organism_entry, all_feature_entries)

    def _check_if_gff_attributes_are_recognized(self, gff_record: gffutils.Feature) -> bool:
        """Checks if all attributes of a GFF record can be recognized"""
        all_recognized = True
        for key in gff_record.attributes.keys():
            if key.lower() not in self._recognized_gff_attributes():
                self.printer.print("WARNING: The attribute '" + key + "' for feature '" + gff_record.id +
                                   "' is unknown by this program and can't be loaded into the database.")
                all_recognized = False
        return all_recognized

    def _create_feature(self, gff_record: gffutils.Feature, organism_id: int, type_id: int) -> sequence.Feature:
        """Creates a feature object from a GFF record"""
        name = self._extract_gff_name(gff_record)
        residues = self._extract_gff_translation(gff_record)
        seqlen = self._extract_gff_size(gff_record)
        if residues is not None:
            seqlen = len(residues)
        return sequence.Feature(organism_id=organism_id, type_id=type_id, uniquename=gff_record.id, name=name,
                                residues=residues, seqlen=seqlen)

    def _create_featureloc(self, gff_record: gffutils.Feature, feature_id: int, srcfeature_id: int
                           ) -> sequence.FeatureLoc:
        """Creates a featureloc object from a GFF record
        coordinates are converted from base-oriented (1-based) to interbase (0-based)"""
        return sequence.FeatureLoc(
            feature_id=feature_id, srcfeature_id=srcfeature_id, fmin=gff_record.start - 1, fmax=gff_record.end,
            strand=self.convert_strand(gff_record.strand), phase=self.convert_frame(gff_record.frame))

    @staticmethod
    def _extract_gff_crossrefs(gff_record: gffutils.Feature) -> List[str]:
        """Extract database cross references from a GFF record"""
        crossrefs = []
        for key, value in gff_record.attributes.items():
            if key.lower() == "dbxref":
                if isinstance(value, str):
                    crossrefs.append(value)
                elif isinstance(value, list):
                    crossrefs.extend(value)
        return crossrefs

    @staticmethod
    def _extract_gff_ontology_terms(gff_record: gffutils.Feature) -> List[str]:
        """Extract cross references to ontology terms from a GFF record"""
        ontology_terms = []
        if "Ontology_term" in gff_record.attributes:
            ontology_terms = gff_record.attributes["Ontology_term"]
            if isinstance(ontology_terms, str):
                ontology_terms = [ontology_terms]
        return ontology_terms

    def _extract_gff_properties(self, gff_record: gffutils.Feature) -> Dict[str, List[str]]:
        """Extracts properties from a GFF record. Properties are 'score', 'source' and certain attributes"""
        gff_to_chado_key = {"note": "comment"}
        properties = {}
        if gff_record.score and gff_record.score != '.':
            properties["score"] = [gff_record.score]
        if gff_record.source and gff_record.source != '.':
            properties["source"] = [gff_record.source]

        for gff_key, value in gff_record.attributes.items():

            chado_key = None
            if gff_key.lower() in gff_to_chado_key.keys():
                chado_key = gff_to_chado_key[gff_key.lower()]
            elif gff_key.lower() in self._feature_property_types():
                chado_key = gff_key.lower()

            if chado_key:
                if isinstance(value, str):
                    properties[chado_key] = [value]
                elif isinstance(value, list):
                    properties[chado_key] = value
        return properties

    def _extract_gff_relationships(self, gff_record: gffutils.Feature) -> Dict[str, List[str]]:
        """Extracts the relationships to other features from a GFF record"""
        gff_to_chado_key = {"parent": "part_of"}
        relationships = {}
        for gff_key, value in gff_record.attributes.items():

            chado_key = None
            if gff_key.lower() in gff_to_chado_key.keys():
                chado_key = gff_to_chado_key[gff_key.lower()]
            elif gff_key.lower() in self._feature_relationship_types():
                chado_key = gff_key.lower()

            if chado_key:
                if isinstance(value, str):
                    relationships[chado_key] = [value]
                elif isinstance(value, list):
                    relationships[chado_key] = value
        return relationships

    def _extract_gff_synonyms(self, gff_record: gffutils.Feature) -> Dict[str, List[ArtemisGffAttribute]]:
        """Extracts synonyms/alias names from a GFF record"""
        aliases = {}
        for gff_key, value in gff_record.attributes.items():

            chado_key = None
            if gff_key.lower() in self._synonym_types():
                chado_key = gff_key.lower()

            if chado_key:
                if isinstance(value, str):
                    aliases[gff_key.lower()] = [self.parse_artemis_gff_attribute(value)]
                elif isinstance(value, list):
                    aliases[gff_key.lower()] = [self.parse_artemis_gff_attribute(v) for v in value]
        return aliases

    @staticmethod
    def _extract_gff_name(gff_record: gffutils.Feature) -> Union[None, str]:
        """Extracts the feature name from a GFF record"""
        name = None
        if "Name" in gff_record.attributes:
            name = gff_record.attributes["Name"]
            if isinstance(name, list):
                name = name[0]
        return name

    @staticmethod
    def _extract_gff_size(gff_record: gffutils.Feature) -> Union[None, int]:
        """Extracts the sequence length of a feature from a GFF record"""
        size = None
        if "size" in gff_record.attributes:
            size = gff_record.attributes["size"]
            if isinstance(size, list):
                size = size[0]
            size = int(size)
        return size

    @staticmethod
    def _extract_gff_translation(gff_record: gffutils.Feature) -> Union[None, str]:
        """Extracts the sequence of amino acids from a GFF record representing a polypeptide"""
        residues = None
        if "translation" in gff_record.attributes:
            residues = gff_record.attributes["translation"]
            if isinstance(residues, str):
                residues = residues.upper()
            elif isinstance(residues, list):
                residues = residues[0].upper()
        return residues

    @staticmethod
    def _extract_gff_publications(gff_record: gffutils.Feature) -> List[str]:
        """Extracts publications names from a GFF record"""
        publications = []
        if "literature" in gff_record.attributes:
            publications = gff_record.attributes["literature"]
            if isinstance(publications, str):
                publications = [publications]
        return publications

    @staticmethod
    def _extract_protein_source_id(gff_record: gffutils.Feature) -> Union[None, str]:
        """Extracts the ID of a polypeptide associated with the feature from a GFF record"""
        protein_id = None
        if "protein_source_id" in gff_record.attributes:
            protein_id = gff_record.attributes["protein_source_id"]
            if isinstance(protein_id, list):
                protein_id = protein_id[0]
        return protein_id

    @staticmethod
    def _extract_gff_sequence_names(gff_db: gffutils.FeatureDB) -> List[str]:
        """Extracts sequence names from a GFF file"""
        sequences = []
        for directive in gff_db.directives:
            if directive.startswith("sequence-region"):
                split_directive = directive.split()
                sequence_name = split_directive[1].strip()
                sequences.append(sequence_name)
        return sequences

    def _recognized_gff_attributes(self) -> List[str]:
        """Lists GFF attributes that are handled by this program"""
        return self._feature_property_types() + self._feature_relationship_types() + self._synonym_types() \
            + ["id", "name", "parent", "note", "dbxref", "ontology_term", "size", "literature", "translation",
               "protein_source_id"]


class GFFExportClient(iobase.ChadoClient, GFFClient):
    """Class for exporting genomic data from Chado to GFF files"""

    def __init__(self, uri: str, verbose=False, test_environment=False):
        """Constructor"""

        # Connect to database
        self.uri = uri
        self.verbose = verbose
        self.test_environment = test_environment
        if self.test_environment:
            self.printer = utils.VerbosePrinter(self.verbose)
        else:
            super().__init__(self.uri, self.verbose)

        # Load essential database entries
        if not self.test_environment:
            self._load_essentials()

    def __del__(self):
        """Destructor - disconnect from database"""
        if not self.test_environment:
            super().__del__()

    def _load_essentials(self) -> None:
        """Loads essential database entries"""
        self._part_of_term = self._load_cvterm_from_cv("part_of", "relationship")
        self._derives_from_term = self._load_cvterm_from_cv("derives_from", "sequence")
        self._parent_terms = {self._part_of_term.name: self._part_of_term,
                              self._derives_from_term.name: self._derives_from_term}
        self._parent_type_ids = [self._part_of_term.cvterm_id, self._derives_from_term.cvterm_id]
        self._top_level_term = self._load_cvterm("top_level_seq")
        self._go_db = self._load_db("GO")

    def export(self, gff_filename: str, organism_name: str, export_fasta: bool, fasta_filename: str,
               include_obsolete_features=False) -> None:
        """Exports sequences from Chado to a GFF file"""

        # Load dependencies
        organism_entry = self._load_organism(organism_name)

        # Open GFF file
        gff_handle = utils.open_file_write(gff_filename)

        # Get top-level sequences and write a GFF header
        chromosome_entries = self.query_features_by_property_type(
            organism_entry.organism_id, self._top_level_term.cvterm_id).all()           # type: List[sequence.Feature]
        self._write_gff_header(gff_handle, chromosome_entries)

        # Loop over all top-level sequences
        for chromosome_entry in chromosome_entries:

            # Load all attributes associated with this sequence
            self._export_gff_record(chromosome_entry, chromosome_entry.uniquename, {}, gff_handle)

            # Get features located on this sequence
            feature_entries = self.query_features_by_srcfeature(chromosome_entry.feature_id).all()
            for feature_entry in feature_entries:

                # Create a GFF record for this feature, if it fulfills certain requirements
                if not self._has_feature_parents(feature_entry) \
                        and (include_obsolete_features or not feature_entry.is_obsolete):
                    self._export_gff_record(feature_entry, chromosome_entry.uniquename, {}, gff_handle)

        # Close GFF file
        utils.close(gff_handle)

        # Print FASTA sequences, if required
        if export_fasta:
            self._export_fasta(gff_filename, fasta_filename, organism_name)

    def _export_fasta(self, gff_file: str, fasta_file: str, organism_name: str) -> None:
        """Exports sequences from the Chado database into a FASTA file"""
        fasta_is_temporary = (fasta_file == "" or fasta_file is None)
        if fasta_is_temporary:

            # Create temporary file
            (fasta_handle, fasta_file) = tempfile.mkstemp(dir=os.getcwd())
            os.close(fasta_handle)

        # Export FASTA sequences to file
        fasta_client = fasta.FastaExportClient(self.uri, self.verbose)
        fasta_client.export(fasta_file, organism_name, "contigs", "")
        if fasta_is_temporary:

            # Append sequences to GFF and remove temporary file
            self._append_fasta(gff_file, fasta_file)
            os.remove(fasta_file)

    @staticmethod
    def _append_fasta(gff_file: str, fasta_file: str) -> None:
        """Appends FASTA sequences to a GFF file"""
        with open(gff_file, 'a') as gff_handle:
            gff_handle.write("##FASTA\n")
            with open(fasta_file, 'r') as fasta_handle:
                for line in fasta_handle:
                    gff_handle.write(line)

    @staticmethod
    def _write_gff_header(file_handle, chromosome_entries: List[sequence.Feature]) -> None:
        """Prints the header of a GFF file"""
        file_handle.write("##gff-version 3\n")
        file_handle.write("# feature-ontology so.obo\n")
        for chromosome_entry in chromosome_entries:
            seq = "\t".join(["##sequence-region", chromosome_entry.uniquename, "1",
                            str(chromosome_entry.seqlen)]) + "\n"
            file_handle.write(seq)

    @staticmethod
    def _print_gff_record(gff_record: gffutils.Feature, file_handle) -> None:
        """Prints a GFF record to file"""
        file_handle.write(str(gff_record) + "\n")

    def _export_gff_record(self, feature_entry: sequence.Feature, chromosome_name: str,
                           parent_relationships: Dict[str, str], file_handle) -> None:
        """Exports a GFF record for a given feature"""

        # Create GFF record
        gff_record = self._create_gff_record(feature_entry, chromosome_name)

        # Query various tables to gather information related to the feature
        feature_type = self._extract_feature_type(feature_entry)
        feature_synonyms = self._extract_feature_synonyms(feature_entry)
        feature_properties = self._extract_feature_properties(feature_entry)
        feature_publications = self._extract_feature_publications(feature_entry)
        feature_dbxrefs = self._extract_feature_cross_references(feature_entry)
        feature_ontology_terms = self._extract_feature_ontology_terms(feature_entry)

        # Add attributes to the GFF record
        self._add_gff_relationships(gff_record, parent_relationships)
        self._add_gff_cross_references(gff_record, feature_dbxrefs)
        self._add_gff_ontology_terms(gff_record, feature_ontology_terms)
        self._add_gff_synonyms(gff_record, feature_synonyms)
        self._add_gff_publications(gff_record, feature_publications)
        self._add_gff_properties(gff_record, feature_properties)
        self._add_gff_featuretype(gff_record, feature_type, feature_entry.residues)

        # Write the generated GFF record to file
        self._print_gff_record(gff_record, file_handle)

        # Handle children of this feature (recursive call)
        self._handle_child_features(feature_entry, chromosome_name, file_handle)

    def _handle_child_features(self, feature_entry: sequence.Feature, chromosome_name: str, file_handle) -> None:
        """Export GFF records for all child features of a given feature"""
        for relationship_type, relationship_term in self._parent_terms.items():
            child_entries = self.query_child_features(feature_entry.feature_id, relationship_term.cvterm_id).all()
            parent_relationships = {relationship_type: feature_entry.uniquename}
            for child_entry in child_entries:
                if not child_entry.is_obsolete:
                    self._export_gff_record(child_entry, chromosome_name, parent_relationships, file_handle)

    def _has_feature_parents(self, feature_entry: sequence.Feature) -> bool:
        """Checks if a given Feature has parents in the database"""
        parent_entry = self.query_parent_features(feature_entry.feature_id, self._parent_type_ids).first()
        return parent_entry is not None

    def _extract_feature_type(self, feature_entry: sequence.Feature) -> str:
        """Extracts the type of a feature by a database query"""
        cvterm_entry = self.query_first(cv.CvTerm, cvterm_id=feature_entry.type_id)
        return cvterm_entry.name

    def _extract_feature_synonyms(self, feature_entry: sequence.Feature) -> Dict[str, List[str]]:
        """Extracts synonyms of a feature by a database query"""
        synonyms = {}
        for synonym_type, synonym_name in self.query_feature_synonyms(feature_entry.feature_id).all():
            if synonym_type in synonyms:
                synonyms[synonym_type].append(synonym_name)
            else:
                synonyms[synonym_type] = [synonym_name]
        return synonyms

    def _extract_feature_properties(self, feature_entry: sequence.Feature) -> Dict[str, List[str]]:
        """Extracts properties of a feature by a database query"""
        properties = {}
        for property_type, property_value in self.query_feature_properties(feature_entry.feature_id).all():
            if property_type in properties:
                properties[property_type].append(property_value)
            else:
                properties[property_type] = [property_value]
        return properties

    def _extract_feature_publications(self, feature_entry: sequence.Feature) -> List[str]:
        """Extracts publications associated with a feature by a database query"""
        publications = []
        for publication, in self.query_feature_pubs(feature_entry.feature_id).all():
            publications.append(publication)
        return publications

    def _extract_feature_cross_references(self, feature_entry: sequence.Feature) -> List[str]:
        """Extracts cross references associated with a feature by a database query"""
        cross_references = []
        for db_authority, accession in self.query_feature_dbxrefs(feature_entry.feature_id).all():
            crossref = ontology.create_dbxref(db_authority, accession)
            cross_references.append(crossref)
        return cross_references

    def _extract_feature_ontology_terms(self, feature_entry: sequence.Feature) -> List[str]:
        """Extracts ontology terms associated with a feature by a database query"""
        ontology_terms = []
        for db_authority, accession in self.query_feature_ontology_terms(
                feature_entry.feature_id, self._go_db.db_id).all():
            crossref = ontology.create_dbxref(db_authority, accession)
            ontology_terms.append(crossref)
        return ontology_terms

    def _create_gff_record(self, feature_entry: sequence.Feature, chromosome_name: str) -> gffutils.Feature:
        """Creates a GFF record with the fields 'seqid', 'start', 'end', 'strand' and 'phase'"""
        featureloc_entry = self.query_first(sequence.FeatureLoc, feature_id=feature_entry.feature_id)
        if featureloc_entry:
            gff_record = gffutils.Feature(seqid=chromosome_name, id=feature_entry.uniquename,
                                          start=featureloc_entry.fmin+1, end=featureloc_entry.fmax,
                                          strand=self.back_convert_strand(featureloc_entry.strand),
                                          frame=self.back_convert_frame(featureloc_entry.phase))
        else:
            gff_record = gffutils.Feature(seqid=chromosome_name, id=feature_entry.uniquename,
                                          start=1, end=feature_entry.seqlen)
        gff_record.attributes["ID"] = feature_entry.uniquename
        if feature_entry.name:
            gff_record.attributes["Name"] = feature_entry.name
        return gff_record

    @staticmethod
    def _add_gff_featuretype(gff_record: gffutils.Feature, featuretype: str, residues: str) -> None:
        """Adds the 'type' and potentially the attribute 'translation' to a GFF record"""
        gff_record.featuretype = featuretype
        if gff_record.featuretype == "polypeptide" and residues:
            gff_record.attributes["translation"] = residues.upper()

    @staticmethod
    def _add_gff_synonyms(gff_record: gffutils.Feature, synonyms: Dict[str, List[str]]):
        """Adds the attribute 'Alias' and various other attributes to a GFF record"""
        for synonym_type in ["Alias", "synonym", "previous_systematic_id"]:
            if synonym_type.lower() in synonyms:
                gff_record.attributes[synonym_type] = synonyms[synonym_type.lower()]

    @staticmethod
    def _add_gff_properties(gff_record: gffutils.Feature, properties: Dict[str, List[str]]) -> None:
        """Adds the 'source', 'score' and various attributes to a GFF record"""
        if "score" in properties:
            gff_record.score = properties["score"][0]
        if "source" in properties:
            gff_record.source = properties["source"][0]
        for property_type in ["comment", "description", "Note"]:
            if property_type.lower() in properties:
                gff_record.attributes[property_type] = properties[property_type.lower()]

    @staticmethod
    def _add_gff_publications(gff_record: gffutils.Feature, publications: List[str]):
        """Adds the attribute 'literature' to a GFF record"""
        if publications:
            gff_record.attributes["literature"] = publications

    @staticmethod
    def _add_gff_cross_references(gff_record: gffutils.Feature, cross_references: List[str]):
        """Adds the attribute 'Dbxref' to a GFF record"""
        if cross_references:
            gff_record.attributes["Dbxref"] = cross_references

    @staticmethod
    def _add_gff_ontology_terms(gff_record: gffutils.Feature, ontology_terms: List[str]):
        """Adds the attribute 'Ontology_term' to a GFF record"""
        if ontology_terms:
            gff_record.attributes["Ontology_term"] = ontology_terms

    @staticmethod
    def _add_gff_relationships(gff_record: gffutils.Feature, relationships: Dict[str, str]) -> None:
        """Adds the attributes 'Parent' and 'Derives_from' to a GFF record"""
        chado_to_gff_key = {"part_of": "Parent", "derives_from": "Derives_from"}
        for chado_relationship_type, gff_relationship_type in chado_to_gff_key.items():
            if chado_relationship_type in relationships:
                gff_record.attributes[gff_relationship_type] = relationships[chado_relationship_type]
