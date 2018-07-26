from pychado import utils, dbutils


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
            # Database already exists - no need to create it
            print("Database already exists.")
        return True
    else:
        if task in ["create", "restore"]:
            # Database doesn't exist, but task implies its creation - create it
            dbutils.create_database(connection_dsn, database)
            return True
        else:
            # Database doesn't exist, and task can't be completed - return without further action
            print("Database does not exist.")
            return False


def run_task_with_arguments(task: str, arguments, connection_parameters: dict):
    """Runs a specified sub-command with the supplied arguments"""

    # Create connection strings
    connection_dsn = dbutils.generate_dsn(connection_parameters)
    connection_uri = dbutils.generate_uri(connection_parameters)

    # Run the command
    if task == "connect":
        # Connect to a PostgreSQL database for an interactive session
        dbutils.connect_to_database(connection_uri)
    elif task == "create":
        # Setup a PostgreSQL database according to a schema
        schema = arguments.schema
        if not schema:
            schema = dbutils.download_schema(dbutils.default_schema_url())
        dbutils.setup_database(connection_uri, schema)
    elif task == "dump":
        # Dump a PostgreSQL database into an archive file
        dbutils.dump_database(connection_uri, arguments.archive)
    elif task == "restore":
        # Restore a PostgreSQL database from an archive file
        dbutils.restore_database(connection_uri, arguments.archive)
    elif task == "import":
        # Import data from a text file into a table of a PostgreSQL database
        dbutils.copy_from_file(connection_dsn, arguments.table, arguments.input_file, arguments.delimiter)
    elif task == "export":
        # Export data from a table of a PostgreSQL database into a text file
        dbutils.copy_to_file(connection_dsn, arguments.table, arguments.output_file, arguments.delimiter,
                             arguments.include_header)
    elif task == "query":
        # Query a PostgreSQL database and exports the result into a text file
        if arguments.query:
            query = arguments.query
        else:
            query = utils.read_text(arguments.input_file)
        dbutils.query_to_file(connection_dsn, query, arguments.output_file, arguments.delimiter,
                              arguments.include_header)
    else:
        raise ValueError("Functionality '" + task + "' is not yet implemented.")
