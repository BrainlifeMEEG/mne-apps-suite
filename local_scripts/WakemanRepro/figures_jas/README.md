# Jas et al. 2018 figure reproductions

Literal reproductions of **Jas et al. 2018** ("A Reproducible MEG/EEG
Group Study With the MNE Software", Frontiers in Neuroscience,
10.3389/fnins.2018.00530), all sensor-space (Figures 8–12 are
source-space and stay out of scope — standing project decision).

| Fig | Script | Output |
|---|---|---|
| 1 | `jas_fig1_maxfilter_comparison.py` | `jas_fig1_maxfilter_comparison_S{09,10}.png` |
| 2 | `jas_fig2_psd.py` | `jas_fig2_psd_S09.png` |
| 3 | `jas_fig3_filter_response.py` (+ `jas_fig3_compute_old_mne_012_filters.py`, `old_mne_012_reference/`) | `jas_fig3_filter_response.png` |
| 4 | `jas_fig4_tsss_analysis.py` | `jas_fig4_tsss_analysis_sub003_famous.pdf` |
| 5 | `jas_fig5_grand_average.py` (panel A) + `cluster/build_fig5_panel_b.py` (panel B) | `jas_fig5_grand_average_highpass-{NoneHz,1Hz}.pdf` |
| 6A/B | `jas_fig6a_sensor_cluster_stats.py`, `jas_fig6b_decoding.py` | matching `.pdf`/`.png` |
| 7 | `jas_fig7_spatiotemporal_cluster.py` | `jas_fig7_spatiotemporal_cluster_highpass-NoneHz-00.pdf` |
| 99 | `99_reports_sensor_only.py` (sensor-only adaptation of `original_scripts/99-make_reports.py`) | `report_sensor_sub*.html`, `report_sensor_average.html` |

`build_comparison_pdf.py` → `jas_figures_comparison.pdf`: side-by-side,
one page per figure, published figure (top) vs. our reproduction (bottom).
Self-contained (renders any `.pdf` inputs via `pdftoppm` into a temp dir).

## `paper_figure{1..7}_reference.{png,webp}`

Fetched from frontiersin.org for the comparison PDF. **Gitignored, not
committed** — not ours to redistribute. If missing, refetch from
`https://www.frontiersin.org/files/Articles/345102/xml-images/fnins-12-00530-g000N.webp`
(N = figure number, zero-padded to 4 digits).

## Known gaps

None currently open. See `../original_scripts/GLITCHES.md`'s Phase 7
sections for how the earlier gaps (Figure 5 panel B needing a 16-subject
`l_freq=1` rerun of 06/07; Figure 4's topomap insets; Figure 7's
`find_layout`/`plot_topomap` position bug) were resolved.

See `../original_scripts/GLITCHES.md`'s Phase 7 sections for the full
methodology writeup (API fixes, overwrite-gap fixes, everything checked
against the installed environment rather than assumed) and
`../figures/README.md` for why this directory exists separately from
`../figures/`.
