# Brawl Stars Aimbot + Dodgebot Implementation Guide

## Based on libBSD.p.so / libg.so Analysis

---

## 1. Core Position Offsets (libg.so)

All game objects (player, enemy, projectile) share the same position struct:

| Field | Offset | Type |
|-------|--------|------|
| X | `+0x10` | float32 |
| Y | `+0x14` | float32 |
| Z | `+0x18` | float32 |

**Read/Write via:**
- `LDR S0, [X0, #0x10]` / `STR S0, [X0, #0x10]` for X
- `LDR S0, [X0, #0x14]` / `STR S0, [X0, #0x14]` for Y
- `LDR S0, [X0, #0x18]` / `STR S0, [X0, #0x18]` for Z

---

## 2. Position Setter Functions (Verified)

### Single-field setters:
| Function | Address | Sets |
|----------|---------|------|
| setX_A | `0x005b0654` | X (+0x10) |
| setY_A | `0x005b0688` | Y (+0x14) |
| setX_B | `0x008e7724` | X (+0x10) |
| setY_B | `0x008e7734` | Y (+0x14) |

### Complete struct copy (position + extra fields):
| Function | Range | Fields |
|----------|-------|--------|
| copyStruct_A | `0x00941038` ~ `0x00941060` | X,Y,Z + extras |
| copyStruct_B | `0x00dd4e84` ~ `0x00dd4ed4` | Full struct 0x00~0x24 |

---

## 3. libBSD.p.so Hook Chain — AIMBOT

libBSD.p.so already has a complete aimbot framework built-in:

| Step | Hook VA | libg.so Target | Purpose |
|------|---------|---------------|---------|
| 1 | `0x004cc0` | `TriggerProjectileOnBasicAttack` | **Trigger shot** |
| 2 | `0x005030` | `angle` string region | **Aim angle** |
| 3 | `0x004e4c` | `direction` string region | **Aim direction** |
| 4 | `0x0056a8` | `projectile_speed` region | **Projectile speed** |
| 5 | `0x004c94` | `shoot_x` region | **Fire position X** |
| 6 | `0x004fac` | `player_position` region | **Track projectile pos** |

**How it works:**
1. `0x004cc0` hooks the shot trigger
2. `0x005030` / `0x004e4c` override aim angle/direction to point at enemy
3. `0x0056a8` ensures projectile speed is optimal
4. `0x004fac` tracks projectile position for homing

---

## 4. libBSD.p.so Hook Chain — DODGEBOT

| Step | Hook VA | libg.so Target | Purpose |
|------|---------|---------------|---------|
| 1 | `0x004c10` | `enemy` string region | **Detect enemies** |
| 2 | `0x004f28` | `projectile_reversion` | **Track enemy projectiles** |
| 3 | `0x004e4c` | `direction` | **Read projectile direction** |
| 4 | `0x005240` | `velocity` string region | **Player movement speed** |
| 5 | `0x004fac` | `player_position` | **Move player to dodge** |

**How it works:**
1. `0x004c10` detects when enemies are present
2. `0x004f28` tracks incoming projectiles
3. `0x004e4c` reads projectile direction vector
4. `0x004fac` moves player position perpendicular to projectile path

---

## 5. Colt-Specific Optimization

### Colt Characteristics:
- Fires straight-line bullets with spread
- Star Power 1: Faster bullets, tighter spread
- Buffy: Additional bullet or enhanced accuracy

### Recommended Hook Strategy:

**Method A — Precise Aim (Best for Colt):**
```
Hook 0x004cc0 (shot trigger):
  1. Read enemy position [enemy_base + 0x10], [enemy_base + 0x14]
  2. Read player position [player_base + 0x10], [player_base + 0x14]
  3. Calculate angle: atan2(enemyY - playerY, enemyX - playerX)
  4. Override aim angle at 0x005030 or 0x004e4c
  5. All bullets fire directly at enemy
```

**Method B — Homing Bullets:**
```
Hook 0x004fac (position tracker):
  1. Every frame, read projectile [projectile + 0x10], [projectile + 0x14]
  2. Read enemy [enemy + 0x10], [enemy + 0x14]
  3. Calculate delta vector
  4. Write new position to [projectile + 0x10], [projectile + 0x14]
  5. Projectile homes in on enemy
```

**Method C — Auto-Move (Colt walking while shooting):**
```
Hook 0x004cc0 (shot trigger):
  1. If enemy is not aligned with current aim:
  2. Calculate optimal player position
  3. Write to [player + 0x10], [player + 0x14] via 0x004fac
  4. Player automatically walks to align all bullets
```

---

## 6. Implementation Code Structure

### Native Hook (ARM64 Inline Hook):
```cpp
// Hook target: 0x004cc0 (TriggerProjectileOnBasicAttack)
// This is called every time a basic attack fires

void aimbot_hook(void* projectile_obj, void* enemy_obj) {
    // Read enemy position
    float enemy_x = *(float*)((uint8_t*)enemy_obj + 0x10);
    float enemy_y = *(float*)((uint8_t*)enemy_obj + 0x14);
    
    // Read player position
    float player_x = *(float*)((uint8_t*)projectile_obj + 0x10);
    float player_y = *(float*)((uint8_t*)projectile_obj + 0x14);
    
    // Calculate aim angle
    float dx = enemy_x - player_x;
    float dy = enemy_y - player_y;
    float aim_angle = atan2f(dy, dx);
    
    // Override aim (hook 0x005030 or 0x004e4c)
    // ... modify direction registers
}
```

### Dodgebot Hook:
```cpp
// Hook target: 0x004f28 (projectile_reversion)
// This tracks enemy projectiles

void dodgebot_hook(void* enemy_projectile, void* player_obj) {
    // Read projectile position
    float proj_x = *(float*)((uint8_t*)enemy_projectile + 0x10);
    float proj_y = *(float*)((uint8_t*)enemy_projectile + 0x14);
    
    // Read player position
    float player_x = *(float*)((uint8_t*)player_obj + 0x10);
    float player_y = *(float*)((uint8_t*)player_obj + 0x14);
    
    // Calculate if projectile is heading toward player
    // (dot product of projectile velocity and player direction)
    
    // If dangerous, move perpendicular
    float dodge_x = player_x + perpendicular_x * DODGE_DISTANCE;
    float dodge_y = player_y + perpendicular_y * DODGE_DISTANCE;
    
    // Write new player position
    *(float*)((uint8_t*)player_obj + 0x10) = dodge_x;
    *(float*)((uint8_t*)player_obj + 0x14) = dodge_y;
}
```

---

## 7. Critical Implementation Notes

### Hook Decryption:
- libBSD.p.so hook trampolines are **runtime-decrypted** by JNI_OnLoad
- Static bytes at file offset are encrypted/opaque
- **To analyze actual hook behavior**: Run APK in emulator, dump decrypted hooks from memory
- Alternative: Hook JNI_OnLoad and dump decrypted table at runtime

### Finding Enemy Base Pointer:
- Enemy objects use same struct layout as player
- Search memory for objects with matching position offsets
- Or hook `0x004c10` (enemy detection) to intercept enemy object references

### Finding Player Base Pointer:
- Hook `0x004fac` (player_position tracker)
- First argument to hooked function is typically `this` pointer
- `this + 0x10` = player X position

### Colt Star Power + Buffy Stack:
- Star Power 1 increases bullet speed → less dodge time for enemy
- Buffy adds bullets or tightens spread → more hits per shot
- Combined: Hook speed multiplier at `0x0056a8` and bullet count at `0x004cc0`

---

## 8. Runtime Analysis Steps

To complete the implementation:

1. **Install APK in Android emulator** (LDPlayer, BlueStacks, or Android Studio emulator)
2. **Use Frida or GameGuardian** to attach to running process
3. **Hook JNI_OnLoad** in libBSD.p.so and dump decrypted hook table
4. **Disassemble decrypted hooks** at 0x004cc0, 0x004e4c, 0x004fac
5. **Trace function arguments** to find enemy/player object pointers
6. **Verify offsets** by reading memory at [obj + 0x10], [obj + 0x14]
7. **Patch hooks** to add aimbot/dodgebot logic

---

## 9. Address Reference Table

### libg.so (Brawl Stars Engine)
| Address | Description |
|---------|-------------|
| `0x005b0654` | X setter (STR S0, [X0, #0x10]) |
| `0x005b0688` | Y setter (STR S0, [X0, #0x14]) |
| `0x008e7724` | Alternative X setter |
| `0x008e7734` | Alternative Y setter |
| `0x00941038` | Struct copy function start |
| `0x00dd4e84` | Full struct copy (0x00~0x24) |

### libBSD.p.so (MOD Hook Library)
| Address | Description |
|---------|-------------|
| `0x004c10` | Enemy detection hook |
| `0x004cc0` | Shot trigger hook |
| `0x004e4c` | Direction control hook |
| `0x004f28` | Projectile tracking hook |
| `0x004fac` | Position tracker hook |
| `0x005030` | Angle control hook |
| `0x005240` | Velocity control hook |
| `0x0056a8` | Projectile speed hook |

---

*Analysis: libg.so (19MB) + libBSD.p.so (7.2MB)*
*Tools: Python3 + ARM64 manual decoding*
*Confidence: HIGH for offsets, MEDIUM for hook behavior (pending runtime decryption)*
