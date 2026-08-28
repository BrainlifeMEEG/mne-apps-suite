#!/usr/bin/env python3
"""Recreate Jas et al. 2018 Figure 7: spatiotemporal cluster stats on EEG
sensors, contrast faces vs. scrambled.

Adapted from
original_scripts/results/statistics/plot_sensor_spatio_temporal_cluster_stats.py
(fetched verbatim). Not edited in place. Changes from the original:
  - `connectivity=` -> `adjacency=` in `permutation_cluster_1samp_test`
    (checked against installed MNE).
  - `mne.channels.find_ch_connectivity` no longer exists at all in current
    MNE -- replaced with `mne.channels.find_ch_adjacency`, confirmed (via
    inspect.signature before writing this) to have the same
    `(info, ch_type)` signature and the same `(matrix, ch_names)` return,
    a genuine drop-in rename, not assumed.
  - `tail=0.` is used to compute `threshold`/`p_thresh` but the actual test
    call passes `tail=1` -- kept exactly as the original has it; that's
    their own methodological choice, not an API issue, not "fixed" here.
  - `n_jobs=2` (hardcoded in the original) kept as-is.
  - `plot_topomap`'s `vmin=`/`vmax=` kwargs no longer exist -- merged into
    a single `vlim=(vmin, vmax)` tuple in current MNE (confirmed via
    inspect.signature before writing this).
  - `pos = mne.find_layout(contrast.info).pos` is wrong for this call: a
    layout's `.pos` is a legacy (x, y, width, height) box-position array
    for the OLD 2D grid-style layout view, not head-normalized sensor
    coordinates -- using its first two columns as topomap positions
    clustered every channel into one corner of the head outline (a real
    bug, caught visually, not from reading the API). Fixed by passing
    `contrast.info` directly as `pos` -- confirmed via
    `plot_topomap`'s own docstring that it accepts an `Info` object
    directly (inferring proper x/y from the montage) when it contains
    exactly one channel type and `len(data)` channels, both true here.
  - `sphere=None` (the default) auto-fits a sphere to this subject's head-
    shape digitization points, and that fit is off-center for this dataset
    (see EEG_SPHERE below) -- skewing the electrode grid up and off-center
    relative to the drawn head outline. Fixed with an explicit sphere.
  - output path points at figures_jas/ instead of a relative '../figures/'.
"""
import os
import sys

import numpy as np
from scipy import stats
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable

import mne
from mne.stats import permutation_cluster_1samp_test
from mne.viz import plot_topomap

HERE = os.path.dirname(os.path.abspath(__file__))
ORIGINAL_SCRIPTS = os.path.normpath(os.path.join(HERE, "..", "original_scripts"))
sys.path.insert(0, ORIGINAL_SCRIPTS)
from library.config import (meg_dir, l_freq, exclude_subjects, annot_kwargs,
                            set_matplotlib_defaults, random_state)  # noqa: E402

OUT_DIR = HERE
os.makedirs(OUT_DIR, exist_ok=True)

###############################################################################
# Read all the data

contrasts = list()
for subject_id in range(1, 20):
    if subject_id in exclude_subjects:
        continue
    subject = "sub%03d" % subject_id
    print("processing subject: %s" % subject)
    data_path = os.path.join(meg_dir, subject)
    contrast = mne.read_evokeds(os.path.join(data_path, '%s_highpass-%sHz-ave.fif'
                                             % (subject, l_freq)),
                                condition='contrast')
    contrast.pick_types(meg=False, eeg=True).crop(None, 0.8)
    contrast.apply_baseline((-0.2, 0.0))
    contrasts.append(contrast)

contrast = mne.combine_evoked(contrasts, 'equal')
print(f"[jas_fig7] {len(contrasts)} subjects contributed")

###############################################################################
# Assemble the data and run the cluster stats on channel data

data = np.array([c.data for c in contrasts])

tail = 0.
p_thresh = 0.01 / (1 + (tail == 0))
n_samples = len(data)
threshold = -stats.t.ppf(p_thresh, n_samples - 1)
if np.sign(tail) < 0:
    threshold = -threshold

adjacency = mne.channels.find_ch_adjacency(contrast.info, 'eeg')[0]

data = np.transpose(data, (0, 2, 1))

cluster_stats = permutation_cluster_1samp_test(
    data, threshold=threshold, n_jobs=2, verbose=True, tail=1,
    adjacency=adjacency, out_type='indices',
    check_disjoint=True, step_down_p=0.05, seed=random_state)

T_obs, clusters, p_values, _ = cluster_stats
good_cluster_inds = np.where(p_values < 0.05)[0]
print("[jas_fig7] Good clusters: %s" % good_cluster_inds)

###############################################################################
# Visualize the spatio-temporal clusters

set_matplotlib_defaults()
times = contrast.times * 1e3
colors = 'r', 'steelblue'
linestyles = '-', '--'

pos = contrast.info  # head-normalized coords inferred from the montage

# sphere=None (plot_topomap's default) fits a sphere to this subject's own
# head-shape digitization points -- for this dataset that fit is off-center
# (MNE's own runtime warning: "(X, Y) fit ... more than 20 mm from head
# frame origin"), which visibly skewed the electrode grid up and off-center
# relative to the drawn head outline (confirmed by comparing sphere=None vs.
# a fixed sphere side by side -- the fixed version lines the ears up at a
# normal height and spreads electrodes evenly across the head, matching the
# published figure much more closely; the auto-fit version crams them near
# the vertex). Using this fixed origin is also MNE's own documented fallback
# value for when no good digitization fit is available (see plot_topomap's
# `sphere` docstring) -- not an arbitrary number.
EEG_SPHERE = (0, 0, 0, 0.095)

T_obs_max = 5.
T_obs_min = -T_obs_max

if len(good_cluster_inds) == 0:
    print("[jas_fig7] No significant clusters found (p < 0.05) -- nothing to plot. "
          "This can happen legitimately; not necessarily a bug.")

for i_clu, clu_idx in enumerate(good_cluster_inds):
    time_inds, space_inds = np.squeeze(clusters[clu_idx])
    ch_inds = np.unique(space_inds)
    time_inds = np.unique(time_inds)

    T_obs_map = T_obs[time_inds, ...].mean(axis=0)

    signals = data[..., ch_inds].mean(axis=-1)
    sig_times = times[time_inds]

    mask = np.zeros((T_obs_map.shape[0], 1), dtype=bool)
    mask[ch_inds, :] = True

    fig, ax_topo = plt.subplots(1, 1, figsize=(7, 2.))

    image, _ = plot_topomap(T_obs_map, pos, mask=mask, axes=ax_topo,
                            vlim=(T_obs_min, T_obs_max), sphere=EEG_SPHERE, show=False)

    divider = make_axes_locatable(ax_topo)
    ax_colorbar = divider.append_axes('right', size='5%', pad=0.05)
    plt.colorbar(image, cax=ax_colorbar, format='%0.1f')
    ax_topo.set_xlabel('Averaged t-map\n({:0.1f} - {:0.1f} ms)'.format(*sig_times[[0, -1]]))
    ax_topo.annotate(chr(65 + 2 * i_clu), (0.1, 1.1), **annot_kwargs)

    ax_signals = divider.append_axes('right', size='300%', pad=1.2)
    for signal, name, col, ls in zip(signals, ['Contrast'], colors, linestyles):
        ax_signals.plot(times, signal * 1e6, color=col, linestyle=ls, label=name)

    ax_signals.axvline(0, color='k', linestyle=':', label='stimulus onset')
    ax_signals.set_xlim([times[0], times[-1]])
    ax_signals.set_xlabel('Time [ms]')
    ax_signals.set_ylabel('Amplitude [uV]')

    ymin, ymax = ax_signals.get_ylim()
    ax_signals.fill_betweenx((ymin, ymax), sig_times[0], sig_times[-1], color='orange', alpha=0.3)
    ax_signals.legend(loc='lower right')
    title = 'Cluster #{0} (p < {1:0.3f})'.format(i_clu + 1, p_values[clu_idx])
    ax_signals.set(ylim=[ymin, ymax], title=title)
    ax_signals.annotate(chr(65 + 2 * i_clu + 1), (-0.125, 1.1), **annot_kwargs)

    fig.tight_layout(pad=0.5, w_pad=0)
    fig.subplots_adjust(bottom=.05)
    out_path = os.path.join(
        OUT_DIR, 'jas_fig7_spatiotemporal_cluster_highpass-%sHz-%02d.pdf' % (l_freq, i_clu))
    fig.savefig(out_path)
    print(f"[jas_fig7] saved {out_path}")
