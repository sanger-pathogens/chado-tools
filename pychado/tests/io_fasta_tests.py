import unittest.mock
from Bio import SeqIO
from .. import dbutils, utils
from ..io import essentials, fasta
from ..orm import base, cv, organism, sequence


class TestFasta(unittest.TestCase):
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
