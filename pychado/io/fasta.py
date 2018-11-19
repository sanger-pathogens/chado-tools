import os
from typing import Union
from Bio import SeqIO
from . import iobase
from ..orm import cv, organism, sequence


class FastaImportClient(iobase.ImportClient):
    """Class for importing genomic data from FASTA files into Chado"""

    def __init__(self, uri: str, verbose=False):
        """Constructor"""

        # Connect to database
        super().__init__(uri, verbose)

        # Load essentials
        self._sequence_terms = self._load_cvterms("sequence", ["contig", "supercontig", "chromosome", "region"])
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
                                name=fasta_record.name, residues=residues, seqlen=len(residues))

    @staticmethod
    def _extract_type(fasta_record: SeqIO.SeqRecord) -> Union[None, str]:
        """Extracts the feature type from a FASTA record"""
        attributes = fasta_record.description.split('|')
        key_value_attributes = dict(attribute.split("=", 1) for attribute in attributes if "=" in attribute)
        for key, value in key_value_attributes.items():
            if key.strip() == "SO":
                return value.strip()
        return None
