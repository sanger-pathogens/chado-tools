import shutil
import pkg_resources
import subprocess
import string
import random
import urllib.parse
import getpass
import sqlalchemy
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
        dsn_as_list.append("dbname=" + connection_details["database"])
    if "user" in connection_details and connection_details["user"] is not None:
        dsn_as_list.append("user=" + connection_details["user"])
    if "password" in connection_details and connection_details["password"] is not None:
        dsn_as_list.append("password=" + connection_details["password"])
    if "host" in connection_details and connection_details["host"] is not None:
        dsn_as_list.append("host=" + connection_details["host"])
    if "port" in connection_details and connection_details["port"] is not None:
        dsn_as_list.append("port=" + connection_details["port"])
    return " ".join(dsn_as_list)


def default_schema_url() -> str:
    """Returns the URL of the default schema"""
    yaml_file = pkg_resources.resource_filename("pychado", "data/gmodSchema.yml")
    default_schema = utils.parse_yaml(yaml_file)
    return default_schema["url"].replace("<VERSION>", default_schema["version"])


def default_configuration_file() -> str:
    """Returns the name of the default configuration file"""
    return pkg_resources.resource_filename("pychado", "data/defaultDatabase.yml")


def factory_settings_configuration_file() -> str:
    """Returns the name of the configuration file with factory settings"""
    return pkg_resources.resource_filename("pychado", "data/factorySettings.yml")


def open_connection(uri: str) -> sqlalchemy.engine.base.Connection:
    """Establishes a database connection"""
    engine = sqlalchemy.create_engine(uri)
    connection = engine.connect()
    return connection


def close_connection(connection: sqlalchemy.engine.base.Connection) -> None:
    """Closes a database connection"""
    connection.close()
    connection.engine.dispose()


def execute_query(connection: sqlalchemy.engine.base.Connection, query: str, params=None) \
        -> sqlalchemy.engine.ResultProxy:
    """Executes an SQL query in an opened database and returns the query result"""
    if params:
        return connection.execute(sqlalchemy.text(query), params)
    else:
        return connection.execute(query)


def execute_statement(connection: sqlalchemy.engine.base.Connection, statement: str, params=None) -> None:
    """Executes an SQL statement in an opened database"""
    if params:
        connection.execute(sqlalchemy.text(statement), params)
    else:
        connection.execute(statement)


def get_keys(connection: sqlalchemy.engine.base.Connection, table: str) -> set:
    """Retrieves the keys of a table in an opened database"""
    sql = "SELECT * FROM " + table + " LIMIT 0"
    result = execute_query(connection, sql)
    return set(result.keys())


def exists(uri: str, dbname: str) -> bool:
    """Checks if a database exists"""
    sql = utils.read_text(pkg_resources.resource_filename("pychado", "sql/check_if_database_exists.sql"))
    conn = open_connection(uri)
    result = execute_query(conn, sql, {"datname": dbname}).scalar()
    close_connection(conn)
    return result != 0


def random_database(uri: str) -> str:
    """Generates a random database name and makes sure the name is not yet in use"""
    dbname = "template0"
    while exists(uri, dbname):
        dbname = "".join(random.choices(string.ascii_lowercase, k=10))
    return dbname


def create_database(uri: str, dbname: str) -> None:
    """Creates a database"""
    sql = "CREATE DATABASE " + dbname
    connect_and_execute(uri, sql, autocommit=True)
    print("Database has been created.")


def drop_database(uri: str, dbname: str) -> None:
    """Deletes a database"""
    sql = "DROP DATABASE " + dbname
    connect_and_execute(uri, sql, autocommit=True)
    print("Database has been deleted.")


def dump_database(uri: str, archive: str):
    """Dumps a database into an archive file"""
    command = ["pg_dump", "-f", archive, "--format=custom", uri]
    subprocess.run(command)
    print("Database has been dumped.")


def restore_database(uri: str, archive: str):
    """Restores a database from an archive file"""
    command = ["pg_restore", "--clean", "--if-exists", "--no-owner", "--no-privileges", "--format=custom",
               "-d", uri, archive]
    subprocess.run(command)
    print("Database has been restored.")


def setup_database(uri: str, schema_file: str) -> None:
    """Sets up a database according to a given schema"""
    command = ["psql", "-q", "-f", schema_file, uri]
    subprocess.run(command)
    print("Database schema has been set up.")


def connect_to_database(uri: str) -> None:
    """Connects to a database for an interactive session"""
    print("Establishing connection to database...")
    command = ["psql", uri]
    subprocess.run(command)
    print("Connection to database closed.")


def connect_and_execute(uri: str, statement: str, params=None, autocommit=False) -> None:
    """Connects to a database and executes a single statement"""
    connection = open_connection(uri)
    if autocommit:
        connection.execution_options(isolation_level="AUTOCOMMIT")
    execute_statement(connection, statement, params)
    close_connection(connection)


def query_to_file(uri: str, query: str, params: dict, filename: str, delimiter: str, header: bool) -> None:
    """Connects to a database, runs a single query, and writes the result into a CSV file"""
    # Query database and convert result to rows
    conn = open_connection(uri)
    result = execute_query(conn, query, params)
    rows = []
    if header:
        rows = [result.keys()]
    for result_row in result.fetchall():
        row = [value for key, value in result_row.items()]
        rows.append(row)
    result.close()
    close_connection(conn)

    # Write table to file
    file = utils.open_file_write(filename)
    for row in rows:
        file.write(utils.list_to_string(row, delimiter) + "\n")
    utils.close(file)
    if filename:
        print("Data exported to " + filename)
