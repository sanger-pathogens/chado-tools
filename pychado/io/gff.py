import os
import tempfile
from typing import List, Dict, Union
import gffutils
from . import iobase, ontology, fasta
from .. import utils
from ..orm import general, cv, organism, pub, sequence


class GFFImportClient(iobase.ImportClient):
    """Class for importing genomic data from GFF files into Chado"""

    def __init__(self, uri: str, verbose=False):
        """Constructor"""

        # Connect to database
        self.uri = uri
        self.verbose = verbose
        super().__init__(self.uri, self.verbose)

        # Create array for temporary SQLite databases
        self._sqlite_databases = []

        # Load essentials
        self._synonym_terms = self._load_cvterms("genedb_synonym_type", ["synonym", "previous_systematic_id"])
        self._relationship_terms = self._load_cvterms("relationship", ["is_a", "part_of", "derives_from"], True)
        self._feature_property_terms = self._load_cvterms("feature_property", ["score", "source", "description",
                                                                               "comment"])
        self._sequence_terms = self._load_cvterms("sequence", ["gene", "intron", "exon", "CDS", "mRNA", "chromosome"])
        self._default_pub = self._load_pub("null")

    def __del__(self):
        """Destructor"""

        # Disconnect from database
        super().__del__()

        # Delete temporary SQLite database
        for database in self._sqlite_databases:
            if os.path.exists(database):
                os.remove(database)

    def load(self, filename: str, organism_name: str, fasta_filename: str):
        """Import data from a GFF3 file into a Chado database"""

        # Check for file existence
        if not os.path.exists(filename):
            raise iobase.InputFileError("Input file '" + filename + "' does not exist.")

        # Import FASTA sequences, if present
        self._import_fasta(filename, fasta_filename, organism_name)

        # Create temporary SQLite database
        gff_db = self._create_sqlite_db(filename)

        # Load dependencies
        default_organism = self._load_organism(organism_name)

        # Initiate global containers
        all_feature_entries = {}

        # Loop over all entries in the gff file
        for gff_feature in gff_db.all_features():

            # Insert or update entries in various tables
            feature_entry = self._handle_child_feature(gff_feature, default_organism)
            if feature_entry:
                self._handle_location(gff_feature, feature_entry)
                self._handle_synonyms(gff_feature, feature_entry)
                self._handle_properties(gff_feature, feature_entry)
                self._handle_cross_references(gff_feature, feature_entry)
                self._handle_ontology_terms(gff_feature, feature_entry)
                self._handle_publications(gff_feature, feature_entry)

                # Save feature entry in global array
                all_feature_entries[feature_entry.uniquename] = feature_entry

        # Second loop over all entries in the gff file
        for gff_feature in gff_db.all_features():

            # Insert or update entries in various tables
            self._handle_relationships(gff_feature, all_feature_entries)

        # Commit changes
        self.session.commit()

    def _import_fasta(self, gff_file: str, fasta_file: str, organism_name: str):
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
            fasta_client.load(fasta_file, organism_name, "region")

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

    def _handle_child_feature(self, gff_feature: gffutils.Feature, organism_entry: organism.Organism
                              ) -> Union[None, sequence.Feature]:
        """Inserts or updates an entry in the 'feature' table and returns it"""

        # Check if all dependencies are met
        if gff_feature.featuretype not in self._sequence_terms:
            self.printer.print("WARNING: Sequence type '" + gff_feature.featuretype + "' not present in database")
            return None
        type_entry = self._sequence_terms[gff_feature.featuretype]

        # Create a feature object, and update the corresponding table
        new_feature_entry = self._create_feature(gff_feature, organism_entry.organism_id, type_entry.cvterm_id)
        feature_entry = self._handle_feature(new_feature_entry, organism_entry.abbreviation)
        return feature_entry

    def _handle_location(self, gff_feature: gffutils.Feature, feature_entry: sequence.Feature
                         ) -> Union[None, sequence.FeatureLoc]:
        """Inserts or updates an entry in the 'featureloc' table and returns it"""

        # Get entry from 'srcfeature' table
        srcfeature_entry = self.query_first(sequence.Feature, organism_id=feature_entry.organism_id,
                                            uniquename=gff_feature.seqid)
        if not srcfeature_entry:
            self.printer.print("WARNING: Parent sequence '" + gff_feature.seqid + "' not present in database")
            return None

        # Insert/update entry in the 'featureloc' table
        new_featureloc_entry = self._create_featureloc(gff_feature, feature_entry.feature_id,
                                                       srcfeature_entry.feature_id)
        featureloc_entry = self._handle_featureloc(new_featureloc_entry, feature_entry.uniquename)
        return featureloc_entry

    def _handle_synonyms(self, gff_feature: gffutils.Feature,
                         feature_entry: sequence.Feature) -> List[sequence.FeatureSynonym]:
        """Inserts or updates entries in the 'synonym' and 'feature_synonym' tables and returns the latter"""

        # Extract existing synonyms for this feature from the database
        existing_feature_synonyms = self.query_all(sequence.FeatureSynonym, feature_id=feature_entry.feature_id)
        all_feature_synonyms = []

        # Loop over all synonyms for this feature in the GFF file
        synonyms = self._extract_synonyms(gff_feature)
        for synonym_type, aliases in synonyms.items():

            # Get database entry for synonym type
            if synonym_type not in self._synonym_terms:
                self.printer.print("WARNING: Synonym type '" + synonym_type + "' not present in database.")
                continue
            type_entry = self._synonym_terms[synonym_type]

            for alias in aliases:

                # Insert/update entry in the 'synonym' table
                new_synonym_entry = sequence.Synonym(name=alias, type_id=type_entry.cvterm_id, synonym_sgml=alias)
                synonym_entry = self._handle_synonym(new_synonym_entry)

                # Insert/update entry in the 'feature_synonym' table
                new_feature_synonym_entry = sequence.FeatureSynonym(
                    synonym_id=synonym_entry.synonym_id, feature_id=feature_entry.feature_id,
                    pub_id=self._default_pub.pub_id, is_current=(synonym_type != "previous_systematic_id"))
                feature_synonym_entry = self._handle_feature_synonym(new_feature_synonym_entry,
                                                                     existing_feature_synonyms)
                all_feature_synonyms.append(feature_synonym_entry)

        return all_feature_synonyms

    def _handle_publications(self, gff_feature: gffutils.Feature, feature_entry: sequence.Feature
                             ) -> List[sequence.FeaturePub]:
        """Inserts or updates entries in the 'pub' and 'feature_pub' tables and returns the latter"""

        # Extract existing publications for this feature from the database
        existing_feature_pubs = self.query_all(sequence.FeaturePub, feature_id=feature_entry.feature_id)
        all_feature_pubs = []

        # Loop over all publications for this feature in the GFF file
        publications = self._extract_publications(gff_feature)
        for publication in publications:

            # Insert/update entry in the 'pub' table
            new_pub_entry = pub.Pub(uniquename=publication, type_id=self._default_pub.type_id)
            pub_entry = self._handle_pub(new_pub_entry)

            # Insert/update entry in the 'feature_pub' table
            new_feature_pub_entry = sequence.FeaturePub(feature_id=feature_entry.feature_id, pub_id=pub_entry.pub_id)
            feature_pub_entry = self._handle_feature_pub(new_feature_pub_entry, existing_feature_pubs,
                                                         feature_entry.uniquename, pub_entry.uniquename)
            all_feature_pubs.append(feature_pub_entry)

        return all_feature_pubs

    def _handle_relationships(self, gff_feature: gffutils.Feature, all_features: Dict[str, sequence.Feature]
                              ) -> List[sequence.FeatureRelationship]:
        """Inserts or updates entries in the 'feature_relationship' table and returns them"""

        # Get database entry for relationship subject from array
        if gff_feature.id not in all_features:
            self.printer.print("WARNING: Feature '" + gff_feature.id + "' not present in input file.")
            return []
        subject_entry = all_features[gff_feature.id]

        # Extract existing relationships for this subject from the database
        existing_feature_relationships = self.query_all(sequence.FeatureRelationship,
                                                        subject_id=subject_entry.feature_id)
        all_feature_relationships = []

        # Loop over all relationships for this feature in the GFF file
        relationships = self._extract_relationships(gff_feature)
        for relationship, parents in relationships.items():

            # Get database entry for relationship type
            if relationship not in self._relationship_terms:
                self.printer.print("WARNING: Relationship '" + relationship + "' not present in database.")
                continue
            type_entry = self._relationship_terms[relationship]

            for parent in parents:

                # Get database entry for object
                if parent not in all_features:
                    self.printer.print("WARNING: Feature '" + parent + "' not present in input file.")
                    continue
                object_entry = all_features[parent]

                # Insert/update entry in the 'feature_relationship' table
                new_relationship_entry = sequence.FeatureRelationship(subject_id=subject_entry.feature_id,
                                                                      object_id=object_entry.feature_id,
                                                                      type_id=type_entry.cvterm_id)
                feature_relationship_entry = self._handle_feature_relationship(
                    new_relationship_entry, existing_feature_relationships, subject_entry.uniquename,
                    object_entry.uniquename, type_entry.name)
                all_feature_relationships.append(feature_relationship_entry)

        return all_feature_relationships

    def _handle_properties(self, gff_feature: gffutils.Feature, feature_entry: sequence.Feature
                           ) -> List[sequence.FeatureProp]:
        """Inserts or updates entries in the 'featureprop' table and returns them"""

        # Extract existing properties for this feature from the database
        existing_featureprops = self.query_all(sequence.FeatureProp, feature_id=feature_entry.feature_id)
        all_featureprops = []

        # Loop over all properties of this feature in the GFF file
        props = self._extract_properties(gff_feature)
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
                all_featureprops.append(featureprop_entry)

        return all_featureprops

    def _handle_cross_references(self, gff_feature: gffutils.Feature, feature_entry: sequence.Feature
                                 ) -> List[sequence.FeatureDbxRef]:
        """Inserts or updates entries in the 'feature_dbxref' table and returns them"""

        # Extract existing cross references for this feature from the database
        existing_feature_dbxrefs = self.query_all(sequence.FeatureDbxRef, feature_id=feature_entry.feature_id)
        all_feature_dbxrefs = []

        # Loop over all cross references of this feature in the GFF file
        crossrefs = self._extract_crossrefs(gff_feature)
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
            all_feature_dbxrefs.append(feature_dbxref_entry)

        return all_feature_dbxrefs

    def _handle_ontology_terms(self, gff_feature: gffutils.Feature, feature_entry: sequence.Feature
                               ) -> List[sequence.FeatureCvTerm]:
        """Inserts or updates entries in the 'feature_cvterm' table and returns them"""

        # Extract existing ontology terms for this feature from the database
        existing_feature_cvterms = self.query_all(sequence.FeatureCvTerm, feature_id=feature_entry.feature_id)
        all_feature_cvterms = []

        ontology_terms = self._extract_ontology_terms(gff_feature)
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
            all_feature_cvterms.append(feature_cvterm_entry)

        return all_feature_cvterms

    def _create_feature(self, gff_feature: gffutils.Feature, organism_id: int, type_id: int) -> sequence.Feature:
        """Creates a feature object from a GFF file entry"""
        name = self._extract_name(gff_feature)
        residues = self._extract_residues(gff_feature)
        seqlen = None
        if residues is not None:
            seqlen = len(residues)
        return sequence.Feature(organism_id=organism_id, type_id=type_id, uniquename=gff_feature.id, name=name,
                                residues=residues, seqlen=seqlen)

    @staticmethod
    def _create_featureloc(gff_feature: gffutils.Feature, feature_id: int, srcfeature_id: int) -> sequence.FeatureLoc:
        """Creates a featureloc object from a GFF file entry
        coordinates are converted from base-oriented (1-based) to interbase (0-based)"""
        return sequence.FeatureLoc(
            feature_id=feature_id, srcfeature_id=srcfeature_id, fmin=gff_feature.start - 1, fmax=gff_feature.end,
            strand=convert_strand(gff_feature.strand), phase=convert_frame(gff_feature.frame))

    @staticmethod
    def _extract_crossrefs(gff_feature: gffutils.Feature) -> List[str]:
        """Extract database cross references from a GFF file entry"""
        crossrefs = []
        for key, value in gff_feature.attributes.items():
            if key.lower() == "dbxref":
                if isinstance(value, str):
                    crossrefs.append(value)
                elif isinstance(value, list):
                    crossrefs.extend(value)
        return crossrefs

    @staticmethod
    def _extract_ontology_terms(gff_feature: gffutils.Feature) -> List[str]:
        """Extract cross references to ontology terms from a GFF file entry"""
        ontology_terms = []
        if "Ontology_term" in gff_feature.attributes:
            ontology_terms = gff_feature.attributes["Ontology_term"]
            if isinstance(ontology_terms, str):
                ontology_terms = [ontology_terms]
        return ontology_terms

    @staticmethod
    def _extract_properties(gff_feature: gffutils.Feature) -> Dict[str, List[str]]:
        """Extracts properties from a GFF file entry
        Properties are the 'score' and the 'source' as well as the attributes 'Note', 'description', 'comment'"""
        gff_to_chado_key = {"Note": "comment", "comment": "comment", "description": "description"}
        properties = {}
        if gff_feature.score and gff_feature.score != '.':
            properties["score"] = [gff_feature.score]
        if gff_feature.source and gff_feature.source != '.':
            properties["source"] = [gff_feature.source]
        for gff_key, value in gff_feature.attributes.items():
            if gff_key in gff_to_chado_key.keys():
                chado_key = gff_to_chado_key[gff_key]
                if isinstance(value, str):
                    properties[chado_key] = [value]
                elif isinstance(value, list):
                    properties[chado_key] = value
        return properties

    @staticmethod
    def _extract_relationships(gff_feature: gffutils.Feature) -> Dict[str, List[str]]:
        """Extracts the relationships to other features from a GFF file entry"""
        gff_to_chado_key = {"Parent": "part_of", "Derives_from": "derives_from"}
        relationships = {}
        for gff_key, value in gff_feature.attributes.items():
            if gff_key in gff_to_chado_key.keys():
                chado_key = gff_to_chado_key[gff_key]
                if isinstance(value, str):
                    relationships[chado_key] = [value]
                elif isinstance(value, list):
                    relationships[chado_key] = value
        return relationships

    @staticmethod
    def _extract_synonyms(gff_feature: gffutils.Feature) -> Dict[str, List[str]]:
        """Extracts synonyms/alias names from a GFF file entry"""
        aliases = {}
        for key, value in gff_feature.attributes.items():
            if key.lower() in ["alias", "synonym", "previous_systematic_id"]:
                if isinstance(value, str):
                    aliases[key.lower()] = [value]
                elif isinstance(value, list):
                    aliases[key.lower()] = value
        return aliases

    @staticmethod
    def _extract_name(gff_feature: gffutils.Feature) -> Union[None, str]:
        """Extracts the feature name from a GFF file entry"""
        name = None
        if "Name" in gff_feature.attributes:
            name = gff_feature.attributes["Name"]
            if isinstance(name, list):
                name = name[0]
        return name

    @staticmethod
    def _extract_residues(gff_feature: gffutils.Feature) -> Union[None, str]:
        """Extracts the sequence of amino acids from a GFF file entry representing a polypeptide"""
        residues = None
        if "translation" in gff_feature.attributes:
            residues = gff_feature.attributes["translation"]
            if isinstance(residues, str):
                residues = residues.upper()
            elif isinstance(residues, list):
                residues = residues[0].upper()
        return residues

    @staticmethod
    def _extract_publications(gff_feature: gffutils.Feature) -> List[str]:
        """Extracts publications names from a GFF file entry"""
        publications = []
        if "literature" in gff_feature.attributes:
            publications = gff_feature.attributes["literature"]
            if isinstance(publications, str):
                publications = [publications]
        return publications


def convert_strand(strand: str) -> Union[None, int]:
    """Converts the strand from string notation to integer notation"""
    if strand == '+':
        return 1
    elif strand == '-':
        return -1
    else:
        return None


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