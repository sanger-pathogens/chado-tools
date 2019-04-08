import unittest.mock
import pkg_resources
from .. import queries


class TestQueries(unittest.TestCase):
    """Tests the loading and modification of stored SQL queries and templates"""

    def test_sql_resources(self):
        # Checks that all required resources are available
        self.assertTrue(pkg_resources.resource_isdir("pychado", "sql"))
        self.assertTrue(pkg_resources.resource_exists("pychado", "sql/extract_annotation_updates.sql"))
        self.assertTrue(pkg_resources.resource_exists("pychado", "sql/extract_public_annotation_updates.sql"))
        self.assertTrue(pkg_resources.resource_exists("pychado", "sql/extract_organisms.sql"))
        self.assertTrue(pkg_resources.resource_exists("pychado", "sql/extract_public_organisms.sql"))
        self.assertTrue(pkg_resources.resource_exists("pychado", "sql/extract_cvterms.sql"))
        self.assertTrue(pkg_resources.resource_exists("pychado", "sql/extract_gene_products.sql"))
        self.assertTrue(pkg_resources.resource_exists("pychado", "sql/extract_public_gene_products.sql"))
        self.assertTrue(pkg_resources.resource_exists("pychado", "sql/extract_curator_comments.sql"))
        self.assertTrue(pkg_resources.resource_exists("pychado", "sql/extract_public_curator_comments.sql"))

    def test_load_query(self):
        # Checks that the templates for the 'chado extracts' queries are correctly loaded
        query = queries.load_query("public_organisms")
        self.assertIn("SELECT", query)

        query = queries.load_query("organisms")
        self.assertIn("SELECT", query)

        query = queries.load_query("cvterms")
        self.assertIn("SELECT", query)

        query = queries.load_query("public_gene_products")
        self.assertIn("SELECT", query)

        query = queries.load_query("gene_products")
        self.assertIn("SELECT", query)

        query = queries.load_query("public_annotation_updates")
        self.assertIn("SELECT", query)

        query = queries.load_query("annotation_updates")
        self.assertIn("SELECT", query)

        query = queries.load_query("public_curator_comments")
        self.assertIn("SELECT", query)

        query = queries.load_query("curator_comments")
        self.assertIn("SELECT", query)

        query = queries.load_query("non_existent_specifier")
        self.assertEqual(query, "")

    def test_bind_parameters(self):
        # Checks if a parameter is correctly bound to a query
        query = "SELECT * FROM testtable WHERE mycolumn = :myvalue"
        query_with_params = queries.bind_parameters(query, myvalue="testvalue")
        query_with_params_inlined = str(query_with_params.compile(compile_kwargs={"literal_binds": True}))
        self.assertEqual(query_with_params_inlined, "SELECT * FROM testtable WHERE mycolumn = 'testvalue'")

        query = "SELECT * FROM testtable WHERE col1 = :val1 AND col2 = :val2"
        query_with_params = queries.bind_parameters(query, val1=12, val2=True)
        query_with_params_inlined = str(query_with_params.compile(compile_kwargs={"literal_binds": True}))
        self.assertEqual(query_with_params_inlined, "SELECT * FROM testtable WHERE col1 = 12 AND col2 = true")

    @unittest.mock.patch("pychado.queries.bind_parameters")
    @unittest.mock.patch("pychado.queries.set_vocabulary_condition")
    @unittest.mock.patch("pychado.queries.set_database_condition")
    @unittest.mock.patch("pychado.queries.set_organism_condition")
    def test_set_conditions(self, mock_organism, mock_database, mock_vocabulary, mock_bind):
        # Checks if placeholders in a query are replaced with actual conditions
        self.assertIs(mock_organism, queries.set_organism_condition)
        self.assertIs(mock_database, queries.set_database_condition)
        self.assertIs(mock_vocabulary, queries.set_vocabulary_condition)
        self.assertIs(mock_bind, queries.bind_parameters)

        query = "SELECT * FROM testtable"
        queries.set_query_conditions(query)
        mock_organism.assert_not_called()
        mock_database.assert_not_called()
        mock_vocabulary.assert_not_called()
        mock_bind.assert_called_with(query)

        mock_bind.reset_mock()
        mock_organism.return_value = "modified_query"
        mock_database.return_value = "further_modified_query"
        mock_vocabulary.return_value = "final_query"
        queries.set_query_conditions(query, organism="testorganism", database="testdatabase",
                                     vocabulary="testvocabulary")
        mock_organism.assert_called_with(query, "testorganism")
        mock_database.assert_called_with("modified_query", "testdatabase")
        mock_vocabulary.assert_called_with("further_modified_query", "testvocabulary")
        mock_bind.assert_called_with("final_query", organism="testorganism", database="testdatabase",
                                     vocabulary="testvocabulary")

    def test_set_organism_condition(self):
        # Checks that a query placeholder is correctly replaced
        query = "SELECT * FROM testtable WHERE :ORGANISM_CONDITION"
        self.assertEqual(queries.set_organism_condition(query, ""),
                         "SELECT * FROM testtable WHERE TRUE")
        self.assertEqual(queries.set_organism_condition(query, "testorganism"),
                         "SELECT * FROM testtable WHERE abbreviation = :organism")

    def test_set_vocabulary_condition(self):
        # Checks that a query placeholder is correctly replaced
        query = "SELECT * FROM testtable WHERE :CV_CONDITION"
        self.assertEqual(queries.set_vocabulary_condition(query, ""),
                         "SELECT * FROM testtable WHERE TRUE")
        self.assertEqual(queries.set_vocabulary_condition(query, "testvocabulary"),
                         "SELECT * FROM testtable WHERE cv.name = :vocabulary")

    def test_set_database_condition(self):
        # Checks that a query placeholder is correctly replaced
        query = "SELECT * FROM testtable WHERE :DB_CONDITION"
        self.assertEqual(queries.set_database_condition(query, ""),
                         "SELECT * FROM testtable WHERE TRUE")
        self.assertEqual(queries.set_database_condition(query, "testdatabase"),
                         "SELECT * FROM testtable WHERE db.name = :database")


if __name__ == '__main__':
    unittest.main(verbosity=2, buffer=True)
