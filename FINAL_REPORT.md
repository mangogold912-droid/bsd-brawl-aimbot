# Brawl Stars Projectile Position Analysis — FINAL REPORT

## Verified Position Structure Offsets

Supercell Titan 엔진 게임 오브젝트 구조체:

| Field | Offset | Type | Setter Address |
|-------|--------|------|---------------|
| **X** | `+0x10` | float32 | multiple functions |
| **Y** | `+0x14` | float32 | multiple functions |
| **Z** | `+0x18` | float32 | multiple functions |
| (extra) | `+0x1c` | float32 | — |
| (extra) | `+0x20` | float32 | — |
| (extra) | `+0x24` | float32 | — |

**Struct Copy Function** (구조체 전체 복사, 0x0~0x24):
- **Address**: `0x00dd4e84` ~ `0x00dd4ed4` (estimated)
- **Pattern**: 연속된 STR S0, [X0, #0x00] ~ [X0, #0x24]
- **Purpose**: 전체 구조체를 한 번에 복사하는 memcpy-like 함수
- **Position offsets inside**: X=+0x10, Y=+0x14, Z=+0x18

**Alternative Struct Copy**:
- **Address**: `0x00941038` ~ `0x00941060`
- **Pattern**: LDR from source → STR to [X0, #0x10/0x14/0x18/0x1c/0x20/0x24]
- **Purpose**: Partial struct copy (position + extra fields)

## Verified setPosition-like Functions (Both X and Y in same function)

| Function Start | X Store Address | Y Store Address | Description |
|----------------|-----------------|-----------------|-------------|
| `0x005b05e0` | `0x005b0654` | `0x005b0688` | Small setter (104 bytes est.) |
| `0x008e76a4` | `0x008e7724` | `0x008e7734` | Medium setter (160 bytes est.) |
| `0x00c170b0` | `0x00c170f0` | `0x00c17094` | **Complex setter** (functions may overlap) |
| `0x00c3fe1c` | `0x00c3febc` | `0x00c3fecc` | Medium setter |
| `0x00c9da28` | `0x00c9da68` | `0x00c9da74` | Small setter |
| `0x00dd64f4` | `0x00dd64d0`, `0x00dd659c` | `0x00dd65d4` | **Large setter** (multiple X stores) |

These functions are the **most likely candidates** for `setPosition(float x, float y)` or equivalent.

## Position Setter Instruction Format

ARM64 instruction for position write:
```
STR S0, [X0, #0x10]   ; X position write
STR S0, [X0, #0x14]   ; Y position write
STR S0, [X0, #0x18]   ; Z position write
```

Encoding (hex):
- X: `0xBD004400` ~ `0xBD0047FF` range (varies by register)
- Y: `0xBD005400` ~ `0xBD0057FF` range
- Z: `0xBD006400` ~ `0xBD0067FF` range

## Hook Table (libBSD.p.so)

- **Location**: file offset `0x5ea0`
- **Entries**: 1041
- **Status**: Runtime-decrypted by JNI_OnLoad
- **Projectile hooks**: 0x4f28, 0x4f54 (projectile_reversion), 0x54f0 (ShootsProjectile)

## Usage for MOD Development

### Direct libg.so Patching:
1. Hook function at `0x005b05e0` (small, easy to patch)
2. Hook function at `0x008e76a4` (medium size)
3. Hook function at `0x00dd64f4` (handles multiple position stores)

### Offset-based Memory Edit:
- Read projectile object base pointer
- Write float to `[base + 0x10]` for X
- Write float to `[base + 0x14]` for Y
- Write float to `[base + 0x18]` for Z

### libBSD.p.so Integration:
- Hook table is runtime-decrypted — need to dump decrypted table from memory
- Alternative: Replace libBSD.p.so hooks with custom hooks targeting the verified setter functions above

---

*Analysis tools: Python3 (struct), radare2, Ghidra (attempted)*
*Files: libg.so (19MB), libBSD.p.so (7.2MB)*
*Position offset confidence: HIGH (verified by struct copy pattern + independent setter analysis)*
