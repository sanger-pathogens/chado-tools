import unittest
import pkg_resources
from pychado import queries, utils


class TestQueries(unittest.TestCase):
    """Tests the loading and modification of stored SQL queries and templates"""

    def test_sql_resources(self):
        # Checks that all required resources are available
        self.assertTrue(pkg_resources.resource_isdir("pychado", "sql"))
        self.assertTrue(pkg_resources.resource_exists("pychado", "sql/stats.sql"))
        self.assertTrue(pkg_resources.resource_exists("pychado", "sql/list_organisms.sql"))
        self.assertTrue(pkg_resources.resource_exists("pychado", "sql/list_products.sql"))
        self.assertTrue(pkg_resources.resource_exists("pychado", "sql/condition_organism.sql"))
        self.assertTrue(pkg_resources.resource_exists("pychado", "sql/insert_organism.sql"))
        self.assertTrue(pkg_resources.resource_exists("pychado", "sql/delete_organism.sql"))

    def test_load_stats_query(self):
        # Checks that the templates for the 'chado stats' query are correctly loaded
        args = utils.EmptyObject(organism="all", date="20180101")
        query = queries.load_stats_query(args)
        self.assertIn("SELECT", query)

    def test_load_list_query(self):
        # Checks that the templates for the 'chado list' queries are correctly loaded
        args = utils.EmptyObject(organism="all")
        query = queries.load_list_query("organisms", args)
        self.assertIn("SELECT", query)
        query = queries.load_list_query("products", args)
        self.assertIn("SELECT", query)
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
        query = "SELECT * FROM testdb WHERE {{ORGANISM_CONDITION}}"
        args = utils.EmptyObject(organism="all")
        self.assertEqual(queries.set_organism_condition(query, args),
                         "SELECT * FROM testdb WHERE TRUE")
        args.organism = "testorganism"
        self.assertEqual(queries.set_organism_condition(query, args),
                         "SELECT * FROM testdb WHERE abbreviation = %s")


if __name__ == '__main__':
    unittest.main(verbosity=2, buffer=True)
