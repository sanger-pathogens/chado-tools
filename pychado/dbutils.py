import shutil
import pkg_resources
import subprocess
import urllib.parse
import getpass
import sqlalchemy
import sqlalchemy_utils
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


def exists(uri: str) -> bool:
    """Checks if a database exists"""
    return sqlalchemy_utils.database_exists(uri)


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


def connect_and_execute(uri: str, statement: str, params=None) -> None:
    """Connects to a database and executes a single statement"""
    connection = open_connection(uri)
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
