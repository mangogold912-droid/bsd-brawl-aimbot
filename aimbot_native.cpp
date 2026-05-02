// Brawl Stars - Moving Aimbot + Dodgebot Implementation
// Target: libBSD.p.so / libg.so hook integration
// Character: Colt with Star Power 1 + Buffy

#include <jni.h>
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <unistd.h>
#include <pthread.h>
#include <android/log.h>

#define LOG_TAG "BSD_AIMBOT"
#define LOGI(...) __android_log_print(ANDROID_LOG_INFO, LOG_TAG, __VA_ARGS__)
#define LOGE(...) __android_log_print(ANDROID_LOG_ERROR, LOG_TAG, __VA_ARGS__)

// ===== CONFIGURATION =====
#define AIMBOT_ENABLED_DEFAULT 1
#define DODGEBOT_ENABLED_DEFAULT 1
#define PROJECTILE_SPEED_COLT 8.33f      // Colt bullet speed (tiles/sec)
#define PROJECTILE_SPEED_COLT_SUPER 6.0f // Colt super (slower, wall breaking)
#define WALL_PENETRATION_DECAY 0.5f      // Speed decays 50% per wall hit
#define MAX_PREDICTION_TIME 1.5f         // Max prediction seconds
#define DODGE_DISTANCE 2.0f              // Dodge movement distance (tiles)
#define POSITION_OFFSET_X 0x10
#define POSITION_OFFSET_Y 0x14
#define POSITION_OFFSET_Z 0x18

// ===== STATE ===== (shared across files, non-static)
int aimbot_enabled = AIMBOT_ENABLED_DEFAULT;
int dodgebot_enabled = DODGEBOT_ENABLED_DEFAULT;
int is_firing = 0;
int is_super = 0;  // Is using super (ultimate)?

// Enemy tracking
static float enemy_x = 0.0f, enemy_y = 0.0f;
static float enemy_vx = 0.0f, enemy_vy = 0.0f;
static float prev_enemy_x = 0.0f, prev_enemy_y = 0.0f;
static int enemy_detected = 0;

// Player tracking
static float player_x = 0.0f, player_y = 0.0f;
static float player_vx = 0.0f, player_vy = 0.0f;
static float prev_player_x = 0.0f, prev_player_y = 0.0f;

// Dodge tracking
static float nearest_projectile_x = 0.0f, nearest_projectile_y = 0.0f;
static float projectile_vx = 0.0f, projectile_vy = 0.0f;
static int projectile_detected = 0;

// Joystick override
static float joystick_x = 0.0f, joystick_y = 0.0f;
static int override_joystick = 0;

// ===== MATH UTILITIES =====
static inline float clamp(float val, float min, float max) {
    return (val < min) ? min : ((val > max) ? max : val);
}

static inline float atan2f_custom(float y, float x) {
    return atan2f(y, x);
}

static inline float distance(float x1, float y1, float x2, float y2) {
    float dx = x2 - x1;
    float dy = y2 - y1;
    return sqrtf(dx*dx + dy*dy);
}

// ===== LEADING SHOT CALCULATION =====
// Calculate where to aim to hit a moving target
// Returns: (aim_x, aim_y) - the predicted position
static void calculate_leading_shot(
    float target_x, float target_y,
    float target_vx, float target_vy,
    float shooter_x, float shooter_y,
    float projectile_speed,
    float* aim_x, float* aim_y
) {
    float dx = target_x - shooter_x;
    float dy = target_y - shooter_y;
    float dist = sqrtf(dx*dx + dy*dy);
    
    // Time for projectile to reach target (initial estimate)
    float t = dist / projectile_speed;
    t = clamp(t, 0.0f, MAX_PREDICTION_TIME);
    
    // Iterative refinement (2 iterations for accuracy)
    for (int i = 0; i < 2; i++) {
        *aim_x = target_x + target_vx * t;
        *aim_y = target_y + target_vy * t;
        
        float new_dx = *aim_x - shooter_x;
        float new_dy = *aim_y - shooter_y;
        float new_dist = sqrtf(new_dx*new_dx + new_dy*new_dy);
        
        t = new_dist / projectile_speed;
        t = clamp(t, 0.0f, MAX_PREDICTION_TIME);
    }
    
    *aim_x = target_x + target_vx * t;
    *aim_y = target_y + target_vy * t;
}

// ===== WALL BREAKING LOGIC =====
// Colt's super breaks walls and decelerates
static float calculate_super_projectile_speed(
    float initial_speed,
    int walls_hit,
    float distance_traveled
) {
    // Speed decays exponentially with walls hit
    float decay = powf(WALL_PENETRATION_DECAY, (float)walls_hit);
    
    // Also decays with distance (simulated linear decay)
    float distance_decay = clamp(1.0f - (distance_traveled / 15.0f), 0.0f, 1.0f);
    
    return initial_speed * decay * distance_decay;
}

// ===== ENEMY PREDICTION WITH WALL BREAK =====
static void calculate_super_leading_shot(
    float target_x, float target_y,
    float target_vx, float target_vy,
    float shooter_x, float shooter_y,
    float* aim_x, float* aim_y
) {
    // For super, we need to account for wall penetration
    // Simplified: assume 1-2 walls between shooter and target
    float avg_speed = PROJECTILE_SPEED_COLT_SUPER * 0.75f; // Average after wall hits
    calculate_leading_shot(target_x, target_y, target_vx, target_vy,
                          shooter_x, shooter_y, avg_speed, aim_x, aim_y);
}

// ===== JOYSTICK CONTROL =====
// This function is called to override joystick input during firing
static void calculate_auto_move_joystick(
    float aim_x, float aim_y,
    float current_player_x, float current_player_y,
    float* out_joystick_x, float* out_joystick_y
) {
    float dx = aim_x - current_player_x;
    float dy = aim_y - current_player_y;
    float dist = sqrtf(dx*dx + dy*dy);
    
    if (dist < 0.1f) {
        // Close enough, stop moving
        *out_joystick_x = 0.0f;
        *out_joystick_y = 0.0f;
        return;
    }
    
    // Normalize to joystick range (-1.0 to 1.0)
    float max_speed = 2.5f; // tiles per second (Colt movement speed)
    *out_joystick_x = clamp(dx / max_speed, -1.0f, 1.0f);
    *out_joystick_y = clamp(dy / max_speed, -1.0f, 1.0f);
}

// ===== DODGEBOT LOGIC =====
static void calculate_dodge_movement(
    float player_x, float player_y,
    float proj_x, float proj_y,
    float proj_vx, float proj_vy,
    float* out_dodge_x, float* out_dodge_y
) {
    // Vector from projectile to player
    float dx = player_x - proj_x;
    float dy = player_y - proj_y;
    float dist = sqrtf(dx*dx + dy*dy);
    
    if (dist < 0.1f) return; // Too close, just move randomly
    
    // Normalize
    float nx = dx / dist;
    float ny = dy / dist;
    
    // Perpendicular vector (for dodging)
    float perp_x = -ny;
    float perp_y = nx;
    
    // Check if projectile is actually heading toward player (dot product)
    float dot = proj_vx * nx + proj_vy * ny;
    if (dot < 0.0f) {
        // Projectile moving away, no dodge needed
        *out_dodge_x = player_x;
        *out_dodge_y = player_y;
        return;
    }
    
    // Dodge perpendicular to projectile path
    *out_dodge_x = player_x + perp_x * DODGE_DISTANCE;
    *out_dodge_y = player_y + perp_y * DODGE_DISTANCE;
    
    // If perpendicular dodge would hit a wall, dodge in opposite direction
    // (Simplified - in real implementation, check wall collision)
}

// ===== HOOK FUNCTIONS =====
// These are called from the hooked libg.so functions

// Hook 0x004cc0 - TriggerProjectileOnBasicAttack
extern "C" void aimbot_on_fire_start(void* projectile_obj, void* player_obj, int is_super_attack) {
    if (!aimbot_enabled) return;
    
    is_firing = 1;
    is_super = is_super_attack;
    
    if (!enemy_detected) return;
    
    // Read current positions
    player_x = *(float*)((uint8_t*)player_obj + POSITION_OFFSET_X);
    player_y = *(float*)((uint8_t*)player_obj + POSITION_OFFSET_Y);
    
    // Calculate velocity from previous frame
    player_vx = player_x - prev_player_x;
    player_vy = player_y - prev_player_y;
    
    // Calculate enemy velocity
    enemy_vx = enemy_x - prev_enemy_x;
    enemy_vy = enemy_y - prev_enemy_y;
    
    // Calculate leading shot
    float aim_x, aim_y;
    if (is_super) {
        calculate_super_leading_shot(enemy_x, enemy_y, enemy_vx, enemy_vy,
                                      player_x, player_y, &aim_x, &aim_y);
    } else {
        calculate_leading_shot(enemy_x, enemy_y, enemy_vx, enemy_vy,
                              player_x, player_y, PROJECTILE_SPEED_COLT, &aim_x, &aim_y);
    }
    
    // Auto-move to align shot
    calculate_auto_move_joystick(aim_x, aim_y, player_x, player_y,
                                &joystick_x, &joystick_y);
    override_joystick = 1;
    
    // Store previous positions
    prev_player_x = player_x;
    prev_player_y = player_y;
    prev_enemy_x = enemy_x;
    prev_enemy_y = enemy_y;
}

// Hook 0x004fac - player_position tracker (called every frame)
extern "C" void aimbot_on_position_update(void* obj, float x, float y) {
    // Update player or enemy position based on object type
    // Simplified: we detect which object by checking if it's near known player position
    float dist_to_player = distance(x, y, player_x, player_y);
    float dist_to_enemy = distance(x, y, enemy_x, enemy_y);
    
    if (dist_to_player < dist_to_enemy) {
        // This is the player
        player_x = x;
        player_y = y;
        
        // Apply dodgebot if enabled and projectile detected
        if (dodgebot_enabled && projectile_detected) {
            float dodge_x, dodge_y;
            calculate_dodge_movement(player_x, player_y,
                                    nearest_projectile_x, nearest_projectile_y,
                                    projectile_vx, projectile_vy,
                                    &dodge_x, &dodge_y);
            
            // Override position
            *(float*)((uint8_t*)obj + POSITION_OFFSET_X) = dodge_x;
            *(float*)((uint8_t*)obj + POSITION_OFFSET_Y) = dodge_y;
        }
    } else {
        // This might be an enemy or projectile
        // We track the closest moving object as enemy
        float speed = sqrtf((x - enemy_x)*(x - enemy_x) + (y - enemy_y)*(y - enemy_y));
        if (speed > 0.01f) { // Moving object
            enemy_x = x;
            enemy_y = y;
            enemy_detected = 1;
        }
    }
}

// Hook 0x004c10 - enemy detection
extern "C" void aimbot_on_enemy_detected(void* enemy_obj) {
    enemy_detected = 1;
    enemy_x = *(float*)((uint8_t*)enemy_obj + POSITION_OFFSET_X);
    enemy_y = *(float*)((uint8_t*)enemy_obj + POSITION_OFFSET_Y);
}

// Hook 0x004f28 - projectile tracking (for dodgebot)
extern "C" void dodgebot_on_projectile_detected(void* proj_obj, float vx, float vy) {
    if (!dodgebot_enabled) return;
    
    projectile_detected = 1;
    nearest_projectile_x = *(float*)((uint8_t*)proj_obj + POSITION_OFFSET_X);
    nearest_projectile_y = *(float*)((uint8_t*)proj_obj + POSITION_OFFSET_Y);
    projectile_vx = vx;
    projectile_vy = vy;
}

// Hook 0x0056a8 - projectile speed (for wall break tracking)
extern "C" float aimbot_get_projectile_speed(float base_speed, int walls_hit, float distance) {
    if (!aimbot_enabled) return base_speed;
    
    if (is_super) {
        return calculate_super_projectile_speed(base_speed, walls_hit, distance);
    }
    return base_speed;
}

// ===== JOYSTICK OVERRIDE =====
// This function intercepts the joystick input from the game
extern "C" void aimbot_get_joystick_input(float* x, float* y) {
    if (override_joystick && is_firing) {
        *x = joystick_x;
        *y = joystick_y;
    }
}

// ===== FIRE STOP =====
extern "C" void aimbot_on_fire_stop() {
    is_firing = 0;
    override_joystick = 0;
    is_super = 0;
}

// ===== TOGGLE FUNCTIONS =====
extern "C" JNIEXPORT void JNICALL
Java_com_bsd_brawl_mod_Aimbot_toggleAimbot(JNIEnv* env, jobject thiz, jboolean enabled) {
    aimbot_enabled = enabled ? 1 : 0;
    LOGI("Aimbot %s", enabled ? "ENABLED" : "DISABLED");
}

extern "C" JNIEXPORT void JNICALL
Java_com_bsd_brawl_mod_Aimbot_toggleDodgebot(JNIEnv* env, jobject thiz, jboolean enabled) {
    dodgebot_enabled = enabled ? 1 : 0;
    LOGI("Dodgebot %s", enabled ? "ENABLED" : "DISABLED");
}

extern "C" JNIEXPORT jint JNICALL
Java_com_bsd_brawl_mod_Aimbot_isAimbotEnabled(JNIEnv* env, jobject thiz) {
    return aimbot_enabled;
}

extern "C" JNIEXPORT jint JNICALL
Java_com_bsd_brawl_mod_Aimbot_isDodgebotEnabled(JNIEnv* env, jobject thiz) {
    return dodgebot_enabled;
}

// ===== INITIALIZATION =====
extern "C" JNIEXPORT void JNICALL
Java_com_bsd_brawl_mod_Aimbot_init(JNIEnv* env, jobject thiz) {
    LOGI("BSD Aimbot initialized - Colt optimized");
    LOGI("Position offsets: X=+0x%x Y=+0x%x Z=+0x%x",
         POSITION_OFFSET_X, POSITION_OFFSET_Y, POSITION_OFFSET_Z);
}
