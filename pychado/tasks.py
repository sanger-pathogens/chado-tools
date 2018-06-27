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


def connect(configurationFile: str) -> None:
    """Connects to a CHADO database and brings back a command line prompt"""

    # Create a URI based on connection parameters from a configuration file
    connectionDetails = utils.parseYaml(configurationFile)
    connectionURI = generate_uri(connectionDetails)

    # Establish a connection to an SQL server by running a subprocess
    print("Establishing connection to database...")
    command = ["psql", connectionURI]
    subprocess.run(command)
    print("Connection to database closed.")


def create(configurationFile: str, schemaFile: str, dbname: str) -> None:
    """Creates a new instance of the CHADO schema"""

    # Create a DSN based on connection parameters from a configuration file
    connectionDetails = utils.parseYaml(configurationFile)
    dsn = generate_dsn(connectionDetails)

    # Create a new database and set it up with the provided schema
    conn = psycopg2.connect(dsn)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("CREATE DATABASE " + dbname + ";")
    cur.close()
    conn.close()
    print("Database has been created.")

    # Download schema if not saved locally
    localSchemaFile = schemaFile
    if schemaFile.startswith("http"):
        print("Downloading database schema...")
        try:
            localSchemaFile, headers = urllib.request.urlretrieve(schemaFile)
        except urllib.error.HTTPError:
            raise Exception("HTTP Error 404: The address '" + schemaFile + "' does not exist.")

    # Set up the database with the provided schema
    connectionDetails["database"] = dbname
    connectionURI = generate_uri(connectionDetails)
    command = ["psql", "-q", "-f", localSchemaFile, connectionURI]
    subprocess.run(command)
    print("Database schema has been set up.")


def dump(configurationFile: str, dumpFile: str) -> None:
    """Dump a PostgreSQL instance of the CHADO schema"""

    # Create a URI based on connection parameters from a configuration file
    connectionDetails = utils.parseYaml(configurationFile)
    connectionURI = generate_uri(connectionDetails)

    # Dump the database scheme by running a subprocess
    command = ["pg_dump", "-s"]
    if dumpFile is not "-":
        command.append("-f")
        command.append(dumpFile)
    command.append(connectionURI)
    subprocess.run(command)
    print("Database schema has been dumped.")
