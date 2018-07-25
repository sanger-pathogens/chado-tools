import sys
import os
import argparse
from pychado import tasks, utils


def run(description):
    """Queries a CHADO database and exports the result into a text file"""
    parser = argparse.ArgumentParser(
        description=description,
        prog=(os.path.basename(sys.argv[0]) + " " + sys.argv[1]))
    parser.add_argument(
        "-H", "--include_header",
        dest="header",
        action="store_true",
        help="include header in output (default: no header)")
    parser.add_argument(
        "-c", "--config",
        dest="config",
        help="YAML file containing connection details")
    parser.add_argument(
        "-d", "--delimiter",
        dest="delimiter",
        help="Character delimiting fields in file (default: tab)",
        default="\t")
    parser.add_argument(
        "-o", "--output_file",
        dest="output",
        help="file into which data are exported (default: stdout)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "-f", "--input_file",
        dest="input_file",
        help="file containing an SQL query")
    group.add_argument("-q", "--query", dest="query", help="SQL query")
    parser.add_argument("dbname", help="name of the database")
    arguments = parser.parse_args(sys.argv[2:])
    if arguments.input_file:
        arguments.query = utils.read_text(arguments.input_file)
    tasks.query(arguments.config, arguments.dbname, arguments.query, arguments.output, arguments.delimiter,
                arguments.header)
