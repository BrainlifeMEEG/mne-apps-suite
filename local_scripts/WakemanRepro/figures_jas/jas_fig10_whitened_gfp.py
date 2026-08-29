#!/usr/bin/env python3
"""Recreate Jas et al. 2018 Figure 10: whitened MEG data + GFP (global
field power) for subject 4, illustrating whether the noise covariance
properly whitens the data (GFP should follow a chi-squared distribution
around the dashed reference lines if so).

Paper caption doesn't specify which evoked condition -- used 'faces' (the
combined faces average, 07-make_evoked.py's condition 4 of 7): the most
generic, representative single evoked available, consistent with the
figure's own framing as a general noise-covariance-quality check rather
than a condition-specific result.

Subject crosswalk (checked, not assumed -- this exact kind of paper-index
vs. our own numbering mismatch bit Figures 4/5 earlier in this project):
paper "subject 4" -> config.py's `map_subjects[4]` = W&H `subject_05` ->
per ds000117's own README crosswalk table -> openfMRI **sub004** -> BIDS
**sub-03**. Cross-checked against three independent sources (config.py,
the dataset's own README table, and cluster/crosswalk.py's openfMRI->BIDS
dict) -- all three agree. NOT the naive "subject 4 = our sub004" guess
that happens to coincide here (it doesn't for e.g. paper "subject 10",
which is openfMRI subject 10, not sub010 -- see crosswalk.py).

Uses `Evoked.plot_white(noise_cov)` directly -- MNE's own built-in
reproduction of exactly this plot (whitened butterfly + GFP with the
expected-value reference lines), no custom plotting needed.

Restricted to MEG channels (`evoked.pick("meg")` before plotting) --
`plot_white()` has no `picks` kwarg of its own, it plots every channel
type present in the evoked object as its own row. The paper's own Figure
10 caption says "Whitened MEG data" -- EEG isn't part of it at all. Also
sidesteps a real, separately-confirmed data-quality issue: the unrestricted
plot's EEG row shows an obvious large frontal deflection around 1-1.5s,
consistent with an unremoved blink -- worth noting as evidence of
imperfect preprocessing in this reproduction (or upstream), but out of
scope to chase down per-subject for a figure the paper itself never showed
in EEG to begin with.
"""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import mne

HERE = os.path.dirname(os.path.abspath(__file__))
ORIGINAL_SCRIPTS = os.path.normpath(os.path.join(HERE, "..", "original_scripts"))
sys.path.insert(0, ORIGINAL_SCRIPTS)
from library.config import meg_dir, l_freq, set_matplotlib_defaults  # noqa: E402

OUT_DIR = HERE
os.makedirs(OUT_DIR, exist_ok=True)

SUBJECT = "sub004"  # paper "subject 4" -- see crosswalk note above
data_path = os.path.join(meg_dir, SUBJECT)

fname_ave = os.path.join(data_path, f"{SUBJECT}_highpass-{l_freq}Hz-ave.fif")
fname_cov = os.path.join(data_path, f"{SUBJECT}_highpass-{l_freq}Hz-cov.fif")

set_matplotlib_defaults()
evoked = mne.read_evokeds(fname_ave, condition="faces")
evoked.pick("meg")  # paper Figure 10 is MEG only -- see docstring
noise_cov = mne.read_cov(fname_cov)

fig = evoked.plot_white(noise_cov, show=False)
fig.suptitle(f"{SUBJECT} (paper subject 4): whitened faces evoked (MEG) + GFP")

out_path = os.path.join(OUT_DIR, f"jas_fig10_whitened_gfp_{SUBJECT}.pdf")
fig.savefig(out_path)
print(f"[jas_fig10] saved {out_path}")
