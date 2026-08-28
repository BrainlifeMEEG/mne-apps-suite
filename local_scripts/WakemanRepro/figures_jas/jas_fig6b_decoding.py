#!/usr/bin/env python3
"""Recreate Jas et al. 2018 Figure 6B: mean decoding AUC across time,
face-vs-scrambled and famous-vs-unfamiliar.

Adapted from original_scripts/results/statistics/plot_sliding_estimator.py
(fetched verbatim from mne-biomag-group-demo). Not edited in place -- per
this project's convention, upstream scripts stay a pristine mirror; this is
a separate adapted copy. Changes from the original:
  - subject loop skips exclude_subjects (1, 5, 16) -- neither this script
    nor 10-sliding_estimator.py itself filter them upstream, an oversight
    worth not repeating (see GLITCHES.md); those subjects were excluded by
    the dataset's own README for bad EEG data, and we never ran 10 for them.
  - output path points at this project's figures_jas/ instead of a relative
    '../figures/' assumed to sit next to the original script's own location.
  - the large per-subject 4x5 diagnostic grid (checking whether famous-vs-
    unfamiliar's noisier decoding is subject-specific) is kept as a
    secondary bonus output, not the primary figure -- 16 subjects now, not
    19, so the original's fixed 4x5/19-panel layout is resized here.
"""
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.io import loadmat
from scipy.stats import sem

HERE = os.path.dirname(os.path.abspath(__file__))
ORIGINAL_SCRIPTS = os.path.normpath(os.path.join(HERE, "..", "original_scripts"))
sys.path.insert(0, ORIGINAL_SCRIPTS)
from library.config import meg_dir, l_freq, annot_kwargs, tmax, set_matplotlib_defaults  # noqa: E402

sys.path.insert(0, os.path.join(HERE, "..", "cluster"))
from crosswalk import ALL_SUBJECT_IDS  # noqa: E402

OUT_DIR = HERE
os.makedirs(OUT_DIR, exist_ok=True)

a_vs_bs = ["face_vs_scrambled", "famous_vs_unfamiliar"]
scores = {a: [] for a in a_vs_bs}
subject_ids_used = []
times = None

for subject_id in ALL_SUBJECT_IDS:  # already excludes 1, 5, 16
    subject = "sub%03d" % subject_id
    data_path = os.path.join(meg_dir, subject)
    try:
        run_scores = {}
        for a_vs_b in a_vs_bs:
            fname_td = os.path.join(
                data_path, "%s_highpass-%sHz-td-auc-%s.mat" % (subject, l_freq, a_vs_b)
            )
            mat = loadmat(fname_td)
            run_scores[a_vs_b] = mat["scores"][0]
            times = mat["times"][0]
        for a_vs_b in a_vs_bs:
            scores[a_vs_b].append(run_scores[a_vs_b])
        subject_ids_used.append(subject_id)
    except FileNotFoundError as e:
        print(f"[jas_fig6b] WARNING: missing decoding scores for {subject}: {e}")

print(f"[jas_fig6b] {len(subject_ids_used)}/{len(ALL_SUBJECT_IDS)} subjects loaded: "
      f"{subject_ids_used}")
assert len(subject_ids_used) > 0, "no subjects' decoding scores found -- run 10 first"

mean_scores, sem_scores = {}, {}
for a_vs_b in a_vs_bs:
    mean_scores[a_vs_b] = np.mean(scores[a_vs_b], axis=0)
    sem_scores[a_vs_b] = sem(scores[a_vs_b])

set_matplotlib_defaults()
colors = ["b", "g"]
fig, ax = plt.subplots(1, figsize=(3.3, 2.5))
for c, a_vs_b in zip(colors, a_vs_bs):
    ax.plot(times, mean_scores[a_vs_b], c, label=a_vs_b.replace("_", " "))
    ax.set(xlabel="Time (s)", ylabel="Area under curve (AUC)")
    ax.fill_between(times, mean_scores[a_vs_b] - sem_scores[a_vs_b],
                    mean_scores[a_vs_b] + sem_scores[a_vs_b],
                    color=c, alpha=0.33, edgecolor="none")
ax.axhline(0.5, color="k", linestyle="--", label="Chance level")
ax.axvline(0.0, color="k", linestyle="--")
ax.legend()
ax.set(xlim=[-0.2, tmax])
ax.annotate("B", (-0.15, 1), **annot_kwargs)
fig.tight_layout(pad=0.5)
out_main = os.path.join(OUT_DIR, "jas_fig6b_decoding_highpass-%sHz.pdf" % (l_freq,))
fig.savefig(out_main, bbox_inches="tight")
print(f"[jas_fig6b] saved {out_main}")

# Secondary bonus output: per-subject grid (not part of the numbered figure)
n = len(subject_ids_used)
ncols = 5
nrows = int(np.ceil(n / ncols))
fig2, axes = plt.subplots(nrows, ncols, sharex=True, sharey=True, figsize=(7, 1.4 * nrows))
axes = np.atleast_1d(axes).ravel()
for i, subject_id in enumerate(subject_ids_used):
    axes[i].axhline(0.5, color="k", linestyle="--", label="Chance level")
    axes[i].axvline(0.0, color="k", linestyle="--")
    for a_vs_b in a_vs_bs:
        axes[i].plot(times, scores[a_vs_b][i], label=a_vs_b)
    axes[i].set_title("sub%03d" % subject_id, fontsize=8)
axes[n - 1].legend(bbox_to_anchor=(1.1, 0.75), loc="center left", fontsize=6)
for j in range(n, len(axes)):
    axes[j].axis("off")
fig2.text(0.5, 0.02, "Time (s)", ha="center", fontsize=12)
fig2.text(0.01, 0.5, "AUC", va="center", rotation="vertical", fontsize=12)
fig2.subplots_adjust(bottom=0.12, left=0.08, right=0.85, top=0.92, hspace=0.6)
out_grid = os.path.join(OUT_DIR, "jas_fig6b_decoding_per_subject.png")
fig2.savefig(out_grid, dpi=150)
print(f"[jas_fig6b] saved {out_grid}")
