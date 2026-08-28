#!/usr/bin/env python3
"""Recreate Jas et al. 2018 Figure 5: grand-average evoked response on
sensor EEG065, famous/scrambled/unfamiliar faces.

Adapted from original_scripts/results/group_analysis/plot_group.py (fetched
verbatim). Not edited in place -- separate adapted copy, per this project's
convention. Changes from the original:
  - the dSPM and LCMV source-space sections (lines ~74-97 of the original)
    are dropped entirely -- source-space stays out of scope for this
    project. Fig 5 is sensor-only; the dropped sections would have been
    Fig 11, not Fig 5.
  - output path points at figures_jas/ instead of a relative '../figures/'.

Run once per l_freq value you want a panel for (config.l_freq controls
which grand_average file is read and the output filename/panel letter,
exactly as the original script does -- 'A' for l_freq=None, 'B' for
l_freq=1, matching the original's own `annotate('A' if l_freq is None
else 'B', ...)`).
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
from library.config import meg_dir, set_matplotlib_defaults, l_freq, tmax, annot_kwargs  # noqa: E402

OUT_DIR = HERE
os.makedirs(OUT_DIR, exist_ok=True)

fname = os.path.join(meg_dir, "grand_average_highpass-%sHz-ave.fif" % l_freq)
evokeds = mne.read_evokeds(fname)[:3]  # famous, scrambled, unfamiliar (07's save order)

idx = evokeds[0].ch_names.index("EEG065")
assert evokeds[1].ch_names[idx] == "EEG065"
assert evokeds[2].ch_names[idx] == "EEG065"
mapping = {"Famous": evokeds[0], "Scrambled": evokeds[1], "Unfamiliar": evokeds[2]}

for evoked in evokeds:
    evoked.apply_baseline(baseline=(-0.1, 0.0))

set_matplotlib_defaults()

fig, ax = plt.subplots(1, figsize=(3.3, 2.3))
scale = 1e6
ax.plot(evoked.times * 1000, mapping["Scrambled"].data[idx] * scale, "r", label="Scrambled")
ax.plot(evoked.times * 1000, mapping["Unfamiliar"].data[idx] * scale, "g", label="Unfamiliar")
ax.plot(evoked.times * 1000, mapping["Famous"].data[idx] * scale, "b", label="Famous")
ax.grid(True)
ax.set(xlim=[-100, 1000 * tmax], xlabel="Time (in ms after stimulus onset)",
       ylim=[-12.5, 5], ylabel="Potential difference (μV)")
ax.axvline(800, ls="--", color="k")
if l_freq == 1:
    ax.legend(loc="lower right")
ax.annotate("A" if l_freq is None else "B", (-0.2, 1), **annot_kwargs)
fig.tight_layout(pad=0.5)
out_path = os.path.join(OUT_DIR, "jas_fig5_grand_average_highpass-%sHz.pdf" % l_freq)
fig.savefig(out_path)
print(f"[jas_fig5] saved {out_path} (n_subjects contributing: see evokeds[0].nave={evokeds[0].nave})")
