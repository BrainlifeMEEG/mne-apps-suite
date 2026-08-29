# Jas et al. 2018 figure reproductions

Literal reproductions of **Jas et al. 2018** ("A Reproducible MEG/EEG
Group Study With the MNE Software", Frontiers in Neuroscience,
10.3389/fnins.2018.00530) — sensor-space (1–7) and source-space (8–12).

| Fig | Script | Output |
|---|---|---|
| 1 | `jas_fig1_maxfilter_comparison.py` | `jas_fig1_maxfilter_comparison_S{09,10}.png` |
| 2 | `jas_fig2_psd.py` | `jas_fig2_psd_S09.png` |
| 3 | `jas_fig3_filter_response.py` (+ `jas_fig3_compute_old_mne_012_filters.py`, `old_mne_012_reference/`) | `jas_fig3_filter_response.png` |
| 4 | `jas_fig4_tsss_analysis.py` | `jas_fig4_tsss_analysis_sub003_famous.pdf` |
| 5 | `jas_fig5_grand_average.py` (panel A) + `cluster/build_fig5_panel_b.py` (panel B) | `jas_fig5_grand_average_highpass-{NoneHz,1Hz}.pdf` |
| 6A/B | `jas_fig6a_sensor_cluster_stats.py`, `jas_fig6b_decoding.py` | matching `.pdf`/`.png` |
| 7 | `jas_fig7_spatiotemporal_cluster.py` | `jas_fig7_spatiotemporal_cluster_highpass-NoneHz-00.pdf` |
| 8 | `jas_fig8_bem_surfaces.py` (needs `cluster/run_subject_anatomy.py`) | `jas_fig8_bem_surfaces_sub004.pdf` |
| 9 | `jas_fig9_coregistration.py` (needs `cluster/run_subject_{anatomy,coreg}.py`) | `jas_fig9_coregistration_sub010.png` |
| 10 | `jas_fig10_whitened_gfp.py` (needs only cov+evoked, no source-space dependency) | `jas_fig10_whitened_gfp_sub004.pdf` |
| 11 | `jas_fig11_group_source.py` (needs `cluster/run_group_source_average.py`, all 16 subjects) | `jas_fig11_group_source_highpass-NoneHz.pdf` |
| 12 | `jas_fig12_source_cluster_stats.py` (needs `cluster/run_group_source_average.py`, all 16 subjects) | `jas_fig12_source_cluster_stats_highpass-NoneHz.png` |
| 99 | `99_reports_sensor_only.py` (sensor-only adaptation of `original_scripts/99-make_reports.py`) | `report_sensor_sub*.html`, `report_sensor_average.html` |

**Source-space (8–12) pipeline order**: `cluster/run_subject_anatomy.py` →
`cluster/run_subject_coreg.py` → `cluster/run_subject_forward_inverse.py` →
`cluster/run_subject_lcmv.py`, per subject (all 4 bundled in
`cluster/submit_source_space.slurm.sh`, one Slurm array task per subject),
then `cluster/setup_fsaverage.py` (once) + `cluster/run_group_source_average.py`
(once, after all 16 subjects) before Figures 11/12. None of this is a
literal rerun of `original_scripts/01,12-16` — real gaps in what this
dataset's public release ships (no FLASH MRI, no full recon-all, no
pre-existing coregistration) forced substitutions, all in
`../original_scripts/GLITCHES.md`'s "Source-space onboarding" section.

`build_comparison_pdf.py` → `jas_figures_comparison.pdf`: side-by-side,
one page per figure, published figure (top) vs. our reproduction (bottom).
Self-contained (renders any `.pdf` inputs via `pdftoppm` into a temp dir).

## `paper_figure{1..12}_reference.{png,webp}`

Fetched from frontiersin.org for the comparison PDF. **Gitignored, not
committed** — not ours to redistribute. If missing, refetch from
`https://www.frontiersin.org/files/Articles/345102/xml-images/fnins-12-00530-g000N.webp`
(N = figure number, zero-padded to 4 digits).

## Known gaps

None currently open. All 12 figures built and verified against the
published paper figures. Two standing, documented (not "fixable")
limitations, neither unique to this reproduction:
- Figures 8/9's anterior/facial region is affected by this dataset's own
  MRI defacing (anonymization) — acknowledged by the paper's own Figure 9
  caption too.
- S04's automated coregistration has a somewhat larger residual rotation
  (-16.7° pitch) than the other 15 subjects (single digits to low 20s) --
  with only LPA/RPA reliably usable for fitting (see below), this was the
  one subject where that wasn't quite enough for a tight fit.
  `mne.make_forward_solution`'s own `on_inside='warn'` was needed to get
  past 27/306 MEG sensors landing just inside the BEM surface for this
  subject specifically; contributes to the 16-subject group average like
  everyone else, just with a somewhat noisier per-subject estimate.

See `../original_scripts/GLITCHES.md` for the full methodology writeup —
notably its "Source-space onboarding", "Watershed BEM neck/defacing
investigation", "Figures 11/12: two more real bugs", and "Coregistration
was systematically wrong dataset-wide" sections — and `../figures/README.md`
for why this directory exists separately from `../figures/`.
