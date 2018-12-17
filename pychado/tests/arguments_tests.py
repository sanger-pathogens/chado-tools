import unittest
from .. import chado_tools


class TestCommands(unittest.TestCase):
    """Tests if all implemented commands and sub-commands are available through the entry point"""

    def test_init_commands(self):
        commands = chado_tools.init_commands()
        self.assertEqual(len(commands), 2)
        self.assertIn("init", commands)
        self.assertIn("reset", commands)

    def test_general_commands(self):
        commands = chado_tools.general_commands()
        self.assertEqual(len(commands), 2)
        self.assertIn("connect", commands)
        self.assertIn("query", commands)

    def test_wrapper_commands(self):
        commands = chado_tools.wrapper_commands()
        self.assertEqual(len(commands), 7)
        self.assertIn("extract", commands)
        self.assertIn("insert", commands)
        self.assertIn("delete", commands)
        self.assertIn("import", commands)
        self.assertIn("export", commands)
        self.assertIn("execute", commands)
        self.assertIn("admin", commands)

    def test_admin_commands(self):
        commands = chado_tools.admin_commands()
        self.assertEqual(len(commands), 7)
        self.assertIn("create", commands)
        self.assertIn("drop", commands)
        self.assertIn("dump", commands)
        self.assertIn("restore", commands)
        self.assertIn("setup", commands)
        self.assertIn("grant", commands)
        self.assertIn("revoke", commands)

    def test_extract_commands(self):
        commands = chado_tools.extract_commands()
        self.assertEqual(len(commands), 4)
        self.assertIn("organisms", commands)
        self.assertIn("cvterms", commands)
        self.assertIn("genedb_products", commands)
        self.assertIn("stats", commands)

    def test_insert_commands(self):
        commands = chado_tools.insert_commands()
        self.assertEqual(len(commands), 1)
        self.assertIn("organism", commands)

    def test_delete_commands(self):
        commands = chado_tools.delete_commands()
        self.assertEqual(len(commands), 1)
        self.assertIn("organism", commands)

    def test_import_commands(self):
        commands = chado_tools.import_commands()
        self.assertEqual(len(commands), 5)
        self.assertIn("essentials", commands)
        self.assertIn("ontology", commands)
        self.assertIn("gff", commands)
        self.assertIn("fasta", commands)
        self.assertIn("gaf", commands)

    def test_export_commands(self):
        commands = chado_tools.export_commands()
        self.assertEqual(len(commands), 2)
        self.assertIn("fasta", commands)
        self.assertIn("gff", commands)

    def test_execute_commands(self):
        commands = chado_tools.execute_commands()
        self.assertEqual(len(commands), 1)
        self.assertIn("audit_backup", commands)


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
        args = ["chado", "admin", "create", "testdb"]
        parsed_args = vars(chado_tools.parse_arguments(args))
        self.assertEqual(parsed_args["dbname"], "testdb")

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

    def test_setup_args(self):
        # Tests if the command line arguments for the subcommand 'chado admin setup' are parsed correctly
        args = ["chado", "admin", "setup", "-s", "basic", "testdb"]
        parsed_args = vars(chado_tools.parse_arguments(args))
        self.assertEqual(parsed_args["dbname"], "testdb")
        self.assertEqual(parsed_args["schema"], "basic")
        self.assertEqual(parsed_args["schema_file"], "")

        # Test the default values / alternatives
        args = ["chado", "admin", "setup", "testdb"]
        parsed_args = vars(chado_tools.parse_arguments(args))
        self.assertEqual(parsed_args["schema"], "gmod")
        self.assertEqual(parsed_args["schema_file"], "")

        args = ["chado", "admin", "setup", "-f", "testschema", "testdb"]
        parsed_args = vars(chado_tools.parse_arguments(args))
        self.assertEqual(parsed_args["schema"], "gmod")
        self.assertEqual(parsed_args["schema_file"], "testschema")

    def test_grant_args(self):
        # Tests if the command line arguments for the subcommand 'chado admin grant' are parsed correctly
        args = ["chado", "admin", "grant", "-r", "testrole", "-s", "testschema", "-w", "testdb"]
        parsed_args = vars(chado_tools.parse_arguments(args))
        self.assertEqual(parsed_args["role"], "testrole")
        self.assertEqual(parsed_args["schema"], "testschema")
        self.assertEqual(parsed_args["write"], True)
        self.assertEqual(parsed_args["dbname"], "testdb")

        # Test the default values / alternatives
        args = ["chado", "admin", "grant", "-r", "testrole", "testdb"]
        parsed_args = vars(chado_tools.parse_arguments(args))
        self.assertEqual(parsed_args["schema"], None)
        self.assertEqual(parsed_args["write"], False)

    def test_revoke_args(self):
        # Tests if the command line arguments for the subcommand 'chado admin revoke' are parsed correctly
        args = ["chado", "admin", "revoke", "-r", "testrole", "-s", "testschema", "testdb"]
        parsed_args = vars(chado_tools.parse_arguments(args))
        self.assertEqual(parsed_args["role"], "testrole")
        self.assertEqual(parsed_args["schema"], "testschema")
        self.assertEqual(parsed_args["dbname"], "testdb")

    def test_query_args(self):
        # Tests if the command line arguments for the subcommand 'chado query' are parsed correctly
        args = ["chado", "query", "-H", "-d", ";", "-o", "testfile", "-F", "json", "-q", "testquery", "testdb"]
        parsed_args = vars(chado_tools.parse_arguments(args))
        self.assertTrue(parsed_args["include_header"])
        self.assertEqual(parsed_args["delimiter"], ";")
        self.assertEqual(parsed_args["output_file"], "testfile")
        self.assertEqual(parsed_args["format"], "json")
        self.assertEqual(parsed_args["query"], "testquery")
        self.assertEqual(parsed_args["input_file"], "")
        self.assertEqual(parsed_args["dbname"], "testdb")

        # Test the default values / alternatives
        args = ["chado", "query", "-f", "testqueryfile", "testdb"]
        parsed_args = vars(chado_tools.parse_arguments(args))
        self.assertFalse(parsed_args["include_header"])
        self.assertEqual(parsed_args["delimiter"], "\t")
        self.assertEqual(parsed_args["output_file"], "")
        self.assertEqual(parsed_args["format"], "csv")
        self.assertEqual(parsed_args["query"], "")
        self.assertEqual(parsed_args["input_file"], "testqueryfile")

    def test_execute_audit_backup_args(self):
        # Tests if the command line arguments for the subcommand 'chado execute audit_backup' are parsed correctly
        args = ["chado", "execute", "audit_backup", "--date", "testdate", "testdb"]
        parsed_args = vars(chado_tools.parse_arguments(args))
        self.assertEqual(parsed_args["date"], "testdate")
        self.assertEqual(parsed_args["dbname"], "testdb")

    def test_extract_stats_args(self):
        # Tests if the command line arguments for the subcommand 'chado extract stats' are parsed correctly
        args = ["chado", "extract", "stats", "-H", "-d", ";", "-o", "testfile", "-F", "json", "-a", "testorganism",
                "--start_date", "testdate", "--end_date", "testdate2", "testdb"]
        parsed_args = vars(chado_tools.parse_arguments(args))
        self.assertTrue(parsed_args["include_header"])
        self.assertEqual(parsed_args["delimiter"], ";")
        self.assertEqual(parsed_args["output_file"], "testfile")
        self.assertEqual(parsed_args["format"], "json")
        self.assertEqual(parsed_args["organism"], "testorganism")
        self.assertEqual(parsed_args["start_date"], "testdate")
        self.assertEqual(parsed_args["end_date"], "testdate2")
        self.assertEqual(parsed_args["dbname"], "testdb")

        # Test the default values
        args = ["chado", "extract", "stats", "--start_date", "testdate", "testdb"]
        parsed_args = vars(chado_tools.parse_arguments(args))
        self.assertFalse(parsed_args["include_header"])
        self.assertEqual(parsed_args["delimiter"], "\t")
        self.assertEqual(parsed_args["output_file"], "")
        self.assertEqual(parsed_args["format"], "csv")
        self.assertEqual(parsed_args["organism"], None)
        self.assertEqual(parsed_args["end_date"], "")

    def test_extract_organisms_args(self):
        # Tests if the command line arguments for the subcommand 'chado extract organisms' are parsed correctly
        args = ["chado", "extract", "organisms", "-H", "-d", ";", "-o", "testfile", "--public_only", "testdb"]
        parsed_args = vars(chado_tools.parse_arguments(args))
        self.assertTrue(parsed_args["include_header"])
        self.assertEqual(parsed_args["delimiter"], ";")
        self.assertEqual(parsed_args["output_file"], "testfile")
        self.assertEqual(parsed_args["format"], "csv")
        self.assertTrue(parsed_args["public_only"])
        self.assertFalse(parsed_args["extract_version"])
        self.assertEqual(parsed_args["dbname"], "testdb")

    def test_extract_cvterms_args(self):
        # Tests if the command line arguments for the subcommand 'chado extract cvterms' are parsed correctly
        args = ["chado", "extract", "cvterms", "--vocabulary", "testcv", "--database", "testdatabase", "testdb"]
        parsed_args = vars(chado_tools.parse_arguments(args))
        self.assertFalse(parsed_args["include_header"])
        self.assertEqual(parsed_args["delimiter"], "\t")
        self.assertEqual(parsed_args["output_file"], "")
        self.assertEqual(parsed_args["format"], "csv")
        self.assertEqual(parsed_args["vocabulary"], "testcv")
        self.assertEqual(parsed_args["database"], "testdatabase")
        self.assertEqual(parsed_args["dbname"], "testdb")

    def test_extract_genedb_products_args(self):
        # Tests if the command line arguments for the subcommand 'chado extract genedb_products' are parsed correctly
        args = ["chado", "extract", "genedb_products", "-H", "-d", ";", "-o", "testfile", "-a", "testorganism",
                "testdb"]
        parsed_args = vars(chado_tools.parse_arguments(args))
        self.assertTrue(parsed_args["include_header"])
        self.assertEqual(parsed_args["delimiter"], ";")
        self.assertEqual(parsed_args["output_file"], "testfile")
        self.assertEqual(parsed_args["format"], "csv")
        self.assertEqual(parsed_args["organism"], "testorganism")
        self.assertEqual(parsed_args["dbname"], "testdb")

    def test_insert_organism_args(self):
        # Tests if the command line arguments for the subcommand 'chado insert organism' are parsed correctly
        args = ["chado", "insert", "organism", "-g", "testgenus", "-s", "testspecies", "-a", "testabbreviation",
                "--common_name", "testname", "-i", "teststrain", "--comment", "testcomment", "--genome_version", "5",
                "testdb"]
        parsed_args = vars(chado_tools.parse_arguments(args))
        self.assertEqual(parsed_args["genus"], "testgenus")
        self.assertEqual(parsed_args["species"], "testspecies")
        self.assertEqual(parsed_args["infraspecific_name"], "teststrain")
        self.assertEqual(parsed_args["abbreviation"], "testabbreviation")
        self.assertEqual(parsed_args["common_name"], "testname")
        self.assertEqual(parsed_args["comment"], "testcomment")
        self.assertEqual(parsed_args["genome_version"], 5)
        self.assertEqual(parsed_args["dbname"], "testdb")

    def test_delete_organism_args(self):
        # Tests if the command line arguments for the subcommand 'chado delete organism' are parsed correctly
        args = ["chado", "delete", "organism", "-a", "testorganism", "testdb"]
        parsed_args = vars(chado_tools.parse_arguments(args))
        self.assertEqual(parsed_args["organism"], "testorganism")
        self.assertEqual(parsed_args["dbname"], "testdb")

    def test_import_essentials_args(self):
        # Tests if the command line arguments for the subcommand 'chado import essentials' are parsed correctly
        args = ["chado", "import", "essentials", "testdb"]
        parsed_args = vars(chado_tools.parse_arguments(args))
        self.assertEqual(parsed_args["dbname"], "testdb")

    def test_import_ontology_args(self):
        # Tests if the command line arguments for the subcommand 'chado import ontology' are parsed correctly
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

    def test_import_gff_args(self):
        # Tests if the command line arguments for the subcommand 'chado import gff' are parsed correctly
        args = ["chado", "import", "gff", "-f", "testfile", "-a", "testorganism", "--fasta", "testfasta",
                "-t", "contig", "--fresh_load", "--force", "--full_genome", "testdb"]
        parsed_args = vars(chado_tools.parse_arguments(args))
        self.assertEqual(parsed_args["input_file"], "testfile")
        self.assertEqual(parsed_args["organism"], "testorganism")
        self.assertEqual(parsed_args["fasta"], "testfasta")
        self.assertEqual(parsed_args["sequence_type"], "contig")
        self.assertTrue(parsed_args["fresh_load"])
        self.assertTrue(parsed_args["force"])
        self.assertTrue(parsed_args["full_genome"])
        self.assertEqual(parsed_args["dbname"], "testdb")

        # Test the default values / alternatives
        args = ["chado", "import", "gff", "-f", "testfile", "-a", "testorganism", "testdb"]
        parsed_args = vars(chado_tools.parse_arguments(args))
        self.assertIsNone(parsed_args["fasta"])
        self.assertFalse(parsed_args["fresh_load"])
        self.assertFalse(parsed_args["force"])
        self.assertFalse(parsed_args["full_genome"])

    def test_import_fasta_args(self):
        # Tests if the command line arguments for the subcommand 'chado import fasta' are parsed correctly
        args = ["chado", "import", "fasta", "-f", "testfile", "-a", "testorganism", "-t", "contig", "testdb"]
        parsed_args = vars(chado_tools.parse_arguments(args))
        self.assertEqual(parsed_args["input_file"], "testfile")
        self.assertEqual(parsed_args["organism"], "testorganism")
        self.assertEqual(parsed_args["sequence_type"], "contig")
        self.assertEqual(parsed_args["dbname"], "testdb")

    def test_import_gaf_args(self):
        # Tests if the command line arguments for the subcommand 'chado import gaf' are parsed correctly
        args = ["chado", "import", "gaf", "-f", "testfile", "-a", "testorganism", "testdb"]
        parsed_args = vars(chado_tools.parse_arguments(args))
        self.assertEqual(parsed_args["input_file"], "testfile")
        self.assertEqual(parsed_args["organism"], "testorganism")
        self.assertEqual(parsed_args["dbname"], "testdb")

    def test_export_fasta_args(self):
        # Tests if the command line arguments for the subcommand 'chado export fasta' are parsed correctly
        args = ["chado", "export", "fasta", "-f", "testfile", "-a", "testorganism", "-t", "proteins",
                "-r", "testrelease", "testdb"]
        parsed_args = vars(chado_tools.parse_arguments(args))
        self.assertEqual(parsed_args["output_file"], "testfile")
        self.assertEqual(parsed_args["organism"], "testorganism")
        self.assertEqual(parsed_args["sequence_type"], "proteins")
        self.assertEqual(parsed_args["release"], "testrelease")
        self.assertFalse(parsed_args["extract_version"])
        self.assertEqual(parsed_args["dbname"], "testdb")

    def test_export_gff_args(self):
        # Tests if the command line arguments for the subcommand 'chado export gff' are parsed correctly
        args = ["chado", "export", "gff", "-f", "testfile", "-a", "testorganism", "--export_fasta", "--fasta_file",
                "testfasta", "testdb"]
        parsed_args = vars(chado_tools.parse_arguments(args))
        self.assertEqual(parsed_args["output_file"], "testfile")
        self.assertEqual(parsed_args["organism"], "testorganism")
        self.assertTrue(parsed_args["export_fasta"])
        self.assertEqual(parsed_args["fasta_file"], "testfasta")
        self.assertEqual(parsed_args["dbname"], "testdb")


if __name__ == '__main__':
    unittest.main(verbosity=2, buffer=True)
