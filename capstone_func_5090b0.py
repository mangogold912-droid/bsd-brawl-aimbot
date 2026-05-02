#!/usr/bin/env python3
"""
0x5090b0 함수 상세 분석 - 함수 시그니처 및 전체 디스어셈블
"""
from capstone import *

BINARY = '/root/.openclaw/workspace/analysis/libg.so'

def read_bytes(path, offset, size):
    with open(path, 'rb') as f:
        f.seek(offset)
        return f.read(size)

START = 0x5090b0
SIZE = 0x200  # 512 bytes

print("=" * 80)
print(f"libg.so - Function 0x{START:x} Full Disassembly")
print("=" * 80)

code = read_bytes(BINARY, START, SIZE)
md = Cs(CS_ARCH_ARM64, CS_MODE_ARM)

for insn in md.disasm(code, START):
    print(f"0x{insn.address:x}:\t{insn.mnemonic}\t{insn.op_str}")

print("\n=== Done ===")
