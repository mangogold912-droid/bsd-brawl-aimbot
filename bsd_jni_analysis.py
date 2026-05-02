#!/usr/bin/env python3
import subprocess

BINARY = '/root/.openclaw/workspace/analysis/libBSD.p.so'

def run_r2(script, timeout=60):
    with open('/tmp/bsd_script.r2', 'w') as f:
        f.write(script)
    result = subprocess.run(
        f"r2 -q -i /tmp/bsd_script.r2 {BINARY}",
        shell=True, capture_output=True, text=True, timeout=timeout
    )
    out = result.stdout + result.stderr
    return '\n'.join([l for l in out.split('\n') if not l.startswith('Warning:')])

print("=" * 80)
print("libBSD.p.so - JNI_OnLoad Analysis")
print("=" * 80)

# Step 1: Analyze and get function list
print("\n=== Function List ===")
script = """aaa
afl
q"""
funcs = run_r2(script, timeout=180)
print(funcs[:3000])

# Step 2: Disassemble JNI_OnLoad
print("\n=== JNI_OnLoad Disassembly ===")
script = """aaa
s 0x2f9288
pdf
q"""
disasm = run_r2(script, timeout=180)
print(disasm[:5000])

# Step 3: Search for libg.so references
print("\n=== Searching for libg.so references ===")
script = """aaa
/x 676c6962  # 'libg' in hex (little endian: 'bgil' but let's search both)
q"""
# Actually, let's search for 'libg.so' bytes
libg_bytes = '6c6962672e736f'  # 'libg.so' in hex
script = f"""aaa
/x {libg_bytes}
q"""
refs = run_r2(script, timeout=120)
print(refs[:2000])

print("\n=== Done ===")
