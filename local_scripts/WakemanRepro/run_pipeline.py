#!/usr/bin/env python3
"""Wakeman & Henson (ds000117) reproduction driver, built on BrainlifePipelineCLI.

Grows one phase at a time, per the brief's phase-boundary pauses. Currently
covers Phase 1 (fif2mne) only.

Usage:
    python run_pipeline.py --dry-run
    python run_pipeline.py
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "BrainlifePipelineCLI"))
from brainlife_pipeline_cli import PipelineRunner, find_root_dataset, bl, load_state

PROJECT = "5df7efdc32bff02262e226b6"
STATE_FILE = Path(__file__).parent / "state.json"

APPS = {
    # (app_id, github_branch, input_id)
    "fif2mne": ("628b5c89d0697cf1eaeaffad", "main", "fif1"),
    "maxwell-filter": ("602bc6a33a001123014c442a", "v1.0", "fif01"),
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--subjects", default="10", help="comma-separated subject ids (default: 10)")
    parser.add_argument("--runs", default="02", help="comma-separated run numbers (default: 02)")
    args = parser.parse_args()
    subjects = args.subjects.split(",")
    runs = args.runs.split(",")

    state = load_state(STATE_FILE)

    print(f"Querying project {PROJECT} for root datasets...")
    catalog = json.loads(bl("data", "query", "--project", PROJECT, "-j", "-l", "5000"))

    for subject in subjects:
        for run in runs:
            print(f"\n===== subject {subject} run {run} =====")
            raw_id = find_root_dataset(catalog, subject, ["task-facerecognition", f"run-{run}"])

            app_id, branch, input_id = APPS["fif2mne"]
            runner = PipelineRunner(project=PROJECT, branch=branch)
            fif2mne_out = runner.run_step(
                state, STATE_FILE,
                step_key=f"S{subject}:run{run}:fif2mne",
                app_id=app_id,
                input_ids=input_id,
                dataset_ids=[raw_id],
                config={},
                tags=[f"S{subject}", f"run{run}"],
                instance_name=f"S{subject}",
                dry_run=args.dry_run,
            )
            print(f"fif2mne output dataset: {fif2mne_out}")

            # NB: maxwell-filter's "fif01" input declares datatype
            # neuro/meg/fif (same as the raw upload), not
            # neuro/meeg/mne/raw (fif2mne's output datatype) -- it
            # consumes the original raw upload directly, not fif2mne's
            # output. Confirmed empirically: chaining fif2mne_out in here
            # fails with "Given input of datatype neuro/meeg/mne/raw but
            # expected neuro/meg/fif".
            app_id, branch, input_id = APPS["maxwell-filter"]
            runner = PipelineRunner(project=PROJECT, branch=branch)
            mf_out = runner.run_step(
                state, STATE_FILE,
                step_key=f"S{subject}:run{run}:maxwell-filter",
                app_id=app_id,
                input_ids=input_id,
                dataset_ids=[raw_id],
                config={},
                tags=[f"S{subject}", f"run{run}"],
                instance_name=f"S{subject}",
                dry_run=args.dry_run,
                output_id="out_dir",
            )
            print(f"maxwell-filter output dataset: {mf_out}")


if __name__ == "__main__":
    main()
