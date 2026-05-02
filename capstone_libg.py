#!/usr/bin/env python3
"""
libg.so 분석 - Projectile Position Write 함수 찾기
Capstone으로 ARM64 디스어셈블
"""
from capstone import *
from capstone.arm64 import *

BINARY = '/root/.openclaw/workspace/analysis/libg.so'

def read_bytes(path, offset, size):
    with open(path, 'rb') as f:
        f.seek(offset)
        return f.read(size)

def analyze_function(md, code, base_addr):
    """함수 내에서 float store 패턴 분석"""
    results = []
    str_count = 0
    freg_usage = set()
    
    for insn in md.disasm(code, base_addr):
        # float store 패턴: str s0/s1/s2/s3, [xn, #offset]
        if insn.mnemonic == 'str':
            ops = insn.op_str.split(',')
            if len(ops) >= 2:
                reg = ops[0].strip()
                if reg.startswith('s') or reg.startswith('d'):
                    str_count += 1
                    freg_usage.add(reg)
                    results.append({
                        'addr': insn.address,
                        'mnemonic': insn.mnemonic,
                        'op_str': insn.op_str,
                        'bytes': insn.bytes.hex()
                    })
        
        # fadd, fsub, fmul 패턴
        if insn.mnemonic in ['fadd', 'fsub', 'fmul', 'fdiv']:
            results.append({
                'addr': insn.address,
                'mnemonic': insn.mnemonic,
                'op_str': insn.op_str,
                'bytes': insn.bytes.hex()
            })
    
    return results, str_count, freg_usage

# libg.so는 19MB이므로, 전체를 분석하는 대신 특정 섹션만 분석
# 코드 섹션은 0x0 ~ 0x10f15a0 (첫 번째 LOAD 세그먼트)

print("=" * 80)
print("libg.so - Float Store Pattern Analysis")
print("=" * 80)

md = Cs(CS_ARCH_ARM64, CS_MODE_ARM)
md.detail = True

# 샘플링: 여러 위치에서 코드 샘플을 분석
sample_offsets = [
    (0x100000, 0x10000),  # 1MB 위치, 64KB 샘플
    (0x500000, 0x10000),  # 5MB 위치
    (0x1000000, 0x10000), # 16MB 위치
    (0x170000, 0x10000),  # 문자열 주소 근처
    (0x190000, 0x10000),  # 문자열 주소 근처
]

all_results = []

for offset, size in sample_offsets:
    print(f"\n=== Analyzing @ 0x{offset:x} (+0x{size:x}) ===")
    code = read_bytes(BINARY, offset, size)
    
    results, str_count, fregs = analyze_function(md, code, offset)
    
    if str_count > 0:
        print(f"  Float stores found: {str_count}")
        print(f"  Float regs used: {fregs}")
        for r in results[:10]:  # 처음 10개만 출력
            print(f"    0x{r['addr']:x}: {r['mnemonic']} {r['op_str']}")
        all_results.extend(results)

print("\n" + "=" * 80)
print(f"Total float store instructions found: {len(all_results)}")
print("=" * 80)

# 상위 20개 float store 주소 출력
if all_results:
    print("\nTop float store locations:")
    for r in all_results[:20]:
        print(f"  0x{r['addr']:x}: {r['mnemonic']} {r['op_str']}")
