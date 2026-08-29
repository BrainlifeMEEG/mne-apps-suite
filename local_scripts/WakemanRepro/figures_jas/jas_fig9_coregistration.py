#!/usr/bin/env python3
"""Recreate Jas et al. 2018 Figure 9: MEG-to-head/head-to-MRI coregistration
result for one subject -- MEG helmet + sensors, inner skull + outer skin
surfaces, source space points, digitized fiducials (large dots), EEG
electrodes (small pink dots), extra head-shape points (small gray dots).
Three views: left, front, right (matching the published figure's own
3-panel layout, checked directly against paper_figure9_reference.png).

Uses this project's standard single-subject reference (openfMRI sub010,
BIDS sub-09, our "S09" throughout -- the only crosswalk row independently
verified against a published figure, see cluster/crosswalk.py) rather than
the paper's own unspecified "one subject" example -- the paper's caption
doesn't name which subject, so there's no crosswalk to match, and using
our own already-verified reference subject is the natural choice.

Deviation worth flagging honestly (see cluster/run_subject_coreg.py's
docstring): the trans this reads was NOT computed the way
mne-biomag-group-demo's own pipeline expects -- ds000117's BIDS release
ships no pre-existing `-trans.fif` at all (the original scripts assume one
already exists), so this project's own automated ICP coregistration was
used instead, and even that needed two real fixes (nasion + head-shape
points excluded from fitting -- both sit in this dataset's defaced MRI
region, which was pulling every subject's fit into a large, unphysical
rotation; then a second, LPA/RPA-only-fit roll ambiguity that left 7 of 16
subjects upside-down, resolved with a nasion-based sign check) -- S09
(this figure's subject) wasn't one of the affected 7, so its trans didn't
change between the two fixes, but the group-level figures (11/12) needed
both --
see run_subject_coreg.py's docstring for the full investigation). Fit
rotation angles are logged at coreg time -- this figure is the visual
complement to those numbers, not a substitute for reading them.

`mne.viz.plot_alignment()` + an offscreen pyvista screenshot (pyvista is
installed locally, confirmed -- MNE's own mayavi backend, which would have
been unavailable in this environment, was replaced by pyvista as MNE's
default 3D backend some versions ago; this project uses whatever MNE's
current default already is, not a special-cased choice).

View angles (azimuth=0/90/180 at elevation=80 -> right/front/left) were
determined empirically, not guessed: rendered all 4 cardinal azimuths and
visually matched the resulting nose/ear positions against "right"/"front"/
"left" before picking these three (`mne.viz.set_3d_view()`'s azimuth
convention isn't documented in terms of anatomical views directly).
"""
import os
import sys

os.environ.setdefault("PYVISTA_OFF_SCREEN", "true")
os.environ.setdefault("MNE_3D_BACKEND", "pyvistaqt")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import mne

HERE = os.path.dirname(os.path.abspath(__file__))
ORIGINAL_SCRIPTS = os.path.normpath(os.path.join(HERE, "..", "original_scripts"))
sys.path.insert(0, ORIGINAL_SCRIPTS)
from library.config import meg_dir, subjects_dir, study_path, l_freq, spacing  # noqa: E402

OUT_DIR = HERE
os.makedirs(OUT_DIR, exist_ok=True)

SUBJECT = "sub010"  # our "S09" (BIDS sub-09) -- see docstring

fname_ave = os.path.join(meg_dir, SUBJECT, f"{SUBJECT}_highpass-{l_freq}Hz-ave.fif")
fname_trans = os.path.join(study_path, "ds117", SUBJECT, "MEG", f"{SUBJECT}-trans.fif")
fname_src = os.path.join(subjects_dir, SUBJECT, "bem", f"{SUBJECT}-{spacing}-src.fif")

info = mne.io.read_info(fname_ave)
src = mne.read_source_spaces(fname_src)

fig = mne.viz.plot_alignment(
    info, trans=fname_trans, subject=SUBJECT, subjects_dir=subjects_dir,
    surfaces=dict(head=0.2, inner_skull=0.3), dig=True, eeg=["original"],
    meg=["helmet", "sensors"], src=src, coord_frame="mri", show_axes=False)

VIEWS = [("left", 180), ("front", 90), ("right", 0)]
panel_pngs = []
for name, az in VIEWS:
    mne.viz.set_3d_view(fig, azimuth=az, elevation=80, distance=0.6)
    png_path = os.path.join(OUT_DIR, f"_tmp_jas_fig9_{name}.png")
    fig.plotter.screenshot(png_path)
    panel_pngs.append(png_path)
    print(f"[jas_fig9] rendered {name} view (azimuth={az})")

fig2, axes = plt.subplots(1, 3, figsize=(15, 5))
for ax, png, (name, _) in zip(axes, panel_pngs, VIEWS):
    ax.imshow(mpimg.imread(png))
    ax.axis("off")
    ax.set_title(name)
fig2.suptitle(f"{SUBJECT} (our S09): coregistration")
fig2.tight_layout()

out_path = os.path.join(OUT_DIR, f"jas_fig9_coregistration_{SUBJECT}.png")
fig2.savefig(out_path, dpi=150)
plt.close(fig2)
for p in panel_pngs:
    os.remove(p)
print(f"[jas_fig9] saved {out_path}")
