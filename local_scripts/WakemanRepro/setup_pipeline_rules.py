#!/usr/bin/env python3
"""
Set up the sensor-space chain (fif2mne -> events -> filter-raw x2 -> concat
-> ICA-fit -> mark-bad-raw -> ICA-apply -> epoch -> autoreject ->
average-erp -> noise-covariance) as brainlife.io Pipeline-tab rules, in
project 5df7efdc32bff02262e226b6.

This is the rule-based counterpart to run_pipeline.py's imperative driver
in this same directory (which does the equivalent one-off `bl app run`
submissions, already proven end-to-end for S09 run02) -- reuses that
script's app ids/branches/configs directly (imported as a module) so the
two can't silently drift apart.

The pipeline itself is subject-agnostic: SUBJECT_MATCH below is the ONLY
place a subject is named anywhere in this design. Every other rule scopes
itself purely via tag-chaining (each stage's output_tags feed the next
stage's input_tags) -- broadening scope to another subject or all of them
later means editing SUBJECT_MATCH alone. mark-bad-raw's bad-channel data
used to be an exception (baked per-subject into rule config) -- fixed
2026-09-04: bad-channel lists are now uploaded neuro/meg/fif-override
channels.tsv datasets (see upload_bad_channels.py), wired in via a real
`channels` input_tags match, so this stage is subject-agnostic too.

Per-run stages are created once per run (6 separate rule objects each,
following the proven S05 precedent in
local_scripts/ReproduceProject/setup_S05_pipeline_rules.py -- rules are not
known to fan out automatically over several matching datasets, so this
mirrors what's actually been confirmed working rather than assuming).
concat/ICA-fit are the two subject-level fan-in stages (one rule object
each, `input_multicount` on concat).

Optional-input gotcha (see plan / BrainlifePipelineCLI/README.md): an
unconfigured optional input silently blocks a rule from ever firing (S05's
`epoch` rule fired zero tasks for exactly this reason). Confirmed by
reading the S05 script directly: the WORKING pattern for "don't wire this
optional input" is `input_selection={"<id>": False}` (boolean, not the
string "ignore" the same script's own unapplied epoch fix suggested and
which was never actually confirmed working). Used here for:
  - noise-covariance's `empty-room`/`evoked`/`ica` optional inputs (using
    only `epochs`)
epoch's own optional `events` input, and (as of 2026-09-04) mark-bad-raw's
own optional `channels` input, ARE wired here (real input_tags), since
this pipeline's proven design uses both.

Usage:
    python3 setup_pipeline_rules.py --dry-run     # print all payloads, create nothing
    python3 setup_pipeline_rules.py               # actually create the rules
"""
import argparse
import sys
from collections import OrderedDict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from create_pipeline_rule import create_rule, list_rules, set_pipeline  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_pipeline import (  # noqa: E402
    APPS, EVENT_ID_CONDITION_MAPPING, FIF2MNE_CHANNEL_FIX,
    PROJECT,
)

SUBJECT_MATCH = "^09$"  # the ONLY subject-specific thing in this whole file
RUNS = ["01", "02", "03", "04", "05", "06"]


def app_id_branch(name):
    app_id, branch, _ = APPS[name]
    return app_id, branch


def make(existing, created, group, name, app_name, active=True, **kwargs):
    """Create one rule (skip if a rule with this name already exists in the
    project -- makes the script safe to re-run), tracking its id under
    `created[group]` so the final pass can nest it in a same-named pipeline
    group."""
    match = next((r for r in existing if r["name"] == name), None)
    if match:
        print(f"[skip] already exists: {name} -> {match['_id']}")
        created.setdefault(group, []).append(match["_id"])
        return

    app_id, branch = app_id_branch(app_name)
    rule = create_rule(
        project=PROJECT, app_id=app_id, name=name,
        branch=branch, active=active,
        dry_run=args.dry_run, **kwargs,
    )
    if args.dry_run:
        print(f"[dry-run] {name}")
    else:
        created.setdefault(group, []).append(rule["_id"])
        print(f"[create] {name} -> {rule['_id']} (active={active})")


def main():
    global args
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    existing = list_rules(PROJECT)
    created = OrderedDict()  # group name -> [rule_id, ...], in pipeline order

    # --- Stage 1: fif2mne (entry point -- the ONLY stage with a subject
    # filter, and the only stage created inactive; every rule here after
    # this one is created active, cascading once this is turned on).
    for run in RUNS:
        make(existing, created, "fif2mne", f"fif2mne - run{run}", "fif2mne",
             active=False,
             subject_match=SUBJECT_MATCH,
             config=dict(FIF2MNE_CHANNEL_FIX),
             input_tags={"fif": ["proc-sss", f"run-{run}"]},
             output_tags={"out_dir": ["fif2mne-out", f"run-{run}"]})

    # --- Stage 2: events
    for run in RUNS:
        make(existing, created, "events", f"events - run{run}", "events",
             config={"mask": 4096 + 256, "mask_type": "not_and",
                     "consecutive": "increasing", "min_duration": 0.003},
             input_tags={"fif": ["fif2mne-out", f"run-{run}"]},
             output_tags={"out_dir": ["events-out", f"run-{run}"]})

    # --- Stage 3: filter-raw, TWO passes (highpass=None for the main
    # chain, highpass=1Hz for ICA-fit only -- see run_pipeline.py's own
    # module docstring for why both are needed)
    for run in RUNS:
        make(existing, created, "filter-raw (lowpass 40Hz)",
             f"filter-raw highpass-None - run{run}", "filter-raw",
             config={"l_freq": None, "h_freq": 40},
             input_tags={"fif": ["fif2mne-out", f"run-{run}"]},
             output_tags={"out_dir": ["filt-raw-lowpass40", f"run-{run}"]})

        make(existing, created, "filter-raw (bandpass 1-40Hz)",
             f"filter-raw highpass-1Hz - run{run}", "filter-raw",
             config={"l_freq": 1, "h_freq": 40},
             input_tags={"fif": ["fif2mne-out", f"run-{run}"]},
             output_tags={"out_dir": ["filt-raw-bandpass1-40", f"run-{run}"]})

    # --- Stage 4: concat (subject-level fan-in, exactly 6 runs)
    make(existing, created, "concat", "concat", "concat",
         config={},
         input_tags={"raw": ["filt-raw-bandpass1-40"]},
         input_multicount={"raw": "6"},
         output_tags={"out_dir": ["concat-out"]})

    # --- Stage 5: ICA-fit (subject-level, real paper value n_components=
    # 0.999 -- NOT the diagnostic 20 used earlier this session purely to
    # get a fast end-to-end mechanics check; decim=11 matches the paper
    # and stays either way)
    make(existing, created, "ICA-fit", "ICA-fit", "ICA-fit",
         config={"method": "fastica", "n_components": 0.999, "decim": 11,
                 "l_freq": 1, "h_freq": 40, "random_state": 42},
         input_tags={"fif": ["concat-out"]},
         output_tags={"out_dir": ["ica-fit-out"]})

    # --- Stage 6: mark-bad-raw. Bad-channel lists now come from uploaded
    # neuro/meg/fif-override channels.tsv datasets (tagged bad-channels +
    # run-NN, one per subject/run -- see upload_bad_channels.py), wired via
    # a real `channels` input_tags match on run alone (subject pairing is
    # automatic via meta.subject/meta.session, per the user). No more
    # `bads` config / read_bad_channels() -- that was the one genuinely
    # subject-specific piece of this whole pipeline, now fixed.
    for run in RUNS:
        make(existing, created, "mark-bad-raw", f"mark-bad-raw - run{run}", "mark-bad-raw",
             config={"reset_bads": False},
             input_tags={"fif": ["filt-raw-lowpass40", f"run-{run}"],
                         "channels": ["bad-channels", f"run-{run}"]},
             output_tags={"out_dir": ["mark-bad-out", f"run-{run}"]})

    # --- Stage 7: ICA-apply (two real inputs: the marked raw + the fitted
    # ICA, both required -- no optional-input handling needed)
    for run in RUNS:
        make(existing, created, "ICA-apply", f"ICA-apply - run{run}", "ICA-apply",
             config={"reject_ECG": True, "reject_EOG": True,
                     "EOG_chan": "EOG061", "ECG_chan": "ECG063"},
             input_tags={"fif": ["mark-bad-out", f"run-{run}"],
                         "ica": ["ica-fit-out"]},
             output_tags={"out_dir": ["ica-apply-out", f"run-{run}"]})

    # --- Stage 8: epoch. events IS wired here (real input_tags), unlike
    # S05's own epoch rule which left it unconfigured and never fired --
    # see this file's module docstring.
    for run in RUNS:
        make(existing, created, "epoch", f"epoch - run{run}", "epoch",
             config={"event_id_condition_mapping": EVENT_ID_CONDITION_MAPPING,
                     "tmin": -0.2, "tmax": 2.9, "baseline": "None,0",
                     "event1kw": "stimulus", "event2kw": "response",
                     "assess_correctness": False},
             input_tags={"raw": ["ica-apply-out", f"run-{run}"],
                         "events": ["events-out", f"run-{run}"]},
             output_tags={"out_dir": ["epoch-out", f"run-{run}"]})

    # --- Stage 9: autoreject
    for run in RUNS:
        make(existing, created, "autoreject", f"autoreject - run{run}", "autoreject",
             config={"random_state": 42, "n_jobs": 8},
             input_tags={"epo": ["epoch-out", f"run-{run}"]},
             output_tags={"out_dir": ["autoreject-out", f"run-{run}"]})

    # --- Stage 10: average-erp. Single rule per run now produces BOTH
    # conditions in one Evoked file (the multi-condition support just
    # added this session), where the old driver needed 3 separate
    # per-condition submissions before that existed.
    #
    # scrambled/famous,scrambled/unfamiliar was WRONG -- confirmed via a
    # real failed task's own error message: "scrambled/famous" doesn't
    # exist as an event name. Only face trials have a famous/unfamiliar
    # split (EVENT_ID_CONDITION_MAPPING's real 9 conditions:
    # face/{famous,unfamiliar}/{first,immediate,long}, and just
    # scrambled/{first,immediate,long} -- no famous/unfamiliar for
    # scrambled, since a scrambled image has no identity). Fixed to plain
    # "scrambled", which pools all 3 scrambled/* sub-conditions via the
    # same partial-tag matching "face/famous,face/unfamiliar" already
    # relies on.
    for run in RUNS:
        make(existing, created, "average-erp", f"average-erp - run{run}", "average-erp",
             config={"average_all": False,
                     "stimulus_names": "face/famous,face/unfamiliar;scrambled",
                     "condition": "face;scrambled", "peaks": "None"},
             input_tags={"evoked": ["autoreject-out", f"run-{run}"]},
             output_tags={"out_dir": ["average-erp-out", f"run-{run}"]})

    # --- Stage 11: noise-covariance. Four optional alternative inputs on
    # this app (empty-room/epochs/evoked/ica) -- only `epochs` is wired,
    # the other three explicitly ignored (same gotcha as mark-bad-raw's
    # `channels`, just three of them here).
    for run in RUNS:
        make(existing, created, "noise-covariance", f"noise-covariance - run{run}", "noise-covariance",
             config={"method": "shrunk", "tmax": 0},
             input_tags={"epochs": ["autoreject-out", f"run-{run}"]},
             input_selection={"empty-room": False, "evoked": False, "ica": False},
             output_tags={"out_dir": ["noise-cov-out", f"run-{run}"]})

    total = sum(len(ids) for ids in created.values())
    print(f"\n{total} rule(s) created/found across {len(created)} groups.")

    pipelines = {
        "type": "group", "name": "", "open": True, "color": "inherit",
        "items": [
            {"type": "group", "name": group, "open": True, "color": "#f0f0f0",
             "items": [{"type": "rule", "ruleId": rid} for rid in rule_ids]}
            for group, rule_ids in created.items()
        ],
    }
    set_pipeline(PROJECT, pipelines, dry_run=args.dry_run)
    if not args.dry_run:
        print("Pipeline tree rebuilt with one group per processing step, "
              "under 'Sensor-space pipeline'.")


if __name__ == "__main__":
    main()
