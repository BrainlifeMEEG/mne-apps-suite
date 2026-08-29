#!/bin/bash
# One-time cleanup after the watershed BEM preflood-height fix (see
# GLITCHES.md's "Watershed BEM preflood fix" section): the original
# watershed run (default preflood) produced malformed surfaces --
# outer skull/skin nearly coincident and extending down the whole neck,
# inner skull too close to the skin, brain surface too large. Everything
# downstream of anatomy (coreg's head.fif, forward, inverse, LCMV, group
# averages) was built on top of those bad surfaces and needs a full redo,
# not just the anatomy step itself.
#
# Does NOT touch: mri/{T1,aseg}.mgz, surf/*, label/* (untouched source
# data, not regenerated), mri/transforms/talairach.xfm (unrelated to
# watershed, doesn't need redoing), fsaverage (morph target, untouched).
#
# Usage: ./wipe_source_space_outputs.sh
set -e
set -x

SUBJECTS_DIR=/network/iss/cenir/analyse/meeg/BRAINLIFE/code/local_scripts/WakemanRepro/derivatives/biomag_repro/subjects
MEG_DIR=/network/iss/cenir/analyse/meeg/BRAINLIFE/code/local_scripts/WakemanRepro/derivatives/biomag_repro/MEG
DS117_DIR=/network/iss/cenir/analyse/meeg/BRAINLIFE/code/local_scripts/WakemanRepro/derivatives/biomag_repro/ds117

for s in 02 03 04 06 07 08 09 10 11 12 13 14 15 17 18 19; do
  sub="sub0$s"
  # anatomy: BEM (watershed surfaces, model, solution, head.fif) + source space
  rm -rf "$SUBJECTS_DIR/$sub/bem"
  mkdir -p "$SUBJECTS_DIR/$sub/bem"
  # coreg: trans file
  rm -f "$DS117_DIR/$sub/MEG/${sub}-trans.fif"
  # forward / inverse / lcmv
  rm -f "$MEG_DIR/$sub/${sub}-meg-eeg-oct6-fwd.fif"
  rm -f "$MEG_DIR/$sub"/mne_dSPM_inverse_highpass-*Hz-*
  rm -f "$MEG_DIR/$sub"/mne_dSPM_inverse_morph_highpass-*Hz-*
  rm -f "$MEG_DIR/$sub"/mne_LCMV_inverse_highpass-*Hz-contrast*
  rm -f "$MEG_DIR/$sub"/*-inv.fif
done

# group averages
rm -f "$MEG_DIR"/contrast-average_highpass-*Hz-stc.h5
rm -f "$MEG_DIR"/contrast-average-lcmv_highpass-*Hz-{lh,rh}.stc

echo "wipe done -- rerun submit_source_space.slurm.sh, then run_group_source_average.py, then figures_jas/jas_fig{8,9,11,12}*.py"
