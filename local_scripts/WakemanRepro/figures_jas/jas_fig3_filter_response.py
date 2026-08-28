#!/usr/bin/env python3
"""Recreate paper Figure 3: old (MNE 0.12) vs. current MNE filter response.

Paper caption (Frontiers 2018, Fig 3): "Comparison of filters between new
(0.16) and old (0.12) MNE versions: (A) The frequency response of the
highpass filter; (B) The frequency response of the lowpass filter; (C)
The impulse response of the highpass filter; (D) The impulse response of
the lowpass filter. The filters in MNE are now adaptive with trade-offs
between frequency attenuation and time domain artifacts that by default
adapt based on the chosen low-pass and high-pass frequencies."

Same 4-panel layout, same blue(old)/orange(new) comparison as the paper.
"Current" here means whatever MNE this repo's Docker image runs
(brainlifemeeg/mne:1.12.1; 1.11.0 locally) -- not literally >=0.16, but
the same "modern adaptive design" lineage the paper's ">=0.16" refers to.

Filter design confirmed against the actual 04-python_filtering.py source
(mne-biomag-group-demo): raw.filter(l_freq, 40, l_trans_bandwidth='auto',
h_trans_bandwidth='auto', filter_length='auto', phase='zero',
fir_window='hamming', fir_design='firwin'). l_freq=1 here, matching the
"filtered between 1 and 40 Hz" already used for Figs 1/2's display filter
in this reproduction.

Current-MNE filters are built directly via mne.filter.create_filter()
(l_freq/h_freq set one at a time to get each filter's own coefficients,
reproducing exactly the highpass-only / lowpass-only component a combined
two-sided raw.filter() call designs internally). Old-MNE (0.12) filters
can't be built the same way in this environment (MNE 1.x here, and 0.12's
own dependencies don't run under current numpy without patching) --
their impulse responses are precomputed by compute_old_mne_012_filters.py
(run once, separately, under an MNE-0.12 environment; see that script's
docstring for the one-time setup) and loaded from
old_mne_012_reference/*.npy here. Uses old MNE's actual *defaults*
(filter_length='10s', trans_bandwidth=0.5 Hz) for the same 1/40 Hz
cutoffs -- the "old" comparison point is old MNE's fixed, non-adaptive
default behavior vs. new MNE's adaptive 'auto' design, which is exactly
what the paper's own comparison is about.
"""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mne
import numpy as np

SFREQ = 1100.0  # matches ds000117's MEG sampling rate
L_FREQ = 1.0
H_FREQ = 40.0
FILTER_KW = dict(
    filter_length="auto", phase="zero", fir_window="hamming", fir_design="firwin",
)
OLD_REF_DIR = Path(__file__).parent / "old_mne_012_reference"


def freq_response_db(h, sfreq, n_fft=32768):
    H = np.fft.rfft(h, n=n_fft)
    freqs = np.fft.rfftfreq(n_fft, d=1 / sfreq)
    mag_db = 20 * np.log10(np.maximum(np.abs(H), 1e-12))
    mag_db -= mag_db[1:50].max()  # normalize passband to ~0 dB (skip DC bin)
    return freqs, mag_db


def centered_time(h, sfreq):
    peak = np.argmax(np.abs(h))
    t = (np.arange(len(h)) - peak) / sfreq
    return t, h


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(Path(__file__).parent / "jas_fig3_filter_response.png"))
    args = parser.parse_args()

    h_highpass_new = mne.filter.create_filter(
        None, SFREQ, l_freq=L_FREQ, h_freq=None, l_trans_bandwidth="auto", **FILTER_KW,
    )
    h_lowpass_new = mne.filter.create_filter(
        None, SFREQ, l_freq=None, h_freq=H_FREQ, h_trans_bandwidth="auto", **FILTER_KW,
    )
    print(f"new highpass filter length: {len(h_highpass_new)} samples ({len(h_highpass_new)/SFREQ*1000:.1f} ms)")
    print(f"new lowpass filter length: {len(h_lowpass_new)} samples ({len(h_lowpass_new)/SFREQ*1000:.1f} ms)")

    h_highpass_old = np.load(OLD_REF_DIR / "highpass_impulse_response.npy")
    h_lowpass_old = np.load(OLD_REF_DIR / "lowpass_impulse_response.npy")

    fig, axes = plt.subplots(2, 2, figsize=(11, 7))
    NEW, OLD = "#ff7f0e", "#1f77b4"  # match paper: orange = new, blue = old

    for h, color, label in [(h_highpass_old, OLD, "MNE 0.12"), (h_highpass_new, NEW, "current MNE")]:
        freqs, mag_db = freq_response_db(h, SFREQ)
        axes[0, 0].plot(freqs, mag_db, color=color, label=label)
        t, hh = centered_time(h, SFREQ)
        axes[1, 0].plot(t, hh, color=color, label=label)

    for h, color, label in [(h_lowpass_old, OLD, "MNE 0.12"), (h_lowpass_new, NEW, "current MNE")]:
        freqs, mag_db = freq_response_db(h, SFREQ)
        axes[0, 1].plot(freqs, mag_db, color=color, label=label)
        t, hh = centered_time(h, SFREQ)
        axes[1, 1].plot(t, hh, color=color, label=label)

    axes[0, 0].set(xlim=(0.1, 4), ylim=(-60, 5), xlabel="Frequency (Hz)", ylabel="Amplitude (dB)")
    axes[0, 1].set(xlim=(35, 55), ylim=(-60, 5), xlabel="Frequency (Hz)", ylabel="Amplitude (dB)")
    axes[1, 0].set(xlim=(-2, 2), ylim=(-0.002, 0.004), xlabel="Time (s)", ylabel="Amplitude")
    axes[1, 1].set(xlim=(-0.5, 0.5), ylim=(-0.02, 0.04), xlabel="Time (s)", ylabel="Amplitude")
    for ax in axes.flat:
        ax.legend(fontsize=8)
        ax.grid(alpha=0.3)

    for ax, label in zip(axes.flat, "ABCD"):
        ax.annotate(label, (-0.12, 1.05), xycoords="axes fraction", fontsize=13, fontweight="bold")
    axes[0, 0].set_title(f"A. Highpass ({L_FREQ:.0f} Hz) frequency response")
    axes[0, 1].set_title(f"B. Lowpass ({H_FREQ:.0f} Hz) frequency response")
    axes[1, 0].set_title("C. Highpass impulse response")
    axes[1, 1].set_title("D. Lowpass impulse response")

    fig.suptitle(f"Figure 3 (reproduction) — filter response, MNE 0.12 vs. current MNE {mne.__version__}")
    fig.tight_layout()
    fig.savefig(args.out, dpi=150)
    print(f"saved {args.out}")


if __name__ == "__main__":
    main()
