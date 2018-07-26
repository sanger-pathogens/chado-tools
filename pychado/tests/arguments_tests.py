import unittest
from scripts import chado_tools


class TestArguments(unittest.TestCase):
    """Tests if input arguments are parsed correctly"""

    def test_available_commands(self):
        # Tests if all implemented sub-commands are available through the entry point
        commands = chado_tools.available_commands()
        self.assertIn("connect", commands)
        self.assertIn("create", commands)
        self.assertIn("dump", commands)
        self.assertIn("restore", commands)
        self.assertIn("import", commands)
        self.assertIn("export", commands)
        self.assertIn("query", commands)
        self.assertNotIn("non_existent_command", commands)

    def test_connect_args(self):
        # Tests if the command line arguments for the subcommand 'chado connect' are parsed correctly
        args = ["chado", "connect", "-c", "testconfig", "testdb"]
        parsed_args = vars(chado_tools.parse_arguments(args))
        self.assertIn("config", parsed_args)
        self.assertEqual(parsed_args["config"], "testconfig")
        self.assertIn("dbname", parsed_args)
        self.assertEqual(parsed_args["dbname"], "testdb")

        # Test the default values
        args = ["chado", "connect", "testdb"]
        parsed_args = vars(chado_tools.parse_arguments(args))
        self.assertIn("config", parsed_args)
        self.assertEqual(parsed_args["config"], "")
        self.assertNotIn("non_existent_argument", parsed_args)

    def test_create_args(self):
        # Tests if the command line arguments for the subcommand 'chado create' are parsed correctly
        args = ["chado", "create", "-s", "testschema", "testdb"]
        parsed_args = vars(chado_tools.parse_arguments(args))
        self.assertIn("schema", parsed_args)
        self.assertEqual(parsed_args["schema"], "testschema")

    def test_dump_args(self):
        # Tests if the command line arguments for the subcommand 'chado dump' are parsed correctly
        args = ["chado", "dump", "testdb", "testarchive"]
        parsed_args = vars(chado_tools.parse_arguments(args))
        self.assertIn("dbname", parsed_args)
        self.assertEqual(parsed_args["dbname"], "testdb")
        self.assertIn("archive", parsed_args)
        self.assertEqual(parsed_args["archive"], "testarchive")

    def test_restore_args(self):
        # Tests if the command line arguments for the subcommand 'chado restore' are parsed correctly
        args = ["chado", "restore", "testdb", "testarchive"]
        parsed_args = vars(chado_tools.parse_arguments(args))
        self.assertIn("dbname", parsed_args)
        self.assertEqual(parsed_args["dbname"], "testdb")
        self.assertIn("archive", parsed_args)
        self.assertEqual(parsed_args["archive"], "testarchive")

    def test_import_args(self):
        # Tests if the command line arguments for the subcommand 'chado import' are parsed correctly
        args = ["chado", "import", "-d", ";", "-f", "testfile", "testdb", "testtable"]
        parsed_args = vars(chado_tools.parse_arguments(args))
        self.assertIn("delimiter", parsed_args)
        self.assertEqual(parsed_args["delimiter"], ";")
        self.assertIn("input_file", parsed_args)
        self.assertEqual(parsed_args["input_file"], "testfile")
        self.assertIn("dbname", parsed_args)
        self.assertEqual(parsed_args["dbname"], "testdb")
        self.assertIn("table", parsed_args)
        self.assertEqual(parsed_args["table"], "testtable")

        # Test the default values
        args = ["chado", "import", "testdb", "testtable"]
        parsed_args = vars(chado_tools.parse_arguments(args))
        self.assertIn("delimiter", parsed_args)
        self.assertEqual(parsed_args["delimiter"], "\t")
        self.assertIn("input_file", parsed_args)
        self.assertEqual(parsed_args["input_file"], "")

    def test_export_args(self):
        # Tests if the command line arguments for the subcommand 'chado export' are parsed correctly
        args = ["chado", "export", "-H", "-d", ";", "-o", "testfile", "testdb", "testtable"]
        parsed_args = vars(chado_tools.parse_arguments(args))
        self.assertIn("include_header", parsed_args)
        self.assertTrue(parsed_args["include_header"])
        self.assertIn("delimiter", parsed_args)
        self.assertEqual(parsed_args["delimiter"], ";")
        self.assertIn("output_file", parsed_args)
        self.assertEqual(parsed_args["output_file"], "testfile")
        self.assertIn("dbname", parsed_args)
        self.assertEqual(parsed_args["dbname"], "testdb")
        self.assertIn("table", parsed_args)
        self.assertEqual(parsed_args["table"], "testtable")

        # Test the default values
        args = ["chado", "export", "testdb", "testtable"]
        parsed_args = vars(chado_tools.parse_arguments(args))
        self.assertIn("include_header", parsed_args)
        self.assertFalse(parsed_args["include_header"])
        self.assertIn("delimiter", parsed_args)
        self.assertEqual(parsed_args["delimiter"], "\t")
        self.assertIn("output_file", parsed_args)
        self.assertEqual(parsed_args["output_file"], "")

    def test_query_args(self):
        # Tests if the command line arguments for the subcommand 'chado query' are parsed correctly
        args = ["chado", "query", "-H", "-d", ";", "-o", "testfile", "-q", "testquery", "testdb"]
        parsed_args = vars(chado_tools.parse_arguments(args))
        self.assertIn("include_header", parsed_args)
        self.assertTrue(parsed_args["include_header"])
        self.assertIn("delimiter", parsed_args)
        self.assertEqual(parsed_args["delimiter"], ";")
        self.assertIn("output_file", parsed_args)
        self.assertEqual(parsed_args["output_file"], "testfile")
        self.assertIn("query", parsed_args)
        self.assertEqual(parsed_args["query"], "testquery")
        self.assertIn("input_file", parsed_args)
        self.assertEqual(parsed_args["input_file"], "")
        self.assertIn("dbname", parsed_args)
        self.assertEqual(parsed_args["dbname"], "testdb")

        # Test the default values / alternatives
        args = ["chado", "query", "-f", "testqueryfile", "testdb"]
        parsed_args = vars(chado_tools.parse_arguments(args))
        self.assertIn("include_header", parsed_args)
        self.assertFalse(parsed_args["include_header"])
        self.assertIn("delimiter", parsed_args)
        self.assertEqual(parsed_args["delimiter"], "\t")
        self.assertIn("output_file", parsed_args)
        self.assertEqual(parsed_args["output_file"], "")
        self.assertIn("query", parsed_args)
        self.assertEqual(parsed_args["query"], "")
        self.assertIn("input_file", parsed_args)
        self.assertEqual(parsed_args["input_file"], "testqueryfile")


if __name__ == '__main__':
    unittest.main(verbosity=2, buffer=True)
