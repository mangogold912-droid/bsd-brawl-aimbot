#!/usr/bin/env python3
"""
Targeted analysis of libBSD.p.so for specific strings and patterns
"""

import r2pipe
import sys

# Open the binary
r = r2pipe.open('/root/.openclaw/workspace/analysis/libBSD.p.so')

# Light analysis
print("Running light analysis (aa)...")
r.cmd('aa 2>/dev/null')

# Get all strings and search for specific ones
print("\n=== Searching for specific strings ===")
strings_output = r.cmd('iz 2>/dev/null')

search_terms = ['projectile_reversion', 'follow_projectile', 'player_position', 'reposition_wall', 'reposition']
for term in search_terms:
    for line in strings_output.split('\n'):
        if term.lower() in line.lower():
            print(f"FOUND: {line.strip()}")

# Find function count
func_count = r.cmd('aflc')
print(f"\nFunctions found: {func_count}")

# Since light analysis only found 6 functions, let's try with aaa but limit output
print("\n=== Attempting deeper analysis (aaa) ===")
r.cmd('aaa 2>/dev/null')
func_count = r.cmd('aflc')
print(f"Functions found after aaa: {func_count}")

# Try to find JNI_OnLoad
jni = r.cmd('afl~JNI')
print(f"\nJNI functions:\n{jni}")

# Get top functions by size
funcs = r.cmd('afl 2>/dev/null')
func_list = []
for line in funcs.strip().split('\n'):
    parts = line.split()
    if len(parts) >= 3:
        try:
            size = int(parts[1], 16) if parts[1].startswith('0x') else int(parts[1])
            func_list.append((size, line))
        except:
            pass

func_list.sort(reverse=True)
print("\n=== Top 30 largest functions ===")
for size, line in func_list[:30]:
    print(f"Size: 0x{size:x} ({size} bytes) @ {line}")

r.quit()
