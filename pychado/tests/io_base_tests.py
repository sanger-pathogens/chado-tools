import unittest
import sqlalchemy.ext.declarative
from .. import dbutils, utils
from ..io import iobase

test_base = sqlalchemy.ext.declarative.declarative_base()


class Species(test_base):
    """ORM of a test table"""
    __tablename__ = "species"
    id = sqlalchemy.Column(sqlalchemy.BIGINT, nullable=False, primary_key=True, autoincrement=True)
    name = sqlalchemy.Column(sqlalchemy.VARCHAR(20), nullable=False)
    clade = sqlalchemy.Column(sqlalchemy.VARCHAR(20), nullable=True)
    legs = sqlalchemy.Column(sqlalchemy.INTEGER, nullable=False, server_default="0")
    extinct = sqlalchemy.Column(sqlalchemy.BOOLEAN, nullable=False, server_default="False")

    def __init__(self, name, clade=None, legs=0, extinct=False):
        for key, value in locals().items():
            if key != self:
                setattr(self, key, value)


class TestBasicIO(unittest.TestCase):
    """Tests basic functions for accessing databases via SQL"""

    connection_parameters = utils.parse_yaml(dbutils.default_configuration_file())
    connection_uri = dbutils.random_database_uri(connection_parameters)

    @classmethod
    def setUpClass(cls):
        # Creates a database, establishes a connection and creates tables
        dbutils.create_database(cls.connection_uri)
        cls.client = iobase.IOClient(cls.connection_uri)
        schema_base = test_base
        schema_base.metadata.create_all(cls.client.engine)
        # self.client = io.IOClient("sqlite:///:memory:")
        # self.client.engine.execute("ATTACH DATABASE ':memory:' AS " + self.client.schema)
        # self.client.session.execute("PRAGMA foreign_keys=ON")

    @classmethod
    def tearDownClass(cls):
        # Drops the database
        dbutils.drop_database(cls.connection_uri, True)

    def tearDown(self):
        # Rolls back all changes to the database
        self.client.session.rollback()

    def test_io(self):
        # Test the basic functionality for inserting data into database tables and retrieving data from them

        # Check the table is initially empty
        empty_table = self.client.query_table(Species).first()
        self.assertIsNone(empty_table)

        # Add an entry using 'add_and_flush', and assert that it automatically obtains an ID
        human = Species(name="human", clade="mammals", legs=2, extinct=False)
        self.client.add_and_flush(human)
        self.assertIsNotNone(human.id)

        # Check the entry is in the database
        retrieved_human = self.client.query_table(Species, name="human").first()
        self.assertEqual(human, retrieved_human)

        # Add an entry using 'insert_into_table'
        diplodocus = self.client.insert_into_table(Species, name="diplodocus", clade="dinosaurs", legs=4, extinct=True)
        self.assertTrue(isinstance(diplodocus, Species))
        self.assertEqual(diplodocus.name, "diplodocus")

        # Check that there are now 2 entries in the table
        full_table = self.client.query_table(Species).all()
        self.assertEqual(len(full_table), 2)

        # Try to insert the same entry again using find_or_insert
        result = self.client.find_or_insert(Species, name=diplodocus.name)
        self.assertEqual(result, diplodocus)

        # Insert another entry using find_or_insert
        bumblebee = self.client.find_or_insert(Species, name="bumblebee", clade="insects", legs=6, extinct=False)
        self.assertTrue(isinstance(bumblebee, Species))
        self.assertEqual(bumblebee.clade, "insects")

        # Check that there are now 2 entries in the table
        full_table = self.client.query_table(Species).all()
        self.assertEqual(len(full_table), 3)


if __name__ == '__main__':
    unittest.main(verbosity=2, buffer=True)
