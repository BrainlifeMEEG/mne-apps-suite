"""
Run 11-group_average_sensors.py verbatim, once, after all 16 non-excluded
subjects have 07-make_evoked output. Unlike 02/04/05/06/07/08/10, script 11
has no per-subject function to strip a batch driver from -- it's pure
top-level code that already loops over range(1, 20) and filters
exclude_subjects itself (checked: no adaptation needed there). So this
wrapper just executes the file directly, no AST surgery.

Usage: python3 run_grand_average.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ORIGINAL_SCRIPTS = os.path.normpath(os.path.join(HERE, "..", "original_scripts"))
sys.path.insert(0, ORIGINAL_SCRIPTS)
os.chdir(ORIGINAL_SCRIPTS)

path = os.path.join(ORIGINAL_SCRIPTS, "11-group_average_sensors.py")
src = open(path).read()
code = compile(src, path, "exec")
exec(code, {"__name__": "__main__", "__file__": path})
print("=== 11-group_average_sensors DONE ===")
