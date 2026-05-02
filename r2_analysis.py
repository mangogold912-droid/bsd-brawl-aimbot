import subprocess
import json

def run_r2cmd(cmds, binary='/root/.openclaw/workspace/analysis/libBSD.p.so'):
    full_cmd = f"r2 -q {binary} <<'EOF'\n{'\n'.join(cmds)}\nEOF"
    result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True, timeout=300)
    return result.stdout + result.stderr

# Analyze
output = run_r2cmd(['aaaa', 'afl~JNI'])
print(output)
