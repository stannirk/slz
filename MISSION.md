# The SLZ Philosophy: Why we built this 🌊

In a world full of powerful CLI tools like `fzf`, `peco`, and `grep`, you might wonder: **Why SLZ?**

Most interactive filters are built for **Selection**. SLZ is built for **Translation**.

## The Core Problems We Solve

### 1. The "fzf + awk" Friction
**The Problem:** In tools like `fzf`, you can find the line you want, but you can't *extract* the value you need. You're forced into a trial-and-error loop:
`ps aux | fzf | awk '{print $2}'` -> *Wrong column?* -> `Up-arrow` -> *Edit* -> `awk '{print $3}'` -> *Repeat.*

**The Sluice Solution:** SLZ integrates the filter and the extractor into one step. By using the `col:N` tag, you see the extracted values in real-time. If you guessed the wrong column, you see it instantly in the preview and fix it before hitting Enter.

### 2. The "Awk Syntax Barrier"
**The Problem:** `awk` is powerful, but its syntax is arcane. Beginners struggle with field variables (`$1`, `$2`), quoting hell (escaping single quotes inside shell scripts), and inconsistent versions across Linux and macOS.

**The Sluice Solution:** SLZ acts as a **Syntax Buffer**. You type in a human-friendly way (`col:2`), and SLZ handles the "backslash madness" and POSIX-compliant formatting for you.

### 3. The "Black Box" Automation Gap
**The Problem:** Fuzzy finders are great for one-off manual tasks, but they are "black boxes." When you're done, you don't have a re-usable command you can put into a bash script or a `.zshrc` alias.

**The Sluice Solution:** SLZ is a **Command Generator**. Its primary output is the actual `grep | awk` string. This allows you to experiment interactively and then copy-paste the perfect command directly into your automation scripts.

### 4. Literal Precision vs. Fuzzy Noise
**The Problem:** Fuzzy matching can sometimes be *too* aggressive, returning "noisy" results that have the right letters but the wrong meaning.

**The Sluice Solution:** SLZ uses **Literal Multi-Term Filtering**. If you type `ssh failed`, it behaves like `grep ssh | grep failed`. It's predictable, precise, and matches the mental model of most systems engineers.

---

## Our Identity
SLZ is a **Refinement Engine**. 

Like a miner’s sluice box, it is designed to take a messy flow of raw data and "wash away" the noise until only the valuable "gold"—the specific PID, IP address, or branch name—remains.

**Stop guessing your column numbers. Start sluicing.**

---

## Our Commitment to Simplicity

SLZ is a surgical tool, not a Swiss Army knife. We believe that a CLI tool’s value is measured by what it *doesn't* do as much as what it does. To prevent feature creep and preserve our 3-letter Unix identity, we apply **The Sluice Test** to every new proposal:

> **"Does this feature help the user visually refine a Shell Pipe, or does it try to be the destination for the data?"**

### The Guardrails:
*   **We Generate, We Don't Process:** SLZ exists to help you write the perfect `grep | awk` string. We will never add features like statistical analysis, graphing, or data transformation that belong to the next tool in the pipeline.
*   **Zero Configuration:** SLZ should work instantly on any stream without a config file.
*   **Transparent Output:** Our primary output will always be a human-readable shell command, not a proprietary format.

By staying small, SLZ remains fast, learnable, and a perfect citizen of the Unix ecosystem.
