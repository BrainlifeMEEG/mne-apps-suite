# Strategy — Wakeman & Henson (ds000117) reproduction on Brainlife.io

Phase 0 deliverable for the brief in `Claude prompt repro Wakeman.md`. Scope: map the
target pipeline (mne-biomag-group-demo / Frontiers 2018) onto this repo's Brainlife Apps,
flag what needs fixing or building, and list open questions — before anything runs.

## Status

- **Data**: confirmed already staged in the target project (`brainlife.io/project/5df7efdc32bff02262e226b6`) — raw MEG (`task-facerecognition`, `run-##`), MaxFilter derivatives (`proc-sss`, `run-##`), T1 (`acq-mprage`). Ready for Phase 1.
- **Source-space work (Figs 8–12)**: deferred. The `obVdo` apps this needs aren't in this repo yet, and you're contacting the developer directly before that work starts. Not analyzed further below.
- **Phase 1 (fif2mne) and Phase 2 (maxwell-filter, Fig 1 A/B)**: done for S10 run02, see `run_pipeline.py` and `figures/fig1_maxfilter_comparison.py`. Along the way: fixed a real `maxwell-filter` bug (`head_pos` fed the wrong file type), fixed a real `bl-app-run-instanced.js` crash (in [[project-brainlifepipelinecli]] terms, `BrainlifePipelineCLI`), and found that `mne.chpi.filter_chpi()` is a required step before `maxwell_filter()` that neither our app nor a naive script call includes by default — see open questions.
- **Raw upload data gap**: this project's raw MEG datasets have no `calibration`/`crosstalk`/`channels` sidecar files attached (all resolve to nonexistent paths) — only `events.tsv`/`headshape.pos`/`coordsystem.json` came through. Calibration/crosstalk turned out to matter less than feared for Fig 1 (see below), but this is still worth fixing via the maintainer conversation already in progress.

## Figure-by-figure roadmap

Cross-referenced against the actual mne-biomag-group-demo script order and the Frontiers 2018 paper's figure captions (both fetched directly) — the brief's figure numbers line up with the paper almost exactly.

| Figure | Content | Target script | Brainlife App(s) | Status |
|---|---|---|---|---|
| — (read data) | — | `02-extract_events.py` | `fif2mne` | ✅ exists |
| 1 A/B | raw vs. SSS vs. MaxFilter comparison | `03-maxwell_filtering.py` | `maxwell-filter` | ✅ **done for S10 run02** — `figures/fig1_maxfilter_comparison.py`. Needed a local (non-app) SSS run with `mne.chpi.filter_chpi()` applied first; the brainlife.io app itself doesn't do this yet (open question below) |
| 2 | PSD, subject 10 run 02 | (pre-ICA QC) | `psd` / `epoch-psd` | 🛑 **broken** — both call `psd_welch`/`psd_multitaper`/`plot_psd`, all removed from current MNE-Python. Must be fixed before this figure can be produced. |
| 3 | filter frequency/impulse response, MNE 1.12 | `04-python_filtering.py` | `filter-raw` | ✅ exists for the filtering itself; the response-curve figure is a custom plot pulling filter coefficients, not an App report — build it as a local script |
| — (bad seg/chan, ICA, epoching) | new diagnostic figures, open-ended | `05-run_ica.py`, `06-make_epochs.py` | `mark-bad-raw`, `ICA-fit`, `ICA-apply`, `epoch`, `drop-bad-epo` | ✅ exist. ⚠️ `ICA-plot`/`ICA-fit`'s `main` bash script overwrites the correct `product.json` with a stale base64 heredoc (known bug) — fix opportunistically when we're at this step, not blocking |
| 4 | fanning artifact: baseline-only vs. 1Hz-HP vs. tSSS, subject 3 | `07-make_evoked.py` | `apply-baseline` | ✅ exists; figure needs a local script pulling 3 differently-processed branches together side by side |
| 5 | evoked response, subject 3 then all subjects | `07-make_evoked.py`, `11-group_average_sensors.py` | `average-erp` / `evoked-averaged` | ✅ exist for within-subject averaging. No app grand-averages Evoked across subjects yet — needed for the "all subjects" pass of this figure |
| 6, 7 | sensor cluster stats + decoding curve; spatiotemporal cluster | `11-group_average_sensors.py` | — | ❌ no app exists for evoked contrasts or cluster-permutation stats anywhere in the repo |
| decoding figure | sliding-window logistic regression, ROC-AUC | `10-sliding_estimator.py` | — | ❌ no app exists. Fig 6B already contains a decoding curve — worth checking whether the brief's separate "decoding figure" step is meant to extend that or is redundant, once we're there |
| 8–12 | BEM, coreg, whitening, group source, source stats | `01-anatomy.py`, `08-make_cov.py`, `12`–`16` | `obVdo`'s apps (not cloned) | **Deferred**, see Status above |

## Known app bugs relevant to this pass

- `psd` / `epoch-psd` — deprecated MNE API calls (`psd_welch`/`psd_multitaper`/`plot_psd`, all removed from current MNE-Python). **Blocks Figure 2 directly.**
- `ICA-plot` / `ICA-fit` — `main` bash script clobbers a correctly-built `product.json` with a stale base64 heredoc. Cosmetic (affects Phase 5 diagnostics reports only); fix when we reach that phase.
- `average-erp`'s earlier config-key mismatch (`average-all` vs `average_all`) — already fixed, confirmed via `REMEDIATION_SUMMARY.md`. No action needed.
- `filter-epo` — not analyzed this pass; not on the critical path we're planning right now.

## Recommendation: local scripts first, promote to Apps later

For everything that doesn't have an app yet (the figure-recreation scripts, and eventually grand-averaging/contrast-stats/decoding), develop as **local Python scripts running inside the same `brainlifemeeg/mne:1.12.1` Docker image** apps run in, and only promote a stage to a compliant Brainlife App once its logic is validated and stable.

- The Docker image is already identical to what a real App would run in, so porting later is cheap — wrap already-working logic in `main.py`'s boilerplate (`load_config`, output-dir creation, `product.json` accumulator), not a rewrite.
- mne-biomag-group-demo itself is a set of plain scripts, not packaged apps — validating step-by-step against it is easier working the same way, especially for figures 2–7, which are exploratory comparison plots (e.g. Fig 4's 3-way baseline/highpass/tSSS comparison) pulling multiple branches together — awkward to force into a single App's one-shot input→output shape on a first attempt.
- Platform round-trips (task queueing, documented Amaretti archiving flakiness, `bl app wait` unreliability) add friction better avoided while a stage's logic is still being worked out.

## Reusable tooling

A new standalone tool, `local_scripts/BrainlifePipelineCLI/` (its own git repo, committed), now holds the generic engine extracted from `local_scripts/ReproduceProject/`'s prior (unrelated) reproduction work: retry/checkpointed app-run chaining (`PipelineRunner`), the tolerant `bl` JSON parser, and the Pipeline-tab rule-management library — all project-agnostic. A Wakeman-specific driver script (app ids, subject list, per-app configs) will be written against this package when Phase 1 execution starts, following the pattern in `BrainlifePipelineCLI/examples/example_driver.py`.

## Open questions

1. Fig 6B already contains a decoding curve — is the brief's separate "decoding figure" phase meant to extend that, or produce something distinct?
2. Grand-averaging across subjects (needed starting at Fig 5's "all subjects" pass) — local script first per the recommendation above, confirm before Phase 7.
3. Source-space apps (`obVdo`) — on hold pending your contact with the developer; revisit scope once that's resolved.
4. Should `maxwell-filter` (the app) be hardened to call `mne.chpi.filter_chpi()` internally before `maxwell_filter()`? Real, reproducible gap found while building Fig 1 — without it, magnetometer output is dominated by a ~7 Hz cHPI beat-frequency artifact (~20x noisier than Elekta's reference `proc-sss`, no visible evoked peak). Not yet fixed in the app itself; Fig 1 used a local script instead.

## Next step

Phase 3 per the brief: compute PSD, recreate Figure 2 for subject 10 run 02 — blocked on fixing `psd`/`epoch-psd`'s deprecated MNE API calls first (see status table above).
