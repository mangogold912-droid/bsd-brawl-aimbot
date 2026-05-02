#!/usr/bin/env python3
"""
libg.so - Position Write Pair Detection
같은 베이스 레지스터로 4바이트/8바이트 차이나는 float store 쌍 찾기
"""
from capstone import *
from collections import defaultdict

BINARY = '/root/.openclaw/workspace/analysis/libg.so'

def read_bytes(path, offset, size):
    with open(path, 'rb') as f:
        f.seek(offset)
        return f.read(size)

# 0x500000 근처에서 발견된 float store가 많았음
# 이 영역을 더 넓게 분석 (0x4f0000 ~ 0x510000, 128KB)
START = 0x4f0000
SIZE = 0x20000  # 128KB

print("=" * 80)
print(f"libg.so - Position Write Pair Detection @ 0x{START:x}")
print("=" * 80)

code = read_bytes(BINARY, START, SIZE)
md = Cs(CS_ARCH_ARM64, CS_MODE_ARM)

# 모든 float store 수집
float_stores = []
for insn in md.disasm(code, START):
    if insn.mnemonic == 'str':
        ops = insn.op_str.split(',')
        if len(ops) >= 2:
            reg = ops[0].strip()
            if reg.startswith('s') or reg.startswith('d'):
                # 메모리 오퍼랜드 파싱
                mem = ops[1].strip()
                float_stores.append({
                    'addr': insn.address,
                    'reg': reg,
                    'mem': mem,
                    'full': f"{insn.mnemonic} {insn.op_str}"
                })

print(f"\nTotal float stores in region: {len(float_stores)}")

# 베이스 레지스터별로 그룹화
base_groups = defaultdict(list)
for fs in float_stores:
    mem = fs['mem']
    # [xN, #offset] 형태 파싱
    if '[' in mem:
        base = mem.split('[')[1].split(',')[0].strip()
        # offset 추출
        if '#' in mem:
            offset_str = mem.split('#')[1].split(']')[0].strip()
            try:
                if offset_str.startswith('0x'):
                    offset = int(offset_str, 16)
                else:
                    offset = int(offset_str)
            except:
                offset = 0
        else:
            offset = 0
        base_groups[base].append({
            'addr': fs['addr'],
            'reg': fs['reg'],
            'offset': offset,
            'full': fs['full']
        })

# 베이스 레지스터별로 오프셋 정렬 후, 4바이트/8바이트 차이나는 쌍 찾기
print("\n=== Position Write Candidates ===")
for base, stores in base_groups.items():
    if len(stores) < 2:
        continue
    
    # 오프셋 정렬
    stores_sorted = sorted(stores, key=lambda x: x['offset'])
    
    # 연속된 store 찾기 (주소가 가까운 것)
    for i in range(len(stores_sorted) - 1):
        s1 = stores_sorted[i]
        s2 = stores_sorted[i + 1]
        
        offset_diff = s2['offset'] - s1['offset']
        addr_diff = s2['addr'] - s1['addr']
        
        # 4바이트 차이 (float x, y) 또는 8바이트 차이 (double x, y)
        # 주소 차이가 32바이트 이내 (같은 함수 내)
        if offset_diff in [4, 8] and addr_diff <= 32:
            reg1 = s1['reg']
            reg2 = s2['reg']
            
            # s0/s1, d0/d1 쌍이면 강력한 position write 후보
            is_position_pair = (
                (reg1 == 's0' and reg2 == 's1') or
                (reg1 == 'd0' and reg2 == 'd1') or
                (reg1.startswith('s') and reg2.startswith('s') and 
                 int(reg1[1:]) + 1 == int(reg2[1:]))
            )
            
            if is_position_pair:
                print(f"\n  [POSITION WRITE CANDIDATE]")
                print(f"    Base: {base}")
                print(f"    0x{s1['addr']:x}: {s1['full']}")
                print(f"    0x{s2['addr']:x}: {s2['full']}")
                print(f"    Offset diff: {offset_diff} (X={s1['offset']}, Y={s2['offset']})")

# 전체 중 offset이 작은 것들만 필터 (구조체 필드 오프셋은 보통 작음)
print("\n=== All small-offset float stores (potential struct fields) ===")
for base, stores in base_groups.items():
    for s in stores:
        if s['offset'] <= 0x100:  # 256바이트 이하 오프셋
            print(f"  0x{s['addr']:x}: {s['full']} (base={base}, offset=0x{s['offset']:x})")

print("\n=== Done ===")
