#!/usr/bin/env python3
"""
Deep analysis of libg.so for projectile position offsets
"""

import r2pipe
import re
import sys

BINARY = '/root/.openclaw/workspace/analysis/libg.so'

def find_string_address(r, pattern):
    """Find address of a string matching pattern"""
    result = r.cmd(f'iz~{pattern}')
    matches = []
    for line in result.strip().split('\n'):
        if not line.strip():
            continue
        # iz output format: num addr vaddr ... string
        parts = line.split()
        if len(parts) >= 5:
            try:
                addr = parts[2] if parts[2].startswith('0x') else parts[1]
                string_data = ' '.join(parts[5:]) if len(parts) > 5 else parts[-1]
                matches.append((addr, string_data))
            except:
                pass
    return matches

def find_xrefs_to_string(r, vaddr):
    """Find cross-references to a string address"""
    result = r.cmd(f'axt @{vaddr}')
    xrefs = []
    for line in result.strip().split('\n'):
        if not line.strip():
            continue
        parts = line.split()
        if len(parts) >= 3:
            try:
                from_addr = parts[0]
                func_addr = parts[2] if len(parts) > 2 else 'unknown'
                xrefs.append((from_addr, func_addr))
            except:
                pass
    return xrefs

def analyze_function_for_float_stores(r, func_addr):
    """Analyze a function for float store patterns"""
    # Get function disassembly
    disasm = r.cmd(f'pdf @{func_addr}')
    
    patterns = []
    lines = disasm.split('\n')
    
    for line in lines:
        # Look for float store patterns
        if any(x in line.lower() for x in ['str s', 'fadd', 'fsub', 'fmul', 'fdiv', 'fmov', 'fmla']):
            patterns.append(line)
        # Look for structure offset patterns (common in position writes)
        if 'str' in line and any(x in line for x in ['[x', '[w']):
            # Check if it has register like s0-s31 or d0-d31
            match = re.search(r'str\s+[sd]\d+', line)
            if match:
                patterns.append(line)
    
    return patterns

def get_function_info(r, func_addr):
    """Get function size and basic info"""
    result = r.cmd(f'afi @{func_addr}')
    info = {}
    for line in result.split('\n'):
        if 'size' in line.lower():
            parts = line.split(':')
            if len(parts) > 1:
                info['size'] = parts[1].strip()
        if 'name' in line.lower():
            parts = line.split(':')
            if len(parts) > 1:
                info['name'] = parts[1].strip()
    return info

# Main analysis
print("=" * 80)
print("libg.so - Projectile Position Analysis")
print("=" * 80)

r = r2pipe.open(BINARY)

# Run analysis (use aa instead of aaaa for speed, or aaaa for thoroughness)
print("\n[1] Running analysis...")
r.cmd('aaaa')  # Full analysis

# Key patterns to search for
search_patterns = [
    'projectile',
    'position',
    'follow',
    'reposition',
    'setX',
    'setY',
    'SetX',
    'SetY',
    'velocity',
    'speed',
    'Player',
    'LogicProjectile',
    'Projectile'
]

print("\n[2] Searching for key strings...")
all_strings = {}
for pattern in search_patterns:
    matches = find_string_address(r, pattern)
    if matches:
        all_strings[pattern] = matches
        print(f"\n  Pattern '{pattern}':")
        for addr, string_data in matches[:10]:  # Limit output
            print(f"    {addr}: {string_data}")

print("\n[3] Finding cross-references...")
string_xrefs = {}
for pattern, matches in all_strings.items():
    for addr, string_data in matches[:3]:  # Limit to first 3 matches
        xrefs = find_xrefs_to_string(r, addr)
        if xrefs:
            key = f"{pattern}@{addr}"
            string_xrefs[key] = xrefs
            print(f"\n  {addr} ({pattern}):")
            for from_addr, func_addr in xrefs[:10]:
                print(f"    xref from: {from_addr} in func: {func_addr}")

print("\n[4] Analyzing referencing functions for float stores...")
analyzed_funcs = set()
for key, xrefs in string_xrefs.items():
    for from_addr, func_addr in xrefs:
        if func_addr not in analyzed_funcs and func_addr != 'unknown':
            analyzed_funcs.add(func_addr)
            info = get_function_info(r, func_addr)
            size = info.get('size', 'unknown')
            name = info.get('name', 'unknown')
            
            patterns = analyze_function_for_float_stores(r, func_addr)
            if patterns:
                print(f"\n  Function {func_addr} ({name}, size: {size})")
                print(f"    Referenced by: {key}")
                print(f"    Float/position patterns found: {len(patterns)}")
                for p in patterns[:15]:  # Limit output
                    print(f"      {p}")

print("\n[5] Searching for common position write patterns...")
# Search for str s0/s1/s2 with structure offsets
for reg in ['s0', 's1', 's2', 's3', 'd0', 'd1', 'd2']:
    print(f"\n  Searching str {reg} patterns...")
    result = r.cmd(f'/ad str {reg} 2>/dev/null | head -30')
    if result.strip():
        for line in result.strip().split('\n')[:10]:
            print(f"    {line}")

print("\n[6] Searching for function names containing position/set...")
func_search = r.cmd('afl~position')
if func_search.strip():
    print("  Functions with 'position':")
    for line in func_search.strip().split('\n')[:20]:
        print(f"    {line}")

func_search = r.cmd('afl~set')
if func_search.strip():
    print("  Functions with 'set':")
    for line in func_search.strip().split('\n')[:20]:
        print(f"    {line}")

print("\n[7] Looking for large functions (potential complex logic)...")
large_funcs = r.cmd('afl 2>/dev/null')
func_sizes = []
for line in large_funcs.strip().split('\n'):
    parts = line.split()
    if len(parts) >= 3:
        try:
            addr = parts[0]
            size = int(parts[1], 16) if parts[1].startswith('0x') else int(parts[1])
            name = parts[3] if len(parts) > 3 else 'unknown'
            func_sizes.append((size, addr, name, line))
        except:
            pass

func_sizes.sort(reverse=True)
print("  Top 20 largest functions:")
for size, addr, name, line in func_sizes[:20]:
    print(f"    0x{size:x} bytes @ {addr} ({name})")

r.quit()
print("\n" + "=" * 80)
print("Analysis complete")
print("=" * 80)
