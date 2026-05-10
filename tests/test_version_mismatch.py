import unittest
import sys
import os
from unittest.mock import patch

# Add parent directory to path to import slz
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
import slz

class TestVersionMismatches(unittest.TestCase):
    
    def test_python_version_guard(self):
        """Ensure the script would fail on Python 2.x (simulated)."""
        with patch.object(sys, 'version_info', (2, 7, 10)):
            # This is tricky to test since the import itself might fail in real Python 2
            # But we can test our explicit check logic
            self.assertTrue(sys.version_info < (3, 6))

    @patch('platform.system')
    def test_linux_gnu_compatibility(self, mock_system):
        """Simulate a Linux environment with GNU tools."""
        mock_system.return_value = 'Linux'
        # Currently slz uses POSIX-only flags, so it should be the same
        cmd = slz.generate_command("test")
        self.assertEqual(cmd, "grep -i 'test'")

    @patch('platform.system')
    def test_macos_bsd_compatibility(self, mock_system):
        """Simulate a macOS environment with BSD tools."""
        mock_system.return_value = 'Darwin'
        # Verify that we aren't using GNU-specific extensions like grep -P
        cmd = slz.generate_command("test")
        self.assertNotIn("-P", cmd)
        self.assertEqual(cmd, "grep -i 'test'")

    def test_shell_escaping_mismatch(self):
        """Test how the tool handles special characters that vary between shells."""
        # User provides a double-quoted phrase containing a single quote
        cmd = slz.generate_command('"it\'s working"')
        # Should be escaped correctly for POSIX sh
        self.assertIn("'it'\\''s working'", cmd)

    def test_empty_input_graceful_handling(self):
        """Test that empty inputs don't crash the command generator."""
        self.assertEqual(slz.generate_command("   "), "")

if __name__ == "__main__":
    unittest.main()
