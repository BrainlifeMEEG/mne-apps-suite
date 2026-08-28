"""
Step 0's crosswalk cross-check (0d), Stage 1 + Stage 2, per the plan at
~/.claude/plans/jazzy-swinging-whistle.md.

For every subject in the crosswalk (cluster/crosswalk.py), compares W&H's
own per-run EEG bad-channel lists (original_scripts/bads/<name>/) against
an automated outlier score computed on that subject's own raw EEG data:

- Stage 1 (count screen): does the automated detector flag roughly the
  same NUMBER of channels per run as W&H's own file lists?
- Stage 2 (name match): for runs where the counts are close, do the
  SPECIFIC channel names overlap?

S09 (openfMRI 10, BIDS sub-09) needs neither stage -- already verified
against the paper's own Figure 2 -- but its known result (run02: exactly
EEG006/013/023/034/043/045/047, 7 channels; run01: 0) is used here to
CALIBRATE the detector's threshold before trusting it on the other 15.

Detector (v2, after calibration against S09 showed v1 -- a plain
across-channel z-score within one run -- fails badly: it keeps flagging
the SAME few channels in every run, including run01 where W&H found
nothing at all, and misses channels W&H did flag. That's a real signature
of picking up persistent per-channel quirks -- electrode placement,
baseline impedance -- rather than acute, run-specific badness. Fixed by
comparing each channel against ITS OWN baseline across that subject's
other 5 runs instead of against other channels within one run):

Retype channels exactly as 02/04 do (EEG061/62/63/64 -> EOG/EOG/ECG/misc),
pick remaining EEG channels, 1 Hz highpass, per-channel log10(variance)
per run -> a (channel x run) matrix per subject. For each channel, compute
its median/MAD ACROSS ITS OWN 6 RUNS, then flag (channel, run) as an
outlier if that run's value is a robust z-score outlier relative to the
channel's own other-run baseline. This targets "unusual for this channel,
in this run" rather than "unusual for this run, among channels."
"""
import os
import sys

import numpy as np
import mne

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "cluster"))
from crosswalk import OPENFMRI_TO_BIDS  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "original_scripts"))
from library.config import map_subjects  # noqa: E402

FARM_DS117 = (
    "/network/iss/cenir/analyse/meeg/BRAINLIFE/code/local_scripts/"
    "WakemanRepro/derivatives/biomag_repro/ds117"
)
BADS_DIR = (
    "/network/iss/cenir/analyse/meeg/BRAINLIFE/code/local_scripts/"
    "WakemanRepro/original_scripts/bads"
)


def wh_bads(openfmri_id, run):
    name = map_subjects[openfmri_id]
    path = os.path.join(BADS_DIR, name, f"run_{run:02d}_raw_tr.fif_bad")
    if not os.path.exists(path):
        return set()
    with open(path) as f:
        return {line.strip() for line in f if line.strip()}


def _logvar_matrix(openfmri_id):
    """Return (ch_names, logvar) where logvar is a (6 runs, n_ch) array of
    per-channel log10(variance), one row per run, for this subject."""
    sub_of = "sub%03d" % openfmri_id
    rows = []
    ch_names = None
    for run in range(1, 7):
        raw_path = os.path.join(FARM_DS117, sub_of, "MEG", f"run_{run:02d}_raw.fif")
        raw = mne.io.read_raw_fif(raw_path, preload=True, verbose="error")
        raw.set_channel_types(
            {"EEG061": "eog", "EEG062": "eog", "EEG063": "ecg", "EEG064": "misc"},
            verbose="error",
        )
        raw.filter(1.0, None, picks="eeg", verbose="error")
        picks = mne.pick_types(raw.info, eeg=True, exclude=())
        names = [raw.ch_names[i] for i in picks]
        if ch_names is None:
            ch_names = names
        assert names == ch_names, "channel order changed between runs"
        data = raw.get_data(picks=picks)
        rows.append(np.log10(data.var(axis=1) + 1e-30))
    return ch_names, np.array(rows)  # (6, n_ch)


def _zscores(logvar, remove_run_level):
    """logvar: (6, n_ch). Two-way normalization: optionally remove each
    run's own overall level (median across channels) first -- isolates
    per-channel badness from session-wide drift (electrode drying,
    warm-up) that shifts ALL channels together in a given run -- then
    take each channel's robust z-score across its own 6 runs."""
    L = logvar.copy()
    if remove_run_level:
        L = L - np.median(L, axis=1, keepdims=True)
    med = np.median(L, axis=0)
    mad = np.median(np.abs(L - med), axis=0) * 1.4826 + 1e-6
    return (L - med) / mad


def detect_bads_per_run(ch_names, logvar, threshold, remove_run_level=True):
    z = _zscores(logvar, remove_run_level)
    out = {}
    for run_idx in range(6):
        out[run_idx + 1] = {ch_names[i] for i in range(len(ch_names))
                             if abs(z[run_idx, i]) > threshold}
    return out


THRESHOLD = 3.0  # calibrated against S09's known ground truth, see docstring


def run_full_crosscheck():
    print("=== Stage 1 (count) + Stage 2 (name overlap) cross-check ===")
    print(f"Detector calibrated against S09 (run01=0 want, run02=7 want): at "
          f"threshold={THRESHOLD} it recovers run01=['EEG030','EEG073'] "
          f"(2 false positives vs 0 true), run02=['EEG006','EEG043','EEG044',"
          f"'EEG045','EEG047'] (4/7 true positives + 1 false positive). This is "
          f"an approximate screen, not a precise replication of manual curation "
          f"-- treat 'close' counts as plausible, not as proof.\n")

    rows = []
    for openfmri_id in sorted(OPENFMRI_TO_BIDS):
        sub_bids = OPENFMRI_TO_BIDS[openfmri_id]
        name = map_subjects[openfmri_id]
        print(f"--- openfMRI sub{openfmri_id:03d} / {name} / BIDS {sub_bids} ---",
              flush=True)
        ch_names, logvar = _logvar_matrix(openfmri_id)
        detected = detect_bads_per_run(ch_names, logvar, THRESHOLD, remove_run_level=True)
        for run in range(1, 7):
            wh = wh_bads(openfmri_id, run)
            det = detected[run]
            overlap = wh & det
            row = dict(
                openfmri_id=openfmri_id, name=name, sub_bids=sub_bids, run=run,
                wh_count=len(wh), det_count=len(det),
                overlap_count=len(overlap), wh=sorted(wh), det=sorted(det),
            )
            rows.append(row)
            close = abs(row["wh_count"] - row["det_count"]) <= 2
            flag = "" if close else "  <-- COUNT MISMATCH"
            print(f"  run{run:02d}: W&H={row['wh_count']:2d} {row['wh']} | "
                  f"detected={row['det_count']:2d} {row['det']} | "
                  f"overlap={row['overlap_count']}{flag}", flush=True)
    return rows


if __name__ == "__main__":
    rows = run_full_crosscheck()
    import json
    out_path = os.path.join(os.path.dirname(__file__), "crosswalk_crosscheck_results.json")
    with open(out_path, "w") as f:
        json.dump(rows, f, indent=2)
    print(f"\nSaved full results to {out_path}")
