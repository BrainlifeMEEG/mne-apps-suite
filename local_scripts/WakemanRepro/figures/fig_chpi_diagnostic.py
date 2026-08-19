#!/usr/bin/env python3
"""Diagnostic (not a paper figure): unfiltered raw vs. 1-40 Hz filtered raw
vs. chpi-filtered raw, subject 10 run 02 -- no Maxwell filtering at all,
to isolate what each step does to the raw signal on its own.

Two views:
  1. PSD (0-350 Hz) -- shows the cHPI coil peaks (293/307/314/321/328 Hz
     for this dataset) directly, and how each processing choice handles
     them.
  2. A short (2s) raw magnetometer time-domain segment -- same 20 channels
     used in the earlier ad hoc diagnostic_raw_segment.png.

Context: mne.chpi.filter_chpi() is not part of the published
03-maxwell_filtering.py pipeline (see fig1_maxfilter_comparison.py's
docstring) -- this figure exists to show directly why it nonetheless
looked like a fix (cHPI peaks are far above the paper's 40 Hz cutoff, so a
plain lowpass removes them anyway) and whether chpi filtering changes
anything a plain 1-40 Hz filter doesn't already handle.
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mne
import numpy as np

DATA_DIR = Path(__file__).parent.parent / "data_cache" / "S10_run02"
RAW_PATH = DATA_DIR / "unprocessed_raw.fif"


def main():
    raw_unfiltered = mne.io.read_raw_fif(RAW_PATH, allow_maxshield=True, verbose=False)
    raw_unfiltered.load_data(verbose=False)

    raw_bp = raw_unfiltered.copy().filter(1, 40, picks="meg", verbose=False)

    raw_chpi = mne.chpi.filter_chpi(raw_unfiltered.copy(), verbose=False)

    versions = {
        "Unfiltered raw": raw_unfiltered,
        "1-40 Hz filtered": raw_bp,
        "chpi-filtered (mne.chpi.filter_chpi)": raw_chpi,
    }
    colors = {"Unfiltered raw": "gray", "1-40 Hz filtered": "C0", "chpi-filtered (mne.chpi.filter_chpi)": "C3"}

    fig, (ax_psd, ax_time) = plt.subplots(1, 2, figsize=(14, 5))

    for label, raw in versions.items():
        psd = raw.compute_psd(picks="mag", fmin=0, fmax=350, verbose=False)
        freqs = psd.freqs
        power_db = 10 * np.log10(psd.get_data().mean(axis=0) * 1e30)  # fT^2/Hz, dB-ish
        ax_psd.plot(freqs, power_db, label=label, color=colors[label], lw=1)
    for f in [50, 100, 150, 200, 250, 293, 307, 314, 321, 328]:
        ax_psd.axvline(f, color="lightgray", lw=0.5, zorder=0)
    ax_psd.set(xlabel="Frequency (Hz)", ylabel="Mean mag PSD (dB, arb. ref)",
               title="A. PSD (0-350 Hz) -- gray lines: 50 Hz + cHPI coil freqs")
    ax_psd.legend(fontsize=8)

    picks = mne.pick_types(raw_unfiltered.info, meg="mag")[:20]
    for label, raw in versions.items():
        data, times = raw[picks, 88000:90200]
        ax_time.plot(times, data[0] * 1e15, label=label, color=colors[label], lw=0.8)
    ax_time.set(xlabel="time (s, raw file indexing)", ylabel="fT",
                title="B. One magnetometer (MEG0111), 2 s segment")
    ax_time.legend(fontsize=8)

    fig.suptitle("Diagnostic — unfiltered vs. 1-40 Hz vs. chpi-filtered raw (S10 run02, no Maxwell filtering)")
    fig.tight_layout()
    out = Path(__file__).parent / "diagnostic_chpi_vs_bandpass.png"
    fig.savefig(out, dpi=150)
    print(f"saved {out}")


if __name__ == "__main__":
    main()
