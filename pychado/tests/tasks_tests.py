import unittest.mock
from pychado import dbutils, tasks


class TestTasks(unittest.TestCase):
    """Tests the functionality of all commands of the CHADO program"""

    @unittest.mock.patch('pychado.dbutils.connect_to_database')
    @unittest.mock.patch('pychado.dbutils.exists')
    def test_connect(self, mock_exist, mock_connect):
        # Checks that a connection is only established if the database exists
        self.assertIs(mock_exist, dbutils.exists)
        self.assertIs(mock_connect, dbutils.connect_to_database)

        mock_exist.return_value = False
        tasks.connect(dbutils.default_configuration_file(), "test")
        mock_connect.assert_not_called()

        mock_connect.reset_mock()
        mock_exist.return_value = True
        tasks.connect(dbutils.default_configuration_file(), "test")
        mock_connect.assert_called()

    @unittest.mock.patch('pychado.dbutils.dump_database')
    @unittest.mock.patch('pychado.dbutils.exists')
    def test_dump(self, mock_exist, mock_dump):
        # Checks that a database is only dumped if it exists
        self.assertIs(mock_exist, dbutils.exists)
        self.assertIs(mock_dump, dbutils.dump_database)

        mock_exist.return_value = False
        tasks.dump(dbutils.default_configuration_file(), "test", "archive")
        mock_dump.assert_not_called()

        mock_dump.reset_mock()
        mock_exist.return_value = True
        tasks.dump(dbutils.default_configuration_file(), "test", "archive")
        mock_dump.assert_called()

    @unittest.mock.patch('pychado.dbutils.setup_database')
    @unittest.mock.patch('pychado.dbutils.download_schema')
    @unittest.mock.patch('pychado.dbutils.create_database')
    @unittest.mock.patch('pychado.dbutils.exists')
    def test_create(self, mock_exist, mock_create, mock_load, mock_setup):
        # Checks that a database is only created if it doesn't exist
        self.assertIs(mock_exist, dbutils.exists)
        self.assertIs(mock_create, dbutils.create_database)
        self.assertIs(mock_load, dbutils.download_schema)
        self.assertIs(mock_setup, dbutils.setup_database)

        mock_exist.return_value = True
        tasks.create(dbutils.default_configuration_file(), "schema.sql", "test")
        mock_create.assert_not_called()
        mock_load.assert_not_called()
        mock_setup.assert_called()

        mock_create.reset_mock()
        mock_load.reset_mock()
        mock_setup.reset_mock()
        mock_exist.return_value = False
        tasks.create(dbutils.default_configuration_file(), "", "test")
        mock_create.assert_called()
        mock_load.assert_called()
        mock_setup.assert_called()

    @unittest.mock.patch('pychado.dbutils.restore_database')
    @unittest.mock.patch('pychado.dbutils.create_database')
    @unittest.mock.patch('pychado.dbutils.exists')
    def test_restore(self, mock_exist, mock_create, mock_restore):
        # Checks that the database for restoring is created if and only if it doesn't exist yet
        self.assertIs(mock_exist, dbutils.exists)
        self.assertIs(mock_create, dbutils.create_database)
        self.assertIs(mock_restore, dbutils.restore_database)

        mock_exist.return_value = True
        tasks.restore(dbutils.default_configuration_file(), "test", "archive")
        mock_create.assert_not_called()
        mock_restore.assert_called()

        mock_create.reset_mock()
        mock_restore.reset_mock()
        mock_exist.return_value = False
        tasks.restore(dbutils.default_configuration_file(), "test", "archive")
        mock_create.assert_called()
        mock_restore.assert_called()

    @unittest.mock.patch('pychado.dbutils.generate_dsn')
    @unittest.mock.patch('pychado.dbutils.copy_from_file')
    @unittest.mock.patch('pychado.dbutils.exists')
    def test_import(self, mock_exist, mock_copy, mock_dsn):
        # Checks that an import is triggered if and only if the database exists
        self.assertIs(mock_exist, dbutils.exists)
        self.assertIs(mock_copy, dbutils.copy_from_file)
        self.assertIs(mock_dsn, dbutils.generate_dsn)

        mock_exist.return_value = False
        tasks.importer(dbutils.default_configuration_file(), "testdb", "testtable", "testfile", "\t")
        mock_copy.assert_not_called()

        mock_copy.reset_mock()
        mock_exist.return_value = True
        mock_dsn.return_value = "testdsn"
        tasks.importer(dbutils.default_configuration_file(), "testdb", "testtable", "testfile", "\t")
        mock_copy.assert_called_with("testdsn", "testtable", "testfile", "\t")

    @unittest.mock.patch('pychado.dbutils.generate_dsn')
    @unittest.mock.patch('pychado.dbutils.copy_to_file')
    @unittest.mock.patch('pychado.dbutils.exists')
    def test_export(self, mock_exist, mock_copy, mock_dsn):
        # Checks that an export is triggered if and only if the database exists
        self.assertIs(mock_exist, dbutils.exists)
        self.assertIs(mock_copy, dbutils.copy_to_file)
        self.assertIs(mock_dsn, dbutils.generate_dsn)

        mock_exist.return_value = False
        tasks.exporter(dbutils.default_configuration_file(), "testdb", "testtable", "testfile", "\t")
        mock_copy.assert_not_called()

        mock_copy.reset_mock()
        mock_exist.return_value = True
        mock_dsn.return_value = "testdsn"
        tasks.exporter(dbutils.default_configuration_file(), "testdb", "testtable", "testfile", "\t")
        mock_copy.assert_called_with("testdsn", "testtable", "testfile", "\t")


if __name__ == '__main__':
    unittest.main(buffer=True)
