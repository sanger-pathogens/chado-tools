import os
import unittest.mock
import urllib.error
import getpass
import sqlalchemy_utils
from .. import dbutils, utils


class TestConnection(unittest.TestCase):
    """Tests for database connections"""

    modules_dir = os.path.dirname(os.path.abspath(dbutils.__file__))
    data_dir = os.path.join(modules_dir, 'tests', 'data')

    def setUp(self):
        # Checks if the default connection file is available and reads in the parameters
        self.assertTrue(os.path.exists(os.path.abspath(dbutils.default_configuration_file())))
        self.connectionParameters = utils.parse_yaml(dbutils.default_configuration_file())
        self.uri = dbutils.generate_uri(self.connectionParameters)

    def tearDown(self):
        self.connectionParameters.clear()

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

    def test_random_database_uri(self):
        # Tests that a function creates a URI of a database that does not exist
        uri = dbutils.random_database_uri(self.connectionParameters)
        self.assertFalse(dbutils.exists(uri))
        pos = self.uri.rfind("/")
        self.assertEqual(uri[:pos], self.uri[:pos])
        self.assertNotEqual(uri[pos:], self.uri[pos:])

    def test_connect(self):
        # Tests that a connection to the default database can be established and that queries can be executed
        conn = dbutils.open_connection(self.uri)
        self.assertFalse(conn.closed)
        result = conn.execute("SELECT 1 + 2").scalar()
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

        # Generate a database with a random name and check it exists
        uri = dbutils.random_database_uri(self.connectionParameters)
        dbutils.create_database(uri)
        self.assertTrue(dbutils.exists(uri))

        # Set up the database according to a test schema
        test_schema = os.path.join(self.data_dir, "dbutils_example_schema.sql")
        self.assertTrue(os.path.exists(test_schema))
        dbutils.setup_database(uri, test_schema)

        # Check if the database is correctly set up
        conn = dbutils.open_connection(uri)
        result_proxy = conn.execute("SELECT * FROM species ORDER BY legs ASC")
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
        result_proxy = conn.execute("SELECT name FROM species WHERE extinct = TRUE")
        result = result_proxy.fetchall()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "diplodocus")
        result_proxy.close()
        dbutils.close_connection(conn)

        # Export the entire table and check that the result is as expected
        result = dbutils.run_query(uri, "SELECT name, clade, legs, extinct FROM species ORDER BY legs ASC", True)
        self.assertEqual(result[0][0], "name")
        self.assertEqual(result[1][0], "leech")
        self.assertEqual(len(result), 5)

        # Drop the database, remove the archive file and check that everything is gone
        dbutils.drop_database(uri, True)
        self.assertFalse(dbutils.exists(uri))
        os.remove(archive_file)
        self.assertFalse(os.path.exists(archive_file))


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
