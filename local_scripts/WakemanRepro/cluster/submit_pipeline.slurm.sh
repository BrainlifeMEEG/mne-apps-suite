#!/bin/bash
#SBATCH --job-name=biomag_repro
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=32G
#SBATCH --time=02:00:00
#SBATCH --array=2,3,4,6,7,8,9,10,11,12,13,14,15,17,18,19
#SBATCH --output=/network/iss/cenir/analyse/meeg/BRAINLIFE/code/local_scripts/WakemanRepro/cluster/logs/subject_%a.out
#SBATCH --error=/network/iss/cenir/analyse/meeg/BRAINLIFE/code/local_scripts/WakemanRepro/cluster/logs/subject_%a.err
#
# Submits the verbatim mne-biomag-group-demo chain (02 -> 04x2 -> 05 -> 06,
# see run_subject_chain.py) as one Slurm array task per ds000117 subject,
# openfMRI-numbered per the crosswalk in crosswalk.py. Array indices skip
# 1, 5, 16 -- excluded per the dataset's own README (bad EEG) and
# library/config.py's exclude_subjects, matching what the original authors
# themselves left out of the analysis.
#
# ── BEFORE running the full array ────────────────────────────────────────
# Only openfMRI subject_id 10 (BIDS sub-09, our "S09") has an independently
# verified crosswalk mapping (checked against the paper's own published
# Figure 2). Every other row rests on ds000117's README table alone -- the
# Stage 1/2 cross-check strategy for those (see the Step 0 plan) has not
# been run yet. Strongly recommend smoke-testing before committing cluster
# resources to all 16:
#
#     sbatch --array=10 submit_pipeline.slurm.sh          # known-good subject
#     sbatch --array=2   submit_pipeline.slurm.sh          # one unverified subject
#
# ── Resource sizing ──────────────────────────────────────────────────────
# --mem=32G is calibrated from ONE subject (S09): 05-run_ica.py peaked at
# 9.96 GB, 06-make_epochs.py at 20.82 GB (measured under a memory-guarded
# wrapper on the dev desktop during Step 0 -- see GLITCHES.md). 32G leaves
# ~11 GB of margin above that; other subjects with longer runs / more
# events could plausibly need more. Watch the first few array tasks'
# actual memory usage (`sacct -j <jobid> --format=MaxRSS`) before trusting
# this default at full scale.
#
# --cpus-per-task=1 matches N_JOBS=1, the only value actually exercised
# during Step 0 -- bump both together if you want per-subject filtering to
# use more cores (config.py's N_JOBS feeds raw.filter()'s n_jobs directly).
#
# ── Network dependency ───────────────────────────────────────────────────
# run_subject_chain.py fetches each subject's raw+proc-sss content via
# `git annex get` from OpenNeuro's public S3 bucket if not already present
# locally (idempotent). If compute nodes lack internet egress, run
# ./prefetch_raw.sh from a machine that has it (e.g. this desktop) first.

set -e
set -x

# .venv-cluster (NOT the project's normal .venv) -- built from the shared
# Spack module python/3.11.12-xa3gulo (/network/iss/apps/...), so its
# interpreter path resolves identically on the desktop and on any compute
# node, unlike .venv's uv-managed interpreter which lives under the
# desktop-only $HOME. Verified importing mne/autoreject/nibabel/etc.
# correctly on an actual compute node (sphpc-cpu49, Broadwell) via srun --
# NOT verified on the login node itself, which turned out to be older
# (Ivy Bridge) hardware lacking the AVX2 instructions this build uses and
# SIGILLs immediately. If Slurm ever schedules this on unexpectedly old
# hardware, that's the failure mode to recognize.
PY=/network/iss/cenir/analyse/meeg/BRAINLIFE/code/.venv-cluster/bin/python3
HERE=/network/iss/cenir/analyse/meeg/BRAINLIFE/code/local_scripts/WakemanRepro/cluster

mkdir -p "$HERE/logs"
"$PY" -u "$HERE/run_subject_chain.py" "$SLURM_ARRAY_TASK_ID"
