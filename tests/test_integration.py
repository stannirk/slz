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
        from unittest.mock import patch, MagicMock
        import io
        
        # Mock curses.wrapper to simulate user entering 'col:1' and then hitting Enter
        # It should return (user_input, gathered_lines)
        mock_lines = ["line1 col1", "line2 col2"]
        with patch("slz.curses.wrapper", return_value=("col:1", mock_lines)):
            with patch("sys.stdin.isatty", return_value=False):
                with patch("sys.stdout", new=io.StringIO()) as mock_stdout:
                    # Mock open('/dev/tty')
                    mock_tty = MagicMock()
                    mock_tty.fileno.return_value = 999
                    
                    with patch("builtins.open", side_effect=lambda *args, **kwargs: mock_tty if args[0] == '/dev/tty' else open(*args, **kwargs)):
                        with patch("os.dup", return_value=1000):
                            with patch("os.dup2"):
                                with patch("os.fdopen", side_effect=lambda fd, mode: mock_stdout if fd == 1 else io.StringIO()):
                                    with patch("os.close"):
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

    def test_filter_mode_e2e(self):
        """End-to-end test of the filtering logic via a subprocess call."""
        # We simulate the filter logic by calling a python snippet that uses slz's filter_lines
        # This bypasses the TUI but exercises the actual filtering engine used by the CLI
        cmd = [
            sys.executable, "-c",
            "import sys, os; "
            "sys.path.insert(0, os.path.join(os.getcwd(), 'src')); "
            "from slz import filter_lines; "
            "print(filter_lines(['user 1234 chrome', 'root 1 init'], 'chrome col:2')[0])"
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        self.assertEqual(result.stdout.strip(), "1234")

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

    def test_non_interactive_mode(self):
        """Tests the new -n/--non-interactive flag."""
        input_data = "hello\nworld\n"
        result = subprocess.run(
            [sys.executable, "-m", "slz", "hello", "-n", "-f"],
            input=input_data,
            capture_output=True,
            text=True,
            env=self.env
        )
        self.assertEqual(result.stdout.strip(), "hello")
        self.assertEqual(result.returncode, 0)

    def test_non_interactive_fallback(self):
        """Tests that slz falls back to non-interactive if filter is provided and TTY fails."""
        # We simulate a pipe input and provide a filter argument
        input_data = "apple\nbanana\n"
        # Since this runs in a subprocess without a real /dev/tty attached to the child,
        # it should naturally hit the OSError when trying to open /dev/tty and fallback.
        result = subprocess.run(
            [sys.executable, "-m", "slz", "banana", "-f"],
            input=input_data,
            capture_output=True,
            text=True,
            env=self.env
        )
        self.assertEqual(result.stdout.strip(), "banana")
        self.assertEqual(result.returncode, 0)

    def test_non_interactive_no_filter(self):
        """Tests that -n without filter just passes through."""
        input_data = "line1\nline2\n"
        result = subprocess.run(
            [sys.executable, "-m", "slz", "-n"],
            input=input_data,
            capture_output=True,
            text=True,
            env=self.env
        )
        self.assertEqual(result.stdout.strip(), "line1\nline2")

if __name__ == "__main__":
    unittest.main()
