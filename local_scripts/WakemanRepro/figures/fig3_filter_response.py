#!/usr/bin/env python3
"""Recreate paper Figure 3, for current MNE (brief: "for mne 1.12 (current
version)" -- not the paper's own old-vs-new MNE 0.12-vs-0.16 comparison).

Paper caption (Frontiers 2018, Fig 3): "Comparison of filters between new
(0.16) and old (0.12) MNE versions: (A) The frequency response of the
highpass filter; (B) The frequency response of the lowpass filter; (C)
The impulse response of the highpass filter; (D) The impulse response of
the lowpass filter. The filters in MNE are now adaptive with trade-offs
between frequency attenuation and time domain artifacts that by default
adapt based on the chosen low-pass and high-pass frequencies."

Same 4-panel layout (A/B frequency response, C/D impulse response;
left column highpass, right column lowpass), but only current MNE's
filter design -- no old-version comparison (0.12 isn't installable
alongside modern MNE, and isn't the point per the brief).

Filter design confirmed against the actual 04-python_filtering.py source
(mne-biomag-group-demo): raw.filter(l_freq, 40, l_trans_bandwidth='auto',
h_trans_bandwidth='auto', filter_length='auto', phase='zero',
fir_window='hamming', fir_design='firwin'). l_freq=1 here, matching the
"filtered between 1 and 40 Hz" already used for Figs 1/2's display filter
in this reproduction. A single two-sided call designs (and applies)
separate highpass and lowpass FIR filters internally -- built directly
via mne.filter.create_filter() here to get each filter's own coefficients
for plotting (mne.filter.create_filter with only l_freq or only h_freq
set reproduces exactly the highpass-only / lowpass-only component MNE
would otherwise design internally for the combined call).
"""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mne

SFREQ = 1100.0  # matches ds000117's MEG sampling rate
L_FREQ = 1.0
H_FREQ = 40.0
FILTER_KW = dict(
    filter_length="auto", phase="zero", fir_window="hamming", fir_design="firwin",
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(Path(__file__).parent / "figure3_filter_response.png"))
    args = parser.parse_args()

    h_highpass = mne.filter.create_filter(
        None, SFREQ, l_freq=L_FREQ, h_freq=None, l_trans_bandwidth="auto", **FILTER_KW,
    )
    h_lowpass = mne.filter.create_filter(
        None, SFREQ, l_freq=None, h_freq=H_FREQ, h_trans_bandwidth="auto", **FILTER_KW,
    )
    print(f"highpass filter length: {len(h_highpass)} samples ({len(h_highpass)/SFREQ*1000:.1f} ms)")
    print(f"lowpass filter length: {len(h_lowpass)} samples ({len(h_lowpass)/SFREQ*1000:.1f} ms)")

    fig, axes = plt.subplots(2, 2, figsize=(11, 7))
    # flim zooms each magnitude panel around its own cutoff (matches the
    # paper's framing, which is what actually makes transition steepness
    # visible -- a full 0.1-400 Hz log view flattens it into invisibility).
    mne.viz.plot_filter(h_highpass, SFREQ, axes=[axes[0, 0], axes[1, 0]], plot=("magnitude", "time"), flim=(0.1, 4), fscale="linear", show=False)
    mne.viz.plot_filter(h_lowpass, SFREQ, axes=[axes[0, 1], axes[1, 1]], plot=("magnitude", "time"), flim=(35, 55), fscale="linear", show=False)

    # plot_filter's "time" panel x-axis runs 0..duration (filter delay not
    # yet removed); recenter on 0 and zoom in, matching the paper's framing
    # (which also clips the y-axis, cutting off the central peak, to make
    # the ripple/ringing structure legible).
    for ax, xlim, ylim in [(axes[1, 0], (-2, 2), (-0.002, 0.004)), (axes[1, 1], (-0.5, 0.5), (-0.02, 0.04))]:
        for line in ax.get_lines():
            xdata = line.get_xdata()
            line.set_xdata(xdata - xdata[-1] / 2)
        ax.set_xlim(*xlim)
        ax.set_ylim(*ylim)

    for ax, label in zip(axes.flat, "ABCD"):
        ax.annotate(label, (-0.12, 1.05), xycoords="axes fraction", fontsize=13, fontweight="bold")
    axes[0, 0].set_title(f"A. Highpass ({L_FREQ:.0f} Hz) frequency response")
    axes[0, 1].set_title(f"B. Lowpass ({H_FREQ:.0f} Hz) frequency response")
    axes[1, 0].set_title("C. Highpass impulse response")
    axes[1, 1].set_title("D. Lowpass impulse response")

    fig.suptitle(f"Figure 3 (reproduction) — filter response, MNE {mne.__version__} (adaptive 'auto' design)")
    fig.tight_layout()
    fig.savefig(args.out, dpi=150)
    print(f"saved {args.out}")


if __name__ == "__main__":
    main()
