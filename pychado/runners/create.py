import sys
import os
import argparse
from pychado import tasks


def run(description):
    """Create a new CHADO database"""
    parser = argparse.ArgumentParser(
        description=description,
        prog=(os.path.basename(sys.argv[0]) + " " + sys.argv[1]))
    parser.add_argument(
        "-c", "--config",
        dest="config",
        help="YAML file containing connection details")
    parser.add_argument(
        "-s", "--schema",
        dest="schema",
        help="File with database schema (default: GMOD schema 1.31)")
    parser.add_argument("dbname", help="name of the database to be created")
    arguments = parser.parse_args(sys.argv[2:])
    tasks.create(arguments.config, arguments.schema, arguments.dbname)
