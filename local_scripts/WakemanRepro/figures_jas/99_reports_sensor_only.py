#!/usr/bin/env python3
"""Sensor-only adaptation of original_scripts/99-make_reports.py.

Not edited in place -- separate file, per this project's convention (see
GLITCHES.md, "Crosswalk cross-check" section's naming precedent and the
Phase 7 plan). Source-space stays deferred project-wide, so this drops:
  - `from mayavi import mlab` (the whole original script fails to even
    import without mayavi, confirmed missing -- see GLITCHES.md)
  - the coregistration `plot_trans`/`mlab.gcf()` panel (needs a
    `<subject>-trans.fif` we don't have -- coregistration is source-space
    setup)
  - the per-condition `stc.plot()` source-estimate loop (needs inverse
    solutions we don't have)
  - the group report's dSPM/LCMV brain plots, same reason

Kept and modernized:
  - per-subject evoked butterfly+GFP plots (famous/unfamiliar/scrambled)
  - the EEG065 plot_compare_evokeds panel -- fixed from the original's
    EEG070 (its own docstring/actual channel mismatch, same EEG065-vs-070
    inconsistency already noted for 09-time_frequency.py in GLITCHES.md;
    EEG065 is what's actually used everywhere else in this pipeline)
  - deprecated `rep.add_figs_to_section`/`rep._add_figs_to_section` ->
    current `Report.add_figure()` (checked its real signature first, see
    Phase 7 plan)

Two more things fixed here, not just API-modernized:
  - `make_report(subject_id)` was DEFINED but never actually CALLED anywhere
    in the original script -- dead code, confirmed by reading the full file.
    This version actually calls it, for every non-excluded subject.
  - the group report read `eeg_faces_highpass-%sHz-ave.fif` /
    `eeg_scrambled-ave.fif`, filenames that don't match anything this
    pipeline's 07/11 actually produce (`grand_average_highpass-%sHz-ave.fif`,
    read by condition name). Fixed to read the real file.

Usage: python3 99_reports_sensor_only.py
"""
import os
import sys

import mne
from mne import Report

HERE = os.path.dirname(os.path.abspath(__file__))
ORIGINAL_SCRIPTS = os.path.normpath(os.path.join(HERE, "..", "original_scripts"))
sys.path.insert(0, ORIGINAL_SCRIPTS)
from library.config import meg_dir, l_freq, exclude_subjects  # noqa: E402

sys.path.insert(0, os.path.join(HERE, "..", "cluster"))
from crosswalk import ALL_SUBJECT_IDS  # noqa: E402

OUT_DIR = HERE
os.makedirs(OUT_DIR, exist_ok=True)


def make_report(subject_id):
    subject = "sub%03d" % subject_id
    print(f"[99_sensor] processing {subject}")

    meg_path = os.path.join(meg_dir, subject)
    ave_fname = os.path.join(meg_path, "%s_highpass-%sHz-ave.fif" % (subject, l_freq))
    if not os.path.exists(ave_fname):
        print(f"[99_sensor] WARNING: no evoked file for {subject}, skipping")
        return

    rep = Report(info_fname=ave_fname, subject=subject, title=f"{subject} sensor report")

    fam, scramb, unfam = mne.read_evokeds(ave_fname)[:3]

    rep.add_figure(fam.plot(spatial_colors=True, show=False, gfp=True),
                   title="Famous faces", section="evoked")
    rep.add_figure(unfam.plot(spatial_colors=True, show=False, gfp=True),
                   title="Unfamiliar faces", section="evoked")
    rep.add_figure(scramb.plot(spatial_colors=True, show=False, gfp=True),
                   title="Scrambled faces", section="evoked")

    if "EEG065" in fam.ch_names:
        idx = fam.ch_names.index("EEG065")
        fig = mne.viz.plot_compare_evokeds(
            {"Famous": fam, "Unfamiliar": unfam, "Scrambled": scramb}, idx, show=False)
        rep.add_figure(fig, title="Famous, unfamiliar and scrambled faces on EEG065",
                       section="evoked")

    out_path = os.path.join(OUT_DIR, f"report_sensor_{subject}.html")
    rep.save(fname=out_path, open_browser=False, overwrite=True)
    print(f"[99_sensor] saved {out_path}")


for subject_id in ALL_SUBJECT_IDS:  # already excludes 1, 5, 16
    make_report(subject_id)

###############################################################################
# Group report

faces_fname = os.path.join(meg_dir, "grand_average_highpass-%sHz-ave.fif" % l_freq)
if os.path.exists(faces_fname):
    rep = Report(info_fname=faces_fname, subject="fsaverage",
                title="Group sensor report")
    famous, scrambled, unfamiliar = mne.read_evokeds(faces_fname)[:3]
    rep.add_figure(famous.plot(spatial_colors=True, gfp=True, show=False),
                   title="Average famous", section="grand_average")
    rep.add_figure(scrambled.plot(spatial_colors=True, gfp=True, show=False),
                   title="Average scrambled", section="grand_average")
    rep.add_figure(unfamiliar.plot(spatial_colors=True, gfp=True, show=False),
                   title="Average unfamiliar", section="grand_average")

    group_out = os.path.join(OUT_DIR, "report_sensor_average.html")
    rep.save(fname=group_out, open_browser=False, overwrite=True)
    print(f"[99_sensor] saved {group_out}")
else:
    print(f"[99_sensor] WARNING: no grand average file at {faces_fname} -- "
          f"run cluster/run_grand_average.py first. Skipping group report.")
