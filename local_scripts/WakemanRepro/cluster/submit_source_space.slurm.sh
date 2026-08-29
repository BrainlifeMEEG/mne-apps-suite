#!/bin/bash
#SBATCH --job-name=biomag_source
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=16G
#SBATCH --time=01:30:00
#SBATCH --array=2,3,4,6,7,8,9,10,11,12,13,14,15,17,18,19
#SBATCH --output=/network/iss/cenir/analyse/meeg/BRAINLIFE/code/local_scripts/WakemanRepro/cluster/logs/source_%a.out
#SBATCH --error=/network/iss/cenir/analyse/meeg/BRAINLIFE/code/local_scripts/WakemanRepro/cluster/logs/source_%a.err
#
# Figures 8/9/11/12's per-subject source-space chain: anatomy (watershed BEM
# + 1-layer BEM solution + oct6 source space) -> coregistration (automated
# ICP -trans.fif) -> forward + dSPM inverse -> LCMV. One Slurm array task per
# subject. Run cluster/setup_fsaverage.py once BEFORE this array (fsaverage
# target needed by nothing in this array, but by run_group_source_average.py
# afterward -- fine either order, just needs to exist before that step).
#
# ── BEFORE running the full array ────────────────────────────────────────
# Smoke-tested on openfMRI subject_id 10 (BIDS sub-09, our "S09") first --
# see GLITCHES.md's source-space section for what broke and got fixed
# (subjects_dir rebuilt as file-level symlinks so BEM/coreg/source-space
# writes don't land in the shared ds000117 datasets tree; missing
# `<hemi>.sphere` -- ds000117's own FreeSurfer derivatives only ship
# `sphere.reg` -- worked around; automated-coregistration fit quality
# logged, not just assumed good). Recommend the same one-subject-first
# discipline before the full array:
#
#     sbatch --array=10 submit_source_space.slurm.sh
#
# ── Resource sizing ──────────────────────────────────────────────────────
# --mem=16G: watershed BEM + source-space setup + forward/inverse/LCMV are
# all much lighter than the sensor-space chain's ICA/epoching steps
# (32G there) -- no big epochs/ICA objects in memory, mostly BEM meshes and
# a handful of evoked/cov/forward matrices. Watch actual usage on the first
# array tasks before trusting this at full scale, same as submit_pipeline.slurm.sh.
#
# ── FreeSurfer dependency ────────────────────────────────────────────────
# Needs `module load FreeSurfer/7.4.1` for `mri_watershed` (anatomy step
# only -- coreg/forward/inverse/lcmv are pure MNE-Python, no FreeSurfer
# binary calls). Loaded explicitly below, not assumed part of the compute
# node's default environment.

set -e
set -x

PY=/network/iss/cenir/analyse/meeg/BRAINLIFE/code/.venv-cluster/bin/python3
HERE=/network/iss/cenir/analyse/meeg/BRAINLIFE/code/local_scripts/WakemanRepro/cluster

mkdir -p "$HERE/logs"
# `module` is a shell function from Lmod's init script -- not available in a
# plain non-interactive #!/bin/bash sbatch script without sourcing it first
# (confirmed: first submission failed instantly, exit 127, "module: command
# not found" -- interactive `bash -lc` shells source this via /etc/profile,
# a plain sbatch script doesn't). Compute nodes' default MODULEPATH also
# doesn't include the workstation module tree FreeSurfer lives in (confirmed
# via srun -- login-node `module load` worked, compute-node one failed
# "unknown module" until this `module use` was added) -- login and compute
# nodes are NOT the same MODULEPATH, unlike what worked for the smoke test
# run directly on the desktop.
source /etc/profile.d/modules.sh
module use /network/iss/apps/modules/scit/workstation
module load FreeSurfer/7.4.1

"$PY" -u "$HERE/run_subject_anatomy.py" "$SLURM_ARRAY_TASK_ID"
"$PY" -u "$HERE/run_subject_coreg.py" "$SLURM_ARRAY_TASK_ID"
"$PY" -u "$HERE/run_subject_forward_inverse.py" "$SLURM_ARRAY_TASK_ID"
"$PY" -u "$HERE/run_subject_lcmv.py" "$SLURM_ARRAY_TASK_ID"
