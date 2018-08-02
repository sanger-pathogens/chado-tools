import unittest
from scripts import chado_tools


class TestCommands(unittest.TestCase):
    """Tests if all implemented commands and sub-commands are available through the entry point"""

    def test_general_commands(self):
        commands = chado_tools.general_commands()
        self.assertIn("connect", commands)
        self.assertIn("create", commands)
        self.assertIn("dump", commands)
        self.assertIn("restore", commands)
        self.assertIn("import", commands)
        self.assertIn("export", commands)
        self.assertIn("query", commands)
        self.assertIn("stats", commands)
        self.assertNotIn("non_existent_command", commands)

    def test_wrapper_commands(self):
        commands = chado_tools.wrapper_commands()
        self.assertIn("list", commands)

    def test_list_commands(self):
        commands = chado_tools.list_commands()
        self.assertIn("organisms", commands)
        self.assertIn("genera", commands)
        self.assertIn("products", commands)


class TestArguments(unittest.TestCase):
    """Tests if input arguments are parsed correctly"""

    def test_connect_args(self):
        # Tests if the command line arguments for the subcommand 'chado connect' are parsed correctly
        args = ["chado", "connect", "-c", "testconfig", "testdb"]
        parsed_args = vars(chado_tools.parse_arguments(args))
        self.assertEqual(parsed_args["config"], "testconfig")
        self.assertEqual(parsed_args["dbname"], "testdb")

        # Test the default values
        args = ["chado", "connect", "testdb"]
        parsed_args = vars(chado_tools.parse_arguments(args))
        self.assertEqual(parsed_args["config"], "")
        self.assertNotIn("non_existent_argument", parsed_args)

    def test_create_args(self):
        # Tests if the command line arguments for the subcommand 'chado create' are parsed correctly
        args = ["chado", "create", "-s", "testschema", "testdb"]
        parsed_args = vars(chado_tools.parse_arguments(args))
        self.assertEqual(parsed_args["schema"], "testschema")

    def test_dump_args(self):
        # Tests if the command line arguments for the subcommand 'chado dump' are parsed correctly
        args = ["chado", "dump", "testdb", "testarchive"]
        parsed_args = vars(chado_tools.parse_arguments(args))
        self.assertEqual(parsed_args["dbname"], "testdb")
        self.assertEqual(parsed_args["archive"], "testarchive")

    def test_restore_args(self):
        # Tests if the command line arguments for the subcommand 'chado restore' are parsed correctly
        args = ["chado", "restore", "testdb", "testarchive"]
        parsed_args = vars(chado_tools.parse_arguments(args))
        self.assertEqual(parsed_args["dbname"], "testdb")
        self.assertEqual(parsed_args["archive"], "testarchive")

    def test_import_args(self):
        # Tests if the command line arguments for the subcommand 'chado import' are parsed correctly
        args = ["chado", "import", "-d", ";", "-f", "testfile", "testdb", "testtable"]
        parsed_args = vars(chado_tools.parse_arguments(args))
        self.assertEqual(parsed_args["delimiter"], ";")
        self.assertEqual(parsed_args["input_file"], "testfile")
        self.assertEqual(parsed_args["dbname"], "testdb")
        self.assertEqual(parsed_args["table"], "testtable")

        # Test the default values
        args = ["chado", "import", "testdb", "testtable"]
        parsed_args = vars(chado_tools.parse_arguments(args))
        self.assertEqual(parsed_args["delimiter"], "\t")
        self.assertEqual(parsed_args["input_file"], "")

    def test_export_args(self):
        # Tests if the command line arguments for the subcommand 'chado export' are parsed correctly
        args = ["chado", "export", "-H", "-d", ";", "-o", "testfile", "testdb", "testtable"]
        parsed_args = vars(chado_tools.parse_arguments(args))
        self.assertTrue(parsed_args["include_header"])
        self.assertEqual(parsed_args["delimiter"], ";")
        self.assertEqual(parsed_args["output_file"], "testfile")
        self.assertEqual(parsed_args["dbname"], "testdb")
        self.assertEqual(parsed_args["table"], "testtable")

        # Test the default values
        args = ["chado", "export", "testdb", "testtable"]
        parsed_args = vars(chado_tools.parse_arguments(args))
        self.assertFalse(parsed_args["include_header"])
        self.assertEqual(parsed_args["delimiter"], "\t")
        self.assertEqual(parsed_args["output_file"], "")

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
        args = ["chado", "stats", "-H", "-d", ";", "-o", "testfile", "-g", "testgenus",
                "-s", "testspecies", "-D", "testdate", "testdb"]
        parsed_args = vars(chado_tools.parse_arguments(args))
        self.assertTrue(parsed_args["include_header"])
        self.assertEqual(parsed_args["delimiter"], ";")
        self.assertEqual(parsed_args["output_file"], "testfile")
        self.assertEqual(parsed_args["genus"], "testgenus")
        self.assertEqual(parsed_args["species"], "testspecies")
        self.assertEqual(parsed_args["date"], "testdate")
        self.assertEqual(parsed_args["dbname"], "testdb")

    def test_list_genera_args(self):
        # Tests if the command line arguments for the subcommand 'chado list genera' are parsed correctly
        args = ["chado", "list", "genera", "-H", "-d", ";", "-o", "testfile", "testdb"]
        parsed_args = vars(chado_tools.parse_arguments(args))
        self.assertTrue(parsed_args["include_header"])
        self.assertEqual(parsed_args["delimiter"], ";")
        self.assertEqual(parsed_args["output_file"], "testfile")
        self.assertEqual(parsed_args["dbname"], "testdb")

    def test_list_organisms_args(self):
        # Tests if the command line arguments for the subcommand 'chado list organisms' are parsed correctly
        args = ["chado", "list", "organisms", "-H", "-d", ";", "-o", "testfile", "-g", "testgenus", "testdb"]
        parsed_args = vars(chado_tools.parse_arguments(args))
        self.assertTrue(parsed_args["include_header"])
        self.assertEqual(parsed_args["delimiter"], ";")
        self.assertEqual(parsed_args["output_file"], "testfile")
        self.assertEqual(parsed_args["genus"], "testgenus")
        self.assertEqual(parsed_args["dbname"], "testdb")

    def test_list_products_args(self):
        # Tests if the command line arguments for the subcommand 'chado list products' are parsed correctly
        args = ["chado", "list", "products", "-H", "-d", ";", "-o", "testfile", "-g", "testgenus",
                "-s", "testspecies", "testdb"]
        parsed_args = vars(chado_tools.parse_arguments(args))
        self.assertTrue(parsed_args["include_header"])
        self.assertEqual(parsed_args["delimiter"], ";")
        self.assertEqual(parsed_args["output_file"], "testfile")
        self.assertEqual(parsed_args["genus"], "testgenus")
        self.assertEqual(parsed_args["species"], "testspecies")
        self.assertEqual(parsed_args["dbname"], "testdb")


if __name__ == '__main__':
    unittest.main(verbosity=2, buffer=True)
