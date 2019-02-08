import sys
import os
import unittest
import subprocess
import string
import io
import filecmp
import tempfile
from contextlib import redirect_stdout
from .. import utils


class TestUtils(unittest.TestCase):
    """Class for testing utilities"""

    modules_dir = os.path.dirname(os.path.abspath(utils.__file__))
    data_dir = os.path.join(modules_dir, 'tests', 'data')

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
        text = utils.random_string(100)
        filename = tempfile.mkstemp()[1]
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
            utils.open_file_read(os.path.join(self.data_dir, 'utils_test_not_really_zipped.gz'))
        with self.assertRaises(FileNotFoundError):
            utils.open_file_write(os.path.join('not_a_directory', 'this_file_is_not_here_so_throw_error'))
        with self.assertRaises(FileNotFoundError):
            utils.open_file_write(os.path.join('not_a_directory', 'this_file_is_not_here_so_throw_error.gz'))

    def test_write_csv(self):
        # checks that data are correctly written into a CSV file
        data = [["name", "clade", "legs", "extinct"],
                ["leech", "annelid", "0", "f"],
                ["human", "mammal", "2", "f"],
                ["diplodocus", "reptile", "4", "t"],
                ["bumblebee", "insect", "6", "f"]]
        filename = tempfile.mkstemp()[1]
        self.assertTrue(os.path.exists(os.path.abspath(filename)))
        utils.write_csv(filename, ";", data)
        self.assertTrue(filecmp.cmp(filename, os.path.join(self.data_dir, "dbutils_species_table.csv")))
        os.remove(filename)
        self.assertFalse(os.path.exists(os.path.abspath(filename)))

    def test_yaml_parser(self):
        # checks if a yaml file is parsed correctly
        filename = os.path.join(self.data_dir, "utils_yaml_example.yml")
        content = utils.parse_yaml(filename)
        self.assertIn("institute", content)
        self.assertEqual(content["institute"], "Sanger")
        self.assertIn("founded", content)
        self.assertEqual(content["founded"], "1993")
        self.assertIn("faculties", content)
        self.assertIn("parasites and microbes", content["faculties"])
        self.assertNotIn("zebrafish genetics", content["faculties"])

    def test_parse_string(self):
        # checks if a string is parsed correctly
        parsed = utils.parse_string("true")
        self.assertTrue(parsed)
        parsed = utils.parse_string("FALSE")
        self.assertFalse(parsed)
        parsed = utils.parse_string("765")
        self.assertEqual(parsed, 765)
        parsed = utils.parse_string("76.5")
        self.assertEqual(parsed, 76.5)
        parsed = utils.parse_string("ture")
        self.assertEqual(parsed, "ture")

    def test_list_to_string(self):
        # checks if a list is correctly concatenated
        test_list = [1.123, None, 'hello', True, 'A', 8, False]
        test_string = utils.list_to_string(test_list, "_")
        self.assertEqual(test_string, "1.123__hello_t_A_8_f")
        test_string_with_prefix = utils.list_to_string(test_list, "\t", "A")
        self.assertEqual(test_string_with_prefix, "A.1.123\tA.\tA.hello\tA.t\tA.A\tA.8\tA.f")

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

    def test_copy_attributes(self):
        # checks if a function correctly copies attributes from one object to another
        john = utils.EmptyObject(name="John", age=42, sex="m")
        mike = utils.EmptyObject(name="Mike", age=23, sex="m")
        updated = utils.copy_attribute(john, mike, "age")
        self.assertTrue(updated)
        self.assertEqual(getattr(john, "age"), 23)
        updated = utils.copy_attribute(john, mike, "sex")
        self.assertFalse(updated)
        updated = utils.copy_attribute("abc", "def", "xyz")
        self.assertFalse(updated)
        updated = utils.copy_attribute("abc", 567, "xyz")
        self.assertFalse(updated)

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

    def test_random_string(self):
        # tests if a function generates a random string of lowercase letters
        string1 = utils.random_string(8)
        self.assertEqual(len(string1), 8)
        for letter in string1:
            self.assertIn(letter, string.ascii_lowercase)
        string2 = utils.random_string(8)
        self.assertNotEqual(string1, string2)

    def test_random_integer(self):
        # tests if a function generates a random integer
        int1 = utils.random_integer(10000)
        self.assertLessEqual(int1, 10000)
        self.assertGreaterEqual(int1, 0)
        int2 = utils.random_integer(10000)
        self.assertNotEqual(int1, int2)

    def test_random_float(self):
        # tests if a function generates a random float number between 0 and 1
        float1 = utils.random_float()
        self.assertGreaterEqual(float1, 0.0)
        self.assertLessEqual(float1, 1.0)
        float2 = utils.random_float()
        self.assertFalse(abs(float1 - float2) < 0.00001)

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
