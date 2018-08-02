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
        self.assertTrue(pkg_resources.resource_exists("pychado", "sql/list_genera.sql"))
        self.assertTrue(pkg_resources.resource_exists("pychado", "sql/list_products.sql"))
        self.assertTrue(pkg_resources.resource_exists("pychado", "sql/condition_genus.sql"))
        self.assertTrue(pkg_resources.resource_exists("pychado", "sql/condition_genus_species.sql"))

    def test_load_stats_query(self):
        # Checks that the templates for the 'chado stats' query are correctly loaded
        args = utils.EmptyObject(genus="all", species="all", date="20180101")
        query = queries.load_stats_query(args)
        self.assertIn("SELECT", query)

    def test_load_list_query(self):
        # Checks that the templates for the 'chado list' queries are correctly loaded
        args = utils.EmptyObject(genus="all", species="all")
        query = queries.load_list_query("organisms", args)
        self.assertIn("SELECT", query)
        query = queries.load_list_query("genera", args)
        self.assertIn("SELECT", query)
        query = queries.load_list_query("products", args)
        self.assertIn("SELECT", query)
        query = queries.load_list_query("non_existent_specifier", args)
        self.assertEqual(query, "")

    def test_set_organism_condition(self):
        # Checks that a query placeholder is correctly replaced
        query = "SELECT * FROM testdb WHERE {{CONDITION}}"
        args = utils.EmptyObject(genus="all", species="all")
        self.assertEqual(queries.set_organism_condition(query, args),
                         "SELECT * FROM testdb WHERE TRUE")
        args.genus = "testgenus"
        self.assertEqual(queries.set_organism_condition(query, args),
                         "SELECT * FROM testdb WHERE genus = %s")
        args.species = "testspecies"
        self.assertEqual(queries.set_organism_condition(query, args),
                         "SELECT * FROM testdb WHERE genus = %s AND species = %s")


if __name__ == '__main__':
    unittest.main(verbosity=2, buffer=True)
