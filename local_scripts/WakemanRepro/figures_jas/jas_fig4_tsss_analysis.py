#!/usr/bin/env python3
"""Recreate Jas et al. 2018 Figure 4: subject 3's "faces" evoked response
under three preprocessing approaches -- baseline correction (l_freq=None),
1 Hz highpass filtering instead of baseline correction (l_freq=1), and tSSS
(st_duration=1s) -- illustrating each approach's effect on slow sustained
responses.

Unlike the other figures_jas/ scripts, this one is NOT a direct adaptation
of a single upstream script. original_scripts/results/demos/plot_tsss_analysis.py
(fetched verbatim, subject-3-only) is a much broader interactive QC dump
(~15 plots: raw PSD, events, drop log, 5 per-condition evoked+topomap plots,
ICA scores/sources, whitening) for the tSSS condition alone -- it doesn't
itself build the specific 3-way comparison the paper's Figure 4 describes.
That comparison is assembled here from three separate pipeline outputs for
subject 3 (see cluster/run_subject3_extra.py for how each was produced):
  (a) l_freq=None:  sub003_highpass-NoneHz-ave.fif  (06/07 default -- 06's
      own epoching applies (None, 0) baseline correction when l_freq=None)
  (b) l_freq=1:      sub003_highpass-1Hz-ave.fif     (06/07 re-run with
      config.l_freq patched to 1 -- reuses the highpass-1Hz raw file the
      regular per-subject chain already produces for ICA input)
  (c) tSSS:          sub003-tsss_1-ave.fif            (03's from-scratch
      recompute, then 06/07's tsss=1 branch)
All three read the 'faces' evoked condition (famous+unfamiliar combined,
comment='faces', per 07-make_evoked.py's own naming) by name, not position.
"""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mne

HERE = os.path.dirname(os.path.abspath(__file__))
ORIGINAL_SCRIPTS = os.path.normpath(os.path.join(HERE, "..", "original_scripts"))
sys.path.insert(0, ORIGINAL_SCRIPTS)
from library.config import meg_dir, ylim, set_matplotlib_defaults  # noqa: E402

OUT_DIR = HERE
os.makedirs(OUT_DIR, exist_ok=True)

SUBJECT = "sub003"
data_path = os.path.join(meg_dir, SUBJECT)

conditions = [
    ("Baseline correction (l_freq=None)",
     os.path.join(data_path, f"{SUBJECT}_highpass-NoneHz-ave.fif")),
    ("1 Hz highpass (l_freq=1)",
     os.path.join(data_path, f"{SUBJECT}_highpass-1Hz-ave.fif")),
    ("tSSS (st_duration=1s)",
     os.path.join(data_path, f"{SUBJECT}-tsss_1-ave.fif")),
]

set_matplotlib_defaults()
fig, axes = plt.subplots(3, 1, figsize=(5, 8), sharex=True)

for ax, (label, fname) in zip(axes, conditions):
    if not os.path.exists(fname):
        ax.set_title(f"{label} -- MISSING: {fname}")
        print(f"[jas_fig4] WARNING: missing {fname} -- run cluster/run_subject3_extra.py first")
        continue
    faces_evo = mne.read_evokeds(fname, condition="faces")
    faces_evo.plot(spatial_colors=True, gfp=True, ylim=ylim, axes=ax, show=False)
    ax.set_title(f"{SUBJECT}: {label}")
    print(f"[jas_fig4] loaded {fname} (nave={faces_evo.nave})")

fig.tight_layout(pad=0.5)
out_path = os.path.join(OUT_DIR, "jas_fig4_tsss_analysis_sub003_faces.pdf")
fig.savefig(out_path)
print(f"[jas_fig4] saved {out_path}")
