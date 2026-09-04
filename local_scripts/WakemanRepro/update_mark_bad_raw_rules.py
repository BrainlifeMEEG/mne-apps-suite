#!/usr/bin/env python3
"""One-shot fixup for the 6 live `mark-bad-raw` Pipeline-tab rules in project
5df7efdc32bff02262e226b6: drop the baked-in, subject-specific `config.bads`
list and wire the `channels` input for real via `input_tags`, now that
per-(subject, run) channels.tsv datasets exist on the platform (see
upload_bad_channels.py). See ~/.claude/plans/jazzy-swinging-whistle.md,
"mark-bad-raw via uploaded channels.tsv, not baked-in config".

Run once, after the upload is confirmed live via `bl data query`. Idempotent
in effect (re-running just PUTs the same target state again), but not
guarded against re-running -- no need, it's a fixed target state.

Usage:
    python3 update_mark_bad_raw_rules.py --dry-run
    python3 update_mark_bad_raw_rules.py
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from create_pipeline_rule import update_rule  # noqa: E402

# name -> rule_id, from setup_pipeline_rules.py --dry-run's "[skip] already
# exists" output (2026-09-04).
RULE_IDS = {
    "01": "6a9ae20d0efc94c8a6bc776a",
    "02": "6a9ae20e0efc94c8a6bc7779",
    "03": "6a9ae20e0efc94c8a6bc7785",
    "04": "6a9ae20f0efc94c8a6bc778d",
    "05": "6a9ae2100efc94c8a6bc77a2",
    "06": "6a9ae2100efc94c8a6bc77b1",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    for run, rule_id in RULE_IDS.items():
        payload = dict(
            config={"bads": "", "reset_bads": False, "annotations": ""},
            input_tags={"fif": ["filt-raw-lowpass40", f"run-{run}"],
                        "channels": ["bad-channels", f"run-{run}"]},
            input_selection={},
        )
        print(f"run{run} ({rule_id}):")
        update_rule(rule_id, dry_run=args.dry_run, **payload)


if __name__ == "__main__":
    main()
