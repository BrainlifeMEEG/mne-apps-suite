#!/usr/bin/env python3
"""Recreate Jas et al. 2018 Figure 4: subject 3's "famous faces" evoked
response under three preprocessing approaches -- no highpass/baseline
correction (l_freq=None), 1 Hz highpass filtering (l_freq=1), and tSSS
(st_duration=1s) -- illustrating each approach's effect on slow sustained
responses.

Unlike the other figures_jas/ scripts, this one is NOT a direct adaptation
of a single upstream script. original_scripts/results/demos/plot_tsss_analysis.py
(fetched verbatim, subject-3-only) is a much broader interactive QC dump
(~15 plots: raw PSD, events, drop log, 5 per-condition evoked+topomap plots,
ICA scores/sources, whitening) for the tSSS condition alone -- it doesn't
itself build the specific 3-way comparison the paper's Figure 4 describes.
That comparison is assembled here from three separate pipeline outputs for
subject 3 (see cluster/run_subject3_extra.py for how each was produced):
  (a) l_freq=None:  sub003_highpass-NoneHz-ave.fif  (06/07 default -- 06's
      own epoching applies (None, 0) baseline correction when l_freq=None)
  (b) l_freq=1:      sub003_highpass-1Hz-ave.fif     (06/07 re-run with
      config.l_freq patched to 1 -- reuses the highpass-1Hz raw file the
      regular per-subject chain already produces for ICA input)
  (c) tSSS:          sub003-tsss_1-ave.fif            (03's from-scratch
      recompute, then 06/07's tsss=1 branch)

Reads the 'famous' evoked condition specifically (not the combined
'faces') -- checked against the actual published figure
(figures_jas/paper_figure4_reference.png, fetched from frontiersin.org)
after an initial draft used 'faces': the real Figure 4 caption/panel
content is famous faces only.

Restricted to magnetometers (`picks='mag'`, y-axis in fT): the published
figure's y-axis unit (fT, not fT/cm) confirms magnetometers specifically,
consistent with the paper's own figure list description ("evoked responses
in magnetometers").

Uses `Evoked.plot_joint(times=[0, 0.12, 0.4, 2.8], ...)` -- topomap insets
at the published figure's own four timepoints, connected to the butterfly
trace by lines, matching its actual layout. Keeps `spatial_colors=True`
(plot_joint's own default) for the colored traces, matching the published
figure's own style -- but that inset sensor-position-color-legend circle
in the corner isn't wanted (per feedback). There's no plot()/plot_joint()
kwarg to suppress just the inset while keeping colored traces (checked
the docstring) -- it's drawn as a real inset Axes
(`mpl_toolkits.axes_grid1`'s `AxesHostAxes`, nested inside the main
butterfly panel's bounding box), found by inspecting `fig.axes` directly,
so it's removed by class name after the fact instead.

plot_joint() always builds its own standalone figure (no `axes=` embedding
without fiddly ts_args/topomap_args coordination -- checked the docstring,
not assumed), so the three conditions are rendered separately and
composited into one 1x3 page here.
"""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import mne

HERE = os.path.dirname(os.path.abspath(__file__))
ORIGINAL_SCRIPTS = os.path.normpath(os.path.join(HERE, "..", "original_scripts"))
sys.path.insert(0, ORIGINAL_SCRIPTS)
from library.config import meg_dir, set_matplotlib_defaults  # noqa: E402

OUT_DIR = HERE
os.makedirs(OUT_DIR, exist_ok=True)

SUBJECT = "sub003"
data_path = os.path.join(meg_dir, SUBJECT)
TIMES = [0, 0.12, 0.4, 2.8]  # seconds -- matches the published figure's own labels

conditions = [
    ("A", "No highpass", os.path.join(data_path, f"{SUBJECT}_highpass-NoneHz-ave.fif")),
    ("B", "1 Hz highpass", os.path.join(data_path, f"{SUBJECT}_highpass-1Hz-ave.fif")),
    ("C", "tSSS", os.path.join(data_path, f"{SUBJECT}-tsss_1-ave.fif")),
]

set_matplotlib_defaults()
panel_pngs = []

for letter, label, fname in conditions:
    if not os.path.exists(fname):
        print(f"[jas_fig4] WARNING: missing {fname} -- run cluster/run_subject3_extra.py first")
        continue
    famous_evo = mne.read_evokeds(fname, condition="famous")
    fig = famous_evo.plot_joint(times=TIMES, picks="mag", title=f"{letter}. {label}",
                                show=False)
    # plot_joint()'s butterfly panel defaults to spatial_colors=True (kept,
    # matches the paper's own colored traces) but that also draws a small
    # inset Axes -- an AxesHostAxes nested inside the main butterfly axes'
    # bounding box -- showing a sensor-position color-legend circle. Not
    # wanted (per feedback); there's no plot_joint()/plot() kwarg to
    # suppress just the inset while keeping colored traces (checked the
    # docstring), so it's found by class name and removed directly.
    for legend_ax in [a for a in fig.axes if type(a).__name__ == "AxesHostAxes"]:
        fig.delaxes(legend_ax)
    png_path = os.path.join(OUT_DIR, f"_tmp_jas_fig4_panel_{letter}.png")
    fig.savefig(png_path, dpi=150)
    plt.close(fig)
    panel_pngs.append(png_path)
    print(f"[jas_fig4] loaded {fname} (nave={famous_evo.nave})")

fig, axes = plt.subplots(1, len(panel_pngs), figsize=(5 * len(panel_pngs), 4.5))
if len(panel_pngs) == 1:
    axes = [axes]
for ax, png_path in zip(axes, panel_pngs):
    ax.imshow(mpimg.imread(png_path))
    ax.axis("off")
fig.suptitle(f"{SUBJECT}: famous faces")
fig.tight_layout()

out_path = os.path.join(OUT_DIR, "jas_fig4_tsss_analysis_sub003_famous.pdf")
fig.savefig(out_path)
plt.close(fig)
for p in panel_pngs:
    os.remove(p)
print(f"[jas_fig4] saved {out_path}")
