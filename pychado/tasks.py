from pychado import utils, dbutils, queries
from pychado.io import load_ontology


def create_connection_string(filename: str, dbname: str) -> str:
    """Reads database connection parameters from a configuration file and generates a connection string"""
    if not filename:
        filename = dbutils.default_configuration_file()
    connection_parameters = utils.parse_yaml(filename)
    connection_parameters["database"] = dbname
    return dbutils.generate_uri(connection_parameters)


def check_access(connection_uri: str, task: str) -> bool:
    """Checks if the database of interest exists and is accessible. If the database doesn't exist, but the
    task implies its creation, create it. Otherwise exit the program."""
    exists = dbutils.exists(connection_uri)
    if exists:
        if task in ["create", "restore"]:
            # Database already exists, we should not overwrite it. Return without further action
            print("Database already exists. Overwriting is not permitted.")
            return False
        else:
            # Database exists, that's all we need
            return True
    else:
        if task in ["create", "restore"]:
            # Database doesn't exist, but task implies its creation
            return True
        else:
            # Database doesn't exist, and task can't be completed. Return without further action
            print("Database does not exist. Task can't be completed.")
            return False


def setup(command: str) -> None:
    """Initiates or resets the default connection parameters"""
    if command == "init":
        # Set the default connection parameters
        dbutils.set_default_parameters()
    elif command == "reset":
        # Reset the default connection parameters to factory settings
        dbutils.reset_default_parameters()
    else:
        print("Functionality '" + command + "' is not yet implemented.")


def run_command_with_arguments(command: str, sub_command: str, arguments, connection_uri: str) -> None:
    """Runs a specified sub-command with the supplied arguments"""

    # Run the command
    if command == "connect":
        # Connect to a PostgreSQL database for an interactive session
        dbutils.connect_to_database(connection_uri)
    elif command == "admin" and sub_command == "create":
        # Setup a PostgreSQL database according to a schema
        dbutils.create_database(connection_uri)
        schema = arguments.schema
        if not schema:
            schema = utils.download_file(dbutils.default_schema_url())
        dbutils.setup_database(connection_uri, schema)
    elif command == "admin" and sub_command == "drop":
        # Drop a PostgreSQL database
        dbutils.drop_database(connection_uri)
    elif command == "admin" and sub_command == "dump":
        # Dump a PostgreSQL database into an archive file
        dbutils.dump_database(connection_uri, arguments.archive)
    elif command == "admin" and sub_command == "restore":
        # Restore a PostgreSQL database from an archive file
        dbutils.create_database(connection_uri)
        dbutils.restore_database(connection_uri, arguments.archive)
    elif command == "query":
        # Query a PostgreSQL database and export the result to a text file
        if arguments.query:
            query = arguments.query
        else:
            query = utils.read_text(arguments.input_file)
        dbutils.query_to_file(connection_uri, query, {}, arguments.output_file, arguments.delimiter,
                              arguments.include_header)
    elif command == "stats":
        # Obtain statistics to updates in a CHADO database
        query = queries.load_stats_query(arguments)
        parameters = queries.specify_stats_parameters(arguments)
        dbutils.query_to_file(connection_uri, query, parameters, arguments.output_file, arguments.delimiter,
                              arguments.include_header)
    elif command == "list":
        # List all entities of a specified type in the CHADO database and export the result to a text file
        query = queries.load_list_query(sub_command, arguments)
        parameters = queries.specify_list_parameters(sub_command, arguments)
        dbutils.query_to_file(connection_uri, query, parameters, arguments.output_file, arguments.delimiter,
                              arguments.include_header)
    elif command == "insert":
        # Insert a new entity of a specified type into the CHADO database
        statement = queries.load_insert_statement(sub_command)
        parameters = queries.specify_insert_parameters(sub_command, arguments)
        dbutils.connect_and_execute(connection_uri, statement, parameters)
    elif command == "delete":
        # Delete an entity of a specified type from the CHADO database
        statement = queries.load_delete_statement(sub_command, arguments)
        parameters = queries.specify_delete_parameters(sub_command, arguments)
        dbutils.connect_and_execute(connection_uri, statement, parameters)
    elif command == "import":
        # Import entities of a specified type into the CHADO database
        run_import_command(sub_command, arguments, connection_uri)
    else:
        print("Functionality '" + command + "' is not yet implemented.")


def run_import_command(specifier: str, arguments, uri: str) -> None:
    """Imports data from a file into a database"""
    file = arguments.input_file
    if arguments.input_url:
        file = utils.download_file(arguments.input_url)

    if specifier == "ontology":
        loader = load_ontology.OntologyLoader(uri, arguments.verbose)
        loader.load(file, arguments.format, arguments.database_authority)
    else:
        print("Functionality 'import " + specifier + "' is not yet implemented.")
