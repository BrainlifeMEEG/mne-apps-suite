#!/bin/bash
#SBATCH --job-name=biomag_lfreq1_epochs
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=32G
#SBATCH --time=01:00:00
#SBATCH --array=2,3,4,6,7,8,9,10,11,12,13,14,15,17,18,19
#SBATCH --output=/network/iss/cenir/analyse/meeg/BRAINLIFE/code/local_scripts/WakemanRepro/cluster/logs/lfreq1_subject_%a.out
#SBATCH --error=/network/iss/cenir/analyse/meeg/BRAINLIFE/code/local_scripts/WakemanRepro/cluster/logs/lfreq1_subject_%a.err
#
# Fills in Jas Figure 5's panel B: 06+07 under l_freq=1 for all 16
# non-excluded subjects (03/04/05 NOT rerun -- see run_subject_lfreq1_epochs.py
# docstring for why). Run cluster/run_grand_average.py again afterward
# (config.l_freq patched to 1) to build grand_average_highpass-1Hz-ave.fif,
# then figures_jas/jas_fig5_grand_average.py (same patch) for the panel.

set -e
set -x

PY=/network/iss/cenir/analyse/meeg/BRAINLIFE/code/.venv-cluster/bin/python3
HERE=/network/iss/cenir/analyse/meeg/BRAINLIFE/code/local_scripts/WakemanRepro/cluster

mkdir -p "$HERE/logs"
"$PY" -u "$HERE/run_subject_lfreq1_epochs.py" "$SLURM_ARRAY_TASK_ID"
