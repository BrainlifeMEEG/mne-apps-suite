#!/usr/bin/env python3
"""Recreate Jas et al. 2018 Figure 8: BEM surfaces on MRI images (inner
skull, outer skull, outer skin outlined), for subject 4.

Deviation from the paper's own Figure 8 (documented, not silently
approximated): the paper's caption specifically says "on flash MRI images"
-- FLASH multi-echo MRI isn't part of this ds000117 BIDS release (confirmed
absent, see run_subject_anatomy.py's docstring), so these are watershed-BEM
surfaces (from the plain T1.mgz) shown on the plain T1, not FLASH-derived
surfaces on a FLASH volume. The 3 outlined surfaces themselves (inner
skull/outer skull/outer skin) are the same conceptual output either way --
watershed is simply this project's substitute BEM-extraction method
throughout (see cluster/run_subject_anatomy.py), applied consistently here
too, not a one-off shortcut for this figure alone.

Subject: same "paper subject 4" = openfMRI sub004 = BIDS sub-03 crosswalk
as Figure 10 (see that script's docstring for the full chain of evidence).

Layout matches the published figure exactly (checked directly against
paper_figure8_reference.png, not assumed): 4 single-slice panels --
1 axial, 2 coronal (at different depths), 1 sagittal -- not a multi-slice
grid in one orientation. `mne.viz.plot_bem()` only draws one orientation
per call, so each panel is rendered separately (`slices=[N]`, one slice)
and composited into a single row, same pattern used for other multi-panel
figures in this project (Figs 4/11). Slice indices were picked to match
the published panels' approximate content (ventricle shape/depth), not
derived from any ground-truth coordinate -- the paper gives no numeric
slice positions.

Earlier draft restricted to axial, cranial-only slices specifically to
avoid this dataset's defaced-MRI artifact in the neck/anterior region (see
GLITCHES.md's "Watershed BEM neck/defacing investigation") -- reverted
after review: the published figure's own coronal/sagittal panels show the
*same* kind of artifact (a visible black missing-data wedge in both
coronal panels, a disconnected fragment in the sagittal panel) -- the
comparison is more honest and more useful showing the same slice types the
paper shows, defacing artifacts included, than a cleaned-up view that
dodges them.
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

OUT_DIR = HERE
os.makedirs(OUT_DIR, exist_ok=True)

SUBJECT = "sub004"  # paper "subject 4" -- see crosswalk note above

# (orientation, slice index) for each of the paper's 4 panels, left to right.
PANELS = [
    ("axial", 150),
    ("coronal", 100),
    ("coronal", 140),
    ("sagittal", 128),
]

panel_pngs = []
for i, (orientation, slice_idx) in enumerate(PANELS):
    fig = mne.viz.plot_bem(subject=SUBJECT, subjects_dir=subjects_dir,
                           orientation=orientation, slices=[slice_idx], show=False)
    png_path = os.path.join(OUT_DIR, f"_tmp_jas_fig8_panel_{i}.png")
    fig.savefig(png_path, dpi=150)
    plt.close(fig)
    panel_pngs.append(png_path)
    print(f"[jas_fig8] rendered {orientation} slice {slice_idx}")

fig, axes = plt.subplots(1, len(panel_pngs), figsize=(4 * len(panel_pngs), 4.2))
for ax, png in zip(axes, panel_pngs):
    ax.imshow(mpimg.imread(png))
    ax.axis("off")
fig.suptitle(f"{SUBJECT} (paper subject 4): watershed BEM surfaces on T1")
fig.tight_layout()

out_path = os.path.join(OUT_DIR, f"jas_fig8_bem_surfaces_{SUBJECT}.pdf")
fig.savefig(out_path)
plt.close(fig)
for p in panel_pngs:
    os.remove(p)
print(f"[jas_fig8] saved {out_path}")
