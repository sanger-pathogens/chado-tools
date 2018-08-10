#!/usr/bin/env python3

import sys
import os
import pkg_resources
import argparse
import pychado.tasks


def main():
    """Main routine of the chado-tools package"""
    # Parse the supplied command line arguments
    arguments = parse_arguments(sys.argv)
    command = sys.argv[1]

    # Check database access
    connection_parameters = pychado.tasks.read_configuration_file(arguments.config)
    if pychado.tasks.check_access(connection_parameters, arguments.dbname, command):

        # Run the command
        connection_parameters["database"] = arguments.dbname
        if command in general_commands():
            pychado.tasks.run_command_with_arguments(command, arguments, connection_parameters)
        else:
            sub_command = sys.argv[2]
            pychado.tasks.run_sub_command_with_arguments(command, sub_command, arguments, connection_parameters)


def general_commands() -> dict:
    """Lists the available general sub-commands of the 'chado' command with corresponding descriptions"""
    return {
        "connect": "connect to a CHADO database for an interactive session",
        "create": "create a new instance of the CHADO schema",
        "dump": "dump a CHADO database into an archive file",
        "restore": "restore a CHADO database from an archive file",
        "import": "import data from a text file to a table of a CHADO database",
        "export": "export data from a table of a CHADO database to a text file",
        "query": "query a CHADO database and export the result to a text file"
    }


def wrapper_commands() -> dict:
    """Lists the available 'wrapper' sub-commands of the 'chado' command with corresponding descriptions"""
    return {
        "list": "list all entities of a specified type in the CHADO database",
        "insert": "insert a new entity of a specified type into the CHADO database",
        "delete": "delete an entity of a specified type from the CHADO database",
        "stats": "obtain statistics to updates in a CHADO database"
    }


def list_commands() -> dict:
    """Lists the available sub-commands of the 'chado list' command with corresponding descriptions"""
    return {
        "organisms": "list all organisms in the CHADO database (genus, species, abbreviation)",
        "products": "list all products of transcripts in the CHADO database"
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


def stats_commands() -> dict:
    """Lists the available sub-commands of the 'chado stats' command with corresponding descriptions"""
    return {
        "annotations": "obtain a list of annotation upates",
        "eupathdb_tags": "obtain a list of updated EuPathDB tags"
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
        add_connect_arguments(parser)
    elif command == "create":
        add_create_arguments(parser)
    elif command == "dump":
        add_dump_arguments(parser)
    elif command == "restore":
        add_restore_arguments(parser)
    elif command == "import":
        add_import_arguments(parser)
    elif command == "export":
        add_export_arguments(parser)
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
    else:
        print("Command '" + parser.prog + "' is not available.")


def add_connect_arguments(parser: argparse.ArgumentParser):
    """Defines formal arguments for the 'chado connect' sub-command"""
    pass


def add_create_arguments(parser: argparse.ArgumentParser):
    """Defines formal arguments for the 'chado create' sub-command"""
    parser.add_argument("-s", "--schema", default="", help="File with database schema (default: GMOD schema 1.31)")


def add_dump_arguments(parser: argparse.ArgumentParser):
    """Defines formal arguments for the 'chado dump' sub-command"""
    parser.add_argument("archive", help="archive file to be created")


def add_restore_arguments(parser: argparse.ArgumentParser):
    """Defines formal arguments for the 'chado restore' sub-command"""
    parser.add_argument("archive", help="archive file")


def add_import_arguments(parser: argparse.ArgumentParser):
    """Defines formal arguments for the 'chado import' sub-command"""
    parser.add_argument("-d", "--delimiter", default="\t",
                        help="Character delimiting fields in input file (default: tab)")
    parser.add_argument("-f", "--input_file", default="", help="file from which data are imported (default: stdin)")
    parser.add_argument("table", help="table into which data are imported")


def add_export_arguments(parser: argparse.ArgumentParser):
    """Defines formal arguments for the 'chado export' sub-command"""
    add_general_export_arguments(parser)
    parser.add_argument("table", help="table from which data are exported")


def add_query_arguments(parser: argparse.ArgumentParser):
    """Defines formal arguments for the 'chado query' sub-command"""
    add_general_export_arguments(parser)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-f", "--input_file", default="", help="file containing an SQL query")
    group.add_argument("-q", "--query", default="", help="SQL query")


def add_stats_arguments(parser: argparse.ArgumentParser):
    """Defines formal arguments for the 'chado stats' sub-command"""
    parser.epilog = "For detailed usage information type '" + parser.prog + " <command> -h'"
    subparsers = parser.add_subparsers()
    for command, description in stats_commands().items():
        # Create subparser and add general and specific formal arguments
        sub = subparsers.add_parser(command, description=description, help=description)
        add_general_arguments(sub)
        add_general_export_arguments(sub)
        sub.add_argument("-a", "--abbreviation", default="all", dest="organism",
                         help="restrict to a certain organism, defined by its abbreviation/short name (default: all)")
        sub.add_argument("-D", "--date", required=True, help="date for maximum age of updates, format 'YYYYMMDD'")
        add_stats_arguments_by_command(command, sub)


def add_stats_arguments_by_command(command: str, parser: argparse.ArgumentParser):
    """Defines formal arguments for a specified sub-command of 'chado stats'"""
    if command == "annotations":
        pass
    elif command == "eupathdb_tags":
        pass
    else:
        print("Command '" + parser.prog + "' is not available.")


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
        add_list_organisms_arguments(parser)
    elif command == "products":
        add_list_product_arguments(parser)
    else:
        print("Command '" + parser.prog + "' is not available.")


def add_list_organisms_arguments(parser: argparse.ArgumentParser):
    """Defines formal arguments for the 'chado list organisms' sub-command"""
    pass


def add_list_product_arguments(parser: argparse.ArgumentParser):
    """Defines formal arguments for the 'chado list products' sub-command"""
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
