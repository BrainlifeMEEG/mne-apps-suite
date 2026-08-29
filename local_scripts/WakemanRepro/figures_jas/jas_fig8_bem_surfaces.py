#!/usr/bin/env python3
"""Recreate Jas et al. 2018 Figure 8: BEM surfaces on MRI images (inner
skull, outer skull, outer skin outlined), for subject 4.

BEM method: a deliberate hybrid, arrived at empirically, not guessed.
- **Surfaces**: real FLASH-based BEM (`cluster/run_subject_flash_bem.py`'s
  `convert_flash_mris`/`make_flash_bem` output) -- the paper's own literal
  method, not the watershed substitute. These separate cleanly with
  realistic skull thickness, closely matching the reference's own spacing.
- **Background MRI**: plain `T1.mgz`, NOT `flash5_reg.mgz` (the volume the
  FLASH surfaces were actually extracted from). Reason: `mri_ms_fitparms`
  logs "non-equal flip_angle found ... Flip_angle is set to zero" while
  combining this subject's 5deg/30deg multi-echo acquisitions (confirmed
  on both sub004 and sub010 -- a systematic issue with how this project
  invokes it, not a one-off), so the synthesized flash5 volume looks
  visibly noisy/degraded as a background image even though it was still
  clean enough for `mri_make_bem_surfaces`'s edge-based extraction to work
  well. A direct 3-way comparison at a fixed slice (reference vs.
  watershed-on-T1 vs. FLASH-on-flash5_reg, see `jas_fig8_3way_compare.png`)
  made this obvious. Since flash5 was registered to T1.mgz's own grid
  (`fsl_rigid_register`), the FLASH surfaces line up correctly on T1.mgz
  directly -- confirmed by rendering both and comparing
  (`hybrid_flashsurf_on_t1.png` scratch render) before adopting this.
  Watershed's own surfaces (`bem/watershed_backup_preflash/*.surf`) are
  kept as a fallback; they have the same near-coincident outer_skull/
  outer_skin problem GLITCHES.md's "Watershed BEM neck/defacing
  investigation" already ruled out fixing via preflood height. Revisit the
  `mri_ms_fitparms` flip-angle issue if a truly all-FLASH figure is wanted
  later; not blocking here since the surfaces themselves are unaffected by
  which background they're drawn on.

Panels: all 4 coronal, posterior to anterior, at slices=[54, 87, 114, 141]
-- found empirically via `jas_fig8_slice_search_watershed.py` (sweep +
normalized-sum-of-squares match against each reference panel, against
T1.mgz renders -- every panel's score curve has a single clean interior
minimum, not a boundary artifact). Panel 1's match (slice 54) looks axial
by eye (round, no neck/jaw visible) but is a real coronal slice far enough
posterior that the plane simply doesn't intersect the neck -- same
geometric reason an axial slice near the vertex looks similar.

Subject: same "paper subject 4" = openfMRI sub004 = BIDS sub-03 crosswalk
as Figure 10 (see that script's docstring for the full chain of evidence).

`mne.viz.plot_bem()` only draws one orientation/slice per call, so each
panel is rendered separately and composited into a single row, same
pattern used for other multi-panel figures in this project (Figs 4/11).

The published figure's own panels show this dataset's defacing artifact
too (a visible black missing-data wedge in the more anterior coronal
panels) -- showing the same slice types with the same imperfections is a
more honest, more useful comparison than a cleaned-up view that dodges it.
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
T1 = os.path.join(subjects_dir, SUBJECT, "mri", "T1.mgz")

# Coronal slice indices for the paper's 4 panels, left to right, posterior
# to anterior -- found empirically via jas_fig8_slice_search_watershed.py
# (see docstring), not guessed.
SLICES = [54, 87, 114, 141]

panel_pngs = []
for i, slice_idx in enumerate(SLICES):
    fig = mne.viz.plot_bem(subject=SUBJECT, subjects_dir=subjects_dir,
                           orientation="coronal", slices=[slice_idx], mri=T1, show=False)
    png_path = os.path.join(OUT_DIR, f"_tmp_jas_fig8_panel_{i}.png")
    fig.savefig(png_path, dpi=150)
    plt.close(fig)
    panel_pngs.append(png_path)
    print(f"[jas_fig8] rendered coronal slice {slice_idx}")

fig, axes = plt.subplots(1, len(panel_pngs), figsize=(4 * len(panel_pngs), 4.2))
for ax, png in zip(axes, panel_pngs):
    ax.imshow(mpimg.imread(png))
    ax.axis("off")
fig.suptitle(f"{SUBJECT} (paper subject 4): FLASH BEM surfaces on T1")
fig.tight_layout()

out_path = os.path.join(OUT_DIR, f"jas_fig8_bem_surfaces_{SUBJECT}.pdf")
fig.savefig(out_path)
plt.close(fig)
for p in panel_pngs:
    os.remove(p)
print(f"[jas_fig8] saved {out_path}")
