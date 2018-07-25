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
    parser.add_argument("dbname", help="name of the database")
    parser.add_argument("table", help="table from which data are exported")
    arguments = parser.parse_args(sys.argv[2:])
    tasks.exporter(arguments.config, arguments.dbname, arguments.table, arguments.output, arguments.delimiter,
                   arguments.header)
