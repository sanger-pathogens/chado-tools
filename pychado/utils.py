import sys
import os
import datetime
import subprocess
import urllib.request
import string
import random
import yaml


class EmptyObject:
    """Helper class that creates objects with attributes supplied by keyword arguments"""
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class VerbosePrinter:
    """Class printing messages if verbose argument is set"""

    def __init__(self, verbose: bool, separator=";"):
        """Constructor"""
        self.verbose = verbose
        self.separator = separator

    def print(self, message):
        """Prints a message if set to verbose. If the message is a list, the method prints all elements,
        separated by the set separator"""
        if self.verbose:
            if isinstance(message, list):
                print(*message, sep=self.separator)
            else:
                print(message)


def open_file_read(filename: str):
    """Function opening a (potentially gzipped) text file for read access"""
    if not filename:
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
    if not filename:
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


def write_csv(filename: str, delimiter: str, content: list) -> None:
    """Function writing data arranged in a table into a CSV file"""
    file = open_file_write(filename)
    for row in content:
        file.write(list_to_string(row, delimiter) + "\n")
    close(file)


def parse_yaml(filename: str) -> dict:
    """Function parsing a YAML file"""
    stream = open_file_read(filename)
    data = yaml.load(stream, Loader=yaml.BaseLoader)
    for key, value in data.items():
        if value is not None:
            data[key] = str(value).strip()
    close(stream)
    return data


def dump_yaml(filename: str, data: dict) -> None:
    """Function dumping data into a YAML file"""
    stream = open_file_write(filename)
    yaml.dump(data, stream, Dumper=yaml.BaseDumper)
    close(stream)


def parse_string(the_string: str):
    """Converts a string to an integer/float/boolean, if applicable"""
    if is_string_float(the_string):
        return float(the_string)
    elif is_string_integer(the_string):
        return int(the_string)
    elif the_string.lower() == "true":
        return True
    elif the_string.lower() == "false":
        return False
    else:
        return the_string


def is_string_integer(the_string: str) -> bool:
    """Tests whether a string can be represented as integer number"""
    try:
        int(the_string)
        return True
    except ValueError:
        return False


def is_string_float(the_string: str) -> bool:
    """Tests whether a string can be represented as floating-point number"""
    try:
        float(the_string)
        return True
    except ValueError:
        return False


def list_to_string(the_list: list, delimiter: str, prefix=None) -> str:
    """Function concatenating all elements of a list"""
    the_string = []
    for element in the_list:
        if isinstance(element, bool) and element:
            the_string.append('t')
        elif isinstance(element, bool) and not element:
            the_string.append('f')
        elif isinstance(element, str):
            the_string.append(element)
        elif element is None:
            the_string.append("")
        else:
            the_string.append(str(element))
    if not prefix:
        return delimiter.join(the_string)
    else:
        return delimiter.join([prefix + "." + item for item in the_string])


def filter_objects(entries: list, **kwargs) -> list:
    """Filters a list of objects of any type according to given keyword arguments"""
    filtered_entries = []
    for entry in entries:
        for key, value in kwargs.items():
            if getattr(entry, key) != value:
                break
        else:
            filtered_entries.append(entry)
    return filtered_entries


def copy_attribute(old_object, new_object, attribute: str) -> bool:
    """Copies the value of a given attribute from one object to another"""
    new_value = getattr(new_object, attribute, None)
    old_value = getattr(old_object, attribute, None)
    if type(old_object) == type(new_object) and new_value is not None and old_value != new_value:
        setattr(old_object, attribute, new_value)
        return True
    return False


def list_to_dict(entries: list, key: str) -> dict:
    """Converts a list of objects of any type into a dictionary, using a specified object parameter as key"""
    dictionary = {}
    for entry in entries:
        current_key = getattr(entry, key)
        dictionary[current_key] = entry
    return dictionary


def random_string(n: int) -> str:
    """Generates a random string of n lowercase letters"""
    return "".join(random.choices(string.ascii_lowercase, k=n))


def random_integer(n: int) -> int:
    """Generates a random integer in the range [0, n]"""
    return random.randint(0, n)


def random_float() -> float:
    """Generates a random positive float number between 0 and 1"""
    n1 = random_integer(1000) + 1
    n2 = random_integer(1000) + 1
    if n2 > n1:
        return float(n1)/float(n2)
    else:
        return float(n2)/float(n1)


def current_date() -> str:
    """Function returning the current date in format 'YYYYMMDD"""
    return datetime.date.today().strftime('%Y%m%d')


def download_file(url: str) -> str:
    """Downloads a file from the internet"""
    print("Downloading file from URL " + url + " ...")
    file, headers = urllib.request.urlretrieve(url)
    return file
