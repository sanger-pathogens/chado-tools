from typing import Union, List
import sqlalchemy.sql
import sqlalchemy.orm.attributes
import sqlalchemy.engine
import sqlalchemy.schema
import sqlalchemy.event
from . import utils
from .orm import base, general, cv, organism, pub, sequence, audit


class ChadoClient(object):
    """Base Class for access to a CHADO database"""

    def __init__(self, uri: str):
        """Constructor - connect to database"""
        self.uri = uri
        self.engine = sqlalchemy.create_engine(self.uri)                            # type: sqlalchemy.engine.Engine

    def __del__(self):
        """Destructor - disconnect from database"""
        # self.engine.dispose()
        pass


class DDLClient(ChadoClient):
    """Base class for all classes using DDL"""

    def __init__(self, uri: str):
        """Constructor - connect to database"""
        super().__init__(uri)
        self.connection = self.engine.connect()

    def __del__(self):
        """Destructor - disconnect from database"""
        self.connection.close()
        super().__del__()

    def schema_exists(self, schema: str) -> bool:
        """Checks if a given schema exists in a database"""
        schemata_table = sqlalchemy.text("information_schema.schemata")
        schemata_condition = sqlalchemy.text("schema_name=:schema")
        exists_query = sqlalchemy.exists().select_from(schemata_table).where(
            schemata_condition.bindparams(schema=schema)).select()
        return self.connection.execute(exists_query).scalar()

    def table_exists(self, table: str, schema: str) -> bool:
        """Checks if a given table exists in a given database schema"""
        tables_table = sqlalchemy.text("information_schema.tables")
        tables_condition = sqlalchemy.text("table_schema=:schema AND table_name=:table")
        exists_query = sqlalchemy.exists().select_from(tables_table).where(
            tables_condition.bindparams(schema=schema, table=table)).select()
        return self.connection.execute(exists_query).scalar()

    def table_inherits(self, child_table: str, parent_table: str) -> bool:
        """Checks if a given table inherits from a given parent table"""
        inheritance_table = sqlalchemy.text("pg_catalog.pg_inherits")
        inheritance_condition = sqlalchemy.text(r"inhparent=:parent\:\:regclass AND inhrelid=:child\:\:regclass")
        inherits_query = sqlalchemy.exists().select_from(inheritance_table).where(
            inheritance_condition.bindparams(parent=parent_table, child=child_table)).select()
        return self.connection.execute(inherits_query).scalar()

    def trigger_exists(self, trigger_name: str) -> bool:
        """Checks if a trigger with a given name exists in a database"""
        triggers_table = sqlalchemy.text("information_schema.triggers")
        triggers_condition = sqlalchemy.text("trigger_name=:trigger_name")
        exists_query = sqlalchemy.exists().select_from(triggers_table).where(
            triggers_condition.bindparams(trigger_name=trigger_name)).select()
        return self.connection.execute(exists_query).scalar()

    def role_exists(self, role_name: str) -> bool:
        """Checks if a given role/user exists in a database"""
        roles_table = sqlalchemy.text("pg_catalog.pg_user")
        roles_condition = sqlalchemy.text("usename=:role_name")
        exists_query = sqlalchemy.exists().select_from(roles_table).where(
            roles_condition.bindparams(role_name=role_name)).select()
        return self.connection.execute(exists_query).scalar()

    def execute_ddl(self, statements: Union[str, List[str]]) -> None:
        """Executes DDL statement[s]"""
        if isinstance(statements, list):
            for statement in statements:
                ddl = sqlalchemy.schema.DDL(statement)
                ddl.execute(self.engine)
        else:
            ddl = sqlalchemy.schema.DDL(statements)
            ddl.execute(self.engine)

    def create(self):
        """Basis function defined for completeness of the API"""
        pass


class RolesClient(DDLClient):
    """Class for handling users/roles in a CHADO database"""

    def grant_or_revoke(self, rolename: str, specific_schema: str, read_write: bool, grant_access: bool):
        """Checks for role and schema existence and grants privileges"""
        # Check if the user exists
        if not self.role_exists(rolename):
            print("Role '" + rolename + "' does not exist. Create it before granting privileges.")
            return

        # Obtain a list of schemata
        if specific_schema:
            schemata = [specific_schema]
        else:
            schemata = ["public", "audit"]

        # Loop over all schemata
        for schema in schemata:

            # Check if the schema exists
            if not self.schema_exists(schema) and schema != "public":
                print("Schema '" + schema + "' does not exist.")
                continue

            # Revoke/grant privileges
            commands = self.revoke_privileges_commands(rolename, schema)
            if grant_access:
                commands.extend(self.grant_privileges_commands(rolename, schema, read_write))
            self.execute_ddl(commands)

            # Print feedback
            if grant_access:
                print("Privileges on schema '" + schema + "' granted to role '" + rolename + "'")
            else:
                print("Privileges on schema '" + schema + "' revoked from role '" + rolename + "'")

    @staticmethod
    def grant_privileges_commands(rolename: str, schema: str, read_write: bool) -> list:
        """Creates commands for granting privileges for accessing database objects to a role/user"""
        x_role = "\"" + rolename + "\""
        x_schema = "\"" + schema + "\""
        statements = list()
        statements.append(" ".join(["GRANT USAGE ON SCHEMA", x_schema, "TO", x_role]))
        statements.append(" ".join(["GRANT SELECT ON ALL SEQUENCES IN SCHEMA", x_schema, "TO", x_role]))
        statements.append(" ".join(["GRANT SELECT ON ALL TABLES IN SCHEMA", x_schema, "TO", x_role]))
        if read_write:
            statements.append(" ".join(["GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA", x_schema, "TO", x_role]))
            statements.append(" ".join(["GRANT USAGE ON ALL SEQUENCES IN SCHEMA", x_schema, "TO", x_role]))
            statements.append(" ".join(["GRANT INSERT ON ALL TABLES IN SCHEMA", x_schema, "TO", x_role]))
            if schema != "audit":
                statements.append(" ".join(["GRANT UPDATE ON ALL TABLES IN SCHEMA", x_schema, "TO", x_role]))
                statements.append(" ".join(["GRANT DELETE ON ALL TABLES IN SCHEMA", x_schema, "TO", x_role]))
        return statements

    @staticmethod
    def revoke_privileges_commands(rolename: str, schema: str) -> list:
        # Create the 'revoke' commands
        x_role = "\"" + rolename + "\""
        x_schema = "\"" + schema + "\""
        statements = list()
        statements.append(" ".join(["REVOKE USAGE ON SCHEMA", x_schema, "FROM", x_role]))
        statements.append(" ".join(["REVOKE ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA", x_schema, "FROM", x_role]))
        statements.append(" ".join(["REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA", x_schema, "FROM", x_role]))
        statements.append(" ".join(["REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA", x_schema, "FROM", x_role]))
        return statements


class SchemaSetupClient(DDLClient):
    """Base Class for setting up a CHADO database schema"""

    def __init__(self, uri: str):
        super().__init__(uri)
        self.base = base.PublicBase
        self.metadata = self.base.metadata
        self.schema = self.metadata.schema

    def create(self):
        """Main function for filling the schema with life"""

        # Create the tables
        self.metadata.create_all(self.engine, tables=self.metadata.sorted_tables)

    def create_schema(self) -> None:
        """Creates a schema in the target database, if it doesn't exist yet"""
        if not self.schema_exists(self.schema):
            command = " ".join(["CREATE SCHEMA", self.schema])
            self.execute_ddl(command)

    def setup_inheritance(self, parent_table: str, child_tables: list) -> None:
        """Sets ups inheritance between parent table and child tables in a schema"""

        # Loop over all child tables
        full_parent_table = self.schema + '.' + parent_table
        for child_table in child_tables:
            full_child_table = self.schema + '.' + child_table

            # Check if the child table exists and if yes, if it already inherits from the parent table
            if self.table_exists(child_table, self.schema) and \
                    not self.table_inherits(full_child_table, full_parent_table):

                # Set up inheritance
                inherit_command = " ".join(["ALTER TABLE", full_child_table, "INHERIT", full_parent_table])
                self.execute_ddl(inherit_command)

    @staticmethod
    def create_trigger_function(name: str, definition: str) -> str:
        return "CREATE OR REPLACE FUNCTION " + name + "()\n" \
               + "RETURNS trigger\nLANGUAGE plpgsql\nAS $function$\nBEGIN\n" \
               + definition + ";" \
               + "\nEND;\n$function$"

    @staticmethod
    def create_generic_trigger(trigger_name: str, function_name: str, table: str) -> str:
        return "CREATE TRIGGER " + trigger_name \
               + " AFTER INSERT OR UPDATE OR DELETE ON " + table \
               + " FOR EACH ROW EXECUTE PROCEDURE " + function_name + "()"


class PublicSchemaSetupClient(SchemaSetupClient):
    """Class for setting up the general tables of a CHADO database"""

    def __init__(self, uri: str):
        """Constructor"""
        super().__init__(uri)
        self.modules = [general, cv, organism, pub, sequence]


class AuditSchemaSetupClient(SchemaSetupClient):
    """Class for setting up an audit schema for a CHADO database"""

    def __init__(self, uri: str):
        """Constructor"""
        super().__init__(uri)
        self.modules = [audit]
        self.base = base.AuditBase
        self.metadata = self.base.metadata
        self.schema = self.metadata.schema
        self.master_table = audit.Audit.__table__

    def create(self):
        """Main function for filling the schema with life"""

        # Make sure all required tables in the public schema exist
        public_client = PublicSchemaSetupClient(self.uri)
        public_client.create()
        data_tables = public_client.metadata.sorted_tables

        # Create the schema
        self.create_schema()

        # Create the tables
        audit_tables = self.create_audit_tables(data_tables)
        audit_tablenames = [table.name for table in audit_tables]
        self.metadata.create_all(self.engine, tables=([self.master_table] + audit_tables))

        # Set up inheritance
        self.setup_inheritance(self.master_table.name, audit_tablenames)

        # Create triggers
        self.create_audit_triggers(audit_tables)

    def create_audit_tables(self, data_tables: list) -> list:
        """Creates an audit table for each given data table"""

        # Define the audit base table and extract constraints
        audit_base_table = self.master_table                                            # type: sqlalchemy.Table
        audit_tables = []

        # Loop over all data tables
        for data_table in data_tables:                                                  # type: sqlalchemy.Table

            # Create a new audit table
            audit_table = sqlalchemy.Table(data_table.name, self.metadata)

            # Copy the columns of the audit base table to the new table
            for audit_column in audit_base_table.columns:                               # type: sqlalchemy.Column
                new_column = sqlalchemy.Column(audit_column.name, audit_column.type, nullable=audit_column.nullable,
                                               server_default=audit_column.server_default,
                                               primary_key=audit_column.primary_key)
                audit_table.append_column(new_column)

            # Copy the columns of the data table to the new table
            for data_column in data_table.columns:                                      # type: sqlalchemy.Column
                new_column = sqlalchemy.Column(data_column.name, data_column.type, nullable=data_column.nullable,
                                               server_default=data_column.server_default)
                audit_table.append_column(new_column)

            # Add table to list
            audit_tables.append(audit_table)

        # Return all audit tables
        return audit_tables

    def create_audit_triggers(self, audit_tables: list) -> None:
        """Creates the functions that trigger insertions of new lines in the audit table
        after each operation on the corresponding data table, and the triggers on the data tables"""

        # Retrieve columns of parent table as reference
        parent_column_names = [col.name for col in self.master_table.columns]

        # Loop over all audit tables
        for table in audit_tables:

            # Get table name
            full_table_name = self.schema + "." + table.name

            # Retrieve columns of this table; exclude columns inherited from parent table
            column_names = [col.name for col in table.columns]
            data_column_names = [name for name in column_names if name not in parent_column_names]

            # Define trigger function
            function_name = self.schema + ".public_" + table.name + "_proc"
            function_definition = self.generic_audit_function(full_table_name, data_column_names)
            function_creator = self.create_trigger_function(function_name, function_definition)

            # Create/replace trigger function
            self.execute_ddl(function_creator)

            # Define trigger
            trigger_name = table.name + "_audit_tr"
            trigger_creator = self.create_generic_trigger(trigger_name, function_name, table.name)

            # Create trigger, if is doesn't exist yet
            if not self.trigger_exists(trigger_name):
                self.execute_ddl(trigger_creator)

    @staticmethod
    def generic_audit_function(table: str, columns: list) -> str:
        return "IF TG_OP = 'INSERT' OR TG_OP = 'UPDATE' THEN\n" \
               + "\tINSERT INTO " + table + "(type, " + utils.list_to_string(columns, ", ") + ")" \
               + " VALUES (CAST(TG_OP AS " + base.operation_type.name + "), " \
               + utils.list_to_string(columns, ", ", "NEW") + ");\n" \
               + "\tRETURN NEW;\n" \
               + "ELSE\n" \
               + "\tINSERT INTO " + table + "(type, " + utils.list_to_string(columns, ", ") + ")" \
               + " VALUES (CAST(TG_OP AS " + base.operation_type.name + "), " \
               + utils.list_to_string(columns, ", ", "OLD") + ");\n" \
               + "\tRETURN OLD;\n" \
               + "END IF"
