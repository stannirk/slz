#!/usr/bin/env python3
import sys

# Version Check: Ensure Python 3.6+ for f-strings and curses features
if sys.version_info < (3, 6):
    sys.exit("Error: SLZ requires Python 3.6 or higher.")

import curses
import os
import re
import locale
import platform
import argparse

# Ensure Unicode support for different locales
try:
    locale.setlocale(locale.LC_ALL, '')
except locale.Error:
    pass

import shlex
import threading
import queue
from typing import List, Optional, Any, Tuple

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

def parse_user_input(user_input: str) -> Tuple[List[str], Optional[str]]:
    """Parses user input into tokens and identifies the custom separator if any."""
    try:
        parts = shlex.split(user_input)
    except ValueError:
        parts = user_input.split()
    
    sep = None
    clean_parts = []
    for part in parts:
        if part.startswith('sep:'):
            val = part[4:]
            if val: sep = val
        else:
            clean_parts.append(part)
    return clean_parts, sep

def generate_command(user_input: str) -> str:
    """Translates user input into a bash pipe sequence, preserving order."""
    if not user_input.strip():
        return ""
    
    parts, sep = parse_user_input(user_input)
    
    commands = []
    fs = f"-F'{sep}' " if sep else ""
    
    for part in parts:
        if part.startswith('col:'):
            col_spec = part[4:]
            if not col_spec: continue
            
            try:
                if ',' in col_spec:
                    cols = [f"${int(c)}" for c in col_spec.split(',') if int(c) > 0]
                    if cols:
                        commands.append(f"awk {fs}'{{print {', '.join(cols)}}}'")
                elif '-' in col_spec:
                    start, end = map(int, col_spec.split('-'))
                    if start > 0 and end >= start:
                        cols = [f"${i}" for i in range(start, end + 1)]
                        commands.append(f"awk {fs}'{{print {', '.join(cols)}}}'")
                else:
                    col_num = int(col_spec)
                    if col_num > 0:
                        commands.append(f"awk {fs}'{{print ${col_num}}}'")
            except (ValueError, IndexError):
                pass
        elif part.startswith('r:'):
            pattern = part[2:]
            if pattern:
                safe_pattern = pattern.replace("'", "'\\''")
                commands.append(f"grep -E -i '{safe_pattern}'")
        else:
            # Escape single quotes for shell safety: ' becomes '\''
            safe_part = part.replace("'", "'\\''")
            commands.append(f"grep -i '{safe_part}'")
    
    return " | ".join(commands)

_filter_cache = {}

def filter_lines(lines: List[str], user_input: str) -> List[str]:
    """Filters lines based on current user input for preview. Uses caching for performance."""
    if not user_input.strip():
        return lines
    
    # Simple cache key: (id(lines), user_input)
    # id(lines) is safe because input_lines is only appended to, never replaced in the TUI loop.
    cache_key = (id(lines), len(lines), user_input)
    if cache_key in _filter_cache:
        return _filter_cache[cache_key]
    
    parts, sep = parse_user_input(user_input)
    filtered = lines
    
    for part in parts:
        if part.startswith('col:'):
            col_spec = part[4:]
            if not col_spec: continue
            
            try:
                new_filtered = []
                target_cols = []
                if ',' in col_spec:
                    target_cols = [int(c) - 1 for c in col_spec.split(',') if int(c) > 0]
                elif '-' in col_spec:
                    start, end = map(int, col_spec.split('-'))
                    if start > 0 and end >= start:
                        target_cols = list(range(start - 1, end))
                else:
                    target_cols = [int(col_spec) - 1] if int(col_spec) > 0 else []

                if not target_cols: continue

                for line in filtered:
                    cols = line.split(sep) if sep else line.split()
                    extracted = [cols[i] for i in target_cols if 0 <= i < len(cols)]
                    if extracted:
                        new_filtered.append(" ".join(extracted))
                filtered = new_filtered
            except (IndexError, ValueError):
                pass
        elif part.startswith('r:'):
            pattern = part[2:]
            if pattern:
                try:
                    regex = re.compile(pattern, re.IGNORECASE)
                    filtered = [line for line in filtered if regex.search(line)]
                except re.error:
                    pass
        else:
            filtered = [line for line in filtered if part.lower() in line.lower()]
            
    _filter_cache[cache_key] = filtered
    # Optional: Keep cache size reasonable
    if len(_filter_cache) > 100:
        # Simple LRU-ish: clear everything if too big
        _filter_cache.clear()
        _filter_cache[cache_key] = filtered

    return filtered

def main(stdscr: Any, initial_lines: List[str] = None) -> Tuple[Optional[str], List[str]]:
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
        curses.init_pair(4, curses.COLOR_MAGENTA, -1) # Highlighted column
        curses.init_pair(5, curses.COLOR_WHITE, curses.COLOR_BLUE) # Selected line
    
    # Setup background stdin reading
    MAX_LINES = 10000
    input_lines: List[str] = initial_lines if initial_lines is not None else []
    input_queue: queue.Queue = queue.Queue()
    is_streaming = False

    if not input_lines:
        if sys.stdin.isatty():
            input_lines = ["No input detected. Pipe something into slz!", "Example: ps aux | slz"]
        else:
            is_streaming = True
            t = threading.Thread(target=read_stdin, args=(input_queue, MAX_LINES), daemon=True)
            t.start()

    current_input = ""
    scroll_offset = 0
    selected_lines = set()
    header_line = None
    
    while True:
        # Drain the input queue
        while not input_queue.empty():
            line = input_queue.get()
            if line is not None:
                # Simple header detection heuristic
                if header_line is None and len(input_lines) == 0:
                    if line.isupper() or (len(line.split()) > 3 and all(t[0].isupper() for t in line.split() if t.isalpha())):
                        header_line = line
                    else:
                        input_lines.append(line)
                else:
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
            sel_text = f" [{len(selected_lines)} selected]" if selected_lines else ""
            header_text = f" SLZ Translator | {status}{sel_text} | col:N, Tab:Sel, Ctrl+Y:Copy | ESC: Cancel ".ljust(width)
            stdscr.addstr(0, 0, header_text)
        except curses.error:
            pass
        stdscr.attroff(header_attr)
        
        # Pinned Header row
        y_offset = 1
        if header_line:
            try:
                stdscr.attron(curses.A_BOLD | curses.A_UNDERLINE)
                stdscr.addstr(1, 0, header_line[:width-1].ljust(width-1))
                stdscr.attroff(curses.A_BOLD | curses.A_UNDERLINE)
                y_offset = 2
            except curses.error:
                pass

        # Draw preview
        preview_lines = filter_lines(input_lines, current_input)
        num_preview = len(preview_lines)
        display_height = height - y_offset - 3
        
        # Clamp scroll offset
        scroll_offset = max(0, min(scroll_offset, num_preview - display_height))
        
        # Determine highlighted column
        highlight_col = -1
        parts, sep = parse_user_input(current_input)
        for part in parts:
            if part.startswith('col:'):
                try:
                    val = part[4:]
                    if '-' not in val and ',' not in val:
                        highlight_col = int(val) - 1
                except ValueError:
                    pass

        visible_lines = preview_lines[scroll_offset : scroll_offset + display_height]
        for i, line in enumerate(visible_lines):
            try:
                draw_y = i + y_offset
                is_selected = line in selected_lines
                attr = curses.color_pair(5) if is_selected and has_colors else curses.A_NORMAL
                
                if highlight_col >= 0:
                    tokens = line.split(sep) if sep else line.split()
                    curr_x = 0
                    for t_idx, token in enumerate(tokens):
                        if t_idx == highlight_col:
                            stdscr.attron(curses.color_pair(4) | curses.A_BOLD)
                        stdscr.addstr(draw_y, curr_x, token)
                        if t_idx == highlight_col:
                            stdscr.attroff(curses.color_pair(4) | curses.A_BOLD)
                        curr_x += len(token) + 1
                        if curr_x >= width - 1: break
                else:
                    stdscr.addstr(draw_y, 0, line[:width-1], attr)
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
            return None, input_lines

        if ch == -1: # Timeout
            continue
        elif ch == curses.KEY_RESIZE:
            curses.update_lines_cols()
            continue
        elif ch in (10, 13, curses.KEY_ENTER): # Enter
            if selected_lines:
                return current_input, list(selected_lines)
            return current_input, input_lines
        elif ch == 27: # ESC
            return None, input_lines
        elif ch == 9: # TAB - Multi-select
            if visible_lines:
                # Toggle selection for the line at the top of visible area for now, 
                # or we could implement a cursor. Let's toggle the first visible one.
                line_to_toggle = visible_lines[0]
                if line_to_toggle in selected_lines:
                    selected_lines.remove(line_to_toggle)
                else:
                    selected_lines.add(line_to_toggle)
        elif ch == 25: # Ctrl+Y - Copy to clipboard
            if cmd:
                copy_to_clipboard(f"| {cmd}")
        elif ch == curses.KEY_UP:
            scroll_offset -= 1
        elif ch == curses.KEY_DOWN:
            scroll_offset += 1
        elif ch == curses.KEY_PPAGE:
            scroll_offset -= display_height
        elif ch == curses.KEY_NPAGE:
            scroll_offset += display_height
        elif ch in (curses.KEY_BACKSPACE, 127, 8):
            current_input = current_input[:-1]
            scroll_offset = 0
        elif 32 <= ch <= 126:
            current_input += chr(ch)
            scroll_offset = 0

    return None, input_lines

def generate_explanation(user_input: str) -> str:
    """Provides a plain-English explanation of the generated command."""
    if not user_input.strip():
        return "No filters applied."
    
    parts, sep = parse_user_input(user_input)
    explanations = []
    
    for part in parts:
        if part.startswith('col:'):
            col_spec = part[4:]
            try:
                if ',' in col_spec:
                    cols = col_spec.split(',')
                    explanations.append(f"awk (extract columns {', '.join(cols)})")
                elif '-' in col_spec:
                    start, end = col_spec.split('-')
                    explanations.append(f"awk (extract columns {start} through {end})")
                else:
                    explanations.append(f"awk (extract column {col_spec})")
            except ValueError:
                pass
        elif part.startswith('r:'):
            pattern = part[2:]
            explanations.append(f"grep (regex match '{pattern}', case-insensitive)")
        elif part.startswith('sep:'):
            pass # Handled by awk
        else:
            explanations.append(f"grep (substring match '{part}', case-insensitive)")
    
    if not explanations:
        return "No valid filters identified."
    
    result = "Steps:\n"
    for i, exp in enumerate(explanations, 1):
        result += f"  {i}. {exp}\n"
    return result

def copy_to_clipboard(text: str) -> bool:
    """Attempts to copy text to the system clipboard."""
    try:
        if platform.system() == "Darwin":
            subprocess.run(["pbcopy"], input=text.encode(), check=True)
        elif platform.system() == "Windows":
            subprocess.run(["clip.exe"], input=text.encode(), check=True)
        else:
            # Try xclip then xsel
            try:
                subprocess.run(["xclip", "-selection", "clipboard"], input=text.encode(), check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                subprocess.run(["xsel", "--clipboard", "--input"], input=text.encode(), check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

import subprocess

def run() -> None:
    # Reduce ESC key delay in curses (default is often 1000ms)
    os.environ.setdefault('ESCDELAY', '25')
    
    parser = argparse.ArgumentParser(description="SLZ: Interactive Pipe Translator")
    parser.add_argument("-f", "--filter", action="store_true", help="Output filtered results instead of the command recipe")
    parser.add_argument("--explain", action="store_true", help="Print a plain-English explanation of the generated command")
    parser.add_argument("--version", action="version", version="%(prog)s 0.2.0")
    args, unknown = parser.parse_known_args()

    if not sys.stdin.isatty():
        try:
            final_input, final_lines = curses.wrapper(main)
            if final_input is not None:
                if args.filter:
                    results = filter_lines(final_lines, final_input)
                    for line in results:
                        print(line)
                else:
                    cmd = generate_command(final_input)
                    if cmd:
                        if sys.stdout.isatty():
                            print(f"\n# Suggested Pipe:\n| {cmd}")
                            if args.explain:
                                print(f"\n# What this does:\n{generate_explanation(final_input)}")
                        else:
                            print(cmd)
        except Exception as e:
            if sys.stdout.isatty():
                print(f"\nError: Terminal does not support TUI mode. ({str(e)})", file=sys.stderr)
            else:
                sys.exit(1)
    else:
        if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help"):
            parser.print_help()
        else:
            print("Usage: <command> | slz")
        sys.exit(1)



if __name__ == "__main__":
    run()

