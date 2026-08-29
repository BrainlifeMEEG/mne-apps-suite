#!/usr/bin/env python3
"""Recreate Jas et al. 2018 Figure 11: group-average source reconstruction,
dSPM (left) and LCMV (right), ventral view of the fsaverage inflated
surface, anterior-posterior running bottom-to-top, right hemisphere on the
right.

Reads cluster/run_group_source_average.py's output
(`contrast-average_highpass-<l_freq>Hz` for dSPM -- a VectorSourceEstimate,
`.magnitude()`'d here to get a scalar activation map matching the paper's
colored heatmap; `contrast-average-lcmv_highpass-<l_freq>Hz` for LCMV --
already scalar). Both already morphed to fsaverage by that script.

Offscreen pyvista rendering (same as Figure 9), one screenshot per method,
composited into one 1x2 page.
"""
import os
import sys

os.environ.setdefault("PYVISTA_OFF_SCREEN", "true")
os.environ.setdefault("MNE_3D_BACKEND", "pyvistaqt")

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import mne

HERE = os.path.dirname(os.path.abspath(__file__))
ORIGINAL_SCRIPTS = os.path.normpath(os.path.join(HERE, "..", "original_scripts"))
sys.path.insert(0, ORIGINAL_SCRIPTS)
from library.config import meg_dir, subjects_dir, l_freq  # noqa: E402

OUT_DIR = HERE
os.makedirs(OUT_DIR, exist_ok=True)


def render(stc, title, png_path):
    # Explicit clim (not MNE's own 'auto' percentile default) so the exact
    # same vmin/vmax can be reused for the matplotlib colorbar drawn in the
    # composite below -- guarantees the two are never out of sync.
    data = stc.data
    vmin = float(np.percentile(data[data > 0], 2)) if (data > 0).any() else 0.0
    vmax = float(data.max())
    # time_viewer defaults to 'auto' (-> True for a single time point), which
    # wires up an interactive picking/observer setup that needs a real
    # interactor -- doesn't exist under pure offscreen rendering
    # (PYVISTA_OFF_SCREEN=true), crashing with "'NoneType' object has no
    # attribute 'add_observer'". Explicitly False since this is a static
    # screenshot, not an interactive session -- confirmed by hitting the
    # crash first, not assumed upfront.
    #
    # colorbar=False here, deliberately: hemi='both'+views='ventral' renders
    # RH on the LEFT of the image (verified directly with a test stc: RH-only
    # data renders on the image's left side) -- the paper's own Figure 11
    # caption is explicit ("Right hemisphere is on the right side"), the
    # opposite convention, so the render needs mirroring. A first attempt
    # cropped-and-flipped just the "brain region" of the image (leaving
    # pyvista's own embedded colorbar/text unflipped) using a fixed pixel-row
    # boundary -- fragile in practice: the real brain content's extent varies
    # enough between renders that a fixed fraction either clipped real
    # content or left colorbar text partially flipped (both actually
    # happened, on different attempts). Cleaner fix: never let pyvista draw
    # a colorbar into the same raster at all -- flip the whole (now
    # colorbar-free) image safely, and draw a proper matplotlib colorbar in
    # the composite figure below instead, using the real vmin/vmax from the
    # data (not guessed).
    brain = stc.plot(subject="fsaverage", surface="inflated", hemi="both",
                     views="ventral", subjects_dir=subjects_dir,
                     background="white", foreground="black",
                     time_label=None, colorbar=False, size=(800, 800),
                     clim=dict(kind="value", lims=[vmin, (vmin + vmax) / 2, vmax]),
                     colormap="hot", transparent=True,
                     time_viewer=False, show_traces=False)
    brain.save_image(png_path)
    brain.close()

    from PIL import Image
    Image.open(png_path).transpose(Image.FLIP_LEFT_RIGHT).save(png_path)
    print(f"[jas_fig11] rendered {title} -> {png_path} (mirrored L/R)")
    return vmin, vmax


dspm_path = os.path.join(meg_dir, f"contrast-average_highpass-{l_freq}Hz")
lcmv_path = os.path.join(meg_dir, f"contrast-average-lcmv_highpass-{l_freq}Hz")

dspm_stc = mne.read_source_estimate(dspm_path, "fsaverage").magnitude()
lcmv_stc = mne.read_source_estimate(lcmv_path, "fsaverage")

# Peak-latency snapshot -- the paper shows a single static time point, not
# an animation; picking each method's own peak (its own strongest moment)
# rather than a fixed arbitrary time. Cropped to (None, 0.8) first, matching
# jas_fig12_source_cluster_stats.py's own crop of the exact same contrast --
# this data is l_freq=None (no highpass), and picking a peak over the FULL
# epoch (to 2.9s) first found one at ~2.26s, squarely in the slow-drift
# region Figs 4/5 already document extensively for this same unfiltered
# condition -- not the face-processing response this figure is about. Using
# the paper's own established analysis window instead of an arbitrary one.
dspm_peak = dspm_stc.copy().crop(None, 0.8).get_peak(vert_as_index=False, time_as_index=False)[1]
lcmv_peak = lcmv_stc.copy().crop(None, 0.8).get_peak(vert_as_index=False, time_as_index=False)[1]
dspm_stc_t = dspm_stc.copy().crop(dspm_peak, dspm_peak)
lcmv_stc_t = lcmv_stc.copy().crop(lcmv_peak, lcmv_peak)

png_dspm = os.path.join(OUT_DIR, "_tmp_jas_fig11_dspm.png")
png_lcmv = os.path.join(OUT_DIR, "_tmp_jas_fig11_lcmv.png")
dspm_clim = render(dspm_stc_t, f"dSPM @ {dspm_peak * 1000:.0f}ms", png_dspm)
lcmv_clim = render(lcmv_stc_t, f"LCMV @ {lcmv_peak * 1000:.0f}ms", png_lcmv)

fig, axes = plt.subplots(1, 2, figsize=(10, 5))
for ax, png, label, t, clim in zip(
        axes, [png_dspm, png_lcmv], ["dSPM", "LCMV"],
        [dspm_peak, lcmv_peak], [dspm_clim, lcmv_clim]):
    ax.imshow(mpimg.imread(png))
    ax.axis("off")
    ax.set_title(f"{label} (peak @ {t * 1000:.0f}ms)")
    sm = plt.cm.ScalarMappable(cmap="hot", norm=plt.Normalize(vmin=clim[0], vmax=clim[1]))
    fig.colorbar(sm, ax=ax, orientation="horizontal", fraction=0.046, pad=0.04)
fig.suptitle("Group average, faces vs. scrambled contrast (ventral view)")
fig.tight_layout()

out_path = os.path.join(OUT_DIR, f"jas_fig11_group_source_highpass-{l_freq}Hz.pdf")
fig.savefig(out_path)
for p in (png_dspm, png_lcmv):
    os.remove(p)
print(f"[jas_fig11] saved {out_path}")
