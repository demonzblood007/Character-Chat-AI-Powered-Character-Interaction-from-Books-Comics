#!/usr/bin/env python3

with open('app/server.py', 'r') as f:
    lines = f.readlines()

# Fix line 440 (0-indexed as 439)
if len(lines) > 439:
    # The line should be indented 16 spaces (same as the if statement)
    line_content = lines[439].lstrip()
    lines[439] = '                ' + line_content

# Write back
with open('app/server.py', 'w') as f:
    f.writelines(lines)

print("Fixed indentation issue in server.py")
