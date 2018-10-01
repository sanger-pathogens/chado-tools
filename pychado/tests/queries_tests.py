import unittest
import pkg_resources
from terminal import chado_tools
from pychado import queries, utils


class TestQueries(unittest.TestCase):
    """Tests the loading and modification of stored SQL queries and templates"""

    def test_sql_resources(self):
        # Checks that all required resources are available
        self.assertTrue(pkg_resources.resource_isdir("pychado", "sql"))
        self.assertTrue(pkg_resources.resource_exists("pychado", "sql/stats.sql"))
        self.assertTrue(pkg_resources.resource_exists("pychado", "sql/list_organisms.sql"))
        self.assertTrue(pkg_resources.resource_exists("pychado", "sql/list_cvterms.sql"))
        self.assertTrue(pkg_resources.resource_exists("pychado", "sql/list_genedb_products.sql"))
        self.assertTrue(pkg_resources.resource_exists("pychado", "sql/insert_organism.sql"))
        self.assertTrue(pkg_resources.resource_exists("pychado", "sql/delete_organism.sql"))

    def test_load_stats_query(self):
        # Checks that the templates for the 'chado stats' query are correctly loaded
        args = utils.EmptyObject(organism="all", date="20180101")
        query = queries.load_stats_query(args)
        self.assertIn("SELECT", query)

    def test_load_list_query(self):
        # Checks that the templates for the 'chado list' queries are correctly loaded
        args = utils.EmptyObject()
        query = queries.load_list_query("organisms", args)
        self.assertIn("SELECT", query)

        args = utils.EmptyObject(vocabulary="all", database="all")
        query = queries.load_list_query("cvterms", args)
        self.assertIn("SELECT", query)

        args = utils.EmptyObject(organism="all")
        query = queries.load_list_query("genedb_products", args)
        self.assertIn("SELECT", query)

        args = utils.EmptyObject()
        query = queries.load_list_query("non_existent_specifier", args)
        self.assertEqual(query, "")

    def test_load_insert_statement(self):
        # Checks that the templates for the 'chado insert' statements are correctly loaded
        query = queries.load_insert_statement("organism")
        self.assertIn("INSERT", query)
        query = queries.load_insert_statement("non_existent_specifier")
        self.assertEqual(query, "")

    def test_load_delete_statement(self):
        # Checks that the templates for the 'chado delete' statements are correctly loaded
        args = utils.EmptyObject(organism="testorganism")
        query = queries.load_delete_statement("organism", args)
        self.assertIn("DELETE", query)
        query = queries.load_delete_statement("non_existent_specifier", args)
        self.assertEqual(query, "")

    def test_set_organism_condition(self):
        # Checks that a query placeholder is correctly replaced
        query = "SELECT * FROM testtable WHERE :ORGANISM_CONDITION"
        args = utils.EmptyObject(organism="all")
        self.assertEqual(queries.set_organism_condition(query, args),
                         "SELECT * FROM testtable WHERE TRUE")
        args.organism = "testorganism"
        self.assertEqual(queries.set_organism_condition(query, args),
                         "SELECT * FROM testtable WHERE abbreviation = :organism")

    def test_set_vocabulary_condition(self):
        # Checks that a query placeholder is correctly replaced
        query = "SELECT * FROM testtable WHERE :CV_CONDITION"
        args = utils.EmptyObject(vocabulary="all")
        self.assertEqual(queries.set_vocabulary_condition(query, args),
                         "SELECT * FROM testtable WHERE TRUE")
        args.vocabulary = "testvocabulary"
        self.assertEqual(queries.set_vocabulary_condition(query, args),
                         "SELECT * FROM testtable WHERE cv.name = :cv_name")

    def test_set_database_condition(self):
        # Checks that a query placeholder is correctly replaced
        query = "SELECT * FROM testtable WHERE :DB_CONDITION"
        args = utils.EmptyObject(database="all")
        self.assertEqual(queries.set_database_condition(query, args),
                         "SELECT * FROM testtable WHERE TRUE")
        args.database = "testdatabase"
        self.assertEqual(queries.set_database_condition(query, args),
                         "SELECT * FROM testtable WHERE db.name = :database_name")

    def test_specify_list_parameters(self):
        # Checks that the parameters that complete the SQL query of a 'chado list' command are correctly specified
        # chado list organisms
        args = chado_tools.parse_arguments(["chado", "list", "organisms", "testdb"])
        params = queries.specify_list_parameters("organisms", args)
        self.assertEqual(len(params), 0)

        # chado list cvterms
        args = chado_tools.parse_arguments(["chado", "list", "cvterms", "--vocabulary", "testcv",
                                            "--database", "testdatabase", "testdb"])
        params = queries.specify_list_parameters("cvterms", args)
        self.assertEqual(len(params), 2)
        self.assertEqual(params["cv_name"], "testcv")
        self.assertEqual(params["database_name"], "testdatabase")

        args = chado_tools.parse_arguments(["chado", "list", "cvterms", "testdb"])
        params = queries.specify_list_parameters("cvterms", args)
        self.assertEqual(len(params), 0)

        # chado list products
        args = chado_tools.parse_arguments(["chado", "list", "genedb_products", "-a", "testorganism", "testdb"])
        params = queries.specify_list_parameters("genedb_products", args)
        self.assertEqual(len(params), 1)
        self.assertEqual(params["organism"], "testorganism")

        args = chado_tools.parse_arguments(["chado", "list", "genedb_products", "testdb"])
        params = queries.specify_list_parameters("genedb_products", args)
        self.assertEqual(len(params), 0)

    def test_specify_stats_parameters(self):
        # Checks that the parameters that complete the SQL query of a 'chado stats' command are correctly specified
        args = chado_tools.parse_arguments(["chado", "stats", "-a", "testorganism", "--start_date", "testdate",
                                            "--end_date", "testdate2", "testdb"])
        params = queries.specify_stats_parameters(args)
        self.assertEqual(len(params), 3)
        self.assertEqual(params["start_date"], "testdate")
        self.assertEqual(params["end_date"], "testdate2")
        self.assertEqual(params["organism"], "testorganism")

        args = chado_tools.parse_arguments(["chado", "stats", "--start_date", "testdate", "testdb"])
        params = queries.specify_stats_parameters(args)
        self.assertEqual(len(params), 2)
        self.assertEqual(params["start_date"], "testdate")
        self.assertEqual(params["end_date"], utils.current_date())

    def test_specify_insert_parameters(self):
        # Checks that the parameters that complete the SQL query of a 'chado insert' command are correctly specified
        args = chado_tools.parse_arguments(["chado", "insert", "organism", "-g", "testgenus", "-s", "testspecies",
                                            "-a", "testabbreviation", "--common_name", "testname",
                                            "--comment", "testcomment", "testdb"])
        params = queries.specify_insert_parameters("organism", args)
        self.assertEqual(len(params), 5)
        self.assertEqual(params["genus"], "testgenus")
        self.assertEqual(params["species"], "testspecies")
        self.assertEqual(params["abbreviation"], "testabbreviation")
        self.assertEqual(params["common_name"], "testname")
        self.assertEqual(params["comment"], "testcomment")

    def test_specify_delete_parameters(self):
        # Checks that the parameters that complete the SQL query of a 'chado delete' command are correctly specified
        args = chado_tools.parse_arguments(["chado", "delete", "organism", "-a", "testorganism", "testdb"])
        params = queries.specify_delete_parameters("organism", args)
        self.assertEqual(len(params), 1)
        self.assertEqual(params["organism"], "testorganism")


if __name__ == '__main__':
    unittest.main(verbosity=2, buffer=True)
