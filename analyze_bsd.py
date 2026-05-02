#!/usr/bin/env python3
"""
Radare2 script to analyze libBSD.p.so for:
1. Functions with floating point stores (potential position setters)
2. Functions referencing JNI_OnLoad and their call graph
3. Vector2/Position setX/setY patterns (STR of float values, FADD/FSUB/FMUL)
4. Largest functions by stack frame size
"""

import r2pipe
import json
import sys

# Open the binary
r = r2pipe.open('/root/.openclaw/workspace/analysis/libBSD.p.so')

# Analyze all
r.cmd('aaaa 2>/dev/null')

# 1. Find functions with floating point stores (str with float registers)
print("=" * 80)
print("1. FUNCTIONS WITH FLOATING POINT STORES (Potential Position Setters)")
print("=" * 80)

# Search for str instructions with S (float) registers
result = r.cmd('/c str s 2>/dev/null | head -100')
print(result)

# 2. Find JNI_OnLoad references
print("\n" + "=" * 80)
print("2. JNI_OnLoad REFERENCES AND CALL GRAPH")
print("=" * 80)

# Find JNI_OnLoad
jni_funcs = r.cmd('afl~JNI 2>/dev/null')
print("JNI Functions found:")
print(jni_funcs)

# Cross references from JNI_OnLoad
for func in jni_funcs.strip().split('\n'):
    if func.strip():
        parts = func.split()
        if len(parts) >= 1:
            addr = parts[0]
            print(f"\n--- XREFS from {func} ---")
            xrefs = r.cmd(f'axF @ {addr} 2>/dev/null | head -50')
            print(xrefs)

# 3. Search for FADD/FSUB/FMUL patterns
print("\n" + "=" * 80)
print("3. FLOATING POINT ARITHMETIC PATTERNS (FADD/FSUB/FMUL/FDIV)")
print("=" * 80)

for op in ['fadd', 'fsub', 'fmul', 'fdiv']:
    print(f"\n--- {op.upper()} occurrences ---")
    result = r.cmd(f'/c {op} 2>/dev/null | head -50')
    print(result)

# 4. Find largest functions by instruction count
print("\n" + "=" * 80)
print("4. LARGEST FUNCTIONS (Most likely game logic)")
print("=" * 80)

r.cmd('e scr.utf8=0')
funcs = r.cmd('afl 2>/dev/null')
func_list = []
for line in funcs.strip().split('\n'):
    parts = line.split()
    if len(parts) >= 3:
        try:
            addr = int(parts[0], 16)
            size = int(parts[1], 16) if parts[1].startswith('0x') else int(parts[1])
            name = parts[2] if len(parts) > 2 else 'unknown'
            func_list.append((size, addr, name, line))
        except:
            pass

# Sort by size (largest first)
func_list.sort(reverse=True)

print("\nTop 30 largest functions:")
for size, addr, name, line in func_list[:30]:
    print(f"Size: 0x{size:x} ({size} bytes) @ {line}")

# 5. Search for common position-related patterns
print("\n" + "=" * 80)
print("5. POSITION-RELATED STRING REFERENCES")
print("=" * 80)

strings = r.cmd('iz~position 2>/dev/null')
print(strings)
strings = r.cmd('iz~vector 2>/dev/null')
print(strings)
strings = r.cmd('iz~x= 2>/dev/null')
print(strings)
strings = r.cmd('iz~y= 2>/dev/null')
print(strings)

r.quit()
