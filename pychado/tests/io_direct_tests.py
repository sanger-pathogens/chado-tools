import unittest.mock
from .. import dbutils, utils
from ..io import direct
from ..orm import base, organism, cv


class TestDirectIO(unittest.TestCase):
    """Tests various functions used to insert, update or delete entries in database tables"""

    connection_parameters = utils.parse_yaml(dbutils.default_configuration_file())
    connection_uri = dbutils.random_database_uri(connection_parameters)

    @classmethod
    def setUpClass(cls):
        # Creates a database, establishes a connection and creates tables
        dbutils.create_database(cls.connection_uri)
        cls.client = direct.DirectIOClient(cls.connection_uri)
        schema_base = base.PublicBase
        schema_metadata = schema_base.metadata
        schema_base.metadata.create_all(cls.client.engine, tables=schema_metadata.sorted_tables)

    @classmethod
    def tearDownClass(cls):
        # Drops the database
        dbutils.drop_database(cls.connection_uri, True)

    def tearDown(self):
        # Rolls back all changes to the database
        self.client.session.rollback()

    def test_insert_delete_organism(self):
        # Tests the insertion of an organism into a Chado database and its deletion

        # Check the table is initially empty
        zero_result = self.client.query_table(organism.Organism).first()
        self.assertIsNone(zero_result)

        # Insert an organism and check that the insertion is successful
        self.client.insert_organism('AAA', 'BBB', 'CCC', 'DDD', 'EEE', 'FFF')
        first_result = self.client.query_table(organism.Organism).all()
        self.assertEqual(len(first_result), 1)
        self.assertEqual(first_result[0].genus, 'AAA')

        # Try to insert an organism with the same properties and check that nothing happened
        self.client.insert_organism('AAA', 'BBB', 'CCC', 'DDD', 'EEE', 'FFF')
        second_result = self.client.query_table(organism.Organism).all()
        self.assertEqual(first_result, second_result)

        # Try to delete an organism that doesn't exist and check that nothing happened
        self.client.delete_organism('XXX')
        third_result = self.client.query_table(organism.Organism).all()
        self.assertEqual(first_result, third_result)

        # Delete the previously inserted organism and check that it is gone
        self.client.delete_organism('CCC')
        fifth_result = self.client.query_table(organism.Organism).first()
        self.assertIsNone(fifth_result)

    @unittest.mock.patch("pychado.io.direct.DirectIOClient.query_organisms_by_property_type")
    @unittest.mock.patch("pychado.io.direct.DirectIOClient.query_all_organisms")
    @unittest.mock.patch("pychado.io.direct.DirectIOClient._load_cvterm")
    def test_select_organisms(self, mock_load_cvterm: unittest.mock.Mock, mock_query_all: unittest.mock.Mock,
                              mock_query_public: unittest.mock.Mock):
        # Tests the selection of organisms from a Chado database
        self.assertIs(mock_load_cvterm, self.client._load_cvterm)
        self.assertIs(mock_query_all, self.client.query_all_organisms)
        self.assertIs(mock_query_public, self.client.query_organisms_by_property_type)
        mock_load_cvterm.return_value = cv.CvTerm(cv_id=1, dbxref_id=2, cvterm_id=3, name="")

        self.client.select_organisms(False, False)
        mock_load_cvterm.assert_not_called()
        mock_query_public.assert_not_called()
        mock_query_all.assert_called()

        mock_load_cvterm.reset_mock()
        mock_query_public.reset_mock()
        mock_query_all.reset_mock()
        self.client.select_organisms(True, False)
        mock_load_cvterm.assert_called_with("genedb_public")
        mock_query_public.assert_called_with(3, False)
        mock_query_all.assert_not_called()
