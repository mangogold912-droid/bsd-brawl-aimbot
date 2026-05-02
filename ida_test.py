import idc
import os

log_file = "/root/.openclaw/workspace/analysis/ida_test_log.txt"
with open(log_file, 'w') as f:
    f.write(f"IDA Test Script Running\n")
    f.write(f"Input file: {idc.get_input_file_path()}\n")
    f.write(f"IDA is working!\n")
    f.flush()

idc.qexit(0)
