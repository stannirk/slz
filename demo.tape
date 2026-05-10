Output slz_demo.gif

Set Shell zsh
Set FontSize 20
Set Width 1200
Set Height 600
Set Padding 40
Set Theme "TokyoNight"
Set TypingSpeed 100ms

# Set PYTHONPATH so python3 -m slz works
Type "export PYTHONPATH=$PYTHONPATH:$(pwd)/src"
Enter
Sleep 500ms

# Start the recording with virtual load
Type "python3 gen_load.py | python3 -m slz -f"
Enter

# WAIT for TUI to fully load
Sleep 3s

# 1. Type filter slowly to ensure capture
Type "chrome"
Sleep 2s

# 2. Add column extraction (Notice the header stays pinned)
Type " col:2"
Sleep 2s

# 3. Navigate the data
Down 3
Sleep 1s
Down 3
Sleep 1s

# 4. Use Tab to select the current line (SEL indicator updates)
Tab
Sleep 1s
Down 2
Tab
Sleep 2s

# 5. Finish and show the output (Headers are preserved)
Enter
Sleep 4s
