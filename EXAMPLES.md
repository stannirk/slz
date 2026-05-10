# SLZ Usage Examples 🌊

Here are some of the most common ways to use SLZ to turn messy output into clean, actionable commands.

### 1. Process Management (The "Smart Kill")
Find a specific process ID without squinting at column headers.
*   **Input:** `ps aux | slz`
*   **Action:** Type `chrome col:2`
*   **Result:** Outputs the PID of the Chrome process.
*   **Pro-Tip:** Chain it with xargs: `kill -9 $(ps aux | slz)`

### 2. Log Surgery (The "Error Finder")
Extract just the timestamps or error codes from a dense log file.
*   **Input:** `tail -n 1000 /var/log/syslog | slz`
*   **Action:** Type `error 500 col:1`
*   **Result:** Extracts the timestamps (column 1) for all lines containing both "error" and "500".

### 3. Git Operations (The "Branch Jumper")
Switch branches when you have dozens of features in progress.
*   **Input:** `git branch | slz`
*   **Action:** Type `feature leak col:1`
*   **Result:** Isolates the branch name.
*   **One-Liner:** `git checkout $(git branch | slz)`

### 4. Docker Janitor (The "ID Grabber")
Get the ID of that Postgres container you just started.
*   **Input:** `docker ps | slz`
*   **Action:** Type `postgres col:1`
*   **Result:** Returns the short Container ID.
*   **Automation:** `docker stop $(docker ps | slz)`

### 5. Network Audit (The "IP Sorter")
Find who is connecting to your server from a `netstat` or `ss` output.
*   **Input:** `ss -tunp | slz`
*   **Action:** Type `ESTAB col:5`
*   **Result:** Extracts the remote address and port.

### 6. Kubernetes Exploration (The "Pod Sniper")
Find the name of a specific pod in a crowded namespace.
*   **Input:** `kubectl get pods | slz`
*   **Action:** Type `api-server running col:1`
*   **Result:** Returns just the pod name for your next `kubectl logs` command.

---

## The "SLZ Loop" Workflow
1.  **Pipe it:** `<command> | slz`
2.  **Filter it:** Type words to narrow down results.
3.  **Extract it:** Type `col:N` to pick your column.
4.  **Confirm it:** Watch the preview to make sure you have the "gold."
5.  **Use it:** Hit Enter and copy the suggested command or use the output in a subshell `$()`.
