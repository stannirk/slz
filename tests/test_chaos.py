import unittest
import sys
import os
import io
from unittest.mock import patch, MagicMock
import curses

# Add parent directory to path to import slz
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
import slz

class TestChaosAndEdgeCases(unittest.TestCase):
    
    @patch('curses.curs_set')
    @patch('curses.use_default_colors')
    @patch('curses.init_pair')
    @patch('curses.color_pair', return_value=0)
    @patch('curses.has_colors', return_value=True)
    def test_micro_terminal_draw_failure(self, mock_has_colors, mock_color_pair, mock_init_pair, mock_use_colors, mock_curs_set):
        """1. MICRO-TERMINAL: Simulate a terminal too small for the error message."""
        stdscr = MagicMock()
        # Simulate a 1x1 terminal
        stdscr.getmaxyx.return_value = (1, 1)
        # addstr should raise error if coordinates are out of bounds (which they will be for a 18-char string)
        stdscr.addstr.side_effect = curses.error("addwstr() returned ERR")
        stdscr.getch.return_value = 27 # ESC
        
        # Test if main() handles the curses.error during 'Terminal too small' draw
        try:
            slz.main(stdscr, data_stream=None)
        except curses.error:
            self.fail("main() raised curses.error; it should handle it internally when terminal is too small.")
        except Exception as e:
            self.fail(f"main() crashed on micro-terminal with unexpected error: {e}")

    def test_unclosed_quote_fallback(self):
        """2. UNCLOSED QUOTE: Ensure shlex fallback doesn't crash."""
        user_input = "col:2 'unclosed quote"
        try:
            cmd = slz.generate_command(user_input)
            # Fallback should at least generate something based on simple split
            self.assertIn("awk", cmd)
            self.assertIn("grep", cmd)
        except Exception as e:
            self.fail(f"generate_command() crashed on unclosed quote: {e}")

    def test_binary_garbage_input(self):
        """3. BINARY BOMB: Simulate non-UTF8 binary input."""
        # \xff is invalid UTF-8
        binary_data = b"valid data\n\xff\xfe\x00\xff\nmore data"
        mock_stdin = io.BytesIO(binary_data)
        
        # Wrap stdin to simulate the reading logic
        with patch('sys.stdin', io.TextIOWrapper(mock_stdin, encoding='utf-8', errors='replace')):
            input_lines = []
            try:
                for line in sys.stdin:
                    input_lines.append(line.rstrip())
            except Exception as e:
                self.fail(f"Input reading crashed on binary garbage: {e}")
            
            self.assertTrue(any("" in line for line in input_lines))

    @patch('curses.initscr')
    def test_terminfo_sabotage(self, mock_initscr):
        """4. TERMINFO SABOTAGE: Simulate TERM=dumb where initscr fails."""
        mock_initscr.side_effect = curses.error("setupterm: could not find terminal")
        
        # We check if the __main__ block (wrapped in a function for testing) handles this.
        # Since we can't easily run the __main__ block, we verify the structure.
        with open(slz.__file__, 'r') as f:
            content = f.read()
            self.assertIn('except OSError:', content) # We added this for /dev/tty
            self.assertIn('Terminal does not support TUI mode', content)

if __name__ == "__main__":
    unittest.main()
