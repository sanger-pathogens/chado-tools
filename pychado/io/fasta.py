import os
import urllib.parse
from typing import Union, List
from Bio import SeqIO, Seq
from . import iobase
from .. import utils
from ..orm import cv, organism, sequence


class FastaImportClient(iobase.ChadoClient):
    """Class for importing genomic data from FASTA files into Chado"""

    def __init__(self, uri: str, verbose=False, test_environment=False):
        """Constructor"""

        # Connect to database
        self.test_environment = test_environment
        if not self.test_environment:
            super().__init__(uri, verbose)

        # Load essentials
        if not self.test_environment:
            self._load_essentials()

    def __del__(self):
        """Destructor - disconnect from database"""
        if not self.test_environment:
            super().__del__()

    def _load_essentials(self) -> None:
        """Loads essential database entries"""
        self._sequence_terms = self._load_terms_from_cv_dict(
            "sequence", ["contig", "supercontig", "chromosome", "region"])
        self._top_level_term = self._load_cvterm("top_level_seq")

    def load(self, filename: str, organism_name: str, sequence_type: str):
        """Import data from a FASTA file into a Chado database"""

        # Load dependencies
        default_organism = self._load_organism(organism_name)
        default_type = self._sequence_terms[sequence_type]

        # Check for file existence
        if not os.path.exists(filename):
            raise iobase.InputFileError("Input file '" + filename + "' does not exist.")

        # Loop over all entries in the FASTA file
        for record in SeqIO.parse(filename, "fasta"):

            # Insert or update entries in the 'feature' table
            feature_entry = self._handle_sequence(record, default_organism, default_type)
            self._mark_as_top_level_sequence(feature_entry)

        # Commit changes
        self.session.commit()

    def _handle_sequence(self, fasta_record: SeqIO.SeqRecord, organism_entry: organism.Organism,
                         default_type_entry: cv.CvTerm) -> sequence.Feature:
        """Inserts or updates an entry in the 'feature' table and returns it"""

        # Check if all dependencies are met. Use default if not.
        sequence_type = self._extract_type(fasta_record)
        if sequence_type:
            if sequence_type not in self._sequence_terms:
                self.printer.print("WARNING: Sequence type '" + sequence_type + "' not present in database")
                type_entry = default_type_entry
            else:
                type_entry = self._sequence_terms[sequence_type]
        else:
            type_entry = default_type_entry

        # Create a feature object, and update the corresponding table
        new_feature_entry = self._create_feature(fasta_record, organism_entry.organism_id, type_entry.cvterm_id)
        feature_entry = self._handle_feature(new_feature_entry, organism_entry.abbreviation)
        return feature_entry

    def _mark_as_top_level_sequence(self, feature_entry: sequence.Feature) -> sequence.FeatureProp:
        """Inserts or updates an entry in the 'featureprop' table and returns it"""
        existing_featureprops = self.query_all(sequence.FeatureProp, feature_id=feature_entry.feature_id)
        new_featureprop_entry = sequence.FeatureProp(feature_id=feature_entry.feature_id,
                                                     type_id=self._top_level_term.cvterm_id, value="true")
        featureprop_entry = self._handle_featureprop(new_featureprop_entry, existing_featureprops,
                                                     self._top_level_term.name, new_featureprop_entry.value,
                                                     feature_entry.uniquename)
        return featureprop_entry

    @staticmethod
    def _create_feature(fasta_record: SeqIO.SeqRecord, organism_id: int, type_id: int) -> sequence.Feature:
        """Creates a feature object from a FASTA record"""
        residues = str(fasta_record.seq)
        return sequence.Feature(organism_id=organism_id, type_id=type_id, uniquename=fasta_record.id,
                                residues=residues, seqlen=len(residues))

    @staticmethod
    def _extract_type(fasta_record: SeqIO.SeqRecord) -> Union[None, str]:
        """Extracts the feature type from a FASTA record"""
        attributes = fasta_record.description.split('|')
        key_value_attributes = dict(attribute.split("=", 1) for attribute in attributes if "=" in attribute)
        for key, value in key_value_attributes.items():
            if key.strip() in ["SO", "sequence_type"]:
                return value.strip()
        return None


class FastaExportClient(iobase.ChadoClient):
    """Class for exporting genomic data from Chado to FASTA files"""

    def __init__(self, uri: str, verbose=False, test_environment=False):
        """Constructor"""

        # Connect to database
        self.test_environment = test_environment
        if not self.test_environment:
            super().__init__(uri, verbose)

        # Load essentials
        if not self.test_environment:
            self._load_essentials()

    def __del__(self):
        """Destructor - disconnect from database"""
        if not self.test_environment:
            super().__del__()

    def _load_essentials(self) -> None:
        """Loads essential database entries"""
        self._sequence_terms = self._load_terms_from_cv_dict(
            "sequence", ["gene", "polypeptide"])
        self._part_of_term = self._load_cvterm_from_cv("part_of", "relationship")
        self._derives_from_term = self._load_cvterm_from_cv("derives_from", "sequence")
        self._top_level_term = self._load_cvterm("top_level_seq")

    def export(self, filename: str, organism_name: str, sequence_type: str, release: str,
               include_obsolete_features=False):
        """Exports sequences from Chado to a FASTA file"""

        # Load dependencies and features of interest
        organism_entry = self._load_organism(organism_name)
        genome_version = self._extract_genome_version(organism_entry)
        feature_entries = self._extract_features_by_type(organism_entry, sequence_type)
        srcfeature_entries = self._extract_srcfeatures_by_type(organism_entry, sequence_type)
        records = []

        # Loop over all features of interest
        for feature_entry in feature_entries:

            # Get feature type
            type_entry = self.query_first(cv.CvTerm, cvterm_id=feature_entry.type_id)

            # Create FASTA record
            residues = self._extract_residues_by_type(feature_entry, srcfeature_entries, sequence_type)
            if self._are_residues_valid(residues, sequence_type) and \
                    (include_obsolete_features or not feature_entry.is_obsolete):
                record = self._create_fasta_record(feature_entry, organism_entry, type_entry, residues,
                                                   genome_version, release)
                records.append(record)

        # Write all FASTA records to file
        records.sort(key=self._sort_record_key)
        SeqIO.write(records, filename, "fasta")

    @staticmethod
    def _sort_record_key(record: SeqIO.SeqRecord):
        """Helper function for sorting records"""
        return record.id

    def _create_fasta_record(self, feature_entry: sequence.Feature, organism_entry: organism.Organism,
                             type_entry: cv.CvTerm, residues: str, genome_version: str, release: str
                             ) -> Union[None, SeqIO.SeqRecord]:
        """Creates a FASTA record"""
        attributes = self._create_fasta_attributes(organism_entry, feature_entry, type_entry, genome_version, release)
        record = SeqIO.SeqRecord(Seq.Seq(residues), id=feature_entry.uniquename, name=feature_entry.uniquename,
                                 description=attributes)
        return record

    def _extract_srcfeatures_by_type(self, organism_entry: organism.Organism, sequence_type: str
                                     ) -> List[sequence.Feature]:
        """Extract features from the database"""
        srcfeature_entries = []
        if sequence_type == "genes":
            srcfeature_entries = self.query_features_by_property_type(organism_entry.organism_id,
                                                                      self._top_level_term.cvterm_id).all()
        return srcfeature_entries

    def _extract_features_by_type(self, organism_entry: organism.Organism, sequence_type: str
                                  ) -> List[sequence.Feature]:
        """Extract features from the database"""
        if sequence_type == "proteins":
            query = self.query_protein_features(organism_entry.organism_id, self._sequence_terms["gene"].cvterm_id,
                                                self._part_of_term.cvterm_id, self._derives_from_term.cvterm_id)
        elif sequence_type == "genes":
            query = self.query_features_by_type(
                organism_entry.organism_id, [self._sequence_terms["gene"].cvterm_id])
        else:
            query = self.query_features_by_property_type(organism_entry.organism_id, self._top_level_term.cvterm_id)
        return query.all()

    def _extract_residues_by_type(self, feature_entry: sequence.Feature, srcfeature_entries: List[sequence.Feature],
                                  sequence_type: str) -> Union[None, str]:
        """Extracts the sequence of nucleotides/amino acids of a feature"""
        if sequence_type == "genes":
            residues = self._extract_nucleotide_sequence(feature_entry, srcfeature_entries)
        else:
            residues = feature_entry.residues
        return residues

    @staticmethod
    def _are_residues_valid(residues: str, sequence_type: str) -> bool:
        """Checks if the sequences of nucleotides/amino acids are composed of valid IUPAC codes"""
        if not residues:
            return False
        if sequence_type == "proteins":
            if residues[0].upper() != "M":
                return False
            if residues[-1].upper() not in Seq.IUPAC.ExtendedIUPACProtein.letters and residues[-1].upper() != "*":
                return False
            for residue in residues[1:-1]:
                if residue.upper() not in Seq.IUPAC.ExtendedIUPACProtein.letters:
                    return False
        else:
            for residue in residues:
                if residue.upper() not in Seq.IUPAC.IUPACAmbiguousDNA.letters:
                    return False
        return True

    def _extract_nucleotide_sequence(self, feature_entry: sequence.Feature, srcfeature_entries: List[sequence.Feature]
                                     ) -> Union[None, str]:
        """Extracts the nucleotide sequence of a (gene) feature"""

        # Get the entry from the 'featureloc' table
        featureloc_entry = self.query_first(sequence.FeatureLoc,
                                            feature_id=feature_entry.feature_id)        # type: sequence.FeatureLoc
        if not featureloc_entry:
            return None

        # Get the entry from the 'feature' table
        matching_entries = utils.filter_objects(
            srcfeature_entries, feature_id=featureloc_entry.srcfeature_id)              # type: List[sequence.Feature]
        if not matching_entries:
            return None

        # Extract the nucleotide sequence
        matching_entry = matching_entries[0]
        if len(matching_entry.residues) >= featureloc_entry.fmax + 1:
            residues = matching_entry.residues[featureloc_entry.fmin:featureloc_entry.fmax].upper()
        else:
            residues = None

        # Compute the complementary sequence, if necessary
        if residues and featureloc_entry.strand < 0:
            sequence_object = Seq.Seq(residues, alphabet=Seq.IUPAC.ambiguous_dna)
            residues = str(sequence_object.reverse_complement())
        return residues

    def _extract_genome_version(self, organism_entry: organism.Organism) -> Union[None, str]:
        """Extracts the version of a genome from the database"""
        version_cvterm = self._load_cvterm("version")
        organismprop_entry = self.query_first(organism.OrganismProp, organism_id=organism_entry.organism_id,
                                              type_id=version_cvterm.cvterm_id)
        if organismprop_entry:
            return organismprop_entry.value
        else:
            return None

    def _create_fasta_attributes(self, organism_entry: organism.Organism, feature_entry: sequence.Feature,
                                 type_entry: cv.CvTerm, genome_version: str, release: str) -> str:
        """Creates a header line for a FASTA sequence with several attributes"""
        attributes_as_list = ["", self._organism_key_value_pair(organism_entry), self._type_key_value_pair(type_entry)]
        if feature_entry.name:
            attributes_as_list.append(self._feature_name_key_value_pair(feature_entry.name))
        if genome_version:
            attributes_as_list.append(self._genome_version_key_value_pair(genome_version))
        if release:
            attributes_as_list.append(self._release_key_value_pair(release))
        attributes_as_string = " | ".join(attributes_as_list).strip()
        return attributes_as_string

    @staticmethod
    def _organism_key_value_pair(organism_entry: organism.Organism):
        """Creates a key-value pair for the FASTA header with the organism name"""
        organism_key = "organism"
        organism_name_as_list = [organism_entry.genus, organism_entry.species]
        if organism_entry.infraspecific_name:
            organism_name_as_list.append(organism_entry.infraspecific_name)
        organism_name_as_string = urllib.parse.quote(" ".join(organism_name_as_list))
        organism_pair = "=".join([organism_key, organism_name_as_string])
        return organism_pair

    @staticmethod
    def _feature_name_key_value_pair(feature_name: str):
        """Creates a key-value pair for the FASTA header with the genome version"""
        feature_name_pair = "=".join(["sequence_name", urllib.parse.quote(feature_name)])
        return feature_name_pair

    @staticmethod
    def _genome_version_key_value_pair(genome_version: str):
        """Creates a key-value pair for the FASTA header with the genome version"""
        version_pair = "=".join(["genome_version", urllib.parse.quote(genome_version)])
        return version_pair

    @staticmethod
    def _type_key_value_pair(type_entry: cv.CvTerm):
        """Creates a key-value pair for the FASTA header with the type of the sequence"""
        type_key = "sequence_type"
        type_name = urllib.parse.quote(type_entry.name)
        type_pair = "=".join([type_key, type_name])
        return type_pair

    @staticmethod
    def _release_key_value_pair(release: str):
        """Creates a key-value pair for the FASTA header with the name of the release"""
        release_key = "release"
        release_name = urllib.parse.quote(release)
        release_pair = "=".join([release_key, release_name])
        return release_pair
