import unittest
import sys
import os

# Add parent directory to path to import slz
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
from slz import filter_lines, generate_command

class TestUsecases(unittest.TestCase):
    def setUp(self):
        self.process_lines = [
            "USER   PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND",
            "root     1  0.0  0.1 168392 11216 ?        Ss   Apr10   0:06 /sbin/init",
            "user   1234  5.0  2.3 456789 23456 ?        Sl   10:00   1:23 /opt/google/chrome/chrome",
            "user   1235  0.1  1.0 234567 12345 ?        S    10:00   0:05 /opt/google/chrome/chrome --type=renderer"
        ]
        self.log_lines = [
            "2023-10-27T10:00:00Z INFO User login successful",
            "2023-10-27T10:05:00Z ERROR 500 Internal Server Error: Database timeout",
            "2023-10-27T10:06:00Z WARN High latency detected",
            "2023-10-27T10:10:00Z ERROR 500 Internal Server Error: Connection refused"
        ]

    def test_process_management(self):
        user_input = "chrome col:2"
        cmd = generate_command(user_input)
        self.assertIn("grep -i 'chrome'", cmd)
        self.assertIn("awk '{print $2}'", cmd)
        
        filtered = filter_lines(self.process_lines, user_input)
        self.assertEqual(filtered, ["1234", "1235"])

    def test_log_surgery(self):
        user_input = "error 500 col:1"
        filtered = filter_lines(self.log_lines, user_input)
        self.assertEqual(filtered, ["2023-10-27T10:05:00Z", "2023-10-27T10:10:00Z"])

    def test_regex_support(self):
        user_input = "r:10:[0-9]{2}:00Z col:2"
        filtered = filter_lines(self.log_lines, user_input)
        self.assertEqual(filtered, ["INFO", "ERROR", "WARN", "ERROR"])
        
        cmd = generate_command(user_input)
        self.assertIn("grep -E -i '10:[0-9]{2}:00Z'", cmd)

    def test_multi_column(self):
        user_input = "chrome col:2, COMMAND"
        # Search for chrome, then search for COMMAND (literal), then extract col 2
        # Wait, "COMMAND" in user_input will grep for it.
        # If I want col 2 and something else, I should use col:2,3
        user_input = "chrome col:2,3"
        filtered = filter_lines(self.process_lines, user_input)
        # col 2 is PID, col 3 is %CPU
        self.assertEqual(filtered, ["1234 5.0", "1235 0.1"])
        
        cmd = generate_command(user_input)
        self.assertIn("awk '{print $2, $3}'", cmd)

    def test_column_range(self):
        user_input = "root col:1-3"
        filtered = filter_lines(self.process_lines, user_input)
        self.assertEqual(filtered, ["root 1 0.0"])
        
        cmd = generate_command(user_input)
        self.assertIn("awk '{print $1, $2, $3}'", cmd)

    def test_custom_separator(self):
        lines = ["a,b,c", "d,e,f"]
        user_input = "sep:, col:2"
        filtered = filter_lines(lines, user_input)
        self.assertEqual(filtered, ["b", "e"])
        
        cmd = generate_command(user_input)
        self.assertIn("awk -F',' '{print $2}'", cmd)

    def test_col_zero_validation(self):
        # col:0 should be ignored or handled safely (not $0)
        user_input = "col:0"
        cmd = generate_command(user_input)
        self.assertEqual(cmd, "") # Should be empty or ignored
        
        filtered = filter_lines(self.process_lines, user_input)
        self.assertEqual(filtered, self.process_lines)

if __name__ == "__main__":
    unittest.main()
