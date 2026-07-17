#!/usr/bin/env python3
"""
Set up the full BrainlifeMEEG sensor-level pipeline as brainlife.io pipeline
rules (Pipeline-tab automation), scoped to subject S05 only, in project
6a5939af13254aef69aecae4 ("New Latinus data analysis").

This is the rule-based counterpart to replicate_pipeline.py in this same
directory (which does the equivalent one-off `bl app run` submissions) --
reuses that script's app ids and configs directly so the two can't silently
drift apart. See /home/maximilien.chaumon/.claude/plans/ok-i-d-like-to-rustling-pony.md
for the full design rationale (tag scheme, why concat needs
input_multicount=4 not 5, why the Secondpass drop moved to after ICA apply).

All rules are created `active: false` -- review on
https://brainlife.io/project/6a5939af13254aef69aecae4/pipeline and activate
yourself once you've checked the config.

Usage:
    python3 setup_S05_pipeline_rules.py --dry-run     # print all 29 payloads, create nothing
    python3 setup_S05_pipeline_rules.py               # actually create the rules
"""
import argparse
import sys
from collections import OrderedDict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from create_pipeline_rule import create_rule, list_rules, set_pipeline  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from replicate_pipeline import (  # noqa: E402
    APPS, EGI2MNE_CONFIG, MARK_BAD_RAW_CONFIG, ADD_MONTAGE_CONFIG,
    FILTER_CONFIG, FILTER_EPO_CONFIG, EPOCH_CONFIG, RereferenceConfig,
    ICA_FIT_CONFIG, ICA_APPLY_CONFIG, INTERPOLATE_CONFIG,
    APPLY_BASELINE_CONFIG, EVOKED_AVERAGED_CONFIG, CONDITIONS,
)

PROJECT = "6a5939af13254aef69aecae4"
SUBJECT_MATCH = "^S05"
RUNS = ["Run1", "Run2", "Run3", "Run4", "Run5"]


def make(existing, created, group, name, app_name, **kwargs):
    """Create one rule (skip if a rule with this name already exists in the
    project -- makes the script safe to re-run), tracking its id under
    `created[group]` so the final pass can nest it in a same-named pipeline
    group."""
    match = next((r for r in existing if r["name"] == name), None)
    if match:
        print(f"[skip] already exists: {name} -> {match['_id']}")
        created.setdefault(group, []).append(match["_id"])
        return

    rule = create_rule(
        project=PROJECT, app_id=APPS[app_name], name=name,
        branch="v1.0", subject_match=SUBJECT_MATCH, active=False,
        dry_run=args.dry_run, **kwargs,
    )
    if args.dry_run:
        print(f"[dry-run] {name}")
    else:
        created.setdefault(group, []).append(rule["_id"])
        print(f"[create] {name} -> {rule['_id']}")


def main():
    global args
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    existing = list_rules(PROJECT)
    created = OrderedDict()  # group name -> [rule_id, ...], in pipeline order

    # Steps 1-3: per run (egi2mne -> mark-bad-raw -> add-montage)
    for run in RUNS:
        make(existing, created, "egi2mne", f"Import EGI - Task1 {run}", "egi2mne",
             config=EGI2MNE_CONFIG,
             input_tags={"egi1": ["Task1", run]},
             output_tags={"out_dir": ["egi2mne", "Task1", run]})

        make(existing, created, "Mark Bad Channels", f"Mark Bad Channels - {run}", "mark-bad-raw",
             config=MARK_BAD_RAW_CONFIG,
             input_tags={"fif": ["egi2mne", run], "channels": ["bad-channels"]},
             input_selection={"channels": False},
             output_tags={"out_dir": ["mark_bad_channels", run]})

        make(existing, created, "Add Montage", f"Add Montage - {run}", "add-montage",
             config=ADD_MONTAGE_CONFIG,
             input_tags={"raw": ["mark_bad_channels", run]},
             output_tags={"out_dir": ["with_montage", run]})

    # Step 4: concat (fan-in exactly 4 runs -- S05 has no Run5 data in this
    # project; see plan for why this must be an exact count, not "at least")
    make(existing, created, "Concatenate", "Concatenate 4 runs - S05", "concat",
         config={},
         input_tags={"raw": ["with_montage"]},
         input_multicount={"raw": "4"},
         output_tags={"out_dir": ["concatenated", "Task1"]})

    # Step 5: filter-raw
    make(existing, created, "Filter raw", "Filter raw", "filter-raw",
         config=FILTER_CONFIG,
         input_tags={"fif": ["concatenated"]},
         output_tags={"out_dir": ["filtered_raw"]})

    # Step 6: epoch
    make(existing, created, "Epoch", "Epoch", "epoch",
         config=EPOCH_CONFIG,
         input_tags={"raw": ["filtered_raw"]},
         output_tags={"out_dir": ["epoched"]})

    # Step 7: drop-bad-epo (Firstpass)
    make(existing, created, "Drop bad epochs (Firstpass)", "Drop bad epochs (Firstpass)", "drop-bad-epo",
         config={"drop": ""},
         input_tags={"epo": ["epoched"], "events": ["bad-epochs", "Firstpass"]},
         input_selection={"events": False},
         output_tags={"out_dir": ["dropped_firstpass"]})

    # Step 8: rereference (on Firstpass-dropped data)
    make(existing, created, "Rereference", "Rereference", "rereference",
         config=RereferenceConfig,
         input_tags={"epoch": ["dropped_firstpass"]},
         output_tags={"out_dir": ["rereferenced"]})

    # Step 9: ica-fit-epo
    make(existing, created, "ICA fit", "ICA fit", "ica-fit-epo",
         config=ICA_FIT_CONFIG,
         input_tags={"data": ["rereferenced"]},
         output_tags={"out_dir": ["ica_fit"]})

    # Step 10: ICA-apply-epo
    make(existing, created, "ICA apply", "ICA apply", "ICA-apply-epo",
         config=ICA_APPLY_CONFIG,
         input_tags={"epo": ["rereferenced"], "ica": ["ica_fit"]},
         output_tags={"out_dir": ["ica_applied"]})

    # Step 11: drop-bad-epo (Secondpass) -- after ICA apply, per user correction
    make(existing, created, "Drop bad epochs (Secondpass)", "Drop bad epochs (Secondpass)", "drop-bad-epo",
         config={"drop": ""},
         input_tags={"epo": ["ica_applied"], "events": ["bad-epochs", "Secondpass"]},
         input_selection={"events": False},
         output_tags={"out_dir": ["dropped_secondpass"]})

    # Step 12: filter-epo
    make(existing, created, "Filter epo", "Filter epo", "filter-epo",
         config=FILTER_EPO_CONFIG,
         input_tags={"fif": ["dropped_secondpass"]},
         output_tags={"out_dir": ["filtered_epo"]})

    # Step 13: interpolate
    make(existing, created, "Interpolate", "Interpolate", "interpolate",
         config=INTERPOLATE_CONFIG,
         input_tags={"fif01": ["filtered_epo"]},
         output_tags={"out_dir": ["interpolated"]})

    # Step 14: apply-baseline
    make(existing, created, "Apply baseline", "Apply baseline", "apply-baseline",
         config=APPLY_BASELINE_CONFIG,
         input_tags={"epoch": ["interpolated"]},
         output_tags={"out_dir": ["baselined"]})

    # Step 15: evoked-averaged
    make(existing, created, "Evoked averaged", "Evoked averaged", "evoked-averaged",
         config=EVOKED_AVERAGED_CONFIG,
         input_tags={"fif": ["baselined"]},
         output_tags={"out_dir": ["evoked"]})

    # Step 16-17: average-erp, once per condition
    for condition, cond_cfg in CONDITIONS.items():
        make(existing, created, "Average ERP", f"Average ERP - {condition}", "average-erp",
             config={"condition": condition, **cond_cfg},
             input_tags={"evoked": ["evoked"]},
             output_tags={"out_dir": ["average_erp", condition]})

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
        print("Pipeline tree rebuilt with one group per processing step.")


if __name__ == "__main__":
    main()
