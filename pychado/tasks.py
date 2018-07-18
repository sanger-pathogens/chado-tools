from pychado import dbutils


def connect(configuration_file: str, dbname: str) -> None:
    """Connects to a PostgreSQL database for an interactive session"""
    connection_details = dbutils.read_configuration_file(configuration_file)
    connection_dsn = dbutils.generate_dsn(connection_details)
    if not dbutils.exists(connection_dsn, dbname):
        # Database doesn't exist - return without further action
        print("Database does not exist.")
    else:
        # Establish a connection to an SQL server by running a subprocess
        connection_details["database"] = dbname
        connection_uri = dbutils.generate_uri(connection_details)
        dbutils.connect_to_database(connection_uri)


def create(configuration_file: str, schema_file: str, dbname: str) -> None:
    """Creates a new PostgreSQL database and sets it up according to a schema"""
    # Create database
    connection_details = dbutils.read_configuration_file(configuration_file)
    connection_dsn = dbutils.generate_dsn(connection_details)
    if dbutils.exists(connection_dsn, dbname):
        # Database already exists - return without further action
        print("Database already exists.")
    else:
        # Database doesn't exist - create it
        dbutils.create_database(connection_dsn, dbname)

    # Setup database
    if not schema_file:
        schema_file = dbutils.download_schema(dbutils.default_schema_url())
    connection_details["database"] = dbname
    connection_uri = dbutils.generate_uri(connection_details)
    dbutils.setup_database(connection_uri, schema_file)


def dump(configuration_file: str, dbname: str, archive: str) -> None:
    """Dumps a PostgreSQL database into an archive file"""
    connection_details = dbutils.read_configuration_file(configuration_file)
    connection_dsn = dbutils.generate_dsn(connection_details)
    if not dbutils.exists(connection_dsn, dbname):
        # Database doesn't exist - return without further action
        print("Database does not exist.")
    else:
        # Dump the database by running a subprocess
        connection_details["database"] = dbname
        connection_uri = dbutils.generate_uri(connection_details)
        dbutils.dump_database(connection_uri, archive)


def restore(configuration_file: str, dbname: str, archive: str) -> None:
    """Restores a PostgreSQL database from an archive file"""
    # Create database
    connection_details = dbutils.read_configuration_file(configuration_file)
    connection_dsn = dbutils.generate_dsn(connection_details)
    if dbutils.exists(connection_dsn, dbname):
        # Database already exists - return without further action
        print("Database already exists.")
    else:
        # Database doesn't exist - create it
        dbutils.create_database(connection_dsn, dbname)

    # Restore database
    connection_details["database"] = dbname
    connection_uri = dbutils.generate_uri(connection_details)
    dbutils.restore_database(connection_uri, archive)


def importer(configuration_file: str, dbname: str, table: str, filename: str, delimiter: str) -> None:
    """Imports data from a text file into a table of a CHADO database"""
    connection_details = dbutils.read_configuration_file(configuration_file)
    connection_dsn = dbutils.generate_dsn(connection_details)
    if not dbutils.exists(connection_dsn, dbname):
        # Database doesn't exist - return without further action
        print("Database does not exist.")
    else:
        # Import the data
        connection_details["database"] = dbname
        connection_dsn = dbutils.generate_dsn(connection_details)
        dbutils.copy_from_file(connection_dsn, table, filename, delimiter)


def exporter(configuration_file: str, dbname: str, table: str, filename: str, delimiter: str) -> None:
    """Exports data from a table of a CHADO database into a text file"""
    connection_details = dbutils.read_configuration_file(configuration_file)
    connection_dsn = dbutils.generate_dsn(connection_details)
    if not dbutils.exists(connection_dsn, dbname):
        # Database doesn't exist - return without further action
        print("Database does not exist.")
    else:
        # Export the data
        connection_details["database"] = dbname
        connection_dsn = dbutils.generate_dsn(connection_details)
        dbutils.copy_to_file(connection_dsn, table, filename, delimiter)
