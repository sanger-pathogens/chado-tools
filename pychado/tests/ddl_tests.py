import unittest.mock
import sqlalchemy.schema
from .. import dbutils, utils, ddl


class RoleTests(unittest.TestCase):
    """Tests the handling of roles for a CHADO database"""

    connection_parameters = utils.parse_yaml(dbutils.default_configuration_file())
    connection_uri = dbutils.random_database_uri(connection_parameters)

    @classmethod
    def setUpClass(cls):
        # Creates a database and establishes a connection
        dbutils.create_database(cls.connection_uri)
        cls.client = ddl.RolesClient(cls.connection_uri)

    @classmethod
    def tearDownClass(cls):
        # Drops the database
        dbutils.drop_database(cls.connection_uri, True)

    def test_revoke_privileges_commands(self):
        # Tests the creation of commands for revoking privileges for database access
        commands = self.client.revoke_privileges_commands("testrole", "testschema")
        self.assertEqual(len(commands), 4)
        self.assertIn("REVOKE USAGE ON SCHEMA \"testschema\" FROM \"testrole\"", commands)
        self.assertIn("REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA \"testschema\" FROM \"testrole\"", commands)

    def test_grant_privileges_commands(self):
        # Tests the creation of commands for granting privileges for database access
        commands = self.client.grant_privileges_commands("testrole", "testschema", False)
        self.assertEqual(len(commands), 3)
        self.assertIn("GRANT USAGE ON SCHEMA \"testschema\" TO \"testrole\"", commands)
        self.assertNotIn("GRANT INSERT ON ALL TABLES IN SCHEMA \"testschema\" TO \"testrole\"", commands)

        commands = self.client.grant_privileges_commands("testrole", "testschema", True)
        self.assertEqual(len(commands), 8)
        self.assertIn("GRANT USAGE ON SCHEMA \"testschema\" TO \"testrole\"", commands)
        self.assertIn("GRANT INSERT ON ALL TABLES IN SCHEMA \"testschema\" TO \"testrole\"", commands)

        commands = self.client.grant_privileges_commands("testrole", "audit", True)
        self.assertEqual(len(commands), 6)

    @unittest.mock.patch("sqlalchemy.schema.DDL")
    def test_execute_ddl(self, mock_ddl):
        # Tests the function that executes DDL statements
        self.assertIs(mock_ddl, sqlalchemy.schema.DDL)
        self.client.execute_ddl(["command1", "command2"])
        self.assertIn(unittest.mock.call("command1"), mock_ddl.mock_calls)
        self.assertIn(unittest.mock.call("command2"), mock_ddl.mock_calls)
        self.assertIn(unittest.mock.call().execute(self.client.engine), mock_ddl.mock_calls)

        mock_ddl.reset_mock()
        self.client.execute_ddl("singlecommand")
        mock_ddl.assert_called_with("singlecommand")
        self.assertIn(unittest.mock.call().execute(self.client.engine), mock_ddl.mock_calls)

    @unittest.mock.patch("pychado.ddl.RolesClient.execute_ddl")
    @unittest.mock.patch("pychado.ddl.RolesClient.revoke_privileges_commands")
    @unittest.mock.patch("pychado.ddl.RolesClient.grant_privileges_commands")
    @unittest.mock.patch("pychado.ddl.RolesClient.schema_exists")
    @unittest.mock.patch("pychado.ddl.RolesClient.role_exists")
    def test_grant_or_revoke(self, mock_exists_role, mock_exists_schema, mock_grant, mock_revoke, mock_execute):
        # Tests the main function granting/revoking privileges
        self.assertIs(mock_exists_role, self.client.role_exists)
        self.assertIs(mock_exists_schema, self.client.schema_exists)
        self.assertIs(mock_grant, self.client.grant_privileges_commands)
        self.assertIs(mock_revoke, self.client.revoke_privileges_commands)
        self.assertIs(mock_execute, self.client.execute_ddl)

        mock_exists_role.return_value = False
        self.client.grant_or_revoke("testrole", "testschema", False, False)
        mock_exists_schema.assert_not_called()
        mock_execute.assert_not_called()

        mock_exists_role.return_value = True
        mock_exists_schema.return_value = False
        self.client.grant_or_revoke("testrole", "testschema", False, False)
        mock_exists_schema.assert_called()
        mock_execute.assert_not_called()

        mock_exists_role.return_value = True
        mock_exists_schema.return_value = True
        mock_grant.return_value = ["grant_command"]
        mock_revoke.return_value = ["revoke_command"]
        self.client.grant_or_revoke("testrole", "testschema", False, False)
        mock_revoke.assert_called_with("testrole", "testschema")
        mock_grant.assert_not_called()
        mock_execute.assert_called_with(["revoke_command"])

        self.client.grant_or_revoke("testrole", "testschema", False, True)
        mock_revoke.assert_called_with("testrole", "testschema")
        mock_grant.assert_called_with("testrole", "testschema", False)
        mock_execute.assert_called_with(["revoke_command", "grant_command"])


class SetupTests(unittest.TestCase):
    """Tests the setup of CHADO database schemas"""

    connection_parameters = utils.parse_yaml(dbutils.default_configuration_file())
    connection_uri = dbutils.random_database_uri(connection_parameters)

    @classmethod
    def setUpClass(cls):
        # Creates a database and establishes a connection
        dbutils.create_database(cls.connection_uri)
        cls.client = ddl.AuditSchemaSetupClient(cls.connection_uri)
        cls.public_metadata = sqlalchemy.schema.MetaData(schema='public')

    @classmethod
    def tearDownClass(cls):
        # Drops the database
        dbutils.drop_database(cls.connection_uri, True)

    def setUp(self):
        # Cleans the database
        sqlalchemy.schema.DDL("DROP SCHEMA public CASCADE").execute(self.client.engine)
        sqlalchemy.schema.DDL("CREATE SCHEMA public").execute(self.client.engine)
        if self.client.schema_exists("audit"):
            sqlalchemy.schema.DDL("DROP SCHEMA audit CASCADE").execute(self.client.engine)

    def test_create_trigger_function(self):
        # Tests the syntax of trigger function creation
        wrapper = self.client.create_trigger_function("trigger_schema", "trigger_name", "trigger_def")
        self.assertEqual(wrapper, "CREATE OR REPLACE FUNCTION trigger_schema.trigger_name()\n"
                                  "RETURNS trigger\n"
                                  "LANGUAGE plpgsql\n"
                                  "AS $function$\n"
                                  "BEGIN\n"
                                  "trigger_def;\n"
                                  "END;\n"
                                  "$function$")

    def test_create_generic_trigger(self):
        # Tests the syntax of trigger creation
        trigger = self.client.create_generic_trigger("testtrigger", "function_schema", "trigger_function",
                                                     "testschema", "testtable")
        self.assertEqual(trigger, "CREATE TRIGGER testtrigger AFTER INSERT OR UPDATE OR DELETE ON testschema.testtable "
                                  "FOR EACH ROW EXECUTE PROCEDURE function_schema.trigger_function()")

    def test_generic_audit_function(self):
        # Tests the syntax of an audit function
        fct = self.client.generic_audit_function("testschema", "testtable", ["col1", "col2"])
        self.assertEqual(fct, "IF TG_OP = 'INSERT' THEN\n"
                              "\tINSERT INTO testschema.testtable(type, col1, col2) "
                              "VALUES (CAST(TG_OP AS operation_type), NEW.col1, NEW.col2);\n"
                              "\tRETURN NEW;\n"
                              "ELSIF TG_OP = 'UPDATE' THEN\n"
                              "\tINSERT INTO testschema.testtable(type, col1, col2) "
                              "VALUES (CAST('BEFORE' AS operation_type), OLD.col1, OLD.col2);\n"
                              "\tINSERT INTO testschema.testtable(type, col1, col2) "
                              "VALUES (CAST(TG_OP AS operation_type), NEW.col1, NEW.col2);\n"
                              "\tRETURN NEW;\n"
                              "ELSE\n"
                              "\tINSERT INTO testschema.testtable(type, col1, col2) "
                              "VALUES (CAST(TG_OP AS operation_type), OLD.col1, OLD.col2);\n"
                              "\tRETURN OLD;\n"
                              "END IF")

    def test_schema_exists(self):
        # Tests the function that checks if a schema exists
        res = self.client.schema_exists("testschema")
        self.assertFalse(res)
        sqlalchemy.schema.DDL("CREATE SCHEMA testschema").execute(self.client.engine)
        res = self.client.schema_exists("testschema")
        self.assertTrue(res)

    def test_table_exists(self):
        # Tests the function that checks if a table exists
        res = self.client.table_exists("testtable", "public")
        self.assertFalse(res)
        sqlalchemy.schema.DDL("CREATE TABLE testtable(id INTEGER, data VARCHAR(255))").execute(self.client.engine)
        res = self.client.table_exists("testtable", "public")
        self.assertTrue(res)

    def test_table_inherits(self):
        # Tests the function that checks if a table inherits from a parent table
        sqlalchemy.schema.DDL("CREATE TABLE capitals(state CHAR(2))").execute(self.client.engine)
        sqlalchemy.schema.DDL("CREATE TABLE cities(name TEXT, population INT)").execute(self.client.engine)
        res = self.client.table_inherits("capitals", "cities")
        self.assertFalse(res)
        sqlalchemy.schema.DDL("DROP TABLE capitals").execute(self.client.engine)
        sqlalchemy.schema.DDL("CREATE TABLE capitals(state CHAR(2)) INHERITS (cities)").execute(self.client.engine)
        res = self.client.table_inherits("capitals", "cities")
        self.assertTrue(res)

    def test_trigger_exists(self):
        # Tests the function that checks if a trigger exists
        sqlalchemy.schema.DDL("CREATE TABLE testtable(id INTEGER, data VARCHAR(255))").execute(self.client.engine)
        res = self.client.trigger_exists("public", "testtrigger")
        self.assertFalse(res)
        fct = self.client.create_trigger_function("public", "testfct", "SELECT 1+1")
        sqlalchemy.schema.DDL(fct).execute(self.client.engine)
        sqlalchemy.schema.DDL("CREATE TRIGGER testtrigger AFTER INSERT ON testtable EXECUTE PROCEDURE testfct()")\
            .execute(self.client.engine)
        res = self.client.trigger_exists("public", "testtrigger")
        self.assertTrue(res)

    def test_function_exists(self):
        # Tests the function that checks if a database function exists
        res = self.client.function_exists("pg_catalog", "now")
        self.assertTrue(res)
        res = self.client.function_exists("pg_catalog", "inexistent_function")
        self.assertFalse(res)
        res = self.client.function_exists("inexistent_schema", "now")
        self.assertFalse(res)

    def test_role_exists(self):
        # Tests the function that checks if a role exists
        res = self.client.role_exists("postgres")
        self.assertTrue(res)
        res = self.client.role_exists(utils.random_string(30))
        self.assertFalse(res)

    @unittest.mock.patch("pychado.ddl.AuditSchemaSetupClient.execute_ddl")
    @unittest.mock.patch("pychado.ddl.AuditSchemaSetupClient.schema_exists")
    def test_create_schema(self, mock_exists, mock_execute):
        # Tests the function that creates a schema
        self.assertIs(mock_exists, self.client.schema_exists)
        self.assertIs(mock_execute, self.client.execute_ddl)

        mock_exists.return_value = True
        self.client.create_schema()
        mock_exists.assert_called_with("audit")
        mock_execute.assert_not_called()

        mock_exists.return_value = False
        self.client.create_schema()
        mock_execute.assert_called_with("CREATE SCHEMA audit")

    @unittest.mock.patch("pychado.ddl.AuditSchemaSetupClient.execute_ddl")
    @unittest.mock.patch("pychado.ddl.AuditSchemaSetupClient.table_inherits")
    @unittest.mock.patch("pychado.ddl.AuditSchemaSetupClient.table_exists")
    def test_setup_inheritance(self, mock_exists, mock_inherits, mock_execute):
        # Tests the function that sets up table inheritance
        self.assertIs(mock_exists, self.client.table_exists)
        self.assertIs(mock_inherits, self.client.table_inherits)
        self.assertIs(mock_execute, self.client.execute_ddl)

        mock_exists.return_value = False
        mock_inherits.return_value = True
        self.client.setup_inheritance("cities", ["capitals"])
        mock_exists.assert_called_with("capitals", "audit")
        mock_inherits.assert_not_called()
        mock_execute.assert_not_called()

        mock_exists.return_value = True
        mock_inherits.return_value = True
        self.client.setup_inheritance("cities", ["capitals"])
        mock_exists.assert_called_with("capitals", "audit")
        mock_inherits.assert_called_with("audit.capitals", "audit.cities")
        mock_execute.assert_not_called()

        mock_exists.return_value = True
        mock_inherits.return_value = False
        self.client.setup_inheritance("cities", ["capitals"])
        mock_exists.assert_called_with("capitals", "audit")
        mock_inherits.assert_called_with("audit.capitals", "audit.cities")
        mock_execute.assert_called_with("ALTER TABLE audit.capitals INHERIT audit.cities")

    @unittest.mock.patch("pychado.ddl.AuditSchemaSetupClient.execute_ddl")
    @unittest.mock.patch("pychado.ddl.AuditSchemaSetupClient.trigger_exists")
    @unittest.mock.patch("pychado.ddl.AuditSchemaSetupClient.create_generic_trigger")
    @unittest.mock.patch("pychado.ddl.AuditSchemaSetupClient.create_trigger_function")
    @unittest.mock.patch("pychado.ddl.AuditSchemaSetupClient.generic_audit_function")
    def test_create_audit_triggers(self, mock_function, mock_wrapper, mock_trigger, mock_exists, mock_execute):
        # Tests the creation of audit trigger functions
        self.assertIs(mock_function, self.client.generic_audit_function)
        self.assertIs(mock_wrapper, self.client.create_trigger_function)
        self.assertIs(mock_trigger, self.client.create_generic_trigger)
        self.assertIs(mock_exists, self.client.trigger_exists)
        self.assertIs(mock_execute, self.client.execute_ddl)

        testtable = sqlalchemy.Table("testtable", self.client.metadata,
                                     sqlalchemy.Column("idcolumn", sqlalchemy.INTEGER, primary_key=True),
                                     sqlalchemy.Column("datacolumn", sqlalchemy.TEXT))

        mock_function.return_value = "function_definition"
        mock_wrapper.return_value = "function_wrapper"
        mock_trigger.return_value = "trigger_wrapper"
        mock_exists.return_value = True
        self.client.create_audit_triggers([testtable])
        mock_function.assert_called_with("audit", "testtable", ["idcolumn", "datacolumn"])
        mock_wrapper.assert_called_with("audit", "public_testtable_proc", "function_definition")
        mock_trigger.assert_called_with("testtable_audit_tr", "audit", "public_testtable_proc", "public", "testtable")
        mock_execute.assert_called_with("function_wrapper")

        mock_execute.reset_mock()
        mock_exists.return_value = False
        self.client.create_audit_triggers([testtable])
        mock_execute.assert_has_calls([unittest.mock.call("function_wrapper"),
                                       unittest.mock.call("trigger_wrapper")])

    def test_create_audit_tables(self):
        # Tests the creation of the audit tables
        newtable = sqlalchemy.Table(
            "newtable", self.public_metadata,
            sqlalchemy.Column("idcolumn", sqlalchemy.INTEGER, nullable=False),
            sqlalchemy.Column("datacolumn", sqlalchemy.TEXT, nullable=True, server_default="whatever"))
        audit_tables = self.client.create_audit_tables([newtable])
        self.assertEqual(len(audit_tables), 1)
        audit_table = audit_tables[0]
        self.assertEqual(len(audit_table.columns), 6)
        for column in audit_table.columns:
            if column.name == "idcolumn":
                self.assertFalse(column.primary_key)
            elif column.name == "audit_id":
                self.assertTrue(column.primary_key)


class BackupSetupTests(unittest.TestCase):

    connection_parameters = utils.parse_yaml(dbutils.default_configuration_file())
    connection_uri = dbutils.random_database_uri(connection_parameters)

    @classmethod
    def setUpClass(cls):
        # Creates a database and establishes a connection
        dbutils.create_database(cls.connection_uri)
        cls.client = ddl.AuditBackupSchemaSetupClient(cls.connection_uri)
        cls.public_metadata = sqlalchemy.schema.MetaData(schema='public')

    @classmethod
    def tearDownClass(cls):
        # Drops the database
        dbutils.drop_database(cls.connection_uri, True)

    @unittest.mock.patch("sqlalchemy.engine.Connection.execute")
    @unittest.mock.patch("pychado.ddl.AuditBackupSchemaSetupClient.function_exists")
    def test_execute_backup_function(self, mock_exists: unittest.mock.Mock, mock_execute: unittest.mock.Mock):
        # Tests the function that executes the backup of the audit schema
        self.assertIs(mock_exists, self.client.function_exists)
        self.assertIs(mock_execute, self.client.connection.execute)

        mock_exists.return_value = False
        self.client.execute_backup_function("testdate")
        mock_execute.assert_not_called()

        mock_exists.return_value = True
        self.client.execute_backup_function("testdate")
        self.assertIn(unittest.mock.call().scalar(), mock_execute.mock_calls)

    def test_backup_function_wrapper(self):
        # Tests the syntax of the backup function
        fct = self.client.backup_function_wrapper("testname", ["var integer"], "testdefinition")
        self.assertEqual(fct, "CREATE OR REPLACE FUNCTION testname(text)\n"
                              "RETURNS bigint\n"
                              "LANGUAGE plpgsql\n"
                              "AS $function$\n"
                              "DECLARE\n"
                              "var integer;\n"
                              "BEGIN\n"
                              "testdefinition;\n"
                              "END;\n"
                              "$function$")


if __name__ == '__main__':
    unittest.main(verbosity=2, buffer=True)
