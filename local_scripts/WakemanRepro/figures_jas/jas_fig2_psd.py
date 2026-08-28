#!/usr/bin/env python3
"""Recreate paper Figure 2.

Paper caption (Frontiers 2018, Fig 2): "Power spectral density per channel
for subject 10, run 02. (A) Log scale for the x axis accentuates low
frequency drifts in the data. The red lines show the PSD for the bad
channels marked manually and provided to us by Wakeman and Henson (2015).
(B) The same data with a linear x-axis scale. Five peaks corresponding to
HPI coils around 300 Hz are visible and marked in gray dotted lines
alongside the power line frequency (50 Hz)."

Confirmed against the actual mne-biomag-group-demo script
(scripts/results/demos/plot_psd.py) that this is EEG channels only (not
MEG), computed on the raw (pre-SSS) data, with EEG061/062 remapped to EOG
and EEG063 to ECG before picking. fmin=0, fmax=350 both panels.

Subject-numbering gotcha (important, easy to get silently wrong,
resolved 2026-08-20): the mne-biomag-group-demo repo's bad-channel files
live under scripts/processing/bads/subject_NN/, using the ORIGINAL
Wakeman & Henson (2015) numbering (19 subjects, 3 excluded) -- NOT
ds000117's BIDS sub-NN numbering, and the two are NOT the same sequence
shifted by a constant. ds000117's own README has the authoritative
crosswalk table between four numbering schemes. The paper's own
"subject 10" turns out to mean the demo's map_subjects dict KEY 10 (=
W&H "subject_12"), which the README crosswalk maps to BIDS **sub-09** --
confirmed because subject_12/run_02's bad-channel list (7 channels)
visually matches the several red lines in the paper's actual published
Figure 2, whereas BIDS sub-10 (= W&H "subject_15" via the same crosswalk,
NOT "subject_10" -- that naming coincidence is a trap, it's actually
BIDS sub-07) has zero marked bad channels in any run and doesn't match
the published figure at all. Default subject here is therefore 09.

Input: data_cache/S<subject>_run<run>/unprocessed_raw.fif (fif2mne
output, no SSS applied -- matches the demo script, which runs PSD on raw
data).
"""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mne
import numpy as np

CACHE_ROOT = Path(__file__).parent.parent / "data_cache"

# BIDS subject -> W&H subject_NN bad-channel list, run 02 (see docstring).
# Source: scripts/processing/bads/<W&H name>/run_02_raw_tr.fif_bad in
# mne-tools/mne-biomag-group-demo.
BAD_CHANNELS_RUN02 = {
    "09": ["EEG006", "EEG013", "EEG023", "EEG034", "EEG043", "EEG045", "EEG047"],  # W&H subject_12
    "10": [],  # W&H subject_15 -- genuinely no bad channels marked
}

LINE_FREQ = 50
HPI_FREQS = [293, 307, 314, 321, 328]


def load_eeg_raw(raw_path, bad_channels):
    raw = mne.io.read_raw_fif(raw_path, allow_maxshield=True, verbose=False)
    raw.load_data(verbose=False)
    # EEG064 is a permanently free-floating (unconnected) electrode for
    # this system/study -- explicitly excluded in the actual plot_psd.py
    # source (retyped "misc", with that exact comment) before picking EEG
    # channels. Missed in an earlier draft of this script (only found via
    # fetching the script's literal raw text, not an AI-summarized read of
    # it -- the summary silently dropped this 4th remapping). Left in
    # without exclusion, it shows a ~10dB-lower baseline and an unrelated
    # ~39 Hz harmonic series (39/78/117/156/195/234 Hz) picked up as
    # ambient interference, having nothing to do with line noise (50 Hz)
    # or the cHPI coils (293-328 Hz) -- consistent with an unconnected
    # input acting as an antenna, not a real recording artifact.
    raw.set_channel_types({"EEG061": "eog", "EEG062": "eog", "EEG063": "ecg", "EEG064": "misc"})
    raw.info["bads"] = list(bad_channels)
    return raw


def plot_panel(ax, freqs, psd_db, ch_names, bads, xscale, title):
    for i, name in enumerate(ch_names):
        color = "red" if name in bads else "black"
        zorder = 3 if name in bads else 2
        ax.plot(freqs, psd_db[i], color=color, alpha=0.6, lw=0.7, zorder=zorder)
    ax.set_xscale(xscale)
    ax.set(xlabel="Frequency (Hz)", ylabel="PSD (dB)", title=title, xlim=(freqs[1] if xscale == "log" else 0, 350))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--subject", default="09", help="BIDS subject id, zero-padded (default: 09, matches the paper)")
    parser.add_argument("--run", default="02", help="run number, zero-padded (default: 02)")
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    raw_path = CACHE_ROOT / f"S{args.subject}_run{args.run}" / "unprocessed_raw.fif"
    bad_channels = BAD_CHANNELS_RUN02.get(args.subject, [])
    out = args.out or str(Path(__file__).parent / f"figure2_psd_S{args.subject}.png")

    raw = load_eeg_raw(raw_path, bad_channels)
    picks = mne.pick_types(raw.info, eeg=True, exclude=[])
    print(f"{len(picks)} EEG channels, {len(raw.info['bads'])} marked bad: {raw.info['bads']}")

    # compute_psd() silently drops info['bads'] from its output even when
    # they're in `picks`, unless exclude=[] is also passed here.
    psd = raw.compute_psd(picks=picks, exclude=[], fmin=0, fmax=350, n_fft=2048, n_overlap=1024, verbose=False)
    freqs = psd.freqs
    ch_names = psd.ch_names
    # Spectrum.get_data() has its own separate exclude='bads' default,
    # independent of what compute_psd() was given -- must override here too.
    psd_db = 10 * np.log10(psd.get_data(exclude=[]) * 1e12)  # V^2/Hz -> dB, arbitrary ref matching paper's scale

    fig, (axA, axB) = plt.subplots(1, 2, figsize=(14, 5))
    plot_panel(axA, freqs, psd_db, ch_names, raw.info["bads"], "log", "A. Log frequency scale")
    plot_panel(axB, freqs, psd_db, ch_names, raw.info["bads"], "linear", "B. Linear frequency scale")

    for f in [LINE_FREQ] + HPI_FREQS:
        axB.axvline(f, color="gray", lw=0.7, ls=":", zorder=1)

    fig.suptitle(f"Figure 2 (reproduction) — Subject {args.subject}, Run {args.run} — EEG channel PSD (raw, pre-SSS)")
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    print(f"saved {out}")


if __name__ == "__main__":
    main()
