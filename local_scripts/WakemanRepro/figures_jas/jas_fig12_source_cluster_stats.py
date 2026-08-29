#!/usr/bin/env python3
"""Recreate Jas et al. 2018 Figure 12: spatio-temporal source-space
clusters (faces vs. scrambled, nonparametric permutation test), vertex
colors = duration each vertex was in a significant cluster.

Adapted from original_scripts/results/statistics/plot_source_stats.py
(fetched verbatim). Not edited in place. Changes from the original:
  - `from mayavi import mlab` + `brain.plot(...)`/`mlab.view(...)` --
    mayavi isn't installed in this environment (confirmed, see GLITCHES.md
    Step 0 audit) and is no longer MNE's default 3D backend anyway;
    replaced with the same pyvista offscreen-rendering approach used for
    Figures 9/11 (`brain.show_view()` + `brain.save_image()`, pyvista's
    own equivalents of the removed mayavi calls).
  - `mne.spatial_src_connectivity` -> `mne.spatial_src_adjacency` (removed
    rename, same pattern as Figs 6A/7's `connectivity=`->`adjacency=`).
  - `spatio_temporal_cluster_1samp_test`'s `connectivity=` kwarg ->
    `adjacency=` (confirmed via inspect.signature, same rename).
  - Reads per-subject morphed faces_eq/scrambled_eq dSPM stcs from
    cluster/run_group_source_average.py's output (all 16 subjects) instead
    of a bespoke read loop -- same files the original script itself reads,
    just produced by this project's own adapted pipeline script. Rebuilt
    after cluster/run_subject_coreg.py's coregistration fix (nasion +
    head-shape points were pulling every subject's fit into an unphysical
    rotation, see that script's docstring) -- the underlying per-subject
    dSPM stcs changed, so this cluster test needed rerunning from scratch,
    not just a rendering fix.
  - output path points at figures_jas/ instead of a relative '../figures/'.

Heaviest step in this project's whole source-space chain: permutation
clustering over ~20484 fsaverage vertices x many timepoints, 1024
permutations. Expect real wall-clock time here -- run with n_jobs from
config, not assumed fast.
"""
import os
import sys
from functools import partial

os.environ.setdefault("PYVISTA_OFF_SCREEN", "true")
os.environ.setdefault("MNE_3D_BACKEND", "pyvistaqt")

import numpy as np
from scipy import stats
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.image as mpimg

import mne
from mne.stats import (spatio_temporal_cluster_1samp_test,
                       summarize_clusters_stc, ttest_1samp_no_p)

HERE = os.path.dirname(os.path.abspath(__file__))
ORIGINAL_SCRIPTS = os.path.normpath(os.path.join(HERE, "..", "original_scripts"))
sys.path.insert(0, ORIGINAL_SCRIPTS)
from library.config import (meg_dir, subjects_dir, fsaverage_vertices,
                            N_JOBS, l_freq, random_state)  # noqa: E402
sys.path.insert(0, os.path.join(HERE, "..", "cluster"))
from crosswalk import EXCLUDED  # noqa: E402

OUT_DIR = HERE
os.makedirs(OUT_DIR, exist_ok=True)

###############################################################################
# Read all the data

faces, scrambled = [], []
for subject_id in range(1, 20):
    if subject_id in EXCLUDED:
        continue
    subject = "sub%03d" % subject_id
    print(f"[jas_fig12] loading subject {subject}")
    data_path = os.path.join(meg_dir, subject)
    stc = mne.read_source_estimate(
        os.path.join(data_path, f"mne_dSPM_inverse_morph_highpass-{l_freq}Hz-faces_eq"))
    faces.append(stc.magnitude().crop(None, 0.8).data.T)
    stc = mne.read_source_estimate(
        os.path.join(data_path, f"mne_dSPM_inverse_morph_highpass-{l_freq}Hz-scrambled_eq"))
    scrambled.append(stc.magnitude().crop(None, 0.8).data.T)
    tstep = stc.tstep

###############################################################################
# Set up contrast + threshold

X = np.array(faces, float) - np.array(scrambled, float)
fsaverage_src = mne.read_source_spaces(
    os.path.join(subjects_dir, "fsaverage", "bem", "fsaverage-5-src.fif"))
adjacency = mne.spatial_src_adjacency(fsaverage_src)

p_threshold = 0.001
t_threshold = -stats.distributions.t.ppf(p_threshold / 2., len(X) - 1)

###############################################################################
# Cluster permutation test (n_permutations=1024, matching the original's
# own speed/simplicity tradeoff -- see its own comment about 32768 being
# the "exact" but impractically slow choice)

# config.py's own N_JOBS resolves to 1 on this machine (its branching is
# keyed off environment/hostname checks tuned for the original authors'
# setup, not this desktop) -- this is by far the heaviest single step in
# the whole reproduction (~20484 fsaverage vertices x many timepoints x
# 1024 permutations), and this desktop has 16 real cores sitting idle, so
# overriding just for this one call rather than accepting a single-core
# runtime here.
cluster_n_jobs = min(8, N_JOBS if N_JOBS > 1 else 8)
stat_fun = partial(ttest_1samp_no_p, sigma=1e-3)
T_obs, clusters, cluster_p_values, H0 = clu = spatio_temporal_cluster_1samp_test(
    X, adjacency=adjacency, n_jobs=cluster_n_jobs, threshold=t_threshold,
    stat_fun=stat_fun, buffer_size=None, seed=random_state,
    step_down_p=0.05, verbose=True)

good_cluster_inds = np.where(cluster_p_values < 0.05)[0]
n_lh_vert = len(fsaverage_vertices[0])
for ind in good_cluster_inds:
    time_inds, space_inds = np.squeeze(clusters[ind])
    verts = np.unique(space_inds)
    n_lh = int((verts < n_lh_vert).sum())
    n_rh = int((verts >= n_lh_vert).sum())
    print(f"[jas_fig12] found cluster p={cluster_p_values[ind]:g}  "
        f"n_vertices={len(verts)} (LH={n_lh}, RH={n_rh})")
if len(good_cluster_inds) == 0:
    print("[jas_fig12] WARNING: no significant clusters found (p < 0.05).")

###############################################################################
# Visualize

# tstep in *milliseconds*, not the seconds `stc.tstep` naturally is --
# summarize_clusters_stc's own docstring says tstep should be in seconds,
# but its output values (cluster duration) then come out in those same
# units, and `pos_lims`/`time_label` below are unambiguously ms-scaled
# (max 100, label says "(ms)", matching the original script verbatim).
# Passing tstep in seconds gave a real, confirmed bug: max duration
# rendered as ~0.055, entirely below pos_lims' own 0.1 lower threshold,
# so nothing was ever colored -- a fully gray brain despite 3 genuinely
# significant clusters existing (verified by directly inspecting
# stc_all_cluster_vis.data.max() before vs. after this fix: 0.055 -> 54.5,
# only the latter actually falls inside the intended 0.1-100 display
# range). The original script's own tstep=tstep (seconds) must have
# behaved differently in whatever much older MNE version it was written
# against -- same "old code, current MNE renders/behaves differently"
# pattern as everywhere else in this project, not a new kind of bug.
stc_all_cluster_vis = summarize_clusters_stc(
    clu, tstep=tstep * 1000, vertices=fsaverage_vertices, subject="fsaverage")
pos_lims = [0, 0.1, 100 if l_freq is None else 30]
# colorbar=False, time_label=None (rendered separately below via matplotlib,
# not pyvista): hemi='both'+views='ventral' renders anterior at the TOP and
# right hemisphere on the LEFT of the image by default -- confirmed
# directly (not assumed) with two synthetic test stcs (RH-only vertices;
# anterior-only LH vertices), each rendered and visually inspected. The
# published figure has anterior at the BOTTOM, right hemisphere on the
# right -- fixed with a 180-degree image rotation (flips both axes at
# once). A first attempt only flipped left-right, leaving anterior at the
# top (missed until reviewed against the published figure directly) and
# cropped-and-flipped just the "brain region" by a fixed pixel-row
# boundary rather than rotating the whole (colorbar-free) image -- fragile
# in practice, see GLITCHES.md's "Figures 11/12: two more real bugs".
# Cleaner fix: never let pyvista draw a colorbar/label into the same raster
# -- rotate the whole (now label-free) image safely, draw a matching
# matplotlib colorbar afterward using the exact colormap MNE would have
# used (extracted via its own internal `_process_clim`, not a matplotlib
# lookalike) and the same pos_lims values.
brain = stc_all_cluster_vis.plot(
    hemi="both", subjects_dir=subjects_dir,
    time_label=None, views="ventral",
    clim=dict(pos_lims=pos_lims, kind="value"), size=(1000, 1000),
    background="white", foreground="black", colorbar=False,
    # time_viewer defaults to True for a single time point, wiring up
    # interactive picking that needs a real interactor -- doesn't exist
    # under pure offscreen rendering (PYVISTA_OFF_SCREEN=true), crashing
    # with "'NoneType' object has no attribute 'add_observer'" (hit for
    # real, see Figure 11's identical fix). This is a static screenshot.
    time_viewer=False, show_traces=False)

out_path = os.path.join(OUT_DIR, f"jas_fig12_source_cluster_stats_highpass-{l_freq}Hz.png")
brain.save_image(out_path)
brain.close()

from PIL import Image
Image.open(out_path).transpose(Image.ROTATE_180).save(out_path)

from mne.viz._3d import _process_clim
cmap = _process_clim(dict(pos_lims=pos_lims, kind="value"), "auto", True)["colormap"]

fig, ax = plt.subplots(figsize=(10, 10.6))
ax.imshow(mpimg.imread(out_path))
ax.axis("off")
sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin=-pos_lims[-1], vmax=pos_lims[-1]))
cbar = fig.colorbar(sm, ax=ax, orientation="horizontal", fraction=0.05, pad=0.02)
cbar.set_label("Duration significant (ms)")
fig.tight_layout()
fig.savefig(out_path, dpi=150)
plt.close(fig)
print(f"[jas_fig12] saved {out_path} (brain mirrored L/R to match paper's convention)")
