import pkg_resources
import subprocess
import psycopg2
import urllib.request
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


def default_schema_url() -> str:
    """Returns the URL of the default schema"""
    yamlFile = pkg_resources.resource_filename("pychado", "data/gmodSchema.yml")
    defaultSchema = utils.parse_yaml(yamlFile)
    return defaultSchema["url"].replace("<VERSION>", defaultSchema["version"])


def download_schema(url: str) -> str:
    """Downloads a file with a database schema"""
    print("Downloading database schema...")
    schemaFile, headers = urllib.request.urlretrieve(url)
    return schemaFile


def default_configuration_file() -> str:
    """Returns the name of the default configuration file"""
    return pkg_resources.resource_filename("pychado", "data/defaultDatabase.yml")


def read_configuration_file(filename: str) -> dict:
    """Reads data from a configuration file into a dictionary"""
    if not filename:
        filename = default_configuration_file()
    return utils.parse_yaml(filename)


def open_connection(dsn: str, autocomm=False) -> psycopg2._psycopg.connection:
    """Connects to a PostgreSQL database"""
    connection = psycopg2.connect(dsn)
    if autocomm:
        connection.autocommit = True
    return connection


def close_connection(connection: psycopg2._psycopg.connection):
    """Closes the connection to a PostgreSQL database"""
    connection.close()


def execute_query(connection: psycopg2._psycopg.connection, query: str) -> list:
    """Executes an SQL query in an opened PostgreSQL database and returns the query result"""
    cursor = connection.cursor()
    cursor.execute(query)
    result = cursor.fetchall()
    cursor.close()
    return result


def execute_statement(connection: psycopg2._psycopg.connection, statement: str):
    """Executes an SQL statement in an opened PostgreSQL database"""
    cursor = connection.cursor()
    cursor.execute(statement)
    cursor.close()


def connect_and_execute_query(dsn: str, query: str) -> list:
    """Connects to a database, executes an SQL query, and returns the result"""
    connection = open_connection(dsn)
    result = execute_query(connection, query)
    close_connection(connection)
    return result


def connect_and_execute_statement(dsn: str, statement: str, autocomm=False):
    """Connects to a database and executes an SQL statement"""
    connection = open_connection(dsn, autocomm)
    execute_statement(connection, statement)
    close_connection(connection)


def exists(dsn: str, dbname: str) -> bool:
    """Checks if a PostgreSQL database exists"""
    sql = "SELECT COUNT(*) FROM pg_catalog.pg_database WHERE datname = '" + dbname + "'"
    result = connect_and_execute_query(dsn, sql)
    return bool(result[0][0])


def create_database(dsn: str, dbname: str) -> None:
    """Creates a PostgreSQL database"""
    sql = "CREATE DATABASE " + dbname
    connect_and_execute_statement(dsn, sql, autocomm=True)
    print("Database has been created.")


def drop_database(dsn: str, dbname: str) -> None:
    """Deletes a PostgreSQL database"""
    sql = "DROP DATABASE " + dbname
    connect_and_execute_statement(dsn, sql, autocomm=True)
    print("Database has been deleted.")


def dump_database(uri: str, archive: str):
    """Dumps a PostgreSQL database into an archive file"""
    command = ["pg_dump", "-f", archive, "--format=custom", uri]
    subprocess.run(command)
    print("Database has been dumped.")


def restore_database(uri: str, archive: str):
    """Restores a PostgreSQL database from an archive file"""
    command = ["pg_restore", "--clean", "--if-exists", "--format=custom", "-d", uri, archive]
    subprocess.run(command)
    print("Database has been restored.")


def setup_database(uri: str, schemaFile: str) -> None:
    """Sets up a PostgreSQL database according to a given schema"""
    command = ["psql", "-q", "-f", schemaFile, uri]
    subprocess.run(command)
    print("Database schema has been set up.")


def connect_to_database(uri: str) -> None:
    """Connects to a PostgreSQL database for an interactive session"""
    print("Establishing connection to database...")
    command = ["psql", uri]
    subprocess.run(command)
    print("Connection to database closed.")
