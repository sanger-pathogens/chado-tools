import unittest.mock
from .. import chado_tools, tasks, queries, dbutils, utils, ddl
from ..io import direct, ontology


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

        tasks.init("init")
        mock_set.assert_called()
        mock_reset.assert_not_called()
        mock_set.reset_mock()
        mock_reset.reset_mock()

        tasks.init("reset")
        mock_set.assert_not_called()
        mock_reset.assert_called()
        mock_set.reset_mock()
        mock_reset.reset_mock()

        tasks.init("non_existing_command")
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

    @unittest.mock.patch('pychado.dbutils.create_database')
    def test_create(self, mock_create):
        # Checks that the function creating and setting up a database is correctly called
        self.assertIs(mock_create, dbutils.create_database)
        args = ["chado", "admin", "create", "testdb"]
        parsed_args = chado_tools.parse_arguments(args)
        tasks.run_command_with_arguments(args[1], args[2], parsed_args, self.uri)
        mock_create.assert_called_with(self.uri)

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

    @unittest.mock.patch('pychado.tasks.run_setup_command')
    def test_run_setup(self, mock_run):
        # Checks that database setup is correctly run
        self.assertIs(mock_run, tasks.run_setup_command)
        args = ["chado", "admin", "setup", "-f", "testschema", "testdb"]
        parsed_args = chado_tools.parse_arguments(args)
        tasks.run_command_with_arguments(args[1], args[2], parsed_args, self.uri)
        mock_run.assert_called_with(parsed_args, self.uri)

    @unittest.mock.patch('pychado.ddl.AuditSchemaSetupClient')
    @unittest.mock.patch('pychado.ddl.PublicSchemaSetupClient')
    @unittest.mock.patch('pychado.utils.download_file')
    @unittest.mock.patch('pychado.dbutils.setup_database')
    def test_setup(self, mock_setup, mock_download, mock_create_public_schema, mock_create_audit_schema):
        # Checks that the function setting up a database schema is correctly called
        self.assertIs(mock_setup, dbutils.setup_database)
        self.assertIs(mock_download, utils.download_file)
        self.assertIs(mock_create_public_schema, ddl.PublicSchemaSetupClient)
        self.assertIs(mock_create_audit_schema, ddl.AuditSchemaSetupClient)

        args = ["chado", "admin", "setup", "-f", "testschema", "testdb"]
        parsed_args = chado_tools.parse_arguments(args)
        tasks.run_setup_command(parsed_args, self.uri)
        mock_download.assert_not_called()
        mock_setup.assert_called_with(self.uri, "testschema")

        mock_download.reset_mock()
        mock_download.return_value = "downloaded_schema"
        args = ["chado", "admin", "setup", "testdb"]
        parsed_args = chado_tools.parse_arguments(args)
        tasks.run_setup_command(parsed_args, self.uri)
        mock_download.assert_called()
        mock_setup.assert_called_with(self.uri, "downloaded_schema")

        mock_create_public_schema.reset_mock()
        mock_create_audit_schema.reset_mock()
        args = ["chado", "admin", "setup", "-s", "basic", "testdb"]
        parsed_args = chado_tools.parse_arguments(args)
        tasks.run_setup_command(parsed_args, self.uri)
        mock_create_public_schema.assert_called_with(self.uri)
        self.assertIn(unittest.mock.call().create(), mock_create_public_schema.mock_calls)
        mock_create_audit_schema.assert_not_called()

        mock_create_public_schema.reset_mock()
        mock_create_audit_schema.reset_mock()
        args = ["chado", "admin", "setup", "-s", "audit", "testdb"]
        parsed_args = chado_tools.parse_arguments(args)
        tasks.run_setup_command(parsed_args, self.uri)
        mock_create_public_schema.assert_not_called()
        mock_create_audit_schema.assert_called_with(self.uri)
        self.assertIn(unittest.mock.call().create(), mock_create_audit_schema.mock_calls)

    @unittest.mock.patch('pychado.tasks.run_grant_revoke_command')
    def test_run_grant(self, mock_run):
        # Checks that database access granting is correctly run
        self.assertIs(mock_run, tasks.run_grant_revoke_command)
        args = ["chado", "admin", "grant", "-r", "testrole", "-s", "testschema", "-w", "testdb"]
        parsed_args = chado_tools.parse_arguments(args)
        tasks.run_command_with_arguments(args[1], args[2], parsed_args, self.uri)
        mock_run.assert_called_with(parsed_args, self.uri, True)

        args = ["chado", "admin", "revoke", "-r", "testrole", "-s", "testschema", "testdb"]
        parsed_args = vars(chado_tools.parse_arguments(args))
        tasks.run_command_with_arguments(args[1], args[2], parsed_args, self.uri)
        mock_run.assert_called_with(parsed_args, self.uri, False)

    @unittest.mock.patch('pychado.ddl.RolesClient')
    def test_grant(self, mock_grant):
        # Checks that the function granting database access is correctly called
        self.assertIs(mock_grant, ddl.RolesClient)
        args = ["chado", "admin", "grant", "-r", "testrole", "-s", "testschema", "-w", "testdb"]
        parsed_args = chado_tools.parse_arguments(args)
        tasks.run_grant_revoke_command(parsed_args, self.uri, True)
        mock_grant.assert_called_with(self.uri)
        self.assertIn(unittest.mock.call().grant_or_revoke("testrole", "testschema", True, True),
                      mock_grant.mock_calls)

    @unittest.mock.patch('pychado.ddl.RolesClient')
    def test_revoke(self, mock_grant):
        # Checks that the function revoking database access is correctly called
        self.assertIs(mock_grant, ddl.RolesClient)
        args = ["chado", "admin", "revoke", "-r", "testrole", "-s", "testschema", "testdb"]
        parsed_args = chado_tools.parse_arguments(args)
        tasks.run_grant_revoke_command(parsed_args, self.uri, False)
        mock_grant.assert_called_with(self.uri)
        self.assertIn(unittest.mock.call().grant_or_revoke("testrole", "testschema", False, False),
                      mock_grant.mock_calls)

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
        mock_query.assert_called_with(self.uri, "testquery", "testfile", ";", True)
        # Query extracted from file
        args = ["chado", "query", "-d", ";", "-o", "testfile", "-f", "testqueryfile", "testdb"]
        parsed_args = chado_tools.parse_arguments(args)
        mock_read.return_value = "query_from_file"
        tasks.run_command_with_arguments(args[1], "", parsed_args, self.uri)
        mock_query.assert_called_with(self.uri, "query_from_file", "testfile", ";", False)

    @unittest.mock.patch('pychado.tasks.run_select_command')
    def test_run_select(self, mock_run):
        # Checks that database queries are correctly run
        self.assertIs(mock_run, tasks.run_select_command)
        args = ["chado", "extract", "organisms", "-H", "-d", ";", "-o", "testfile", "testdb"]
        parsed_args = chado_tools.parse_arguments(args)
        tasks.run_command_with_arguments(args[1], args[2], parsed_args, self.uri)
        mock_run.assert_called_with("organisms", parsed_args, self.uri)

    @unittest.mock.patch('pychado.dbutils.query_to_file')
    @unittest.mock.patch('pychado.queries.set_query_conditions')
    @unittest.mock.patch('pychado.queries.load_query')
    def test_extract_stats(self, mock_load, mock_set, mock_query):
        # Checks that the function providing database statistics is correctly called
        self.assertIs(mock_load, queries.load_query)
        self.assertIs(mock_set, queries.set_query_conditions)
        self.assertIs(mock_query, dbutils.query_to_file)

        args = ["chado", "extract", "stats", "--start_date", "teststartdate", "--end_date", "testenddate",
                "-a", "testorganism", "testdb"]
        parsed_args = chado_tools.parse_arguments(args)
        mock_load.return_value = "testquery"
        mock_set.return_value = "testquery_with_params"
        tasks.run_select_command(args[2], parsed_args, self.uri)
        mock_load.assert_called_with("stats")
        mock_set.assert_called_with("testquery", organism="testorganism", start_date="teststartdate",
                                    end_date="testenddate")
        mock_query.assert_called_with(self.uri, "testquery_with_params", "", "\t", False)

        args = ["chado", "extract", "stats", "-H", "-d", ";", "-o", "testfile", "--start_date", "teststartdate",
                "testdb"]
        parsed_args = chado_tools.parse_arguments(args)
        mock_load.return_value = "testquery"
        mock_set.return_value = "testquery_with_params"
        tasks.run_select_command(args[2], parsed_args, self.uri)
        mock_load.assert_called_with("stats")
        mock_set.assert_called_with("testquery", organism=None, start_date="teststartdate",
                                    end_date=utils.current_date())
        mock_query.assert_called_with(self.uri, "testquery_with_params", "testfile", ";", True)

    @unittest.mock.patch('pychado.dbutils.query_to_file')
    @unittest.mock.patch('pychado.queries.set_query_conditions')
    @unittest.mock.patch('pychado.queries.load_query')
    def test_extract_organisms(self, mock_load, mock_set, mock_query):
        # Checks that the function extracting organisms is correctly called
        self.assertIs(mock_load, queries.load_query)
        self.assertIs(mock_set, queries.set_query_conditions)
        self.assertIs(mock_query, dbutils.query_to_file)

        args = ["chado", "extract", "organisms", "testdb"]
        parsed_args = chado_tools.parse_arguments(args)
        mock_load.return_value = "testquery"
        mock_set.return_value = "testquery_with_params"
        tasks.run_select_command(args[2], parsed_args, self.uri)
        mock_load.assert_called_with("organisms")
        mock_set.assert_called_with("testquery")
        mock_query.assert_called_with(self.uri, "testquery_with_params", "", "\t", False)

        tasks.run_select_command("inexistent_specifier", parsed_args, self.uri)
        mock_set.assert_called_with("")

    @unittest.mock.patch('pychado.dbutils.query_to_file')
    @unittest.mock.patch('pychado.queries.set_query_conditions')
    @unittest.mock.patch('pychado.queries.load_query')
    def test_extract_cvterms(self, mock_load, mock_set, mock_query):
        # Checks that the function extracting CV terms is correctly called
        self.assertIs(mock_load, queries.load_query)
        self.assertIs(mock_set, queries.set_query_conditions)
        self.assertIs(mock_query, dbutils.query_to_file)

        args = ["chado", "extract", "cvterms", "--database", "testdatabase", "--vocabulary", "testvocabulary", "testdb"]
        parsed_args = chado_tools.parse_arguments(args)
        mock_load.return_value = "testquery"
        mock_set.return_value = "testquery_with_params"
        tasks.run_select_command(args[2], parsed_args, self.uri)
        mock_load.assert_called_with("cvterms")
        mock_set.assert_called_with("testquery", vocabulary="testvocabulary", database="testdatabase")
        mock_query.assert_called_with(self.uri, "testquery_with_params", "", "\t", False)

    @unittest.mock.patch('pychado.dbutils.query_to_file')
    @unittest.mock.patch('pychado.queries.set_query_conditions')
    @unittest.mock.patch('pychado.queries.load_query')
    def test_extract_genedb_products(self, mock_load, mock_set, mock_query):
        # Checks that the function extracting GeneDB products is correctly called
        self.assertIs(mock_load, queries.load_query)
        self.assertIs(mock_set, queries.set_query_conditions)
        self.assertIs(mock_query, dbutils.query_to_file)

        args = ["chado", "extract", "genedb_products", "-a", "testorganism", "testdb"]
        parsed_args = chado_tools.parse_arguments(args)
        mock_load.return_value = "testquery"
        mock_set.return_value = "testquery_with_params"
        tasks.run_select_command(args[2], parsed_args, self.uri)
        mock_load.assert_called_with("genedb_products")
        mock_set.assert_called_with("testquery", organism="testorganism")
        mock_query.assert_called_with(self.uri, "testquery_with_params", "", "\t", False)

    @unittest.mock.patch('pychado.tasks.run_insert_command')
    def test_run_insert(self, mock_run):
        # Checks that database inserts are correctly run
        self.assertIs(mock_run, tasks.run_insert_command)
        args = ["chado", "insert", "organism", "-g", "testgenus", "-s", "testspecies", "-a", "testorganism", "testdb"]
        parsed_args = chado_tools.parse_arguments(args)
        tasks.run_command_with_arguments(args[1], args[2], parsed_args, self.uri)
        mock_run.assert_called_with("organism", parsed_args, self.uri)

    @unittest.mock.patch('pychado.tasks.run_delete_command')
    def test_run_delete(self, mock_run):
        # Checks that database inserts are correctly run
        self.assertIs(mock_run, tasks.run_delete_command)
        args = ["chado", "delete", "organism", "-a", "testorganism", "testdb"]
        parsed_args = chado_tools.parse_arguments(args)
        tasks.run_command_with_arguments(args[1], args[2], parsed_args, self.uri)
        mock_run.assert_called_with("organism", parsed_args, self.uri)

    @unittest.mock.patch('pychado.io.direct.DirectIOClient.insert_organism')
    def test_insert_organism(self, mock_insert):
        # Checks that the function inserting organisms is correctly called
        self.assertIs(mock_insert, direct.DirectIOClient.insert_organism)
        args = ["chado", "insert", "organism", "-g", "testgenus", "-s", "testspecies", "-a", "testorganism", "testdb"]
        parsed_args = chado_tools.parse_arguments(args)

        tasks.run_insert_command(args[2], parsed_args, self.uri)
        mock_insert.assert_called_with("testgenus", "testspecies", "testorganism", None, None, None)

        mock_insert.reset_mock()
        tasks.run_insert_command("inexistent_specifier", parsed_args, self.uri)
        mock_insert.assert_not_called()

    @unittest.mock.patch('pychado.io.direct.DirectIOClient.delete_organism')
    def test_delete_organism(self, mock_delete):
        # Checks that the function inserting organisms is correctly called
        self.assertIs(mock_delete, direct.DirectIOClient.delete_organism)
        args = ["chado", "delete", "organism", "-a", "testorganism", "testdb"]
        parsed_args = chado_tools.parse_arguments(args)

        tasks.run_delete_command(args[2], parsed_args, self.uri)
        mock_delete.assert_called_with("testorganism")

        mock_delete.reset_mock()
        tasks.run_delete_command("inexistent_specifier", parsed_args, self.uri)
        mock_delete.assert_not_called()

    @unittest.mock.patch('pychado.tasks.run_import_command')
    def test_run_import(self, mock_run):
        # Checks that database imports are correctly run
        self.assertIs(mock_run, tasks.run_import_command)
        args = ["chado", "import", "ontology", "-f", "testfile", "-A", "testauthority", "-F", "owl", "testdb"]
        parsed_args = chado_tools.parse_arguments(args)
        tasks.run_command_with_arguments(args[1], args[2], parsed_args, self.uri)
        mock_run.assert_called_with("ontology", parsed_args, self.uri)

    @unittest.mock.patch('pychado.utils.download_file')
    @unittest.mock.patch('pychado.io.ontology.OntologyClient.load')
    def test_import_ontology(self, mock_import, mock_download):
        # Checks that the function importing an ontology into the database is correctly called
        self.assertIs(mock_import, ontology.OntologyClient.load)
        self.assertIs(mock_download, utils.download_file)
        args = ["chado", "import", "ontology", "-f", "testfile", "-A", "testauthority", "-F", "owl", "testdb"]
        parsed_args = chado_tools.parse_arguments(args)
        tasks.run_import_command(args[2], parsed_args, self.uri)
        mock_download.assert_not_called()
        mock_import.assert_called_with("testfile", "owl", "testauthority")

        mock_download.reset_mock()
        mock_download.return_value = "downloaded_file"
        args = ["chado", "import", "ontology", "-u", "testurl", "-A", "testauthority", "testdb"]
        parsed_args = chado_tools.parse_arguments(args)
        tasks.run_import_command(args[2], parsed_args, self.uri)
        mock_download.assert_called_with("testurl")
        mock_import.assert_called_with("downloaded_file", "obo", "testauthority")

        mock_import.reset_mock()
        tasks.run_import_command("inexistent_specifier", parsed_args, self.uri)
        mock_import.assert_not_called()


if __name__ == '__main__':
    unittest.main(verbosity=2, buffer=True)
