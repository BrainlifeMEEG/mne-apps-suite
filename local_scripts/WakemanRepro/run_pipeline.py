#!/usr/bin/env python3
"""Wakeman & Henson (ds000117) sensor-space reproduction driver, on
brainlife.io, built on BrainlifePipelineCLI.

Scope (see ~/.claude/plans/jazzy-swinging-whistle.md for the full plan this
implements): sensor-space only (Figs 1-7, 10) -- Maxwell-filter selection
through evoked averaging + noise covariance, per subject. Source-space
(Figs 8/9/11/12) is out of scope here; group-level stats/decoding/figures
move to brainlife.io's Analysis-tab notebook once this chain's outputs are
exposed via a Pipeline, also out of scope for this driver.

STATUS (2026-08-31): all 11 app ids resolved (`bl app query`, real network
access confirmed working -- see below) and every stage's real config-key
schema pulled from the platform (`bl app query -i <id> -j`), not guessed.
One real correction found this way: the pre-staged `proc-sss` dataset's
datatype is `neuro/meg/fif`, but events/filter-raw/concat/ICA-fit/
mark-bad-raw/ICA-apply all declare their `fif` input as `neuro/meeg/mne/raw`
-- fif2mne's own output datatype, NOT the raw upload's. So fif2mne is a
required stage on the MAIN chain too (per run, right after proc-sss
selection), not just the Fig-1-diagnostic branch as originally assumed.
Confirmed via `bl datatype query`, not left as a guess.

Two real, confirmed methodological gaps vs. the local/cluster reference
implementation (not blocking, but the outputs won't be bit-identical to
the paper-verified local pipeline until addressed):
- `autoreject` (app) uses the full `AutoReject` class (Bayesian
  optimization over n_interpolate/consensus) -- the local pipeline instead
  uses the simpler `autoreject.get_rejection_threshold()` (a single
  per-channel-type amplitude threshold, epochs above it dropped). Verified
  by reading both `autoreject/main.py` (this repo) and
  `06-make_epochs.py`. Different algorithm, not just different params.
- `average-erp` has no `equalize_epoch_counts` option anywhere in its
  config or `main.py` -- the local pipeline's `faces_eq`/`scrambled_eq`
  conditions (trial-count-equalized) can't be reproduced by this app as-is.

Two real bugs found+fixed in BrainlifeMEEG/ICA-fit and ICA-apply (their
`v1.0` branches, pushed directly) by actually running this chain: ICA-fit's
`.gitmodules` used SSH for its brainlife_utils submodule (every sibling app
already used HTTPS -- fails Amaretti's app-cache build with a host-key
error the first time that commit runs on a cluster node); both ICA-fit and
ICA-apply pinned a brainlife_utils commit that predates `require_config_keys()`,
which their own `main.py`s import (`ImportError`). See
[[project_ica_fit_apply_bugfixes]] in memory for the full writeup.

Every `run_step`/`app_run` call here passes `direct_deps=True` (2026-09-01,
per the user's reminder) -- without it, every chained app run re-stages its
input from archive storage even when immediately consuming the previous
step's own output within the same instance; BrainlifePipelineCLI's own
README already documents this as "confirmed working," it just wasn't wired
into this driver yet.

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
# PipelineRunner's own default is 4 -- most failures hit this session have
# been real app bugs, not transient infra flakiness, so 4 identical retries
# just burns cluster time waiting to find that out. Overridable via
# --max-attempts; set from main() before any PipelineRunner is constructed.
MAX_ATTEMPTS = 2
STATE_FILE = Path(__file__).parent / "state.json"
BADS_DIR = Path(__file__).parent / "original_scripts" / "bads"

# BIDS 'sub-NN' numeric part -> openfMRI subject_id (inverse of crosswalk.py's
# OPENFMRI_TO_BIDS). This project's platform datasets are tagged/keyed by the
# BIDS numeric id directly (confirmed against the live catalog: dataset
# meta.subject values are '01'.."16"), which is NOT the same numbering as
# either openfMRI ids or the W&H `subject_NN` names config.py's bad-channel
# lookup needs -- see GLITCHES.md / Strategy.md's "four numbering schemes"
# warning. Verified empirically before use: BIDS sub-09 -> openfMRI id 10 ->
# W&H 'subject_12' -> bads/subject_12/run_02_raw_tr.fif_bad has exactly 7
# channels, matching Strategy.md's independent Fig 2 crosswalk verification;
# BIDS sub-10 -> 'subject_15' has zero bad channels every run, also
# independently matching Strategy.md's own finding.
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


# Real event-id mapping from 06-make_epochs.py's events_id dict, formatted
# as the `epoch` app's own "name-id,name-id,..." config string convention
# (confirmed against a live sample of that app's config, though that sample
# turned out to be a leftover from a different, unrelated experiment --
# checked its actual content before trusting it, not just its existence).
EVENT_ID_CONDITION_MAPPING = ",".join(
    f"{name}-{eid}" for name, eid in {
        "face/famous/first": 5, "face/famous/immediate": 6, "face/famous/long": 7,
        "face/unfamiliar/first": 13, "face/unfamiliar/immediate": 14, "face/unfamiliar/long": 15,
        "scrambled/first": 17, "scrambled/immediate": 18, "scrambled/long": 19,
    }.items()
)

# EEG061/062/063 are actually EOG/EOG/ECG on this system, digitized through
# spare EEG amplifier channels -- see original_scripts/04-python_filtering.py
# (raw.set_channel_types + raw.rename_channels, done once, early). No app
# in this chain knew about this until fif2mne gained optional
# channel_types/rename_channels config (commit 4bc9472) specifically for
# it. EEG064 ("free-floating electrode" per that script's own comment)
# only gets retyped, not renamed. Applied once here, at fif2mne (the first
# touchpoint), so every downstream stage sees the fix.
FIF2MNE_CHANNEL_FIX = {
    "channel_types": "EEG061-eog,EEG062-eog,EEG063-ecg,EEG064-misc",
    "rename_channels": "EEG061-EOG061,EEG062-EOG062,EEG063-ECG063",
}

# (app_id, github_branch, input_id) -- ALL resolved via `bl app query`
# (2026-08-31, live platform access). input_id is the app's real declared
# input slot name for its primary data input (from `bl app query -i <id> -j`
# -> "inputs"), not guessed.
APPS = {
    # NOTE (2026-09-03): was ("628b5c89d0697cf1eaeaffad", "main", "fif1") --
    # that app id is guiomar/app_fif2mne, github_branch=main, _canedit=False
    # (admin-locked). Every fif2mne call all session had actually been going
    # to an app we can't modify. The real, editable one (BrainlifeMEEG/
    # fif2mne, v1.0, _canedit=True) already exists per the earlier
    # re-registration (project_fif2mne_multifile_and_new_app memory) -- the
    # driver just never got updated to point at it. Fixed here.
    "fif2mne": ("6a8d9b56ad4d4a4b5327f838", "v1.0", "fif"),
    "maxwell-filter": ("602bc6a33a001123014c442a", "v1.0", "fif01"),
    "events": ("632993fd71291bb27f9ab7c9", "v1.0", "fif"),
    "filter-raw": ("642dc7d173d2685502ec4d5f", "v1.0", "fif"),
    "concat": ("642daf2d73d2685502ebfd09", "v1.0", "raw"),
    "ICA-fit": ("63344389db978c79919cbb82", "v1.0", "fif"),
    "mark-bad-raw": ("64075b6fc538c16a826b67be", "v1.0", "fif"),
    "ICA-apply": ("63358285db978c7991a30e5b", "v1.0", "fif"),
    "epoch": ("625d3130cc8ab2b339ea2692", "v1.0", "raw"),
    "autoreject": ("6a86e1ab3d6b58548ca9ad20", "v1.0", "epo"),
    "average-erp": ("6a594cfc13254aef69af404a", "v1.0", "evoked"),  # input id is misleadingly
    # named "evoked" but its declared datatype is neuro/meeg/mne/epochs --
    # average-erp does its own per-condition averaging from epochs
    # internally. Confirmed via `bl app query`, not assumed.
    "noise-covariance": ("698f0a5e88100c81ffc8a41d", "working_ver", "epochs"),  # obVdo/app-noise-covariance-v2
}

# Real datatype ids, confirmed via `bl datatype query` -- kept here only as
# a documented cross-check, not consumed by the driver (the platform itself
# enforces these on every app_run call).
#   neuro/meg/fif             6000737faacf9ee51fa691cb  (raw upload, proc-sss)
#   neuro/meeg/mne/raw        61893398e8be76b34cb9826e  (fif2mne output; what
#                                                         events/filter-raw/etc. want)
#   neuro/meg/fif-override    608195ce89df435fd26893c1  (events output; also
#                                                         mark-bad-raw's optional
#                                                         "channels" input, epoch's
#                                                         optional "events" input)
#   neuro/meeg/mne/ica        6283e821d0697cf1eade9d5c
#   neuro/meeg/mne/epochs     61797fc39538685e5db952b0
#   neuro/meeg/mne/evoked     5978fd38b09297d8d8aa8746
#   neuro/meeg/mne/covariance 5afb21465858d874a4b393a1


def app_step(runner, state, step_key, stage_name, dataset_ids, config,
            tags, instance_name, dry_run, output_id="out_dir", input_id=None,
            direct_deps=True):
    """Thin wrapper around PipelineRunner.run_step, using APPS' resolved
    (app_id, branch, input_id) for `stage_name` unless input_id is
    overridden (needed when an app has more than one required input, e.g.
    ICA-apply's fif+ica or noise-covariance's epochs+...).

    direct_deps=True by default -- per the user's own reminder (2026-09-01)
    and BrainlifePipelineCLI's README: without it, every single app run
    re-stages its input from archive storage even when it's immediately
    consuming the previous step's own output within the same instance, an
    unnecessary "Data Staging Task" + archive re-read per chained step.
    Confirmed working end-to-end for freshly-chained same-run outputs
    (ICA-fit -> ICA-apply -> epoch, 2026-09-03).

    BUT: having prov.task/prov.subdir on a dataset (true for every app-task
    output and every `bl data upload`ed dataset -- direct_deps' own
    precondition) does NOT guarantee that task's ephemeral compute workdir
    still exists -- confirmed on the ICM cluster: fif2mne consuming the
    project's original proc-sss UPLOAD (months old) failed 4/4 with
    "Dependency removed", the exact "referenced workdir is gone" failure
    mode, despite proc-sss carrying real provenance fields. direct_deps is
    only actually safe for a task produced earlier in the SAME run, not for
    old/pre-existing datasets -- callers touching proc-sss or any other
    already-archived-a-while-ago dataset should pass direct_deps=False."""
    app_id, branch, declared_input_id = APPS[stage_name]
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
        direct_deps=direct_deps,
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
    runner = PipelineRunner(project=PROJECT, branch=branch, max_attempts=MAX_ATTEMPTS)
    # direct_deps=False: raw_id is the project's original upload, months
    # old -- see app_step's docstring above. Confirmed: this exact call
    # (fif2mne on proc-sss/raw_id) failed 4/4 with "Dependency removed"
    # when this was True.
    fif2mne_out = runner.run_step(
        state, STATE_FILE, step_key=f"S{subject}:run{run}:fif2mne",
        app_id=app_id, input_ids=input_id, dataset_ids=[raw_id],
        config=dict(FIF2MNE_CHANNEL_FIX),
        tags=[f"S{subject}", f"run{run}"], instance_name=f"S{subject}", dry_run=dry_run,
        direct_deps=False,
    )
    print(f"fif2mne output dataset: {fif2mne_out}")

    # NB: maxwell-filter's "fif01" input declares datatype neuro/meg/fif
    # (same as the raw upload), not neuro/meeg/mne/raw (fif2mne's output
    # datatype) -- it consumes the original raw upload directly. Confirmed
    # empirically: chaining fif2mne_out in here fails with "Given input of
    # datatype neuro/meeg/mne/raw but expected neuro/meg/fif". Same
    # direct_deps=False reasoning as fif2mne above -- raw_id is old.
    app_id, branch, input_id = APPS["maxwell-filter"]
    runner = PipelineRunner(project=PROJECT, branch=branch, max_attempts=MAX_ATTEMPTS)
    mf_out = runner.run_step(
        state, STATE_FILE, step_key=f"S{subject}:run{run}:maxwell-filter",
        app_id=app_id, input_ids=input_id, dataset_ids=[raw_id], config={},
        tags=[f"S{subject}", f"run{run}"], instance_name=f"S{subject}", dry_run=dry_run,
        output_id="out_dir", direct_deps=False,
    )
    print(f"maxwell-filter output dataset: {mf_out}")
    return fif2mne_out, mf_out


def run_subject_chain(catalog, subject, runs, state, dry_run):
    """Main sensor-space chain (stages 1-11 of the plan), per subject.
    Runs the per-run stages for every run, then the subject-level stages
    (concat/ICA/epoch/evoked/cov) once, on all runs together.
    """
    instance_name = f"S{subject}"
    runner = PipelineRunner(project=PROJECT, branch="v1.0", max_attempts=MAX_ATTEMPTS)
    runner_cov = PipelineRunner(project=PROJECT, branch="working_ver", max_attempts=MAX_ATTEMPTS)

    mne_raw_ids = {}        # run -> fif2mne'd raw (neuro/meeg/mne/raw)
    events_ids = {}         # run -> events (neuro/meg/fif-override)
    filtered_none_ids = {}  # run -> dataset id, l_freq=None pass (feeds epoching)
    filtered_1hz_ids = {}   # run -> dataset id, l_freq=1 pass (feeds ICA fit only)

    for run in runs:
        print(f"\n===== subject {subject} run {run}: per-run stages =====")

        # --- Stage 1: select the pre-staged proc-sss dataset (NOT a
        # maxwell-filter app call -- the main pipeline never recomputes
        # Maxwell filtering, see module docstring). Tag confirmed against
        # the live catalog: proc-sss datasets carry tags ['proc-sss',
        # 'run-NN'] only, no 'task-facerecognition' tag (that's only on the
        # raw upload) -- do NOT include it here.
        proc_sss_id = find_root_dataset(catalog, subject, ["proc-sss", f"run-{run}"])
        print(f"proc-sss dataset (stage 1, no app run): {proc_sss_id}")

        # --- Stage 1.5: fif2mne. Required on the main chain too, not just
        # the Fig-1 branch -- proc-sss's datatype is neuro/meg/fif, but
        # events/filter-raw/etc. all declare their input as
        # neuro/meeg/mne/raw (fif2mne's own output datatype). Confirmed via
        # `bl datatype query`, see module docstring.
        # direct_deps=False here: proc_sss_id is the project's original
        # upload, months old -- its producing task's ephemeral workdir is
        # long gone (confirmed: 4/4 "Dependency removed" with direct_deps
        # here). Every OTHER stage below stays direct_deps=True (app_step's
        # default), since each of those really is a fresh same-run output.
        mne_raw_out = app_step(
            runner, state, f"S{subject}:run{run}:fif2mne", "fif2mne",
            dataset_ids=[proc_sss_id], config=dict(FIF2MNE_CHANNEL_FIX),
            tags=[f"S{subject}", f"run{run}"], instance_name=instance_name, dry_run=dry_run,
            direct_deps=False,
        )
        mne_raw_ids[run] = mne_raw_out

        # --- Stage 2: events. mask=4096+256, mask_type='not_and',
        # consecutive='increasing', min_duration=0.003s (02-extract_events.py).
        events_out = app_step(
            runner, state, f"S{subject}:run{run}:events", "events",
            dataset_ids=[mne_raw_out],
            config={"mask": 4096 + 256, "mask_type": "not_and",
                    "consecutive": "increasing", "min_duration": 0.003},
            tags=[f"S{subject}", f"run{run}"], instance_name=instance_name, dry_run=dry_run,
        )
        events_ids[run] = events_out

        # --- Stage 3: bandpass filter, TWO passes (04-python_filtering.py +
        # the documented "run twice" workaround -- 05-run_ica.py hardcodes
        # highpass-1Hz input regardless of config's l_freq).
        for l_freq, target_dict, pass_name in (
            (None, filtered_none_ids, "highpass-None"),
            (1, filtered_1hz_ids, "highpass-1Hz"),
        ):
            filt_out = app_step(
                runner, state, f"S{subject}:run{run}:filter-raw:{pass_name}", "filter-raw",
                dataset_ids=[mne_raw_out],
                config={"l_freq": l_freq, "h_freq": 40},
                tags=[f"S{subject}", f"run{run}", pass_name], instance_name=instance_name,
                dry_run=dry_run,
            )
            target_dict[run] = filt_out

    # --- Stage 4: concatenate the 6 runs' highpass-1Hz filtered raws (ICA
    # fit input only -- 05-run_ica.py concatenates before fitting).
    print(f"\n===== subject {subject}: subject-level stages =====")
    concat_out = app_step(
        runner, state, f"S{subject}:concat:highpass-1Hz", "concat",
        dataset_ids=[filtered_1hz_ids[r] for r in runs],
        config={},
        tags=[f"S{subject}", "concat", "highpass-1Hz"], instance_name=instance_name, dry_run=dry_run,
    )

    # --- Stage 5: ICA fit. method='fastica', paper value n_components=0.999,
    # reject=dict(grad=4000e-13, mag=4e-12), decim=11, random_state=42.
    # l_freq/h_freq set to match the already-filtered (1-40Hz) input rather
    # than left at the app's own default, to avoid an unintended second
    # filtering pass -- ICA-fit's config schema includes its own l_freq/
    # h_freq keys (it can pre-filter internally), confirmed via `bl app
    # query`, so this needs to be explicit, not assumed harmless.
    # DIAGNOSTIC (user call, 2026-09-03): n_components temporarily dropped
    # to a fixed 20 (int, not a variance fraction) and decim=11 added
    # (matching the original pipeline's own ica.fit(decim=11), now
    # supported by the app -- ICA-fit commit 996f2e2), purely to get a fast
    # end-to-end confirmation that the rest of the chain (report writing,
    # mark-bad-raw, ICA-apply, epoch, ...) all work, decoupled from how
    # long a full 0.999-variance fit takes (67 min, real, not a hang --
    # see ICA-fit commit b46af81's buffering fix). Revert n_components to
    # 0.999 (the paper value) once the chain is confirmed working end to
    # end; decim=11 matches the paper either way and can stay.
    ica_out = app_step(
        runner, state, f"S{subject}:ICA-fit", "ICA-fit",
        dataset_ids=[concat_out],
        config={"method": "fastica", "n_components": 20, "decim": 11,
                "l_freq": 1, "h_freq": 40, "random_state": 42},
        tags=[f"S{subject}"], instance_name=instance_name, dry_run=dry_run,
    )

    clean_epochs_out = {}
    for run in runs:
        # --- Stage 6: mark bad EEG channels (per-subject/run list from this
        # repo's own bads/ files, config key is `bads` -- confirmed via
        # `bl app query`. The app's own main.py does
        # `config['bads'].split(',')` -- a plain string, NOT a list
        # (confirmed via a real AttributeError: 'list' object has no
        # attribute 'split' on the ICM cluster). NOTE: `channels` is NOT a
        # config field despite appearing in main.py's `config['channels']`
        # -- `bl app query` shows it's declared as an optional file-type
        # *input* (a channels.tsv dataset slot). When that input isn't
        # wired, Amaretti never adds a `channels` key to config.json at
        # all, so passing "channels": "" here did nothing (confirmed: it
        # still KeyError'd on the cluster) -- fixed at the source instead
        # (mark-bad-raw commit 119d173, config.get('channels')). Don't pass
        # a `channels` key here; there's no dataset to wire into that slot.
        bad_channels = read_bad_channels(subject, run)
        print(f"S{subject} run{run} bad channels ({len(bad_channels)}): {bad_channels}")
        # NOTE: don't pass "annotations": "" here -- bl-app-run-instanced.js
        # only substitutes an app's declared config default when a key is
        # OMITTED (`userParam === undefined`), never when it's present but
        # blank. Passing "" explicitly defeats that and (for apps whose
        # main.py checks it more strictly than mark-bad-raw's own
        # `config.get("annotations")` does) can misfire the same way `picks`
        # did on `epoch` -- see the stage-8 comment below and
        # [[project_ica_fit_apply_bugfixes]]. Omit rather than blank out any
        # config key we don't have a real value for; let the app's own
        # declared default apply.
        marked_out = app_step(
            runner, state, f"S{subject}:run{run}:mark-bad-raw", "mark-bad-raw",
            dataset_ids=[filtered_none_ids[run]],
            config={"bads": ",".join(bad_channels), "reset_bads": False},
            tags=[f"S{subject}", f"run{run}"], instance_name=instance_name, dry_run=dry_run,
        )

        # --- Stage 7: ICA apply (component exclusion). ICA-apply needs TWO
        # inputs (fif + ica) -- input_ids/dataset_ids must be parallel lists
        # here, not the single-input_id convenience path. ECG via ctps
        # (matches the local pipeline's method, but this app's threshold is
        # hardcoded 'auto', not the local pipeline's explicit 0.8 -- see
        # ICA-apply/main.py, a minor parameter difference not a method one).
        cleaned_out = app_step(
            runner, state, f"S{subject}:run{run}:ICA-apply", "ICA-apply",
            dataset_ids=[marked_out, ica_out], input_id=["fif", "ica"],
            config={"reject_ECG": True, "reject_EOG": True, "EOG_chan": "EOG061",
                    "ECG_chan": "ECG063"},
            tags=[f"S{subject}", f"run{run}"], instance_name=instance_name, dry_run=dry_run,
        )

        # --- Stage 8: epoching. 9 conditions, tmin=-0.2, tmax=2.9,
        # baseline=(None,0) since l_freq=None here (matches 06-make_epochs.py's
        # `baseline = (None, 0) if l_freq is None else None`). Real cluster run
        # found `require_config_keys` demanded picks/metadata_tmin/metadata_tmax
        # up front even though picks='' is a valid "all channels" choice and
        # metadata_* are only used when assess_correctness=True -- fixed at the
        # source (epoch commit 7e9e293). `picks` and `metadata_tmin`/
        # `metadata_tmax` are omitted here rather than sent as ""/0 placeholders
        # -- omitting lets the platform apply the app's own declared default
        # (`userParam === undefined` in bl-app-run-instanced.js), matching how
        # a user leaving a web-UI field blank should behave, project-wide.
        epo_out = app_step(
            runner, state, f"S{subject}:run{run}:epoch", "epoch",
            dataset_ids=[cleaned_out, events_ids[run]], input_id=["raw", "events"],
            config={"event_id_condition_mapping": EVENT_ID_CONDITION_MAPPING,
                    "tmin": -0.2, "tmax": 2.9, "baseline": "None,0",
                    "event1kw": "stimulus", "event2kw": "response",
                    "assess_correctness": False},
            tags=[f"S{subject}", f"run{run}"], instance_name=instance_name, dry_run=dry_run,
        )

        # --- Stage 9: bad-epoch rejection. NOTE the methodological gap in
        # the module docstring -- this app's `autoreject` uses the full
        # AutoReject class, not the local pipeline's
        # `get_rejection_threshold()`. Using the app's own reasonable
        # defaults here (random_state=42 to at least match that one param).
        clean_epo_out = app_step(
            runner, state, f"S{subject}:run{run}:autoreject", "autoreject",
            dataset_ids=[epo_out],
            config={"random_state": 42},
            tags=[f"S{subject}", f"run{run}"], instance_name=instance_name, dry_run=dry_run,
        )
        clean_epochs_out[run] = clean_epo_out

    # --- Stage 10: evoked averaging, per condition (famous/scrambled/
    # unfamiliar at minimum -- NOTE the equalize_epoch_counts gap in the
    # module docstring: faces_eq/scrambled_eq are not reproducible via this
    # app as-is, left out here rather than silently approximated).
    for stim in ("famous", "unfamiliar", "scrambled"):
        for run in runs:
            app_step(
                runner, state, f"S{subject}:run{run}:average-erp:{stim}", "average-erp",
                dataset_ids=[clean_epochs_out[run]],
                # stimulus_names: config['stimulus_names'].split(',') runs
                # unconditionally whenever average_all is False -- must be
                # set (same class of bug as epoch's metadata_* keys).
                # peaks: config['peaks'].split(',') too, unless the literal
                # string "None" -- a Python bool crashes here just like
                # mark-bad-raw's `bads` list did.
                config={"average_all": False, "condition": stim, "stimulus_names": stim,
                        "peaks": "None"},
                tags=[f"S{subject}", f"run{run}", stim], instance_name=instance_name, dry_run=dry_run,
            )

    # --- Stage 11: noise covariance (obVdo/app-noise-covariance-v2, a real
    # existing app -- NOT the confirmed-gap the earlier draft of this
    # driver assumed; found via `bl app query -q baseline`). tmax=0,
    # method='shrunk' (08-make_cov.py). Computed from the first run's
    # cleaned epochs (matching the local pipeline's per-subject, not
    # per-run, covariance).
    app_step(
        runner_cov, state, f"S{subject}:covariance", "noise-covariance",
        dataset_ids=[clean_epochs_out[runs[0]]],
        config={"method": "shrunk", "tmax": 0},
        tags=[f"S{subject}"], instance_name=instance_name, dry_run=dry_run,
    )


def main():
    global MAX_ATTEMPTS
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--subjects", default="10", help="comma-separated BIDS subject numbers (default: 10)")
    parser.add_argument("--runs", default="02", help="comma-separated run numbers (default: 02)")
    parser.add_argument("--fig1-only", action="store_true",
                        help="run only the Fig-1 diagnostic branch (fif2mne+maxwell-filter), "
                             "not the main sensor-space chain")
    parser.add_argument("--max-attempts", type=int, default=MAX_ATTEMPTS,
                        help=f"retries per app-run step before giving up (default: {MAX_ATTEMPTS})")
    args = parser.parse_args()
    subjects = args.subjects.split(",")
    runs = args.runs.split(",")
    MAX_ATTEMPTS = args.max_attempts

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
