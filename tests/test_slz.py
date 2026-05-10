import unittest
import sys
import os

# Add parent directory to path to import slz
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
from slz import generate_command, filter_lines, detect_col_before_filter_warning

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

    def test_filter_lines_head(self):
        lines = ["header", "line1", "line2"]
        self.assertEqual(filter_lines(lines, "head:1"), ["line1", "line2"])
        self.assertEqual(filter_lines(lines, "head:2"), ["line2"])
        self.assertEqual(filter_lines(lines, "head:0"), lines)

    def test_generate_command_head(self):
        self.assertEqual(generate_command("head:1"), "sed '1,1d'")
        self.assertEqual(generate_command("head:1 chrome"), "sed '1,1d' | grep -i 'chrome'")

    def test_header_bleed_bug_fix(self):
        lines = ['USER       PID %CPU', 'user      1234  5.2', 'root         1  0.0']
        self.assertEqual(filter_lines(lines, 'r:^user col:2 head:1'), ['1234'])
        # Without head:1, it should still include the header
        self.assertEqual(filter_lines(lines, 'r:^user col:2'), ['PID', '1234'])

    def test_col_before_text_warning(self):
        self.assertIsNotNone(detect_col_before_filter_warning("col:2 chrome"))
        self.assertIsNone(detect_col_before_filter_warning("chrome col:2"))
        self.assertIsNone(detect_col_before_filter_warning("col:2 r:foo"))
        self.assertIsNotNone(detect_col_before_filter_warning("col:2 head:1 chrome"))


if __name__ == "__main__":
    unittest.main()
