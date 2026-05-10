# SLZ Translator 🥋

[![CI](https://github.com/stannirk/slz/actions/workflows/ci.yml/badge.svg)](https://github.com/stannirk/slz/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/slz.svg)](https://badge.fury.io/py/slz)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

The interactive command-line tool that translates your visual filtering into powerful `awk` and `grep` commands.

## Why SLZ?
Experienced developers often find themselves writing repetitive `grep | awk | sed` chains just to extract a single piece of information from a messy command output. `slz` eliminates the mental overhead of remembering exact flags and column numbers by providing an interactive TUI to do it for you.

**Read our [Project Philosophy (MISSION.md)](./MISSION.md) and see more [Usage Examples (EXAMPLES.md)](./EXAMPLES.md).**

## Quick Start Examples
Try these common patterns to see SLZ in action:

```bash
# Find and kill a process by name (uses --filter to output values)
kill -9 $(ps aux | slz -f)
# Interactive filter: "chrome col:2"

# Get the ID of a specific Docker container
docker inspect $(docker ps | slz -f)
# Interactive filter: "nginx col:1"

# Extract timestamps for specific log errors
cat server.log | slz -f
# Interactive filter: "timeout 504 col:2"

# Checkout a branch interactively
git checkout $(git branch | slz -f)
# Interactive filter: "feature/api col:1"
```

## Features
- **Interactive Filtering**: Type as you go to see live results.
- **Smart Column Extraction**: Use `col:N` to extract the Nth column. Supports multiple columns (`col:1,3`) and ranges (`col:1-4`).
- **Regex Support**: Use `r:pattern` for powerful regular expression filtering (case-insensitive).
- **Custom Delimiters**: Use `sep:X` (e.g., `sep:,`) to handle CSV or other delimited data.
- **Command Generation**: Generates the exact `grep` and `awk` commands for you to copy or re-run.
- **Output Mode**: Use `--filter` (or `-f`) to output the filtered results directly instead of the command recipe.
- **Virtual Scrolling**: Navigate through thousands of lines of output using arrow keys.
- **Streaming Input**: UI stays responsive while reading from slow piped commands.
- **Zero Dependencies**: Pure Python using the standard `curses` library.

## Installation

### 1. Install the package
You can install `slz` directly via pip:

```bash
pip install .
```

Or for a single-user installation:

```bash
pip install --user .
```

### 2. Add to your Zsh configuration
Add the following to your `~/.zshrc` to bind SLZ to `Ctrl+P`. This version stages the command in your buffer without executing it immediately, allowing you to review it first:

```zsh
# SLZ Widget (Stages command in buffer)
slz-widget() {
  if [[ -n "$LBUFFER" ]]; then
    LBUFFER="$LBUFFER | slz"
  fi
}
zle -N slz-widget
bindkey '^P' slz-widget
```

### 3. Add to your Fish configuration
Add the following to your `~/.config/fish/config.fish` to bind SLZ to `Ctrl+P`:

```fish
# SLZ Widget (Fish shell)
function slz_widget
    if test -n (commandline)
        commandline -a " | slz"
    end
end
bind \cp slz_widget
```

## Usage
1. Type a command like `ps aux`.
2. Press `Ctrl+P`.
3. In the interface, type `chrome` to filter for Chrome processes.
4. Type ` col:2` to extract the PID column.
5. Use **Arrow Keys** or **Page Up/Down** to scroll the results.
6. Hit Enter. The tool will exit and display:
   `# Suggested Pipe: | grep -i 'chrome' | awk '{print $2}'`

## Compatibility
- **Linux/macOS**: Supported natively (requires Python 3.6+).
- **Windows**: Supported via WSL or by installing the `windows-curses` package (`pip install windows-curses`) in PowerShell/CMD.
- **Terminals**: Works in all standard terminal emulators (iTerm2, Terminal.app, xterm, Windows Terminal, GNOME Terminal). 
  *Note: May not work inside IDE-integrated terminals (like VS Code's debug console) if they do not provide full TTY support.*

## Development & Testing
To run the full test suite:
```bash
python3 -m unittest discover tests
```
