from pychado import dbutils


def connect(configurationFile: str, dbname: str) -> None:
    """Connects to a PostgreSQL database for an interactive session"""
    connectionDetails = dbutils.read_configuration_file(configurationFile)
    connectionDSN = dbutils.generate_dsn(connectionDetails)
    if not dbutils.exists(connectionDSN, dbname):
        # Database doesn't exist - return without further action
        print("Database does not exist.")
    else:
        # Establish a connection to an SQL server by running a subprocess
        connectionDetails["database"] = dbname
        connectionURI = dbutils.generate_uri(connectionDetails)
        dbutils.connect_to_database(connectionURI)


def create(configurationFile: str, schemaFile: str, dbname: str) -> None:
    """Creates a new PostgreSQL database and sets it up according to a schema"""
    # Create database
    connectionDetails = dbutils.read_configuration_file(configurationFile)
    connectionDSN = dbutils.generate_dsn(connectionDetails)
    if dbutils.exists(connectionDSN, dbname):
        # Database already exists - return without further action
        print("Database already exists.")
    else:
        # Database doesn't exist - create it
        dbutils.create_database(connectionDSN, dbname)

    # Setup database
    if not schemaFile:
        schemaFile = dbutils.download_schema(dbutils.default_schema_url())
    connectionDetails["database"] = dbname
    connectionURI = dbutils.generate_uri(connectionDetails)
    dbutils.setup_database(connectionURI, schemaFile)


def dump(configurationFile: str, dbname: str, archive: str) -> None:
    """Dumps a PostgreSQL database into an archive file"""
    connectionDetails = dbutils.read_configuration_file(configurationFile)
    connectionDSN = dbutils.generate_dsn(connectionDetails)
    if not dbutils.exists(connectionDSN, dbname):
        # Database doesn't exist - return without further action
        print("Database does not exist.")
    else:
        # Dump the database by running a subprocess
        connectionDetails["database"] = dbname
        connectionURI = dbutils.generate_uri(connectionDetails)
        dbutils.dump_database(connectionURI, archive)


def restore(configurationFile: str, dbname: str, archive: str) -> None:
    """Restores a PostgreSQL database from an archive file"""
    # Create database
    connectionDetails = dbutils.read_configuration_file(configurationFile)
    connectionDSN = dbutils.generate_dsn(connectionDetails)
    if dbutils.exists(connectionDSN, dbname):
        # Database already exists - return without further action
        print("Database already exists.")
    else:
        # Database doesn't exist - create it
        dbutils.create_database(connectionDSN, dbname)

    # Restore database
    connectionDetails["database"] = dbname
    connectionURI = dbutils.generate_uri(connectionDetails)
    dbutils.restore_database(connectionURI, archive)
