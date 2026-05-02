#!/usr/bin/env python3
import subprocess

BINARY = '/root/.openclaw/workspace/analysis/libg.so'

def run_r2(script, timeout=180):
    cmd = f"echo -e '{script}' | r2 -q {BINARY}"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    out = result.stdout + result.stderr
    # Filter warnings
    lines = [l for l in out.split('\n') if not l.startswith('Warning:') and not l.startswith('[r]')]
    return '\n'.join(lines)

print("=" * 80)
print("libg.so - Position Write Function Discovery")
print("=" * 80)

# Step 1: List all functions
print("\n=== Step 1: Getting function list ===")
funcs_script = """aaa
afl
q
"""
funcs_raw = run_r2(funcs_script, timeout=300)
print(f"Functions output length: {len(funcs_raw)}")
print(funcs_raw[:2000])

# Parse functions
functions = []
for line in funcs_raw.split('\n'):
    parts = line.split()
    if len(parts) >= 3 and parts[0].startswith('0x'):
        try:
            addr = parts[0]
            size = int(parts[1], 16) if parts[1].startswith('0x') else int(parts[1])
            name = parts[3] if len(parts) > 3 else 'unknown'
            functions.append((size, addr, name))
        except:
            pass

functions.sort(reverse=True)
print(f"\nTotal functions found: {len(functions)}")
print(f"Top 20 largest functions:")
for size, addr, name in functions[:20]:
    print(f"  0x{size:x} bytes @ {addr} ({name})")

# Step 2: Search for float/position patterns in top functions
print("\n=== Step 2: Searching for position write patterns ===")
target_patterns = ['str s0', 'str s1', 'str s2', 'str s3', 'str d0', 'str d1', 'fadd', 'fsub', 'fmul', 'fdiv', 'fmov']

for size, addr, name in functions[:50]:
    script = f"""aaa
af @ {addr}
pdf @ {addr}
q
"""
    disasm = run_r2(script, timeout=60)
    
    matches = []
    for line in disasm.split('\n'):
        for pat in target_patterns:
            if pat in line.lower():
                matches.append(line)
                break
    
    if len(matches) >= 3:  # Functions with multiple float ops are interesting
        print(f"\n  Function {name} @ {addr} (size: 0x{size:x}):")
        print(f"    Float/position operations: {len(matches)}")
        for m in matches[:15]:
            print(f"      {m}")

print("\n=== Step 3: Direct string address search in code ===")
string_addrs = [0x17f3ce, 0x196e42, 0x19a117, 0x1a4c02, 0x1e6938, 0x1b295e]
for saddr in string_addrs:
    # Search for references to this address using /x
    # ARM64 may reference strings with ADRP+ADD or LDR =address
    script = f"""aaa
/x {saddr & 0xFFFFFFFF:08x}
q
"""
    result = run_r2(script, timeout=60)
    lines = [l for l in result.split('\n') if l.strip() and 'hits' not in l.lower()]
    if len(lines) > 0:
        print(f"\n  References to 0x{saddr:x}:")
        for line in lines[:20]:
            print(f"    {line}")

print("\n=== Done ===")
