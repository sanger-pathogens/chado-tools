import unittest
from pychado import utils
from pychado.io import load_cvterms


class TestLoadCvterms(unittest.TestCase):
    """Tests various functions used to load CV terms from a file into a database"""

    def test_filter_objects(self):
        # Checks that a function correctly filters objects in a list according to keyword arguments
        john = utils.EmptyObject(name="John")
        mike = utils.EmptyObject(name="Mike")
        persons = [john, mike]
        filtered_persons = load_cvterms.filter_objects(persons, name="Mike")
        self.assertEqual(len(filtered_persons), 1)
        self.assertEqual(filtered_persons[0], mike)
        with self.assertRaises(AttributeError):
            load_cvterms.filter_objects(persons, age=42)

    def test_list_to_dict(self):
        # Checks that a function correctly converts a list into a dictionary
        john = utils.EmptyObject(name="John")
        mike = utils.EmptyObject(name="Mike")
        persons = [john, mike]
        persons_dict = load_cvterms.list_to_dict(persons, "name")
        self.assertEqual(len(persons_dict), 2)
        self.assertIn("John", persons_dict)
        self.assertEqual(persons_dict["John"], john)
        with self.assertRaises(AttributeError):
            load_cvterms.list_to_dict(persons, "age")

    def test_split_dbxref(self):
        # Checks the splitting of a given database cross reference into its constituents
        result = load_cvterms.split_dbxref("testdb:testaccession:testversion")
        self.assertEqual(result[0], "testdb")
        self.assertEqual(result[1], "testaccession")
        self.assertEqual(result[2], "testversion")

        result = load_cvterms.split_dbxref("testdb:testaccession")
        self.assertEqual(result[0], "testdb")
        self.assertEqual(result[1], "testaccession")
        self.assertEqual(result[2], "")

        with self.assertRaises(AttributeError):
            load_cvterms.split_dbxref("testdb_testaccession")

    def test_create_dbxref(self):
        # Checks the creation of a database cross reference from its constituents
        result = load_cvterms.create_dbxref("testdb", "testaccession", "testversion")
        self.assertEqual(result, "testdb:testaccession:testversion")

        result = load_cvterms.create_dbxref("testdb", "testaccession")
        self.assertEqual(result, "testdb:testaccession")

        with self.assertRaises(AttributeError):
            load_cvterms.create_dbxref("testdb", "")


if __name__ == '__main__':
    unittest.main(verbosity=2, buffer=True)
