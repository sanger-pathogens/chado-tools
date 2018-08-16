import shutil
import pkg_resources
import subprocess
import string
import random
import psycopg2
import urllib.request
import urllib.parse
import getpass
from pychado import utils


def set_default_parameters() -> None:
    """Sets the default connection parameters"""
    parameters = {}
    print("Please set the connection parameters for your default database.")
    parameters["host"] = input("host: ")
    parameters["port"] = input("port: ")
    parameters["database"] = input("database: ")
    parameters["user"] = input("username: ")
    parameters["password"] = getpass.getpass(prompt="password: ")
    utils.dump_yaml(default_configuration_file(), parameters)
    print("Your default connection parameters have been changed.")


def reset_default_parameters() -> None:
    """Resets the default connection parameters to factory settings"""
    shutil.copyfile(factory_settings_configuration_file(), default_configuration_file())
    print("Your default connection parameters have been reset.")


def generate_uri(connection_details: dict) -> str:
    """Creates a connection URI"""
    uri_as_list = ["postgresql://"]
    if "user" in connection_details and connection_details["user"] is not None:
        uri_as_list.append(urllib.parse.quote(connection_details["user"]))
        if "password" in connection_details and connection_details["password"] is not None:
            uri_as_list.append(":" + urllib.parse.quote(connection_details["password"]))
        uri_as_list.append("@")
    if "host" in connection_details and connection_details["host"] is not None:
        uri_as_list.append(urllib.parse.quote(connection_details["host"]))
    if "port" in connection_details and connection_details["port"] is not None:
        uri_as_list.append(":" + connection_details["port"])
    if "database" in connection_details and connection_details["database"] is not None:
        uri_as_list.append("/" + urllib.parse.quote(connection_details["database"]))
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


def factory_settings_configuration_file() -> str:
    """Returns the name of the configuration file with factory settings"""
    return pkg_resources.resource_filename("pychado", "data/factorySettings.yml")


def execute_query(connection, query: str, params: tuple, header=False) -> list:
    """Executes an SQL query in an opened PostgreSQL database and returns the query result"""
    cursor = connection.cursor()
    cursor.execute(query, params)
    if header:
        result = [tuple([desc[0] for desc in cursor.description])]
        result.extend(cursor.fetchall())
    else:
        result = cursor.fetchall()
    cursor.close()
    return result


def execute_statement(connection, statement: str, params: tuple):
    """Executes an SQL statement in an opened PostgreSQL database"""
    cursor = connection.cursor()
    cursor.execute(statement, params)
    cursor.close()


def connect_and_execute_query(dsn: str, query: str, params=tuple(), header=False) -> list:
    """Connects to a database, executes an SQL query, and returns the result"""
    connection = psycopg2.connect(dsn)
    connection.set_client_encoding("UTF8")
    result = execute_query(connection, query, params, header)
    connection.close()
    return result


def connect_and_execute_statement(dsn: str, statement: str, params=tuple(), autocommit=False):
    """Connects to a database and executes an SQL statement"""
    connection = psycopg2.connect(dsn)
    if autocommit:
        connection.autocommit = True
    execute_statement(connection, statement, params)
    if not autocommit:
        connection.commit()
    connection.close()


def exists(dsn: str, dbname: str) -> bool:
    """Checks if a PostgreSQL database exists"""
    sql = utils.read_text(pkg_resources.resource_filename("pychado", "sql/check_if_database_exists.sql"))
    result = connect_and_execute_query(dsn, sql, (dbname,))
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
    connect_and_execute_statement(dsn, sql, (), autocommit=True)
    print("Database has been created.")


def drop_database(dsn: str, dbname: str) -> None:
    """Deletes a PostgreSQL database"""
    sql = "DROP DATABASE " + dbname
    connect_and_execute_statement(dsn, sql, (), autocommit=True)
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
    if filename:
        print("Data imported from " + filename)


def copy_to_file(dsn: str, table: str, filename: str, delimiter: str, header: bool) -> None:
    """Copies data from a table of a PostgreSQL database into a CSV file"""
    sql = "SELECT * FROM " + table
    query_to_file(dsn, sql, (), filename, delimiter, header)


def query_to_file(dsn: str, query: str, params: tuple, filename: str, delimiter: str, header: bool) -> None:
    """Executes a query in a PostgreSQL database and writes the result into a CSV file"""
    result = connect_and_execute_query(dsn, query, params, header)
    file = utils.open_file_write(filename)
    for line in result:
        file.write(utils.list_to_string(line, delimiter) + "\n")
    utils.close(file)
    if filename:
        print("Data exported to " + filename)
