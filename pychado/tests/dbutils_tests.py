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
        self.connectionParameters["database"] = "postgres"
        self.uri = dbutils.generate_uri(self.connectionParameters)

    def tearDown(self):
        self.connectionParameters.clear()

    def test_connection_parameters(self):
        # Tests if the default connection file contains all required parameters
        self.assertIn("database", self.connectionParameters)
        self.assertIn("user", self.connectionParameters)
        self.assertIn("password", self.connectionParameters)
        self.assertIn("host", self.connectionParameters)
        self.assertIn("port", self.connectionParameters)

    @unittest.mock.patch('pychado.dbutils.get_connection_password')
    @unittest.mock.patch('pychado.dbutils.get_connection_parameters_from_env')
    @unittest.mock.patch('pychado.utils.parse_yaml')
    def test_get_connection_parameters(self, mock_parse, mock_env, mock_pw):
        # Tests the function that determines connection parameters
        self.assertIs(mock_env, dbutils.get_connection_parameters_from_env)
        self.assertIs(mock_pw, dbutils.get_connection_password)
        self.assertIs(mock_parse, utils.parse_yaml)
        mock_pw.return_value = "mypw"
        mock_env.return_value = {"host": "myhost", "port": 1234, "user": "myself", "password": "somepw"}
        mock_parse.return_value = {"host": "otherhost", "port": 4321, "user": "someone", "password": "too_easy"}

        params = dbutils.get_connection_parameters("", False, "testdb")
        mock_parse.assert_not_called()
        mock_env.assert_called()
        mock_pw.assert_not_called()
        self.assertEqual(params["host"], "myhost")
        self.assertEqual(params["password"], "somepw")
        self.assertEqual(params["database"], "testdb")

        mock_env.reset_mock()
        mock_pw.reset_mock()
        mock_parse.reset_mock()
        params = dbutils.get_connection_parameters("", True, "testdb")
        mock_parse.assert_not_called()
        mock_env.assert_called()
        mock_pw.assert_called()
        self.assertEqual(params["host"], "myhost")
        self.assertEqual(params["password"], "mypw")
        self.assertEqual(params["database"], "testdb")

        mock_env.reset_mock()
        mock_pw.reset_mock()
        mock_parse.reset_mock()
        params = dbutils.get_connection_parameters("user_supplied_file", False, "otherdb")
        mock_parse.assert_called_with("user_supplied_file")
        mock_env.assert_not_called()
        mock_pw.assert_not_called()
        self.assertEqual(params["host"], "otherhost")
        self.assertEqual(params["password"], "too_easy")
        self.assertEqual(params["database"], "otherdb")

    @unittest.skipIf("TRAVIS_BUILD" not in os.environ or os.environ["TRAVIS_BUILD"] == "no",
                     "Only run this test on Travis CI (to avoid messing up local environment).")
    def test_get_connection_parameters_from_env(self):
        # Tests the function that reads connection parameters from environment variables
        params = dbutils.get_connection_parameters_from_env()
        self.assertEqual(params["host"], self.connectionParameters["host"])
        self.assertEqual(params["port"], self.connectionParameters["port"])
        self.assertEqual(params["user"], self.connectionParameters["user"])
        self.assertEqual(params["password"], self.connectionParameters["password"])

        os.environ["CHADO_HOST"] = "newhost"
        os.environ["CHADO_PORT"] = "5555"
        os.environ["CHADO_USER"] = "newuser"
        os.environ["CHADO_PASS"] = "newpassword"
        params = dbutils.get_connection_parameters_from_env()
        self.assertEqual(params["host"], "newhost")
        self.assertEqual(params["port"], "5555")
        self.assertEqual(params["user"], "newuser")
        self.assertEqual(params["password"], "newpassword")

    @unittest.mock.patch('getpass.getpass')
    def test_get_connection_password(self, mock_getpass):
        # Tests the setting of a connection password by the user
        self.assertIs(mock_getpass, getpass.getpass)
        mock_getpass.return_value = "mypw"
        pw = dbutils.get_connection_password()
        mock_getpass.assert_called()
        self.assertEqual(pw, "mypw")

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
