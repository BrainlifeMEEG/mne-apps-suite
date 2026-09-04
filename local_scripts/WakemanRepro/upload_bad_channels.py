#!/usr/bin/env python3
"""Upload per-(subject, run) bad-channel lists to brainlife.io as
neuro/meg/fif-override datasets, so the Pipeline-tab `mark-bad-raw` rules can
wire them in via a real `input_tags={"channels": [...]}` match instead of
`config.bads` baked at rule-creation time (which was subject-specific -- see
~/.claude/plans/jazzy-swinging-whistle.md, "mark-bad-raw via uploaded
channels.tsv, not baked-in config").

Source data: original_scripts/bads/<W&H name>/run_NN_raw_tr.fif_bad, the same
files `run_pipeline.py`'s own `read_bad_channels()` already reads (in turn
the same files `original_scripts/06-make_epochs.py` -- "06. Construct
epochs" -- reads for this exact purpose). Reused directly here, not
reimplemented.

For every BIDS subject in BIDS_TO_OPENFMRI x runs 01-06: write a minimal
2-column (name, status) TSV of just the bad channels (mark-bad-raw's own
main.py only acts on rows where status.lower()=='bad' -- good channels don't
need listing), then `bl data upload` it as neuro/meg/fif-override, tagged
`bad-channels` + `run-NN` (via --run), with --subject <NN> --session meg
matching this project's existing meta.subject/meta.session convention
exactly (bare numeric subject, literal "meg" session -- confirmed against
every other dataset already in this project).

Every (subject, run) combination gets a file uploaded, including
zero-bad-channel ones (a valid TSV with just a header row) -- mark-bad-raw
needs something to match for every run once `channels` is wired via a real
input_tags entry instead of input_selection={"channels": False}.

Usage:
    python upload_bad_channels.py --dry-run
    python upload_bad_channels.py --dry-run --subjects 09,10
    python upload_bad_channels.py                    # real upload, all 19 subjects x 6 runs
    python upload_bad_channels.py --subjects 09       # real upload, just S09
"""
import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from run_pipeline import PROJECT, BIDS_TO_OPENFMRI, read_bad_channels, wh_subject_name  # noqa: E402

RUNS = ["01", "02", "03", "04", "05", "06"]
SCRATCH_DIR = Path("/tmp/claude-19108/-network-iss-cenir-analyse-meeg-BRAINLIFE-code/37ec2ce5-5e5a-4acb-b763-97da5ecc2f6a/scratchpad/bad_channels_tsv")


def make_tsv(bids_subject, run):
    """Write name/status TSV of bad channels for one (subject, run) to
    SCRATCH_DIR; returns (path, list_of_channel_names)."""
    bads = read_bad_channels(bids_subject, run)
    SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
    out_path = SCRATCH_DIR / f"sub-{bids_subject}_run-{run}_channels.tsv"
    with open(out_path, "w") as f:
        f.write("name\tstatus\n")
        for ch in bads:
            f.write(f"{ch}\tbad\n")
    return out_path, bads


def upload_one(bids_subject, run, tsv_path, dry_run):
    cmd = [
        "bl", "data", "upload",
        "--project", PROJECT,
        "--datatype", "neuro/meg/fif-override",
        "--subject", bids_subject,
        "--session", "meg",
        "--run", run,
        "--tag", "bad-channels",
        "--desc", f"Bad channels, subject {bids_subject} run {run} (from original_scripts/bads/, W&H "
                  f"{wh_subject_name(bids_subject)[0]})",
        "--channels", str(tsv_path),
    ]
    if dry_run:
        print("  [dry-run] " + " ".join(cmd))
        return None
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  FAILED (exit {result.returncode}): {result.stdout}\n{result.stderr}")
        return False
    print(f"  uploaded: {result.stdout.strip()}")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--subjects", default=None, help="comma-separated BIDS subject numbers, e.g. 09,10 (default: all)")
    ap.add_argument("--runs", default=",".join(RUNS))
    args = ap.parse_args()

    subjects = args.subjects.split(",") if args.subjects else sorted(BIDS_TO_OPENFMRI.keys())
    runs = args.runs.split(",")

    n_ok, n_fail, n_skip = 0, 0, 0
    for bids_subject in subjects:
        try:
            wh_name, _ = wh_subject_name(bids_subject)
        except ValueError as e:
            print(f"sub-{bids_subject}: skipping ({e})")
            n_skip += len(runs)
            continue
        for run in runs:
            try:
                tsv_path, bads = make_tsv(bids_subject, run)
            except FileNotFoundError as e:
                print(f"sub-{bids_subject} run {run}: skipping ({e})")
                n_skip += 1
                continue
            print(f"sub-{bids_subject} ({wh_name}) run {run}: {len(bads)} bad channel(s) -> {tsv_path}")
            ok = upload_one(bids_subject, run, tsv_path, args.dry_run)
            if ok is True:
                n_ok += 1
            elif ok is False:
                n_fail += 1

    print(f"\nDone. uploaded={n_ok} failed={n_fail} skipped={n_skip} "
          f"({'dry-run, nothing actually uploaded' if args.dry_run else 'real uploads'})")
    if n_fail:
        sys.exit(1)


if __name__ == "__main__":
    main()
