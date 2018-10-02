import unittest.mock
from terminal import chado_tools
from pychado import tasks, queries, dbutils, utils
from pychado.io import load_ontology


class TestTasks(unittest.TestCase):
    """Tests the functionality of all commands of the CHADO program"""

    def setUp(self):
        self.uri = tasks.create_connection_string("", "testdb")

    @unittest.mock.patch('pychado.utils.parse_yaml')
    @unittest.mock.patch('pychado.dbutils.default_configuration_file')
    def test_create_connection_string(self, mock_default, mock_parse):
        # Checks that the default configuration file is used unless another file is supplied
        self.assertIs(mock_default, dbutils.default_configuration_file)
        self.assertIs(mock_parse, utils.parse_yaml)

        mock_default.return_value = "default_file"
        tasks.create_connection_string("", "testdb")
        mock_default.assert_called()
        mock_parse.assert_called_with("default_file")

        mock_default.reset_mock()
        mock_parse.reset_mock()
        tasks.create_connection_string("user_supplied_file", "testdb")
        mock_default.assert_not_called()
        mock_parse.assert_called_with("user_supplied_file")

    @unittest.mock.patch('pychado.dbutils.exists')
    def test_access(self, mock_exist):
        # Checks that database access is only permitted if the database exists or gets created,
        # and checks that no existing database is overwritten
        self.assertIs(mock_exist, dbutils.exists)

        mock_exist.return_value = True
        self.assertTrue(tasks.check_access(self.uri, "connect"))
        self.assertFalse(tasks.check_access(self.uri, "create"))

        mock_exist.return_value = False
        self.assertFalse(tasks.check_access(self.uri, "connect"))
        self.assertTrue(tasks.check_access(self.uri, "create"))

    @unittest.mock.patch('pychado.dbutils.reset_default_parameters')
    @unittest.mock.patch('pychado.dbutils.set_default_parameters')
    def test_init_reset(self, mock_set, mock_reset):
        # Checks that the functions setting/resetting default connection parameters are correctly called
        self.assertIs(mock_set, dbutils.set_default_parameters)
        self.assertIs(mock_reset, dbutils.reset_default_parameters)

        tasks.setup("init")
        mock_set.assert_called()
        mock_reset.assert_not_called()
        mock_set.reset_mock()
        mock_reset.reset_mock()

        tasks.setup("reset")
        mock_set.assert_not_called()
        mock_reset.assert_called()
        mock_set.reset_mock()
        mock_reset.reset_mock()

        tasks.setup("non_existing_command")
        mock_set.assert_not_called()
        mock_reset.assert_not_called()

    @unittest.mock.patch('pychado.dbutils.connect_to_database')
    def test_connect(self, mock_connect):
        # Checks that the function establishing a connection is correctly called
        self.assertIs(mock_connect, dbutils.connect_to_database)
        args = ["chado", "connect", "testdb"]
        parsed_args = chado_tools.parse_arguments(args)
        tasks.run_command_with_arguments(args[1], "", parsed_args, self.uri)
        mock_connect.assert_called_with(self.uri)

    @unittest.mock.patch('pychado.dbutils.setup_database')
    @unittest.mock.patch('pychado.dbutils.create_database')
    def test_create(self, mock_create, mock_setup):
        # Checks that the function creating and setting up a database is correctly called
        self.assertIs(mock_create, dbutils.create_database)
        self.assertIs(mock_setup, dbutils.setup_database)
        args = ["chado", "admin", "create", "-s", "testschema", "testdb"]
        parsed_args = chado_tools.parse_arguments(args)
        tasks.run_command_with_arguments(args[1], args[2], parsed_args, self.uri)
        mock_create.assert_called_with(self.uri)
        mock_setup.assert_called_with(self.uri, "testschema")

    @unittest.mock.patch('pychado.dbutils.drop_database')
    def test_drop(self, mock_drop):
        # Checks that a function dropping a database is correctly called
        self.assertIs(mock_drop, dbutils.drop_database)
        args = ["chado", "admin", "drop", "testdb"]
        parsed_args = chado_tools.parse_arguments(args)
        tasks.run_command_with_arguments(args[1], args[2], parsed_args, self.uri)
        mock_drop.assert_called_with(self.uri)

    @unittest.mock.patch('pychado.dbutils.dump_database')
    def test_dump(self, mock_dump):
        # Checks that the function dumping a database is correctly called
        self.assertIs(mock_dump, dbutils.dump_database)
        args = ["chado", "admin", "dump", "testdb", "testarchive"]
        parsed_args = chado_tools.parse_arguments(args)
        tasks.run_command_with_arguments(args[1], args[2], parsed_args, self.uri)
        mock_dump.assert_called_with(self.uri, "testarchive")

    @unittest.mock.patch('pychado.dbutils.restore_database')
    @unittest.mock.patch('pychado.dbutils.create_database')
    def test_restore(self, mock_create, mock_restore):
        # Checks that the function restoring a database is correctly called
        self.assertIs(mock_create, dbutils.create_database)
        self.assertIs(mock_restore, dbutils.restore_database)
        args = ["chado", "admin", "restore", "testdb", "testarchive"]
        parsed_args = chado_tools.parse_arguments(args)
        tasks.run_command_with_arguments(args[1], args[2], parsed_args, self.uri)
        mock_create.assert_called_with(self.uri)
        mock_restore.assert_called_with(self.uri, "testarchive")

    @unittest.mock.patch('pychado.utils.read_text')
    @unittest.mock.patch('pychado.dbutils.query_to_file')
    def test_query(self, mock_query, mock_read):
        # Checks that the function querying a database is correctly called
        self.assertIs(mock_query, dbutils.query_to_file)
        self.assertIs(mock_read, utils.read_text)
        # Direct query
        args = ["chado", "query", "-H", "-d", ";", "-o", "testfile", "-q", "testquery", "testdb"]
        parsed_args = chado_tools.parse_arguments(args)
        tasks.run_command_with_arguments(args[1], "", parsed_args, self.uri)
        mock_query.assert_called_with(self.uri, "testquery", {}, "testfile", ";", True)
        # Query extracted from file
        args = ["chado", "query", "-d", ";", "-o", "testfile", "-f", "testqueryfile", "testdb"]
        parsed_args = chado_tools.parse_arguments(args)
        mock_read.return_value = "query_from_file"
        tasks.run_command_with_arguments(args[1], "", parsed_args, self.uri)
        mock_query.assert_called_with(self.uri, "query_from_file", {}, "testfile", ";", False)

    @unittest.mock.patch('pychado.queries.specify_stats_parameters')
    @unittest.mock.patch('pychado.queries.load_stats_query')
    @unittest.mock.patch('pychado.dbutils.query_to_file')
    def test_stats(self, mock_query, mock_load, mock_specify):
        # Checks that the function providing database statistics is correctly called
        self.assertIs(mock_query, dbutils.query_to_file)
        self.assertIs(mock_load, queries.load_stats_query)
        self.assertIs(mock_specify, queries.specify_stats_parameters)
        args = ["chado", "stats", "-H", "-d", ";", "-o", "testfile", "--start_date", "testdate", "testdb"]
        parsed_args = chado_tools.parse_arguments(args)
        mock_load.return_value = "testquery"
        mock_specify.return_value = {"testkey": "testvalue"}
        tasks.run_command_with_arguments(args[1], "", parsed_args, self.uri)
        mock_query.assert_called_with(self.uri, "testquery", {"testkey": "testvalue"}, "testfile", ";", True)

    @unittest.mock.patch('pychado.queries.specify_list_parameters')
    @unittest.mock.patch('pychado.queries.load_list_query')
    @unittest.mock.patch('pychado.dbutils.query_to_file')
    def test_list_organisms(self, mock_query, mock_load, mock_specify):
        # Checks that the function listing organisms is correctly called
        self.assertIs(mock_query, dbutils.query_to_file)
        self.assertIs(mock_load, queries.load_list_query)
        self.assertIs(mock_specify, queries.specify_list_parameters)
        args = ["chado", "list", "organisms", "-H", "-d", ";", "-o", "testfile", "testdb"]
        parsed_args = chado_tools.parse_arguments(args)
        mock_load.return_value = "testquery"
        mock_specify.return_value = {"testkey": "testvalue"}
        tasks.run_command_with_arguments(args[1], args[2], parsed_args, self.uri)
        mock_query.assert_called_with(self.uri, "testquery", {"testkey": "testvalue"}, "testfile", ";", True)

    @unittest.mock.patch('pychado.queries.specify_list_parameters')
    @unittest.mock.patch('pychado.queries.load_list_query')
    @unittest.mock.patch('pychado.dbutils.query_to_file')
    def test_list_cvterms(self, mock_query, mock_load, mock_specify):
        # Checks that the function listing CV terms is correctly called
        self.assertIs(mock_query, dbutils.query_to_file)
        self.assertIs(mock_load, queries.load_list_query)
        self.assertIs(mock_specify, queries.specify_list_parameters)
        args = ["chado", "list", "cvterms", "-H", "-d", ";", "-o", "testfile", "testdb"]
        parsed_args = chado_tools.parse_arguments(args)
        mock_load.return_value = "testquery"
        mock_specify.return_value = {"testkey": "testvalue"}
        tasks.run_command_with_arguments(args[1], args[2], parsed_args, self.uri)
        mock_query.assert_called_with(self.uri, "testquery", {"testkey": "testvalue"}, "testfile", ";", True)

    @unittest.mock.patch('pychado.queries.specify_list_parameters')
    @unittest.mock.patch('pychado.queries.load_list_query')
    @unittest.mock.patch('pychado.dbutils.query_to_file')
    def test_list_genedb_products(self, mock_query, mock_load, mock_specify):
        # Checks that the function listing GeneDB products is correctly called
        self.assertIs(mock_query, dbutils.query_to_file)
        self.assertIs(mock_load, queries.load_list_query)
        self.assertIs(mock_specify, queries.specify_list_parameters)
        args = ["chado", "list", "genedb_products", "-H", "-d", ";", "-o", "testfile", "testdb"]
        parsed_args = chado_tools.parse_arguments(args)
        mock_load.return_value = "testquery"
        mock_specify.return_value = {"testkey": "testvalue"}
        tasks.run_command_with_arguments(args[1], args[2], parsed_args, self.uri)
        mock_query.assert_called_with(self.uri, "testquery", {"testkey": "testvalue"}, "testfile", ";", True)

    @unittest.mock.patch('pychado.queries.specify_insert_parameters')
    @unittest.mock.patch('pychado.queries.load_insert_statement')
    @unittest.mock.patch('pychado.dbutils.connect_and_execute')
    def test_insert_organism(self, mock_statement, mock_load, mock_specify):
        # Checks that the function inserting organisms is correctly called
        self.assertIs(mock_statement, dbutils.connect_and_execute)
        self.assertIs(mock_load, queries.load_insert_statement)
        self.assertIs(mock_specify, queries.specify_insert_parameters)
        args = ["chado", "insert", "organism", "-g", "testgenus", "-s", "testspecies", "-a", "testorganism", "testdb"]
        parsed_args = chado_tools.parse_arguments(args)
        mock_load.return_value = "teststatement"
        mock_specify.return_value = {"testkey": "testvalue"}
        tasks.run_command_with_arguments(args[1], args[2], parsed_args, self.uri)
        mock_statement.assert_called_with(self.uri, "teststatement", {"testkey": "testvalue"})

    @unittest.mock.patch('pychado.queries.specify_delete_parameters')
    @unittest.mock.patch('pychado.queries.load_delete_statement')
    @unittest.mock.patch('pychado.dbutils.connect_and_execute')
    def test_delete_organism(self, mock_statement, mock_load, mock_specify):
        # Checks that the function deleting organisms is correctly called
        self.assertIs(mock_statement, dbutils.connect_and_execute)
        self.assertIs(mock_load, queries.load_delete_statement)
        self.assertIs(mock_specify, queries.specify_delete_parameters)
        args = ["chado", "delete", "organism", "-a", "testorganism", "testdb"]
        parsed_args = chado_tools.parse_arguments(args)
        mock_load.return_value = "teststatement"
        mock_specify.return_value = {"testkey": "testvalue"}
        tasks.run_command_with_arguments(args[1], args[2], parsed_args, self.uri)
        mock_statement.assert_called_with(self.uri, "teststatement", {"testkey": "testvalue"})

    @unittest.mock.patch('pychado.tasks.run_import_command')
    def test_run_import(self, mock_run):
        # Checks that database imports are correctly run
        self.assertIs(mock_run, tasks.run_import_command)
        args = ["chado", "import", "ontology", "-f", "testfile", "-A", "testauthority", "-F", "owl", "testdb"]
        parsed_args = chado_tools.parse_arguments(args)
        tasks.run_command_with_arguments(args[1], args[2], parsed_args, self.uri)
        mock_run.assert_called_with("ontology", parsed_args, self.uri)

    @unittest.mock.patch('pychado.utils.download_file')
    @unittest.mock.patch('pychado.io.load_ontology.OntologyLoader.load')
    def test_import_ontology(self, mock_import, mock_download):
        # Checks that the function importing an ontology into the database is correctly called
        self.assertIs(mock_import, load_ontology.OntologyLoader.load)
        self.assertIs(mock_download, utils.download_file)
        args = ["chado", "import", "ontology", "-f", "testfile", "-A", "testauthority", "-F", "owl", "testdb"]
        parsed_args = chado_tools.parse_arguments(args)
        tasks.run_import_command(args[2], parsed_args, self.uri)
        mock_download.assert_not_called()
        mock_import.assert_called_with("testfile", "owl", "testauthority")

        mock_download.reset_mock()
        mock_download.return_value = "downloaded_file"
        args = ["chado", "import", "ontology", "-u", "testurl", "-A", "testauthority", "-F", "owl", "testdb"]
        parsed_args = chado_tools.parse_arguments(args)
        tasks.run_import_command(args[2], parsed_args, self.uri)
        mock_download.assert_called_with("testurl")
        mock_import.assert_called_with("downloaded_file", "owl", "testauthority")


if __name__ == '__main__':
    unittest.main(verbosity=2, buffer=True)
