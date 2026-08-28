#!/bin/bash
#SBATCH --job-name=biomag_sub3_extra
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=40G
#SBATCH --time=02:00:00
#SBATCH --output=/network/iss/cenir/analyse/meeg/BRAINLIFE/code/local_scripts/WakemanRepro/cluster/logs/subject3_extra.out
#SBATCH --error=/network/iss/cenir/analyse/meeg/BRAINLIFE/code/local_scripts/WakemanRepro/cluster/logs/subject3_extra.err
#
# One-off job for cluster/run_subject3_extra.py -- subject 3's tSSS
# recompute (03 + tsss branches of 05/06/07/08, x2 for tsss=10 and tsss=1)
# plus a config-wide l_freq=1 pass of 06/07/08, needed for Jas Figure 4.
# --mem=40G: three sequential heavy 06-make_epochs passes in one process
# (each individually peaks ~21G per the regular chain) -- bumped above the
# regular chain's 32G for extra headroom against GC/fragmentation across
# passes, not because any single pass is expected to need more.

set -e
set -x

PY=/network/iss/cenir/analyse/meeg/BRAINLIFE/code/.venv-cluster/bin/python3
HERE=/network/iss/cenir/analyse/meeg/BRAINLIFE/code/local_scripts/WakemanRepro/cluster

mkdir -p "$HERE/logs"
"$PY" -u "$HERE/run_subject3_extra.py"
