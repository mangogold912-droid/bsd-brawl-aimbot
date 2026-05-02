// Enhanced BSD Brawl Aimbot - Self-Learning Moving Aimbot
// Character: Colt with Star Power 1 + Buffy
// Features: Multi-target tracking, advanced leading shot, optimal distance, self-learning

#include <jni.h>
#include <math.h>
#include <string.h>
#include <android/log.h>

#define LOG_TAG "BSD_ENHANCED"
#define LOGI(...) __android_log_print(ANDROID_LOG_INFO, LOG_TAG, __VA_ARGS__)
#define LOGE(...) __android_log_print(ANDROID_LOG_ERROR, LOG_TAG, __VA_ARGS__)

#define MAX_ENEMIES 10
#define HISTORY_SIZE 16
#define POSITION_OFFSET_X 0x10
#define POSITION_OFFSET_Y 0x14
#define PROJECTILE_SPEED_COLT 8.33f
#define COLT_OPTIMAL_RANGE_MIN 4.0f   // Minimum optimal range (tiles)
#define COLT_OPTIMAL_RANGE_MAX 9.0f   // Maximum optimal range (tiles)
#define COLT_OPTIMAL_RANGE_CENTER 6.5f // Preferred distance

// Enhanced enemy tracking with pattern learning
typedef struct {
    float x, y;           // Current position
    float vx, vy;         // Velocity
    float ax, ay;         // Acceleration
    float history_x[HISTORY_SIZE];
    float history_y[HISTORY_SIZE];
    float history_vx[HISTORY_SIZE];
    float history_vy[HISTORY_SIZE];
    int history_idx;
    int valid;
    int frames_tracked;
    float health;         // Estimated health (lower = priority target)
    float threat_level;   // Calculated threat
} enemy_data_t;

static enemy_data_t enemies[MAX_ENEMIES];
static int enemy_count = 0;

// Player data
static float player_x = 0.0f, player_y = 0.0f;
static float player_vx = 0.0f, player_vy = 0.0f;

// Self-learning weights
static float learning_weights[4] = {0.4f, 0.3f, 0.2f, 0.1f}; // distance, health, threat, pattern
static float accuracy_history[32]; // Track shot accuracy
static int accuracy_idx = 0;

// State
static int aimbot_enabled = 1;
static int is_firing = 0;
static int is_super = 0;

// ===== SELF-LEARNING: PATTERN RECOGNITION =====

// Analyze enemy movement pattern
// Returns pattern type: 0=straight, 1=zigzag, 2=circle, 3=random
int analyze_movement_pattern(enemy_data_t* enemy) {
    if (enemy->frames_tracked < 8) return 3; // Not enough data
    
    float variance_x = 0.0f, variance_y = 0.0f;
    float mean_vx = 0.0f, mean_vy = 0.0f;
    
    // Calculate mean velocity
    for (int i = 0; i < HISTORY_SIZE; i++) {
        mean_vx += enemy->history_vx[i];
        mean_vy += enemy->history_vy[i];
    }
    mean_vx /= HISTORY_SIZE;
    mean_vy /= HISTORY_SIZE;
    
    // Calculate variance
    for (int i = 0; i < HISTORY_SIZE; i++) {
        variance_x += (enemy->history_vx[i] - mean_vx) * (enemy->history_vx[i] - mean_vx);
        variance_y += (enemy->history_vy[i] - mean_vy) * (enemy->history_vy[i] - mean_vy);
    }
    
    float total_variance = variance_x + variance_y;
    
    // Detect zigzag: high variance but periodic
    float direction_changes = 0.0f;
    for (int i = 1; i < HISTORY_SIZE; i++) {
        float dot = enemy->history_vx[i-1] * enemy->history_vx[i] + 
                    enemy->history_vy[i-1] * enemy->history_vy[i];
        if (dot < 0) direction_changes++;
    }
    
    if (direction_changes >= HISTORY_SIZE * 0.4f) {
        return 1; // Zigzag pattern
    } else if (total_variance < 0.01f) {
        return 0; // Straight line
    } else if (total_variance > 0.5f) {
        return 3; // Random
    }
    
    return 2; // Circular/other
}

// Predict enemy position based on learned pattern
void predict_with_pattern(enemy_data_t* enemy, float time, float* out_x, float* out_y) {
    int pattern = analyze_movement_pattern(enemy);
    
    switch (pattern) {
        case 0: // Straight - linear prediction
            *out_x = enemy->x + enemy->vx * time;
            *out_y = enemy->y + enemy->vy * time;
            break;
            
        case 1: // Zigzag - add oscillation
            {
                *out_x = enemy->x + enemy->vx * time;
                *out_y = enemy->y + enemy->vy * time;
                // Add perpendicular oscillation
                float perp_x = -enemy->vy;
                float perp_y = enemy->vx;
                float oscillation = sinf(time * 3.0f) * 1.5f; // Amplitude
                *out_x += perp_x * oscillation;
                *out_y += perp_y * oscillation;
            }
            break;
            
        case 2: // Circular - predict circular path
            {
                float speed = sqrtf(enemy->vx * enemy->vx + enemy->vy * enemy->vy);
                float radius = 2.0f; // Estimated turn radius
                float angular_speed = speed / radius;
                float angle = atan2f(enemy->vy, enemy->vx);
                float new_angle = angle + angular_speed * time;
                *out_x = enemy->x + radius * (cosf(new_angle) - cosf(angle));
                *out_y = enemy->y + radius * (sinf(new_angle) - sinf(angle));
            }
            break;
            
        default: // Random - conservative prediction
            *out_x = enemy->x + enemy->vx * time * 0.5f;
            *out_y = enemy->y + enemy->vy * time * 0.5f;
            break;
    }
}

// ===== MULTI-TARGET PRIORITY SYSTEM =====

// Calculate priority score for each enemy
// Lower score = higher priority (target this enemy)
float calculate_target_priority(enemy_data_t* enemy, float player_x, float player_y) {
    float dist = sqrtf((enemy->x - player_x) * (enemy->x - player_x) + 
                       (enemy->y - player_y) * (enemy->y - player_y));
    
    // Distance factor (closer = higher priority, but not too close)
    float dist_score = fabsf(dist - COLT_OPTIMAL_RANGE_CENTER) / COLT_OPTIMAL_RANGE_CENTER;
    
    // Health factor (lower health = higher priority)
    float health_score = enemy->health / 100.0f;
    
    // Threat factor
    float threat_score = enemy->threat_level / 10.0f;
    
    // Pattern predictability (straight line = easier to hit = higher priority)
    int pattern = analyze_movement_pattern(enemy);
    float pattern_score = (pattern == 0) ? 0.0f : (pattern == 1) ? 0.3f : 0.6f;
    
    // Weighted sum
    return learning_weights[0] * dist_score + 
           learning_weights[1] * health_score + 
           learning_weights[2] * threat_score + 
           learning_weights[3] * pattern_score;
}

// Select best target
enemy_data_t* select_best_target(float player_x, float player_y) {
    enemy_data_t* best = NULL;
    float best_score = 999999.0f;
    
    for (int i = 0; i < MAX_ENEMIES; i++) {
        if (!enemies[i].valid) continue;
        
        float score = calculate_target_priority(&enemies[i], player_x, player_y);
        if (score < best_score) {
            best_score = score;
            best = &enemies[i];
        }
    }
    
    return best;
}

// ===== ADVANCED LEADING SHOT =====

// 3-iteration Newton-Raphson with acceleration
void calculate_advanced_leading_shot(
    enemy_data_t* enemy,
    float shooter_x, float shooter_y,
    float projectile_speed,
    float* aim_x, float* aim_y
) {
    float dx = enemy->x - shooter_x;
    float dy = enemy->y - shooter_y;
    float dist = sqrtf(dx * dx + dy * dy);
    
    float t = dist / projectile_speed;
    if (t > 1.5f) t = 1.5f;
    
    // Iterative refinement
    for (int i = 0; i < 3; i++) {
        predict_with_pattern(enemy, t, aim_x, aim_y);
        
        float new_dx = *aim_x - shooter_x;
        float new_dy = *aim_y - shooter_y;
        float new_dist = sqrtf(new_dx * new_dx + new_dy * new_dy);
        
        // For super with wall deceleration, adjust speed
        if (is_super) {
            // Assume 1-2 walls average
            float avg_speed = projectile_speed * 0.75f;
            t = new_dist / avg_speed;
        } else {
            t = new_dist / projectile_speed;
        }
        
        if (t > 1.5f) t = 1.5f;
    }
    
    predict_with_pattern(enemy, t, aim_x, aim_y);
}

// ===== OPTIMAL DISTANCE AUTO-MOVE =====

// Calculate joystick input to maintain optimal range while shooting
void calculate_optimal_move_joystick(
    enemy_data_t* target,
    float current_x, float current_y,
    float* out_joystick_x, float* out_joystick_y
) {
    float dx = target->x - current_x;
    float dy = target->y - current_y;
    float dist = sqrtf(dx * dx + dy * dy);
    
    if (dist < 0.01f) {
        *out_joystick_x = 0.0f;
        *out_joystick_y = 0.0f;
        return;
    }
    
    // Direction to enemy
    float dir_x = dx / dist;
    float dir_y = dy / dist;
    
    // Calculate desired distance change
    float dist_error = dist - COLT_OPTIMAL_RANGE_CENTER;
    
    // If too close, move away; if too far, move closer
    float move_speed = dist_error * 0.5f;
    if (move_speed > 2.5f) move_speed = 2.5f; // Max movement speed
    if (move_speed < -2.5f) move_speed = -2.5f;
    
    // For lateral alignment (to hit moving enemy), add perpendicular component
    float perp_x = -dir_y;
    float perp_y = dir_x;
    
    // Lateral movement to track enemy
    float lateral_speed = 1.0f; // Lateral tracking speed
    float lateral_x = perp_x * lateral_speed;
    float lateral_y = perp_y * lateral_speed;
    
    // Combine: radial movement + lateral tracking
    float joy_x = dir_x * move_speed + lateral_x;
    float joy_y = dir_y * move_speed + lateral_y;
    
    // Normalize to -1.0 ~ 1.0
    float joy_mag = sqrtf(joy_x * joy_x + joy_y * joy_y);
    if (joy_mag > 1.0f) {
        joy_x /= joy_mag;
        joy_y /= joy_mag;
    }
    
    *out_joystick_x = joy_x;
    *out_joystick_y = joy_y;
}

// ===== SELF-LEARNING: ACCURACY FEEDBACK =====

// Call this when a shot hits or misses
void update_accuracy(float hit_distance) {
    float accuracy = (hit_distance < 0.5f) ? 1.0f : 
                     (hit_distance < 1.0f) ? 0.7f : 
                     (hit_distance < 2.0f) ? 0.3f : 0.0f;
    
    accuracy_history[accuracy_idx % 32] = accuracy;
    accuracy_idx++;
    
    // Adjust learning weights based on accuracy
    if (accuracy_idx >= 32) {
        float avg_accuracy = 0.0f;
        for (int i = 0; i < 32; i++) avg_accuracy += accuracy_history[i];
        avg_accuracy /= 32.0f;
        
        // If accuracy is low, increase pattern weight (more conservative)
        if (avg_accuracy < 0.5f) {
            learning_weights[3] += 0.05f; // Increase pattern weight
            learning_weights[0] -= 0.02f; // Decrease distance weight
        } else {
            learning_weights[3] -= 0.02f; // Decrease pattern weight
            learning_weights[0] += 0.01f; // Increase distance weight
        }
        
        // Clamp weights
        for (int i = 0; i < 4; i++) {
            if (learning_weights[i] < 0.05f) learning_weights[i] = 0.05f;
            if (learning_weights[i] > 0.6f) learning_weights[i] = 0.6f;
        }
        
        LOGI("Accuracy: %.2f%% | Weights: D=%.2f H=%.2f T=%.2f P=%.2f",
             avg_accuracy * 100,
             learning_weights[0], learning_weights[1], 
             learning_weights[2], learning_weights[3]);
    }
}

// ===== UPDATE ENEMY DATA =====

void update_enemy(int slot, float x, float y, float health) {
    if (slot < 0 || slot >= MAX_ENEMIES) return;
    
    enemy_data_t* enemy = &enemies[slot];
    
    if (!enemy->valid) {
        // New enemy
        enemy->valid = 1;
        enemy->frames_tracked = 0;
        enemy->history_idx = 0;
    }
    
    // Calculate velocity
    float new_vx = x - enemy->x;
    float new_vy = y - enemy->y;
    
    // Calculate acceleration
    enemy->ax = new_vx - enemy->vx;
    enemy->ay = new_vy - enemy->vy;
    
    // Update position and velocity
    enemy->x = x;
    enemy->y = y;
    enemy->vx = new_vx;
    enemy->vy = new_vy;
    enemy->health = health;
    
    // Update history
    enemy->history_x[enemy->history_idx] = x;
    enemy->history_y[enemy->history_idx] = y;
    enemy->history_vx[enemy->history_idx] = new_vx;
    enemy->history_vy[enemy->history_idx] = new_vy;
    enemy->history_idx = (enemy->history_idx + 1) % HISTORY_SIZE;
    enemy->frames_tracked++;
    
    // Calculate threat level (based on distance, DPS, etc.)
    // Simplified: closer and faster = more threatening
    float speed = sqrtf(new_vx * new_vx + new_vy * new_vy);
    float dist_to_player = sqrtf((x - player_x) * (x - player_x) + (y - player_y) * (y - player_y));
    enemy->threat_level = (10.0f - dist_to_player) * speed;
    if (enemy->threat_level < 0) enemy->threat_level = 0;
}

// ===== MAIN FIRE TRIGGER =====

extern "C" void enhanced_aimbot_on_fire(void* player_obj, int is_super_attack) {
    if (!aimbot_enabled) return;
    
    is_firing = 1;
    is_super = is_super_attack;
    
    // Read player position
    player_x = *(float*)((uint8_t*)player_obj + POSITION_OFFSET_X);
    player_y = *(float*)((uint8_t*)player_obj + POSITION_OFFSET_Y);
    
    // Select best target
    enemy_data_t* target = select_best_target(player_x, player_y);
    if (!target) {
        is_firing = 0;
        return;
    }
    
    // Calculate aim position
    float aim_x, aim_y;
    float speed = is_super ? PROJECTILE_SPEED_COLT * 0.75f : PROJECTILE_SPEED_COLT;
    calculate_advanced_leading_shot(target, player_x, player_y, speed, &aim_x, &aim_y);
    
    // Calculate auto-move joystick
    float joy_x, joy_y;
    calculate_optimal_move_joystick(target, player_x, player_y, &joy_x, &joy_y);
    
    // Apply joystick override (hook game's joystick input)
    // ... (platform-specific joystick hook)
    
    LOGI("Fire: Target[%d] Pos(%.1f,%.1f) Aim(%.1f,%.1f) Joy(%.2f,%.2f) Pattern=%d",
         target - enemies, target->x, target->y, aim_x, aim_y, joy_x, joy_y,
         analyze_movement_pattern(target));
}

extern "C" void enhanced_aimbot_on_fire_stop() {
    is_firing = 0;
    is_super = 0;
}

// ===== JNI EXPORTS =====

extern "C" JNIEXPORT void JNICALL
Java_com_bsd_brawl_mod_EnhancedAimbot_init(JNIEnv* env, jobject thiz) {
    memset(enemies, 0, sizeof(enemies));
    memset(accuracy_history, 0, sizeof(accuracy_history));
    accuracy_idx = 0;
    learning_weights[0] = 0.4f;
    learning_weights[1] = 0.3f;
    learning_weights[2] = 0.2f;
    learning_weights[3] = 0.1f;
    LOGI("Enhanced Aimbot initialized - Self-Learning Colt");
}

extern "C" JNIEXPORT void JNICALL
Java_com_bsd_brawl_mod_EnhancedAimbot_updateEnemy(JNIEnv* env, jobject thiz,
                                                   jint slot, jfloat x, jfloat y, jfloat health) {
    update_enemy(slot, x, y, health);
}

extern "C" JNIEXPORT void JNICALL
Java_com_bsd_brawl_mod_EnhancedAimbot_reportHit(JNIEnv* env, jobject thiz, jfloat distance) {
    update_accuracy(distance);
}

extern "C" JNIEXPORT void JNICALL
Java_com_bsd_brawl_mod_EnhancedAimbot_setEnabled(JNIEnv* env, jobject thiz, jboolean enabled) {
    aimbot_enabled = enabled ? 1 : 0;
    LOGI("Enhanced Aimbot %s", enabled ? "ENABLED" : "DISABLED");
}
