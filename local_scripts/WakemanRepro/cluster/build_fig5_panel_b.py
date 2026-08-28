"""
Builds Jas Figure 5's panel B: grand_average_highpass-1Hz-ave.fif (11's own
group-average, forced-overwrite) + the l_freq=1 run of
figures_jas/jas_fig5_grand_average.py.

Both source files are read+exec'd verbatim (not edited in place) with
library.config.l_freq patched to 1 beforehand -- both already key off
config.l_freq for their I/O paths (11's output filename, jas_fig5's input
filename/output filename/panel-letter annotation), so no other adaptation
is needed; this is exactly the usage jas_fig5_grand_average.py's own
docstring describes ("Run once per l_freq value you want a panel for").

11's own `mne.evoked.write_evokeds()` call doesn't pass `overwrite=`
(defaults to False) -- monkeypatched here to force True, same pattern as
cluster/run_subject_lfreq1_epochs.py.

Runs entirely on already-computed per-subject evoked files (all 16
produced by cluster/run_subject_lfreq1_epochs.py) -- light plotting/
averaging, no memory-guarding needed, run directly (not via Slurm).

Usage: python3 build_fig5_panel_b.py
"""
import os
import sys

import mne
import mne.evoked  # mne's lazy loader doesn't expose submodules until imported directly

_orig_write_evokeds = mne.evoked.write_evokeds


def _write_evokeds_overwrite(fname, evoked, *, on_mismatch="raise", overwrite=False, verbose=None):
    return _orig_write_evokeds(fname, evoked, on_mismatch=on_mismatch, overwrite=True, verbose=verbose)


mne.evoked.write_evokeds = _write_evokeds_overwrite
mne.write_evokeds = _write_evokeds_overwrite

HERE = os.path.dirname(os.path.abspath(__file__))
ORIGINAL_SCRIPTS = os.path.normpath(os.path.join(HERE, "..", "original_scripts"))
FIGURES_JAS = os.path.normpath(os.path.join(HERE, "..", "figures_jas"))
sys.path.insert(0, ORIGINAL_SCRIPTS)
os.chdir(ORIGINAL_SCRIPTS)

import library.config as cfgmod
cfgmod.l_freq = 1

print("=== 11-group_average_sensors (l_freq=1) ===")
path11 = os.path.join(ORIGINAL_SCRIPTS, "11-group_average_sensors.py")
src11 = open(path11).read()
exec(compile(src11, path11, "exec"), {"__name__": "__main__", "__file__": path11})
print("=== 11-group_average_sensors DONE ===")

print("=== jas_fig5_grand_average (l_freq=1) ===")
path5 = os.path.join(FIGURES_JAS, "jas_fig5_grand_average.py")
src5 = open(path5).read()
exec(compile(src5, path5, "exec"), {"__name__": "__main__", "__file__": path5})
print("=== jas_fig5_grand_average DONE ===")
