#!/usr/bin/env python3
"""
0x5091a0 영역 상세 분석 - Position Write 함수 확인
"""
from capstone import *

BINARY = '/root/.openclaw/workspace/analysis/libg.so'

def read_bytes(path, offset, size):
    with open(path, 'rb') as f:
        f.seek(offset)
        return f.read(size)

# 0x5091a0 전후 4KB 분석
START = 0x508000
SIZE = 0x4000  # 16KB

print("=" * 80)
print(f"libg.so - Detailed Analysis @ 0x{START:x} - 0x{START+SIZE:x}")
print("=" * 80)

code = read_bytes(BINARY, START, SIZE)
md = Cs(CS_ARCH_ARM64, CS_MODE_ARM)

# 함수 경계 추정 (ret 명령어 기준)
current_func_start = START
func_stores = []

for insn in md.disasm(code, START):
    # ret 또는 b (unconditional branch to far)가 함수 끝으로 추정
    if insn.mnemonic == 'ret':
        # 현재 함수의 float store 요약
        if func_stores:
            print(f"\n--- Function 0x{current_func_start:x} ~ 0x{insn.address:x} ---")
            for fs in func_stores:
                print(f"  0x{fs['addr']:x}: {fs['mnemonic']} {fs['op_str']}")
        current_func_start = insn.address + 4
        func_stores = []
    
    # float store 수집
    if insn.mnemonic == 'str':
        ops = insn.op_str.split(',')
        if len(ops) >= 2:
            reg = ops[0].strip()
            if reg.startswith('s') or reg.startswith('d'):
                func_stores.append({
                    'addr': insn.address,
                    'mnemonic': insn.mnemonic,
                    'op_str': insn.op_str
                })
    
    # vector 연산도 수집
    if insn.mnemonic in ['fadd', 'fsub', 'fmul', 'fdiv', 'fmov']:
        func_stores.append({
            'addr': insn.address,
            'mnemonic': insn.mnemonic,
            'op_str': insn.op_str
        })

# 마지막 함수
if func_stores:
    print(f"\n--- Function 0x{current_func_start:x} ~ 0x{START+SIZE:x} ---")
    for fs in func_stores:
        print(f"  0x{fs['addr']:x}: {fs['mnemonic']} {fs['op_str']}")

print("\n=== Done ===")
