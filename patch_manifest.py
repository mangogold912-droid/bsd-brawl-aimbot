import xml.etree.ElementTree as ET
import sys

def patch_manifest(manifest_path):
    tree = ET.parse(manifest_path)
    root = tree.getroot()
    
    # Android namespace
    ns = 'http://schemas.android.com/apk/res/android'
    ET.register_namespace('android', ns)
    
    # Remove unnecessary permissions that were added before
    for perm in root.findall('uses-permission'):
        name = perm.get(f'{{{ns}}}name')
        if name in ['android.permission.SYSTEM_ALERT_WINDOW', 'android.permission.FOREGROUND_SERVICE']:
            root.remove(perm)
            print(f"Removed permission: {name}")
    
    # Find application element
    app = root.find('application')
    if app is None:
        print("ERROR: No <application> found in manifest")
        sys.exit(1)
    
    # Remove previously added MainActivity and AimbotFloatingService
    for activity in app.findall('activity'):
        name = activity.get(f'{{{ns}}}name')
        if name == 'com.bsd.brawl.mod.MainActivity':
            app.remove(activity)
            print(f"Removed activity: {name}")
    
    for service in app.findall('service'):
        name = service.get(f'{{{ns}}}name')
        if name == 'com.bsd.brawl.mod.AimbotFloatingService':
            app.remove(service)
            print(f"Removed service: {name}")
    
    # Find main activity for logging
    main_activity = None
    for activity in app.findall('activity'):
        intent_filter = activity.find('intent-filter')
        if intent_filter is not None:
            for action in intent_filter.findall('action'):
                if action.get(f'{{{ns}}}name') == 'android.intent.action.MAIN':
                    main_activity = activity.get(f'{{{ns}}}name')
                    break
    
    print(f"Main activity: {main_activity}")
    
    # Write back
    tree.write(manifest_path, encoding='utf-8', xml_declaration=True)
    print("Manifest patched successfully")

if __name__ == '__main__':
    patch_manifest(sys.argv[1])
