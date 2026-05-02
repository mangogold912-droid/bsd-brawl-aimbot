package com.bsd.brawl.mod;

import android.app.Service;
import android.content.Intent;
import android.graphics.PixelFormat;
import android.os.IBinder;
import android.view.Gravity;
import android.view.LayoutInflater;
import android.view.MotionEvent;
import android.view.View;
import android.view.WindowManager;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

public class AimbotFloatingService extends Service {
    private WindowManager windowManager;
    private LinearLayout floatingLayout;
    private Button btnAimbot;
    private Button btnDodgebot;
    private TextView tvStatus;
    private WindowManager.LayoutParams params;
    private boolean aimbotEnabled = true;
    private boolean dodgebotEnabled = true;

    // Native methods
    static {
        System.loadLibrary("bsd_aimbot");
    }
    
    public native void init();
    public native void toggleAimbot(boolean enabled);
    public native void toggleDodgebot(boolean enabled);
    public native boolean isAimbotEnabled();
    public native boolean isDodgebotEnabled();

    @Override
    public void onCreate() {
        super.onCreate();
        init();
        createFloatingWindow();
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    private void createFloatingWindow() {
        windowManager = (WindowManager) getSystemService(WINDOW_SERVICE);
        
        // Create the floating layout
        floatingLayout = new LinearLayout(this);
        floatingLayout.setOrientation(LinearLayout.VERTICAL);
        floatingLayout.setBackgroundColor(0xAA000000); // Semi-transparent black
        
        // Title text
        tvStatus = new TextView(this);
        tvStatus.setText("BSD MOD - Colt Enhanced");
        tvStatus.setTextColor(0xFFFFD700); // Gold color
        tvStatus.setTextSize(14);
        tvStatus.setPadding(10, 10, 10, 5);
        floatingLayout.addView(tvStatus);
        
        // Aimbot toggle button
        btnAimbot = new Button(this);
        btnAimbot.setText("AIMBOT: ON");
        btnAimbot.setTextColor(0xFF00FF00); // Green
        btnAimbot.setBackgroundColor(0xFF333333);
        btnAimbot.setPadding(5, 5, 5, 5);
        btnAimbot.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                aimbotEnabled = !aimbotEnabled;
                toggleAimbot(aimbotEnabled);
                updateButtonStates();
                Toast.makeText(AimbotFloatingService.this, 
                    "Aimbot " + (aimbotEnabled ? "ON" : "OFF"), Toast.LENGTH_SHORT).show();
            }
        });
        floatingLayout.addView(btnAimbot);
        
        // Dodgebot toggle button
        btnDodgebot = new Button(this);
        btnDodgebot.setText("DODGEBOT: ON");
        btnDodgebot.setTextColor(0xFF00FF00); // Green
        btnDodgebot.setBackgroundColor(0xFF333333);
        btnDodgebot.setPadding(5, 5, 5, 5);
        btnDodgebot.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                dodgebotEnabled = !dodgebotEnabled;
                toggleDodgebot(dodgebotEnabled);
                updateButtonStates();
                Toast.makeText(AimbotFloatingService.this, 
                    "Dodgebot " + (dodgebotEnabled ? "ON" : "OFF"), Toast.LENGTH_SHORT).show();
            }
        });
        floatingLayout.addView(btnDodgebot);
        
        // Window parameters
        int layoutType;
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.O) {
            layoutType = WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY;
        } else {
            layoutType = WindowManager.LayoutParams.TYPE_PHONE;
        }
        
        params = new WindowManager.LayoutParams(
            WindowManager.LayoutParams.WRAP_CONTENT,
            WindowManager.LayoutParams.WRAP_CONTENT,
            layoutType,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE | 
            WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON,
            PixelFormat.TRANSLUCENT
        );
        
        params.gravity = Gravity.TOP | Gravity.LEFT;
        params.x = 50;
        params.y = 100;
        
        // Make it draggable
        floatingLayout.setOnTouchListener(new View.OnTouchListener() {
            private int initialX;
            private int initialY;
            private float initialTouchX;
            private float initialTouchY;
            
            @Override
            public boolean onTouch(View v, MotionEvent event) {
                switch (event.getAction()) {
                    case MotionEvent.ACTION_DOWN:
                        initialX = params.x;
                        initialY = params.y;
                        initialTouchX = event.getRawX();
                        initialTouchY = event.getRawY();
                        return true;
                        
                    case MotionEvent.ACTION_MOVE:
                        params.x = initialX + (int)(event.getRawX() - initialTouchX);
                        params.y = initialY + (int)(event.getRawY() - initialTouchY);
                        windowManager.updateViewLayout(floatingLayout, params);
                        return true;
                }
                return false;
            }
        });
        
        windowManager.addView(floatingLayout, params);
        updateButtonStates();
    }
    
    private void updateButtonStates() {
        if (aimbotEnabled) {
            btnAimbot.setText("AIMBOT: ON");
            btnAimbot.setTextColor(0xFF00FF00);
        } else {
            btnAimbot.setText("AIMBOT: OFF");
            btnAimbot.setTextColor(0xFFFF0000);
        }
        
        if (dodgebotEnabled) {
            btnDodgebot.setText("DODGEBOT: ON");
            btnDodgebot.setTextColor(0xFF00FF00);
        } else {
            btnDodgebot.setText("DODGEBOT: OFF");
            btnDodgebot.setTextColor(0xFFFF0000);
        }
    }
    
    @Override
    public void onDestroy() {
        super.onDestroy();
        if (floatingLayout != null) {
            windowManager.removeView(floatingLayout);
        }
    }
}
