#!/usr/bin/env python3
import sys

# Version Check: Ensure Python 3.6+ for f-strings and curses features
if sys.version_info < (3, 6):
    sys.exit("Error: SLZ requires Python 3.6 or higher.")

import curses
import re
import locale
import platform

# Ensure Unicode support for different locales
try:
    locale.setlocale(locale.LC_ALL, '')
except locale.Error:
    pass

import shlex
import threading
import queue
from typing import List, Optional, Any

def read_stdin(q: queue.Queue, max_lines: int) -> None:
    """Background thread function to read stdin into a queue."""
    MAX_LINE_LENGTH = 4096 # Safety limit for single line length
    try:
        for i, line in enumerate(sys.stdin):
            if i >= max_lines:
                q.put(f"... [Truncated after {max_lines} lines] ...")
                break
            
            clean_line = line.rstrip()
            if len(clean_line) > MAX_LINE_LENGTH:
                clean_line = clean_line[:MAX_LINE_LENGTH] + " [Line Truncated]"
            q.put(clean_line)
    except (UnicodeDecodeError, EOFError):
        q.put("Error: Could not decode input as UTF-8.")
    finally:
        q.put(None) # Sentinel for EOF

def generate_command(user_input: str) -> str:
    """Translates user input into a bash pipe sequence, preserving order."""
    if not user_input.strip():
        return ""
    
    try:
        parts = shlex.split(user_input)
    except ValueError:
        parts = user_input.split()
    
    commands = []
    for part in parts:
        if part.startswith('col:'):
            try:
                col_num = int(part.split(':')[1])
                commands.append(f"awk '{{print ${col_num}}}'")
            except (IndexError, ValueError):
                pass
        else:
            # Escape single quotes for shell safety: ' becomes '\''
            safe_part = part.replace("'", "'\\''")
            commands.append(f"grep -i '{safe_part}'")
    
    return " | ".join(commands)

def filter_lines(lines: List[str], user_input: str) -> List[str]:
    """Filters lines based on current user input for preview."""
    if not user_input.strip():
        return lines
    
    try:
        parts = shlex.split(user_input)
    except ValueError:
        parts = user_input.split()
    
    filtered = lines
    
    for part in parts:
        if part.startswith('col:'):
            try:
                col_idx = int(part.split(':')[1]) - 1
                new_filtered = []
                for line in filtered:
                    cols = line.split()
                    if 0 <= col_idx < len(cols):
                        new_filtered.append(cols[col_idx])
                filtered = new_filtered
            except (IndexError, ValueError):
                pass
        else:
            filtered = [line for line in filtered if part.lower() in line.lower()]
            
    return filtered

def main(stdscr: Any) -> Optional[str]:
    # Setup curses with compatibility checks
    curses.curs_set(1)
    stdscr.timeout(100) # Non-blocking input (100ms)
    stdscr.keypad(True) # Handle arrow keys and special keys
    
    # Initialize colors only if supported
    has_colors = curses.has_colors()
    if has_colors:
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_CYAN, -1)  # Header
        curses.init_pair(2, curses.COLOR_YELLOW, -1) # Generated command
        curses.init_pair(3, curses.COLOR_GREEN, -1)  # Filter text
    
    # Setup background stdin reading
    MAX_LINES = 10000
    input_lines: List[str] = []
    input_queue: queue.Queue = queue.Queue()
    is_streaming = False

    if sys.stdin.isatty():
        input_lines = ["No input detected. Pipe something into slz!", "Example: ps aux | slz"]
    else:
        is_streaming = True
        t = threading.Thread(target=read_stdin, args=(input_queue, MAX_LINES), daemon=True)
        t.start()

    current_input = ""
    scroll_offset = 0
    
    while True:
        # Drain the input queue
        while not input_queue.empty():
            line = input_queue.get()
            if line is not None:
                input_lines.append(line)
            else:
                is_streaming = False

        stdscr.clear()
        height, width = stdscr.getmaxyx()
        
        # Ensure we have a minimum screen size
        if height < 5 or width < 20:
            try:
                stdscr.addstr(0, 0, "Terminal too small")
            except curses.error:
                pass
            stdscr.refresh()
            ch = stdscr.getch()
            if ch == 27: break
            continue

        # Draw header
        header_attr = curses.color_pair(1) | curses.A_REVERSE if has_colors else curses.A_REVERSE
        stdscr.attron(header_attr)
        try:
            status = "Streaming..." if is_streaming else "Ready"
            header_text = f" SLZ Translator | {status} | ESC: Cancel ".ljust(width)
            stdscr.addstr(0, 0, header_text)
        except curses.error:
            pass
        stdscr.attroff(header_attr)
        
        # Draw preview
        preview_lines = filter_lines(input_lines, current_input)
        num_preview = len(preview_lines)
        display_height = height - 4
        
        # Clamp scroll offset
        scroll_offset = max(0, min(scroll_offset, num_preview - display_height))
        
        visible_lines = preview_lines[scroll_offset : scroll_offset + display_height]
        for i, line in enumerate(visible_lines):
            try:
                # Truncate line to fit screen
                display_line = line[:width-1]
                stdscr.addstr(i + 1, 0, display_line)
            except curses.error:
                pass
        
        # Draw footer
        footer_y = height - 2
        cmd = generate_command(current_input)
        
        cmd_attr = curses.color_pair(2) | curses.A_BOLD if has_colors else curses.A_BOLD
        try:
            stdscr.addstr(footer_y, 0, f"Generated [{scroll_offset + 1}-{min(scroll_offset + display_height, num_preview)}/{num_preview}]: ")
            stdscr.attron(cmd_attr)
            stdscr.addstr(cmd[:width-25])
            stdscr.attroff(cmd_attr)
            
            stdscr.addstr(footer_y + 1, 0, "Filter: ")
            filter_attr = curses.color_pair(3) if has_colors else curses.A_NORMAL
            stdscr.attron(filter_attr)
            stdscr.addstr(current_input[:width-9])
            stdscr.attroff(filter_attr)
        except curses.error:
            pass
        
        stdscr.refresh()
        
        # Handle input
        try:
            ch = stdscr.getch()
        except KeyboardInterrupt:
            return None

        if ch == -1: # Timeout, no key pressed
            continue
        elif ch == curses.KEY_RESIZE:
            curses.update_lines_cols()
            continue
        elif ch in (10, 13, curses.KEY_ENTER): # Enter
            break
        elif ch == 27: # ESC
            return None
        elif ch == curses.KEY_UP:
            scroll_offset -= 1
        elif ch == curses.KEY_DOWN:
            scroll_offset += 1
        elif ch == curses.KEY_PPAGE: # Page Up
            scroll_offset -= display_height
        elif ch == curses.KEY_NPAGE: # Page Down
            scroll_offset += display_height
        elif ch in (curses.KEY_BACKSPACE, 127, 8):
            current_input = current_input[:-1]
            scroll_offset = 0
        elif 32 <= ch <= 126:
            current_input += chr(ch)
            scroll_offset = 0

    return current_input

def run() -> None:
    # Reduce ESC key delay in curses (default is often 1000ms)
    os.environ.setdefault('ESCDELAY', '25')
    
    if not sys.stdin.isatty() or len(sys.argv) > 1:
        try:
            final_input = curses.wrapper(main)
            if final_input is not None:
                cmd = generate_command(final_input)
                if cmd:
                    # Smart Output: If stdout is a TTY, be pretty. If not, be silent/raw.
                    if sys.stdout.isatty():
                        print(f"\n# Suggested Pipe:\n| {cmd}")
                    else:
                        # Print only the command for easy capture: CMD=$(ps aux | slz)
                        print(cmd)
        except Exception as e:
            # Fallback for systems where curses might fail
            if sys.stdout.isatty():
                print(f"\nError: Terminal does not support TUI mode. ({str(e)})", file=sys.stderr)
            else:
                sys.exit(1)
    else:
        print("Usage: <command> | slz")
        sys.exit(1)

if __name__ == "__main__":
    run()

