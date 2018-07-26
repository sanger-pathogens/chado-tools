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
    sub_command = sys.argv[1]

    # Check database access
    connection_parameters = pychado.tasks.read_configuration_file(arguments.config)
    if pychado.tasks.check_access(connection_parameters, arguments.dbname, sub_command):

        # Run the sub_command
        connection_parameters["database"] = arguments.dbname
        pychado.tasks.run_task_with_arguments(sub_command, arguments, connection_parameters)


def available_commands() -> dict:
    """Lists the available sub-commands of the chado command with corresponding descriptions"""
    return {
        "connect": "connect to a CHADO database for an interactive session",
        "create": "create a new instance of the CHADO schema",
        "dump": "dump a CHADO database into an archive file",
        "restore": "restore a CHADO database from an archive file",
        "import": "import data from a text file into a table of a CHADO database",
        "export": "export data from a table of a CHADO database into a text file",
        "query": "query a CHADO database and export the result into a text file"
    }


def parse_arguments(input_arguments: list) -> argparse.Namespace:
    """Defines the formal arguments of the chado command and parses the actual arguments accordingly"""

    # Create a parser and add global formal arguments
    program_name = os.path.basename(input_arguments[0])
    parser = argparse.ArgumentParser(description="Tools to access CHADO databases",
                                     epilog="For detailed usage information type '" + program_name + " <command> -h'",
                                     prog=program_name, allow_abbrev=False)
    parser.add_argument("-v", "--version", help="show the version of the software and exit",
                        action='version', version=str(pkg_resources.get_distribution("chado-tools").version))

    # Add subparsers for all sub-commands
    subparsers = parser.add_subparsers()
    for command, description in available_commands().items():

        # Create subparser and add general formal arguments (available to all sub-commands)
        sub = subparsers.add_parser(command, description=description, help=description)
        sub.add_argument("-c", "--config", default="", help="YAML file containing connection details")
        sub.add_argument("dbname", help="name of the database")

        # Add specific formal arguments (for this sub-command)
        add_arguments_by_command(command, sub)

    # Parse the actual arguments
    return parser.parse_args(input_arguments[1:])


def add_arguments_by_command(task: str, parser: argparse.ArgumentParser):
    """Defines formal arguments for a specified sub-command"""
    if task == "connect":
        add_connect_arguments(parser)
    elif task == "create":
        add_create_arguments(parser)
    elif task == "dump":
        add_dump_arguments(parser)
    elif task == "restore":
        add_restore_arguments(parser)
    elif task == "import":
        add_import_arguments(parser)
    elif task == "export":
        add_export_arguments(parser)
    elif task == "query":
        add_query_arguments(parser)


def add_connect_arguments(parser: argparse.ArgumentParser):
    """Defines formal arguments for the 'chado connect' subcommand"""
    pass


def add_create_arguments(parser: argparse.ArgumentParser):
    """Defines formal arguments for the 'chado create' subcommand"""
    parser.add_argument("-s", "--schema", default="", help="File with database schema (default: GMOD schema 1.31)")


def add_dump_arguments(parser: argparse.ArgumentParser):
    """Defines formal arguments for the 'chado dump' subcommand"""
    parser.add_argument("archive", help="archive file to be created")


def add_restore_arguments(parser: argparse.ArgumentParser):
    """Defines formal arguments for the 'chado restore' subcommand"""
    parser.add_argument("archive", help="archive file")


def add_import_arguments(parser: argparse.ArgumentParser):
    """Defines formal arguments for the 'chado import' subcommand"""
    parser.add_argument("-d", "--delimiter", default="\t",
                        help="Character delimiting fields in file (default: tab)")
    parser.add_argument("-f", "--input_file", default="", help="file from which data are imported (default: stdin)")
    parser.add_argument("table", help="table into which data are imported")


def add_export_arguments(parser: argparse.ArgumentParser):
    """Defines formal arguments for the 'chado export' subcommand"""
    parser.add_argument("-H", "--include_header", action="store_true", help="include header in output (default: False)")
    parser.add_argument("-d", "--delimiter", default="\t",
                        help="Character delimiting fields in file (default: tab)")
    parser.add_argument("-o", "--output_file", default="", help="file into which data are exported (default: stdout)")
    parser.add_argument("table", help="table from which data are exported")


def add_query_arguments(parser: argparse.ArgumentParser):
    """Defines formal arguments for the 'chado query' subcommand"""
    parser.add_argument("-H", "--include_header", action="store_true", help="include header in output (default: False)")
    parser.add_argument("-d", "--delimiter", default="\t",
                        help="Character delimiting fields in file (default: tab)")
    parser.add_argument("-o", "--output_file", default="", help="file into which data are exported (default: stdout)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-f", "--input_file", default="", help="file containing an SQL query")
    group.add_argument("-q", "--query", default="", help="SQL query")
