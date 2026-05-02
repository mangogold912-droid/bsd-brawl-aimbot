#!/usr/bin/env python3
"""
Patch game's main Activity smali to call AimbotPanel.createInActivity().
Finds the MAIN/LAUNCHER activity from AndroidManifest.xml and injects
AimbotPanel call at the end of onCreate().
"""
import sys
import os
import re
import xml.etree.ElementTree as ET

def find_main_activity(manifest_path):
    """Find the MAIN/LAUNCHER activity from AndroidManifest.xml using regex"""
    with open(manifest_path, 'r') as f:
        content = f.read()
    
    # First try activity-alias with targetActivity (common for Supercell games)
    alias_pattern = re.compile(
        r'<activity-alias\s+([^>]*?)>.*?<intent-filter>.*?android\.intent\.action\.MAIN.*?</intent-filter>.*?</activity-alias>',
        re.DOTALL
    )
    match = alias_pattern.search(content)
    if match:
        attrs = match.group(1)
        target_match = re.search(r'targetActivity="([^"]+)"', attrs)
        if target_match:
            return target_match.group(1)
        name_match = re.search(r'name="([^"]+)"', attrs)
        if name_match:
            return name_match.group(1)
    
    # Try activity with MAIN/LAUNCHER
    activity_pattern = re.compile(
        r'<activity\s+([^>]*?)>.*?<intent-filter>.*?android\.intent\.action\.MAIN.*?</intent-filter>.*?</activity>',
        re.DOTALL
    )
    match = activity_pattern.search(content)
    if match:
        attrs = match.group(1)
        name_match = re.search(r'name="([^"]+)"', attrs)
        if name_match:
            return name_match.group(1)
    
    # Fallback: line-by-line search
    lines = content.split('\n')
    current_activity = None
    for i, line in enumerate(lines):
        act_match = re.search(r'<activity[^>]+name="([^"]+)"', line)
        if act_match:
            current_activity = act_match.group(1)
        if 'android.intent.action.MAIN' in line and current_activity:
            for j in range(i, min(i+10, len(lines))):
                if 'android.intent.category.LAUNCHER' in lines[j]:
                    return current_activity
    
    return None

def smali_path_for_class(class_name, smali_dirs):
    """Convert class name to smali file path"""
    # com.supercell.titan.GameApp -> com/supercell/titan/GameApp.smali
    path = class_name.replace('.', '/') + '.smali'
    for smali_dir in smali_dirs:
        full = os.path.join(smali_dir, path)
        if os.path.exists(full):
            return full
    return None

def patch_oncreate(smali_path, activity_class):
    """Inject AimbotPanel.createInActivity() call before return-void in onCreate"""
    with open(smali_path, 'r') as f:
        lines = f.readlines()
    
    patched = False
    output = []
    in_oncreate = False
    return_line_idx = -1
    
    for i, line in enumerate(lines):
        # Detect onCreate start
        if re.match(r'\s*\.method.*onCreate\(Landroid/os/Bundle;\)V', line):
            in_oncreate = True
            return_line_idx = -1
            output.append(line)
            continue
        
        if in_oncreate:
            # Track last return instruction before .end method
            if line.strip().startswith('return'):
                return_line_idx = len(output)
            
            # Detect method end
            if line.strip() == '.end method':
                # Inject before the last return instruction
                if return_line_idx >= 0:
                    output.insert(return_line_idx, '\n')
                    output.insert(return_line_idx + 1, '    # BSD Aimbot - Auto-injected AimbotPanel call\n')
                    output.insert(return_line_idx + 2, '    invoke-static {p0}, Lcom/bsd/brawl/mod/AimbotPanel;->createInActivity(Landroid/app/Activity;)V\n')
                    output.insert(return_line_idx + 3, '\n')
                    print(f"Patched onCreate in {smali_path} (before return)")
                    patched = True
                else:
                    print(f"WARNING: No return found in onCreate in {smali_path}")
                
                output.append(line)
                in_oncreate = False
                continue
        
        output.append(line)
    
    if not patched:
        print(f"WARNING: Could not find onCreate in {smali_path}")
        return False
    
    with open(smali_path, 'w') as f:
        f.writelines(output)
    return True

def main():
    if len(sys.argv) < 3:
        print("Usage: patch_main_activity.py <apk_decompiled_dir> <smali_dirs_comma_separated>")
        sys.exit(1)
    
    apk_dir = sys.argv[1]
    smali_dirs = sys.argv[2].split(',')
    manifest_path = os.path.join(apk_dir, 'AndroidManifest.xml')
    
    if not os.path.exists(manifest_path):
        print(f"Manifest not found: {manifest_path}")
        sys.exit(1)
    
    main_activity = find_main_activity(manifest_path)
    if not main_activity:
        print("ERROR: Could not find MAIN/LAUNCHER activity")
        sys.exit(1)
    
    print(f"Found main activity: {main_activity}")
    
    smali_path = smali_path_for_class(main_activity, smali_dirs)
    if not smali_path:
        print(f"ERROR: Smali file not found for {main_activity}")
        print(f"Searched in: {smali_dirs}")
        sys.exit(1)
    
    print(f"Found smali: {smali_path}")
    
    if patch_oncreate(smali_path, main_activity):
        print("SUCCESS: MainActivity patched")
    else:
        print("WARNING: Could not patch onCreate")

if __name__ == '__main__':
    main()
