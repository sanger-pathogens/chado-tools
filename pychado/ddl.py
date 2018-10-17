import sqlalchemy.sql
import sqlalchemy.orm.attributes
import sqlalchemy.engine
import sqlalchemy.schema
import sqlalchemy.event
from pychado import utils
from pychado.orm import base, general, cv, organism, pub, sequence, audit


class ChadoEngine:
    """Base Class for setting up a CHADO database"""

    def __init__(self, uri: str):
        """Constructor - connect to database"""
        self.uri = uri
        self.engine = sqlalchemy.create_engine(uri)                                 # type: sqlalchemy.engine.Engine
        session_maker = sqlalchemy.orm.sessionmaker(bind=self.engine)
        self.session = session_maker()                                              # type: sqlalchemy.orm.Session

        self.base = base.PublicBase
        self.metadata = self.base.metadata
        self.schema = self.metadata.schema

    def __del__(self):
        """Destructor - disconnect from database"""
        self.session.close()
        self.engine.dispose()

    def create(self):
        """Basis function for schema creation"""
        pass

    def create_schema(self) -> None:
        """Creates a schema in the target database, if it doesn't exist yet"""

        # Create a query to check for schema existence
        schemata_table = sqlalchemy.text("information_schema.schemata")
        schemata_condition = sqlalchemy.text("schema_name=:schema")
        query = sqlalchemy.exists().select_from(schemata_table).where(schemata_condition.bindparams(schema=self.schema))

        # Check if schema exists
        if not self.session.query(query).scalar():

            # Assure schema is created before the tables
            sqlalchemy.event.listen(self.metadata, "before_create", sqlalchemy.schema.CreateSchema(self.schema))

    def setup_inheritance(self, parent_table: str, child_tables: list) -> None:
        """Sets ups inheritance between parent table and child tables in a schema"""

        # Initiate query components
        table_exists_table = sqlalchemy.text("information_schema.tables")
        table_exists_condition = sqlalchemy.text("table_schema=:schema AND table_name=:child")
        inherits_table = sqlalchemy.text("pg_catalog.pg_inherits")
        inherits_condition = sqlalchemy.text(r"inhparent=:parent\:\:regclass AND inhrelid=:child\:\:regclass")

        # Loop over all child tables
        full_parent_table = self.schema + '.' + parent_table
        for child_table in child_tables:
            full_child_table = self.schema + '.' + child_table

            # Generate queries and bind parameters
            exists_query = sqlalchemy.exists().select_from(table_exists_table).where(
                table_exists_condition.bindparams(schema=self.schema, child=child_table))
            inherits_query = sqlalchemy.exists().select_from(inherits_table).where(
                inherits_condition.bindparams(parent=full_parent_table, child=full_child_table))

            # Check if the child table exists and if it already inherits from the parent table
            if not self.session.query(exists_query).scalar() or not self.session.query(inherits_query).scalar():

                # Table doesn't exist or doesn't inherit yet. Set up inheritance
                inherit_command = " ".join(["ALTER TABLE", full_child_table, "INHERIT", full_parent_table])
                sqlalchemy.event.listen(self.metadata, "after_create", sqlalchemy.DDL(inherit_command))

    @staticmethod
    def create_trigger_function(name: str, definition: str) -> str:
        return "CREATE OR REPLACE FUNCTION " + name + "()\n" \
               + "RETURNS trigger\nLANGUAGE plpgsql\nAS $function$\nBEGIN\n" \
               + definition \
               + "\nEND;\n$function$"

    @staticmethod
    def create_generic_trigger(trigger_name: str, function_name: str, table: str) -> str:
        return "CREATE TRIGGER " + trigger_name \
               + " AFTER INSERT OR UPDATE OR DELETE ON " + table \
               + " FOR EACH ROW EXECUTE PROCEDURE " + function_name + "();"


class PublicSchemaEngine(ChadoEngine):
    """Class for setting up the general tables of a CHADO database"""

    def __init__(self, uri: str):
        """Constructor"""
        ChadoEngine.__init__(self, uri)
        self.modules = [general, cv, organism, pub, sequence]

    def create(self):
        """Main function for filling the schema with life"""

        # Create the schema
        self.create_schema()

        # Create the tables
        self.metadata.create_all(self.engine, tables=self.metadata.sorted_tables)


class AuditSchemaEngine(ChadoEngine):
    """Class for setting up an audit schema for a CHADO database"""

    def __init__(self, uri: str):
        """Constructor"""
        ChadoEngine.__init__(self, uri)
        self.base = base.AuditBase
        self.modules = [audit]
        self.metadata = self.base.metadata
        self.schema = self.metadata.schema
        self.master_table = audit.Audit.__table__

    def create(self):
        """Main function for filling the schema with life"""

        # Make sure all required tables in the public schema exists
        public_engine = PublicSchemaEngine(self.uri)
        public_engine.create()
        data_tables = public_engine.metadata.sorted_tables

        # Create the schema
        self.create_schema()

        # Create the tables
        audit_tables = self.create_audit_tables(data_tables)
        audit_tablenames = [table.name for table in audit_tables]

        # Set up inheritance
        self.setup_inheritance(self.master_table.name, audit_tablenames)

        # Create triggers
        self.create_audit_triggers(audit_tables)

        # Transfer all created objects to the actual database
        audit_tables.insert(0, self.master_table)
        self.metadata.create_all(self.engine, tables=audit_tables)

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

        # Initiate query components
        triggers_table = sqlalchemy.text("information_schema.triggers")
        triggers_condition = sqlalchemy.text("trigger_name=:trigger_name")

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

            # Assert function is created after table
            sqlalchemy.event.listen(self.metadata, "after_create", sqlalchemy.DDL(function_creator))

            # Define trigger
            trigger_name = table.name + "_audit_tr"
            trigger_creator = self.create_generic_trigger(trigger_name, function_name, table.name)

            # Check if trigger already exists
            trigger_exists_query = sqlalchemy.exists().select_from(triggers_table).where(
                triggers_condition.bindparams(trigger_name=trigger_name))
            if not self.session.query(trigger_exists_query).scalar():

                # Assert trigger is created after table
                sqlalchemy.event.listen(self.metadata, "after_create", sqlalchemy.DDL(trigger_creator))

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
               + "END IF;"
