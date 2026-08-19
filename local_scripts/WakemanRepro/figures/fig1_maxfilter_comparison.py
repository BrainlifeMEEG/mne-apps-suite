#!/usr/bin/env python3
"""Recreate paper Figure 1 A/B (subject 10, run 02).

Paper caption: "Evoked responses in magnetometer channels comparing
unprocessed data, MNE maxwell_filter, and Elekta MaxFilter outputs; shows
clear 100 ms post-stimulus peaks in filtered data."

Panel A: magnetometer GFP, full epoch window.
Panel B: zoom around the ~100 ms post-stimulus peak.

Inputs are local files in data_cache/S10_run02/:
  - unprocessed_raw.fif          <- fif2mne output (re-saved raw, no SSS)
  - mne_maxwellfilter_proper_meg.fif
        <- mne.chpi.filter_chpi() THEN mne.preprocessing.maxwell_filter()
           (calibration/cross_talk from OpenNeuro's shared sss_cal.dat /
           ct_sparse.fif), run locally -- NOT the brainlife.io
           maxwell-filter app's own output (that app doesn't call
           filter_chpi() and has no wiring for a shared calibration input;
           see data_cache/S10_run02/mne_maxwellfilter_meg.fif for that
           app's actual, noisier output, kept for comparison/reference)
  - elekta_maxfilter_meg.fif     <- pre-existing "proc-sss" staged dataset
      (subject 10 run02, tags ["proc-sss", "run-02"])

Debugging note: the first pass at this figure showed the MNE-SSS branch
~20x noisier than Elekta's reference, with a strong ~7 Hz beat-frequency
oscillation riding on the signal -- residual cHPI coil artifact (head
coils run continuously at 293/307/314/321/328 Hz for this dataset; SSS's
spatial separation does not remove them, since they're near-field sources
much like the brain itself). Calibration/cross_talk and auto-bad-channel
detection were tested first and ruled out (near-zero effect); filter_chpi()
before maxwell_filter was the actual fix.

All three stimulus types (Famous/Unfamiliar/Scrambled) are merged into one
condition here -- this figure is about the SSS/MaxFilter comparison, not
condition contrasts (those come in later figures).
"""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mne
import numpy as np

DATA_DIR = Path(__file__).parent.parent / "data_cache" / "S10_run02"
STIM_CODES = [5, 6, 7, 13, 14, 15, 17, 18, 19]  # Famous/Unfamiliar/Scrambled onsets

BRANCHES = {
    "Unprocessed": DATA_DIR / "unprocessed_raw.fif",
    "MNE maxwell_filter": DATA_DIR / "mne_maxwellfilter_proper_meg.fif",
    "Elekta MaxFilter": DATA_DIR / "elekta_maxfilter_meg.fif",
}
COLORS = {
    "Unprocessed": "gray",
    "MNE maxwell_filter": "C0",
    "Elekta MaxFilter": "C1",
}


def load_evoked(fif_path, label, tmin=-0.2, tmax=0.5):
    raw = mne.io.read_raw_fif(fif_path, allow_maxshield=True, verbose=False)
    raw.load_data(verbose=False)
    events = mne.find_events(raw, stim_channel="STI101", shortest_event=1, verbose=False)
    events = events[np.isin(events[:, 2], STIM_CODES)]
    events[:, 2] = 1
    epochs = mne.Epochs(
        raw, events, event_id={"stimulus": 1}, tmin=tmin, tmax=tmax,
        baseline=(tmin, 0), picks="mag", preload=True, verbose=False,
    )
    evoked = epochs.average()
    print(f"{label}: {len(epochs)} epochs, {len(evoked.ch_names)} magnetometers")
    return evoked


def gfp_ft(evoked):
    return np.sqrt((evoked.data ** 2).mean(axis=0)) * 1e15


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(Path(__file__).parent / "figure1_maxfilter_comparison.png"))
    args = parser.parse_args()

    evokeds = {label: load_evoked(path, label) for label, path in BRANCHES.items()}

    fig, (axA, axB) = plt.subplots(1, 2, figsize=(12, 4.5))
    for label, evoked in evokeds.items():
        times_ms = evoked.times * 1000
        g = gfp_ft(evoked)
        axA.plot(times_ms, g, label=label, color=COLORS[label])
        axB.plot(times_ms, g, label=label, color=COLORS[label])

    axA.axvline(0, color="k", lw=0.5, ls="--")
    axA.set(xlabel="Time (ms)", ylabel="GFP (fT)", title="A. Magnetometer GFP, full epoch")
    axA.legend(fontsize=8)

    axB.axvline(100, color="k", lw=0.5, ls=":")
    axB.set(xlabel="Time (ms)", ylabel="GFP (fT)", title="B. Zoom around ~100 ms peak", xlim=(0, 250))

    fig.suptitle("Figure 1 (reproduction) — Subject 10, Run 02: Maxwell filtering comparison")
    fig.tight_layout()
    fig.savefig(args.out, dpi=150)
    print(f"saved {args.out}")


if __name__ == "__main__":
    main()
