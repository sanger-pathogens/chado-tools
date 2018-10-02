import sys
import os
import pkg_resources
import argparse
import pychado.tasks
import time


def main():
    """Main routine of the chado-tools package"""

    # Parse the supplied command line arguments
    arguments = parse_arguments(sys.argv)
    command = sys.argv[1]
    sub_command = ""
    if command in wrapper_commands():
        sub_command = sys.argv[2]

    if command in setup_commands():

        # Set database connection parameters
        pychado.tasks.setup(command)
    else:

        # Check database access
        start_time = time.time()
        connection_string = pychado.tasks.create_connection_string(arguments.config, arguments.dbname)
        if pychado.tasks.check_access(connection_string, sub_command):

            # Run the command
            pychado.tasks.run_command_with_arguments(command, sub_command, arguments, connection_string)

        # Print run time
        if arguments.verbose:
            print("Runtime: {0:.2f} s".format(time.time()-start_time))


def setup_commands() -> dict:
    """Lists the available 'setup' sub-commands of the 'chado' command with corresponding descriptions"""
    return {
        "init": "set the default connection parameters",
        "reset": "reset the default connection parameters to factory settings"
    }


def general_commands() -> dict:
    """Lists the available general sub-commands of the 'chado' command with corresponding descriptions"""
    return {
        "connect": "connect to a CHADO database for an interactive session",
        "query": "query a CHADO database and export the result to a text file",
        "stats": "obtain statistics to updates in a CHADO database"
    }


def wrapper_commands() -> dict:
    """Lists the available 'wrapper' sub-commands of the 'chado' command with corresponding descriptions"""
    return {
        "list": "list all entities of a specified type in the CHADO database",
        "insert": "insert a new entity of a specified type into the CHADO database",
        "delete": "delete an entity of a specified type from the CHADO database",
        "import": "import entities of a specified type into the CHADO database",
        "admin": "perform administrative tasks, such as creating or dumping a CHADO database"
    }


def admin_commands() -> dict:
    """Lists the available sub-commands of the 'chado admin' command with corresponding descriptions"""
    return {
        "create": "create a new instance of the CHADO schema",
        "drop": "drop a CHADO database",
        "dump": "dump a CHADO database into an archive file",
        "restore": "restore a CHADO database from an archive file"
    }


def list_commands() -> dict:
    """Lists the available sub-commands of the 'chado list' command with corresponding descriptions"""
    return {
        "organisms": "list all organisms in the CHADO database",
        "cvterms": "list all CV terms in the CHADO database",
        "genedb_products": "list all products of transcripts in the CHADO database"
    }


def insert_commands() -> dict:
    """Lists the available sub-commands of the 'chado insert' command with corresponding descriptions"""
    return {
        "organism": "insert an organism into the CHADO database"
    }


def delete_commands() -> dict:
    """Lists the available sub-commands of the 'chado delete' command with corresponding descriptions"""
    return {
        "organism": "delete an organism from the CHADO database"
    }


def import_commands() -> dict:
    """Lists the available sub-commands of the 'chado import' command with corresponding descriptions"""
    return {
        "ontology": "import an ontology into the CHADO database"
    }


def parse_arguments(input_arguments: list) -> argparse.Namespace:
    """Defines the formal arguments of the 'chado' command and parses the actual arguments accordingly"""

    # Create a parser and add global formal arguments
    program_name = os.path.basename(input_arguments[0])
    parser = argparse.ArgumentParser(description="Tools to access CHADO databases",
                                     epilog="For detailed usage information type '" + program_name + " <command> -h'",
                                     prog=program_name, allow_abbrev=False)
    parser.add_argument("-v", "--version", help="show the version of the software and exit",
                        action='version', version=str(pkg_resources.get_distribution("chado-tools").version))

    # Add subparsers for all sub-commands
    subparsers = parser.add_subparsers()

    for command, description in setup_commands().items():
        # Create subparser
        subparsers.add_parser(command, description=description, help=description)

    for command, description in general_commands().items():
        # Create subparser and add general and specific formal arguments
        sub = subparsers.add_parser(command, description=description, help=description)
        add_general_arguments(sub)
        add_arguments_by_command(command, sub)

    for command, description in wrapper_commands().items():
        # Create subparser and add specific formal arguments
        sub = subparsers.add_parser(command, description=description, help=description)
        add_arguments_by_command(command, sub)

    # Parse the actual arguments
    return parser.parse_args(input_arguments[1:])


def add_general_arguments(parser: argparse.ArgumentParser):
    """Defines general formal arguments (available to all sub-commands)"""
    parser.add_argument("-V", "--verbose", action="store_true", help="verbose mode")
    parser.add_argument("-c", "--config", default="", help="YAML file containing connection details")
    parser.add_argument("dbname", help="name of the database")


def add_general_export_arguments(parser: argparse.ArgumentParser):
    """Defines general formal arguments for all sub-commands that export data from a database"""
    parser.add_argument("-H", "--include_header", action="store_true", help="include header in output (default: False)")
    parser.add_argument("-d", "--delimiter", default="\t",
                        help="Character delimiting fields in output (default: tab)")
    parser.add_argument("-o", "--output_file", default="", help="file into which data are exported (default: stdout)")


def add_arguments_by_command(command: str, parser: argparse.ArgumentParser):
    """Defines formal arguments for a specified sub-command"""
    if command == "connect":
        pass
    elif command == "admin":
        add_admin_arguments(parser)
    elif command == "query":
        add_query_arguments(parser)
    elif command == "stats":
        add_stats_arguments(parser)
    elif command == "list":
        add_list_arguments(parser)
    elif command == "insert":
        add_insert_arguments(parser)
    elif command == "delete":
        add_delete_arguments(parser)
    elif command == "import":
        add_import_arguments(parser)
    else:
        print("Command '" + parser.prog + "' is not available.")


def add_admin_arguments(parser: argparse.ArgumentParser):
    """Defines formal arguments for the 'chado admin' sub-command"""
    parser.epilog = "For detailed usage information type '" + parser.prog + " <command> -h'"
    subparsers = parser.add_subparsers()
    for command, description in admin_commands().items():
        # Create subparser and add general and specific formal arguments
        sub = subparsers.add_parser(command, description=description, help=description)
        add_general_arguments(sub)
        add_admin_arguments_by_command(command, sub)


def add_admin_arguments_by_command(command: str, parser: argparse.ArgumentParser):
    """Defines formal arguments for a specified sub-command of 'chado admin'"""
    if command == "create":
        add_create_arguments(parser)
    elif command == "drop":
        pass
    elif command == "dump":
        add_dump_arguments(parser)
    elif command == "restore":
        add_restore_arguments(parser)
    else:
        print("Command '" + parser.prog + "' is not available.")


def add_create_arguments(parser: argparse.ArgumentParser):
    """Defines formal arguments for the 'chado admin create' sub-command"""
    parser.add_argument("-s", "--schema", default="", help="File with database schema (default: GMOD schema 1.31)")


def add_dump_arguments(parser: argparse.ArgumentParser):
    """Defines formal arguments for the 'chado admin dump' sub-command"""
    parser.add_argument("archive", help="archive file to be created")


def add_restore_arguments(parser: argparse.ArgumentParser):
    """Defines formal arguments for the 'chado admin restore' sub-command"""
    parser.add_argument("archive", help="archive file")


def add_query_arguments(parser: argparse.ArgumentParser):
    """Defines formal arguments for the 'chado query' sub-command"""
    add_general_export_arguments(parser)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-f", "--input_file", default="", help="file containing an SQL query")
    group.add_argument("-q", "--query", default="", help="SQL query")


def add_stats_arguments(parser: argparse.ArgumentParser):
    """Defines formal arguments for the 'chado stats' sub-command"""
    add_general_export_arguments(parser)
    parser.add_argument("-a", "--abbreviation", default="all", dest="organism",
                        help="restrict to a certain organism, defined by its abbreviation/short name (default: all)")
    parser.add_argument("--start_date", required=True, help="date for maximum age of updates, format 'YYYYMMDD'")
    parser.add_argument("--end_date", default="", help="date for minimum age of updates, format 'YYYYMMDD' "
                                                       "(default: today)")


def add_list_arguments(parser: argparse.ArgumentParser):
    """Defines formal arguments for the 'chado list' sub-command"""
    parser.epilog = "For detailed usage information type '" + parser.prog + " <command> -h'"
    subparsers = parser.add_subparsers()
    for command, description in list_commands().items():
        # Create subparser and add general and specific formal arguments
        sub = subparsers.add_parser(command, description=description, help=description)
        add_general_arguments(sub)
        add_general_export_arguments(sub)
        add_list_arguments_by_command(command, sub)


def add_list_arguments_by_command(command: str, parser: argparse.ArgumentParser):
    """Defines formal arguments for a specified sub-command of 'chado list'"""
    if command == "organisms":
        pass
    elif command == "cvterms":
        add_list_cvterms_arguments(parser)
    elif command == "genedb_products":
        add_list_genedb_product_arguments(parser)
    else:
        print("Command '" + parser.prog + "' is not available.")


def add_list_cvterms_arguments(parser: argparse.ArgumentParser):
    """Defines formal arguments for the 'chado list cvterms' sub-command"""
    parser.add_argument("--vocabulary", default="all", help="restrict to a vocabulary, e.g. 'relationship'")
    parser.add_argument("--database", default="all", help="restrict to a database, e.g. 'GO'")


def add_list_genedb_product_arguments(parser: argparse.ArgumentParser):
    """Defines formal arguments for the 'chado list genedb_products' sub-command"""
    parser.add_argument("-a", "--abbreviation", dest="organism", default="all",
                        help="restrict to a certain organism, defined by its abbreviation/short name (default: all)")


def add_insert_arguments(parser: argparse.ArgumentParser):
    """Defines formal arguments for the 'chado insert' sub-command"""
    parser.epilog = "For detailed usage information type '" + parser.prog + " <command> -h'"
    subparsers = parser.add_subparsers()
    for command, description in insert_commands().items():
        # Create subparser and add general and specific formal arguments
        sub = subparsers.add_parser(command, description=description, help=description)
        add_general_arguments(sub)
        add_insert_arguments_by_command(command, sub)


def add_insert_arguments_by_command(command: str, parser: argparse.ArgumentParser):
    """Defines formal arguments for a specified sub-command of 'chado insert'"""
    if command == "organism":
        add_insert_organism_arguments(parser)
    else:
        print("Command '" + parser.prog + "' is not available.")


def add_insert_organism_arguments(parser: argparse.ArgumentParser):
    """Defines formal arguments for the 'chado insert organism' sub-command"""
    parser.add_argument("-g", "--genus", required=True, help="genus of the organism")
    parser.add_argument("-s", "--species", required=True, help="species of the organism")
    parser.add_argument("-a", "--abbreviation", required=True, help="abbreviation/short name of the organism")
    parser.add_argument("--common_name", help="common name of the organism (default: use abbreviation, if provided)")
    parser.add_argument("--comment", help="comment")


def add_delete_arguments(parser: argparse.ArgumentParser):
    """Defines formal arguments for the 'chado delete' sub-command"""
    parser.epilog = "For detailed usage information type '" + parser.prog + " <command> -h'"
    subparsers = parser.add_subparsers()
    for command, description in delete_commands().items():
        # Create subparser and add general and specific formal arguments
        sub = subparsers.add_parser(command, description=description, help=description)
        add_general_arguments(sub)
        add_delete_arguments_by_command(command, sub)


def add_delete_arguments_by_command(command: str, parser: argparse.ArgumentParser):
    """Defines formal arguments for a specified sub-command of 'chado delete'"""
    if command == "organism":
        add_delete_organism_arguments(parser)
    else:
        print("Command '" + parser.prog + "' is not available.")


def add_delete_organism_arguments(parser: argparse.ArgumentParser):
    """Defines formal arguments for the 'chado delete organism' sub-command"""
    parser.add_argument("-a", "--abbreviation", required=True, dest="organism",
                        help="abbreviation/short name of the organism")


def add_import_arguments(parser: argparse.ArgumentParser):
    """Defines formal arguments for the 'chado import' sub-command"""
    parser.epilog = "For detailed usage information type '" + parser.prog + " <command> -h'"
    subparsers = parser.add_subparsers()
    for command, description in import_commands().items():
        # Create subparser and add general and specific formal arguments
        sub = subparsers.add_parser(command, description=description, help=description)
        add_general_arguments(sub)
        add_import_arguments_by_command(command, sub)


def add_import_arguments_by_command(command: str, parser: argparse.ArgumentParser):
    """Defines formal arguments for a specified sub-command of 'chado import'"""
    if command == "ontology":
        add_import_ontology_arguments(parser)
    else:
        print("Command '" + parser.prog + "' is not available.")


def add_import_ontology_arguments(parser: argparse.ArgumentParser):
    """Defines formal arguments for the 'chado import ontology' sub-command"""
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-f", "--input_file", default="", help="file containing CV terms")
    group.add_argument("-u", "--input_url", default="", help="URL to a file containing CV terms")
    parser.add_argument("-A", "--database_authority", required=True,
                        help="database authority of the terms in the file, e.g. 'GO'")
    parser.add_argument("-F", "--format", default="obo", choices={"obo", "owl"},
                        help="format of the file (default: obo)")
