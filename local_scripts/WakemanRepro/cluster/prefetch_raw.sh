#!/bin/bash
# Pre-fetch raw + proc-sss git-annex content for all non-excluded ds000117
# subjects, from a machine with internet egress (this desktop already
# confirmed working during Step 0). Run this BEFORE submitting the Slurm
# array if compute nodes might lack internet access -- git annex get is
# idempotent, so it's harmless to also let run_subject_chain.py re-check
# from the compute node (fast no-op once content is already local).
set -e
set -x

DATASET_ROOT=/network/iss/cenir/analyse/meeg/BRAINLIFE/datasets/ds000117
cd "$DATASET_ROOT"

for sub in sub-01 sub-02 sub-03 sub-04 sub-05 sub-06 sub-07 sub-08 sub-09 \
           sub-10 sub-11 sub-12 sub-13 sub-14 sub-15 sub-16; do
    git annex get "${sub}/ses-meg/meg" --from=s3-PUBLIC
    git annex get "derivatives/meg_derivatives/${sub}/ses-meg/meg" --from=s3-PUBLIC
done
