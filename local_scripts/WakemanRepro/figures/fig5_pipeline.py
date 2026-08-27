#!/usr/bin/env python3
"""Phase 5 v2: corrected pipeline, replacing fig5_diagnostics.py's approach.

Triggered by user-directed investigation that found two real, unexplained
MEG artifact types in the pre-existing elekta_maxfilter_meg.fif ("proc-sss")
files fig5_diagnostics.py was built on:
  - MEG1611: brief (few-30ms) square pulses, run02-specific (0 occurrences
    in the other 5 runs), never marked bad by either Wakeman & Henson's own
    manual per-run lists (EEG-only in every run) or MaxFilter's own autobad
    (info['bads'] empty in all 6 runs) -- likely too low-duty-cycle for
    autobad's sustained-badness threshold to catch.
  - A separate "on-the-second" common-mode phenomenon: sub-ms discontinuities
    on a handful of magnetometers landing almost exactly on integer-second
    boundaries, present in 5/6 runs (0, 8, 30, 3, 1, 1 occurrences for
    runs 01-06). STI and CHPI channels show no correlate at these times;
    mechanism unconfirmed (best guess: a MaxFilter-internal per-second
    numerical artifact, since these files are static SSS -- max_st={} in
    proc_history for all 6 runs, confirmed -- not something tied to
    movement or triggers).

Route (user's explicit direction, given the above wasn't going to resolve
itself by tweaking ICA component selection further):
  1. Maxwell-filter from RAW (pre-SSS, fif2mne output) ourselves for all 6
     runs, marking MEG1611 bad for this subject (all runs, not just
     run02 -- SSS fully reconstructs a bad MEG channel from the others
     regardless, so there's no downside to being conservative here even
     though the pulse was only confirmed in run02).
  2. Re-scan the Maxwell-filtered output for the on-the-second artifact;
     annotate +/-100ms BAD_artifact around any found (ICA fit and epoching
     both respect annotations by default via reject_by_annotation).
  3. Crop each run to [first stim event - 1s, last stim event + 1s] --
     drops dead pre/post-task time, incidentally removing whatever lives
     there (e.g. run01's ~1s broadband burst at t=21s, well before task
     onset).
  4. Concatenate all 6 cleaned runs.
  5. Filter 1-40 Hz as a single uniform bandpass across all channels --
     matches 04-python_filtering.py's actual call
     (raw.filter(l_freq, 40, ...)) exactly; fig5_diagnostics.py's
     per-channel-type patchwork (MEG lowpass-only, EEG bandpass, EOG
     highpass-only) was a simplification that turns out not to match the
     primary source as closely as just doing this.
  6. ICA: same fastica/n_components=0.999/MEG-only parameters as before.
     ECG via find_bads_ecg(method='ctps', threshold=0.8); EOG via default
     find_bads_eog() but with ch_name='EOG061' pinned -- confirmed
     separately (independent of the MEG1611/on-the-second issues) that
     EOG062 is broken for this subject throughout all 6 runs (208 real
     blinks on EOG061 vs. 6 on EOG062 when auto-selected).
  7. Regenerate the Phase 5 diagnostic figures.
"""
import argparse
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mne
import numpy as np
from mne.preprocessing import ICA, create_ecg_epochs, create_eog_epochs

DATA_DIR_ROOT = Path(__file__).parent.parent / "data_cache"
CAL_DIR = DATA_DIR_ROOT / "shared_calibration"
CALIBRATION = CAL_DIR / "sss_cal.dat"
CROSS_TALK = CAL_DIR / "ct_sparse.fif"
SSS_ORIGIN = (0, 0.008, 0.037)  # matches Elekta's own JSON-documented origin (Fig 1)
RANDOM_STATE = 42
L_FREQ, H_FREQ = 1.0, 40.0
ALL_RUNS = ["01", "02", "03", "04", "05", "06"]

EVENTS_ID = {
    "face/famous/first": 5, "face/famous/immediate": 6, "face/famous/long": 7,
    "face/unfamiliar/first": 13, "face/unfamiliar/immediate": 14, "face/unfamiliar/long": 15,
    "scrambled/first": 17, "scrambled/immediate": 18, "scrambled/long": 19,
}

# MEG bad channels, marked for this subject across ALL runs (see docstring).
MEG_BAD_CHANNELS = {"09": ["MEG1611"]}

# W&H's own per-run EEG bad-channel lists (unchanged from fig5_diagnostics.py).
EEG_BAD_CHANNELS = {
    "09": {
        "01": [],
        "02": ["EEG006", "EEG013", "EEG023", "EEG034", "EEG043", "EEG045", "EEG047"],
        "03": ["EEG004", "EEG008", "EEG043", "EEG045", "EEG047"],
        "04": ["EEG043", "EEG045", "EEG047", "EEG071"],
        "05": ["EEG004", "EEG007", "EEG008"],
        "06": ["EEG004", "EEG008"],
    },
}


def find_raw_path(subject, run):
    """fif2mne output for this run -- filename varies by how/when it was
    fetched (unprocessed_raw.fif, raw.fif, or meg.fif)."""
    data_dir = DATA_DIR_ROOT / f"S{subject}_run{run}"
    for name in ["unprocessed_raw.fif", "raw.fif", "meg.fif"]:
        p = data_dir / name
        if p.exists():
            return p
    raise FileNotFoundError(f"no raw fif2mne output found in {data_dir}")


def find_common_mode_jump_events(raw, ratio_thresh=8, frac_thresh=0.15, win_s=0.5):
    """The on-the-second-type common-mode artifact detector, calibrated in
    the prior investigation against what's actually visible (ratio>8,
    frac>0.15 cleanly separates real events from statistical noise -- see
    conversation history: run03-06's original looser-threshold "events"
    at ratio~4-6 turned out to be noise, while the real ones all had
    ratio>=11)."""
    sfreq = raw.info["sfreq"]
    mag_picks = mne.pick_types(raw.info, meg="mag")
    data = raw.get_data(picks=mag_picks)
    win = int(win_s * sfreq)
    csum = np.cumsum(np.insert(data, 0, 0, axis=1), axis=1)
    csum2 = np.cumsum(np.insert(data**2, 0, 0, axis=1), axis=1)
    local_mean = (csum[:, win:] - csum[:, :-win]) / win
    local_meansq = (csum2[:, win:] - csum2[:, :-win]) / win
    local_std = np.sqrt(np.maximum(local_meansq - local_mean**2, 1e-30))
    gap = win
    before, after = local_mean[:, :-gap], local_mean[:, gap:]
    jump = np.abs(after - before)
    ratio = jump / (local_std[:, :-gap] + 1e-30)
    frac_jumped = (ratio > ratio_thresh).mean(axis=0)
    above = np.where(frac_jumped > frac_thresh)[0]
    events = []
    if len(above):
        start = prev = above[0]
        for idx in above[1:]:
            if idx - prev > sfreq * 0.5:
                events.append((start, prev))
                start = idx
            prev = idx
        events.append((start, prev))
    return [(s + win) / sfreq for s, e in events]


def process_run(subject, run, destination_path):
    print(f"  run{run}: loading raw...")
    raw = mne.io.read_raw_fif(find_raw_path(subject, run), allow_maxshield=True, verbose=False)
    raw.load_data(verbose=False)
    raw.set_channel_types({"EEG061": "eog", "EEG062": "eog", "EEG063": "ecg", "EEG064": "misc"})
    raw.rename_channels({"EEG061": "EOG061", "EEG062": "EOG062", "EEG063": "ECG063"})
    raw.info["bads"] = list(MEG_BAD_CHANNELS.get(subject, []))

    print(f"  run{run}: maxwell_filter (MEG1611 marked bad, reconstructed via SSS)...")
    raw_sss = mne.preprocessing.maxwell_filter(
        raw, calibration=str(CALIBRATION), cross_talk=str(CROSS_TALK),
        origin=SSS_ORIGIN, destination=str(destination_path), verbose=False,
    )

    raw_sss.info["bads"] = list(EEG_BAD_CHANNELS.get(subject, {}).get(run, []))
    raw_sss.interpolate_bads(verbose=False)

    jump_times = find_common_mode_jump_events(raw_sss)
    if jump_times:
        onsets = [t - 0.1 for t in jump_times]
        durations = [0.2] * len(jump_times)
        raw_sss.set_annotations(mne.Annotations(
            onset=onsets, duration=durations, description=["BAD_artifact"] * len(jump_times),
        ))
        print(f"  run{run}: {len(jump_times)} common-mode artifact(s) annotated BAD at "
              f"{[round(t, 2) for t in jump_times]}")
    else:
        print(f"  run{run}: no common-mode artifacts found")

    events = mne.find_events(raw_sss, stim_channel="STI101", shortest_event=1, verbose=False)
    stim_codes = list(EVENTS_ID.values())
    events = events[np.isin(events[:, 2], stim_codes)]
    t_first = (events[0, 0] - raw_sss.first_samp) / raw_sss.info["sfreq"]
    t_last = (events[-1, 0] - raw_sss.first_samp) / raw_sss.info["sfreq"]
    tmin, tmax = max(0, t_first - 1.0), min(raw_sss.times[-1], t_last + 1.0)
    print(f"  run{run}: {len(events)} events, cropping [{tmin:.1f}, {tmax:.1f}]s "
          f"(from {raw_sss.times[-1]:.1f}s total)")
    raw_sss.crop(tmin=tmin, tmax=tmax)

    # Filtered here, per-run, before saving -- matches the primary source's
    # own structure (04-python_filtering.py filters each run individually;
    # 05-run_ica.py's ICA fit concatenates the already-filtered per-run
    # files), and avoids a second full-rate load-filter-concatenate pass
    # later just to apply the same filter to everything at once.
    picks_filt = mne.pick_types(raw_sss.info, meg=True, eeg=True, eog=True, exclude=())
    raw_sss.filter(L_FREQ, H_FREQ, picks=picks_filt, l_trans_bandwidth="auto", h_trans_bandwidth="auto",
                   filter_length="auto", phase="zero", fir_window="hamming", fir_design="firwin",
                   verbose=False)

    out_path = DATA_DIR_ROOT / f"S{subject}_run{run}" / "phase5v2_maxfiltered_raw.fif"
    raw_sss.save(out_path, overwrite=True, verbose=False)
    del raw_sss
    return out_path


def load_lean_ica_concat(run_paths):
    """MEG+EOG+ECG only, resampled 1100->300 Hz, concatenated in place one
    run at a time -- for ICA fitting/scoring only. Six full-rate,
    full-channel runs concatenated simultaneously OOM'd this box twice
    already (once with Elekta's files, once with our own re-SSS'd ones);
    this sidesteps it the same way fig5_diagnostics.py's
    load_meg_eog_ecg_raw did. The official stimulus epochs (saved output)
    are built separately, per-run at full rate, so this resampling never
    touches what actually gets saved."""
    def _lean(p):
        r = mne.io.read_raw_fif(p, preload=True, verbose=False)
        picks_keep = mne.pick_types(r.info, meg=True, eog=True, ecg=True, exclude=())
        r.pick([r.ch_names[i] for i in picks_keep])
        r.resample(300, npad="auto", verbose=False)
        return r

    raw = _lean(run_paths[0])
    for p in run_paths[1:]:
        raw_next = _lean(p)
        raw.append(raw_next)
        del raw_next
    return raw


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--subject", default="09")
    parser.add_argument("--run", default="02", help="which run's events to use for figures C/D")
    parser.add_argument("--out-prefix", default=None)
    args = parser.parse_args()
    out_prefix = args.out_prefix or str(Path(__file__).parent / f"fig5_S{args.subject}")

    destination_path = find_raw_path(args.subject, "04")

    print("Processing all 6 runs (maxwell_filter + artifact annotation + crop)...")
    print("  (each run saved to disk immediately -- avoids holding all 6 full-rate,")
    print("   full-channel raws in memory simultaneously, which OOM'd earlier attempts)")
    run_paths = [process_run(args.subject, run, destination_path) for run in ALL_RUNS]

    print("Building lean (MEG+EOG+ECG, 300 Hz) concatenation for ICA fitting...")
    raw = load_lean_ica_concat(run_paths)

    print("Fitting ICA (fastica, n_components=0.999, MEG only, all 6 runs, annotations respected)...")
    picks_ica = mne.pick_types(raw.info, meg=True, eeg=False, eog=False, stim=False, exclude="bads")
    ica = ICA(method="fastica", random_state=RANDOM_STATE, n_components=0.999, max_iter="auto")
    # decim=3, not the official decim=11 -- raw is already resampled
    # 1100->300 Hz, so decim=3 lands on the same ~100 Hz effective fit
    # rate decim=11-on-1100Hz would have given.
    ica.fit(raw, picks=picks_ica, reject=dict(grad=4000e-13, mag=4e-12), reject_by_annotation=True,
            decim=3, verbose=False)
    print(f"  fit {ica.n_components_} components")

    ecg_epochs = create_ecg_epochs(raw, tmin=-0.3, tmax=0.3, preload=True, reject_by_annotation=True, verbose=False)
    ecg_epochs_bl = ecg_epochs.copy().apply_baseline((None, None), verbose=False)
    ecg_inds, ecg_scores = ica.find_bads_ecg(ecg_epochs_bl, method="ctps", threshold=0.8, verbose=False)
    ecg_scores = np.asarray(ecg_scores)
    print(f"  ECG: {len(ecg_epochs)} heartbeats, {len(ecg_inds)} candidate components: {ecg_inds}")

    # ch_name pinned to EOG061 -- see module docstring; EOG062 broken for
    # this subject throughout, independent of the MEG1611/on-the-second issues.
    eog_epochs = create_eog_epochs(raw, ch_name="EOG061", tmin=-0.5, tmax=0.5, preload=True,
                                    reject_by_annotation=True, verbose=False)
    eog_epochs_bl = eog_epochs.copy().apply_baseline((None, None), verbose=False)
    eog_inds, eog_scores = ica.find_bads_eog(eog_epochs_bl, ch_name="EOG061", verbose=False)
    eog_scores = np.asarray(eog_scores)
    if eog_scores.ndim == 2:
        eog_scores = eog_scores[np.argmax(np.abs(eog_scores).max(axis=1))]
    print(f"  EOG: {len(eog_epochs)} blinks, {len(eog_inds)} candidate components: {eog_inds}")

    n_max_ecg = n_max_eog = 3
    ecg_inds, eog_inds = list(ecg_inds[:n_max_ecg]), list(eog_inds[:n_max_eog])
    excluded = sorted(set(ecg_inds) | set(eog_inds))
    print(f"  excluding {excluded}")
    ica.exclude = excluded

    if excluded:
        fig_a = ica.plot_components(picks=excluded, show=False)
        fig_a.suptitle(f"A. Excluded ICA components (ECG={ecg_inds}, EOG={eog_inds}) — S{args.subject}, all 6 runs (v2)")
        fig_a.savefig(f"{out_prefix}_A_ica_components.png", dpi=150)
        plt.close(fig_a)

        fig_scores, axes = plt.subplots(1, 2, figsize=(11, 3.5))
        axes[0].bar(range(len(ecg_scores)), ecg_scores, color=["r" if i in ecg_inds else "gray" for i in range(len(ecg_scores))])
        axes[0].set(title="ECG score per component (ctps method)", xlabel="ICA component", ylabel="score")
        axes[1].bar(range(len(eog_scores)), eog_scores, color=["r" if i in eog_inds else "gray" for i in range(len(eog_scores))])
        axes[1].set(title="EOG score per component (zscore method)", xlabel="ICA component", ylabel="score")
        fig_scores.tight_layout()
        fig_scores.savefig(f"{out_prefix}_A_ica_scores.png", dpi=150)
        plt.close(fig_scores)
        print(f"  saved {out_prefix}_A_ica_components.png, _A_ica_scores.png")

    fig_b, axes = plt.subplots(2, 2, figsize=(11, 6.5))
    ecg_avg_before = ecg_epochs_bl.average()
    eog_avg_before = eog_epochs_bl.average()
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
        picks_mag = mne.pick_types(evk.info, meg="mag")
        ax.plot(evk.times * 1000, evk.data[picks_mag].T * 1e15, lw=0.5, color="C0", alpha=0.5)
        ax.set(title=title, xlabel="Time (ms)", ylabel="fT")
    fig_b.suptitle(f"B. ICA artifact removal, ECG/EOG-locked magnetometer averages — S{args.subject}, all 6 runs (v2)")
    fig_b.tight_layout()
    fig_b.savefig(f"{out_prefix}_B_ica_before_after.png", dpi=150)
    plt.close(fig_b)
    print(f"  saved {out_prefix}_B_ica_before_after.png")

    del raw  # lean ICA-fit concat no longer needed; free it before the full-rate epoching pass

    print("Epoching each run individually at full rate (tmin=-0.2, tmax=2.9, decim=5), then concatenating...")
    print("  (avoids holding all 6 full-rate raws in memory at once, same reasoning as process_run)")
    epochs_list = []
    for p in run_paths:
        raw_run = mne.io.read_raw_fif(p, preload=True, verbose=False)
        picks_epochs = mne.pick_types(raw_run.info, meg=True, eeg=True, stim=True, eog=True, exclude=())
        events_run = mne.find_events(raw_run, stim_channel="STI101", shortest_event=1, verbose=False)
        events_run = events_run[np.isin(events_run[:, 2], list(EVENTS_ID.values()))]
        epochs_run = mne.Epochs(raw_run, events_run, EVENTS_ID, tmin=-0.2, tmax=2.9, proj=True,
                                 picks=picks_epochs, baseline=None, preload=True, decim=5, reject=None,
                                 reject_tmax=0.8, reject_by_annotation=True, verbose=False)
        epochs_list.append(epochs_run)
        del raw_run
    epochs = mne.concatenate_epochs(epochs_list, verbose=False)
    del epochs_list
    ica.apply(epochs, verbose=False)

    n_before = len(epochs)
    fixed_reject = dict(mag=4e-12, grad=4000e-13, eeg=150e-6)
    epochs.drop_bad(reject=fixed_reject, verbose=False)
    n_after = len(epochs)
    print(f"  kept {n_after}/{n_before} epochs ({100*(1-n_after/n_before):.1f}% dropped) [all 6 runs]")

    epo_path = DATA_DIR_ROOT / f"S{args.subject}_allruns" / "phase5v2_epo.fif"
    epo_path.parent.mkdir(exist_ok=True)
    epochs.save(epo_path, overwrite=True)
    print(f"  saved epochs to {epo_path}")

    fig_c, ax = plt.subplots(figsize=(7, 4))
    reason_counts = Counter()
    for log in epochs.drop_log:
        reason_counts["kept" if not log else ",".join(log)] += 1
    labels, values = zip(*sorted(reason_counts.items(), key=lambda kv: -kv[1]))
    ax.bar(range(len(labels)), values, color=["C2" if l == "kept" else "C3" for l in labels])
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=30, ha="right", fontsize=7)
    ax.set(title=f"C. Epoch drop summary — S{args.subject}, all 6 runs ({n_after}/{n_before} kept)", ylabel="n epochs")
    fig_c.tight_layout()
    fig_c.savefig(f"{out_prefix}_C_drop_log.png", dpi=150)
    plt.close(fig_c)
    print(f"  saved {out_prefix}_C_drop_log.png")

    print("done")


if __name__ == "__main__":
    main()
