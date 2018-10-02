import os
import string
import random
import unittest.mock
import urllib.error
import filecmp
import getpass
import sqlalchemy_utils
from pychado import dbutils, utils

modules_dir = os.path.dirname(os.path.abspath(dbutils.__file__))
data_dir = os.path.join(modules_dir, 'tests', 'data')


class TestConnection(unittest.TestCase):
    """Tests for database connections"""

    def setUp(self):
        # Checks if the default connection file is available and reads in the parameters
        self.assertTrue(os.path.exists(os.path.abspath(dbutils.default_configuration_file())))
        self.connectionParameters = utils.parse_yaml(dbutils.default_configuration_file())
        self.dsn = dbutils.generate_dsn(self.connectionParameters)
        self.uri = dbutils.generate_uri(self.connectionParameters)

    def tearDown(self):
        self.connectionParameters.clear()

    def random_database(self) -> str:
        """Generates a random database name and makes sure the name is not yet in use"""
        parameters = self.connectionParameters.copy()
        parameters["database"] = "postgres"
        uri = dbutils.generate_uri(parameters)
        while dbutils.exists(uri):
            parameters["database"] = "".join(random.choices(string.ascii_lowercase, k=10))
            uri = dbutils.generate_uri(parameters)
        return uri

    def test_factory_settings(self):
        # Tests if the settings in the default connection file are equivalent to the factory settings
        factory_settings = utils.parse_yaml(dbutils.factory_settings_configuration_file())
        self.assertEqual(self.connectionParameters, factory_settings)

    def test_connection_parameters(self):
        # Tests if the default connection file contains all required parameters
        self.assertIn("database", self.connectionParameters)
        self.assertIn("user", self.connectionParameters)
        self.assertIn("password", self.connectionParameters)
        self.assertIn("host", self.connectionParameters)
        self.assertIn("port", self.connectionParameters)

    @unittest.mock.patch('builtins.input')
    @unittest.mock.patch('getpass.getpass')
    def test_set_reset_parameters(self, mock_getpass, mock_input):
        # Tests if the default connection parameters can be changed
        self.assertIs(mock_input, input)
        self.assertIs(mock_getpass, getpass.getpass)
        mock_input.side_effect = ["myhost", 5555, "mydb", "myuser"]
        mock_getpass.return_value = "mypw"
        dbutils.set_default_parameters()
        default_parameters = utils.parse_yaml(dbutils.default_configuration_file())
        self.assertEqual(default_parameters["host"], "myhost")
        self.assertEqual(default_parameters["port"], "5555")
        self.assertEqual(default_parameters["database"], "mydb")
        self.assertEqual(default_parameters["user"], "myuser")
        self.assertEqual(default_parameters["password"], "mypw")
        dbutils.reset_default_parameters()
        default_parameters = utils.parse_yaml(dbutils.default_configuration_file())
        self.assertEqual(self.connectionParameters, default_parameters)

    def test_connection_uri(self):
        # Tests the correct creation of a database connection string in URI format
        uri = "postgresql://" \
              + self.connectionParameters["user"] + ":" \
              + self.connectionParameters["password"] + "@" \
              + self.connectionParameters["host"] + ":" \
              + self.connectionParameters["port"] + "/" \
              + self.connectionParameters["database"]
        self.assertEqual(self.uri, uri)

    def test_connection_dsn(self):
        # Tests the correct creation of a database connection string in keyword/value format
        dsn = "dbname=" + self.connectionParameters["database"] \
              + " user=" + self.connectionParameters["user"] \
              + " password=" + self.connectionParameters["password"] \
              + " host=" + self.connectionParameters["host"] \
              + " port=" + self.connectionParameters["port"]
        self.assertEqual(self.dsn, dsn)

    def test_connect(self):
        # Tests that a connection to the default database can be established and that queries can be executed
        conn = dbutils.open_connection(self.uri)
        self.assertFalse(conn.closed)
        result = dbutils.execute_query(conn, "SELECT 1 + 2").scalar()
        self.assertEqual(result, 3)
        dbutils.close_connection(conn)
        self.assertTrue(conn.closed)

    @unittest.mock.patch('builtins.input')
    @unittest.mock.patch('sqlalchemy_utils.drop_database')
    def test_drop_on_demand(self, mock_drop, mock_input):
        # Tests that a database is only dropped after confirmation by the user
        self.assertIs(mock_drop, sqlalchemy_utils.drop_database)
        self.assertIs(mock_input, input)

        mock_input.return_value = 'n'
        dbutils.drop_database(self.uri)
        mock_drop.assert_not_called()

        mock_drop.reset_mock()
        mock_input.return_value = 'y'
        dbutils.drop_database(self.uri)
        mock_drop.assert_called()

        mock_drop.reset_mock()
        dbutils.drop_database(self.uri, True)
        mock_drop.assert_called()

    def test_integration(self):
        # Test the basic functionality for creation and deletion of databases
        # NOTE: This test depends on an example SQL schema in the tests/data directory.
        # If the schema is changed, the test might fail.

        # Generate a random database name
        uri = self.random_database()

        # Create the database and check it exists
        dbutils.create_database(uri)
        self.assertTrue(dbutils.exists(uri))

        # Set up the database according to a test schema
        test_schema = os.path.join(data_dir, "dbutils_example_schema.sql")
        self.assertTrue(os.path.exists(test_schema))
        dbutils.setup_database(uri, test_schema)

        # Check if the database is correctly set up
        conn = dbutils.open_connection(uri)
        result_proxy = dbutils.execute_query(conn, "SELECT * FROM species ORDER BY legs ASC")
        result = result_proxy.fetchall()
        self.assertEqual(len(result), 4)
        self.assertEqual(result[0]["name"], "leech")
        result_proxy.close()
        dbutils.close_connection(conn)

        # Dump the database and check for the archive file
        archive_file = "tmp.dump"
        dbutils.dump_database(uri, archive_file)
        self.assertTrue(os.path.exists(archive_file))

        # Restore the database and check it exists
        dbutils.restore_database(uri, archive_file)
        self.assertTrue(dbutils.exists(uri))

        # Check if the database is still correctly set up
        conn = dbutils.open_connection(uri)
        result_proxy = dbutils.execute_query(conn, "SELECT name FROM species WHERE extinct = TRUE")
        result = result_proxy.fetchall()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "diplodocus")
        result_proxy.close()
        dbutils.close_connection(conn)

        # Export the entire table to a file and check that the result is as expected
        temp_file = os.path.join(os.getcwd(), "tmp.csv")
        dbutils.query_to_file(uri, "SELECT name, class, legs, extinct FROM species ORDER BY legs ASC", {}, temp_file,
                              ";", True)
        self.assertTrue(os.path.exists(temp_file))
        output_file = os.path.join(data_dir, "dbutils_species_table.csv")
        self.assertTrue(os.path.exists(output_file))
        self.assertTrue(filecmp.cmp(temp_file, output_file))

        # Drop the database, remove the archive file and check that everything is gone
        dbutils.drop_database(uri, True)
        self.assertFalse(dbutils.exists(uri))
        os.remove(archive_file)
        os.remove(temp_file)
        self.assertFalse(os.path.exists(archive_file))
        self.assertFalse(os.path.exists(temp_file))


class TestDownload(unittest.TestCase):
    """Tests for data download"""

    def test_default_schema_url(self):
        # Tests if the default schema is retrievable and has a valid address
        url = dbutils.default_schema_url()
        self.assertEqual(url[:4], "http")
        self.assertEqual(url[-3:], "sql")

    def test_download_schema(self):
        # Tests the download of a file from a given url
        url = dbutils.default_schema_url()
        utils.download_file(url)
        url = url + "_arbitraryString"
        with self.assertRaises(urllib.error.HTTPError):
            utils.download_file(url)
        url = "http://xyzxyz.xyzxyz"
        with self.assertRaises(urllib.error.URLError):
            utils.download_file(url)


if __name__ == '__main__':
    unittest.main(verbosity=2, buffer=True)
