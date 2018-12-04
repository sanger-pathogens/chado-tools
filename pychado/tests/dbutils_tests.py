import os
import unittest.mock
import urllib.error
import tempfile
import filecmp
import getpass
import sqlalchemy.engine
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

        # Export the entire table and check that the result is as expected
        result = dbutils.run_query(conn, "SELECT name, clade, legs FROM species ORDER BY legs ASC").fetchall()
        self.assertEqual(len(result), 4)
        self.assertEqual(len(result[0]), 3)
        self.assertEqual(result[0][0], "leech")
        dbutils.close_connection(conn)

        # Drop the database, remove the archive file and check that everything is gone
        dbutils.drop_database(uri, True)
        self.assertFalse(dbutils.exists(uri))
        os.remove(archive_file)
        self.assertFalse(os.path.exists(archive_file))

    @unittest.mock.patch('pychado.dbutils.print_query_result')
    @unittest.mock.patch('pychado.dbutils.run_query')
    @unittest.mock.patch('pychado.dbutils.close_connection')
    @unittest.mock.patch('pychado.dbutils.open_connection')
    def test_query_and_print(self, mock_open, mock_close, mock_query, mock_print):
        # Tests that the wrapper function for database queries is correctly run
        self.assertIs(mock_open, dbutils.open_connection)
        self.assertIs(mock_close, dbutils.close_connection)
        self.assertIs(mock_query, dbutils.run_query)
        self.assertIs(mock_print, dbutils.print_query_result)

        mock_connection_object = mock_open.return_value
        mock_result_object = mock_query.return_value

        dbutils.query_and_print("testuri", "testquery", "testfile", "json", True, ";")
        mock_open.assert_called_with("testuri")
        mock_query.assert_called_with(mock_connection_object, "testquery")
        mock_print.assert_called_with(mock_result_object, "testfile", "json", True, ";")
        self.assertIn(unittest.mock.call.close(), mock_result_object.mock_calls)
        mock_close.assert_called_with(mock_connection_object)

    @unittest.mock.patch('pychado.dbutils.print_query_result_csv')
    @unittest.mock.patch('pychado.dbutils.print_query_result_json')
    @unittest.mock.patch('pychado.utils.close')
    @unittest.mock.patch('pychado.utils.open_file_write')
    def test_print_query_result(self, mock_open, mock_close, mock_json, mock_csv):
        # Tests the function printing database queries to file
        self.assertIs(mock_open, utils.open_file_write)
        self.assertIs(mock_close, utils.close)
        self.assertIs(mock_json, dbutils.print_query_result_json)
        self.assertIs(mock_csv, dbutils.print_query_result_csv)

        result_object = unittest.mock.Mock(spec=sqlalchemy.engine.ResultProxy)
        mock_file_object = mock_open.return_value

        dbutils.print_query_result(result_object, "testfile", "json", True, ";")
        mock_open.assert_called_with("testfile")
        mock_json.assert_called_with(result_object, mock_file_object)
        mock_csv.assert_not_called()
        mock_close.assert_called_with(mock_file_object)

        mock_json.reset_mock()
        mock_csv.reset_mock()
        dbutils.print_query_result(result_object, "testfile", "csv", True, ";")
        mock_json.assert_not_called()
        mock_csv.assert_called_with(result_object, mock_file_object, True, ";")

    def test_print_json(self):
        # Tests the function exporting a query result to a JSON file
        result_object = unittest.mock.Mock(spec=sqlalchemy.engine.ResultProxy)
        result_object.configure_mock(**{"keys.return_value": ["key1", "key2"],
                                        "fetchone.side_effect": [["v1", "v2"], ["x1", "x2"], None]})
        filename = tempfile.mkstemp()[1]
        f = utils.open_file_write(filename)
        dbutils.print_query_result_json(result_object, f)
        utils.close(f)
        self.assertTrue(filecmp.cmp(filename, os.path.join(self.data_dir, "dbutils_test_result.json")))
        os.remove(filename)

    def test_print_csv(self):
        # Tests the function exporting a query result to a CSV file
        result_object = unittest.mock.Mock(spec=sqlalchemy.engine.ResultProxy)
        result_object.configure_mock(**{"keys.return_value": ["key1", "key2"],
                                        "fetchone.side_effect": [["v1", "v2"], ["x1", "x2"], None]})
        filename = tempfile.mkstemp()[1]
        f = utils.open_file_write(filename)
        dbutils.print_query_result_csv(result_object, f, True, ";")
        utils.close(f)
        self.assertTrue(filecmp.cmp(filename, os.path.join(self.data_dir, "dbutils_test_result.csv")))
        os.remove(filename)


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
