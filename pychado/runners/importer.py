import sys
import os
import argparse
from pychado import tasks


def run(description):
    """Imports data from a text file into a table of a CHADO database"""
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
        "-f", "--input_file",
        dest="input",
        help="file from which data are imported (default: stdin)")
    parser.add_argument("dbname", help="name of the database")
    parser.add_argument("table", help="table into which data are imported")
    arguments = parser.parse_args(sys.argv[2:])
    tasks.importer(arguments.config, arguments.dbname, arguments.table, arguments.input, arguments.delimiter)
