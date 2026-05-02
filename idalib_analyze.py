#!/usr/bin/env python3
"""Headless IDA analysis using idalib (idapro package) for libg.so."""

import os
import sys
import json

# Set IDA directory for idapro
os.environ["IDADIR"] = "/opt/ida-pro"

import idapro

# Enable console messages
idapro.enable_console_messages(True)

LIBG_PATH = "/root/.openclaw/workspace/analysis/libg.so"
OUTPUT_DIR = "/root/.openclaw/workspace/analysis"

def main():
    print(f"[idalib] Opening database: {LIBG_PATH}")
    
    # Open database with auto-analysis
    ret = idapro.open_database(LIBG_PATH, run_auto_analysis=True)
    if ret != 0:
        print(f"[idalib] Failed to open database, return code: {ret}")
        return
    
    print("[idalib] Database opened and analysis complete.")
    
    # Now we can use IDAPython modules
    import ida_auto
    import ida_funcs
    import ida_search
    import ida_name
    import idautils
    import idc
    import ida_idaapi
    import ida_bytes
    
    # --- Find target strings and xrefs ---
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
    
    string_results = {}
    
    for target in targets:
        print(f"[idalib] Searching for string: {target.decode()}")
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
            
            string_results[target.decode()] = str_info
            print(f"  Found at {hex(addr)} with {len(str_info['xrefs'])} xrefs")
        else:
            print(f"  NOT FOUND")
    
    # --- Search for position write patterns ---
    print("[idalib] Searching for position write patterns...")
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
    
    print(f"  Found {len(patterns)} position write patterns")
    
    # --- Find candidate functions by name ---
    print("[idalib] Analyzing candidate functions...")
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
    
    print(f"  Found {len(candidates)} candidate functions by name")
    
    # --- Find functions that store floats to structure offsets ---
    print("[idalib] Looking for vector/math functions with float stores...")
    vector_funcs = []
    
    for func_addr in idautils.Functions():
        func = ida_funcs.get_func(func_addr)
        if not func or func.size() > 500:  # Focus on smaller getter/setter functions
            continue
        
        # Check if function contains float store instructions
        contains_float_store = False
        for head in idautils.FuncItems(func_addr):
            insn = idc.print_insn_mnem(head)
            if insn and 'str' in insn.lower():
                opnd = idc.print_operand(head, 0)
                if opnd and opnd.startswith('s'):
                    contains_float_store = True
                    break
        
        if contains_float_store:
            func_name = ida_name.get_name(func_addr)
            vector_funcs.append({
                "address": hex(func_addr),
                "name": func_name,
                "size": func.size()
            })
    
    print(f"  Found {len(vector_funcs)} functions with float stores")
    
    # --- Save results ---
    output = {
        "strings": string_results,
        "position_patterns": patterns,
        "candidate_functions": candidates,
        "vector_functions": vector_funcs
    }
    
    output_file = os.path.join(OUTPUT_DIR, "ida_idalib_results.json")
    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\n[idalib] Results saved to {output_file}")
    
    # Close database
    idapro.close_database(save=True)
    print("[idalib] Database closed. Analysis complete.")

if __name__ == "__main__":
    main()
