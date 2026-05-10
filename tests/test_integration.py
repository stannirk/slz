import unittest
import subprocess
import sys
import os
import io

class TestIntegration(unittest.TestCase):
    def setUp(self):
        self.env = os.environ.copy()
        src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
        self.env["PYTHONPATH"] = f"{src_path}{os.pathsep}{self.env.get('PYTHONPATH', '')}"

    def test_filter_mode_mocked(self):
        """Tests slz -f by mocking the TUI result."""
        from unittest.mock import patch
        
        # Mock curses.wrapper to simulate user entering 'col:1' and then hitting Enter
        # It should return (user_input, gathered_lines)
        mock_lines = ["line1 col1", "line2 col2"]
        with patch("slz.curses.wrapper", return_value=("col:1", mock_lines)):
            with patch("sys.stdin.isatty", return_value=False):
                with patch("sys.stdout", new=io.StringIO()) as mock_stdout:
                    # We need to call slz.run() but it uses argparse.sys.argv
                    with patch("sys.argv", ["slz", "-f"]):
                        import slz
                        slz.run()
                        output = mock_stdout.getvalue()
                        self.assertIn("line1\nline2", output)

    def test_version_flag(self):
        result = subprocess.run(
            [sys.executable, "-m", "slz", "--version"],
            capture_output=True,
            text=True,
            env=self.env
        )
        self.assertIn("0.2.0", result.stdout)

    @unittest.skipUnless(sys.stdin.isatty(), "Requires a TTY")
    def test_no_input_usage(self):
        # Running slz without pipe and without args should show usage
        result = subprocess.run(
            [sys.executable, "-m", "slz"],
            capture_output=True,
            text=True,
            env=self.env
        )
        self.assertIn("Usage: <command> | slz", result.stdout)
        self.assertEqual(result.returncode, 1)

    def test_no_input_usage_mocked(self):
        """Test usage message using mocks to simulate TTY-less environment (like CI)."""
        from unittest.mock import patch
        with patch("sys.stdin.isatty", return_value=True):
            with patch("sys.stdout", new=io.StringIO()) as mock_stdout:
                with patch("sys.argv", ["slz"]):
                    with self.assertRaises(SystemExit) as cm:
                        import slz
                        slz.run()
                    self.assertEqual(cm.exception.code, 1)
                    self.assertIn("Usage: <command> | slz", mock_stdout.getvalue())

if __name__ == "__main__":
    unittest.main()
