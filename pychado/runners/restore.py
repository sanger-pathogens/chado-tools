import sys
import os
import argparse
from pychado import tasks


def run(description):
    """Restores a CHADO database from an archive file"""
    parser = argparse.ArgumentParser(
        description=description,
        prog=(os.path.basename(sys.argv[0]) + " " + sys.argv[1]))
    parser.add_argument(
        "-c", "--config",
        dest="config",
        help="YAML file containing connection details")
    parser.add_argument("dbname", help="name of the database")
    parser.add_argument("archive", help="name of the archive file")
    arguments = parser.parse_args(sys.argv[2:])
    tasks.restore(arguments.config, arguments.dbname, arguments.archive)
