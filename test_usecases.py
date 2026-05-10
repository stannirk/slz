import sys
import os

# Add src to python path to import slz
sys.path.insert(0, os.path.abspath('src'))
from slz import filter_lines, generate_command

usecases = [
    {
        "name": "Process Management",
        "input_lines": [
            "USER   PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND",
            "root     1  0.0  0.1 168392 11216 ?        Ss   Apr10   0:06 /sbin/init",
            "user   1234  5.0  2.3 456789 23456 ?        Sl   10:00   1:23 /opt/google/chrome/chrome",
            "user   1235  0.1  1.0 234567 12345 ?        S    10:00   0:05 /opt/google/chrome/chrome --type=renderer"
        ],
        "user_input": "chrome col:2"
    },
    {
        "name": "Log Surgery",
        "input_lines": [
            "2023-10-27T10:00:00Z INFO User login successful",
            "2023-10-27T10:05:00Z ERROR 500 Internal Server Error: Database timeout",
            "2023-10-27T10:06:00Z WARN High latency detected",
            "2023-10-27T10:10:00Z ERROR 500 Internal Server Error: Connection refused"
        ],
        "user_input": "error 500 col:1"
    },
    {
        "name": "Git Operations",
        "input_lines": [
            "* main",
            "  feature/memory-leak-fix",
            "  bugfix/login-error"
        ],
        "user_input": "feature leak col:1"
    },
    {
        "name": "Docker Janitor",
        "input_lines": [
            "CONTAINER ID   IMAGE         COMMAND                  CREATED       STATUS       PORTS      NAMES",
            "a1b2c3d4e5f6   postgres:13   \"docker-entrypoint.s…\"   2 hours ago   Up 2 hours   5432/tcp   my-postgres",
            "1234567890ab   nginx:latest  \"/docker-entrypoint.…\"   3 hours ago   Up 3 hours   80/tcp     my-nginx"
        ],
        "user_input": "postgres col:1"
    }
]

for uc in usecases:
    print(f"--- {uc['name']} ---")
    print(f"User Input: '{uc['user_input']}'")
    cmd = generate_command(uc['user_input'])
    print(f"Generated Command: {cmd}")
    filtered = filter_lines(uc['input_lines'], uc['user_input'])
    print(f"Filtered Output: {filtered}")
    print()
