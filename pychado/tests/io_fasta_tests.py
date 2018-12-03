import unittest.mock
from Bio import SeqIO, Seq
from .. import dbutils, utils
from ..io import essentials, fasta
from ..orm import base, cv, organism, sequence


class TestFastaImport(unittest.TestCase):
    """Tests various functions used to load a FASTA file into a database"""

    connection_parameters = utils.parse_yaml(dbutils.default_configuration_file())
    connection_uri = dbutils.random_database_uri(connection_parameters)

    @classmethod
    def setUpClass(cls):
        # Creates a database and establishes a connection
        dbutils.create_database(cls.connection_uri)
        schema_base = base.PublicBase
        schema_metadata = schema_base.metadata
        essentials_client = essentials.EssentialsClient(cls.connection_uri)
        schema_metadata.create_all(essentials_client.engine, tables=schema_metadata.sorted_tables)
        essentials_client.load()
        essentials_client._load_sequence_type_entries()
        cls.client = fasta.FastaImportClient(cls.connection_uri)

    @classmethod
    def tearDownClass(cls):
        # Drops the database
        dbutils.drop_database(cls.connection_uri, True)

    def setUp(self):
        # Create a default FASTA record
        self.default_fasta_record = SeqIO.SeqRecord(seq="ACTGAAC", id="testid", name="testname",
                                                    description="sequence_name | organism=testorganism | SO=chromosome")

    def tearDown(self):
        # Rolls back all changes to the database
        self.client.session.rollback()

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
        type_entry = cv.CvTerm(name="contig", cv_id=1, dbxref_id=2, cvterm_id=44)

        mock_extract_type.return_value = None
        self.client._handle_sequence(self.default_fasta_record, organism_entry, type_entry)
        mock_extract_type.assert_called_with(self.default_fasta_record)
        mock_create.assert_called_with(self.default_fasta_record, 33, 44)
        mock_insert.assert_called()

        mock_extract_type.return_value = "chromosome"
        self.client._handle_sequence(self.default_fasta_record, organism_entry, type_entry)
        mock_extract_type.assert_called_with(self.default_fasta_record)
        mock_create.assert_called_with(self.default_fasta_record, 33,
                                       self.client._sequence_terms["chromosome"].cvterm_id)
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
        mock_featureprop.assert_called_with(feature_id=33, type_id=self.client._top_level_term.cvterm_id, value="true")
        mock_insert.assert_called()

    def test_create_feature(self):
        # Tests the function creating an entry for the 'feature' table from a FASTA record
        feature_entry = self.client._create_feature(self.default_fasta_record, 1, 2)
        self.assertEqual(feature_entry.organism_id, 1)
        self.assertEqual(feature_entry.type_id, 2)
        self.assertEqual(feature_entry.uniquename, "testid")
        self.assertEqual(feature_entry.name, "testname")
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

    connection_parameters = utils.parse_yaml(dbutils.default_configuration_file())
    connection_uri = dbutils.random_database_uri(connection_parameters)

    @classmethod
    def setUpClass(cls):
        # Creates a database and establishes a connection
        dbutils.create_database(cls.connection_uri)
        cls.client = fasta.FastaExportClient(cls.connection_uri)

    @classmethod
    def tearDownClass(cls):
        # Drops the database
        dbutils.drop_database(cls.connection_uri, True)

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

    @unittest.mock.patch("pychado.io.fasta.FastaExportClient.query_first")
    def test_extract_nucleotide_sequences(self, mock_query: unittest.mock.Mock):
        # Tests the function that extracts the nucleotide sequence of a feature from the database
        self.assertIs(mock_query, self.client.query_first)
        feature_entry = sequence.Feature(organism_id=1, type_id=2, uniquename="test", residues="CTGA", feature_id=33)

        mock_query.return_value = sequence.FeatureLoc(feature_id=33, srcfeature_id=34, fmin=1, fmax=3)
        residues = self.client._extract_nucleotide_sequence(feature_entry, [])
        mock_query.assert_called_with(sequence.FeatureLoc, feature_id=33)
        self.assertIsNone(residues)

        srcfeature_entries = [sequence.Feature(organism_id=1, type_id=2, uniquename="test", residues="ACTGGTAA",
                                               feature_id=34)]
        residues = self.client._extract_nucleotide_sequence(feature_entry, srcfeature_entries)
        self.assertEqual(residues, "CT")

        mock_query.return_value = sequence.FeatureLoc(feature_id=33, srcfeature_id=34, fmin=1, fmax=300)
        residues = self.client._extract_nucleotide_sequence(feature_entry, srcfeature_entries)
        self.assertIsNone(residues)

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

        self.client._create_fasta_record(feature_entry, organism_entry, type_entry, "AGCT", "testrelease")
        mock_attributes.assert_called_with(organism_entry, type_entry, "testrelease")
        mock_sequence.assert_called_with("AGCT")
        mock_record.assert_called_with("seq", id="test", name="test", description="desc")

    @unittest.mock.patch("pychado.io.fasta.FastaExportClient.query_srcfeatures")
    def test_extract_srcfeatures_by_type(self, mock_query: unittest.mock.Mock):
        # Tests that the feature table is only queried for certain feature types
        self.assertIs(mock_query, self.client.query_srcfeatures)
        self.client._extract_srcfeatures_by_type("testorganism", "contigs")
        mock_query.assert_not_called()
        self.client._extract_srcfeatures_by_type("testorganism", "genes")
        mock_query.assert_called_with("testorganism")

    @unittest.mock.patch("pychado.io.fasta.FastaExportClient.query_top_level_features")
    @unittest.mock.patch("pychado.io.fasta.FastaExportClient.query_features_by_organism_and_type")
    def test_extract_features_by_type(self, mock_query_by_type: unittest.mock.Mock,
                                      mock_query_contigs: unittest.mock.Mock):
        # Tests that the feature table is correctly queried depending on the type of features of interest
        self.assertIs(mock_query_by_type, self.client.query_features_by_organism_and_type)
        self.assertIs(mock_query_contigs, self.client.query_top_level_features)

        self.client._extract_features_by_type("testorganism", "contigs")
        mock_query_by_type.assert_not_called()
        mock_query_contigs.assert_called_with("testorganism")

        mock_query_by_type.reset_mock()
        mock_query_contigs.reset_mock()
        self.client._extract_features_by_type("testorganism", "proteins")
        mock_query_by_type.assert_called_with("testorganism", ["polypeptide"])
        mock_query_contigs.assert_not_called()

        mock_query_by_type.reset_mock()
        mock_query_contigs.reset_mock()
        self.client._extract_features_by_type("testorganism", "genes")
        mock_query_by_type.assert_called_with("testorganism", ["gene", "pseudogene"])
        mock_query_contigs.assert_not_called()

    @unittest.mock.patch("pychado.io.fasta.FastaExportClient._release_key_value_pair")
    @unittest.mock.patch("pychado.io.fasta.FastaExportClient._type_key_value_pair")
    @unittest.mock.patch("pychado.io.fasta.FastaExportClient._organism_key_value_pair")
    def test_create_fasta_attributes(self, mock_organism: unittest.mock.Mock, mock_type: unittest.mock.Mock,
                                     mock_release: unittest.mock.Mock):
        # Tests the correct creation of a header for a FASTA sequence
        self.assertIs(mock_organism, self.client._organism_key_value_pair)
        self.assertIs(mock_type, self.client._type_key_value_pair)
        self.assertIs(mock_release, self.client._release_key_value_pair)

        organism_entry = organism.Organism(genus="testgenus", species="testspecies", organism_id=33)
        type_entry = cv.CvTerm(name="contig", cv_id=1, dbxref_id=2, cvterm_id=44)
        mock_organism.return_value = "orgname"
        mock_type.return_value = "typename"
        mock_release.return_value = "relname"

        attributes = self.client._create_fasta_attributes(organism_entry, type_entry, "")
        mock_organism.assert_called_with(organism_entry)
        mock_type.assert_called_with(type_entry)
        mock_release.assert_not_called()
        self.assertEqual(attributes, "| orgname | typename")

        attributes = self.client._create_fasta_attributes(organism_entry, type_entry, "testrelease")
        mock_release.assert_called_with("testrelease")
        self.assertEqual(attributes, "| orgname | typename | relname")

    def test_organism_key_value_pair(self):
        # Tests the correct creation of a key-value pair for an organism name with proper escaping applied
        organism_entry = organism.Organism(genus="testgenus", species="testspecies", organism_id=33)
        pair = self.client._organism_key_value_pair(organism_entry)
        self.assertEqual(pair, "organism=testgenus%20testspecies")
        organism_entry.infraspecific_name = "teststrain"
        pair = self.client._organism_key_value_pair(organism_entry)
        self.assertEqual(pair, "organism=testgenus%20testspecies%20teststrain")

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
