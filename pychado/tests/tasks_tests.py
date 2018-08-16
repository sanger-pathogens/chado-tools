import unittest.mock
from scripts import chado_tools
from pychado import tasks, queries, dbutils, utils


class TestTasks(unittest.TestCase):
    """Tests the functionality of all commands of the CHADO program"""

    def setUp(self):
        self.connectionParameters = tasks.read_configuration_file("")
        self.dsn = dbutils.generate_dsn(self.connectionParameters)
        self.uri = dbutils.generate_uri(self.connectionParameters)

    def tearDown(self):
        self.connectionParameters.clear()

    @unittest.mock.patch('pychado.utils.parse_yaml')
    @unittest.mock.patch('pychado.dbutils.default_configuration_file')
    def test_read_configuration_file(self, mock_default, mock_parse):
        # Checks that the default configuration file is used unless another file is supplied
        self.assertIs(mock_default, dbutils.default_configuration_file)
        self.assertIs(mock_parse, utils.parse_yaml)

        mock_default.return_value = "default_file"
        tasks.read_configuration_file("")
        mock_default.assert_called()
        mock_parse.assert_called_with("default_file")

        mock_default.reset_mock()
        mock_parse.reset_mock()
        tasks.read_configuration_file("user_supplied_file")
        mock_default.assert_not_called()
        mock_parse.assert_called_with("user_supplied_file")

    @unittest.mock.patch('pychado.dbutils.create_database')
    @unittest.mock.patch('pychado.dbutils.exists')
    def test_access(self, mock_exist, mock_create):
        # Checks that database access is only permitted if the database exists or gets created,
        # and checks that no existing database is overwritten
        self.assertIs(mock_exist, dbutils.exists)
        self.assertIs(mock_create, dbutils.create_database)

        mock_exist.return_value = True
        self.assertTrue(tasks.check_access(self.connectionParameters, "testdb", "connect"))
        mock_create.assert_not_called()
        self.assertFalse(tasks.check_access(self.connectionParameters, "testdb", "create"))
        mock_create.assert_not_called()

        mock_exist.return_value = False
        self.assertFalse(tasks.check_access(self.connectionParameters, "testdb", "connect"))
        mock_create.assert_not_called()
        self.assertTrue(tasks.check_access(self.connectionParameters, "testdb", "create"))
        mock_create.assert_called_with(self.dsn, "testdb")

    @unittest.mock.patch('pychado.dbutils.set_default_parameters')
    def test_init(self, mock_set):
        # Checks that the function setting default connection parameters is correctly called
        self.assertIs(mock_set, dbutils.set_default_parameters)
        args = chado_tools.parse_arguments(["chado", "init"])
        tasks.run_command_with_arguments("init", args, self.connectionParameters)
        mock_set.assert_called()

    @unittest.mock.patch('pychado.dbutils.reset_default_parameters')
    def test_reset(self, mock_reset):
        # Checks that the function resetting default connection parameters to factory state is correctly called
        self.assertIs(mock_reset, dbutils.reset_default_parameters)
        args = chado_tools.parse_arguments(["chado", "reset"])
        tasks.run_command_with_arguments("reset", args, self.connectionParameters)
        mock_reset.assert_called()

    @unittest.mock.patch('pychado.dbutils.connect_to_database')
    def test_connect(self, mock_connect):
        # Checks that the function establishing a connection is correctly called
        self.assertIs(mock_connect, dbutils.connect_to_database)
        args = chado_tools.parse_arguments(["chado", "connect", "testdb"])
        tasks.run_command_with_arguments("connect", args, self.connectionParameters)
        mock_connect.assert_called_with(self.uri)

    @unittest.mock.patch('pychado.dbutils.setup_database')
    def test_create(self, mock_create):
        # Checks that the function setting up a database is correctly called
        self.assertIs(mock_create, dbutils.setup_database)
        args = chado_tools.parse_arguments(["chado", "create", "-s", "testschema", "testdb"])
        tasks.run_command_with_arguments("create", args, self.connectionParameters)
        mock_create.assert_called_with(self.uri, "testschema")

    @unittest.mock.patch('pychado.dbutils.dump_database')
    def test_dump(self, mock_dump):
        # Checks that the function dumping a database is correctly called
        self.assertIs(mock_dump, dbutils.dump_database)
        args = chado_tools.parse_arguments(["chado", "dump", "testdb", "testarchive"])
        tasks.run_command_with_arguments("dump", args, self.connectionParameters)
        mock_dump.assert_called_with(self.uri, "testarchive")

    @unittest.mock.patch('pychado.dbutils.restore_database')
    def test_restore(self, mock_restore):
        # Checks that the function restoring a database is correctly called
        self.assertIs(mock_restore, dbutils.restore_database)
        args = chado_tools.parse_arguments(["chado", "restore", "testdb", "testarchive"])
        tasks.run_command_with_arguments("restore", args, self.connectionParameters)
        mock_restore.assert_called_with(self.uri, "testarchive")

    @unittest.mock.patch('pychado.dbutils.copy_from_file')
    def test_import(self, mock_import):
        # Checks that the function importing data into a database table is correctly called
        self.assertIs(mock_import, dbutils.copy_from_file)
        args = chado_tools.parse_arguments(["chado", "import", "-d", ";", "-f", "testfile", "testdb", "testtable"])
        tasks.run_command_with_arguments("import", args, self.connectionParameters)
        mock_import.assert_called_with(self.dsn, "testtable", "testfile", ";")

    @unittest.mock.patch('pychado.dbutils.copy_to_file')
    def test_export(self, mock_export):
        # Checks that the function exporting data from a database table is correctly called
        self.assertIs(mock_export, dbutils.copy_to_file)
        args = chado_tools.parse_arguments(["chado", "export", "-H", "-d", ";", "-o", "testfile", "testdb",
                                            "testtable"])
        tasks.run_command_with_arguments("export", args, self.connectionParameters)
        mock_export.assert_called_with(self.dsn, "testtable", "testfile", ";", True)

    @unittest.mock.patch('pychado.utils.read_text')
    @unittest.mock.patch('pychado.dbutils.query_to_file')
    def test_query(self, mock_query, mock_read):
        # Checks that the function querying a database is correctly called
        self.assertIs(mock_query, dbutils.query_to_file)
        self.assertIs(mock_read, utils.read_text)
        # Direct query
        args = chado_tools.parse_arguments(["chado", "query", "-H", "-d", ";", "-o", "testfile", "-q", "testquery",
                                            "testdb"])
        tasks.run_command_with_arguments("query", args, self.connectionParameters)
        mock_query.assert_called_with(self.dsn, "testquery", (), "testfile", ";", True)
        # Query extracted from file
        args = chado_tools.parse_arguments(["chado", "query", "-d", ";", "-o", "testfile", "-f", "testqueryfile",
                                            "testdb"])
        mock_read.return_value = "query_from_file"
        tasks.run_command_with_arguments("query", args, self.connectionParameters)
        mock_query.assert_called_with(self.dsn, "query_from_file", (), "testfile", ";", False)

    @unittest.mock.patch('pychado.queries.load_stats_query')
    @unittest.mock.patch('pychado.dbutils.query_to_file')
    def test_stats(self, mock_query, mock_load):
        # Checks that the function providing database statistics is correctly called
        self.assertIs(mock_query, dbutils.query_to_file)
        self.assertIs(mock_load, queries.load_stats_query)
        args = chado_tools.parse_arguments(["chado", "stats", "-H", "-d", ";", "-o", "testfile",
                                            "-a", "testorganism", "-D", "testdate", "testdb"])
        mock_load.return_value = "testquery"
        tasks.run_command_with_arguments("stats", args, self.connectionParameters)
        mock_query.assert_called_with(self.dsn, "testquery", ("testdate", "testorganism"), "testfile", ";", True)

    @unittest.mock.patch('pychado.queries.load_list_query')
    @unittest.mock.patch('pychado.dbutils.query_to_file')
    def test_list_organisms(self, mock_query, mock_load):
        # Checks that the function listing organisms is correctly called
        self.assertIs(mock_query, dbutils.query_to_file)
        self.assertIs(mock_load, queries.load_list_query)
        args = chado_tools.parse_arguments(["chado", "list", "organisms", "-H", "-d", ";", "-o", "testfile", "testdb"])
        mock_load.return_value = "testquery"
        tasks.run_sub_command_with_arguments("list", "organisms", args, self.connectionParameters)
        mock_query.assert_called_with(self.dsn, "testquery", (), "testfile", ";", True)

    @unittest.mock.patch('pychado.queries.load_list_query')
    @unittest.mock.patch('pychado.dbutils.query_to_file')
    def test_list_products(self, mock_query, mock_load):
        # Checks that the function listing products is correctly called
        self.assertIs(mock_query, dbutils.query_to_file)
        self.assertIs(mock_load, queries.load_list_query)
        args = chado_tools.parse_arguments(["chado", "list", "products", "-H", "-d", ";", "-o", "testfile",
                                            "-a", "testorganism", "testdb"])
        mock_load.return_value = "testquery"
        tasks.run_sub_command_with_arguments("list", "products", args, self.connectionParameters)
        mock_query.assert_called_with(self.dsn, "testquery", ("testorganism", ), "testfile", ";", True)

    @unittest.mock.patch('pychado.queries.load_insert_statement')
    @unittest.mock.patch('pychado.dbutils.connect_and_execute_statement')
    def test_insert_organism(self, mock_statement, mock_load):
        # Checks that the function inserting organisms is correctly called
        self.assertIs(mock_statement, dbutils.connect_and_execute_statement)
        self.assertIs(mock_load, queries.load_insert_statement)
        args = chado_tools.parse_arguments(["chado", "insert", "organism", "-g", "testgenus", "-s", "testspecies",
                                            "-a", "testabbreviation", "--common_name", "testname",
                                            "--comment", "testcomment", "testdb"])
        mock_load.return_value = "teststatement"
        tasks.run_sub_command_with_arguments("insert", "organism", args, self.connectionParameters)
        mock_statement.assert_called_with(self.dsn, "teststatement", ("testgenus", "testspecies",
                                                                      "testabbreviation", "testname", "testcomment"))

    @unittest.mock.patch('pychado.queries.load_delete_statement')
    @unittest.mock.patch('pychado.dbutils.connect_and_execute_statement')
    def test_delete_organism(self, mock_statement, mock_load):
        # Checks that the function deleting organisms is correctly called
        self.assertIs(mock_statement, dbutils.connect_and_execute_statement)
        self.assertIs(mock_load, queries.load_delete_statement)
        args = chado_tools.parse_arguments(["chado", "delete", "organism", "-a", "testorganism", "testdb"])
        mock_load.return_value = "teststatement"
        tasks.run_sub_command_with_arguments("delete", "organism", args, self.connectionParameters)
        mock_statement.assert_called_with(self.dsn, "teststatement", ("testorganism", ))


if __name__ == '__main__':
    unittest.main(verbosity=2, buffer=True)
