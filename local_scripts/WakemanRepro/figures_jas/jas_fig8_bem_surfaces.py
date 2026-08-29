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

Uses `mne.viz.plot_bem()` directly -- draws all 3 watershed BEM surfaces
automatically from `subjects_dir/subject/bem/watershed/` through the MRI,
exactly this figure's content.

`orientation='axial'`, restricted to `slices=range(100, 220, 12)` (not the
default coronal auto-slicing across the whole volume): confirmed via
direct visual inspection (raw T1 slices, no BEM overlay) that ds000117's
T1 volumes are defaced -- a sharp, artificial straight-edged cut through
the anterior face/neck region, consistent with the dataset's own README
("Defacing of MPRAGE T1 images was performed by the submitter") and
independently corroborated by the *paper's own* Figure 9 caption: "the
anonymization of the MRI produces a mismatch between digitized points and
outer skin surface at the front of the head." That corrupted region makes
watershed's surfaces genuinely unreliable there (confirmed empirically --
swept preflood 5/15(default)/30/50 and tried gcaatlas=True, all
visually identical in the affected region, ruling out a watershed-tunable
segmentation bug -- see GLITCHES.md's "Watershed BEM neck/defacing
investigation"). Axial slices in this range stay within the cranial vault,
avoiding the neck entirely (a coronal or sagittal view can't avoid it --
the neck sits directly below the head in every such slice) and only
brushing the defaced region's edge in the lowest 1-2 slices, giving an
honest, representative view of surfaces that separate cleanly everywhere
that isn't corrupted by anonymization -- not a cosmetic crop hiding a
real bug.
"""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import mne

HERE = os.path.dirname(os.path.abspath(__file__))
ORIGINAL_SCRIPTS = os.path.normpath(os.path.join(HERE, "..", "original_scripts"))
sys.path.insert(0, ORIGINAL_SCRIPTS)
from library.config import subjects_dir  # noqa: E402

OUT_DIR = HERE
os.makedirs(OUT_DIR, exist_ok=True)

SUBJECT = "sub004"  # paper "subject 4" -- see crosswalk note above

fig = mne.viz.plot_bem(subject=SUBJECT, subjects_dir=subjects_dir,
                       orientation="axial", slices=range(100, 220, 12), show=False)
fig.suptitle(f"{SUBJECT} (paper subject 4): watershed BEM surfaces on T1")

out_path = os.path.join(OUT_DIR, f"jas_fig8_bem_surfaces_{SUBJECT}.pdf")
fig.savefig(out_path)
print(f"[jas_fig8] saved {out_path}")
