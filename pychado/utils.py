import sys
import os
import subprocess
import yaml


def open_file_read(filename: str):
    """Function opening a (potentially gzipped) text file for read access"""
    if filename == "-":
        # Read from stdin
        f = sys.stdin
    else:
        # Check if file exists
        filepath = os.path.abspath(filename)
        if not os.path.exists(filepath):
            raise FileNotFoundError("File '" + filepath + "' does not exist.")
        # Open file for reading
        if filename.endswith(".gz"):
            subprocess.check_call("gunzip -t " + filename, shell=True, stderr=subprocess.DEVNULL)
            f = os.popen("gunzip -c " + filename, "r")
        else:
            f = open(filename, "r")
    return f


def open_file_write(filename: str):
    """Function opening a (potentially gzipped) text file for write access"""
    if filename == "-":
        # Write to stdout
        f = sys.stdout
    else:
        # Check if path exists
        filepath = os.path.abspath(os.path.dirname(filename))
        if not os.path.exists(filepath):
            raise FileNotFoundError("Directory '" + filepath + "' does not exist.")
        # Open file for writing
        if filename.endswith(".gz"):
            f = os.popen("gzip -9 -c > " + filename, "w")
        else:
            f = open(filename, "w")
    return f


def close(file):
    """Function closing a text file"""
    if file not in [sys.stdout, sys.stderr]:
        file.close()


def read_text(filename: str) -> str:
    """Function reading text from a file"""
    file = open_file_read(filename)
    content = file.read()
    close(file)
    return content


def write_text(filename: str, content: str) -> None:
    """Function writing text to a file"""
    file = open_file_write(filename)
    file.write(content)
    close(file)


def parse_yaml(filename: str) -> dict:
    """Function parsing a YAML file"""
    stream = open_file_read(filename)
    data = dict(yaml.load(stream))
    for key, value in data.items():
        if value is not None:
            data[key] = str(value).strip()
    close(stream)
    return data


def dump_yaml(filename: str, data: dict) -> None:
    """Function dumping data into a YAML file"""
    stream = open_file_write(filename)
    yaml.dump(data, stream)
    close(stream)
