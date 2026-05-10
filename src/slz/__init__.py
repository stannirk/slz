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

def read_stdin(q: queue.Queue, max_lines: int, stream: Any) -> None:
    """Background thread function to read a stream into a queue."""
    MAX_LINE_LENGTH = 4096 # Safety limit for single line length
    try:
        for i, line in enumerate(stream):
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

def parse_user_input(user_input: str) -> Tuple[List[str], Optional[str], Optional[int]]:
    """Parses user input into tokens, identifies custom separator, and head count."""
    try:
        parts = shlex.split(user_input)
    except ValueError:
        parts = user_input.split()
    
    sep = None
    head_skip = None
    clean_parts = []
    for part in parts:
        if part.startswith('sep:'):
            val = part[4:]
            if val: sep = val
        elif part.startswith('head:'):
            try:
                head_skip = int(part[5:])
            except (ValueError, IndexError):
                pass
        else:
            clean_parts.append(part)
    return clean_parts, sep, head_skip

def detect_col_before_filter_warning(user_input: str) -> Optional[str]:
    """
    Detects if a text filter token appears after a `col:` token.
    If so, returns a warning message.
    """
    parts, _, _ = parse_user_input(user_input)
    col_seen = False
    for part in parts:
        is_col = part.startswith('col:')
        is_regex = part.startswith('r:')
        is_sep = part.startswith('sep:')
        is_head = part.startswith('head:')
        is_text = not is_col and not is_regex and not is_sep and not is_head

        if is_col:
            col_seen = True
        
        if col_seen and is_text:
            return "⚠ Text after col: acts on extracted data. Reorder for global filtering."
            
    return None

def generate_command(user_input: str) -> str:
    """Translates user input into a bash pipe sequence, preserving order."""
    if not user_input.strip():
        return ""
    
    parts, sep, head_skip = parse_user_input(user_input)
    
    commands = []
    if head_skip and head_skip > 0:
        commands.append(f"sed '1,{head_skip}d'")

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
    
    parts, sep, head_skip = parse_user_input(user_input)
    
    if head_skip and head_skip > 0:
        filtered = lines[head_skip:]
    else:
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

def main(stdscr: Any, data_stream: Any = None, initial_filter: str = "") -> Tuple[Optional[str], List[str]]:
    # Setup curses with compatibility checks
    curses.curs_set(1)
    stdscr.timeout(100)
    stdscr.keypad(True)
    
    has_colors = curses.has_colors()
    if has_colors:
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_CYAN, -1)   # Header
        curses.init_pair(2, curses.COLOR_YELLOW, -1) # Generated command
        curses.init_pair(3, curses.COLOR_GREEN, -1)  # Filter text
        curses.init_pair(4, curses.COLOR_MAGENTA, -1) # Highlighted column
        curses.init_pair(5, curses.COLOR_WHITE, curses.COLOR_BLUE) # Selected line
    
    MAX_LINES = 10000
    input_lines: List[str] = []
    input_queue: queue.Queue = queue.Queue()
    is_streaming = False

    if data_stream is not None or not sys.stdin.isatty():
        is_streaming = True
        stream_to_read = data_stream if data_stream is not None else sys.stdin
        t = threading.Thread(target=read_stdin, args=(input_queue, MAX_LINES, stream_to_read), daemon=True)
        t.start()
    elif sys.stdin.isatty():
        input_lines = ["No input detected. Pipe something into slz!", "Example: ps aux | slz"]

    current_input = initial_filter
    scroll_offset = 0
    selected_indices = set() # Changed to indices
    header_line = None
    
    # Clear any pending input from the buffer (prevents garbage on startup)
    try:
        curses.flushinp()
    except curses.error:
        pass
    
    while True:
        # Limit processing to 500 lines per frame to keep UI responsive
        lines_processed = 0
        while not input_queue.empty() and lines_processed < 500:
            lines_processed += 1
            line = input_queue.get()
            if line is not None:
                if header_line is None and not input_lines:
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
        
        if height < 5 or width < 20:
            try: stdscr.addstr(0, 0, "Terminal too small")
            except curses.error: pass
            stdscr.refresh()
            if stdscr.getch() == 27: break
            continue

        # Draw main header
        header_attr = curses.color_pair(1) | curses.A_REVERSE if has_colors else curses.A_REVERSE
        stdscr.attron(header_attr)
        try:
            status = "STRE" if is_streaming else "IDLE"
            sel_text = f" [SEL:{len(selected_indices)}]" if selected_indices else ""
            header_text = f" SLZ | {status}{sel_text} | Tab:Toggle, Ctrl+Y:Copy, Enter:Apply ".ljust(width)
            stdscr.addstr(0, 0, header_text[:width])
        except curses.error: pass
        stdscr.attroff(header_attr)
        
        # Determine layout based on warning
        warning_message = detect_col_before_filter_warning(current_input)
        
        # Draw pinned header
        y_offset = 1
        if header_line:
            try:
                stdscr.attron(curses.A_BOLD | curses.A_UNDERLINE)
                stdscr.addstr(1, 0, header_line[:width-1].ljust(width-1))
                stdscr.attroff(curses.A_BOLD | curses.A_UNDERLINE)
                y_offset = 2
            except curses.error: pass

        # Filter and track indices
        parts, sep, head_skip = parse_user_input(current_input)
        
        if head_skip and head_skip > 0:
            indexed_lines = list(enumerate(input_lines))[head_skip:]
        else:
            indexed_lines = list(enumerate(input_lines))
        
        # Apply filters to indexed_lines
        filtered_indexed = indexed_lines
        for part in parts:
            if part.startswith('col:'):
                # We don't filter indices here, just content for the next grep-like step
                # But col: extraction actually changes the content.
                # For preview, we'll just keep the original content but highlight it.
                pass
            elif part.startswith('r:'):
                pattern = part[2:]
                if pattern:
                    try:
                        regex = re.compile(pattern, re.IGNORECASE)
                        filtered_indexed = [item for item in filtered_indexed if regex.search(item[1])]
                    except re.error: pass
            else:
                filtered_indexed = [item for item in filtered_indexed if part.lower() in item[1].lower()]

        num_preview = len(filtered_indexed)
        footer_height = 3 if warning_message else 2
        display_height = height - y_offset - footer_height
        
        scroll_offset = max(0, min(scroll_offset, num_preview - display_height))
        
        # Highlight logic
        highlight_col = -1
        for part in parts:
            if part.startswith('col:'):
                try:
                    val = part[4:]
                    if '-' not in val and ',' not in val:
                        highlight_col = int(val) - 1
                except ValueError: pass

        visible_items = filtered_indexed[scroll_offset : scroll_offset + display_height]
        for i, (orig_idx, line) in enumerate(visible_items):
            try:
                draw_y = i + y_offset
                is_selected = orig_idx in selected_indices
                line_attr = curses.color_pair(5) if is_selected and has_colors else curses.A_NORMAL
                
                # Draw base line
                stdscr.addstr(draw_y, 0, line[:width-1].ljust(width-1), line_attr)
                
                # Overlay highlight
                if highlight_col >= 0:
                    import re
                    matches = list(re.finditer(r'\S+', line)) if not sep else []
                    if sep:
                        # Find start/end for sep
                        start = 0
                        s_parts = line.split(sep)
                        if highlight_col < len(s_parts):
                            for j in range(highlight_col):
                                start += len(s_parts[j]) + len(sep)
                            end = start + len(s_parts[highlight_col])
                            token = s_parts[highlight_col]
                            if start < width - 1:
                                stdscr.attron(curses.color_pair(4) | curses.A_BOLD)
                                stdscr.addstr(draw_y, start, token[:width-1-start])
                                stdscr.attroff(curses.color_pair(4) | curses.A_BOLD)
                    elif 0 <= highlight_col < len(matches):
                        m = matches[highlight_col]
                        start, end = m.start(), m.end()
                        if start < width - 1:
                            stdscr.attron(curses.color_pair(4) | curses.A_BOLD)
                            stdscr.addstr(draw_y, start, line[start:min(end, width-1)])
                            stdscr.attroff(curses.color_pair(4) | curses.A_BOLD)
            except curses.error: pass
        
        # Draw footer
        footer_y = height - footer_height
        if warning_message:
            try:
                warning_attr = curses.color_pair(2) | curses.A_BOLD if has_colors else curses.A_BOLD
                stdscr.attron(warning_attr)
                stdscr.addstr(footer_y, 0, warning_message[:width-1])
                stdscr.attroff(warning_attr)
                footer_y += 1
            except curses.error:
                pass

        cmd = generate_command(current_input)
        cmd_attr = curses.color_pair(2) | curses.A_BOLD if has_colors else curses.A_BOLD
        try:
            footer_text = f"Cmd [{scroll_offset + 1}-{min(scroll_offset + display_height, num_preview)}/{num_preview}]: "
            stdscr.addstr(footer_y, 0, footer_text)
            stdscr.addstr(footer_y, len(footer_text), cmd[:width-len(footer_text)], cmd_attr)
            
            stdscr.addstr(footer_y + 1, 0, "Filter: ")
            filter_attr = curses.color_pair(3) if has_colors else curses.A_NORMAL
            stdscr.attron(filter_attr)
            display_filter = f"{current_input}_"
            stdscr.addstr(footer_y + 1, 8, display_filter[:width-9])
            stdscr.attroff(filter_attr)
        except curses.error: pass
        
        stdscr.refresh()
        
        try: ch = stdscr.getch()
        except KeyboardInterrupt: return None, input_lines

        if ch == -1: continue
        elif ch == curses.KEY_RESIZE:
            curses.update_lines_cols()
            continue
        elif ch in (10, 13, curses.KEY_ENTER):
            # Combine header with output
            final_output = []
            if header_line:
                final_output.append(header_line)
            
            if selected_indices:
                # Output only selected lines (ordered by original appearance)
                for idx in sorted(selected_indices):
                    final_output.append(input_lines[idx])
            else:
                # Output all current filtered lines
                for idx, content in filtered_indexed:
                    final_output.append(content)
            
            return current_input, final_output
        elif ch == 27: return None, input_lines
        elif ch == 9: # Tab
            if visible_items:
                orig_idx, _ = visible_items[0]
                if orig_idx in selected_indices: selected_indices.remove(orig_idx)
                else: selected_indices.add(orig_idx)
        elif ch == 25: # Ctrl+Y
            if cmd: copy_to_clipboard(f"| {cmd}")
        elif ch == curses.KEY_UP: scroll_offset -= 1
        elif ch == curses.KEY_DOWN: scroll_offset += 1
        elif ch == curses.KEY_PPAGE: scroll_offset -= display_height
        elif ch == curses.KEY_NPAGE: scroll_offset += display_height
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
    
    parts, sep, head_skip = parse_user_input(user_input)
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
    parser.add_argument("-n", "--non-interactive", action="store_true", help="Run without TUI (requires filter arguments)")
    parser.add_argument("--explain", action="store_true", help="Print a plain-English explanation of the generated command")
    parser.add_argument("--version", action="version", version="%(prog)s 0.2.0")
    args, unknown = parser.parse_known_args()

    if not sys.stdin.isatty():
        initial_filter = " ".join(unknown)
        
        # Determine if we should run in non-interactive mode
        is_non_interactive = args.non_interactive
        
        # Attempt to open /dev/tty for interactive mode
        tty = None
        if not is_non_interactive:
            try:
                tty = open('/dev/tty', 'r+')
            except OSError:
                if initial_filter:
                    is_non_interactive = True
                else:
                    print("Error: Terminal required for interactive mode and no filter provided.", file=sys.stderr)
                    sys.exit(1)

        if is_non_interactive:
            input_lines = [line.rstrip() for line in sys.stdin]
            if not initial_filter:
                # If no filter provided in non-interactive mode, just output everything
                for line in input_lines:
                    print(line)
                return

            if args.filter:
                results = filter_lines(input_lines, initial_filter)
                for line in results:
                    print(line)
            else:
                cmd = generate_command(initial_filter)
                if cmd:
                    print(cmd)
            return

        # Interactive mode with piped input
        # Save original pipes and redirect to TTY
        orig_stdin_fd = os.dup(0)
        orig_stdout_fd = os.dup(1)
        
        try:
            os.dup2(tty.fileno(), 0)
            os.dup2(tty.fileno(), 1)
            
            # Create a new stream for the data from the original pipe
            data_stream = os.fdopen(orig_stdin_fd, 'r')
            
            # Update Python's sys.stdin/stdout to the TTY for curses
            sys.stdin = os.fdopen(0, 'r')
            sys.stdout = os.fdopen(1, 'w')

            try:
                final_input, final_lines = curses.wrapper(main, data_stream, initial_filter)
            except Exception as e:
                # Restore original stdout to print the error
                os.dup2(orig_stdout_fd, 1)
                sys.stdout = os.fdopen(1, 'w')
                print(f"\nError: Terminal does not support TUI mode. ({str(e)})", file=sys.stderr)
                sys.exit(1)

            # Restore original stdout to print the final result
            os.dup2(orig_stdout_fd, 1)
            sys.stdout = os.fdopen(1, 'w')
            
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
        finally:
            if tty: tty.close()
            # Restore original descriptors
            os.dup2(orig_stdin_fd, 0)
            os.dup2(orig_stdout_fd, 1)
            os.close(orig_stdin_fd)
            os.close(orig_stdout_fd)
            
            # Update Python objects back to restored descriptors
            sys.stdin = os.fdopen(0, 'r')
            sys.stdout = os.fdopen(1, 'w')
    else:
        if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help"):
            parser.print_help()
        else:
            print("Usage: <command> | slz")
        sys.exit(1)



if __name__ == "__main__":
    run()

