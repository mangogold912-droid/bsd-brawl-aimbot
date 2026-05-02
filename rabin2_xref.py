#!/usr/bin/env python3
import subprocess
import re

BINARY = '/root/.openclaw/workspace/analysis/libg.so'

def run_cmd(cmd, timeout=60):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    return result.stdout + result.stderr

# Step 1: Get string virtual addresses using rabin2
print("=== Step 1: String Addresses via rabin2 ===")
strings_raw = run_cmd(f'rabin2 -z {BINARY}')

target_strings = ['follow_projectile', 'projectile_reversion', 'player_position', 'reposition_wall', 'offsetX', 'offsetY']
string_addrs = {}

for line in strings_raw.split('\n'):
    for ts in target_strings:
        if ts in line:
            parts = line.split()
            if len(parts) >= 2:
                addr = parts[1] if parts[1].startswith('0x') else parts[0]
                string_addrs[ts] = addr
                print(f"  {ts}: {addr}")
                break

# Step 2: Find xrefs using r2
print("\n=== Step 2: Cross References via r2 ===")
xref_results = {}
for name, addr in string_addrs.items():
    print(f"\n  {name} @ {addr}:")
    # Use r2 to find xrefs
    r2_out = run_cmd(f"r2 -q -c 'aa' -c 'axt @{addr}' -c 'q' {BINARY}", timeout=120)
    if 'Warning' in r2_out:
        r2_out = r2_out.split('Warning')[0]  # Strip warnings
    lines = [l for l in r2_out.split('\n') if l.strip() and not l.startswith('Warning')]
    if lines:
        xref_results[name] = lines
        for line in lines[:30]:
            print(f"    {line}")
    else:
        print(f"    No xrefs (output was: {r2_out[:200]})")

# Step 3: Analyze functions that reference strings
print("\n=== Step 3: Function Analysis ===")
for name, xrefs in xref_results.items():
    print(f"\n--- References to {name} ---")
    seen_funcs = set()
    for line in xrefs[:10]:
        parts = line.split()
        if len(parts) >= 2:
            ref_addr = parts[0]
            # Get function name
            func_out = run_cmd(f"r2 -q -c 'aa' -c 'afn @{ref_addr}' -c 'q' {BINARY}", timeout=60)
            func_name = func_out.strip()
            if func_name and func_name not in seen_funcs:
                seen_funcs.add(func_name)
                print(f"\n  Function: {func_name} (ref @ {ref_addr})")
                # Get disassembly around reference
                disasm = run_cmd(f"r2 -q -c 'aa' -c 'pd 20 @{ref_addr}' -c 'q' {BINARY}", timeout=60)
                for dline in disasm.split('\n')[:20]:
                    if dline.strip():
                        print(f"    {dline}")

print("\n=== Done ===")
