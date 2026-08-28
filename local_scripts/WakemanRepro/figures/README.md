# Figure naming — read this before adding another `fig*` file here

This directory's `fig1_maxfilter_comparison.py`, `fig2_psd.py`, and
`fig3_filter_response.py` **are** literal reproductions of **Jas et al. 2018**
("A Reproducible MEG/EEG Group Study With the MNE Software", Frontiers in
Neuroscience) Figures 1–3 — confirmed against the paper's actual figure list.

`fig5_diagnostics.py`, `fig5_pipeline.py`, and `fig5_ica_inspect.py` are
**not** "Jas Figure 5" — they're this project's own Phase-5 (bad
channels/ICA/epoching) pipeline-validation diagnostics, informally numbered
by our own pipeline phase, not the paper's figure numbering. Jas's actual
Figure 5 (grand-average evoked) lives in `../figures_jas/jas_fig5_grand_average.py`.

This numbering collision caused real confusion mid-project (see
`../original_scripts/GLITCHES.md`'s Phase 7 section). To avoid repeating it:

- **This project's own diagnostics** (not tied to a specific paper figure
  number) stay in this directory, named after our own pipeline phase —
  `fig<phase>_<description>.py`.
- **Literal paper-figure reproductions** for Jas et al. 2018 go in
  `../figures_jas/`, prefixed `jas_fig<N>_...` — e.g. `jas_fig4_tsss_analysis.py`,
  `jas_fig6a_sensor_cluster_stats.py` — so a paper figure number can never be
  misread as this project's own phase numbering, or vice versa.
- The original Wakeman & Henson (2015) data-descriptor paper has never been
  targeted by this project at all (different toolchain, SPM vs. MNE) — if
  you're looking for W&H's own figures, they don't exist here.
