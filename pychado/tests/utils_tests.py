import sys
import os
import unittest
import subprocess
import string
import random
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
        f = utils.open_file_read('-')
        self.assertEqual(sys.stdin, f)
        f = utils.open_file_write('-')
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


if __name__ == '__main__':
    unittest.main(buffer=True)
