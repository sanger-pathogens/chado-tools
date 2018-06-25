"""Connect to a database"""

import sys
import os
import argparse
from pychado import tasks


def run(description):
    parser = argparse.ArgumentParser(description=description, prog=(os.path.basename(sys.argv[0]) + ' ' + sys.argv[1]))
    parser.add_argument('file', help="Name of YAML file containing connection details")
    arguments = parser.parse_args(sys.argv[2:])
    tasks.connect(arguments.file)
