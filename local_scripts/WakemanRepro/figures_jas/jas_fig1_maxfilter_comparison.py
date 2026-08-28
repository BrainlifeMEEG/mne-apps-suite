#!/usr/bin/env python3
"""Recreate paper Figure 1.

IMPORTANT subject-numbering finding (2026-08-20): the paper's own
"subject 10" example does not correspond to BIDS sub-10. ds000117's
README documents an authoritative crosswalk between four different
numbering schemes (original Wakeman & Henson 2015, openfMRI, the FTP N=16
subset, and BIDS/OpenNeuro) -- none of which are a simple constant offset
of each other. Checked against the actual mne-biomag-group-demo config
(map_subjects dict): key 10 there = W&H "subject_12", which the README
crosswalk maps to BIDS sub-09 -- and sub-09's demo-repo bad-channel list
for run 2 (7 channels) visually matches the paper's published Figure 2
(several red/bad lines), while BIDS sub-10 (= W&H "subject_15" via the
same crosswalk) has zero marked bad channels in any run, which does not
match the published figure at all. So: default subject here is 09,
matching the paper. sub-10 work from earlier in this reproduction is kept
as valid platform work but doesn't correspond to the paper's own example
subject -- pass --subject 10 to still regenerate it for reference.

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
wrong reason (see fig_chpi_diagnostic.py for why it looked like a fix).
The real recipe: maxwell_filter(calibration=..., cross_talk=...,
st_duration=..., origin=..., destination=..., head_pos=...) with bad
channels read from a MaxFilter log file, then raw.filter(None, 40) (MEG)
before plotting.

ds000117's derivatives sidecar JSON on OpenNeuro
(sub-10_ses-meg_task-facerecognition_proc-sss_meg.json) documents exactly
what Elekta's own MaxFilter run used: autobad=on, movecomp=inter,
linefreq=50, hpisubt=amp, origin=[0,8,37]mm, trans=run4 (SSS destination
aligned to run 4's head position, not run 2's own). Tested against that
reference, in order: movement compensation (no improvement -- within-run
head motion here is <0.4mm, negligible); MNE's
find_bad_channels_maxwell() (found nothing, with or without calibration
-- doesn't reproduce Elekta's own autobad thresholds); explicit
origin=(0, 0.008, 0.037) matching Elekta's JSON instead of MNE's
origin="auto" fit, which converged to a substantially different point
([0.26, 37.7, 40.5]mm -- MNE's own "more than 20mm from head frame
origin" warning flagged this): roughly halved the residual difference
(evoked diff std 25.8 -> 13.2 fT, peak 217 -> 60 fT); destination=<S10
run04's raw.fif> (cross-run alignment, matching Elekta's trans=run4 --
run 4's raw fetched via a fresh fif2mne run since it wasn't cached
locally yet) on top of that: diff std 13.2 -> 10.0 fT, peak 60 -> 37 fT.
Both fixes now used here. Remaining ~10 fT residual likely reflects
hpisubt=amp / linefreq=50 / autobad=on, none of which have a direct MNE
equivalent tried yet.

Inputs are local files in data_cache/S10_run02/:
  - unprocessed_raw.fif                 <- fif2mne output (re-saved raw, no SSS)
  - mne_maxwellfilter_dest_run4_meg.fif
        <- mne.preprocessing.maxwell_filter(calibration=..., cross_talk=...,
           origin=(0, 0.008, 0.037), destination=<S10 run04 raw.fif>),
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

CACHE_ROOT = Path(__file__).parent.parent / "data_cache"
STIM_CODES = [5, 6, 7, 13, 14, 15, 17, 18, 19]  # Famous/Unfamiliar/Scrambled onsets


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
    parser.add_argument("--subject", default="09", help="BIDS subject id, zero-padded (default: 09, matches the paper)")
    parser.add_argument("--run", default="02", help="run number, zero-padded (default: 02)")
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    data_dir = CACHE_ROOT / f"S{args.subject}_run{args.run}"
    branches = {
        "A. Unprocessed": data_dir / "unprocessed_raw.fif",
        "B. MNE maxwell_filter": data_dir / "mne_maxwellfilter_dest_run4_meg.fif",
    }
    elekta_path = data_dir / "elekta_maxfilter_meg.fif"
    out = args.out or str(Path(__file__).parent / f"jas_fig1_maxfilter_comparison_S{args.subject}.png")

    evokeds = {}
    for label, path in branches.items():
        evokeds[label] = load_evoked(path)
        print(f"{label}: {len(evokeds[label].ch_names)} magnetometers, "
              f"std={evokeds[label].data.std()*1e15:.1f} fT")

    elekta = load_evoked(elekta_path)
    print(f"Elekta MaxFilter: std={elekta.data.std()*1e15:.1f} fT")

    picks = mne.pick_types(evokeds["A. Unprocessed"].info, meg="mag")
    colors = sensor_rgb(evokeds["A. Unprocessed"].info, picks)

    diff = evokeds["B. MNE maxwell_filter"].copy()
    diff.data = evokeds["B. MNE maxwell_filter"].data - elekta.data

    fig, axes = plt.subplots(1, 3, figsize=(16, 4.5))
    butterfly(axes[0], evokeds["A. Unprocessed"], colors, "A. Unprocessed", ylim=(-550, 550))
    butterfly(axes[1], evokeds["B. MNE maxwell_filter"], colors, "B. MNE maxwell_filter", ylim=axes[0].get_ylim())
    butterfly(axes[2], diff, colors, "C. MNE − Elekta MaxFilter (difference)", ylim=axes[1].get_ylim())

    fig.suptitle(f"Figure 1 (reproduction) — Subject {args.subject}, Run {args.run} — magnetometers, 1–40 Hz")
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    print(f"saved {out}")


if __name__ == "__main__":
    main()
