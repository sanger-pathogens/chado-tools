import sys
import os
import unittest
import subprocess
import string
import random
import io
from contextlib import redirect_stdout
from pychado import utils

modules_dir = os.path.dirname(os.path.abspath(utils.__file__))
data_dir = os.path.join(modules_dir, 'tests', 'data')


class TestUtils(unittest.TestCase):
    """Class for testing utilities"""

    def test_write_and_read(self):
        # open_file_write() and open_file_read() should do the right thing whether gzipped or not
        for filename in ['utils.tmp', 'utils.tmp.gz']:
            # Test write
            f = utils.open_file_write(filename)
            for i in range(3):
                print(i, file=f)
            utils.close(f)
            # Test read
            counter = 0
            f = utils.open_file_read(filename)
            for line in f:
                self.assertEqual(counter, int(line.strip()))
                counter += 1
            utils.close(f)
            # Remove files
            os.unlink(filename)
        # Test streams stdin/stdout
        f = utils.open_file_read('')
        self.assertEqual(sys.stdin, f)
        f = utils.open_file_write('')
        self.assertEqual(sys.stdout, f)

    def test_write_read_text(self):
        # tests reading and writing text from/to file
        text = ''.join(random.choices(string.ascii_lowercase, k=100)).strip()
        filename = "tmp.txt"
        utils.write_text(filename, text)
        self.assertTrue(os.path.exists(os.path.abspath(filename)))
        read_text = utils.read_text(filename)
        self.assertEqual(text, read_text)
        os.remove(filename)
        self.assertFalse(os.path.exists(os.path.abspath(filename)))

    def test_raise_exception(self):
        # open_file_write() and open_file_read() should raise an exception if opening fails
        with self.assertRaises(FileNotFoundError):
            utils.open_file_read('this_file_is_not_here_so_throw_error')
        with self.assertRaises(FileNotFoundError):
            utils.open_file_read('this_file_is_not_here_so_throw_error.gz')
        with self.assertRaises(subprocess.CalledProcessError):
            utils.open_file_read(os.path.join(data_dir, 'utils_test_not_really_zipped.gz'))
        with self.assertRaises(FileNotFoundError):
            utils.open_file_write(os.path.join('not_a_directory', 'this_file_is_not_here_so_throw_error'))
        with self.assertRaises(FileNotFoundError):
            utils.open_file_write(os.path.join('not_a_directory', 'this_file_is_not_here_so_throw_error.gz'))

    def test_yaml_parser(self):
        # checks if a yaml file is parsed correctly
        filename = os.path.join(data_dir, "utils_yaml_example.yml")
        content = utils.parse_yaml(filename)
        self.assertIn("institute", content)
        self.assertEqual(content["institute"], "Sanger")
        self.assertIn("founded", content)
        self.assertEqual(content["founded"], "1993")
        self.assertIn("faculties", content)
        self.assertIn("parasites and microbes", content["faculties"])
        self.assertNotIn("zebrafish genetics", content["faculties"])

    def test_list_to_string(self):
        # checks if a list is correctly concatenated
        test_list = [1.123, None, 'hello', True, 'A', 8, False]
        test_string = utils.list_to_string(test_list, "_")
        self.assertEqual(test_string, "1.123__hello_t_A_8_f")

    def test_filter_objects(self):
        # checks if a function correctly filters objects in a list according to keyword arguments
        john = utils.EmptyObject(name="John", age=42, sex="m")
        mike = utils.EmptyObject(name="Mike", age=23, sex="m")
        persons = [john, mike]
        filtered_persons = utils.filter_objects(persons, name="Mike", sex="m")
        self.assertEqual(len(filtered_persons), 1)
        self.assertEqual(filtered_persons[0], mike)
        with self.assertRaises(AttributeError):
            utils.filter_objects(persons, heads=2)

    def test_list_to_dict(self):
        # checks if a function correctly converts a list into a dictionary
        john = utils.EmptyObject(name="John")
        mike = utils.EmptyObject(name="Mike")
        persons = [john, mike]
        persons_dict = utils.list_to_dict(persons, "name")
        self.assertEqual(len(persons_dict), 2)
        self.assertIn("John", persons_dict)
        self.assertEqual(persons_dict["John"], john)
        with self.assertRaises(AttributeError):
            utils.list_to_dict(persons, "age")

    def test_current_date(self):
        # checks if a function returns the current date in the correct format
        date = utils.current_date()
        self.assertEqual(len(date), 8)
        self.assertEqual(int(date[0]), 2)
        self.assertTrue(int(date[4:5]) <= 12)
        self.assertTrue(int(date[6:7]) <= 31)

    def test_verbose_printer(self):
        # tests the verpose printer
        printer = utils.VerbosePrinter(True, "-")
        f = io.StringIO()
        with redirect_stdout(f):
            printer.print(["AAA", "BBB"])
            printed = f.getvalue()
        self.assertEqual(printed, "AAA-BBB\n")


if __name__ == '__main__':
    unittest.main(verbosity=2, buffer=True)
