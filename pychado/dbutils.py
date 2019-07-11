import os
import pkg_resources
import subprocess
import urllib.parse
import json
import getpass
import sqlalchemy.engine
import sqlalchemy.sql
import sqlalchemy_utils
from . import utils


def get_connection_parameters(filename: str, use_password: bool, dbname: str) -> dict:
    """Reads database connection parameters from a configuration file or the environment"""
    if filename:
        connection_parameters = utils.parse_yaml(filename)
    else:
        connection_parameters = get_connection_parameters_from_env()
        if use_password:
            connection_parameters["password"] = get_connection_password()
    connection_parameters["database"] = dbname
    return connection_parameters


def get_connection_parameters_from_env() -> dict:
    """Reads connection parameters from environment variables"""
    default_connection_parameters = utils.parse_yaml(default_configuration_file())
    connection_parameters = dict()
    connection_parameters["host"] = os.getenv('CHADO_HOST', default_connection_parameters["host"])
    connection_parameters["port"] = os.getenv('CHADO_PORT', default_connection_parameters["port"])
    connection_parameters["user"] = os.getenv('CHADO_USER', default_connection_parameters["user"])
    connection_parameters["password"] = os.getenv('CHADO_PASS', default_connection_parameters["password"])
    return connection_parameters


def get_connection_password() -> str:
    """Asks the user to supply the connection password"""
    return getpass.getpass()


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


def default_schema_url() -> str:
    """Returns the URL of the default schema"""
    yaml_file = pkg_resources.resource_filename("pychado", "data/gmodSchema.yml")
    default_schema = utils.parse_yaml(yaml_file)
    return default_schema["url"].replace("<VERSION>", default_schema["version"])


def default_configuration_file() -> str:
    """Returns the name of the default configuration file"""
    return pkg_resources.resource_filename("pychado", "data/defaultDatabase.yml")


def open_connection(uri: str) -> sqlalchemy.engine.base.Connection:
    """Establishes a database connection"""
    engine = sqlalchemy.create_engine(uri)
    connection = engine.connect()
    return connection


def close_connection(connection: sqlalchemy.engine.base.Connection) -> None:
    """Closes a database connection"""
    connection.close()
    connection.engine.dispose()


def exists(uri: str) -> bool:
    """Checks if a database exists"""
    return sqlalchemy_utils.database_exists(uri)


def random_database_uri(connection_parameters: dict) -> str:
    """Generates a random database name and makes sure the name is not yet in use"""
    parameters = connection_parameters.copy()
    while True:
        parameters["database"] = utils.random_string(10)
        uri = generate_uri(parameters)
        if not exists(uri):
            break
    return uri


def create_database(uri: str) -> None:
    """Creates a database"""
    sqlalchemy_utils.create_database(uri)
    print("Database has been created.")


def drop_database(uri: str, force=False) -> None:
    """Deletes a database"""
    if not force:
        dbname = uri.split("/")[-1]
        if input("Are you sure you want to drop the database '" + dbname + "' [y/n]?\n").lower() != "y":
            print("Database is conserved.")
            return
    sqlalchemy_utils.drop_database(uri)
    print("Database has been deleted.")


def dump_database(uri: str, archive: str) -> None:
    """Dumps a database into an archive file"""
    command = ["pg_dump", "-f", archive, "--format=custom", uri]
    subprocess.run(command)
    print("Database has been dumped.")


def restore_database(uri: str, archive: str) -> None:
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


def query_and_print(uri: str, query, filename: str, file_format: str, header: bool, delimiter: str) -> None:
    """Opens a database connection, runs a single query, and prints the query result"""
    conn = open_connection(uri)
    result = run_query(conn, query)
    print_query_result(result, filename, file_format, header, delimiter)
    result.close()
    close_connection(conn)


def run_query(conn: sqlalchemy.engine.Connection, query) -> sqlalchemy.engine.ResultProxy:
    """Runs a single query against a database"""
    if isinstance(query, sqlalchemy.sql.expression.TextClause) or isinstance(query, sqlalchemy.sql.Select):
        result = conn.execute(query)
    else:
        result = conn.execute(sqlalchemy.text(query))
    return result


def print_query_result(result: sqlalchemy.engine.ResultProxy, filename: str, file_format: str, header: bool,
                       delimiter: str) -> None:
    """Exports a table resulting from a database query"""
    file_handle = utils.open_file_write(filename)
    if file_format == "csv":
        print_query_result_csv(result, file_handle, header, delimiter)
    elif file_format == "json":
        print_query_result_json(result, file_handle)
    else:
        print("Unknown file format: '" + file_format + "'")
    utils.close(file_handle)


def print_query_result_csv(result: sqlalchemy.engine.ResultProxy, file_handle, header: bool, delimiter: str) -> None:
    """Exports a table resulting from a database query as CSV"""
    keys = result.keys()
    if header:
        file_handle.write(utils.list_to_string(keys, delimiter) + "\n")
    while True:
        row = result.fetchone()
        if not row:
            break
        file_handle.write(utils.list_to_string(row, delimiter) + "\n")


def print_query_result_json(result: sqlalchemy.engine.ResultProxy, file_handle) -> None:
    """Exports a table resulting from a database query as JSON"""
    keys = result.keys()
    json_obj = []
    while True:
        row = result.fetchone()
        if not row:
            break
        json_dict = dict(zip(keys, row))
        json_obj.append(json_dict)
    json.dump(json_obj, file_handle, indent=4, sort_keys=True)
    file_handle.write("\n")
