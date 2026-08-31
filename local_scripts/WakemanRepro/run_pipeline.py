#!/usr/bin/env python3
"""Wakeman & Henson (ds000117) sensor-space reproduction driver, on
brainlife.io, built on BrainlifePipelineCLI.

Scope (see ~/.claude/plans/jazzy-swinging-whistle.md for the full plan this
implements): sensor-space only (Figs 1-7, 10) -- Maxwell-filter selection
through evoked averaging + noise covariance, per subject. Source-space
(Figs 8/9/11/12) is out of scope here; group-level stats/decoding/figures
move to brainlife.io's Analysis-tab notebook once this chain's outputs are
exposed via a Pipeline, also out of scope for this driver.

STATUS (2026-08-31): stages 1 (proc-sss selection) and the existing
fif2mne/maxwell-filter Fig-1-diagnostic branch are real and runnable.
Stages 2-11 have their app IDs UNRESOLVED (`app_id=None` placeholders in
APPS below) -- this environment has no live brainlife.io API access to run
`bl app search` and pin them down (confirmed: `bl project query` and a
direct `curl` to the warehouse API both hang/time out here, even with
sandboxing disabled, while the plain https://brainlife.io homepage
resolves fine -- a real network-reachability gap, not a permissions
issue). Resolve each placeholder from an environment that *does* have
`bl` connectivity (same as however the existing state.json progress was
made), then fill in `APPS`; `run_subject_chain()` skips any stage whose
app_id is still None (prints `[TODO]` and stops that subject's chain there)
rather than erroring, so this file is safe to run as-is while apps get
resolved incrementally, matching the plan's phase-by-phase approach.

Usage:
    python run_pipeline.py --dry-run
    python run_pipeline.py --subjects 09,10 --runs 01,02,03,04,05,06
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "BrainlifePipelineCLI"))
from brainlife_pipeline_cli import PipelineRunner, find_root_dataset, bl, load_state

sys.path.insert(0, str(Path(__file__).parent / "cluster"))
sys.path.insert(0, str(Path(__file__).parent / "original_scripts"))
from crosswalk import OPENFMRI_TO_BIDS, EXCLUDED  # noqa: E402
from library.config import map_subjects  # noqa: E402

PROJECT = "5df7efdc32bff02262e226b6"
STATE_FILE = Path(__file__).parent / "state.json"
BADS_DIR = Path(__file__).parent / "original_scripts" / "bads"

# BIDS 'sub-NN' numeric part -> openfMRI subject_id (inverse of crosswalk.py's
# OPENFMRI_TO_BIDS). This project's platform datasets are tagged/keyed by the
# BIDS numeric id directly (confirmed: run_pipeline.py's own pre-existing
# --subjects usage, e.g. "09,10", matches BIDS sub-09/sub-10 folder names),
# which is NOT the same numbering as either openfMRI ids or the W&H
# `subject_NN` names config.py's bad-channel lookup needs -- see
# GLITCHES.md / Strategy.md's "four numbering schemes" warning. Verified
# empirically before use, not assumed: BIDS sub-09 -> openfMRI id 10 ->
# W&H 'subject_12' -> bads/subject_12/run_02_raw_tr.fif_bad has exactly 7
# channels, matching Strategy.md's independent Fig 2 crosswalk verification.
BIDS_TO_OPENFMRI = {v.replace("sub-", ""): k for k, v in OPENFMRI_TO_BIDS.items()}


def wh_subject_name(bids_subject):
    """BIDS 'sub-NN' numeric part (e.g. "09") -> (W&H 'subject_NN' name,
    openfMRI subject_id) -- see BIDS_TO_OPENFMRI's docstring above."""
    if bids_subject not in BIDS_TO_OPENFMRI:
        raise ValueError(f"BIDS subject '{bids_subject}' not in crosswalk (excluded or unknown)")
    openfmri_id = int(BIDS_TO_OPENFMRI[bids_subject])
    if openfmri_id in EXCLUDED:
        raise ValueError(f"BIDS sub-{bids_subject} (openfMRI id {openfmri_id}) is excluded")
    return map_subjects[openfmri_id], openfmri_id


def read_bad_channels(bids_subject, run):
    """Per-subject/run bad-EEG-channel list, sourced from the project repo's
    own bads/<W&H name>/run_NN_raw_tr.fif_bad files (NOT Elekta's MaxFilter
    log -- 06-make_epochs.py's own documented source, see GLITCHES.md).
    Returns a (possibly empty) list of channel names."""
    wh_name, _ = wh_subject_name(bids_subject)
    fname = BADS_DIR / wh_name / f"run_{run}_raw_tr.fif_bad"
    if not fname.exists():
        raise FileNotFoundError(f"no bad-channel file for {wh_name} run {run}: {fname}")
    with open(fname) as f:
        return [line.strip() for line in f if line.strip()]


APPS = {
    # (app_id, github_branch, input_id) -- resolved, tested (see state.json)
    "fif2mne": ("628b5c89d0697cf1eaeaffad", "main", "fif1"),
    "maxwell-filter": ("602bc6a33a001123014c442a", "v1.0", "fif01"),

    # --- UNRESOLVED (app_id=None) -- fill in via `bl app search --name <name> -j`
    # from an environment with real brainlife.io API access, then update the
    # tuple below. Config dicts underneath each stage in run_subject_chain()
    # already carry the target parameter VALUES (from config.py/GLITCHES.md);
    # only the app id/branch and the exact config KEY NAMES need confirming
    # against each app's real schema once resolved.
    "events": (None, None, None),
    "filter-raw": (None, None, None),
    "concat": (None, None, None),
    "ICA-fit": (None, None, None),
    "mark-bad-raw": (None, None, None),
    "ICA-apply": (None, None, None),
    "epoch": (None, None, None),
    "autoreject": (None, None, None),
    "average-erp": (None, None, None),
    # noise covariance (stage 11): NO app exists anywhere in this repo for
    # mne.compute_covariance -- confirmed gap, not just unresolved. Needed
    # for Fig 10 (whitened GFP) even though it's sensor-space. Not in APPS
    # at all; run_subject_chain() stops before this stage with a clear
    # message rather than pretending there's an app to resolve.
}


def app_step(runner, state, step_key, stage_name, input_id, dataset_ids, config,
            tags, instance_name, dry_run, output_id="out_dir"):
    """Thin wrapper around PipelineRunner.run_step that no-ops (prints
    [TODO], returns None) instead of erroring when a stage's app id hasn't
    been resolved yet -- lets this driver run end-to-end (stopping cleanly
    at the first unresolved stage) while apps get filled in incrementally."""
    app_id, branch, declared_input_id = APPS[stage_name]
    if app_id is None:
        print(f"[TODO] {step_key}: '{stage_name}' app id not resolved yet -- stopping this "
              "subject's chain here. Resolve via `bl app search --name "
              f"{stage_name} -j` from a brainlife.io-connected environment.")
        return None
    return runner.run_step(
        state, STATE_FILE,
        step_key=step_key,
        app_id=app_id,
        input_ids=input_id or declared_input_id,
        dataset_ids=dataset_ids,
        config=config,
        tags=tags,
        instance_name=instance_name,
        dry_run=dry_run,
        output_id=output_id,
    )


def run_fig1_diagnostic_branch(catalog, subject, run, state, dry_run):
    """The ORIGINAL Phase-1/Phase-2 pair (fif2mne + maxwell-filter), kept as
    a separate, explicit branch -- this is Fig-1-specific (MNE's own SSS
    recompute vs. Elekta's proc-sss file, side by side), NOT what the main
    sensor-space chain needs. GLITCHES.md / cluster/run_subject_chain.py
    both confirm the main pipeline never recomputes Maxwell filtering; it
    uses Elekta's deposited proc-sss file as-is (see run_subject_chain()'s
    stage 1 below). Call this only when actually rebuilding Fig 1."""
    raw_id = find_root_dataset(catalog, subject, ["task-facerecognition", f"run-{run}"])

    app_id, branch, input_id = APPS["fif2mne"]
    runner = PipelineRunner(project=PROJECT, branch=branch)
    fif2mne_out = runner.run_step(
        state, STATE_FILE, step_key=f"S{subject}:run{run}:fif2mne",
        app_id=app_id, input_ids=input_id, dataset_ids=[raw_id], config={},
        tags=[f"S{subject}", f"run{run}"], instance_name=f"S{subject}", dry_run=dry_run,
    )
    print(f"fif2mne output dataset: {fif2mne_out}")

    # NB: maxwell-filter's "fif01" input declares datatype neuro/meg/fif
    # (same as the raw upload), not neuro/meeg/mne/raw (fif2mne's output
    # datatype) -- it consumes the original raw upload directly. Confirmed
    # empirically: chaining fif2mne_out in here fails with "Given input of
    # datatype neuro/meeg/mne/raw but expected neuro/meg/fif".
    app_id, branch, input_id = APPS["maxwell-filter"]
    runner = PipelineRunner(project=PROJECT, branch=branch)
    mf_out = runner.run_step(
        state, STATE_FILE, step_key=f"S{subject}:run{run}:maxwell-filter",
        app_id=app_id, input_ids=input_id, dataset_ids=[raw_id], config={},
        tags=[f"S{subject}", f"run{run}"], instance_name=f"S{subject}", dry_run=dry_run,
        output_id="out_dir",
    )
    print(f"maxwell-filter output dataset: {mf_out}")
    return fif2mne_out, mf_out


def run_subject_chain(catalog, subject, runs, state, dry_run):
    """Main sensor-space chain (stages 1-11 of the plan), per subject.
    Runs the per-run stages (1-3) for every run, then the subject-level
    stages (4-11: concat/ICA/epoch/evoked/cov) once, on all runs together.
    Stops cleanly at the first stage whose app id is unresolved (see
    app_step()) -- currently that's stage 2 (events), since only stage 1
    needs no app at all.
    """
    instance_name = f"S{subject}"
    runner_v1 = PipelineRunner(project=PROJECT, branch="v1.0")  # placeholder branch; confirm per-app

    filtered_none_ids = {}  # run -> dataset id, l_freq=None pass (feeds epoching)
    filtered_1hz_ids = {}   # run -> dataset id, l_freq=1 pass (feeds ICA fit only)
    events_ids = {}

    for run in runs:
        print(f"\n===== subject {subject} run {run}: per-run stages =====")

        # --- Stage 1: select the pre-staged proc-sss dataset (NOT a
        # maxwell-filter app call -- the main pipeline never recomputes
        # Maxwell filtering, see module docstring). TODO: confirm the exact
        # tag ("proc-sss") once there's live access to inspect the actual
        # dataset catalog -- guessed from Strategy.md's own description
        # ("MaxFilter derivatives (proc-sss, run-##)").
        try:
            proc_sss_id = find_root_dataset(catalog, subject,
                                            ["task-facerecognition", f"run-{run}", "proc-sss"])
        except RuntimeError as exc:
            print(f"[TODO] stage 1 (select proc-sss) for S{subject} run{run}: {exc} -- "
                  "confirm the real tag/datatype for the proc-sss dataset once there's live "
                  "platform access, then fix this filter.")
            return
        print(f"proc-sss dataset (stage 1, no app run): {proc_sss_id}")

        # --- Stage 2: events. mask=4096+256, mask_type='not_and',
        # consecutive='increasing', min_duration=0.003s (02-extract_events.py).
        events_out = app_step(
            runner_v1, state, f"S{subject}:run{run}:events", "events",
            input_id=None, dataset_ids=[proc_sss_id],
            config={"mask": 4096 + 256, "mask_type": "not_and",
                    "consecutive": "increasing", "min_duration": 0.003},
            tags=[f"S{subject}", f"run{run}"], instance_name=instance_name, dry_run=dry_run,
        )
        if events_out is None:
            return
        events_ids[run] = events_out

        # --- Stage 3: bandpass filter, TWO passes (04-python_filtering.py +
        # the documented "run twice" workaround -- 05-run_ica.py hardcodes
        # highpass-1Hz input regardless of config's l_freq).
        for l_freq, target_dict, pass_name in (
            (None, filtered_none_ids, "highpass-None"),
            (1, filtered_1hz_ids, "highpass-1Hz"),
        ):
            filt_out = app_step(
                runner_v1, state, f"S{subject}:run{run}:filter-raw:{pass_name}", "filter-raw",
                input_id=None, dataset_ids=[proc_sss_id],
                config={"l_freq": l_freq, "h_freq": 40},
                tags=[f"S{subject}", f"run{run}", pass_name], instance_name=instance_name,
                dry_run=dry_run,
            )
            if filt_out is None:
                return
            target_dict[run] = filt_out

    # --- Stage 4: concatenate the 6 runs' highpass-1Hz filtered raws (ICA
    # fit input only -- 05-run_ica.py concatenates before fitting).
    print(f"\n===== subject {subject}: subject-level stages =====")
    concat_out = app_step(
        runner_v1, state, f"S{subject}:concat:highpass-1Hz", "concat",
        input_id=None, dataset_ids=[filtered_1hz_ids[r] for r in runs],
        config={},
        tags=[f"S{subject}", "concat", "highpass-1Hz"], instance_name=instance_name, dry_run=dry_run,
    )
    if concat_out is None:
        return

    # --- Stage 5: ICA fit. method='fastica', n_components=0.999, MEG-only,
    # reject=dict(grad=4000e-13, mag=4e-12), decim=11, random_state=42.
    ica_out = app_step(
        runner_v1, state, f"S{subject}:ICA-fit", "ICA-fit",
        input_id=None, dataset_ids=[concat_out],
        config={"method": "fastica", "n_components": 0.999,
                "reject": {"grad": 4000e-13, "mag": 4e-12}, "decim": 11, "random_state": 42},
        tags=[f"S{subject}"], instance_name=instance_name, dry_run=dry_run,
    )
    if ica_out is None:
        return

    # Everything from here (mark-bad-raw per run, ICA-apply, epoch,
    # autoreject, average-erp, covariance) needs its app resolved first;
    # app_step() will [TODO]-stop at mark-bad-raw (the next unresolved
    # stage) via the per-run loop below once reached. Left structured (not
    # collapsed into a stub) so filling in one more app id immediately
    # extends how far this subject's chain actually runs.

    for run in runs:
        bad_channels = read_bad_channels(subject, run)
        print(f"S{subject} run{run} bad channels ({len(bad_channels)}): {bad_channels}")
        marked_out = app_step(
            runner_v1, state, f"S{subject}:run{run}:mark-bad-raw", "mark-bad-raw",
            input_id=None, dataset_ids=[filtered_none_ids[run]],
            config={"bads": bad_channels},
            tags=[f"S{subject}", f"run{run}"], instance_name=instance_name, dry_run=dry_run,
        )
        if marked_out is None:
            return
        # ICA-apply, epoch, autoreject, average-erp, covariance: same
        # pattern, added once mark-bad-raw's app id (and its real config
        # schema) is confirmed. See the plan (jazzy-swinging-whistle.md)
        # phases 7-11 for the exact parameters to use per stage.


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--subjects", default="10", help="comma-separated BIDS subject numbers (default: 10)")
    parser.add_argument("--runs", default="02", help="comma-separated run numbers (default: 02)")
    parser.add_argument("--fig1-only", action="store_true",
                        help="run only the Fig-1 diagnostic branch (fif2mne+maxwell-filter), "
                             "not the main sensor-space chain")
    args = parser.parse_args()
    subjects = args.subjects.split(",")
    runs = args.runs.split(",")

    state = load_state(STATE_FILE)

    print(f"Querying project {PROJECT} for root datasets...")
    catalog = json.loads(bl("data", "query", "--project", PROJECT, "-j", "-l", "5000"))

    for subject in subjects:
        if args.fig1_only:
            for run in runs:
                print(f"\n===== subject {subject} run {run}: Fig 1 diagnostic branch =====")
                run_fig1_diagnostic_branch(catalog, subject, run, state, args.dry_run)
        else:
            run_subject_chain(catalog, subject, runs, state, args.dry_run)


if __name__ == "__main__":
    main()
