package com.bsd.brawl.mod;

import android.app.Service;
import android.content.Intent;
import android.graphics.Color;
import android.graphics.PixelFormat;
import android.os.IBinder;
import android.view.Gravity;
import android.view.MotionEvent;
import android.view.View;
import android.view.WindowManager;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;

public class AimbotFloatingService extends Service {
    private WindowManager windowManager;
    private LinearLayout rootLayout;
    private boolean isAimbotOn = true;
    private boolean isDodgebotOn = true;
    private boolean isHyperchargeOn = false;

    static { System.loadLibrary("bsd_aimbot"); }
    public native void toggleAimbot(boolean enabled);
    public native void toggleDodgebot(boolean enabled);
    public native void setHypercharge(boolean active);

    @Override
    public void onCreate() {
        super.onCreate();
        setupFloatingUI();
    }

    private void setupFloatingUI() {
        windowManager = (WindowManager) getSystemService(WINDOW_SERVICE);
        rootLayout = new LinearLayout(this);
        rootLayout.setOrientation(LinearLayout.VERTICAL);
        rootLayout.setBackgroundColor(Color.parseColor("#EE000000"));
        rootLayout.setPadding(25, 25, 25, 25);

        TextView title = new TextView(this);
        title.setText("COLT GOD MODE V2");
        title.setTextColor(Color.parseColor("#FFD700"));
        title.setTextSize(16);
        title.setGravity(Gravity.CENTER);
        title.setPadding(0, 0, 0, 15);
        rootLayout.addView(title);

        final Button aimBtn = createMenuButton("AIMBOT: ON", true);
        aimBtn.setOnClickListener(v -> {
            isAimbotOn = !isAimbotOn;
            toggleAimbot(isAimbotOn);
            updateBtn(aimBtn, "AIMBOT", isAimbotOn);
        });
        rootLayout.addView(aimBtn);

        final Button dodgeBtn = createMenuButton("DODGEBOT: ON", true);
        dodgeBtn.setOnClickListener(v -> {
            isDodgebotOn = !isDodgebotOn;
            toggleDodgebot(isDodgebotOn);
            updateBtn(dodgeBtn, "DODGEBOT", isDodgebotOn);
        });
        rootLayout.addView(dodgeBtn);

        final Button hyperBtn = createMenuButton("HYPERCHARGE: OFF", false);
        hyperBtn.setOnClickListener(v -> {
            isHyperchargeOn = !isHyperchargeOn;
            setHypercharge(isHyperchargeOn);
            updateBtn(hyperBtn, "HYPERCHARGE", isHyperchargeOn);
            hyperBtn.setTextColor(isHyperchargeOn ? Color.parseColor("#FF00FF") : Color.GRAY);
        });
        rootLayout.addView(hyperBtn);

        WindowManager.LayoutParams params = new WindowManager.LayoutParams(
                WindowManager.LayoutParams.WRAP_CONTENT,
                WindowManager.LayoutParams.WRAP_CONTENT,
                WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE,
                PixelFormat.TRANSLUCENT);
        params.gravity = Gravity.TOP | Gravity.START;
        params.x = 150;
        params.y = 150;

        rootLayout.setOnTouchListener(new View.OnTouchListener() {
            private int initialX, initialY;
            private float initialTouchX, initialTouchY;
            @Override
            public boolean onTouch(View v, MotionEvent event) {
                switch (event.getAction()) {
                    case MotionEvent.ACTION_DOWN:
                        initialX = params.x; initialY = params.y;
                        initialTouchX = event.getRawX(); initialTouchY = event.getRawY();
                        return true;
                    case MotionEvent.ACTION_MOVE:
                        params.x = initialX + (int) (event.getRawX() - initialTouchX);
                        params.y = initialY + (int) (event.getRawY() - initialTouchY);
                        windowManager.updateViewLayout(rootLayout, params);
                        return true;
                }
                return false;
            }
        });

        windowManager.addView(rootLayout, params);
    }

    private Button createMenuButton(String text, boolean active) {
        Button btn = new Button(this);
        btn.setText(text);
        btn.setTextColor(active ? Color.GREEN : Color.RED);
        btn.setBackgroundColor(Color.parseColor("#333333"));
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(-1, -2);
        lp.setMargins(0, 10, 0, 0);
        btn.setLayoutParams(lp);
        btn.setAllCaps(false);
        return btn;
    }

    private void updateBtn(Button btn, String label, boolean on) {
        btn.setText(label + ": " + (on ? "ON" : "OFF"));
        btn.setTextColor(on ? Color.GREEN : Color.RED);
    }

    @Override
    public IBinder onBind(Intent intent) { return null; }

    @Override
    public void onDestroy() {
        super.onDestroy();
        if (rootLayout != null) windowManager.removeView(rootLayout);
    }
}
