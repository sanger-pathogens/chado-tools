import unittest
from pychado.io import io
from pychado.orm import base, general


class TestIO(unittest.TestCase):
    """Tests basic functions for accessing databases via SQL"""

    def setUp(self):
        # Establishes a database connection and creates tables
        global loader
        loader = io.DatabaseLoader("sqlite:///:memory:")
        base.Base.metadata.create_all(loader.engine)

    def test_find_or_create(self):
        # Tests the functionality for checking if entries exist in the database, and for creating new entries
        res = loader.insert_into_table(general.Db, name="testdb")
        self.assertTrue(isinstance(res, general.Db))
        self.assertEqual(res.name, "testdb")

        query = loader.query_table(general.Db, name="testdb")
        res = query.first()
        self.assertTrue(isinstance(res, general.Db))
        self.assertEqual(res.name, "testdb")

        query = loader.query_table(general.Db, name="anotherdb")
        res = query.first()
        self.assertIsNone(res)
        loader.rollback()


if __name__ == '__main__':
    unittest.main(verbosity=2, buffer=True)
