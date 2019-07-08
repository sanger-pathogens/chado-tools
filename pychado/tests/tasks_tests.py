import unittest.mock
from .. import chado_tools, tasks, queries, dbutils, utils, ddl
from ..io import direct, essentials, ontology, fasta, gff, gaf


class TestTasks(unittest.TestCase):
    """Tests the functionality of all commands of the CHADO program"""

    def setUp(self):
        connection_params = dbutils.get_connection_parameters("", False, "testdb")
        self.uri = dbutils.generate_uri(connection_params)

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

    @unittest.mock.patch('pychado.ddl.AuditBackupSchemaSetupClient')
    @unittest.mock.patch('pychado.ddl.AuditSchemaSetupClient')
    @unittest.mock.patch('pychado.ddl.PublicSchemaSetupClient')
    @unittest.mock.patch('pychado.utils.download_file')
    @unittest.mock.patch('pychado.dbutils.setup_database')
    def test_setup(self, mock_setup, mock_download, mock_public_schema_client, mock_audit_schema_client,
                   mock_backup_schema_client):
        # Checks that the function setting up a database schema is correctly called
        self.assertIs(mock_setup, dbutils.setup_database)
        self.assertIs(mock_download, utils.download_file)
        self.assertIs(mock_public_schema_client, ddl.PublicSchemaSetupClient)
        self.assertIs(mock_audit_schema_client, ddl.AuditSchemaSetupClient)
        self.assertIs(mock_backup_schema_client, ddl.AuditBackupSchemaSetupClient)

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

        mock_public_schema_client.reset_mock()
        mock_audit_schema_client.reset_mock()
        mock_backup_schema_client.reset_mock()
        args = ["chado", "admin", "setup", "-s", "basic", "testdb"]
        parsed_args = chado_tools.parse_arguments(args)
        tasks.run_setup_command(parsed_args, self.uri)
        mock_public_schema_client.assert_called_with(self.uri)
        mock_backup_schema_client.assert_not_called()
        mock_audit_schema_client.assert_not_called()
        self.assertIn(unittest.mock.call().create(), mock_public_schema_client.mock_calls)

        mock_public_schema_client.reset_mock()
        mock_audit_schema_client.reset_mock()
        mock_backup_schema_client.reset_mock()
        args = ["chado", "admin", "setup", "-s", "audit", "testdb"]
        parsed_args = chado_tools.parse_arguments(args)
        tasks.run_setup_command(parsed_args, self.uri)
        mock_public_schema_client.assert_not_called()
        mock_audit_schema_client.assert_called_with(self.uri)
        mock_backup_schema_client.assert_not_called()
        self.assertIn(unittest.mock.call().create(), mock_audit_schema_client.mock_calls)

        mock_public_schema_client.reset_mock()
        mock_audit_schema_client.reset_mock()
        mock_backup_schema_client.reset_mock()
        args = ["chado", "admin", "setup", "-s", "audit_backup", "testdb"]
        parsed_args = chado_tools.parse_arguments(args)
        tasks.run_setup_command(parsed_args, self.uri)
        mock_public_schema_client.assert_not_called()
        mock_audit_schema_client.assert_not_called()
        mock_backup_schema_client.assert_called_with(self.uri)
        self.assertIn(unittest.mock.call().create(), mock_backup_schema_client.mock_calls)

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
    def test_grant(self, mock_client):
        # Checks that the function granting database access is correctly called
        self.assertIs(mock_client, ddl.RolesClient)
        args = ["chado", "admin", "grant", "-r", "testrole", "-s", "testschema", "-w", "testdb"]
        parsed_args = chado_tools.parse_arguments(args)
        tasks.run_grant_revoke_command(parsed_args, self.uri, True)
        mock_client.assert_called_with(self.uri)
        self.assertIn(unittest.mock.call().grant_or_revoke("testrole", "testschema", True, True),
                      mock_client.mock_calls)

    @unittest.mock.patch('pychado.ddl.RolesClient')
    def test_revoke(self, mock_client):
        # Checks that the function revoking database access is correctly called
        self.assertIs(mock_client, ddl.RolesClient)
        args = ["chado", "admin", "revoke", "-r", "testrole", "-s", "testschema", "testdb"]
        parsed_args = chado_tools.parse_arguments(args)
        tasks.run_grant_revoke_command(parsed_args, self.uri, False)
        mock_client.assert_called_with(self.uri)
        self.assertIn(unittest.mock.call().grant_or_revoke("testrole", "testschema", False, False),
                      mock_client.mock_calls)

    @unittest.mock.patch('pychado.tasks.run_query_command')
    def test_run_query(self, mock_run):
        # Checks that database queries are correctly run
        self.assertIs(mock_run, tasks.run_query_command)
        args = ["chado", "query", "-H", "-d", ";", "-o", "testfile", "-q", "testquery", "testdb"]
        parsed_args = chado_tools.parse_arguments(args)
        tasks.run_command_with_arguments(args[1], args[2], parsed_args, self.uri)
        mock_run.assert_called_with(parsed_args, self.uri)

    @unittest.mock.patch('pychado.dbutils.query_and_print')
    @unittest.mock.patch('pychado.utils.read_text')
    def test_query(self, mock_read, mock_query):
        # Checks that the function querying a database is correctly called
        self.assertIs(mock_read, utils.read_text)
        self.assertIs(mock_query, dbutils.query_and_print)

        # Direct query
        args = ["chado", "query", "-H", "-d", ";", "-o", "testfile", "-F", "json", "-q", "testquery", "testdb"]
        parsed_args = chado_tools.parse_arguments(args)
        mock_query.return_value = ['a', 'b', 'c']
        tasks.run_query_command(parsed_args, self.uri)
        mock_query.assert_called_with(self.uri, "testquery", "testfile", "json", True, ";")

        # Query extracted from file
        args = ["chado", "query", "-d", "\t", "-o", "otherfile", "-f", "testqueryfile", "testdb"]
        parsed_args = chado_tools.parse_arguments(args)
        mock_read.return_value = "query_from_file"
        tasks.run_query_command(parsed_args, self.uri)
        mock_query.assert_called_with(self.uri, "query_from_file", "otherfile", "csv", False, "\t")

    @unittest.mock.patch('pychado.tasks.run_execute_command')
    def test_run_execute(self, mock_run):
        # Checks that calls to database functions are correctly run
        self.assertIs(mock_run, tasks.run_execute_command)
        args = ["chado", "execute", "audit_backup", "--date", "testdate", "testdb"]
        parsed_args = chado_tools.parse_arguments(args)
        tasks.run_command_with_arguments(args[1], args[2], parsed_args, self.uri)
        mock_run.assert_called_with("audit_backup", parsed_args, self.uri)

    @unittest.mock.patch('pychado.ddl.AuditBackupSchemaSetupClient')
    def test_execute_audit_backup(self, mock_backup_schema_client):
        # Checks that the function calling the backup process of the audit schema is correctly called
        self.assertIs(mock_backup_schema_client, ddl.AuditBackupSchemaSetupClient)
        args = ["chado", "execute", "audit_backup", "--date", "testdate", "testdb"]
        parsed_args = chado_tools.parse_arguments(args)
        tasks.run_execute_command(args[2], parsed_args, self.uri)
        mock_backup_schema_client.assert_called_with(self.uri)
        self.assertIn(unittest.mock.call().execute_backup_function("testdate"), mock_backup_schema_client.mock_calls)

    @unittest.mock.patch('pychado.tasks.run_select_command')
    def test_run_select(self, mock_run):
        # Checks that database queries are correctly run
        self.assertIs(mock_run, tasks.run_select_command)
        args = ["chado", "extract", "organisms", "-H", "-d", ";", "-o", "testfile", "testdb"]
        parsed_args = chado_tools.parse_arguments(args)
        tasks.run_command_with_arguments(args[1], args[2], parsed_args, self.uri)
        mock_run.assert_called_with("organisms", parsed_args, self.uri)

    @unittest.mock.patch('pychado.dbutils.query_and_print')
    @unittest.mock.patch('pychado.queries.set_query_conditions')
    @unittest.mock.patch('pychado.queries.load_query')
    def test_extract(self, mock_load, mock_set, mock_query):
        # Checks the general behaviour of the function extracting data via SQL queries
        self.assertIs(mock_load, queries.load_query)
        self.assertIs(mock_set, queries.set_query_conditions)
        self.assertIs(mock_query, dbutils.query_and_print)

        args = ["chado", "extract", "organisms", "testdb"]
        parsed_args = chado_tools.parse_arguments(args)
        tasks.run_select_command("inexistent_specifier", parsed_args, self.uri)
        mock_load.assert_called_with("inexistent_specifier")
        mock_set.assert_not_called()

        parsed_args.public_only = True
        tasks.run_select_command("inexistent_specifier", parsed_args, self.uri)
        mock_load.assert_called_with("public_inexistent_specifier")
        mock_set.assert_not_called()

    @unittest.mock.patch('pychado.dbutils.query_and_print')
    @unittest.mock.patch('pychado.queries.set_query_conditions')
    @unittest.mock.patch('pychado.queries.load_query')
    def test_extract_annotation_updates(self, mock_load, mock_set, mock_query):
        # Checks that the function extracting annotation updates is correctly called
        self.assertIs(mock_load, queries.load_query)
        self.assertIs(mock_set, queries.set_query_conditions)
        self.assertIs(mock_query, dbutils.query_and_print)

        args = ["chado", "extract", "annotation_updates", "--start_date", "teststartdate", "--end_date", "testenddate",
                "-a", "testorganism", "testdb"]
        parsed_args = chado_tools.parse_arguments(args)
        mock_load.return_value = "testquery"
        mock_set.return_value = "testquery_with_params"

        tasks.run_select_command(args[2], parsed_args, self.uri)
        mock_load.assert_called_with("annotation_updates")
        mock_set.assert_called_with("testquery", organism="testorganism", start_date="teststartdate",
                                    end_date="testenddate")
        mock_query.assert_called_with(self.uri, "testquery_with_params", "", "csv", False, "\t")

        args = ["chado", "extract", "annotation_updates", "-H", "-d", ";", "-o", "testfile", "--start_date",
                "teststartdate", "--public_only", "testdb"]
        parsed_args = chado_tools.parse_arguments(args)

        tasks.run_select_command(args[2], parsed_args, self.uri)
        mock_load.assert_called_with("public_annotation_updates")
        mock_set.assert_called_with("testquery", organism=None, start_date="teststartdate",
                                    end_date=utils.current_date())
        mock_query.assert_called_with(self.uri, "testquery_with_params", "testfile", "csv", True, ";")

    @unittest.mock.patch('pychado.dbutils.query_and_print')
    @unittest.mock.patch('pychado.queries.set_query_conditions')
    @unittest.mock.patch('pychado.queries.load_query')
    def test_extract_organisms(self, mock_load, mock_set, mock_query):
        # Checks that the function extracting organisms is correctly called
        self.assertIs(mock_load, queries.load_query)
        self.assertIs(mock_set, queries.set_query_conditions)
        self.assertIs(mock_query, dbutils.query_and_print)

        args = ["chado", "extract", "organisms", "--public_only", "testdb"]
        parsed_args = chado_tools.parse_arguments(args)
        mock_load.return_value = "testquery"

        tasks.run_select_command(args[2], parsed_args, self.uri)
        mock_load.assert_called_with("public_organisms")
        mock_set.assert_not_called()
        mock_query.assert_called_with(self.uri, "testquery", "", "csv", False, "\t")

        args = ["chado", "extract", "organisms", "testdb"]
        parsed_args = chado_tools.parse_arguments(args)

        tasks.run_select_command(args[2], parsed_args, self.uri)
        mock_load.assert_called_with("organisms")
        mock_set.assert_not_called()

    @unittest.mock.patch('pychado.dbutils.query_and_print')
    @unittest.mock.patch('pychado.queries.set_query_conditions')
    @unittest.mock.patch('pychado.queries.load_query')
    def test_extract_cvterms(self, mock_load, mock_set, mock_query):
        # Checks that the function extracting CV terms is correctly called
        self.assertIs(mock_load, queries.load_query)
        self.assertIs(mock_set, queries.set_query_conditions)
        self.assertIs(mock_query, dbutils.query_and_print)

        args = ["chado", "extract", "cvterms", "--database", "testdatabase", "--vocabulary", "testvocabulary", "testdb"]
        parsed_args = chado_tools.parse_arguments(args)
        mock_load.return_value = "testquery"
        mock_set.return_value = "testquery_with_params"

        tasks.run_select_command(args[2], parsed_args, self.uri)
        mock_load.assert_called_with("cvterms")
        mock_set.assert_called_with("testquery", vocabulary="testvocabulary", database="testdatabase")
        mock_query.assert_called_with(self.uri, "testquery_with_params", "", "csv", False, "\t")

    @unittest.mock.patch('pychado.dbutils.query_and_print')
    @unittest.mock.patch('pychado.queries.set_query_conditions')
    @unittest.mock.patch('pychado.queries.load_query')
    def test_extract_gene_products(self, mock_load, mock_set, mock_query):
        # Checks that the function extracting gene products is correctly called
        self.assertIs(mock_load, queries.load_query)
        self.assertIs(mock_set, queries.set_query_conditions)
        self.assertIs(mock_query, dbutils.query_and_print)

        args = ["chado", "extract", "gene_products", "-a", "testorganism", "testdb"]
        parsed_args = chado_tools.parse_arguments(args)
        mock_load.return_value = "testquery"
        mock_set.return_value = "testquery_with_params"

        tasks.run_select_command(args[2], parsed_args, self.uri)
        mock_load.assert_called_with("gene_products")
        mock_set.assert_called_with("testquery", organism="testorganism")
        mock_query.assert_called_with(self.uri, "testquery_with_params", "", "csv", False, "\t")

        args = ["chado", "extract", "gene_products", "--public_only", "testdb"]
        parsed_args = chado_tools.parse_arguments(args)
        tasks.run_select_command(args[2], parsed_args, self.uri)
        mock_load.assert_called_with("public_gene_products")
        mock_set.assert_called_with("testquery", organism=None)
        mock_query.assert_called_with(self.uri, "testquery_with_params", "", "csv", False, "\t")

    @unittest.mock.patch('pychado.dbutils.query_and_print')
    @unittest.mock.patch('pychado.queries.set_query_conditions')
    @unittest.mock.patch('pychado.queries.load_query')
    def test_extract_curator_comments(self, mock_load, mock_set, mock_query):
        # Checks that the function extracting curator comments on features is correctly called
        self.assertIs(mock_load, queries.load_query)
        self.assertIs(mock_set, queries.set_query_conditions)
        self.assertIs(mock_query, dbutils.query_and_print)

        args = ["chado", "extract", "curator_comments", "-a", "testorganism", "testdb"]
        parsed_args = chado_tools.parse_arguments(args)
        mock_load.return_value = "testquery"
        mock_set.return_value = "testquery_with_params"

        tasks.run_select_command(args[2], parsed_args, self.uri)
        mock_load.assert_called_with("curator_comments")
        mock_set.assert_called_with("testquery", organism="testorganism")
        mock_query.assert_called_with(self.uri, "testquery_with_params", "", "csv", False, "\t")

        args = ["chado", "extract", "curator_comments", "--public_only", "testdb"]
        parsed_args = chado_tools.parse_arguments(args)
        tasks.run_select_command(args[2], parsed_args, self.uri)
        mock_load.assert_called_with("public_curator_comments")
        mock_set.assert_called_with("testquery", organism=None)
        mock_query.assert_called_with(self.uri, "testquery_with_params", "", "csv", False, "\t")

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

    @unittest.mock.patch('pychado.io.direct.DirectIOClient')
    def test_insert_organism(self, mock_client):
        # Checks that the function inserting organisms is correctly called
        self.assertIs(mock_client, direct.DirectIOClient)
        args = ["chado", "insert", "organism", "-g", "testgenus", "-s", "testspecies", "-a", "testabbreviation",
                "--common_name", "testname", "-i", "teststrain", "--comment", "testcomment", "--genome_version", "5",
                "--taxon_id", "1234", "--wikidata_id", "Q9876", "testdb"]
        parsed_args = chado_tools.parse_arguments(args)

        tasks.run_insert_command(args[2], parsed_args, self.uri)
        mock_client.assert_called_with(self.uri, False)
        self.assertIn(unittest.mock.call().insert_organism("testgenus", "testspecies", "testabbreviation",
                                                           "testname", "teststrain", "testcomment", "5", "1234",
                                                           "Q9876"), mock_client.mock_calls)

        mock_client.reset_mock()
        tasks.run_insert_command("inexistent_specifier", parsed_args, self.uri)
        self.assertEqual([unittest.mock.call(self.uri, False)], mock_client.mock_calls)

    @unittest.mock.patch('pychado.io.direct.DirectIOClient')
    def test_delete_organism(self, mock_client):
        # Checks that the function inserting organisms is correctly called
        self.assertIs(mock_client, direct.DirectIOClient)
        args = ["chado", "delete", "organism", "-a", "testorganism", "testdb"]
        parsed_args = chado_tools.parse_arguments(args)

        tasks.run_delete_command(args[2], parsed_args, self.uri)
        mock_client.assert_called_with(self.uri, False)
        self.assertIn(unittest.mock.call().delete_organism("testorganism"), mock_client.mock_calls)

        mock_client.reset_mock()
        tasks.run_delete_command("inexistent_specifier", parsed_args, self.uri)
        self.assertEqual([unittest.mock.call(self.uri, False)], mock_client.mock_calls)

    @unittest.mock.patch('pychado.tasks.run_import_command')
    def test_run_import(self, mock_run):
        # Checks that database imports are correctly run
        self.assertIs(mock_run, tasks.run_import_command)
        args = ["chado", "import", "essentials", "testdb"]
        parsed_args = chado_tools.parse_arguments(args)
        tasks.run_command_with_arguments(args[1], args[2], parsed_args, self.uri)
        mock_run.assert_called_with("essentials", parsed_args, self.uri)

    @unittest.mock.patch('pychado.io.essentials.EssentialsClient')
    def test_import_essentials(self, mock_client):
        # Checks that the function importing essentials into the database is correctly called
        self.assertIs(mock_client, essentials.EssentialsClient)
        args = ["chado", "import", "essentials", "testdb"]
        parsed_args = chado_tools.parse_arguments(args)
        tasks.run_import_command(args[2], parsed_args, self.uri)
        mock_client.assert_called_with(self.uri, False)
        self.assertIn(unittest.mock.call().load(), mock_client.mock_calls)

        mock_client.reset_mock()
        tasks.run_import_command("inexistent_specifier", parsed_args, self.uri)
        mock_client.assert_not_called()

    @unittest.mock.patch('pychado.utils.download_file')
    @unittest.mock.patch('pychado.io.ontology.OntologyClient')
    def test_import_ontology(self, mock_client, mock_download):
        # Checks that the function importing an ontology into the database is correctly called
        self.assertIs(mock_client, ontology.OntologyClient)
        self.assertIs(mock_download, utils.download_file)
        args = ["chado", "import", "ontology", "-f", "testfile", "-A", "testauthority", "-F", "owl", "testdb"]
        parsed_args = chado_tools.parse_arguments(args)
        tasks.run_import_command(args[2], parsed_args, self.uri)
        mock_download.assert_not_called()
        mock_client.assert_called_with(self.uri, False)
        self.assertIn(unittest.mock.call().load("testfile", "owl", "testauthority"), mock_client.mock_calls)

        mock_client.reset_mock()
        mock_download.return_value = "downloaded_file"
        args = ["chado", "import", "ontology", "-V", "-u", "testurl", "-A", "testauthority", "testdb"]
        parsed_args = chado_tools.parse_arguments(args)
        tasks.run_import_command(args[2], parsed_args, self.uri)
        mock_download.assert_called_with("testurl")
        mock_client.assert_called_with(self.uri, True)
        self.assertIn(unittest.mock.call().load("downloaded_file", "obo", "testauthority"), mock_client.mock_calls)

    @unittest.mock.patch('pychado.io.gff.GFFImportClient')
    def test_import_gff(self, mock_client):
        # Checks that the function importing a GFF file into the database is correctly called
        self.assertIs(mock_client, gff.GFFImportClient)
        args = ["chado", "import", "gff", "-f", "testfile", "-a", "testorganism", "--fasta", "testfasta",
                "-t", "contig", "--fresh_load", "--force", "--full_genome", "testdb"]
        parsed_args = chado_tools.parse_arguments(args)
        tasks.run_import_command(args[2], parsed_args, self.uri)
        mock_client.assert_called_with(self.uri, False)
        self.assertIn(unittest.mock.call().load("testfile", "testorganism", "testfasta", "contig",
                                                True, True, True, False), mock_client.mock_calls)

    @unittest.mock.patch('pychado.io.fasta.FastaImportClient')
    def test_import_fasta(self, mock_client):
        # Checks that the function importing a FASTA file into the database is correctly called
        self.assertIs(mock_client, fasta.FastaImportClient)
        args = ["chado", "import", "fasta", "-f", "testfile", "-a", "testorganism", "-t", "contig", "testdb"]
        parsed_args = chado_tools.parse_arguments(args)
        tasks.run_import_command(args[2], parsed_args, self.uri)
        mock_client.assert_called_with(self.uri, False)
        self.assertIn(unittest.mock.call().load("testfile", "testorganism", "contig"), mock_client.mock_calls)

    @unittest.mock.patch('pychado.io.gaf.GAFImportClient')
    def test_import_gaf(self, mock_client):
        # Checks that the function importing a GAF file into the database is correctly called
        self.assertIs(mock_client, gaf.GAFImportClient)
        args = ["chado", "import", "gaf", "-f", "testfile", "-a", "testorganism", "-L", "protein", "testdb"]
        parsed_args = chado_tools.parse_arguments(args)
        tasks.run_import_command(args[2], parsed_args, self.uri)
        mock_client.assert_called_with(self.uri, False)
        self.assertIn(unittest.mock.call().load("testfile", "testorganism", "protein"), mock_client.mock_calls)

    @unittest.mock.patch('pychado.tasks.run_export_command')
    def test_run_export(self, mock_run):
        # Checks that database exports are correctly run
        self.assertIs(mock_run, tasks.run_export_command)
        args = ["chado", "export", "fasta", "-f", "testfile", "-a", "testorganism", "-t", "proteins", "testdb"]
        parsed_args = chado_tools.parse_arguments(args)
        tasks.run_command_with_arguments(args[1], args[2], parsed_args, self.uri)
        mock_run.assert_called_with("fasta", parsed_args, self.uri)

    @unittest.mock.patch('pychado.io.fasta.FastaExportClient')
    def test_export_fasta(self, mock_client):
        # Checks that the function exporting sequences from the database to a FASTA file is correctly called
        self.assertIs(mock_client, fasta.FastaExportClient)
        args = ["chado", "export", "fasta", "-f", "testfile", "-a", "testorganism", "-t", "proteins",
                "-r", "testrelease", "testdb"]
        parsed_args = chado_tools.parse_arguments(args)
        tasks.run_export_command(args[2], parsed_args, self.uri)
        mock_client.assert_called_with(self.uri, False)
        self.assertIn(unittest.mock.call().export("testfile", "testorganism", "proteins", "testrelease", False),
                      mock_client.mock_calls)

    @unittest.mock.patch('pychado.io.gff.GFFExportClient')
    def test_export_gff(self, mock_client):
        # Checks that the function exporting genomic data from the database to a GFF file is correctly called
        self.assertIs(mock_client, gff.GFFExportClient)
        args = ["chado", "export", "gff", "-f", "testfile", "-a", "testorganism", "--export_fasta", "--fasta_file",
                "testfasta", "testdb"]
        parsed_args = chado_tools.parse_arguments(args)
        tasks.run_export_command(args[2], parsed_args, self.uri)
        mock_client.assert_called_with(self.uri, False)
        self.assertIn(unittest.mock.call().export("testfile", "testorganism", True, "testfasta", False),
                      mock_client.mock_calls)

    @unittest.mock.patch('pychado.io.gaf.GAFExportClient')
    def test_export_gaf(self, mock_client):
        # Checks that the function exporting gene annotation data from the database to a GAF file is correctly called
        self.assertIs(mock_client, gaf.GAFExportClient)
        args = ["chado", "export", "gaf", "-f", "testfile", "-a", "testorganism", "-A", "testauthority",
                "-L", "protein", "testdb"]
        parsed_args = chado_tools.parse_arguments(args)
        tasks.run_export_command(args[2], parsed_args, self.uri)
        mock_client.assert_called_with(self.uri, False)
        self.assertIn(unittest.mock.call().export("testfile", "testorganism", "testauthority", "protein", False),
                      mock_client.mock_calls)


if __name__ == '__main__':
    unittest.main(verbosity=2, buffer=True)
