#!/usr/bin/env python3
"""Recreate paper Figure 1 (subject 10, run 02).

Paper caption (Frontiers 2018, Fig 1): "Evoked responses (filtered between
1 and 40 Hz) in the magnetometer channels from (A) unprocessed data, (B)
data processed with maxwell_filter in MNE, and (C) the difference between
data processed using maxwell_filter and Elekta MaxFilter(TM). The colors
show the sensor position, with (x, y, z) sensor coordinates converted to
(R, G, B) values, respectively."

So: butterfly plots (one trace per magnetometer, colored by sensor
position), not a GFP summary -- and the data is 1-40 Hz filtered before
plotting in all panels. The brief only asks for panels A and B; C (the
MNE-vs-Elekta difference) is included too since it's a natural validation
check given the data is already on hand.

Confirmed against the actual mne-biomag-group-demo script
(03-maxwell_filtering.py) that there is NO mne.chpi.filter_chpi() call
anywhere in the published pipeline -- an earlier draft of this figure used
that step and got a superficially similar-looking result, but for the
wrong reason. The real recipe: maxwell_filter(calibration=..., cross_talk=...,
st_duration=..., origin=..., destination=..., head_pos=...) with bad
channels read from a MaxFilter log file, then raw.filter(None, 40) (MEG)
before plotting. This script currently only supplies calibration/cross_talk
(from OpenNeuro's shared sss_cal.dat/ct_sparse.fif) -- st_duration (tSSS),
destination, head_pos (movement compensation), and the MaxFilter-log bad
channel list are not yet reproduced (open question in Strategy.md). Even
without those, calibration + cross_talk + a plain 1-40 Hz post-filter
already gets close to Elekta's reference (~2.6x apart in std, vs. ~100x
apart before filtering).

Inputs are local files in data_cache/S10_run02/:
  - unprocessed_raw.fif                 <- fif2mne output (re-saved raw, no SSS)
  - mne_maxwellfilter_calibrated_only_meg.fif
        <- mne.preprocessing.maxwell_filter(calibration=..., cross_talk=...),
           run locally (NOT the brainlife.io maxwell-filter app's own
           output -- that app has no wiring for a shared calibration
           input yet; see mne_maxwellfilter_meg.fif for that app's actual
           output, kept for reference)
  - elekta_maxfilter_meg.fif            <- pre-existing "proc-sss" staged
        dataset (subject 10 run02, tags ["proc-sss", "run-02"])
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
    "A. Unprocessed": DATA_DIR / "unprocessed_raw.fif",
    "B. MNE maxwell_filter": DATA_DIR / "mne_maxwellfilter_calibrated_only_meg.fif",
}
ELEKTA_PATH = DATA_DIR / "elekta_maxfilter_meg.fif"


def sensor_rgb(info, picks):
    """(x, y, z) sensor position -> (R, G, B), each channel's own position
    linearly rescaled into [0, 1] across the picked sensors -- mirrors the
    paper's stated color scheme."""
    locs = np.array([info["chs"][p]["loc"][:3] for p in picks])
    mins, maxs = locs.min(axis=0), locs.max(axis=0)
    return (locs - mins) / (maxs - mins)


def load_evoked(fif_path, tmin=-0.2, tmax=0.8, l_freq=1.0, h_freq=40.0):
    raw = mne.io.read_raw_fif(fif_path, allow_maxshield=True, verbose=False)
    raw.load_data(verbose=False)
    events = mne.find_events(raw, stim_channel="STI101", shortest_event=1, verbose=False)
    events = events[np.isin(events[:, 2], STIM_CODES)]
    events[:, 2] = 1
    raw.filter(l_freq, h_freq, picks="meg", verbose=False)
    epochs = mne.Epochs(
        raw, events, event_id={"stimulus": 1}, tmin=tmin, tmax=tmax,
        baseline=(tmin, 0), picks="mag", preload=True, verbose=False,
    )
    return epochs.average()


def butterfly(ax, evoked, colors, title, ylim=None):
    times_ms = evoked.times * 1000
    data_ft = evoked.data * 1e15
    for i in range(data_ft.shape[0]):
        ax.plot(times_ms, data_ft[i], color=colors[i], lw=0.6)
    ax.axvline(0, color="k", lw=0.5, ls="--")
    ax.set(xlabel="Time (ms)", ylabel="fT", title=title)
    if ylim is not None:
        ax.set_ylim(ylim)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(Path(__file__).parent / "figure1_maxfilter_comparison.png"))
    args = parser.parse_args()

    evokeds = {}
    for label, path in BRANCHES.items():
        evokeds[label] = load_evoked(path)
        print(f"{label}: {len(evokeds[label].ch_names)} magnetometers, "
              f"std={evokeds[label].data.std()*1e15:.1f} fT")

    elekta = load_evoked(ELEKTA_PATH)
    print(f"Elekta MaxFilter: std={elekta.data.std()*1e15:.1f} fT")

    picks = mne.pick_types(evokeds["A. Unprocessed"].info, meg="mag")
    colors = sensor_rgb(evokeds["A. Unprocessed"].info, picks)

    diff = evokeds["B. MNE maxwell_filter"].copy()
    diff.data = evokeds["B. MNE maxwell_filter"].data - elekta.data

    fig, axes = plt.subplots(1, 3, figsize=(16, 4.5))
    butterfly(axes[0], evokeds["A. Unprocessed"], colors, "A. Unprocessed")
    butterfly(axes[1], evokeds["B. MNE maxwell_filter"], colors, "B. MNE maxwell_filter", ylim=axes[0].get_ylim())
    butterfly(axes[2], diff, colors, "C. MNE − Elekta MaxFilter (difference)", ylim=axes[1].get_ylim())

    fig.suptitle("Figure 1 (reproduction) — Subject 10, Run 02 — magnetometers, 1–40 Hz")
    fig.tight_layout()
    fig.savefig(args.out, dpi=150)
    print(f"saved {args.out}")


if __name__ == "__main__":
    main()
