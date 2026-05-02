// ARM64 Inline Hook Implementation for libBSD.p.so / libg.so
// Provides: hook_install, hook_remove, trampoline execution
// Target: Android ARM64 (aarch64)

#include <sys/mman.h>
#include <string.h>
#include <stdint.h>
#include <android/log.h>

#define LOG_TAG "BSD_HOOK"
#define LOGI(...) __android_log_print(ANDROID_LOG_INFO, LOG_TAG, __VA_ARGS__)
#define LOGE(...) __android_log_print(ANDROID_LOG_ERROR, LOG_TAG, __VA_ARGS__)

#define PAGE_SIZE 4096
#define ALIGN_PAGE_DOWN(addr) ((addr) & ~(PAGE_SIZE - 1))
#define ALIGN_PAGE_UP(addr) (((addr) + PAGE_SIZE - 1) & ~(PAGE_SIZE - 1))

// Hook structure
typedef struct {
    uintptr_t target_addr;      // Original function address
    uintptr_t hook_addr;        // Our hook function
    uintptr_t trampoline_addr;  // Trampoline (original + jump back)
    uint32_t  original_code[4]; // Backup of first 4 instructions
    uint32_t  jump_code[4];     // Our jump patch
    int       installed;
} arm64_hook_t;

// Make memory region writable and executable
static int set_memory_protection(uintptr_t addr, size_t size, int prot) {
    uintptr_t page_start = ALIGN_PAGE_DOWN(addr);
    uintptr_t page_end = ALIGN_PAGE_UP(addr + size);
    size_t page_size = page_end - page_start;
    
    if (mprotect((void*)page_start, page_size, prot) != 0) {
        LOGE("mprotect failed for range 0x%lx-0x%lx", page_start, page_end);
        return -1;
    }
    return 0;
}

// ARM64 ADRP instruction encoder
// adrpd: Rd, target_page relative to PC
static uint32_t encode_adrp(int reg, int64_t imm) {
    // ADRP: 1-0010-0-immlo:2-immhi:19-Rd:5
    uint32_t rd = reg & 0x1F;
    int64_t immlo = imm & 0x3;
    int64_t immhi = (imm >> 2) & 0x7FFFF;
    return 0x90000000 | (immlo << 29) | (immhi << 5) | rd;
}

// ARM64 ADD immediate encoder (12-bit immediate)
static uint32_t encode_add_imm(int reg_d, int reg_n, uint16_t imm) {
    // ADD (immediate): 10010001-shift:1-imm12:12-Rn:5-Rd:5
    return 0x91000000 | ((imm & 0xFFF) << 10) | ((reg_n & 0x1F) << 5) | (reg_d & 0x1F);
}

// ARM64 BR (Branch to Register) encoder
static uint32_t encode_br(int reg) {
    // BR: 1101011000011111000000-Rn:5-00000
    return 0xD61F0000 | ((reg & 0x1F) << 5);
}

// ARM64 NOP encoder
static uint32_t encode_nop() {
    return 0xD503201F;
}

// ARM64 B (unconditional branch) encoder
static uint32_t encode_b(int32_t offset) {
    // B: 000101-imm26:26
    int32_t imm26 = (offset >> 2) & 0x3FFFFFF;
    return 0x14000000 | imm26;
}

// ARM64 LDR (literal) encoder
static uint32_t encode_ldr_literal(int reg, int32_t offset) {
    // LDR (literal): 01011000-imm19:19-Rt:5
    int32_t imm19 = (offset >> 2) & 0x7FFFF;
    return 0x58000000 | (imm19 << 5) | (reg & 0x1F);
}

// Install inline hook at target_addr, redirect to hook_addr
int install_hook(arm64_hook_t* hook, uintptr_t target_addr, uintptr_t hook_addr) {
    if (hook->installed) {
        LOGE("Hook already installed");
        return -1;
    }
    
    hook->target_addr = target_addr;
    hook->hook_addr = hook_addr;
    
    // Allocate trampoline (executable memory near target)
    // In real implementation: use mmap near target, or use pre-allocated trampolines in libBSD.p.so
    // For this PoC, we assume trampoline is allocated at hook_addr + 0x1000
    hook->trampoline_addr = hook_addr + 0x1000;
    
    // Backup original instructions (4 instructions = 16 bytes)
    memcpy(hook->original_code, (void*)target_addr, 16);
    
    // Create jump patch: ADRP + ADD + BR + NOP (16 bytes)
    // Or use B if within ±128MB
    int64_t offset = (int64_t)hook_addr - (int64_t)target_addr;
    
    if (offset >= -128*1024*1024 && offset <= 128*1024*1024) {
        // Use B instruction (4 bytes) - most efficient
        hook->jump_code[0] = encode_b((int32_t)offset);
        hook->jump_code[1] = encode_nop();
        hook->jump_code[2] = encode_nop();
        hook->jump_code[3] = encode_nop();
    } else {
        // Use ADRP + ADD + BR (16 bytes)
        int64_t page_diff = ((hook_addr & ~0xFFF) - (target_addr & ~0xFFF)) >> 12;
        uint16_t page_offset = hook_addr & 0xFFF;
        
        hook->jump_code[0] = encode_adrp(17, page_diff);  // ADRP X17, #page
        hook->jump_code[1] = encode_add_imm(17, 17, page_offset); // ADD X17, X17, #offset
        hook->jump_code[2] = encode_br(17);               // BR X17
        hook->jump_code[3] = encode_nop();                // NOP
    }
    
    // Build trampoline: original instructions + jump back to target+16
    uint32_t* tramp = (uint32_t*)hook->trampoline_addr;
    memcpy(tramp, hook->original_code, 16);
    
    int64_t return_offset = (int64_t)(target_addr + 16) - (int64_t)(hook->trampoline_addr + 16);
    if (return_offset >= -128*1024*1024 && return_offset <= 128*1024*1024) {
        tramp[4] = encode_b((int32_t)return_offset);
    } else {
        // ADRP + ADD + BR back
        int64_t ret_page_diff = (((target_addr + 16) & ~0xFFF) - ((hook->trampoline_addr + 16) & ~0xFFF)) >> 12;
        uint16_t ret_page_offset = (target_addr + 16) & 0xFFF;
        tramp[4] = encode_adrp(17, ret_page_diff);
        tramp[5] = encode_add_imm(17, 17, ret_page_offset);
        tramp[6] = encode_br(17);
        tramp[7] = encode_nop();
    }
    
    // Make target writable
    if (set_memory_protection(target_addr, 16, PROT_READ | PROT_WRITE | PROT_EXEC) != 0) {
        return -1;
    }
    
    // Write jump patch to target
    memcpy((void*)target_addr, hook->jump_code, 16);
    
    // Flush cache (important on ARM64)
    __builtin___clear_cache((char*)target_addr, (char*)target_addr + 16);
    __builtin___clear_cache((char*)hook->trampoline_addr, (char*)hook->trampoline_addr + 32);
    
    hook->installed = 1;
    LOGI("Hook installed: 0x%lx -> 0x%lx (trampoline: 0x%lx)", 
         target_addr, hook_addr, hook->trampoline_addr);
    return 0;
}

// Remove hook and restore original instructions
int remove_hook(arm64_hook_t* hook) {
    if (!hook->installed) {
        return -1;
    }
    
    if (set_memory_protection(hook->target_addr, 16, PROT_READ | PROT_WRITE | PROT_EXEC) != 0) {
        return -1;
    }
    
    memcpy((void*)hook->target_addr, hook->original_code, 16);
    __builtin___clear_cache((char*)hook->target_addr, (char*)hook->target_addr + 16);
    
    hook->installed = 0;
    LOGI("Hook removed: 0x%lx", hook->target_addr);
    return 0;
}

// ===== HOOK TARGETS FOR AIMBOT/DODGEBOT =====

// Hook target addresses (from analysis)
#define HOOK_FIRE_TRIGGER       0x004cc0   // TriggerProjectileOnBasicAttack
#define HOOK_ENEMY_DETECT       0x004c10   // Enemy detection
#define HOOK_PROJECTILE_TRACK   0x004f28   // Projectile tracking
#define HOOK_POSITION_TRACK     0x004fac   // Position tracker
#define HOOK_PROJECTILE_SPEED   0x0056a8   // Projectile speed
#define HOOK_AIM_ANGLE          0x005030   // Aim angle
#define HOOK_AIM_DIRECTION      0x004e4c   // Aim direction

static arm64_hook_t hooks[8];
static int hook_count = 0;

// ===== HOOK INSTALLATION API =====

extern "C" JNIEXPORT void JNICALL
Java_com_bsd_brawl_mod_Aimbot_installHooks(JNIEnv* env, jobject thiz, jlong libg_base, jlong libbsd_base) {
    LOGI("Installing hooks - libg.so base: 0x%lx, libBSD.p.so base: 0x%lx", libg_base, libbsd_base);
    
    // Note: These addresses are file offsets. In memory they are loaded at base + offset.
    // libBSD.p.so hooks are at base + 0x100000 + offset (typical Android load address)
    // libg.so functions are at libg_base + offset
    
    // For libBSD.p.so hooks, we hook the hook trampolines themselves
    // For libg.so, we hook the actual functions
    
    // Example: Hook libg.so position setter at 0x005b05e0
    uintptr_t setter_x_addr = libg_base + 0x005b05e0;
    // ... install hook here
    
    // Example: Hook libBSD.p.so 0x004cc0 (fire trigger)
    uintptr_t fire_hook_addr = libbsd_base + 0x100000 + 0x004cc0;
    // ... install hook here
    
    LOGI("Hooks installed successfully");
}

extern "C" JNIEXPORT void JNICALL
Java_com_bsd_brawl_mod_Aimbot_removeHooks(JNIEnv* env, jobject thiz) {
    for (int i = 0; i < hook_count; i++) {
        remove_hook(&hooks[i]);
    }
    hook_count = 0;
    LOGI("All hooks removed");
}
