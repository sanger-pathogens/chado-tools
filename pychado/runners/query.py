import sys
import os
import argparse
from pychado import tasks


def run(description):
    """Queries a CHADO database and exports the result into a text file"""
    parser = argparse.ArgumentParser(
        description=description,
        prog=(os.path.basename(sys.argv[0]) + " " + sys.argv[1]))
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
        "-o", "--output",
        dest="output",
        help="name of the file into which data are exported (default: stdout)")
    parser.add_argument("dbname", help="name of the database")
    parser.add_argument("query", help="SQL query")
    arguments = parser.parse_args(sys.argv[2:])
    tasks.query(arguments.config, arguments.dbname, arguments.query, arguments.output, arguments.delimiter)
