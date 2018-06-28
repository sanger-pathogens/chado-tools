import sys
import os
import argparse
from pychado import tasks


def run(description):
    """Dump the schema of a CHADO database"""
    parser = argparse.ArgumentParser(
        description=description,
        prog=(os.path.basename(sys.argv[0]) + " " + sys.argv[1]))
    parser.add_argument(
        "-c", "--config",
        dest="config",
        help="YAML file containing connection details")
    parser.add_argument(
        "-o", "--output",
        dest="output",
        help="File into which the database dump is written (default: stdout)",
        default="-")
    arguments = parser.parse_args(sys.argv[2:])
    tasks.dump(arguments.config, arguments.output)
