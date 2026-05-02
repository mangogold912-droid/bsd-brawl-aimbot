// Joystick Input Override for BSD Brawl
// Hooks joystick input to enable auto-move during firing

#include <jni.h>
#include <math.h>
#include <string.h>
#include <android/log.h>
#include <stdint.h>

#define LOG_TAG "BSD_JOYSTICK"
#define LOGI(...) __android_log_print(ANDROID_LOG_INFO, LOG_TAG, __VA_ARGS__)

// External from aimbot_enhanced.cpp
extern int aimbot_enabled;
extern int is_firing;
extern int is_super;
extern float player_x, player_y;

// Joystick override state
static float override_joystick_x = 0.0f;
static float override_joystick_y = 0.0f;
static int joystick_override_active = 0;

// Original joystick values (when not overriding)
static float original_joystick_x = 0.0f;
static float original_joystick_y = 0.0f;

// ===== JOYSTICK INPUT HOOK =====
// This function intercepts the game's joystick input
// It is called every frame to get the current joystick values

extern "C" void joystick_input_hook(float* out_x, float* out_y) {
    // Store original values
    original_joystick_x = *out_x;
    original_joystick_y = *out_y;
    
    // If aimbot is enabled and we are firing, override joystick
    if (aimbot_enabled && is_firing && joystick_override_active) {
        *out_x = override_joystick_x;
        *out_y = override_joystick_y;
        
        LOGI("Joystick Override: Original(%.2f,%.2f) -> Aimbot(%.2f,%.2f)",
             original_joystick_x, original_joystick_y,
             override_joystick_x, override_joystick_y);
    }
    // Otherwise, pass through original values
}

// ===== FIRE BUTTON DETECTION =====
// Detects when fire button is pressed/released

extern "C" void fire_button_hook(int button_state, int is_super_button) {
    // button_state: 1 = pressed, 0 = released
    // is_super_button: 1 = super button, 0 = normal fire button
    
    if (button_state == 1) {
        // Fire button pressed
        is_firing = 1;
        is_super = is_super_button;
        
        LOGI("Fire button PRESSED (super=%d)", is_super);
    } else {
        // Fire button released
        is_firing = 0;
        is_super = 0;
        joystick_override_active = 0;
        
        LOGI("Fire button RELEASED");
    }
}

// ===== SUPER BUTTON DETECTION =====
// Separate hook for super/ultimate button

extern "C" void super_button_hook(int button_state) {
    if (button_state == 1) {
        is_firing = 1;
        is_super = 1;
        LOGI("Super button PRESSED");
    } else {
        is_firing = 0;
        is_super = 0;
        joystick_override_active = 0;
        LOGI("Super button RELEASED");
    }
}

// ===== JOYSTICK OVERRIDE SETTER =====
// Called from aimbot logic to set desired joystick direction

extern "C" void set_joystick_override(float x, float y) {
    override_joystick_x = x;
    override_joystick_y = y;
    joystick_override_active = 1;
}

extern "C" void clear_joystick_override() {
    joystick_override_active = 0;
    override_joystick_x = 0.0f;
    override_joystick_y = 0.0f;
}

// ===== TOUCH/SWIPE INTERCEPTION =====
// For devices that use touch/swipe instead of joystick

extern "C" void touch_input_hook(float touch_x, float touch_y, int action) {
    // action: 0 = down, 1 = move, 2 = up
    
    if (!aimbot_enabled || !is_firing) return;
    
    if (action == 1) { // move
        // Override touch position to auto-move
        // In real implementation: modify the touch event being sent to the game
        LOGI("Touch Override: (%.1f,%.1f)", touch_x, touch_y);
    }
}

// ===== JNI EXPORTS =====

extern "C" JNIEXPORT void JNICALL
Java_com_bsd_brawl_mod_JoystickController_setJoystickOverride(JNIEnv* env, jobject thiz,
                                                               jfloat x, jfloat y) {
    set_joystick_override(x, y);
}

extern "C" JNIEXPORT void JNICALL
Java_com_bsd_brawl_mod_JoystickController_clearJoystickOverride(JNIEnv* env, jobject thiz) {
    clear_joystick_override();
}

extern "C" JNIEXPORT jboolean JNICALL
Java_com_bsd_brawl_mod_JoystickController_isOverriding(JNIEnv* env, jobject thiz) {
    return joystick_override_active ? JNI_TRUE : JNI_FALSE;
}
