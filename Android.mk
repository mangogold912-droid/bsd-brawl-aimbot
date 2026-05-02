LOCAL_PATH := $(call my-dir)

# BSD Brawl Enhanced Aimbot Library
include $(CLEAR_VARS)

LOCAL_MODULE    := bsd_aimbot
LOCAL_SRC_FILES := \
    aimbot_native.cpp \
    aimbot_enhanced.cpp \
    joystick_controller.cpp \
    colt_super_physics.cpp \
    arm64_hook.cpp

LOCAL_LDLIBS    := -llog -landroid
LOCAL_CFLAGS    := -O2 -Wall -fPIC
LOCAL_CPP_FEATURES := rtti exceptions

include $(BUILD_SHARED_LIBRARY)

# Alternative: Static library for direct injection
include $(CLEAR_VARS)
LOCAL_MODULE    := bsd_aimbot_static
LOCAL_SRC_FILES := \
    aimbot_native.cpp \
    aimbot_enhanced.cpp \
    joystick_controller.cpp \
    colt_super_physics.cpp \
    arm64_hook.cpp

LOCAL_LDLIBS    := -llog -landroid
LOCAL_CFLAGS    := -O2 -Wall -fPIC

include $(BUILD_STATIC_LIBRARY)
