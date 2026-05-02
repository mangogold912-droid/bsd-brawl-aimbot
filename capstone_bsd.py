#!/usr/bin/env python3
from capstone import *

BINARY = '/root/.openclaw/workspace/analysis/libBSD.p.so'
JNI_ONLOAD_ADDR = 0x2f9288

def read_bytes(path, offset, size):
    with open(path, 'rb') as f:
        f.seek(offset)
        return f.read(size)

# Read code around JNI_OnLoad
code = read_bytes(BINARY, JNI_ONLOAD_ADDR, 0x3000)

print("=" * 80)
print(f"libBSD.p.so - JNI_OnLoad @ 0x{JNI_ONLOAD_ADDR:x}")
print("=" * 80)

md = Cs(CS_ARCH_ARM64, CS_MODE_ARM)

print("\n=== Disassembly ===")
for insn in md.disasm(code, JNI_ONLOAD_ADDR):
    print(f"0x{insn.address:x}:\t{insn.mnemonic}\t{insn.op_str}")
    
print("\n=== Done ===")
