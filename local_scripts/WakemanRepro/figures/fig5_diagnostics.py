#!/usr/bin/env python3
"""Phase 5: bad channels/segments, ICA, epoching -- plus diagnostic figures
(brief: "Can you think of diagnostic new figures to show?").

Subject 09 (paper's "subject 10"), run 02 only for now, matching this
reproduction's established incremental-development pattern -- NOT yet the
full 6-run concatenation the real group pipeline uses for ICA fitting
(see below). Single-run ICA is a real methodological simplification worth
being explicit about; it isn't just a smaller version of the same thing.

Methodology confirmed against the actual scripts (raw text, not AI
summaries -- 03-maxwell_filtering.py, 05-run_ica.py, 06-make_epochs.py,
library/config.py):

- SSS source: 03-maxwell_filtering.py's own hardcoded call is
  `run_maxwell_filter(subject_id=3)` -- ONLY subject 3 -- and its output
  filenames are always `*_filt_tsss_*`, which never matches the
  `*_filt_sss_highpass-*Hz` files 05/06 actually load for the main
  per-subject loop (`range(1, 20)`). So MNE-recomputing SSS (what Figure 1
  did, and validated closely against Elekta's own output) looks like a
  one-off methods-validation step for one demo subject, not what most
  subjects' processing is actually based on -- the main pipeline appears
  to take Elekta's own proc-sss output directly and filter on top of it.
  Used here accordingly: elekta_maxfilter_meg.fif, not our own
  recomputed mne_maxwellfilter_dest_run4_meg.fif (Fig 1 already showed
  these are nearly identical for this subject/run anyway).
- Bad channels: ONE source, not two -- the same per-subject/run text file
  used for Figure 2's red lines (bads/<W&H name>/run_NN_raw_tr.fif_bad)
  is also used here, via `raw.info['bads'] = bads; raw.interpolate_bads()`
  (interpolation, not exclusion). An earlier note in this project claimed
  a *separate* MaxFilter-log-based bad-channel source for the SSS step
  specifically ("Static bad channels" line) -- real, but it's internal to
  03-maxwell_filtering.py's own one-off subject-3 demo, not part of the
  main pipeline we're following here.
- Filtering (on top of the SSS'd data): lowpass 40 Hz for MEG; 1-40 Hz
  bandpass for EEG; 1 Hz highpass for EOG -- same 'auto'/firwin/hamming
  design as Figure 3, confirmed against the same script.
- ICA: fastica, n_components=0.999, MEG picks only, random_state=42,
  reject=dict(grad=4000e-13, mag=4e-12) during fitting, decim=11.
  Officially fit on all 6 runs concatenated ("ICA needs a highpass" is
  why the 1 Hz-filtered branch specifically is used) -- single-run here.
- ECG/EOG component detection: create_ecg_epochs/create_eog_epochs on the
  filtered raw, ica.find_bads_ecg(method='ctps', threshold=0.8) /
  find_bads_eog(), excluding up to 3 components each.
- Epoching: tmin=-0.2, tmax=2.9 (not Figs 1/2's short display windows --
  those were zoomed views for those specific figures, not this pipeline's
  real epoch window), baseline=None (since we're on the l_freq=1 highpass
  branch -- baseline=(None, 0) is the *alternative*, l_freq=None branch,
  which is what Phase 6/Figure 4 compares against), decim=5,
  reject_tmax=0.8 (only the early, scientifically-relevant part of each
  long epoch is used for the amplitude-based rejection threshold).
  autoreject's get_rejection_threshold() needs the `autoreject` package;
  falls back to a fixed peak-to-peak threshold if unavailable.

Diagnostic figures (open-ended per the brief):
  A. ICA component properties: topographies for the excluded (ECG/EOG)
     components, with their find_bads_ecg/eog scores -- shows *which*
     components got removed and *why*, not just a before/after blur.
  B. Before/after ICA cleaning on the ECG- and EOG-locked averages --
     direct evidence the excluded components were actually capturing
     cardiac/ocular artifacts, not signal.
  C. Epoch drop summary -- how many epochs survived, and why the rest
     didn't (drop_log reasons), a standard but easy-to-skip sanity check.
  D. EOG channel quality check -- found by accident (first pass rejected
     91% of epochs): create_eog_epochs()'s automatic channel selection
     picked EOG062 for blink detection, but EOG062 is dominated by two
     huge non-physiological transients in the first ~25s then goes flat
     for the rest of the run, while EOG061 shows regular, plausible blink
     activity throughout. Using the auto-selected (bad) channel meant
     ica.find_bads_eog() found nothing to exclude, real blink artifacts
     stayed in the data, and the rejection threshold then correctly
     rejected almost everything. Fixed by pinning ch_name="EOG061"
     explicitly rather than trusting automatic channel selection -- worth
     checking per-subject, this may not generalize.
"""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mne
import numpy as np
from mne.preprocessing import ICA, create_ecg_epochs, create_eog_epochs

DATA_DIR_ROOT = Path(__file__).parent.parent / "data_cache"
RANDOM_STATE = 42
L_FREQ = 1.0
H_FREQ = 40.0

EVENTS_ID = {
    "face/famous/first": 5, "face/famous/immediate": 6, "face/famous/long": 7,
    "face/unfamiliar/first": 13, "face/unfamiliar/immediate": 14, "face/unfamiliar/long": 15,
    "scrambled/first": 17, "scrambled/immediate": 18, "scrambled/long": 19,
}

BAD_CHANNELS_RUN02 = {
    "09": ["EEG006", "EEG013", "EEG023", "EEG034", "EEG043", "EEG045", "EEG047"],
    "10": [],
}


def load_filtered_raw(subject, run):
    data_dir = DATA_DIR_ROOT / f"S{subject}_run{run}"
    raw = mne.io.read_raw_fif(data_dir / "elekta_maxfilter_meg.fif", allow_maxshield=True, verbose=False)
    raw.load_data(verbose=False)
    raw.set_channel_types({"EEG061": "eog", "EEG062": "eog", "EEG063": "ecg", "EEG064": "misc"})
    raw.rename_channels({"EEG061": "EOG061", "EEG062": "EOG062", "EEG063": "ECG063"})
    raw.info["bads"] = list(BAD_CHANNELS_RUN02.get(subject, []))
    raw.interpolate_bads(verbose=False)

    filt_kw = dict(l_trans_bandwidth="auto", h_trans_bandwidth="auto", filter_length="auto",
                    phase="zero", fir_window="hamming", fir_design="firwin", verbose=False)
    picks_meg = mne.pick_types(raw.info, meg=True, exclude=())
    raw.filter(None, H_FREQ, picks=picks_meg, **filt_kw)
    picks_eeg = mne.pick_types(raw.info, eeg=True, exclude=())
    raw.filter(L_FREQ, H_FREQ, picks=picks_eeg, **filt_kw)
    picks_eog = mne.pick_types(raw.info, meg=False, eog=True)
    raw.filter(L_FREQ, None, picks=picks_eog, l_trans_bandwidth="auto", filter_length="auto",
               phase="zero", fir_window="hann", fir_design="firwin", verbose=False)
    return raw


def find_events_from_stim(raw):
    stim_codes = list(EVENTS_ID.values())
    events = mne.find_events(raw, stim_channel="STI101", shortest_event=1, verbose=False)
    return events[np.isin(events[:, 2], stim_codes)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--subject", default="09")
    parser.add_argument("--run", default="02")
    parser.add_argument("--out-prefix", default=None)
    args = parser.parse_args()
    out_prefix = args.out_prefix or str(Path(__file__).parent / f"fig5_S{args.subject}")

    print("Loading + interpolating bads + filtering (matches 03-maxwell_filtering.py's filter block)...")
    raw = load_filtered_raw(args.subject, args.run)
    events = find_events_from_stim(raw)
    print(f"{len(events)} stimulus events found")

    # --- Diagnostic figure D: EOG channel quality (see module docstring) ---
    eog_picks = mne.pick_types(raw.info, meg=False, eog=True)
    eog_data, eog_times = raw[eog_picks, :]
    fig_d, axes = plt.subplots(len(eog_picks), 1, figsize=(12, 2.5 * len(eog_picks)), sharex=True)
    for ax, ch_data, name in zip(np.atleast_1d(axes), eog_data, [raw.ch_names[p] for p in eog_picks]):
        ax.plot(eog_times, ch_data * 1e6, lw=0.3)
        ax.set_ylabel(f"{name} (µV)")
    axes[-1].set_xlabel("time (s)")
    fig_d.suptitle(f"D. EOG channel quality — S{args.subject} run{args.run} (pick the channel with real, regular blinks, not just the biggest amplitude)")
    fig_d.tight_layout()
    fig_d.savefig(f"{out_prefix}_D_eog_quality.png", dpi=150)
    plt.close(fig_d)
    print(f"  saved {out_prefix}_D_eog_quality.png")

    print("Fitting ICA (fastica, n_components=0.999, MEG only)...")
    picks_ica = mne.pick_types(raw.info, meg=True, eeg=False, eog=False, stim=False, exclude="bads")
    ica = ICA(method="fastica", random_state=RANDOM_STATE, n_components=0.999, max_iter="auto")
    ica.fit(raw, picks=picks_ica, reject=dict(grad=4000e-13, mag=4e-12), decim=11, verbose=False)
    print(f"  fit {ica.n_components_} components")

    # NB: keep an un-baselined copy of each for ica.apply() later. Applying
    # ICA to data that's had a (None, None) (whole-epoch-mean) baseline
    # subtracted desyncs ICA's internal mean-restoration from the mean it
    # was fit on and blows up the reconstruction ~25x (found the hard way:
    # a "before/after ICA" comparison came back with the "after" panel at
    # 10-15000 fT instead of a few hundred). The official script never hits
    # this because it only calls ica.apply() on the main stimulus-locked
    # epochs (which get no baseline on this l_freq=1 branch), never on
    # ecg_epochs/eog_epochs themselves -- those are baselined immediately
    # for find_bads_ecg/eog's own purposes and then discarded.
    ecg_epochs = create_ecg_epochs(raw, tmin=-0.3, tmax=0.3, preload=True, verbose=False)
    ecg_epochs_bl = ecg_epochs.copy().apply_baseline((None, None), verbose=False)
    ecg_inds, ecg_scores = ica.find_bads_ecg(ecg_epochs_bl, method="ctps", threshold=0.8, verbose=False)

    # ch_name pinned to EOG061 explicitly -- see module docstring, point D:
    # automatic channel selection here picks whichever EOG channel has the
    # largest peak-to-peak amplitude, which for this subject/run is EOG062,
    # a channel dominated by two huge non-physiological transients early on
    # and flat for the rest of the recording, not real blinks.
    eog_epochs = create_eog_epochs(raw, ch_name="EOG061", tmin=-0.5, tmax=0.5, preload=True, verbose=False)
    eog_epochs_bl = eog_epochs.copy().apply_baseline((None, None), verbose=False)
    eog_inds, eog_scores = ica.find_bads_eog(eog_epochs_bl, ch_name="EOG061", verbose=False)
    # find_bads_eog returns one score row per EOG channel (2 here:
    # EOG061/EOG062) rather than ecg's single row -- collapse to one score
    # per component (max abs across channels) for plotting/consistency.
    eog_scores = np.asarray(eog_scores)
    if eog_scores.ndim == 2:
        eog_scores = eog_scores[np.argmax(np.abs(eog_scores).max(axis=1))]

    # NB: many components score highly for ECG here (several >0.9, close to
    # or above some of the ones actually selected) -- find_bads_ecg's
    # returned order isn't simply "sorted by the plotted score descending",
    # so ecg_inds[:n_max] can look like it skips a visually-taller bar.
    # Matches the official script's own selection exactly (ecg_inds[:n_max]),
    # not a bug here -- CTPS scoring on SSS'd, reduced-rank MEG data seems
    # to spread cardiac-correlated signal across many components rather
    # than concentrating it in one or two, plausibly a volume-conduction/
    # SSS-mixing effect worth keeping in mind, not chased further here.
    n_max = 3
    excluded = list(dict.fromkeys(ecg_inds[:n_max] + eog_inds[:n_max]))
    print(f"  ECG components: {ecg_inds[:n_max]}, EOG components: {eog_inds[:n_max]} -> excluding {excluded}")
    ica.exclude = excluded

    # --- Diagnostic figure A: excluded component topographies + scores ---
    if excluded:
        fig_a = ica.plot_components(picks=excluded, show=False)
        fig_a.suptitle(f"A. Excluded ICA components (ECG={ecg_inds[:n_max]}, EOG={eog_inds[:n_max]}) — S{args.subject} run{args.run}")
        fig_a.savefig(f"{out_prefix}_A_ica_components.png", dpi=150)
        plt.close(fig_a)

        fig_scores, axes = plt.subplots(1, 2, figsize=(11, 3.5))
        axes[0].bar(range(len(ecg_scores)), ecg_scores, color=["r" if i in ecg_inds[:n_max] else "gray" for i in range(len(ecg_scores))])
        axes[0].set(title="ECG score per component", xlabel="ICA component", ylabel="score")
        axes[1].bar(range(len(eog_scores)), eog_scores, color=["r" if i in eog_inds[:n_max] else "gray" for i in range(len(eog_scores))])
        axes[1].set(title="EOG score per component", xlabel="ICA component", ylabel="score")
        fig_scores.tight_layout()
        fig_scores.savefig(f"{out_prefix}_A_ica_scores.png", dpi=150)
        plt.close(fig_scores)
        print(f"  saved {out_prefix}_A_ica_components.png, _A_ica_scores.png")

    # --- Diagnostic figure B: before/after ICA on ECG/EOG-locked averages ---
    fig_b, axes = plt.subplots(2, 2, figsize=(11, 6.5))
    ecg_avg_before = ecg_epochs_bl.average()
    eog_avg_before = eog_epochs_bl.average()
    # Apply ICA to the un-baselined copies (see comment above), *then*
    # baseline for display -- keeps the before/after panels visually
    # comparable without hitting the mean-restoration blow-up.
    ecg_epochs_after, eog_epochs_after = ecg_epochs.copy(), eog_epochs.copy()
    ica.apply(ecg_epochs_after, verbose=False)
    ica.apply(eog_epochs_after, verbose=False)
    ecg_epochs_after.apply_baseline((None, None), verbose=False)
    eog_epochs_after.apply_baseline((None, None), verbose=False)
    for ax, evk, title in [
        (axes[0, 0], ecg_avg_before, "ECG-locked average, before ICA"),
        (axes[0, 1], ecg_epochs_after.average(), "ECG-locked average, after ICA"),
        (axes[1, 0], eog_avg_before, "EOG-locked average, before ICA"),
        (axes[1, 1], eog_epochs_after.average(), "EOG-locked average, after ICA"),
    ]:
        picks = mne.pick_types(evk.info, meg="mag")
        ax.plot(evk.times * 1000, evk.data[picks].T * 1e15, lw=0.5, color="C0", alpha=0.5)
        ax.set(title=title, xlabel="Time (ms)", ylabel="fT")
    fig_b.suptitle(f"B. ICA artifact removal, ECG/EOG-locked magnetometer averages — S{args.subject} run{args.run}")
    fig_b.tight_layout()
    fig_b.savefig(f"{out_prefix}_B_ica_before_after.png", dpi=150)
    plt.close(fig_b)
    print(f"  saved {out_prefix}_B_ica_before_after.png")

    # --- Epoching ---
    print("Epoching (tmin=-0.2, tmax=2.9, decim=5)...")
    picks_epochs = mne.pick_types(raw.info, meg=True, eeg=True, stim=True, eog=True, exclude=())
    epochs = mne.Epochs(raw, events, EVENTS_ID, tmin=-0.2, tmax=2.9, proj=True, picks=picks_epochs,
                         baseline=None, preload=True, decim=5, reject=None, reject_tmax=0.8, verbose=False)
    ica.apply(epochs, verbose=False)

    # autoreject's get_rejection_threshold() is the official method (used
    # as-is in 06-make_epochs.py), but its cross-validated estimate needs
    # more data than one run's ~148 epochs to be reliable -- the official
    # pipeline calls it on all 6 runs concatenated (~900 epochs). Checked
    # empirically here: autoreject's threshold from this single run keeps
    # only 13/148 (9%) epochs, vs. 139/148 (94%) for a conventional fixed
    # threshold on the exact same data -- not a real data-quality problem,
    # an under-constrained threshold estimate. Reporting both; saving
    # epochs with the fixed threshold so this run's output is actually
    # usable for now. Redo with autoreject once runs are concatenated
    # (Phase 6+, "catch up the whole processing").
    n_before = len(epochs)
    fixed_reject = dict(mag=4e-12, grad=4000e-13, eeg=150e-6)
    epochs_fixed = epochs.copy()
    epochs_fixed.drop_bad(reject=fixed_reject, verbose=False)
    print(f"  fixed threshold {fixed_reject}: kept {len(epochs_fixed)}/{n_before}")

    try:
        from autoreject import get_rejection_threshold
        reject_ar = get_rejection_threshold(epochs.copy().crop(None, 0.8), random_state=RANDOM_STATE, verbose=False)
        epochs_ar = epochs.copy()
        epochs_ar.drop_bad(reject=reject_ar, verbose=False)
        print(f"  autoreject threshold {reject_ar}: kept {len(epochs_ar)}/{n_before} "
              f"(single-run estimate, likely too strict -- see comment above)")
    except ImportError:
        print("  autoreject not installed, skipping comparison")

    epochs = epochs_fixed
    n_after = len(epochs)
    print(f"  kept {n_after}/{n_before} epochs ({100*(1-n_after/n_before):.1f}% dropped) [fixed threshold, used for saved output]")

    epo_path = DATA_DIR_ROOT / f"S{args.subject}_run{args.run}" / "phase5_epo.fif"
    epochs.save(epo_path, overwrite=True)
    print(f"  saved epochs to {epo_path} (data_cache, not committed -- ~150MB)")

    # --- Diagnostic figure C: epoch drop summary ---
    fig_c, ax = plt.subplots(figsize=(7, 4))
    from collections import Counter
    reason_counts = Counter()
    for log in epochs.drop_log:
        if log:
            reason_counts[",".join(log)] += 1
        else:
            reason_counts["kept"] += 1
    labels, values = zip(*sorted(reason_counts.items(), key=lambda kv: -kv[1]))
    ax.bar(range(len(labels)), values, color=["C2" if l == "kept" else "C3" for l in labels])
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=30, ha="right", fontsize=7)
    ax.set(title=f"C. Epoch drop summary — S{args.subject} run{args.run} ({n_after}/{n_before} kept)", ylabel="n epochs")
    fig_c.tight_layout()
    fig_c.savefig(f"{out_prefix}_C_drop_log.png", dpi=150)
    plt.close(fig_c)
    print(f"  saved {out_prefix}_C_drop_log.png")

    print("done")


if __name__ == "__main__":
    main()
