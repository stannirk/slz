import unittest
import sys
import os
import io
import queue
import threading
import time
from unittest.mock import patch, MagicMock

# Add parent directory to path to import slz
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
from slz import generate_command, filter_lines, read_stdin

class TestAudit(unittest.TestCase):
    
    def test_extremely_long_lines(self):
        """Test how the filter handles extremely long lines."""
        long_line = "a" * 1000000 # 1MB line
        lines = [long_line, "short line"]
        # Filtering for "short" should still work
        result = filter_lines(lines, "short")
        self.assertEqual(result, ["short line"])
        
        # Filtering for something in the long line
        result = filter_lines(lines, "a" * 1000)
        self.assertEqual(result, [long_line])

    def test_many_columns(self):
        """Test lines with many columns."""
        cols = [f"col{i}" for i in range(1000)]
        line = " ".join(cols)
        lines = [line]
        
        # Extract last column
        result = filter_lines(lines, "col:1000")
        self.assertEqual(result, ["col999"])
        
        # Out of bounds column
        result = filter_lines(lines, "col:1001")
        self.assertEqual(result, [])

    def test_shlex_complexity(self):
        """Test complex shlex inputs."""
        # Nested quotes (shlex might handle this differently than expected if not careful)
        user_input = "'grep with space' \"another one\""
        cmd = generate_command(user_input)
        self.assertIn("grep -i 'grep with space'", cmd)
        self.assertIn("grep -i 'another one'", cmd)

    def test_line_truncation_safety(self):
        """Verify that individual lines are truncated if too long."""
        q = queue.Queue()
        long_line = "x" * 10000
        mock_stdin = io.StringIO(long_line + "\n")
        
        read_stdin(q, 10, mock_stdin)
            
        line = q.get()
        self.assertEqual(len(line), 4096 + len(" [Line Truncated]"))
        self.assertTrue(line.endswith(" [Line Truncated]"))

    def test_read_stdin_error_handling(self):
        """Test read_stdin with various failure modes."""
        q = queue.Queue()
        
        # Mock sys.stdin to raise an error during iteration
        class ErrorStdin:
            def __iter__(self):
                yield "line1"
                raise UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte")
        
        read_stdin(q, 100, ErrorStdin())
            
        items = []
        while not q.empty():
            items.append(q.get())
        
        self.assertIn("line1", items)
        self.assertIn("Error: Could not decode input as UTF-8.", items)
        self.assertIsNone(items[-1]) # Sentinel

    def test_case_sensitivity_consistency(self):
        """Verify that preview matches generated command behavior for case sensitivity."""
        lines = ["Apple", "banana"]
        user_input = "apple"
        
        # Current preview is case-insensitive
        preview = filter_lines(lines, user_input)
        self.assertIn("Apple", preview)
        
        # Generated command should ideally be case-insensitive too, or preview should be case-sensitive.
        # Most users expect case-insensitive search in TUIs like this.
        cmd = generate_command(user_input)
        self.assertIn("grep -i", cmd.lower()) # Checking if -i is used


if __name__ == "__main__":
    unittest.main()
