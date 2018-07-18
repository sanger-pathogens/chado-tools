import sys
import os
import argparse
from pychado import tasks


def run(description):
    """Exports data from a table of a CHADO database into a text file"""
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
        help="Character delimiting fields in file",
        default="\t")
    parser.add_argument("dbname", help="name of the database")
    parser.add_argument("table", help="name of the table from which data are exported")
    parser.add_argument("file", help="name of the file into which data are exported")
    arguments = parser.parse_args(sys.argv[2:])
    tasks.exporter(arguments.config, arguments.dbname, arguments.table, arguments.file, arguments.delimiter)
