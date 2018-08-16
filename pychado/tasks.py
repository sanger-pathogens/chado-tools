from pychado import utils, dbutils, queries


def read_configuration_file(filename: str) -> dict:
    """Reads data from a configuration file into a dictionary"""
    if not filename:
        filename = dbutils.default_configuration_file()
    return utils.parse_yaml(filename)


def check_access(connection_parameters: dict, database: str, task: str) -> bool:
    """Checks if the database of interest exists and is accessible. If the database doesn't exist, but the
    task implies its creation, create it. Otherwise exit the program."""
    connection_dsn = dbutils.generate_dsn(connection_parameters)
    exists = dbutils.exists(connection_dsn, database)
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
            # Database doesn't exist, but task implies its creation. Create it
            dbutils.create_database(connection_dsn, database)
            return True
        else:
            # Database doesn't exist, and task can't be completed. Return without further action
            print("Database does not exist. Task can't be completed.")
            return False


def run_command_with_arguments(command: str, arguments, connection_parameters: dict) -> None:
    """Runs a specified sub-command with the supplied arguments"""

    # Create connection strings
    connection_dsn = dbutils.generate_dsn(connection_parameters)
    connection_uri = dbutils.generate_uri(connection_parameters)

    # Run the command
    if command == "init":
        # Set the default connection parameters
        dbutils.set_default_parameters()
    elif command == "reset":
        # Reset the default connection parameters to factory settings
        dbutils.reset_default_parameters()
    elif command == "connect":
        # Connect to a PostgreSQL database for an interactive session
        dbutils.connect_to_database(connection_uri)
    elif command == "create":
        # Setup a PostgreSQL database according to a schema
        schema = arguments.schema
        if not schema:
            schema = dbutils.download_schema(dbutils.default_schema_url())
        dbutils.setup_database(connection_uri, schema)
    elif command == "dump":
        # Dump a PostgreSQL database into an archive file
        dbutils.dump_database(connection_uri, arguments.archive)
    elif command == "restore":
        # Restore a PostgreSQL database from an archive file
        dbutils.restore_database(connection_uri, arguments.archive)
    elif command == "import":
        # Import data from a text file to a table of a PostgreSQL database
        dbutils.copy_from_file(connection_dsn, arguments.table, arguments.input_file, arguments.delimiter)
    elif command == "export":
        # Export data from a table of a PostgreSQL database to a text file
        dbutils.copy_to_file(connection_dsn, arguments.table, arguments.output_file, arguments.delimiter,
                             arguments.include_header)
    elif command == "query":
        # Query a PostgreSQL database and export the result to a text file
        if arguments.query:
            query = arguments.query
        else:
            query = utils.read_text(arguments.input_file)
        dbutils.query_to_file(connection_dsn, query, tuple(), arguments.output_file, arguments.delimiter,
                              arguments.include_header)
    elif command == "stats":
        # Obtain statistics to updates in a CHADO database
        query = queries.load_stats_query(arguments)
        parameters = queries.specify_stats_parameters(arguments)
        dbutils.query_to_file(connection_dsn, query, parameters, arguments.output_file, arguments.delimiter,
                              arguments.include_header)
    else:
        print("Functionality '" + command + "' is not yet implemented.")


def run_sub_command_with_arguments(command: str, sub_command: str, arguments, connection_parameters: dict) -> None:
    """Runs a specified sub-command with the supplied arguments"""

    # Create connection strings
    connection_dsn = dbutils.generate_dsn(connection_parameters)

    # Run the command
    if command == "list":
        # List all entities of a specified type in the CHADO database and export the result to a text file
        query = queries.load_list_query(sub_command, arguments)
        parameters = queries.specify_list_parameters(sub_command, arguments)
        dbutils.query_to_file(connection_dsn, query, parameters, arguments.output_file, arguments.delimiter,
                             arguments.include_header)
    elif command == "insert":
        # Insert a new entity of a specified type into the CHADO database
        statement = queries.load_insert_statement(sub_command)
        parameters = queries.specify_insert_parameters(sub_command, arguments)
        dbutils.connect_and_execute_statement(connection_dsn, statement, parameters)
        print("Inserted a new " + sub_command + " into the database.")
    elif command == "delete":
        # Delete an entity of a specified type from the CHADO database
        statement = queries.load_delete_statement(sub_command, arguments)
        parameters = queries.specify_delete_parameters(sub_command, arguments)
        dbutils.connect_and_execute_statement(connection_dsn, statement, parameters)
        print("Deleted an existing " + sub_command + " from the database.")
    else:
        print("Functionality '" + command + "' is not yet implemented.")
