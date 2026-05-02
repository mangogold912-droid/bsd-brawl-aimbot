import ida_auto
import ida_nalt
import ida_funcs
import ida_search
import ida_bytes
import ida_name
import idautils
import idc
import ida_idaapi
import json
import os
import sys

OUTPUT_DIR = "/root/.openclaw/workspace/analysis"
LIBG_PATH = "/root/.openclaw/workspace/analysis/libg.so"
LOG_FILE = os.path.join(OUTPUT_DIR, "ida_script_log.txt")

# Redirect stdout/stderr to log file for headless mode
log_f = open(LOG_FILE, 'w')
sys.stdout = log_f
sys.stderr = log_f

def log(msg):
    print(msg)
    log_f.flush()

def wait_for_analysis():
    log("[IDA] Waiting for auto-analysis...")
    ida_auto.auto_wait()
    log("[IDA] Auto-analysis complete.")

def find_strings_and_xrefs():
    targets = [
        b"player_position",
        b"projectile_reversion", 
        b"follow_projectile",
        b"reposition_wall",
        b"projectile",
        b"position",
        b"setX",
        b"setY",
        b"getX",
        b"getY",
        b"m_position",
        b"m_x",
        b"m_y"
    ]
    
    results = {}
    
    for target in targets:
        log(f"[IDA] Searching for string: {target.decode()}")
        addr = ida_search.find_binary(0, ida_idaapi.BADADDR, target, 16, ida_search.SEARCH_UP)
        if addr == ida_idaapi.BADADDR:
            addr = ida_search.find_text(0, ida_idaapi.BADADDR, 0, target.decode(), ida_search.SEARCH_UP)
        
        if addr != ida_idaapi.BADADDR:
            str_info = {
                "address": hex(addr),
                "name": ida_name.get_name(addr),
                "xrefs": []
            }
            
            for xref in idautils.XrefsTo(addr):
                func = ida_funcs.get_func(xref.frm)
                func_addr = func.start_ea if func else xref.frm
                func_name = ida_name.get_name(func_addr) if func else "unknown"
                str_info["xrefs"].append({
                    "xref_from": hex(xref.frm),
                    "xref_type": str(xref.type),
                    "function": hex(func_addr),
                    "function_name": func_name
                })
            
            results[target.decode()] = str_info
            log(f"  Found at {hex(addr)} with {len(str_info['xrefs'])} xrefs")
        else:
            log(f"  NOT FOUND")
    
    return results

def find_position_write_patterns():
    log("[IDA] Searching for position write patterns...")
    patterns = []
    
    search_patterns = [
        ("str s0, [x0", "00 00 80 BD"),
        ("str s1, [x0", "01 00 80 BD"),
        ("str s2, [x0", "02 00 80 BD"),
        ("str w0, [x0", "00 00 80 B9"),
        ("str w1, [x0", "01 00 80 B9"),
        ("str x0, [x0", "00 00 80 F9"),
    ]
    
    for desc, pat in search_patterns:
        ea = 0
        while True:
            ea = ida_search.find_binary(ea, ida_idaapi.BADADDR, pat, 16, ida_search.SEARCH_DOWN)
            if ea == ida_idaapi.BADADDR:
                break
            
            func = ida_funcs.get_func(ea)
            if func:
                func_name = ida_name.get_name(func.start_ea)
                patterns.append({
                    "pattern": desc,
                    "address": hex(ea),
                    "function": hex(func.start_ea),
                    "function_name": func_name
                })
            ea += 4
    
    log(f"  Found {len(patterns)} position write patterns")
    return patterns

def analyze_candidate_functions():
    log("[IDA] Analyzing candidate functions...")
    candidates = []
    
    for func_addr in idautils.Functions():
        func_name = ida_name.get_name(func_addr)
        if not func_name:
            continue
        
        name_lower = func_name.lower()
        if any(kw in name_lower for kw in ['position', 'pos', 'setx', 'sety', 'getx', 'gety', 
                                              'move', 'locat', 'coord', 'projectile']):
            candidates.append({
                "address": hex(func_addr),
                "name": func_name,
                "size": ida_funcs.get_func(func_addr).size()
            })
    
    log(f"  Found {len(candidates)} candidate functions by name")
    return candidates

def main():
    log("=" * 60)
    log("IDA Pro Automated Analysis - libg.so")
    log("=" * 60)
    
    log(f"[IDA] Current file: {idc.get_input_file_path()}")
    
    wait_for_analysis()
    
    string_results = find_strings_and_xrefs()
    patterns = find_position_write_patterns()
    candidates = analyze_candidate_functions()
    
    output = {
        "strings": string_results,
        "position_patterns": patterns,
        "candidate_functions": candidates
    }
    
    output_file = os.path.join(OUTPUT_DIR, "ida_analysis_results.json")
    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2)
    
    log(f"\n[IDA] Results saved to {output_file}")
    log("[IDA] Analysis complete. Terminating...")
    
    log_f.close()
    idc.qexit(0)

if __name__ == "__main__":
    main()
