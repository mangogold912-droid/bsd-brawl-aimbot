package com.bsd.brawl.mod;

import android.app.Activity;
import android.content.Intent;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.provider.Settings;
import android.widget.Button;
import android.widget.Toast;

public class MainActivity extends Activity {
    private static final int REQUEST_OVERLAY_PERMISSION = 1001;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        
        // Check overlay permission
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            if (!Settings.canDrawOverlays(this)) {
                Intent intent = new Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                        Uri.parse("package:" + getPackageName()));
                startActivityForResult(intent, REQUEST_OVERLAY_PERMISSION);
                return;
            }
        }
        
        startModService();
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        if (requestCode == REQUEST_OVERLAY_PERMISSION) {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                if (Settings.canDrawOverlays(this)) {
                    startModService();
                } else {
                    Toast.makeText(this, "Overlay permission required for floating button", Toast.LENGTH_LONG).show();
                    finish();
                }
            }
        }
    }

    private void startModService() {
        // Start floating service
        Intent serviceIntent = new Intent(this, AimbotFloatingService.class);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(serviceIntent);
        } else {
            startService(serviceIntent);
        }
        
        Toast.makeText(this, "BSD Brawl Mod - Colt Enhanced Active", Toast.LENGTH_LONG).show();
        finish();  // Close activity, keep service running
    }
}
