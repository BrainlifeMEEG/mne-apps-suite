#!/usr/bin/env python3
"""Renders a contact sheet of coronal BEM-contour slices at native scale,
undistorted, for direct visual slice-matching against Figure 8's reference
panels -- the method that actually worked, after three automated proxies
(`jas_fig8_slice_search.py`, `_watershed.py`, `_shape.py`, `_combined.py`)
each failed in a different way. See GLITCHES.md's "Figure 8 slice
matching: four attempts" section for the full story; short version:

1. Whole-panel grayscale SSD is dominated by gyral texture and can't
   reliably tell "neck visible" from "not" (a thin, low-area feature).
2. Binary silhouette + Dice overlap fixes that in principle, but requires
   crop+resize-to-a-common-shape first, which throws away real relative
   head-size information (a small posterior slice's silhouette gets
   blown up to fill the same frame as a much bigger mid-head slice) --
   user caught this directly ("the images aren't aligned").
3. Combining Dice-like aspect-ratio matching with SSD by rank-sum still
   picked degenerate near-empty slices at the sweep's edges for the two
   hardest panels (1 and 4).

This script doesn't try to fix the metric a fourth time. It renders every
candidate slice at MNE's own native, undistorted scale (no per-slice
crop/resize at all -- directly comparable to every other candidate AND,
after visual side-by-side placement, to the reference panels), and slice
selection is done by looking at the result, same as picking a channel or
a time window would be. The final indices used in `jas_fig8_bem_surfaces.py`
were confirmed this way, then sanity-checked with a size-fraction
side-by-side (largest-connected-component bounding box vs. the matching
reference panel, both native scale) for panel 1's specific "closed round
shape, no neck" criterion.

Usage: adjust INDICES/step for a finer/coarser sweep, run, open the PNG.
"""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import mne

HERE = os.path.dirname(os.path.abspath(__file__))
ORIGINAL_SCRIPTS = os.path.normpath(os.path.join(HERE, "..", "original_scripts"))
sys.path.insert(0, ORIGINAL_SCRIPTS)
from library.config import subjects_dir  # noqa: E402

SUBJECT = "sub004"
T1 = os.path.join(subjects_dir, SUBJECT, "mri", "T1.mgz")

INDICES = list(range(15, 241, 6))
NCOLS = 8

TMP_PNG = os.path.join(HERE, "_tmp_contact_sheet_panel.png")

nrows = (len(INDICES) + NCOLS - 1) // NCOLS
fig, axes = plt.subplots(nrows, NCOLS, figsize=(NCOLS * 2.2, nrows * 2.4))
axes = axes.flatten()
for ax, idx in zip(axes, INDICES):
    f = mne.viz.plot_bem(subject=SUBJECT, subjects_dir=subjects_dir, orientation="coronal",
                         slices=[idx], mri=T1, show_indices=False, show_orientation=False, show=False)
    f.savefig(TMP_PNG, dpi=80)
    plt.close(f)
    ax.imshow(mpimg.imread(TMP_PNG))
    ax.axis("off")
    ax.set_title(str(idx), fontsize=9)
for ax in axes[len(INDICES):]:
    ax.axis("off")
fig.tight_layout()
out_path = os.path.join(HERE, "jas_fig8_slice_contact_sheet.png")
fig.savefig(out_path, dpi=110)
os.remove(TMP_PNG)
print(f"saved {out_path}")
