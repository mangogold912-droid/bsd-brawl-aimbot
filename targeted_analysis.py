#!/usr/bin/env python3
"""
Targeted analysis of libBSD.p.so for position-related patterns
"""

import r2pipe
import sys

# Open the binary
r = r2pipe.open('/root/.openclaw/workspace/analysis/libBSD.p.so')

# Full analysis - use aaaa but with output suppressed
print("Running full analysis (this may take a while)...")
r.cmd('aaaa 2>/dev/null')

# Get function count
func_count = r.cmd('aflc')
print(f"Functions found: {func_count}")

# Find JNI_OnLoad
print("\n=== JNI_OnLoad ===")
jni = r.cmd('afl~JNI')
print(jni)

# Get cross-references from JNI_OnLoad
print("\n=== XREFS from JNI_OnLoad ===")
# JNI_OnLoad is at 0x002f9288 based on earlier output
xrefs = r.cmd('axF @ 0x002f9288 2>/dev/null | head -100')
print(xrefs)

# Search for specific strings - first dump all strings
print("\n=== All strings (first 500) ===")
strings = r.cmd('iz 2>/dev/null | head -500')
print(strings)

# Search for float stores using /ad (assemble/disassemble search)
print("\n=== Float store patterns ===")
result = r.cmd('/ad str s 2>/dev/null | head -50')
print(result)

# Search for vector-like patterns  
print("\n=== Vector position patterns ===")
for reg in ['s0', 's1', 's2', 's3']:
    print(f"\n--- str {reg} patterns ---")
    result = r.cmd(f'/ad str {reg} 2>/dev/null | head -20')
    print(result)

# Find large functions
print("\n=== Top 30 largest functions ===")
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
for size, line in func_list[:30]:
    print(f"Size: 0x{size:x} ({size} bytes) @ {line}")

# Search for FADD/FSUB/FMUL
print("\n=== Float arithmetic ===")
for op in ['fadd', 'fsub', 'fmul']:
    print(f"\n--- {op} ---")
    result = r.cmd(f'/ad {op} 2>/dev/null | head -20')
    print(result)

r.quit()
