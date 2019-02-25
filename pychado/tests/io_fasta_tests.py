import unittest.mock
from Bio import SeqIO, Seq
from ..io import fasta
from ..orm import cv, organism, sequence


class TestFastaImport(unittest.TestCase):
    """Tests various functions used to load a FASTA file into a database"""

    @classmethod
    def setUpClass(cls):
        """Creates an instance of the base class to be tested and instantiates global attributes"""
        cls.client = fasta.FastaImportClient("testuri", test_environment=True)
        cls.client._sequence_terms = {
            "contig": cv.CvTerm(cv_id=4, dbxref_id=41, name="contig", cvterm_id=41),
            "supercontig": cv.CvTerm(cv_id=4, dbxref_id=42, name="supercontig", cvterm_id=42),
            "chromosome": cv.CvTerm(cv_id=4, dbxref_id=43, name="chromosome", cvterm_id=43),
            "region": cv.CvTerm(cv_id=4, dbxref_id=44, name="region", cvterm_id=44)
        }
        cls.client._top_level_term = cv.CvTerm(cv_id=11, dbxref_id=91, name="top_level_seq", cvterm_id=91)

    def setUp(self):
        # Create a default FASTA record
        self.default_fasta_record = SeqIO.SeqRecord(seq="ACTGAAC", id="testid", name="testname",
                                                    description="sequence_name | organism=testorganism | SO=chromosome")

    @unittest.mock.patch("pychado.io.fasta.FastaImportClient._handle_feature")
    @unittest.mock.patch("pychado.io.fasta.FastaImportClient._create_feature")
    @unittest.mock.patch("pychado.io.fasta.FastaImportClient._extract_type")
    def test_handle_sequence(self, mock_extract_type: unittest.mock.Mock, mock_create: unittest.mock.Mock,
                             mock_insert: unittest.mock.Mock):
        # Tests the function transferring data from a FASTA record to the 'feature' table
        self.assertIs(mock_extract_type, self.client._extract_type)
        self.assertIs(mock_create, self.client._create_feature)
        self.assertIs(mock_insert, self.client._handle_feature)

        organism_entry = organism.Organism(genus="", species="", abbreviation="testorganism", organism_id=33)
        type_entry = cv.CvTerm(name="contig", cv_id=1, dbxref_id=2, cvterm_id=77)

        mock_extract_type.return_value = None
        self.client._handle_sequence(self.default_fasta_record, organism_entry, type_entry)
        mock_extract_type.assert_called_with(self.default_fasta_record)
        mock_create.assert_called_with(self.default_fasta_record, 33, 77)
        mock_insert.assert_called()

        mock_extract_type.return_value = "chromosome"
        self.client._handle_sequence(self.default_fasta_record, organism_entry, type_entry)
        mock_extract_type.assert_called_with(self.default_fasta_record)
        mock_create.assert_called_with(self.default_fasta_record, 33, 43)
        mock_insert.assert_called()

    @unittest.mock.patch("pychado.io.fasta.FastaImportClient._handle_featureprop")
    @unittest.mock.patch("pychado.orm.sequence.FeatureProp")
    @unittest.mock.patch("pychado.io.fasta.FastaImportClient.query_all")
    def test_mark_as_top_level_sequence(self, mock_query: unittest.mock.Mock, mock_featureprop: unittest.mock.Mock,
                                        mock_insert: unittest.mock.Mock):
        # Tests the function transferring data from a FASTA record to the 'feature' table
        self.assertIs(mock_query, self.client.query_all)
        self.assertIs(mock_featureprop, sequence.FeatureProp)
        self.assertIs(mock_insert, self.client._handle_featureprop)
        feature_entry = sequence.Feature(organism_id=1, type_id=2, uniquename="", feature_id=33)

        self.client._mark_as_top_level_sequence(feature_entry)
        mock_query.assert_called_with(sequence.FeatureProp, feature_id=33)
        mock_featureprop.assert_called_with(feature_id=33, type_id=91, value="true")
        mock_insert.assert_called()

    def test_create_feature(self):
        # Tests the function creating an entry for the 'feature' table from a FASTA record
        feature_entry = self.client._create_feature(self.default_fasta_record, 1, 2)
        self.assertEqual(feature_entry.organism_id, 1)
        self.assertEqual(feature_entry.type_id, 2)
        self.assertEqual(feature_entry.uniquename, "testid")
        self.assertEqual(feature_entry.residues, "ACTGAAC")
        self.assertEqual(feature_entry.seqlen, 7)

    def test_extract_type(self):
        # Tests the function extracting the sequence type from a FASTA record
        sequence_type = self.client._extract_type(self.default_fasta_record)
        self.assertEqual(sequence_type, "chromosome")
        self.default_fasta_record.description = ""
        sequence_type = self.client._extract_type(self.default_fasta_record)
        self.assertIsNone(sequence_type)


class TestFastaExport(unittest.TestCase):
    """Tests various functions used to export a FASTA file from a database"""

    @classmethod
    def setUpClass(cls):
        """Creates an instance of the base class to be tested and instantiates global attributes"""
        cls.client = fasta.FastaExportClient("testuri", test_environment=True)
        cls.client._sequence_terms = {
            "gene": cv.CvTerm(cv_id=4, dbxref_id=41, name="gene", cvterm_id=41),
            "pseudogene": cv.CvTerm(cv_id=4, dbxref_id=42, name="pseudogene", cvterm_id=42),
            "polypeptide": cv.CvTerm(cv_id=4, dbxref_id=43, name="polypeptide", cvterm_id=43)
        }
        cls.client._part_of_term = cv.CvTerm(cv_id=11, dbxref_id=91, name="part_of", is_relationshiptype=1,
                                             cvterm_id=91)
        cls.client._derives_from_term = cv.CvTerm(cv_id=11, dbxref_id=92, name="derives_from",
                                                  is_relationshiptype=1, cvterm_id=92)
        cls.client._top_level_term = cv.CvTerm(cv_id=11, dbxref_id=91, name="top_level_seq", cvterm_id=91)

    @unittest.mock.patch("pychado.io.fasta.FastaExportClient._extract_nucleotide_sequence")
    def test_extract_residues_by_type(self, mock_extract_nucleotides: unittest.mock.Mock):
        # Tests the function that extracts the sequence of nucleotides/amino acids of a feature
        self.assertIs(mock_extract_nucleotides, self.client._extract_nucleotide_sequence)
        feature_entry = sequence.Feature(organism_id=1, type_id=2, uniquename="test", residues="CTGA", feature_id=33)

        mock_extract_nucleotides.return_value = "AAGG"
        residues = self.client._extract_residues_by_type(feature_entry, [], "genes")
        mock_extract_nucleotides.assert_called_with(feature_entry, [])
        self.assertEqual(residues, "AAGG")

        mock_extract_nucleotides.reset_mock()
        residues = self.client._extract_residues_by_type(feature_entry, [], "contigs")
        mock_extract_nucleotides.assert_not_called()
        self.assertEqual(residues, "CTGA")

    def test_are_residues_valid(self):
        # Tests the function that checks if a sequence of nucleotides/amino acids is composed of valid IUPAC codes
        valid = self.client._are_residues_valid("", "genes")
        self.assertFalse(valid)
        valid = self.client._are_residues_valid("agct", "genes")
        self.assertTrue(valid)
        valid = self.client._are_residues_valid("AGCTXX", "genes")
        self.assertFalse(valid)
        valid = self.client._are_residues_valid("MRAB*", "proteins")
        self.assertTrue(valid)
        valid = self.client._are_residues_valid("RMAB*", "proteins")
        self.assertFalse(valid)
        valid = self.client._are_residues_valid("MR*AB*", "proteins")
        self.assertFalse(valid)

    @unittest.mock.patch("pychado.io.fasta.FastaExportClient.query_first")
    def test_extract_nucleotide_sequences(self, mock_query: unittest.mock.Mock):
        # Tests the function that extracts the nucleotide sequence of a feature from the database
        self.assertIs(mock_query, self.client.query_first)
        feature_entry = sequence.Feature(organism_id=1, type_id=2, uniquename="test", residues="CTGA", feature_id=33)

        mock_query.return_value = sequence.FeatureLoc(feature_id=33, srcfeature_id=34, fmin=1, fmax=3, strand=1)
        residues = self.client._extract_nucleotide_sequence(feature_entry, [])
        mock_query.assert_called_with(sequence.FeatureLoc, feature_id=33)
        self.assertIsNone(residues)

        srcfeature_entries = [sequence.Feature(organism_id=1, type_id=2, uniquename="test", residues="ACTGGTAA",
                                               feature_id=34)]
        residues = self.client._extract_nucleotide_sequence(feature_entry, srcfeature_entries)
        self.assertEqual(residues, "CT")

        mock_query.return_value = sequence.FeatureLoc(feature_id=33, srcfeature_id=34, fmin=0, fmax=6, strand=-1)
        residues = self.client._extract_nucleotide_sequence(feature_entry, srcfeature_entries)
        self.assertEqual(residues, "ACCAGT")

        mock_query.return_value = sequence.FeatureLoc(feature_id=33, srcfeature_id=34, fmin=1, fmax=300)
        residues = self.client._extract_nucleotide_sequence(feature_entry, srcfeature_entries)
        self.assertIsNone(residues)

    @unittest.mock.patch("pychado.io.fasta.FastaExportClient.query_first")
    @unittest.mock.patch("pychado.io.fasta.FastaExportClient._load_cvterm")
    def test_extract_genome_version(self, mock_load: unittest.mock.Mock, mock_query: unittest.mock.Mock):
        # Tests the function that extracts the genome version from the database
        self.assertIs(mock_load, self.client._load_cvterm)
        self.assertIs(mock_query, self.client.query_first)
        organism_entry = organism.Organism(genus="testgenus", species="testspecies", organism_id=44)

        mock_query.return_value = None
        genome_version = self.client._extract_genome_version(organism_entry)
        self.assertIsNone(genome_version)

        mock_query.return_value = organism.OrganismProp(organismprop_id=1, organism_id=12, type_id=33, value="v8")
        genome_version = self.client._extract_genome_version(organism_entry)
        self.assertEqual(genome_version, "v8")

    @unittest.mock.patch("Bio.SeqIO.SeqRecord")
    @unittest.mock.patch("Bio.Seq.Seq")
    @unittest.mock.patch("pychado.io.fasta.FastaExportClient._create_fasta_attributes")
    def test_create_fasta_record(self, mock_attributes: unittest.mock.Mock, mock_sequence: unittest.mock.Mock,
                                 mock_record: unittest.mock.Mock):
        # Tests the function that creates a FASTA record
        self.assertIs(mock_attributes, self.client._create_fasta_attributes)
        self.assertIs(mock_sequence, Seq.Seq)
        self.assertIs(mock_record, SeqIO.SeqRecord)

        feature_entry = sequence.Feature(organism_id=1, type_id=2, uniquename="test", feature_id=33)
        organism_entry = organism.Organism(genus="testgenus", species="testspecies", organism_id=44)
        type_entry = cv.CvTerm(name="contig", cv_id=1, dbxref_id=2, cvterm_id=55)
        mock_attributes.return_value = "desc"
        mock_sequence.return_value = "seq"

        self.client._create_fasta_record(feature_entry, organism_entry, type_entry, "AGCT", "v3.6", "testrelease")
        mock_attributes.assert_called_with(organism_entry, feature_entry, type_entry, "v3.6", "testrelease")
        mock_sequence.assert_called_with("AGCT")
        mock_record.assert_called_with("seq", id="test", name="test", description="desc")

    @unittest.mock.patch("pychado.io.fasta.FastaExportClient.query_features_by_property_type")
    def test_extract_srcfeatures_by_type(self, mock_query: unittest.mock.Mock):
        # Tests that the feature table is only queried for certain feature types
        self.assertIs(mock_query, self.client.query_features_by_property_type)

        organism_entry = organism.Organism(genus="testgenus", species="testspecies", organism_id=44)
        self.client._extract_srcfeatures_by_type(organism_entry, "contigs")
        mock_query.assert_not_called()

        self.client._extract_srcfeatures_by_type(organism_entry, "genes")
        mock_query.assert_called_with(44, 91)

    @unittest.mock.patch("pychado.io.fasta.FastaExportClient.query_protein_features")
    @unittest.mock.patch("pychado.io.fasta.FastaExportClient.query_features_by_property_type")
    @unittest.mock.patch("pychado.io.fasta.FastaExportClient.query_features_by_type")
    def test_extract_features_by_type(self, mock_query_genes: unittest.mock.Mock,
                                      mock_query_contigs: unittest.mock.Mock, mock_query_proteins: unittest.mock.Mock):
        # Tests that the feature table is correctly queried depending on the type of features of interest
        self.assertIs(mock_query_genes, self.client.query_features_by_type)
        self.assertIs(mock_query_contigs, self.client.query_features_by_property_type)
        self.assertIs(mock_query_proteins, self.client.query_protein_features)

        organism_entry = organism.Organism(genus="testgenus", species="testspecies", organism_id=44)
        self.client._extract_features_by_type(organism_entry, "contigs")
        mock_query_genes.assert_not_called()
        mock_query_contigs.assert_called_with(44, 91)
        mock_query_proteins.assert_not_called()

        mock_query_genes.reset_mock()
        mock_query_contigs.reset_mock()
        mock_query_proteins.reset_mock()
        self.client._extract_features_by_type(organism_entry, "proteins")
        mock_query_genes.assert_not_called()
        mock_query_contigs.assert_not_called()
        mock_query_proteins.assert_called_with(44, 41, 91, 92)

        mock_query_genes.reset_mock()
        mock_query_contigs.reset_mock()
        mock_query_proteins.reset_mock()
        self.client._extract_features_by_type(organism_entry, "genes")
        mock_query_genes.assert_called_with(44, [41])
        mock_query_contigs.assert_not_called()
        mock_query_proteins.assert_not_called()

    @unittest.mock.patch("pychado.io.fasta.FastaExportClient._release_key_value_pair")
    @unittest.mock.patch("pychado.io.fasta.FastaExportClient._genome_version_key_value_pair")
    @unittest.mock.patch("pychado.io.fasta.FastaExportClient._feature_name_key_value_pair")
    @unittest.mock.patch("pychado.io.fasta.FastaExportClient._type_key_value_pair")
    @unittest.mock.patch("pychado.io.fasta.FastaExportClient._organism_key_value_pair")
    def test_create_fasta_attributes(self, mock_organism: unittest.mock.Mock, mock_type: unittest.mock.Mock,
                                     mock_name: unittest.mock.Mock, mock_version: unittest.mock.Mock,
                                     mock_release: unittest.mock.Mock):
        # Tests the correct creation of a header for a FASTA sequence
        self.assertIs(mock_organism, self.client._organism_key_value_pair)
        self.assertIs(mock_type, self.client._type_key_value_pair)
        self.assertIs(mock_name, self.client._feature_name_key_value_pair)
        self.assertIs(mock_version, self.client._genome_version_key_value_pair)
        self.assertIs(mock_release, self.client._release_key_value_pair)

        organism_entry = organism.Organism(genus="testgenus", species="testspecies", organism_id=33)
        feature_entry = sequence.Feature(organism_id=33, type_id=2, uniquename="test", feature_id=99)
        type_entry = cv.CvTerm(name="contig", cv_id=1, dbxref_id=2, cvterm_id=44)
        mock_organism.return_value = "orgname"
        mock_type.return_value = "typename"
        mock_name.return_value = "genename"
        mock_version.return_value = "versionnumber"
        mock_release.return_value = "relname"

        attributes = self.client._create_fasta_attributes(organism_entry, feature_entry, type_entry, "", "")
        mock_organism.assert_called_with(organism_entry)
        mock_type.assert_called_with(type_entry)
        mock_name.assert_not_called()
        mock_version.assert_not_called()
        mock_release.assert_not_called()
        self.assertEqual(attributes, "| orgname | typename")

        feature_entry.name = "ABCD"
        attributes = self.client._create_fasta_attributes(organism_entry, feature_entry, type_entry, "v3",
                                                          "testrelease")
        mock_name.assert_called_with("ABCD")
        mock_version.assert_called_with("v3")
        mock_release.assert_called_with("testrelease")
        self.assertEqual(attributes, "| orgname | typename | genename | versionnumber | relname")

    def test_organism_key_value_pair(self):
        # Tests the correct creation of a key-value pair for an organism name with proper escaping applied
        organism_entry = organism.Organism(genus="testgenus", species="testspecies", organism_id=33)
        pair = self.client._organism_key_value_pair(organism_entry)
        self.assertEqual(pair, "organism=testgenus%20testspecies")
        organism_entry.infraspecific_name = "teststrain"
        pair = self.client._organism_key_value_pair(organism_entry)
        self.assertEqual(pair, "organism=testgenus%20testspecies%20teststrain")

    def test_feature_name_key_value_pair(self):
        # Tests the correct creation of a key-value pair for a feature name with proper escaping applied
        pair = self.client._feature_name_key_value_pair("some name")
        self.assertEqual(pair, "sequence_name=some%20name")

    def test_genome_version_key_value_pair(self):
        # Tests the correct creation of a key-value pair for a genome version with proper escaping applied
        pair = self.client._genome_version_key_value_pair("3.5")
        self.assertEqual(pair, "genome_version=3.5")

    def test_type_key_value_pair(self):
        # Tests the correct creation of a key-value pair for a feature type with proper escaping applied
        type_entry = cv.CvTerm(name="contig", cv_id=1, dbxref_id=2, cvterm_id=44)
        pair = self.client._type_key_value_pair(type_entry)
        self.assertEqual(pair, "sequence_type=contig")
        type_entry.name = "con tig"
        pair = self.client._type_key_value_pair(type_entry)
        self.assertEqual(pair, "sequence_type=con%20tig")

    def test_release_key_value_pair(self):
        # Tests the correct creation of a key-value pair for a release name with proper escaping applied
        pair = self.client._release_key_value_pair("2019-01")
        self.assertEqual(pair, "release=2019-01")
        pair = self.client._release_key_value_pair("2019:01")
        self.assertEqual(pair, "release=2019%3A01")
