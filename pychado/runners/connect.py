import sys
import os
import argparse
from pychado import tasks


def run(description):
    """Establish a connection to a CHADO database"""
    parser = argparse.ArgumentParser(
        description=description,
        prog=(os.path.basename(sys.argv[0]) + " " + sys.argv[1]))
    parser.add_argument(
        "-c", "--config",
        dest="config",
        help="YAML file containing connection details")
    arguments = parser.parse_args(sys.argv[2:])
    tasks.connect(arguments.config)
