#!/usr/bin/env python3
"""Recreate Jas et al. 2018 Figure 9: MEG-to-head/head-to-MRI coregistration
result for one subject -- MEG helmet + sensors, inner skull + outer skin
surfaces, digitized fiducials (large dots), EEG electrodes (small pink
dots), extra head-shape points (small gray dots).

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
used instead. Final head-shape<->MRI point distances were logged at
coreg time (mean/median/max, see GLITCHES.md) -- this figure is the visual
complement to those numbers, not a substitute for reading them: a
low-numbers-but-bad-picture (or vice versa) would both be worth noticing.

`mne.viz.plot_alignment()` + an offscreen pyvista screenshot (pyvista is
installed locally, confirmed -- MNE's own mayavi backend, which would have
been unavailable in this environment, was replaced by pyvista as MNE's
default 3D backend some versions ago; this project uses whatever MNE's
current default already is, not a special-cased choice).
"""
import os
import sys

os.environ.setdefault("PYVISTA_OFF_SCREEN", "true")
os.environ.setdefault("MNE_3D_BACKEND", "pyvistaqt")

import mne

HERE = os.path.dirname(os.path.abspath(__file__))
ORIGINAL_SCRIPTS = os.path.normpath(os.path.join(HERE, "..", "original_scripts"))
sys.path.insert(0, ORIGINAL_SCRIPTS)
from library.config import meg_dir, subjects_dir, study_path, l_freq  # noqa: E402

OUT_DIR = HERE
os.makedirs(OUT_DIR, exist_ok=True)

SUBJECT = "sub010"  # our "S09" (BIDS sub-09) -- see docstring

fname_ave = os.path.join(meg_dir, SUBJECT, f"{SUBJECT}_highpass-{l_freq}Hz-ave.fif")
fname_trans = os.path.join(study_path, "ds117", SUBJECT, "MEG", f"{SUBJECT}-trans.fif")

info = mne.io.read_info(fname_ave)

fig = mne.viz.plot_alignment(
    info, trans=fname_trans, subject=SUBJECT, subjects_dir=subjects_dir,
    surfaces=["head", "inner_skull"], dig=True, eeg=["original"],
    meg=["helmet", "sensors"], coord_frame="mri", show_axes=False)

# Real bug, not a coreg problem: setting `camera_position = "yz"` (a preset)
# and THEN mutating `.azimuth`/`.elevation` on top of it compounds two
# different, not-obviously-composable rotation conventions -- produced a
# picture where the head looked tilted forward and the helmet tilted
# backward relative to it (flagged in review). `mne.viz.set_3d_view()` is
# MNE's own well-defined, documented view-setting helper (absolute
# azimuth/elevation in a single consistent convention) -- confirmed via a
# side-by-side render with no camera changes at all that the underlying
# coregistration itself is fine (helmet follows the head normally, no
# gross mismatch); this was purely a camera-framing bug.
mne.viz.set_3d_view(fig, azimuth=180, elevation=80, distance=0.6)

out_path = os.path.join(OUT_DIR, f"jas_fig9_coregistration_{SUBJECT}.png")
fig.plotter.screenshot(out_path)
print(f"[jas_fig9] saved {out_path}")
