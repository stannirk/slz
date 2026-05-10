import unittest
import subprocess
import sys
import os

class TestEntryPoint(unittest.TestCase):
    def test_help_command(self):
        """Verifies that 'slz --help' runs without crashing (checks imports and entry point)."""
        # Set PYTHONPATH to include the src directory
        env = os.environ.copy()
        src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
        env["PYTHONPATH"] = f"{src_path}{os.pathsep}{env.get('PYTHONPATH', '')}"
        
        # Run slz with --help. It shouldn't crash with a NameError (like the missing 'os' bug).
        try:
            result = subprocess.run(
                [sys.executable, "-m", "slz", "--help"],
                capture_output=True,
                text=True,
                env=env,
                timeout=5
            )
            self.assertEqual(result.returncode, 0, f"slz --help failed with: {result.stderr}")
            self.assertIn("SLZ: Interactive Pipe Translator", result.stdout)
        except subprocess.TimeoutExpired:
            self.fail("slz --help timed out")

if __name__ == "__main__":
    unittest.main()
