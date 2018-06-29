import pkg_resources
import subprocess
import psycopg2
import urllib.request, urllib.error
from pychado import utils


def generate_uri(connectionDetails: dict) -> str:
    """Creates a connection URI"""
    uriAsList = ["postgresql://"]
    if "user" in connectionDetails and connectionDetails["user"] is not None:
        uriAsList.append(connectionDetails["user"])
        if "password" in connectionDetails and connectionDetails["password"] is not None:
            uriAsList.append(":" + connectionDetails["password"])
        uriAsList.append("@")
    if "host" in connectionDetails and connectionDetails["host"] is not None:
        uriAsList.append(connectionDetails["host"])
    if "port" in connectionDetails and connectionDetails["port"] is not None:
        uriAsList.append(":" + connectionDetails["port"])
    if "database" in connectionDetails and connectionDetails["database"] is not None:
        uriAsList.append("/" + connectionDetails["database"])
    return "".join(uriAsList)


def generate_dsn(connectionDetails: dict) -> str:
    """Creates a connection DSN"""
    dsnAsList = []
    if "database" in connectionDetails and connectionDetails["database"] is not None:
        dsnAsList.append("dbname=" + connectionDetails["database"] + " ")
    if "user" in connectionDetails and connectionDetails["user"] is not None:
        dsnAsList.append("user=" + connectionDetails["user"] + " ")
    if "password" in connectionDetails and connectionDetails["password"] is not None:
        dsnAsList.append("password=" + connectionDetails["password"] + " ")
    if "host" in connectionDetails and connectionDetails["host"] is not None:
        dsnAsList.append("host=" + connectionDetails["host"] + " ")
    if "port" in connectionDetails and connectionDetails["port"] is not None:
        dsnAsList.append("port=" + connectionDetails["port"] + " ")
    return "".join(dsnAsList).strip()


def get_schema_url() -> str:
    """Obtains the URL for a database schema from parsing a YAML file"""
    yamlFile = pkg_resources.resource_filename("pychado", "data/gmodSchema.yml")
    defaultSchema = utils.parse_yaml(yamlFile)
    return defaultSchema["url"].replace("<VERSION>", defaultSchema["version"])


def download_schema() -> str:
    """Downloads a file with a database schema"""
    print("Downloading database schema...")
    url = get_schema_url()
    try:
        schemaFile, headers = urllib.request.urlretrieve(url)
        return schemaFile
    except urllib.error.HTTPError:
        raise Exception("HTTP Error 404: The address '" + url + "' does not exist.")


def exists(dsn: str, dbname: str) -> bool:
    """Checks if a PostgreSQL database exists"""
    conn = psycopg2.connect(dsn)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM pg_catalog.pg_database WHERE datname = '" + dbname + "'")
    res = cur.fetchone()
    cur.close()
    conn.close()
    return bool(res[0])


def create_database(dsn: str, dbname: str) -> None:
    """Creates a PostgreSQL database"""

    # Check if the database already exists
    if exists(dsn, dbname):
        # Database exists - return without further action
        print("Database already exists.")
    else:
        # Database doesn't exist - create it
        conn = psycopg2.connect(dsn)
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute("CREATE DATABASE " + dbname)
        cur.close()
        conn.close()
        print("Database has been created.")


def drop_database(dsn: str, dbname: str) -> None:
    """Deletes a PostgreSQL database"""

    # Check if the database exists at all
    if not exists(dsn, dbname):
        # Database doesn't exist - return without further action
        print("Database does not exist.")
    else:
        # Database exists - delete it
        conn = psycopg2.connect(dsn)
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute("DROP DATABASE " + dbname)
        cur.close()
        conn.close()
        print("Database has been deleted.")


def connect(configurationFile: str, dbname: str) -> None:
    """Connects to a PostgreSQL database and brings back a command line prompt"""

    # Create a URI based on connection parameters from a configuration file
    if not configurationFile:
        configurationFile = pkg_resources.resource_filename("pychado", "data/exampleDB.yml")
    connectionDetails = utils.parse_yaml(configurationFile)
    connectionDSN = generate_dsn(connectionDetails)

    # Check if the database exists
    if exists(connectionDSN, dbname):
        # Establish a connection to an SQL server by running a subprocess
        print("Establishing connection to database...")
        connectionDetails["database"] = dbname
        connectionURI = generate_uri(connectionDetails)
        command = ["psql", connectionURI]
        subprocess.run(command)
        print("Connection to database closed.")
    else:
        # Database doesn't exist - return without further action
        print("Database does not exist.")


def create(configurationFile: str, schemaFile: str, dbname: str) -> None:
    """Creates a new PostgreSQL database and sets it up according to a schema"""

    # Create DSN based on connection parameters from a configuration file
    if not configurationFile:
        configurationFile = pkg_resources.resource_filename("pychado", "data/exampleDB.yml")
    connectionDetails = utils.parse_yaml(configurationFile)
    connectionDSN = generate_dsn(connectionDetails)

    # Create the database
    create_database(connectionDSN, dbname)

    # Download schema if not saved locally
    if not schemaFile:
        schemaFile = download_schema()

    # Set up the database with the provided schema
    connectionDetails["database"] = dbname
    connectionURI = generate_uri(connectionDetails)
    command = ["psql", "-q", "-f", schemaFile, connectionURI]
    subprocess.run(command)
    print("Database schema has been set up.")


def dump(configurationFile: str, dbname: str, archive: str) -> None:
    """Dumps a PostgreSQL database into an archive file"""

    # Create a DSN based on connection parameters from a configuration file
    if not configurationFile:
        configurationFile = pkg_resources.resource_filename("pychado", "data/exampleDB.yml")
    connectionDetails = utils.parse_yaml(configurationFile)
    connectionDSN = generate_dsn(connectionDetails)

    # Check if the database exists
    if exists(connectionDSN, dbname):
        # Dump the database by running a subprocess
        connectionDetails["database"] = dbname
        connectionURI = generate_uri(connectionDetails)
        command = ["pg_dump", "-f", archive, "--format=custom", connectionURI]
        subprocess.run(command)
        print("Database has been dumped.")
    else:
        # Database doesn't exist - return without further action
        print("Database does not exist.")


def restore(configurationFile: str, dbname: str, archive: str) -> None:
    """Restores a PostgreSQL database from an archive file"""

    # Create DSN based on connection parameters from a configuration file
    if not configurationFile:
        configurationFile = pkg_resources.resource_filename("pychado", "data/exampleDB.yml")
    connectionDetails = utils.parse_yaml(configurationFile)
    connectionDSN = generate_dsn(connectionDetails)

    # Create a database with the provided name
    create_database(connectionDSN, dbname)

    # Restore into the created database by running a subprocess
    connectionDetails["database"] = dbname
    connectionURI = generate_uri(connectionDetails)
    command = ["pg_restore", "--clean", "--if-exists", "--format=custom", "-d", connectionURI, archive]
    subprocess.run(command)
    print("Database has been restored.")
