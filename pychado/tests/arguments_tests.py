import unittest
from terminal import chado_tools


class TestCommands(unittest.TestCase):
    """Tests if all implemented commands and sub-commands are available through the entry point"""

    def test_setup_commands(self):
        commands = chado_tools.setup_commands()
        self.assertIn("init", commands)
        self.assertIn("reset", commands)
        self.assertNotIn("non_existent_command", commands)

    def test_general_commands(self):
        commands = chado_tools.general_commands()
        self.assertIn("connect", commands)
        self.assertIn("query", commands)
        self.assertIn("stats", commands)
        self.assertNotIn("non_existent_command", commands)

    def test_wrapper_commands(self):
        commands = chado_tools.wrapper_commands()
        self.assertIn("list", commands)
        self.assertIn("insert", commands)
        self.assertIn("delete", commands)
        self.assertIn("import", commands)
        self.assertIn("admin", commands)
        self.assertNotIn("non_existent_command", commands)

    def test_admin_commands(self):
        commands = chado_tools.admin_commands()
        self.assertIn("create", commands)
        self.assertIn("drop", commands)
        self.assertIn("dump", commands)
        self.assertIn("restore", commands)

    def test_list_commands(self):
        commands = chado_tools.list_commands()
        self.assertIn("organisms", commands)
        self.assertIn("cvterms", commands)
        self.assertIn("genedb_products", commands)

    def test_insert_commands(self):
        commands = chado_tools.insert_commands()
        self.assertIn("organism", commands)

    def test_delete_commands(self):
        commands = chado_tools.delete_commands()
        self.assertIn("organism", commands)

    def test_import_commands(self):
        commands = chado_tools.import_commands()
        self.assertIn("ontology", commands)


class TestArguments(unittest.TestCase):
    """Tests if input arguments are parsed correctly"""

    def test_connect_args(self):
        # Tests if the command line arguments for the subcommand 'chado connect' are parsed correctly
        args = ["chado", "connect", "-c", "testconfig", "-V", "testdb"]
        parsed_args = vars(chado_tools.parse_arguments(args))
        self.assertEqual(parsed_args["config"], "testconfig")
        self.assertEqual(parsed_args["dbname"], "testdb")
        self.assertTrue(parsed_args["verbose"])

        # Test the default values
        args = ["chado", "connect", "testdb"]
        parsed_args = vars(chado_tools.parse_arguments(args))
        self.assertEqual(parsed_args["config"], "")
        self.assertFalse(parsed_args["verbose"])
        self.assertNotIn("non_existent_argument", parsed_args)

    def test_create_args(self):
        # Tests if the command line arguments for the subcommand 'chado admin create' are parsed correctly
        args = ["chado", "admin", "create", "-s", "testschema", "testdb"]
        parsed_args = vars(chado_tools.parse_arguments(args))
        self.assertEqual(parsed_args["dbname"], "testdb")
        self.assertEqual(parsed_args["schema"], "testschema")

    def test_drop_args(self):
        # Tests if the command line arguments for the subcommand 'chado admin drop' are parsed correctly
        args = ["chado", "admin", "drop", "testdb"]
        parsed_args = vars(chado_tools.parse_arguments(args))
        self.assertEqual(parsed_args["dbname"], "testdb")

    def test_dump_args(self):
        # Tests if the command line arguments for the subcommand 'chado admin dump' are parsed correctly
        args = ["chado", "admin", "dump", "testdb", "testarchive"]
        parsed_args = vars(chado_tools.parse_arguments(args))
        self.assertEqual(parsed_args["dbname"], "testdb")
        self.assertEqual(parsed_args["archive"], "testarchive")

    def test_restore_args(self):
        # Tests if the command line arguments for the subcommand 'chado admin restore' are parsed correctly
        args = ["chado", "admin", "restore", "testdb", "testarchive"]
        parsed_args = vars(chado_tools.parse_arguments(args))
        self.assertEqual(parsed_args["dbname"], "testdb")
        self.assertEqual(parsed_args["archive"], "testarchive")

    def test_query_args(self):
        # Tests if the command line arguments for the subcommand 'chado query' are parsed correctly
        args = ["chado", "query", "-H", "-d", ";", "-o", "testfile", "-q", "testquery", "testdb"]
        parsed_args = vars(chado_tools.parse_arguments(args))
        self.assertTrue(parsed_args["include_header"])
        self.assertEqual(parsed_args["delimiter"], ";")
        self.assertEqual(parsed_args["output_file"], "testfile")
        self.assertEqual(parsed_args["query"], "testquery")
        self.assertEqual(parsed_args["input_file"], "")
        self.assertEqual(parsed_args["dbname"], "testdb")

        # Test the default values / alternatives
        args = ["chado", "query", "-f", "testqueryfile", "testdb"]
        parsed_args = vars(chado_tools.parse_arguments(args))
        self.assertFalse(parsed_args["include_header"])
        self.assertEqual(parsed_args["delimiter"], "\t")
        self.assertEqual(parsed_args["output_file"], "")
        self.assertEqual(parsed_args["query"], "")
        self.assertEqual(parsed_args["input_file"], "testqueryfile")

    def test_stats_args(self):
        # Tests if the command line arguments for the subcommand 'chado stats' are parsed correctly
        args = ["chado", "stats", "-H", "-d", ";", "-o", "testfile", "-a", "testorganism",
                "--start_date", "testdate", "--end_date", "testdate2", "testdb"]
        parsed_args = vars(chado_tools.parse_arguments(args))
        self.assertTrue(parsed_args["include_header"])
        self.assertEqual(parsed_args["delimiter"], ";")
        self.assertEqual(parsed_args["output_file"], "testfile")
        self.assertEqual(parsed_args["organism"], "testorganism")
        self.assertEqual(parsed_args["start_date"], "testdate")
        self.assertEqual(parsed_args["end_date"], "testdate2")
        self.assertEqual(parsed_args["dbname"], "testdb")

        # Test the default values
        args = ["chado", "stats", "--start_date", "testdate", "testdb"]
        parsed_args = vars(chado_tools.parse_arguments(args))
        self.assertFalse(parsed_args["include_header"])
        self.assertEqual(parsed_args["delimiter"], "\t")
        self.assertEqual(parsed_args["output_file"], "")
        self.assertEqual(parsed_args["organism"], "all")
        self.assertEqual(parsed_args["end_date"], "")

    def test_list_organisms_args(self):
        # Tests if the command line arguments for the subcommand 'chado list organisms' are parsed correctly
        args = ["chado", "list", "organisms", "-H", "-d", ";", "-o", "testfile", "testdb"]
        parsed_args = vars(chado_tools.parse_arguments(args))
        self.assertTrue(parsed_args["include_header"])
        self.assertEqual(parsed_args["delimiter"], ";")
        self.assertEqual(parsed_args["output_file"], "testfile")
        self.assertEqual(parsed_args["dbname"], "testdb")

    def test_list_cvterms_args(self):
        # Tests if the command line arguments for the subcommand 'chado list cvterms' are parsed correctly
        args = ["chado", "list", "cvterms", "--vocabulary", "testcv", "--database", "testdatabase", "testdb"]
        parsed_args = vars(chado_tools.parse_arguments(args))
        self.assertFalse(parsed_args["include_header"])
        self.assertEqual(parsed_args["delimiter"], "\t")
        self.assertEqual(parsed_args["output_file"], "")
        self.assertEqual(parsed_args["vocabulary"], "testcv")
        self.assertEqual(parsed_args["database"], "testdatabase")
        self.assertEqual(parsed_args["dbname"], "testdb")

    def test_list_genedb_products_args(self):
        # Tests if the command line arguments for the subcommand 'chado list genedb_products' are parsed correctly
        args = ["chado", "list", "genedb_products", "-H", "-d", ";", "-o", "testfile", "-a", "testorganism", "testdb"]
        parsed_args = vars(chado_tools.parse_arguments(args))
        self.assertTrue(parsed_args["include_header"])
        self.assertEqual(parsed_args["delimiter"], ";")
        self.assertEqual(parsed_args["output_file"], "testfile")
        self.assertEqual(parsed_args["organism"], "testorganism")
        self.assertEqual(parsed_args["dbname"], "testdb")

    def test_insert_organism_args(self):
        # Tests if the command line arguments for the subcommand 'chado insert organism' are parsed correctly
        args = ["chado", "insert", "organism", "-g", "testgenus", "-s", "testspecies", "-a", "testabbreviation",
                "--common_name", "testname", "--comment", "testcomment", "testdb"]
        parsed_args = vars(chado_tools.parse_arguments(args))
        self.assertEqual(parsed_args["genus"], "testgenus")
        self.assertEqual(parsed_args["species"], "testspecies")
        self.assertEqual(parsed_args["abbreviation"], "testabbreviation")
        self.assertEqual(parsed_args["common_name"], "testname")
        self.assertEqual(parsed_args["comment"], "testcomment")
        self.assertEqual(parsed_args["dbname"], "testdb")

    def test_delete_organism_args(self):
        # Tests if the command line arguments for the subcommand 'chado delete organism' are parsed correctly
        args = ["chado", "delete", "organism", "-a", "testorganism", "testdb"]
        parsed_args = vars(chado_tools.parse_arguments(args))
        self.assertEqual(parsed_args["organism"], "testorganism")
        self.assertEqual(parsed_args["dbname"], "testdb")

    def test_import_ontology_args(self):
        # Tests if the command line arguments for the subcommand 'chado import cv_terms' are parsed correctly
        args = ["chado", "import", "ontology", "-f", "testfile", "-A", "testauthority", "-F", "owl", "testdb"]
        parsed_args = vars(chado_tools.parse_arguments(args))
        self.assertEqual(parsed_args["input_file"], "testfile")
        self.assertEqual(parsed_args["input_url"], "")
        self.assertEqual(parsed_args["database_authority"], "testauthority")
        self.assertEqual(parsed_args["format"], "owl")
        self.assertEqual(parsed_args["dbname"], "testdb")

        # Test the default values / alternatives
        args = ["chado", "import", "ontology", "-u", "testurl", "-A", "testauthority", "testdb"]
        parsed_args = vars(chado_tools.parse_arguments(args))
        self.assertEqual(parsed_args["input_file"], "")
        self.assertEqual(parsed_args["input_url"], "testurl")
        self.assertEqual(parsed_args["format"], "obo")


if __name__ == '__main__':
    unittest.main(verbosity=2, buffer=True)
