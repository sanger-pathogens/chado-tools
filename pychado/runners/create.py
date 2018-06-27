import sys
import os
import argparse
import pkg_resources
from pychado import tasks


def run(description):
    """Create a new CHADO database"""
    defaultConfigFile = pkg_resources.resource_filename("pychado", "data/exampleDB.yml")
    defaultSchemaFile = pkg_resources.resource_filename("pychado", "data/gmod_schema.sql")
    parser = argparse.ArgumentParser(
        description=description,
        prog=(os.path.basename(sys.argv[0]) + " " + sys.argv[1]))
    parser.add_argument(
        "-c", "--config",
        dest="config",
        help="YAML file containing connection details (for an existing database)",
        default=defaultConfigFile)
    parser.add_argument(
        "-s", "--schema",
        dest="schema",
        help="Database schema (default: most recent GMOD schema)",
        default=defaultSchemaFile)
    parser.add_argument("dbname", help="name of the database to be created")
    arguments = parser.parse_args(sys.argv[2:])
    tasks.create(arguments.config, arguments.schema, arguments.dbname)
