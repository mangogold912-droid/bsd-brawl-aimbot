import xml.etree.ElementTree as ET
import sys

def patch_manifest(manifest_path):
    tree = ET.parse(manifest_path)
    root = tree.getroot()
    
    # Android namespace
    ns = 'http://schemas.android.com/apk/res/android'
    ET.register_namespace('android', ns)
    
    # Add permissions
    existing_perms = [p.get(f'{{{ns}}}name') for p in root.findall('uses-permission')]
    
    if 'android.permission.SYSTEM_ALERT_WINDOW' not in existing_perms:
        perm1 = ET.SubElement(root, 'uses-permission')
        perm1.set(f'{{{ns}}}name', 'android.permission.SYSTEM_ALERT_WINDOW')
    
    if 'android.permission.FOREGROUND_SERVICE' not in existing_perms:
        perm2 = ET.SubElement(root, 'uses-permission')
        perm2.set(f'{{{ns}}}name', 'android.permission.FOREGROUND_SERVICE')
    
    # Find application element
    app = root.find('application')
    if app is None:
        print("ERROR: No <application> found in manifest")
        sys.exit(1)
    
    # Add MainActivity
    existing_activities = [a.get(f'{{{ns}}}name') for a in app.findall('activity')]
    if 'com.bsd.brawl.mod.MainActivity' not in existing_activities:
        activity = ET.SubElement(app, 'activity')
        activity.set(f'{{{ns}}}name', 'com.bsd.brawl.mod.MainActivity')
        activity.set(f'{{{ns}}}exported', 'true')
        
        intent_filter = ET.SubElement(activity, 'intent-filter')
        action = ET.SubElement(intent_filter, 'action')
        action.set(f'{{{ns}}}name', 'android.intent.action.MAIN')
        category = ET.SubElement(intent_filter, 'category')
        category.set(f'{{{ns}}}name', 'android.intent.category.LAUNCHER')
    
    # Add AimbotFloatingService
    existing_services = [s.get(f'{{{ns}}}name') for s in app.findall('service')]
    if 'com.bsd.brawl.mod.AimbotFloatingService' not in existing_services:
        service = ET.SubElement(app, 'service')
        service.set(f'{{{ns}}}name', 'com.bsd.brawl.mod.AimbotFloatingService')
        service.set(f'{{{ns}}}enabled', 'true')
        service.set(f'{{{ns}}}exported', 'false')
        service.set(f'{{{ns}}}foregroundServiceType', 'specialUse')
    
    # Write back
    tree.write(manifest_path, encoding='utf-8', xml_declaration=True)
    print("Manifest patched successfully")

if __name__ == '__main__':
    patch_manifest(sys.argv[1])
