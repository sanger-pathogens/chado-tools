import sys
import os
import io
import subprocess
import ruamel.yaml


def open_file_read(filename: str) -> io.TextIOBase:
    """Function opening a (potentially gzipped) text file for read access"""
    if filename == "-":
        f = sys.stdin
    elif filename.endswith(".gz"):
        if subprocess.call("gunzip -t " + filename, shell=True) != 0:
            raise Exception("Error opening for reading gzipped file '" + filename + "'")
        f = os.popen("gunzip -c " + filename)
    else:
        f = open(filename, "r")
    return f


def open_file_write(filename: str) -> io.TextIOBase:
    """Function opening a (potentially gzipped) text file for write access"""
    if filename == "-":
        f = sys.stdout
    elif filename.endswith(".gz"):
        if not os.path.exists(os.path.abspath(os.path.dirname(filename))):
            raise Exception("Error opening for writing gzipped file '" + filename + "'")
        f = os.popen("gzip -9 -c > " + filename, "w")
    else:
        f = open(filename, "w")
    return f


def close(file: io.TextIOBase):
    """Function closing a text file"""
    if file not in [sys.stdout, sys.stderr]:
        file.close()


def parse_yaml(filename: str) -> dict:
    """Function parsing a YAML file"""
    stream = open(filename, "r")
    data = dict(ruamel.yaml.load(stream, Loader=ruamel.yaml.Loader))
    for key, value in data.items():
        if value is not None:
            data[key] = str(value).strip()
    stream.close()
    return data
