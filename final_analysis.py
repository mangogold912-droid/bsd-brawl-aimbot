#!/usr/bin/env python3
import subprocess

BINARY = '/root/.openclaw/workspace/analysis/libg.so'

string_addrs = {
    'follow_projectile': 0x17f3ce,
    'projectile_reversion': 0x196e42,
    'player_position': 0x19a117,
    'reposition_wall': 0x1a4c02,
    'offsetX': 0x1e6938,
    'offsetY': 0x1b295e,
}

def run_r2(cmds, timeout=120):
    # Build script
    script = 'e bin.cache=true\n'
    for cmd in cmds:
        script += cmd + '\n'
    script += 'q\n'
    cmd_str = f"echo -e '{script}' | r2 -q {BINARY}"
    result = subprocess.run(cmd_str, shell=True, capture_output=True, text=True, timeout=timeout)
    return result.stdout + result.stderr

print("=" * 80)
print("libg.so - Projectile Position Analysis - Final Report")
print("=" * 80)

print("\n=== Step 1: String Verification ===")
for name, addr in string_addrs.items():
    # Verify string at address
    result = run_r2([f'ps @ {addr}'], timeout=30)
    print(f"  0x{addr:x}: {name} = '{result.strip()}'")

print("\n=== Step 2: Cross References ===")
xrefs_all = {}
for name, addr in string_addrs.items():
    print(f"\n  {name} (0x{addr:x}):")
    result = run_r2([f'axt @ {addr}'], timeout=60)
    lines = [l for l in result.split('\n') if l.strip() and not l.startswith('Warning')]
    xrefs_all[name] = lines
    for line in lines[:20]:
        print(f"    {line}")

print("\n=== Step 3: Function Analysis at XREFs ===")
for name, xrefs in xrefs_all.items():
    if not xrefs:
        continue
    print(f"\n--- {name} ---")
    seen = set()
    for line in xrefs[:5]:
        parts = line.split()
        if len(parts) >= 2:
            ref_addr = parts[0]
            if ref_addr in seen:
                continue
            seen.add(ref_addr)
            # Get function info
            func = run_r2([f'afn @{ref_addr}'], timeout=30).strip()
            if not func or 'WARNING' in func:
                func = f"sub_{ref_addr}"
            print(f"\n  Function: {func} (ref @ {ref_addr})")
            # Disassemble around reference
            disasm = run_r2([f'pd 30 @{ref_addr}'], timeout=30)
            for dline in disasm.split('\n')[:30]:
                if 'WARNING' not in dline and dline.strip():
                    print(f"    {dline}")

print("\n=== Step 4: Search for Float/Position Patterns ===")
print("\nSearching for common position write patterns (str s0, str s1, etc.):")
for reg in ['s0', 's1', 's2']:
    print(f"\n  str {reg} patterns:")
    result = run_r2([f'/ad str {reg} [x'], timeout=120)
    lines = [l for l in result.split('\n') if l.strip() and not l.startswith('Warning')][:10]
    for line in lines:
        print(f"    {line}")

print("\n=== Analysis Complete ===")
print("=" * 80)
