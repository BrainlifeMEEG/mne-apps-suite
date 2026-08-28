# Figure naming — read this before adding another `fig*` file here

**This directory now holds only this project's own diagnostics — not paper
figures.** All literal Jas et al. 2018 reproductions (Figures 1–7,
including what used to be `fig1_maxfilter_comparison.py`/`fig2_psd.py`/
`fig3_filter_response.py`) have moved to `../figures_jas/`, prefixed
`jas_fig<N>_...`. See `../figures_jas/README.md`.

What's left here:

- `fig5_diagnostics.py`, `fig5_pipeline.py`, `fig5_ica_inspect.py`, and the
  `fig5_S09_*` control figures — this project's own Phase-5 (bad
  channels/ICA/epoching) pipeline-validation diagnostics, informally
  numbered by our own pipeline phase. **Not** "Jas Figure 5" — Jas's actual
  Figure 5 (grand-average evoked) is `../figures_jas/jas_fig5_grand_average.py`.
  This naming collision caused real confusion mid-project (see
  `../original_scripts/GLITCHES.md`'s Phase 7 section) — the split below
  exists specifically to prevent it recurring.
- `fig_chpi_diagnostic.py` + `diagnostic_chpi_vs_bandpass.png` +
  `diagnostic_raw_segment.png` — also not a paper figure (says so in its
  own docstring): an isolated look at what chpi filtering vs. bandpass
  filtering each do to raw data on their own.

Going forward:

- **This project's own diagnostics** (not tied to a specific paper figure
  number) stay in this directory, named after our own pipeline phase —
  `fig<phase>_<description>.py`.
- **Literal paper-figure reproductions** for Jas et al. 2018 go in
  `../figures_jas/`, prefixed `jas_fig<N>_...`.
- The original Wakeman & Henson (2015) data-descriptor paper has never been
  targeted by this project at all (different toolchain, SPM vs. MNE) — if
  you're looking for W&H's own figures, they don't exist here.
