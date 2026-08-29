#!/usr/bin/env python3
"""Recreate Jas et al. 2018 Figure 11: group-average source reconstruction,
dSPM (left) and LCMV (right), ventral view of the fsaverage inflated
surface, anterior pointing down, left/right on the figure matching
anatomical left/right.

Reads cluster/run_group_source_average.py's output
(`contrast-average_highpass-<l_freq>Hz` for dSPM -- a VectorSourceEstimate,
`.magnitude()`'d here to get a scalar activation map matching the paper's
colored heatmap; `contrast-average-lcmv_highpass-<l_freq>Hz` for LCMV --
already scalar). Both already morphed to fsaverage by that script, and
both were rebuilt after cluster/run_subject_coreg.py's coregistration fix
(see that script's docstring -- nasion + head-shape points were pulling
every subject's fit into an unphysical rotation).

Offscreen pyvista rendering (same as Figure 9), one screenshot per method,
composited into one 1x2 page.

Time point: fixed at t=0.168s (per review feedback), not a peak search.

Orientation: `hemi='both'+views='ventral'` renders anterior at the TOP and
right hemisphere on the LEFT by default -- confirmed directly, not
assumed, with two synthetic test stcs (one with data on RH-only vertices,
one with data on anterior-only LH vertices) rendered and visually
inspected. The published figure has anterior at the BOTTOM and right
hemisphere on the right -- a 180-degree image rotation fixes both at once
(equivalent to flipping both axes simultaneously).

Colorbar: rendered separately in matplotlib (not pyvista's own embedded
one) using an alpha-ramped colormap so the sub-vmin range -- fully
transparent in the actual brain render (`transparent=True`) -- reads as
fading out on the colorbar too, instead of looking like solid opaque
color all the way to zero (per review feedback: "colorbars should reveal
transparency"). A first version rendered pyvista's colorbar/text into the
same raster as the brain -- fragile to flip cleanly (see GLITCHES.md's
"Figures 11/12: two more real bugs" for why that approach was replaced).
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
from matplotlib.colors import ListedColormap
import mne

HERE = os.path.dirname(os.path.abspath(__file__))
ORIGINAL_SCRIPTS = os.path.normpath(os.path.join(HERE, "..", "original_scripts"))
sys.path.insert(0, ORIGINAL_SCRIPTS)
from library.config import meg_dir, subjects_dir, l_freq  # noqa: E402

OUT_DIR = HERE
os.makedirs(OUT_DIR, exist_ok=True)

TIME_POINT = 0.168  # seconds -- fixed per review feedback, not a peak search


def transparent_hot(vmin, vmax, n=256):
    """'hot' colormap with alpha ramping 0->1 from 0 up to vmin, matching
    plot_topomap/stc.plot's own transparent=True behavior (values below
    vmin are fully suppressed in the render) -- so a colorbar built from
    this looks the same way: faded/transparent below vmin, opaque hot
    color from vmin to vmax.
    """
    base = plt.get_cmap("hot", n)
    colors = base(np.linspace(0, 1, n))
    frac_vmin = np.clip(vmin / vmax, 0, 1) if vmax > 0 else 0
    ramp_end = max(int(frac_vmin * n), 1)
    colors[:ramp_end, -1] = np.linspace(0, 1, ramp_end)
    return ListedColormap(colors)


def render(stc, png_path):
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
    Image.open(png_path).transpose(Image.ROTATE_180).save(png_path)
    print(f"[jas_fig11] rendered -> {png_path} (rotated 180: anterior down, R on right)")
    return vmin, vmax


dspm_path = os.path.join(meg_dir, f"contrast-average_highpass-{l_freq}Hz")
lcmv_path = os.path.join(meg_dir, f"contrast-average-lcmv_highpass-{l_freq}Hz")

dspm_stc = mne.read_source_estimate(dspm_path, "fsaverage").magnitude()
lcmv_stc = mne.read_source_estimate(lcmv_path, "fsaverage")

dspm_stc_t = dspm_stc.copy().crop(TIME_POINT, TIME_POINT)
lcmv_stc_t = lcmv_stc.copy().crop(TIME_POINT, TIME_POINT)

png_dspm = os.path.join(OUT_DIR, "_tmp_jas_fig11_dspm.png")
png_lcmv = os.path.join(OUT_DIR, "_tmp_jas_fig11_lcmv.png")
dspm_clim = render(dspm_stc_t, png_dspm)
lcmv_clim = render(lcmv_stc_t, png_lcmv)

fig, axes = plt.subplots(1, 2, figsize=(10, 5))
for ax, png, label, clim in zip(axes, [png_dspm, png_lcmv], ["dSPM", "LCMV"],
                                [dspm_clim, lcmv_clim]):
    ax.imshow(mpimg.imread(png))
    ax.axis("off")
    ax.set_title(label)
    cmap = transparent_hot(clim[0], clim[1])
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin=0, vmax=clim[1]))
    fig.colorbar(sm, ax=ax, orientation="horizontal", fraction=0.046, pad=0.04)
fig.suptitle(f"Group average, faces vs. scrambled contrast (ventral view, t={TIME_POINT * 1000:.0f}ms)")
fig.tight_layout()

out_path = os.path.join(OUT_DIR, f"jas_fig11_group_source_highpass-{l_freq}Hz.pdf")
fig.savefig(out_path)
for p in (png_dspm, png_lcmv):
    os.remove(p)
print(f"[jas_fig11] saved {out_path}")
