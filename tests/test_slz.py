import unittest
import sys
import os

# Add parent directory to path to import slz
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
from slz import generate_command, filter_lines

class TestSLZ(unittest.TestCase):
    
    def test_generate_grep(self):
        self.assertEqual(generate_command("chrome"), "grep -i 'chrome'")
        self.assertEqual(generate_command("error logs"), "grep -i 'error' | grep -i 'logs'")

    def test_generate_awk(self):
        self.assertEqual(generate_command("col:2"), "awk '{print $2}'")

    def test_generate_combined(self):
        result = generate_command("col:2 chrome")
        self.assertIn("awk '{print $2}'", result)
        self.assertIn("grep -i 'chrome'", result)

    def test_filter_lines_simple(self):
        lines = ["apple", "banana", "cherry"]
        self.assertEqual(filter_lines(lines, "ba"), ["banana"])

    def test_filter_lines_column(self):
        lines = ["1 root info", "2 user warn", "3 admin error"]
        # Extract column 2
        self.assertEqual(filter_lines(lines, "col:2"), ["root", "user", "admin"])

    def test_filter_lines_combined(self):
        lines = ["1 root info", "2 user warn", "3 admin error"]
        # Extract column 2 AND search for 'r'
        self.assertEqual(filter_lines(lines, "col:2 r"), ["root", "user"])

if __name__ == "__main__":
    unittest.main()
