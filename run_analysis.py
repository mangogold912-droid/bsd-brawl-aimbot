import subprocess
import json

def run_r2cmd(cmds, binary='/root/.openclaw/workspace/analysis/libBSD.p.so'):
    """Run radare2 commands and return output"""
    script = '\n'.join(cmds)
    result = subprocess.run(
        ['r2', '-q', binary],
        input=script,
        capture_output=True,
        text=True,
        timeout=300
    )
    return result.stdout + result.stderr

# Initial analysis
print("=== Running initial analysis ===")
output = run_r2cmd(['aaaa', 'aflc'])
print(output)

# Find JNI_OnLoad
print("\n=== JNI Functions ===")
output = run_r2cmd(['aaaa', 'afl~JNI'])
print(output)

# Search for floating point stores (str with S registers)
print("\n=== Floating Point Stores (str s*) ===")
output = run_r2cmd(['aaaa', '/c str s | head -50'])
print(output)

# Search for FADD/FSUB/FMUL/FDIV
print("\n=== Float Arithmetic ===")
for op in ['fadd', 'fsub', 'fmul', 'fdiv']:
    print(f"\n--- {op} ---")
    output = run_r2cmd(['aaaa', f'/c {op} | head -30'])
    print(output)

# Get largest functions
print("\n=== Largest Functions ===")
output = run_r2cmd(['aaaa', 'afl'])
print(output[:5000])

# Search for position-related strings
print("\n=== Position/Vector Strings ===")
for term in ['position', 'vector', 'x=', 'y=', 'setX', 'setY']:
    print(f"\n--- {term} ---")
    output = run_r2cmd(['iz~' + term])
    print(output)
