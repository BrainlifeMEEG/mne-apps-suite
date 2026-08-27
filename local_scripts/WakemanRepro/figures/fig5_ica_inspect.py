#!/usr/bin/env python3
"""Ad hoc inspection tool, not part of the Phase 5 pipeline itself: dumps
every ICA component's topography plus detailed "properties" (topography +
time course + PSD + epochs-image + ERP/ERF) for manual visual review, in
response to wanting to eyeball the actual components behind fig5_S09_A's
CTPS pick (component 8) and the before/after result that showed almost no
change (see fig5_diagnostics.py's module docstring for the full story).

Reuses fig5_diagnostics.load_all_runs_concat() and the same ICA fit
parameters, so the component numbering here matches fig5_S09_A exactly.
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mne
from mne.preprocessing import ICA, create_ecg_epochs

sys.path.insert(0, str(Path(__file__).parent))
from fig5_diagnostics import RANDOM_STATE, load_all_runs_concat

OUT_DIR = Path(__file__).parent


def main():
    print("Loading + concatenating all 6 runs...")
    raw = load_all_runs_concat("09")

    print("Fitting ICA (same params as fig5_diagnostics.py)...")
    picks_ica = mne.pick_types(raw.info, meg=True, eeg=False, eog=False, stim=False, exclude="bads")
    ica = ICA(method="fastica", random_state=RANDOM_STATE, n_components=0.999, max_iter="auto")
    ica.fit(raw, picks=picks_ica, reject=dict(grad=4000e-13, mag=4e-12), decim=3, verbose=False)
    print(f"  fit {ica.n_components_} components")

    ecg_epochs = create_ecg_epochs(raw, tmin=-0.3, tmax=0.3, preload=True, verbose=False)
    ecg_epochs_bl = ecg_epochs.copy().apply_baseline((None, None), verbose=False)
    ecg_inds, ecg_scores = ica.find_bads_ecg(ecg_epochs_bl, method="ctps", threshold=0.8, verbose=False)
    print(f"  CTPS ECG candidates: {ecg_inds}")

    print("Saving all-components topography overview...")
    fig_all = ica.plot_components(show=False)
    figs_all = fig_all if isinstance(fig_all, list) else [fig_all]
    for i, fig in enumerate(figs_all):
        fig.suptitle(f"All {ica.n_components_} ICA components (topographies) — S09, all 6 runs")
        fig.savefig(OUT_DIR / f"fig5_S09_ica_all_components_{i}.png", dpi=150)
        plt.close(fig)
    print(f"  saved fig5_S09_ica_all_components_*.png")

    print("Saving detailed properties for components 0-9...")
    # Passing ecg_epochs (not raw) sidesteps an MNE internal-epoching edge
    # case on this concatenated raw (IndexError from a fixed-length-epochs
    # drop_var size mismatch) and is arguably more informative anyway: the
    # epochs-image panel is then literally locked to real R-peaks.
    for i in range(min(10, ica.n_components_)):
        figs = ica.plot_properties(ecg_epochs, picks=[i], psd_args=dict(fmax=60), show=False, verbose=False)
        fig = figs[0] if isinstance(figs, list) else figs
        tag = " <- CTPS ECG candidate" if i in ecg_inds else ""
        fig.suptitle(f"ICA{i:03d} properties — S09, all 6 runs{tag}", y=1.02)
        fig.savefig(OUT_DIR / f"fig5_S09_ica_properties_{i:02d}.png", dpi=150, bbox_inches="tight")
        plt.close(fig)
        print(f"  saved fig5_S09_ica_properties_{i:02d}.png{tag}")

    print("done")


if __name__ == "__main__":
    main()
