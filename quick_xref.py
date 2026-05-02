import subprocess

BINARY = '/root/.openclaw/workspace/analysis/libg.so'

string_offsets = {
    'follow_projectile': 0x17f3ce,
    'projectile_reversion': 0x196e42,
    'player_position': 0x19a117,
    'reposition_wall': 0x1a4c02,
    'offsetX': 0x1e6938,
    'offsetY': 0x1b295e,
}

def run_r2(cmds):
    full = f"r2 -q -e bin.cache=true {BINARY}"
    for cmd in cmds:
        full += f" -c '{cmd}'"
    result = subprocess.run(full, shell=True, capture_output=True, text=True, timeout=300)
    return result.stdout + result.stderr

print("=== String Virtual Addresses ===")
vaddrs = {}
for name, foffset in string_offsets.items():
    # Search for string using iz
    iz_result = run_r2([f'iz~{name}'])
    print(f"\n  {name}: file_offset=0x{foffset:x}")
    if iz_result.strip():
        print(f"    iz output: {iz_result.strip()}")
        # Parse vaddr - format: num addr vaddr ...
        for line in iz_result.strip().split('\n'):
            parts = line.split()
            if len(parts) >= 3 and parts[2].startswith('0x'):
                vaddr = parts[2]
                vaddrs[name] = vaddr
                print(f"    vaddr: {vaddr}")
                break
    else:
        print(f"    No iz output")

print("\n=== Cross References ===")
for name, vaddr in vaddrs.items():
    print(f"\n  {name} @ {vaddr}:")
    xrefs = run_r2([f'axt @{vaddr}'])
    if xrefs.strip():
        for line in xrefs.strip().split('\n')[:30]:
            print(f"    {line}")
    else:
        print("    No xrefs found")

print("\n=== Analysis Complete ===")
