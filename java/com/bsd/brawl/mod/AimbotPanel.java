package com.bsd.brawl.mod;

import android.app.Activity;
import android.content.Context;
import android.graphics.PixelFormat;
import android.graphics.Color;
import android.view.Gravity;
import android.view.MotionEvent;
import android.view.View;
import android.view.ViewGroup;
import android.view.WindowManager;
import android.widget.Button;
import android.widget.FrameLayout;
import android.widget.LinearLayout;

/**
 * TaleStars-style floating button panel.
 * Uses Activity-level WindowManager with TYPE_APPLICATION_PANEL.
 * No SYSTEM_ALERT_WINDOW permission needed!
 */
public class AimbotPanel extends FrameLayout {
    
    private static AimbotPanel instance;
    private WindowManager wm;
    private WindowManager.LayoutParams params;
    private float touchX, touchY;
    private int startX, startY;
    
    private Button btnAimbot;
    private Button btnDodge;
    private Button btnHyper;
    
    private boolean aimbotOn = false;
    private boolean dodgeOn = false;
    private boolean hyperOn = false;
    
    public AimbotPanel(Activity activity) {
        super(activity);
        init(activity);
    }
    
    private void init(Activity activity) {
        wm = activity.getWindowManager();
        
        // TaleStars style: TYPE_APPLICATION_PANEL (not TYPE_APPLICATION_OVERLAY)
        params = new WindowManager.LayoutParams(
            ViewGroup.LayoutParams.WRAP_CONTENT,
            ViewGroup.LayoutParams.WRAP_CONTENT,
            WindowManager.LayoutParams.TYPE_APPLICATION_PANEL,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE
                | WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL,
            PixelFormat.TRANSLUCENT
        );
        
        params.gravity = Gravity.TOP | Gravity.START;
        params.x = 50;
        params.y = 100;
        params.softInputMode = WindowManager.LayoutParams.SOFT_INPUT_ADJUST_NOTHING;
        
        // Build UI
        LinearLayout layout = new LinearLayout(getContext());
        layout.setOrientation(LinearLayout.VERTICAL);
        layout.setBackgroundColor(Color.argb(180, 30, 30, 30));
        layout.setPadding(10, 10, 10, 10);
        
        btnAimbot = createToggle("AIMBOT");
        btnDodge = createToggle("DODGE");
        btnHyper = createToggle("HYPER");
        
        layout.addView(btnAimbot);
        layout.addView(btnDodge);
        layout.addView(btnHyper);
        
        addView(layout);
        
        // Drag support
        setOnTouchListener(new OnTouchListener() {
            @Override
            public boolean onTouch(View v, MotionEvent event) {
                switch (event.getAction()) {
                    case MotionEvent.ACTION_DOWN:
                        touchX = event.getRawX();
                        touchY = event.getRawY();
                        startX = params.x;
                        startY = params.y;
                        return true;
                    case MotionEvent.ACTION_MOVE:
                        params.x = startX + (int)(event.getRawX() - touchX);
                        params.y = startY + (int)(event.getRawY() - touchY);
                        wm.updateViewLayout(AimbotPanel.this, params);
                        return true;
                }
                return false;
            }
        });
    }
    
    private Button createToggle(String label) {
        Button btn = new Button(getContext());
        btn.setText(label + ": OFF");
        btn.setTextColor(Color.WHITE);
        btn.setBackgroundColor(Color.DKGRAY);
        btn.setOnClickListener(new OnClickListener() {
            @Override
            public void onClick(View v) {
                boolean state;
                if (label.equals("AIMBOT")) {
                    aimbotOn = !aimbotOn;
                    state = aimbotOn;
                    nativeToggleAimbot(aimbotOn ? 1 : 0);
                } else if (label.equals("DODGE")) {
                    dodgeOn = !dodgeOn;
                    state = dodgeOn;
                    nativeToggleDodge(dodgeOn ? 1 : 0);
                } else {
                    hyperOn = !hyperOn;
                    state = hyperOn;
                    nativeSetHyper(hyperOn ? 1 : 0);
                }
                btn.setText(label + ": " + (state ? "ON" : "OFF"));
                btn.setBackgroundColor(state ? Color.parseColor("#00AA00") : Color.DKGRAY);
            }
        });
        return btn;
    }
    
    public void show() {
        if (getParent() == null) {
            wm.addView(this, params);
        }
    }
    
    public void hide() {
        if (getParent() != null) {
            wm.removeView(this);
        }
    }
    
    /**
     * Static entry point - call from native hook or from game Activity.
     */
    public static void createInActivity(Activity activity) {
        activity.runOnUiThread(new Runnable() {
            @Override
            public void run() {
                if (instance != null) {
                    instance.hide();
                }
                instance = new AimbotPanel(activity);
                instance.show();
            }
        });
    }
    
    public static native void nativeToggleAimbot(int on);
    public static native void nativeToggleDodge(int on);
    public static native void nativeSetHyper(int on);
    
    static {
        System.loadLibrary("bsd_aimbot");
    }
}
