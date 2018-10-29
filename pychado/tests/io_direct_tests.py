import unittest
from .. import dbutils, utils
from ..io import direct
from ..orm import base, organism


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
