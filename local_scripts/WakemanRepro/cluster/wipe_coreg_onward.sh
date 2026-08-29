#!/bin/bash
# One-time cleanup after the coregistration fix (see run_subject_coreg.py's
# docstring, "Real, dataset-wide bug found and fixed here"): the original
# coregistration used the nasion fiducial + head-shape points, both of
# which sit entirely in this dataset's defaced anterior MRI region, giving
# every subject a large (tens of degrees) rotation error. Anatomy/BEM is
# untouched by this bug (upstream of coregistration) and does NOT need
# redoing -- only coreg and everything downstream of it.
#
# Usage: ./wipe_coreg_onward.sh
set -e
set -x

MEG_DIR=/network/iss/cenir/analyse/meeg/BRAINLIFE/code/local_scripts/WakemanRepro/derivatives/biomag_repro/MEG
DS117_DIR=/network/iss/cenir/analyse/meeg/BRAINLIFE/code/local_scripts/WakemanRepro/derivatives/biomag_repro/ds117

for s in 02 03 04 06 07 08 09 10 11 12 13 14 15 17 18 19; do
  sub="sub0$s"
  rm -f "$DS117_DIR/$sub/MEG/${sub}-trans.fif"
  rm -f "$MEG_DIR/$sub/${sub}-meg-eeg-oct6-fwd.fif"
  rm -f "$MEG_DIR/$sub"/mne_dSPM_inverse_highpass-*Hz-*
  rm -f "$MEG_DIR/$sub"/mne_dSPM_inverse_morph_highpass-*Hz-*
  rm -f "$MEG_DIR/$sub"/mne_LCMV_inverse_highpass-*Hz-contrast*
  rm -f "$MEG_DIR/$sub"/*-inv.fif
done

rm -f "$MEG_DIR"/contrast-average_highpass-*Hz-stc.h5
rm -f "$MEG_DIR"/contrast-average-lcmv_highpass-*Hz-{lh,rh}.stc

echo "wipe done -- rerun submit_source_space.slurm.sh (anatomy step will skip, already done), then run_group_source_average.py, then figures_jas/jas_fig{9,11,12}*.py"
