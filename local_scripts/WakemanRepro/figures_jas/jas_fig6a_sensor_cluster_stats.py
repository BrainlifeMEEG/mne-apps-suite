#!/usr/bin/env python3
"""Recreate Jas et al. 2018 Figure 6A: non-parametric temporal cluster
stats on sensor EEG065, contrast faces vs. scrambled.

Adapted from original_scripts/results/statistics/plot_sensor_cluster_stats_eeg_channel.py
(fetched verbatim). Not edited in place. Changes from the original:
  - `permutation_cluster_1samp_test`'s `connectivity=` kwarg is now
    `adjacency=` in current MNE (checked against the installed version,
    the function's other behavior is unchanged) -- confirmed via
    inspect.signature before writing this, not assumed.
  - `show_sensors=4` (a matplotlib legend-location int code) raised
    TypeError at runtime despite `int` being listed as a valid type in
    plot_compare_evokeds's own docstring -- a real inconsistency between
    the docstring and the actual `_validate_type` check in this MNE
    version. Replaced with the equivalent string position, `'lower right'`
    (matplotlib loc code 4), which the same validator accepts cleanly.
  - `permutation_cluster_1samp_test`'s `out_type` default changed from
    `'mask'` (old MNE: for 1D data with no adjacency, clusters were `slice`
    objects) to `'indices'` (current MNE: clusters are index ndarrays) --
    confirmed via inspect.signature + docstring, not assumed. The original
    script's `c.start`/`c.stop` doesn't apply to an ndarray; replaced with
    `c.min()`/`c.max()` on the index array, same visual intent (span the
    cluster's temporal extent).
  - the original already filters `exclude_subjects` itself (1, 5, 16) --
    no change needed there.
  - output path points at figures_jas/ instead of a relative '../figures/'.
  - EEG065, not EEG070: the original hardcodes EEG065 already, consistent
    with 09-time_frequency.py's actual code (its docstring says EEG070,
    its code says EEG065 -- a known upstream inconsistency, see GLITCHES.md).
"""
import os
import sys

import numpy as np
from scipy import stats
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import mne
from mne.stats import permutation_cluster_1samp_test

HERE = os.path.dirname(os.path.abspath(__file__))
ORIGINAL_SCRIPTS = os.path.normpath(os.path.join(HERE, "..", "original_scripts"))
sys.path.insert(0, ORIGINAL_SCRIPTS)
from library.config import (meg_dir, l_freq, N_JOBS, set_matplotlib_defaults,
                            exclude_subjects, annot_kwargs, random_state)  # noqa: E402

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
    contrast.apply_baseline((-0.2, 0.0)).crop(None, 0.8)
    contrast.pick_types(meg=False, eeg=True)
    contrasts.append(contrast)

contrast = mne.combine_evoked(contrasts, 'equal')
print(f"[jas_fig6a] {len(contrasts)} subjects contributed")

channel = 'EEG065'
idx = contrast.ch_names.index(channel)
fig_compare = mne.viz.plot_compare_evokeds(contrast, [idx], show_sensors='lower right',
                                           truncate_xaxis=False, show=False)

###############################################################################
# Assemble the data and run the cluster stats on channel data

data = np.array([c.data[idx] for c in contrasts])

n_permutations = 1000
p_initial = 0.001
p_thresh = 0.01
adjacency = None  # renamed from `connectivity` -- see module docstring
tail = 0.

n_samples = len(data)
threshold = -stats.t.ppf(p_initial / (1 + (tail == 0)), n_samples - 1)
if np.sign(tail) < 0:
    threshold = -threshold

cluster_stats = permutation_cluster_1samp_test(
    data, threshold=threshold, n_jobs=N_JOBS, verbose=True, tail=tail,
    step_down_p=0.05, adjacency=adjacency,
    n_permutations=n_permutations, seed=random_state)

T_obs, clusters, cluster_p_values, _ = cluster_stats
print(f"[jas_fig6a] cluster p-values: {cluster_p_values}")

###############################################################################
# Visualize results

set_matplotlib_defaults()

times = 1e3 * contrast.times

fig, axes = plt.subplots(2, sharex=True, figsize=(3.3, 2.5))
ax = axes[0]
ax.plot(times, 1e6 * data.mean(axis=0), label="ERP Contrast")
ax.set(title='Channel : ' + channel, ylabel="EEG (uV)", ylim=[-5, 2.5])
ax.legend()
ax.annotate('A', (-0.16, 1.15), **annot_kwargs)

ax = axes[1]
h1 = None
for i_c, c in enumerate(clusters):
    c = c[0]  # tuple of one ndarray (1D data, out_type='indices' default)
    if cluster_p_values[i_c] < p_thresh:
        h1 = ax.axvspan(times[c.min()], times[c.max()], color='r', alpha=0.3)
ax.plot(times, T_obs, 'g')
if h1 is not None:
    ax.legend((h1,), ('p < %s' % p_thresh,), loc='upper right', ncol=1)
ax.set(xlabel="time (ms)", ylabel="T-values",
       ylim=[-10., 10.], xlim=contrast.times[[0, -1]] * 1000)
fig.tight_layout(pad=0.5)
out_path = os.path.join(OUT_DIR, 'jas_fig6a_sensor_cluster_stats_highpass-%sHz.pdf' % (l_freq,))
fig.savefig(out_path, bbox_inches='tight')
print(f"[jas_fig6a] saved {out_path}")
