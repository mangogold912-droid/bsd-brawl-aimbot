// Colt Super - Wall Breaking Physics
// Handles wall penetration, deceleration, and trajectory prediction

#include <math.h>
#include <stdint.h>

#define MAX_WALLS 5
#define SUPER_INITIAL_SPEED 6.0f
#define SUPER_MAX_RANGE 15.0f
#define WALL_HIT_DECAY 0.5f
#define SUPER_BULLET_COUNT 6  // Colt super fires 6 large bullets

// Wall structure (simplified - in real game, read from game memory)
typedef struct {
    float x, y;
    float width, height;
    int exists;  // 0 = destroyed, 1 = exists
} wall_t;

static wall_t walls[64];  // Max 64 walls in map
static int wall_count = 0;

// Add wall to tracking
void add_wall(float x, float y, float w, float h) {
    if (wall_count >= 64) return;
    walls[wall_count].x = x;
    walls[wall_count].y = y;
    walls[wall_count].width = w;
    walls[wall_count].height = h;
    walls[wall_count].exists = 1;
    wall_count++;
}

// Check if point is inside wall
int point_in_wall(float px, float py, wall_t* wall) {
    return (px >= wall->x && px <= wall->x + wall->width &&
            py >= wall->y && py <= wall->y + wall->height);
}

// Ray-wall intersection test
// Returns: distance to wall, or -1 if no intersection
float ray_wall_intersection(float start_x, float start_y, 
                             float dir_x, float dir_y,
                             wall_t* wall) {
    if (!wall->exists) return -1.0f;
    
    // Simple AABB ray intersection
    float tmin = -INFINITY, tmax = INFINITY;
    
    if (dir_x != 0.0f) {
        float tx1 = (wall->x - start_x) / dir_x;
        float tx2 = (wall->x + wall->width - start_x) / dir_x;
        tmin = fmaxf(tmin, fminf(tx1, tx2));
        tmax = fminf(tmax, fmaxf(tx1, tx2));
    }
    
    if (dir_y != 0.0f) {
        float ty1 = (wall->y - start_y) / dir_y;
        float ty2 = (wall->y + wall->height - start_y) / dir_y;
        tmin = fmaxf(tmin, fminf(ty1, ty2));
        tmax = fminf(tmax, fmaxf(ty1, ty2));
    }
    
    if (tmax < tmin || tmax < 0) return -1.0f;
    return tmin > 0 ? tmin : -1.0f;
}

// Calculate super projectile trajectory with wall breaking
// Returns array of (time, speed) segments
void calculate_super_trajectory(
    float start_x, float start_y,
    float aim_x, float aim_y,
    float* segment_times,      // Output: time for each segment
    float* segment_speeds,     // Output: speed for each segment
    int* num_segments          // Output: number of segments
) {
    float dx = aim_x - start_x;
    float dy = aim_y - start_y;
    float dist = sqrtf(dx*dx + dy*dy);
    
    if (dist < 0.01f) {
        *num_segments = 0;
        return;
    }
    
    float dir_x = dx / dist;
    float dir_y = dy / dist;
    
    float current_speed = SUPER_INITIAL_SPEED;
    float current_x = start_x;
    float current_y = start_y;
    float total_distance = 0.0f;
    int walls_hit = 0;
    int seg = 0;
    
    segment_speeds[0] = current_speed;
    
    while (total_distance < SUPER_MAX_RANGE && walls_hit < MAX_WALLS) {
        // Find nearest wall in direction
        float nearest_dist = INFINITY;
        int nearest_wall = -1;
        
        for (int i = 0; i < wall_count; i++) {
            if (!walls[i].exists) continue;
            float d = ray_wall_intersection(current_x, current_y, dir_x, dir_y, &walls[i]);
            if (d > 0.01f && d < nearest_dist) {
                nearest_dist = d;
                nearest_wall = i;
            }
        }
        
        if (nearest_wall >= 0 && total_distance + nearest_dist < dist) {
            // Will hit a wall
            float time_to_wall = nearest_dist / current_speed;
            segment_times[seg] = time_to_wall;
            segment_speeds[seg] = current_speed;
            seg++;
            
            // Move to wall, destroy it, decelerate
            current_x += dir_x * nearest_dist;
            current_y += dir_y * nearest_dist;
            total_distance += nearest_dist;
            walls[nearest_wall].exists = 0;  // Destroy wall
            walls_hit++;
            
            // Decelerate
            current_speed *= WALL_HIT_DECAY;
            if (current_speed < 0.5f) break;  // Too slow
        } else {
            // No more walls or target reached
            float remaining_dist = dist - total_distance;
            float time_remaining = remaining_dist / current_speed;
            segment_times[seg] = time_remaining;
            segment_speeds[seg] = current_speed;
            seg++;
            total_distance += remaining_dist;
            break;
        }
    }
    
    *num_segments = seg;
}

// Predict enemy position for super with wall breaking
void predict_super_leading_position(
    float target_x, float target_y,
    float target_vx, float target_vy,
    float shooter_x, float shooter_y,
    float aim_x, float aim_y,
    float* predicted_x, float* predicted_y
) {
    float segment_times[8];
    float segment_speeds[8];
    int num_segments;
    
    calculate_super_trajectory(shooter_x, shooter_y, aim_x, aim_y,
                               segment_times, segment_speeds, &num_segments);
    
    // Total time
    float total_time = 0.0f;
    for (int i = 0; i < num_segments; i++) {
        total_time += segment_times[i];
    }
    
    // Clamp prediction time
    total_time = total_time > 1.5f ? 1.5f : total_time;
    
    // Predict enemy position
    *predicted_x = target_x + target_vx * total_time;
    *predicted_y = target_y + target_vy * total_time;
}

// Check if super can reach target (considering walls and range)
int can_super_reach_target(
    float shooter_x, float shooter_y,
    float target_x, float target_y
) {
    float dist = sqrtf((target_x - shooter_x)*(target_x - shooter_x) + 
                       (target_y - shooter_y)*(target_y - shooter_y));
    return dist <= SUPER_MAX_RANGE * 1.2f;  // Small buffer
}
