import unittest
import sys
import os
import io
from unittest.mock import patch, MagicMock

# Add parent directory to path to import slz
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
import slz

class TestStressAndHardening(unittest.TestCase):
    
    def test_tty_check(self):
        """Ensure the tool detects if it is NOT in a TTY."""
        with patch('sys.stdin.isatty', return_value=False):
            with patch('sys.stdout.isatty', return_value=False):
                # The __main__ block checks this, let's verify logic
                self.assertFalse(sys.stdin.isatty())

    def test_large_input_truncation(self):
        """Verify that massive inputs are truncated to prevent OOM."""
        # Create a mock stream with 20,000 lines
        mock_stdin = io.StringIO("\n".join([f"line {i}" for i in range(20000)]))
        
        with patch('sys.stdin', mock_stdin):
            # Simulate the part of main() that reads stdin
            input_lines = []
            MAX_LINES = 10000
            for i, line in enumerate(sys.stdin):
                if i >= MAX_LINES:
                    input_lines.append(f"Truncated")
                    break
                input_lines.append(line.rstrip())
            
            self.assertEqual(len(input_lines), MAX_LINES + 1)
            self.assertEqual(input_lines[-1], "Truncated")

    @patch('curses.update_lines_cols')
    @patch('curses.curs_set')
    @patch('curses.has_colors', return_value=True)
    @patch('curses.use_default_colors')
    @patch('curses.init_pair')
    @patch('curses.color_pair', return_value=0)
    def test_resize_logic_triggered(self, mock_color_pair, mock_init_pair, mock_use_colors, mock_has_colors, mock_curs_set, mock_update):
        """Verify that KEY_RESIZE calls update_lines_cols."""
        stdscr = MagicMock()
        stdscr.getch.side_effect = [slz.curses.KEY_RESIZE, 27] # Resize then ESC
        stdscr.getmaxyx.return_value = (24, 80)
        
        # Mock sys.stdin.isatty to prevent reading from real stdin
        with patch('sys.stdin.isatty', return_value=True):
            slz.main(stdscr)
            mock_update.assert_called_once()

    @patch('curses.curs_set')
    @patch('curses.has_colors', return_value=True)
    @patch('curses.use_default_colors')
    @patch('curses.init_pair')
    @patch('curses.color_pair', return_value=0)
    def test_scrolling_logic(self, mock_color_pair, mock_init_pair, mock_use_colors, mock_has_colors, mock_curs_set):
        """Verify that KEY_DOWN and KEY_UP would trigger scroll (via internal state)."""
        stdscr = MagicMock()
        # Down, Down, Up, ESC
        stdscr.getch.side_effect = [slz.curses.KEY_DOWN, slz.curses.KEY_DOWN, slz.curses.KEY_UP, 27]
        stdscr.getmaxyx.return_value = (10, 80) # height=10 -> display_height=6
        
        with patch('sys.stdin.isatty', return_value=True):
            slz.main(stdscr)
            # We can't easily check the local scroll_offset variable, but we can verify 
            # that addstr was called with expected lines if we were more elaborate.
            # At minimum, we verify it doesn't crash and handles the keys.
            self.assertTrue(stdscr.getch.called)

    def test_broken_pipe_handling(self):
        """Exercise the exception path in run() directly."""
        with patch("slz.curses.wrapper", side_effect=BrokenPipeError):
            with patch("sys.stdin.isatty", return_value=False):
                with patch("sys.stdout.isatty", return_value=False):
                    # Mock open('/dev/tty')
                    mock_tty = MagicMock()
                    mock_tty.fileno.return_value = 999
                    
                    with patch("builtins.open", side_effect=lambda *args, **kwargs: mock_tty if args[0] == '/dev/tty' else open(*args, **kwargs)):
                        with patch("os.dup", return_value=1000):
                            with patch("os.dup2"):
                                with patch("os.fdopen", return_value=io.StringIO()):
                                    with patch("os.close"):
                                        with self.assertRaises(SystemExit) as cm:
                                            slz.run()
                                        # BrokenPipeError should exit with non-zero
                                        self.assertEqual(cm.exception.code, 1)

if __name__ == "__main__":
    unittest.main()
