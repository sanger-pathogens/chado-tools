import pkg_resources
import subprocess
import string
import random
import psycopg2
import urllib.request
from pychado import utils


def generate_uri(connection_details: dict) -> str:
    """Creates a connection URI"""
    uri_as_list = ["postgresql://"]
    if "user" in connection_details and connection_details["user"] is not None:
        uri_as_list.append(connection_details["user"])
        if "password" in connection_details and connection_details["password"] is not None:
            uri_as_list.append(":" + connection_details["password"])
        uri_as_list.append("@")
    if "host" in connection_details and connection_details["host"] is not None:
        uri_as_list.append(connection_details["host"])
    if "port" in connection_details and connection_details["port"] is not None:
        uri_as_list.append(":" + connection_details["port"])
    if "database" in connection_details and connection_details["database"] is not None:
        uri_as_list.append("/" + connection_details["database"])
    return "".join(uri_as_list)


def generate_dsn(connection_details: dict) -> str:
    """Creates a connection DSN"""
    dsn_as_list = []
    if "database" in connection_details and connection_details["database"] is not None:
        dsn_as_list.append("dbname=" + connection_details["database"] + " ")
    if "user" in connection_details and connection_details["user"] is not None:
        dsn_as_list.append("user=" + connection_details["user"] + " ")
    if "password" in connection_details and connection_details["password"] is not None:
        dsn_as_list.append("password=" + connection_details["password"] + " ")
    if "host" in connection_details and connection_details["host"] is not None:
        dsn_as_list.append("host=" + connection_details["host"] + " ")
    if "port" in connection_details and connection_details["port"] is not None:
        dsn_as_list.append("port=" + connection_details["port"] + " ")
    return "".join(dsn_as_list).strip()


def default_schema_url() -> str:
    """Returns the URL of the default schema"""
    yaml_file = pkg_resources.resource_filename("pychado", "data/gmodSchema.yml")
    default_schema = utils.parse_yaml(yaml_file)
    return default_schema["url"].replace("<VERSION>", default_schema["version"])


def download_schema(url: str) -> str:
    """Downloads a file with a database schema"""
    print("Downloading database schema...")
    schema_file, headers = urllib.request.urlretrieve(url)
    return schema_file


def default_configuration_file() -> str:
    """Returns the name of the default configuration file"""
    return pkg_resources.resource_filename("pychado", "data/defaultDatabase.yml")


def read_configuration_file(filename: str) -> dict:
    """Reads data from a configuration file into a dictionary"""
    if not filename:
        filename = default_configuration_file()
    return utils.parse_yaml(filename)


def execute_query(connection, query: str) -> list:
    """Executes an SQL query in an opened PostgreSQL database and returns the query result"""
    cursor = connection.cursor()
    cursor.execute(query)
    result = cursor.fetchall()
    cursor.close()
    return result


def execute_statement(connection, statement: str):
    """Executes an SQL statement in an opened PostgreSQL database"""
    cursor = connection.cursor()
    cursor.execute(statement)
    cursor.close()


def connect_and_execute_query(dsn: str, query: str) -> list:
    """Connects to a database, executes an SQL query, and returns the result"""
    connection = psycopg2.connect(dsn)
    result = execute_query(connection, query)
    connection.close()
    return result


def connect_and_execute_statement(dsn: str, statement: str, autocommit=False):
    """Connects to a database and executes an SQL statement"""
    connection = psycopg2.connect(dsn)
    if autocommit:
        connection.autocommit = True
    execute_statement(connection, statement)
    if not autocommit:
        connection.commit()
    connection.close()


def exists(dsn: str, dbname: str) -> bool:
    """Checks if a PostgreSQL database exists"""
    sql = "SELECT COUNT(*) FROM pg_catalog.pg_database WHERE datname = '" + dbname + "'"
    result = connect_and_execute_query(dsn, sql)
    return bool(result[0][0])


def random_database(dsn: str) -> str:
    """Generates a random database name and makes sure the name is not yet in use"""
    dbname = "template0"
    while exists(dsn, dbname):
        dbname = ''.join(random.choices(string.ascii_lowercase, k=10))
    return dbname


def create_database(dsn: str, dbname: str) -> None:
    """Creates a PostgreSQL database"""
    sql = "CREATE DATABASE " + dbname
    connect_and_execute_statement(dsn, sql, autocommit=True)
    print("Database has been created.")


def drop_database(dsn: str, dbname: str) -> None:
    """Deletes a PostgreSQL database"""
    sql = "DROP DATABASE " + dbname
    connect_and_execute_statement(dsn, sql, autocommit=True)
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


def setup_database(uri: str, schema_file: str) -> None:
    """Sets up a PostgreSQL database according to a given schema"""
    command = ["psql", "-q", "-f", schema_file, uri]
    subprocess.run(command)
    print("Database schema has been set up.")


def connect_to_database(uri: str) -> None:
    """Connects to a PostgreSQL database for an interactive session"""
    print("Establishing connection to database...")
    command = ["psql", uri]
    subprocess.run(command)
    print("Connection to database closed.")


def copy_from_file(dsn: str, table: str, filename: str, delimiter: str) -> None:
    """Copies data from a CSV file into a table of a PostgreSQL database"""
    file = utils.open_file_read(filename)
    connection = psycopg2.connect(dsn)
    cursor = connection.cursor()
    cursor.copy_from(file, table, sep=delimiter, null='\\null')
    cursor.close()
    connection.commit()
    connection.close()
    utils.close(file)
    print("Data imported from " + filename)


def copy_to_file(dsn: str, table: str, filename: str, delimiter: str) -> None:
    """Copies data from a table of a PostgreSQL database into a CSV file"""
    file = utils.open_file_write(filename)
    connection = psycopg2.connect(dsn)
    cursor = connection.cursor()
    cursor.copy_to(file, table, sep=delimiter, null='\\null')
    cursor.close()
    connection.close()
    utils.close(file)
    print("Data exported to " + filename)
