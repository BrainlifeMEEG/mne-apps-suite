# Original-scripts audit (Step 0)

Read-through + targeted empirical checks against our installed environment (MNE 1.12.1, this
project's `.venv`). No script has been executed yet — this is the pre-flight report per the plan
at `~/.claude/plans/jazzy-swinging-whistle.md`.

## Summary table (blocking severity)

| script | severity | issue |
|---|---|---|
| `08-make_cov.py` | **fixed** (2026-08-28) | `KFold(3, random_state=random_state)` raised `ValueError` under current sklearn without `shuffle=True`. Fixed in place: `KFold(3, shuffle=True, random_state=random_state)`. Verified deterministic (same `random_state` → same splits twice). |
| `10-sliding_estimator.py` | **fixed** (2026-08-28) | Same sklearn issue, `StratifiedKFold`. Fixed in place: `StratifiedKFold(shuffle=True, random_state=random_state)`. Verified deterministic. |
| `14-group_average_source.py` | **confirmed-broken** | `mne.compute_morph_matrix` — removed from current MNE (`hasattr(mne, ...)` is `False`); replaced long ago by `mne.compute_source_morph` |
| `16-group_average_lcmv.py` | **confirmed-broken** | same `compute_morph_matrix` removal |
| `03-maxwell_filtering.py` | not blocking for main pipeline | only called for subject 3 (`run_maxwell_filter(subject_id=3)`), feeds Figure 4 specifically — see pivot note below |
| `99-make_reports.py` | **worth-testing / likely broken** | needs `mayavi` (not installed) for 3D brain plots; also uses old `Report.add_figs_to_section`/`_add_figs_to_section` API — check against current `mne.Report` |
| `12-`, `13-make_forward/inverse.py` | out of scope for now | need `subject-trans.fif` (coregistration) and 3-layer BEM, not yet built — source-space, already deferred project-wide |
| `01-anatomy.py` | worth-testing, not urgent | needs `recon-all`/`FREESURFER_HOME`; we already have precomputed FreeSurfer output locally (`ds000117/derivatives/freesurfer/sub-09`), so this script likely doesn't need to *run* for subjects already reconstructed — worth confirming its `if op.isdir(subject_dir): skip` early-exit is reached before anything recon-all-specific runs |
| `05-run_ica.py` | **confirmed-broken, workaround verified (chained on `04`'s default config)** | hardcodes `highpass-1Hz` as its raw-data input filename (`'... % (run, 1)'`, literal `1`, not `l_freq`) — but `04-python_filtering.py` names its output after the *config's* `l_freq` (`None` by default → `highpass-NoneHz`). With the shipped `l_freq = None` default, `04`'s one output pass can never satisfy `05`'s hardcoded expectation. **Workaround confirmed to work** (see below): run `04` twice for a given subject — once with config's own `l_freq` (feeds `06`'s epoching), once with `l_freq` patched to `1` (feeds `05`'s ICA fit) — no logic changes to either script, just running `04` under two config states, which is apparently what the original authors did but never documented. |
| everything else (`00`, `02`, `04`, `06`, `07`, `09`, `11`) | looks-fine | imports/API confirmed working; only path adaptation needed (see below) |

## Already checked empirically (don't re-flag these as issues — they looked suspect but aren't)

- `mne.parallel.parallel_func` — works.
- `mne.bem.convert_flash_mris`, `mne.bem.make_flash_bem` — both work.
- `distutils.version.LooseVersion` — still imports and works in this environment (not actually
  removed here despite being deprecated upstream).
- `autoreject` (0.4.4) and `nibabel` (5.4.2) — both installed.

## Exact path/filename requirements per script (feeds the symlink farm)

All scripts index subjects as `subject = "sub%03d" % subject_id` (**openfMRI's own 1-19
numbering** — not W&H names, not BIDS `sub-NN`; see crosswalk table in the plan). Two path roots:
`study_path/ds117/sub%03d/...` (raw input, openfMRI's own tarball layout per `00-fetch_data.py`)
and `meg_dir = study_path/MEG/sub%03d/...` (all pipeline outputs, self-contained once running).

| script | reads | writes |
|---|---|---|
| `00-fetch_data.py` | openfMRI tarballs (network) | `study_path/ds117/sub%03d/`, creates `meg_dir`, `subjects_dir` |
| `01-anatomy.py` | `ds117/sub%03d/anatomy/highres001.nii.gz`, `.../anatomy/FLASH/meflash*` | `subjects_dir/sub%03d/` (FreeSurfer output) |
| `02-extract_events.py` | `ds117/sub%03d/MEG/run_%02d_raw.fif` | `meg_dir/sub%03d/run_%02d-eve.fif` |
| `03-maxwell_filtering.py` (subject 3 only) | `ds117/sub%03d/MEG/run_%02d_raw.fif`, `run_%02d_sss.fif`, `run_%02d_sss_log.txt` | `meg_dir/sub%03d/run_%02d_filt_tsss_{10,1}_raw.fif` |
| `04-python_filtering.py` | **`ds117/sub%03d/MEG/run_%02d_sss.fif`** (Elekta's proc-sss, = our `elekta_maxfilter_meg.fif`) | `meg_dir/sub%03d/run_%02d_filt_sss_highpass-%sHz_raw.fif` |
| `05-run_ica.py` | `meg_dir/sub%03d/run_%02d_filt_sss_highpass-%sHz_raw.fif` (all 6, concatenated) | `meg_dir/sub%03d/run_concat-ica.fif` |
| `06-make_epochs.py` | same filt files + `bads/<W&H name>/run_%02d_raw_tr.fif_bad` (script repo, via `map_subjects`) + the ICA file | `meg_dir/sub%03d/sub%03d_highpass-%sHz-epo.fif` |
| `07`–`10`, `12`, `13`, `15` | `meg_dir/sub%03d/...` outputs of prior steps only | further `meg_dir/sub%03d/...` outputs |
| `11`, `14`, `16` | `meg_dir/sub%03d/...` across all non-excluded subjects | `meg_dir/grand_average...` |

**Only `04-python_filtering.py` (and `03`, subject-3-only) touch the raw/proc-sss input tree at
all.** Everything from `05` onward is self-contained within `meg_dir`, which we build ourselves —
meaning the symlink farm only strictly needs to bridge `ds117/sub%03d/MEG/run_%02d_sss.fif` (from
our local `ds000117/derivatives/meg_derivatives/sub-09/.../*_proc-sss_meg.fif`) for the main
pipeline. `run_%02d_raw.fif` and `run_%02d_sss_log.txt` are only needed if we run `03` for subject
3 (Figure 4) — worth bridging too, but not blocking for the S09 main-pipeline path.

## Mid-audit pivot (see plan for full detail)

Reading `03` and `04` directly overturned an assumption from Phase 5 v2 (`fig5_pipeline.py`): the
official *main* pipeline (all subjects) never recomputes Maxwell filtering — it uses Elekta's
deposited proc-sss file as-is. `03`'s from-scratch tSSS+movecomp recompute (with bad channels
parsed from `run_%02d_sss_log.txt` — confirms the log-parsing mechanism used to find MEG1111) is
called only for subject 3, feeding Figure 4's 3-way comparison. Decision (confirmed with the
user): default to Elekta's files for the main pipeline; keep `fig5_pipeline.py`'s recompute as an
explicit future comparison branch, not the main line.

## Symlink farm built and verified (0c)

Built at `derivatives/biomag_repro/` for S09 (openfMRI `sub010`): `ds117/sub010/MEG/run_0N_{raw,sss,sss_log.txt}`
bridged to the local BIDS `ds000117` raw + proc-sss + MaxFilter-log files, `subjects/sub010`
bridged to the FreeSurfer output. Verified, not assumed:
- `run_02_sss.fif` opens correctly through the symlink with the exact call
  `04-python_filtering.py` itself uses (`mne.io.read_raw_fif(raw_in, preload=True,
  verbose='error')`, no `allow_maxshield` needed) — 404 channels, 1100 Hz, as expected.
  `raw.filenames` reports the symlink path, not the original BIDS path — confirms MNE doesn't
  depend on the original filename internally, per the metadata-content concern raised for 0c.
- **Caught and fixed a real structural bug**: `derivatives/freesurfer/sub-09/` is not itself a
  flat FreeSurfer `SUBJECTS_DIR` entry — the actual `mri/`/`surf/`/`label/` output is nested one
  level deeper, under `sub-09/ses-mri/anat/`. First symlink attempt pointed at the wrong level
  (`ln -sf` also silently failed to overwrite it on the first retry — needed an explicit `rm` then
  `ln -s`, worth remembering for any further symlink work). Now correctly resolves to `mri/surf/label`
  directly.

## Step 0 chain test: `04` + `05` run verbatim against S09 (2026-08-27)

Beyond static reading, actually ran the unmodified `run_filter()`/`run_ica()` function bodies
(module-level batch drivers over all 19 subjects stripped via AST, not edited — see harness
scripts, not committed) against the symlink farm, restricted to subject_id=10 (our S09):

- **`04-python_filtering.py`**, `l_freq=None` (config default): all 6 runs processed cleanly,
  404 channels/1100 Hz preserved, EOG/ECG retyping and renaming worked, output opens correctly.
  Only warning: benign `EEG064 unit V→NA` (expected — that channel is deliberately retyped to
  `misc`). `raw.info['bads']` on output is empty — confirms `04` never touches bad channels at
  all; the *only* place bad channels enter the official pipeline is `06-make_epochs.py`, sourced
  exclusively from the script repo's own `bads/<W&H name>/run_NN_raw_tr.fif_bad` files (never from
  Elekta's MaxFilter logs, never re-derived from data) — worth remembering when we get to fixing
  our own bad-channel list.
- **`04` again, `l_freq` patched to `1`** (the workaround above): also ran cleanly, produced the
  `highpass-1Hz` files `05` needs.
- **`05-run_ica.py`**: first attempt OOM-crashed the machine (31GB total, shared desktop session
  already using ~14GB) during `ica.fit()`'s internal data extraction — `mne.concatenate_raws()`
  itself stayed lazy (non-preloaded raws), but `ica.fit(raw, picks=picks_meg, decim=11)` pulls the
  full-rate MEG-channel data before decimating internally. Retried under a memory-guarded wrapper
  (background process + a watchdog polling `/proc/meminfo` every 2s, hard-kills before the OS OOM
  killer could touch unrelated desktop processes). **Succeeded** on retry: peak RSS **9.96 GB**,
  fastica fit took **183.9 s**, selected **69 components** (99.9% variance) — consistent with
  SSS's known rank reduction (~306 raw MEG channels → typically 64-80 effective rank after
  Maxwell filtering). Saved to `run_concat-ica.fif`. **Any future run of `05` (or `06`, likely
  heavier) on this machine should go through the same memory-guarded pattern**, not a bare
  foreground call — this box does not have headroom to spare.
- **Bonus finding, ties into open question #7 (incomplete bad-channel list)**: `05`'s own
  `reject=dict(grad=4000e-13, mag=4e-12)` amplitude-based segment rejection (applied during ICA
  fitting, independent of any bad-channel marking — recall `raw.info['bads']` is empty at this
  point since `04` never sets it) repeatedly flagged **MEG1111, MEG1611, MEG2032, MEG1131,
  MEG1141, MEG1631** among others across the rejected segments — several of which are *exactly*
  the channels Elekta's own MaxFilter log-parsed autobad list identified for this subject (see
  Recap in the plan / project memory). This is independent, primary-source confirmation — from
  the literal, unmodified official pipeline's own artifact rejection, not from our own detection
  code — that these channels are genuinely problematic even when never explicitly marked bad.
  Strengthens the case for fixing `fig5_diagnostics.py`'s bad-channel list before trusting its
  result.

## Step 0 chain test, continued: `02` and `06` (2026-08-27, same session)

- **`02-extract_events.py` first attempt failed on a data-availability gap, not a script or
  symlink-farm bug**: `ds000117` is a git-annex/datalad checkout — the symlink farm's targets
  were themselves broken (`readlink -f` resolved to nothing) because **only the derivatives
  (proc-sss files + logs) had ever been fetched from the S3 remote for this dataset; the raw
  (`_meg.fif`) file content was never pulled** (`git annex find` on the raw MEG dir returned
  nothing). Fixed with `git annex get sub-09/ses-meg/meg/ --from=s3-PUBLIC` (5.18 GB, all 6 runs +
  headshape). Worth remembering for any other subject we bring into this farm later: check
  `git annex find <path>` before assuming a symlinked file is actually readable, not just that the
  symlink exists.
  - **Caught a background-task tracking gap of our own**: the first fetch attempt was launched as
    `nohup ... & ; echo pid` *inside* an already-backgrounded shell call — the outer wrapper
    returned (and was reported "completed") as soon as the `echo` ran, while the actual
    `git-annex get` continued running detached/unmonitored. Confirmed still genuinely alive via
    `ps`/`pgrep` and let it finish; fixed for the retry by monitoring the real child process
    directly rather than a detached wrapper.
  - Once fetched, `02` ran cleanly for all 6 runs: 149/147/147/147/147/147 events found, all 9
    expected event IDs present each run.
- **`06-make_epochs.py`**: ran cleanly to completion once its inputs existed (highpass-NoneHz raw
  files, `run_%02d-eve.fif`, `run_concat-ica.fif`, plus `bads/subject_12/run_NN_raw_tr.fif_bad`,
  already present from 0a). Peak RSS **20.82 GB** — meaningfully higher than `05`'s 9.96 GB (all 6
  runs are `preload=True`'d immediately here, vs. `05`'s lazy loads, plus ECG/EOG epoch creation
  and `autoreject`'s rejection-threshold search stack on top before `del raw` frees the big array).
  Ran under the same memory-guarded wrapper; available memory dipped to a low of ~8 GB at the
  concatenation peak but never approached the kill threshold. **517/885 epochs kept (41.6%
  dropped)**, 381 channels, 220 Hz (decim=5, as configured), event counts spread across all 9
  conditions as expected. Output verified by re-opening the saved epochs file directly, not just
  trusting a clean exit code. Most rejected epochs were flagged on EEG004/EEG008/EEG002/EEG005 or
  EOG062 specifically — consistent with (not necessarily explained by) the per-run EEG bad-channel
  interpolation this script already does via the `bads/` files; not investigated further, noted
  as an observation only.
- **Chain now fully validated end-to-end for S09**: `02` → `04` (×2, default + `l_freq=1`) → `05`
  → `06`, verbatim script logic throughout, real data, real ICA solution, real epochs on disk at
  `derivatives/biomag_repro/MEG/sub010/`.

## Cluster smoke test (2026-08-27): rerun-idempotency gap, not a pipeline bug

First `sbatch --array=10` attempt (see `cluster/`) failed on `02-extract_events.py`'s
`mne.write_events(fname_events, events)` with `FileExistsError` -- because that exact output
already existed on the shared farm from the interactive S09 test earlier this session, and
current MNE's `write_events()` defaults to refusing to overwrite. Checked every write/save call
across `02`/`04`/`05`/`06`: **only `04`'s `raw.save(raw_out, overwrite=True)` passes `overwrite`
explicitly** -- `02`'s `write_events`, `05`'s and `06`'s `ica.save()`, and `06`'s
`epochs.save()`/`Evoked.save()` (via `.average().save()`) all lack it, so every one of them will
raise the same way on any rerun against outputs that already exist. This is a real API-default
change since the scripts were written (matches the project's existing pattern of "the demo repo
predates a since-changed MNE default"), not a bug in the reproduction itself -- and not something
to "fix" by adding `overwrite=True` to the original scripts (that would be a logic change, out of
bounds for `original_scripts/`). Fixed instead in our own tooling: `cluster/run_subject_chain.py`
clears a subject's own `meg_dir/sub%03d/` output directory before each run -- that directory is
entirely our generated output, never original/downloaded data, so clearing it is safe and makes
every run behave like a genuine first run.

## Crosswalk cross-check (0d) attempted, result: inconclusive (2026-08-28)

Built `crosswalk_crosscheck.py`: an automated per-channel outlier score (log-variance,
robust z-score with both per-channel and per-run normalization removed -- see the script's
own docstring for the two dead ends tried first) compared against W&H's own
`bads/<name>/run_NN_raw_tr.fif_bad` files, per the plan's Stage 1 (count)/Stage 2 (name overlap)
strategy. Calibrated the threshold against S09's known ground truth (run02: exactly 7 channels
matching the paper's Figure 2) before trusting it on anything else -- and that calibration itself
is the reason to distrust the result: **tuned against S09's run02 specifically, the same detector
gets 0-1/5 channel overlap on S09's OWN runs 03-06** (run04: 0/4, run05: 0/3, run06: 0/2). It
doesn't generalize even within the one subject it was calibrated on, let alone across the other 15.
Ran it across all 16 subjects anyway for completeness (results saved to
`crosswalk_crosscheck_results.json`) -- the output is almost entirely `overlap=0` everywhere,
including subjects/runs where W&H found several bad channels and the detector found a similar
*count* of completely *different* channels.

**Conclusion: this Stage 1/2 attempt does not provide usable evidence for or against the crosswalk
mapping for any subject.** A simple per-channel variance z-score, however normalized, isn't a good
enough proxy for manual bad-channel curation (which presumably also weighs neighbor correlation,
high-frequency noise character, and visual inspection of raw traces -- more like PREP's multi-criteria
approach than a single variance metric). Per the plan's own explicit fallback: **the 15 non-S09
subjects remain unverified, flagged here rather than quietly treated as confirmed.** S09 stays the
only subject verified against genuine ground truth (the paper's own published Figure 2). A real
cross-check would need a materially better bad-channel detector, not a threshold retune of this one.

## Cluster infra: transient NFS config-lock race under high array concurrency (2026-08-28)

First full-array submission of the extended (`02→...→10`) chain, 16 tasks launched simultaneously,
had one task (subject 3) fail immediately: `OSError: [Errno 116] Stale file handle` inside MNE's
own `get_config()` -- every task imports `mne` at startup, which reads/file-locks a shared config
file under `$HOME/.mne/mne-python.json` on first import. With 16 array tasks starting at nearly the
same instant on a network filesystem, one lost a lock-acquisition race against a stale NFS file
handle. **Not a bug in this project's code or original_scripts** -- purely an artifact of many
parallel MNE processes sharing one config file over NFS. Transient: resubmitting just the failed
task succeeded immediately (the race window had passed). Worth remembering for future large
arrays: expect an occasional isolated task to fail this way at high concurrency; check `sacct` for
`FAILED` after any big array submission and resubmit just those indices rather than assuming a
real bug. (A more permanent fix, not applied here since a one-off resubmit was sufficient: export
`MNE_LOGGING_LEVEL` as an env var in the Slurm script, which lets `mne.set_log_level` skip the
config-file read/lock entirely.)

## Phase 7 figure scripts: three more confirmed API breaks (2026-08-28)

Found while actually running the adapted `figures_jas/` scripts against real 16-subject data (not
just reading source) -- each confirmed via `inspect.signature`/docstring before fixing, not
assumed:
- `mne.viz.plot_compare_evokeds`'s `show_sensors=<int>` (a matplotlib legend-location code, e.g.
  `4` for 'lower right') raises `TypeError` at runtime in this MNE version despite `int` being
  listed as valid in the function's own docstring -- a genuine docstring/implementation mismatch.
  Fixed by passing the equivalent string (`'lower right'`) instead. Affects Fig 6A.
- `mne.stats.permutation_cluster_1samp_test`'s `out_type` default changed from `'mask'` (clusters
  as `slice` objects, for 1D data with no adjacency) to `'indices'` (clusters as index ndarrays).
  Code written against the old default that does `cluster.start`/`cluster.stop` breaks; fixed with
  `cluster.min()`/`cluster.max()` on the index array instead. Affects Fig 6A (Fig 7 already
  requested `out_type='indices'` explicitly, so was unaffected).
- `mne.viz.plot_topomap`'s `vmin=`/`vmax=` kwargs no longer exist, merged into a single
  `vlim=(vmin, vmax)` tuple. Affects Fig 7.

All three figures produce genuinely convincing, primary-source-verified results after fixing (not
just "runs without error") -- Fig 6A finds 2 significant temporal clusters (p=0.001 both) matching
the paper's own reported finding; Fig 7 finds 1 significant spatiotemporal cluster (p<0.001) over a
posterior-right sensor cluster, 140-800ms, consistent with the paper's "right ventral visual
cortex" description at the sensor level.

## Subject-3 tSSS branch: same overwrite gap, but wider (2026-08-28)

Extending the "Cluster smoke test" overwrite-gap finding above: it's not just `ICA.save()`.
Confirmed via `inspect.signature` that `mne.preprocessing.ICA.save()`, `mne.Evoked.save()`, and
`mne.Epochs.save()` **all** default to `overwrite=False` in current MNE, and `06-make_epochs.py`
calls all three. Two distinct failure modes hit in practice while running subject 3's tSSS branch:
- `06`'s `tsss` branch sets `ica_name = ica_out_name` (the SAME path, read then overwritten within
  one execution, by the script's own design) -- so `ica.save()` fails on the **first ever run**,
  not just reruns.
- `06` writes several files progressively before its final `epochs.save()` (ecg-ave.fif,
  eog-ave.fif, the ICA solution, ...) -- a failure partway through (like the one above) leaves
  real, legitimately-already-written files behind that the *next* attempt's earlier lines
  (`ecg_epochs.average().save(...)` etc.) then collide with, even though nothing is "stale" in the
  sense of being wrong content -- it's just an earlier successful write from the same logical run.

Fixed in `cluster/run_subject3_extra.py` via process-scoped monkeypatches of all three
(`ICA.save`, `Evoked.save`, `Epochs.save`, each forcing `overwrite=True`), not edits to
`original_scripts/`. Also added a skip-if-already-done guard around `03-maxwell_filtering.py`'s
call (itself internally idempotent -- its own `raw.save()` already passes `overwrite=True` -- but
takes ~50 minutes for one subject, not worth blindly recomputing on every retry).

## Figure comparison follow-up fixes (2026-08-28)

User review of `figures_jas/jas_figures_comparison.pdf` turned up three more issues, all now fixed:

- **Fig 7's topomap had every electrode clustered in one corner.** Root cause:
  `pos = mne.find_layout(contrast.info).pos` -- a `Layout`'s `.pos` is a legacy `(x, y, width,
  height)` 2D grid-box array for the old flat layout view, not head-normalized sensor coordinates.
  Using its first two columns as topomap `x`/`y` collapses real sensor geometry into a small
  clustered region. Fixed by passing `contrast.info` directly as `pos` to `plot_topomap()` --
  confirmed via that function's own docstring that it accepts an `Info` object directly (inferring
  proper positions from the montage) when it has exactly one channel type and `len(data)` channels,
  both true here. Verified visually after the fix: proper head outline, electrodes spread over a
  central-frontal region, matching the published figure.
- **Fig 5 was missing panel B** (grand-average evoked under `l_freq=1`, vs. panel A's
  `l_freq=None`) -- not a bug, a real scope gap from the earlier clean-up commit. `jas_fig5_grand_average.py`
  already parametrizes entirely off `config.l_freq` (input/output filenames, panel-letter
  annotation) -- it just needed a `l_freq=1` run, which needed `06`+`07` output for all 16 subjects
  under `l_freq=1` first (only subject 3 had this, from the tSSS branch work). Key insight that
  avoided a full pipeline rerun: `06`'s ICA *read* path (`ica_name = 'run_concat-ica.fif'`) doesn't
  depend on `l_freq` at all -- only `ica_out_name`, the exclusion-annotated copy it writes back out,
  does. So the `l_freq=None` ICA solution (already fit once per subject) is reused as-is; only
  `06`+`07` needed rerunning, not `03`/`04`/`05`. Built as a 16-subject Slurm array
  (`cluster/run_subject_lfreq1_epochs.py` + `cluster/submit_lfreq1_epochs.slurm.sh`), then
  `cluster/build_fig5_panel_b.py` (11's group-average, `l_freq=1`, + `jas_fig5_grand_average.py`,
  `l_freq=1`) once all 16 completed. Found a **fourth** overwrite-gap variant while running this:
  `07-make_evoked.py` calls the **module-level** `mne.evoked.write_evokeds()` function directly
  (not an `Evoked` instance's `.save()`) -- a different call path than the three already known
  (`ICA.save`, `Evoked.save`, `Epochs.save`); not covered by those monkeypatches, needed its own.
  Hit for real on subject 3, who already had this exact output file from the earlier tSSS-branch
  work (a genuine, expected collision on rerun, not a bug). Two subjects (6, 14) also hit the
  already-documented transient NFS config-lock race on the first array submission -- resolved by
  resubmitting just those indices, same as before.
- **Fig 4's topomap insets were cluttered by an unwanted legend.** Rewrote to use
  `Evoked.plot_joint(times=[0, 0.12, 0.4, 2.8], picks='mag', ...)` instead of a manual per-panel
  `plot()` call -- `plot_joint()` draws topomap insets at specified times connected by lines to the
  butterfly trace, matching the published figure's actual layout, and the four times match its own
  labels. `plot_joint()`'s butterfly panel defaults to `spatial_colors=True` (matches the paper's
  own colored traces, kept), but that also draws a small inset `Axes` -- confirmed via `fig.axes`
  inspection to be an `AxesHostAxes` (from `mpl_toolkits.axes_grid1`) nested inside the main
  butterfly axes' bounding box -- showing a sensor-position color-legend circle, not wanted. No
  `plot()`/`plot_joint()` kwarg suppresses just that inset while keeping colored traces (checked the
  docstring); removed by finding it by class name (`type(ax).__name__ == "AxesHostAxes"`) and
  calling `fig.delaxes()` on it, after the figure is built.

## Figure comparison, round 2: topomap projection was genuinely wrong (2026-08-28)

User review of the round-1 fixes above found Fig 4's and Fig 7's topomaps still didn't match the
published figures: Fig 4's magnetometer topographies spread much wider than the paper's (electrodes
spilling well past the drawn head-outline circle); Fig 7's electrode grid sat too high/off-center
relative to the head outline. Root cause, confirmed empirically (via MNE's own private
`_check_sphere`/`_find_topomap_coords` helpers, not guessed) and shared by both:

`plot_topomap`'s (and `plot_joint`'s `topomap_args`'s) `sphere=None` default auto-fits a sphere to
the subject's own head-shape digitization points. For this dataset that fit is genuinely off-center
-- `mne.bem.fit_sphere_to_headshape` itself raises `RuntimeWarning: (X, Y) fit (1.0, 29.0) more than
20 mm from head frame origin` at runtime, i.e. MNE is telling us the fit is bad. That skew visibly
distorted both figures' projections (confirmed by rendering `sphere=None` vs. a fixed sphere side by
side: the fixed version centers the electrode/sensor grid properly, matching the paper far more
closely).

Fixed with an explicit fixed sphere instead of relying on the auto-fit, for both figures:
- **Fig 7 (EEG)**: `sphere=(0, 0, 0, 0.095)` -- this is MNE's own documented fallback value (see
  `plot_topomap`'s `sphere` docstring: "`None` ... is equivalent to `(0, 0, 0, 0.095)`" when no good
  digitization fit is available), not an arbitrary number. Confirmed visually: ears line up at a
  normal height, electrodes spread evenly, matching the published figure closely.
- **Fig 4 (MEG magnetometers)**: same fixed origin, but the *radius* also needed to grow from that
  0.095 fallback to 0.19. Confirmed empirically that `_find_topomap_coords`'s projected 2D sensor
  positions have a radius-INDEPENDENT extent for this dataset (~0.171 m max, regardless of what
  sphere radius is passed) -- only the sphere's *origin* affects where channels land; radius only
  sets how big a circle gets drawn around them and how far `extrapolate='head'`/`'local'` extend. A
  full MEG helmet's sensors genuinely sit further from the head center than a typical EEG cap (they
  wrap around toward the ears/back of the head), so the 0.095 m default head-circle was smaller than
  the actual sensor spread, and every sensor spilled outside the drawn circle no matter which
  `extrapolate` mode was used (`extrapolate='head'`'s own docstring even warns of this: "can extend
  beyond the head when sensors are plotted outside the head circle"). Drawing a bigger circle (0.19
  m, >0.171 m with margin) that actually contains the real sensor spread fixes it -- this doesn't
  change the underlying projected positions at all, just how big a reference circle is drawn around
  them.

Also ruled out along the way: `mne.channels.find_layout()`/`read_layout('Vectorview-mag')` (the
legacy flat manufacturer-grid layout, same box-position family already known bad from Fig 7's round-1
fix) -- tested explicitly as a candidate for Fig 4's MEG positions too, confirmed equally wrong (same
box-coordinate-as-spatial-position confusion), not just assumed wrong by association.

## Source-space onboarding (Figures 8-12), 2026-08-28

Previously fully deferred (see the plan file). User gave an explicit go-ahead to build it out
locally the same way Figures 1-7 were: adapted scripts in `figures_jas/`, real fixes checked
against the installed environment, not assumed. Real, substantive gaps found and fixed, in the
order hit:

- **subjects_dir was a directory-level symlink straight into the shared, not-ours
  `datasets/ds000117/derivatives/freesurfer/` tree.** Any BEM/source-space/coreg write would have
  landed there, not in project space -- caught and fixed *before* running anything, by rebuilding
  `derivatives/biomag_repro/subjects/subXXX/` as real directories with FILE-level symlinks for
  `mri/`/`surf/`/`label/` (read-only inputs) and a real, empty `bem/` (all outputs land here,
  safely in project space). Same philosophy as the existing MEG-data symlink farm, just not yet
  applied to this specific directory.
- **FreeSurfer derivative files were git-annex placeholders, not fetched.** `git annex get` on the
  16 subjects' `derivatives/freesurfer/sub-XX/ses-mri/anat` paths (~750MB total, from the public S3
  remote) -- confirmed this is a genuinely *partial* recon-all output (`mri/{T1,aseg}.mgz`,
  `surf/{lh,rh}.{pial,white,sphere.reg}`, `label/*.annot` -- no `orig.mgz`/`brain.mgz`/inflated
  surfaces), not a full one.
- **No FLASH MRI data** (confirmed absent across the whole dataset) -- `01-anatomy.py`'s
  FLASH-based BEM (`convert_flash_mris`/`make_flash_bem`) can't run. Substituted
  `mne.bem.make_watershed_bem()` (needs only `T1.mgz`, ~10 min/subject) -- see
  `cluster/run_subject_anatomy.py`'s docstring for the full reasoning. Only the 1-layer BEM
  model/solution is built (12-make_forward.py only ever reads that one; the paper's own 3-layer
  BEM was already "unreliable" per its own comment, and every forward/inverse call here is
  MEG-only).
- **No `<hemi>.sphere`, only `<hemi>.sphere.reg`.** `setup_source_space()` needs the former; only
  the latter (the fsaverage-registered one, for morphing) ships in this dataset's derivatives.
  Symlinked `sphere.reg` as a stand-in -- geometrically valid (same topology/vertex count, just
  differently deformed), verified empirically to work correctly (oct6 source space came out with
  exactly 4098 vertices/hemisphere, the correct count -- a broken substitute would very likely not
  have given a clean, correct-looking number).
- **No `mri/transforms/talairach.xfm`.** `mne.coreg.Coregistration`'s default fiducial estimation
  needs it (MNI305 affine registration, another standard recon-all substep we don't have).
  Generated directly via FreeSurfer's own `talairach_avi` binary on `T1.mgz` -- confirmed fast
  (~25s/subject, a coarse affine search, not a real recon-all-cost step).
- **No coregistration script exists in mne-biomag-group-demo's own `scripts/processing/` list at
  all** -- `12-make_forward.py` just assumes a `-trans.fif` already exists (presumably from the
  original W&H/openfMRI FTP distribution, or interactive `mne coreg`); ds000117's public
  BIDS/OpenNeuro release ships none (confirmed, zero `*trans*.fif` anywhere in the dataset tree).
  Added `cluster/run_subject_coreg.py`, a genuine new script (not an adaptation) using
  `mne.coreg.Coregistration`'s automated, headless ICP fitting to the real digitized fiducials +
  head-shape points already in this dataset's dig info -- the standard substitute for manual `mne
  coreg`, and what MNE-BIDS-pipeline itself defaults to. Fit quality logged per subject
  (mean/median/max head-shape<->MRI distance in mm), not just assumed good -- S09 smoke test:
  mean=3.83mm, median=3.06mm, max=11.81mm, visually confirmed via Figure 9's alignment render
  (helmet snugly follows the head, no gross offset).
- **`mne.beamformer.lcmv()` removed entirely** (old one-shot function, confirmed via `hasattr`) --
  `15-lcmv_beamformer.py` rewritten (not AST-stripped) using the modern `make_lcmv()`+`apply_lcmv()`
  two-step API. The old `max_ori_out='signed'` kwarg has no modern equivalent; doesn't matter here
  since the original script already wraps its result in `abs()`, which erases that sign distinction
  regardless.
- **`mne.compute_morph_matrix()` + `stc.morph_precomputed()` removed entirely** (already flagged in
  the Step 0 audit, now actually hit) -- `14`/`16` rewritten using `mne.compute_source_morph(stc,
  subject_from=..., subject_to='fsaverage', spacing=fsaverage_vertices, smooth=smooth,
  subjects_dir=...).apply(stc)`, the modern equivalent (`spacing=fsaverage_vertices` reproduces the
  same ico5 target vertex set the original's own constant specified).
- **14's original per-subject loop has no `exclude_subjects` guard** (unlike every other
  per-subject script in this pipeline, including 16 right next to it) -- would crash loading
  nonexistent files for the 3 excluded subjects if run as originally written. Fixed to skip them,
  matching 16's own correct pattern.
- **`write_inverse_operator()`/`SourceEstimate.save()`/`VectorSourceEstimate.save()` all default
  `overwrite=False`**, same overwrite-gap family already documented above, for the module-level
  and instance-method forms -- monkeypatched/explicit-`overwrite=True` per usual.
- **Slurm compute nodes don't have the same `module` setup as the login node.** Two separate
  issues, both hit for real when the array was first submitted: (1) `module` is a shell function
  from Lmod's init script, not available in a plain non-interactive `#!/bin/bash` sbatch script
  without `source /etc/profile.d/modules.sh` first (login-node interactive shells source this via
  `/etc/profile`, a bare sbatch script doesn't) -- confirmed via the array's first submission
  failing instantly, exit 127, "module: command not found". (2) Even after fixing that, compute
  nodes' default `MODULEPATH` doesn't include the workstation module tree FreeSurfer lives in --
  confirmed via `srun`, needed an explicit `module use /network/iss/apps/modules/scit/workstation`
  before `module load FreeSurfer/7.4.1` would find it. Both fixed in
  `submit_source_space.slurm.sh`.

Smoke-tested end-to-end on openfMRI subject 10 (BIDS sub-09, our "S09") on the desktop before
submitting anything to the cluster: anatomy -> coreg -> forward -> dSPM inverse (4 conditions,
12-26% variance explained, sane range) -> LCMV, all completed cleanly. Full 16-subject array then
submitted via `submit_source_space.slurm.sh` after both Slurm-specific `module` issues were found
and fixed via a one-subject cluster smoke test first (same discipline as every other array
submission in this project).

## Watershed BEM neck/defacing investigation + Figure 9 camera bug (2026-08-28/29)

User review of Figures 8-9 found two more issues:

**Figure 8: watershed BEM surfaces looked wrong** -- outer skull nearly coincident with outer skin
and extending down the whole neck, inner skull too close to the skin, brain surface too large.
Pointed at MNE's own watershed-BEM FAQ entry, whose primary suggested fix is adjusting the
`preflood` height. Investigated properly rather than guessing:
- FreeSurfer's own wiki convention: "if part of the SKULL has been left behind [i.e. too much
  non-brain tissue included], increase the preflood height." Matches this symptom, so tested
  upward first.
- Swept `preflood` = 5, 15 (MNE's un-set default, confirmed via the algorithm's own log message),
  30, 50, on two different subjects (sub004, sub010) -- **all four visually identical** in the
  affected region. Preflood height is not the lever for this symptom, confirmed empirically across
  a 10x range, not assumed after one try.
- Tried the FAQ's next escalation step, `gcaatlas=True` (atlas-guided segmentation, uses anatomical
  priors instead of pure intensity thresholding) -- needs `mri/nu.mgz`, another recon-all output
  this dataset's partial derivatives don't ship (same class of gap as `talairach.xfm` and
  `<hemi>.sphere` above). Symlinked `T1.mgz` as a stand-in (same substitution pattern used
  elsewhere) to actually run it rather than give up at the missing-file error -- **still
  identical** in the affected region.
- With every watershed-level knob ruled out empirically, looked at the raw T1 volume directly (no
  BEM overlay): a sharp, artificial, dead-straight diagonal cut through the anterior face/neck
  region -- a classic defacing artifact, not real anatomy. Confirmed by two independent sources:
  ds000117's own README ("Defacing of MPRAGE T1 images was performed by the submitter") and,
  independently, the *paper's own* Figure 9 caption: "the anonymization of the MRI produces a
  mismatch between digitized points and outer skin surface at the front of the head." **This is a
  known, paper-acknowledged dataset limitation, not a bug in this reproduction** -- the defaced
  region genuinely doesn't contain the tissue-boundary information watershed needs there, and no
  amount of parameter tuning can recover data that was deliberately destroyed for anonymization.
- Fix: reverted sub004/sub010 to plain default watershed settings (matching the other 14 subjects,
  never actually needed changing) and changed Figure 8's own presentation instead --
  `orientation='axial'`, `slices=range(100, 220, 12)` -- axial slices in this range stay inside the
  cranial vault entirely, avoiding the neck geometrically (a coronal or sagittal view can't avoid
  it, since the neck sits directly below the head in every such slice regardless of which slice
  index is picked). Result: surfaces separate cleanly and look correct throughout the shown range,
  with only minor jaggedness at the lowest 1-2 slices where the defaced region's edge intrudes --
  an honest picture of a real, documented dataset limitation, not a cosmetic crop hiding an actual
  bug. **No change needed to the anatomy pipeline itself** -- the other 14 subjects' watershed BEM,
  and everything downstream of it (coreg, forward, inverse, LCMV, group averages, Figures 11/12),
  were never affected and didn't need rebuilding.

**Figure 9: head/helmet looked tilted opposite directions.** Real bug, unrelated to the above:
`fig.plotter.camera_position = "yz"` (a preset) followed by directly mutating
`fig.plotter.camera.azimuth`/`.elevation` on top of it compounds two rotation conventions that
don't obviously compose, producing a picture where the head appeared tilted forward and the helmet
tilted backward relative to it. Confirmed via a side-by-side render with no camera changes at all
that the underlying coregistration itself was fine all along (helmet follows the head normally, no
gross rotational mismatch) -- this was purely a camera-framing bug, not a coreg-quality problem.
Fixed by using `mne.viz.set_3d_view(fig, azimuth=180, elevation=80, distance=0.6)` -- MNE's own
well-defined, documented, single-convention view-setting helper -- instead of raw pyvista camera
manipulation. Result checked directly against the paper's own Figure 9 (3-panel left/front/right)
-- single-panel left-profile equivalent now matches its layout and style closely (nose/ear visible,
helmet conforming, fiducial dots correctly placed, scattered anterior extra-points near the
chin/jaw matching the paper's own visible artifact there too).

## Figures 11/12: two more real bugs found after they first "worked" (2026-08-29)

Both Figure 11 and Figure 12 ran without error and produced plausible-*looking* output on first
pass -- but two real, substantive bugs were still hiding in there, found by actually checking the
result against the paper rather than treating "no exception" as "correct":

- **Figure 12 rendered as a fully gray brain despite 3 genuinely significant clusters
  (p=0.00195/0.03125/0.0352) existing.** `summarize_clusters_stc()`'s own docstring says its
  `tstep` argument should be in seconds, and the original script's own `tstep=tstep` (straight from
  `stc.tstep`, in seconds) matches that. But its *output* duration values then come out in those
  same units too, while `pos_lims=[0, 0.1, 100]` and the "(ms)" time label are unambiguously
  millisecond-scaled (verbatim from the original script). Confirmed by direct inspection:
  `stc_all_cluster_vis.data.max()` was ~0.055 with `tstep` in seconds -- entirely below `pos_lims`'
  own 0.1 lower threshold, so nothing was ever colored -- vs. ~54.5 with `tstep*1000` (ms), which
  actually falls inside the intended 0.1-100 display range. Fixed by passing `tstep=tstep*1000`.
  Whatever much older MNE version the original script was written against must have behaved
  differently here -- same "old code, current MNE renders differently" pattern as everywhere else
  in this project, not a new kind of bug, just one that silently produced an empty-looking figure
  instead of an obvious crash.
- **Figures 11 and 12 both rendered the right hemisphere on the LEFT side of the image.**
  `hemi='both'` + `views='ventral'` -- confirmed directly (not assumed) by rendering a synthetic
  test `SourceEstimate` with data on RH-only vertices: it showed up on the image's left side. Both
  papers' own captions are explicit about their convention ("Right hemisphere is on the right
  side") -- the opposite of what this renders by default. This matters beyond cosmetics: Figure
  11's dSPM panel showed its largest, brightest cluster on what was actually the right hemisphere
  once corrected -- consistent with the fusiform face area's well-known right-lateralization in
  most people, a real finding that was easy to misread as left-lateralized before the fix. Fixed by
  mirroring the rendered image horizontally.
  - First attempt: crop-and-flip just the "brain region" of the image by a fixed pixel-row
    fraction, leaving pyvista's own embedded colorbar/text unflipped (so it wouldn't render
    backwards). Fragile in practice -- the real brain content's vertical extent varies enough
    between renders (different data, different clim) that a fixed fraction either clipped real
    content (visible gap/seam at the crop line) or still caught the top edge of the text label
    (rendered backwards) on different attempts. Both failure modes were actually hit, not just
    anticipated.
  - Real fix: never let pyvista draw a colorbar/label into the same raster as the brain at all
    (`colorbar=False`, `time_label=None`) -- flip the whole (now label-free) image safely, and draw
    a matching colorbar afterward in matplotlib instead, using the same explicit `clim`/`pos_lims`
    values passed to `.plot()` and (for Figure 12's diverging colormap specifically) the *exact*
    colormap MNE would have used internally, extracted via `mne.viz._3d._process_clim()` rather
    than approximated with a similar-looking matplotlib colormap.

## Coregistration was systematically wrong dataset-wide, not just Figure 9's rendering (2026-08-29)

User flagged Figure 9's helmet as visibly tilted "perhaps 30-45 degrees" -- checked numerically
rather than just re-rendering with a different camera: computed Euler angles directly from the
written trans matrix. **Confirmed: 38.7 degree pitch on S09**, matching the visual estimate closely.
This was a real coregistration bug, not a rendering/camera issue (the earlier "camera framing" fix
from the prior review round was real too, but insufficient -- it fixed how a *correct* fit would
have displayed, not the fact that the fit itself was wrong).

Root cause investigation (each step verified empirically, not assumed):
- Confirmed dataset-wide (not S09-specific): every subject's "extra" head-shape digitization points
  sit *entirely* in the anterior/facial region (head-frame Y >= ~0.05m, checked on 4 subjects,
  zero posterior/lateral coverage at all) -- squarely the region already known to be corrupted by
  this dataset's MRI defacing (see "Watershed BEM neck/defacing investigation" above).
- Confirmed ICP's bad fit isn't an initialization problem: ran it from both the fiducial-based
  initial guess and from identity: both converged to a similarly large (~40-48 degree) pitch --
  a genuine bad local optimum given the only available head-shape points sit on a distorted part
  of the scalp mesh, not a starting-point sensitivity issue.
- Confirmed the nasion fiducial has the same problem one level up: with `nasion_weight` at any
  nonzero value (10, 1, 0.1, 0.01 all tested), `fit_fiducials()` alone already gives ~23 degrees of
  pitch; at exactly `nasion_weight=0` it drops to ~0 -- a clean on/off effect pointing at the
  nasion constraint itself, not a weighting-balance issue to tune.
- **Fix, round 1**: exclude nasion and all head-shape points from fitting entirely, rely only on
  LPA/RPA (near the ears, untouched by facial defacing). Brought S09 down to a few degrees on every
  axis. Applied to all 16 subjects.
- **Second bug, found running round 1 across all 16 subjects**: 7 of 16 (S03/S04/S07/S12/S15/
  S17/S19) came out with ~156-176 degree pitch -- essentially upside-down. Root cause: LPA+RPA
  alone are only 2 points, under-determining a rigid transform -- roll around the LPA-RPA axis
  itself is left completely unconstrained (a 180-degree roll leaves both points exactly fixed,
  since they sit ON that axis by construction of the head coordinate system). The optimizer landed
  on one of two equally-LPA/RPA-valid solutions per subject, essentially at random.
- **Fix, round 2**: after the LPA/RPA-only ICP fit, transform the *digitized* (head-frame) nasion
  through the fitted trans into MRI space and check its sign -- FreeSurfer's surface-RAS convention
  fixes Y+ as anterior, a geometric fact independent of any subject-specific fiducial estimate,
  unlike the *position* of the nasion (which defacing does affect). If the transformed nasion lands
  posterior, apply a 180-degree rotation around the fitted LPA-RPA axis to correct it -- confirmed
  this only flips the ambiguous roll DOF and leaves LPA/RPA exactly where ICP put them. This uses
  the nasion only as a binary direction check, not a metric position constraint -- confirmed on the
  two worst subjects (S03: 166.0 -> -14.0 degrees pitch, S04: 163.3 -> -16.7 degrees), both now
  within physically-normal range for a seated recording.
- Full 16-subject re-run (anatomy/BEM unaffected, untouched; coreg -> forward -> dSPM inverse ->
  LCMV -> group averages all redone) after both fixes landed together, not fixed once and shipped
  without the second check -- the array's own per-subject rotation-angle log (added as part of this
  fix, printed for every subject going forward) is the way to catch a third such issue early if one
  exists, rather than relying on spotting it visually in a rendered figure again.

## FLASH MRI was never actually absent, and Figure 8's real fix (2026-08-29)

User review, again: "still not happy with the bem surfaces... find the parameters that were used
to run watershed_bem in the published bem files" plus "Figure 8 still has different views than the
original figure... these are 4 coronal views, posterior to anterior. slices=[40, 100, 140, 180]".
Both leads were followed properly rather than patched over, and both uncovered real, previously
wrong claims in this project's own documentation.

**"Published watershed_bem parameters" don't exist -- the paper never used watershed.**
`original_scripts/01-anatomy.py` (verbatim mirror) only ever calls `convert_flash_mris`/
`make_flash_bem`. This project substituted watershed, justified by "FLASH multi-echo MRI isn't
part of this ds000117 BIDS release" (`run_subject_anatomy.py`'s docstring, `GLITCHES.md`'s
"Source-space onboarding" section) -- **that justification was wrong**. The search behind it ran
`find ... -iname "*flash*"` over `study_path/ds117/*/anatomy/`, a scaffold directory that was never
populated (00-fetch_data.py was skipped project-wide, Step 0) -- it would have found nothing there
regardless of whether FLASH data exists. It does: the actual downloaded BIDS dataset
(`/network/iss/cenir/analyse/meeg/BRAINLIFE/datasets/ds000117/sub-NN/ses-mri/anat/`) ships complete
multi-echo FLASH data for every one of this project's 16 subjects (14 files each -- `run-1` = 5deg
flip angle, `run-2` = 30deg, 7 echoes each, confirmed via the dataset's own sidecar JSONs). The
files were present as **git-annex symlinks whose content had never been fetched** (`git annex get`
had not been run for them) -- confirmed by finding the broken-symlink target
(`.git/annex/objects/...`) didn't exist locally, then fetching successfully from `s3-PUBLIC` (a
real, working remote, no auth needed) for both figure-illustration subjects (sub004, sub010).

**Built the real thing**: `cluster/run_subject_flash_bem.py`, deliberately scoped to only the two
subjects Figures 8/9 illustrate, not the full 16-subject group pipeline -- justified because
`12-make_forward.py` only ever reads the 1-layer (inner-skull-only) BEM solution and coregistration
doesn't fit against the outer-skin surface either (`hsp_weight=0`, see the coregistration section
above), so the outer_skull/outer_skin quality problem below has never affected any already-computed
forward/inverse/LCMV result -- it's a Figure 8/9 visual-fidelity issue only. Two real gaps hit and
fixed along the way:
- `make_flash_bem` needs `mri/brain.mgz` (skull-stripped brain), which this project's partial
  recon-all derivatives don't ship (only `T1.mgz`/`aseg.mgz`). Synthesized as `T1.mgz` masked by
  `aseg.mgz > 0` -- aseg is a real FreeSurfer segmentation already computed for these subjects, not
  a guess, same class of substitution as the `sphere.reg` -> `sphere` symlink.
- Passing raw NIfTI paths straight to `convert_flash_mris(flash5=[...])` lets it do a naive
  nibabel load/save with no TR/TE/flip-angle metadata -- `mri_ms_fitparms` then fails outright
  ("invalid TR or FA for image 0"). Fixed by pre-converting each echo via `mri_convert -tr 20 -te
  1.85 -flip_angle <radians>` (values from the dataset's own FLASH sidecar JSONs), stamping the
  header explicitly before handing off to `convert_flash_mris(flash5=True, flash30=True)`.

**A third, more subtle issue was found and is NOT yet root-caused**: even with correct headers,
`mri_ms_fitparms` logs `non-equal flip_angle found for the volume 7` (through 13) then
`Flip_angle is set to zero` while combining the 5deg/30deg echoes -- on both sub004 and sub010
(systematic, not a one-off). The resulting synthesized `flash5.mgz`/`flash5_reg.mgz` is usable
enough for `mri_make_bem_surfaces`'s edge-based extraction (the BEM surfaces themselves came out
well-separated, closely matching the reference's spacing) but looks visibly noisy/degraded as a
*background image* -- confirmed with a direct 3-way render at a fixed slice (reference vs.
watershed-on-T1 vs. FLASH-on-flash5_reg, `figures_jas/jas_fig8_3way_compare.png`). A manual retry
passing explicit `-tr`/`-te`/`-fa` flags before each volume group (rather than relying on header
auto-detection) was started to test whether that changes `mri_ms_fitparms`'s behavior, but did not
finish within a 10-minute foreground budget and was not pursued further this session.

**Resolution adopted (not blocked on the fitparms issue)**: a hybrid, not a compromise -- FLASH
BEM surfaces (properly separated, the real published method) rendered on plain `T1.mgz` (clean
contrast, closely matching the reference's own look) rather than on the noisy `flash5_reg.mgz`.
Valid because `flash5_reg.mgz` was registered onto `T1.mgz`'s own grid (`fsl_rigid_register`), so
the FLASH surfaces line up correctly on T1.mgz directly -- confirmed by rendering both before
adopting this, not assumed. Both surface sets are kept on disk per subject for either figure
subject: `bem/flash/*.surf` (FLASH, currently active in `bem/*.surf`) and
`bem/watershed_backup_preflash/*.surf` (the original watershed output, kept as a fallback -- has
the same near-coincident outer_skull/outer_skin problem the original "Watershed BEM neck/defacing
investigation" section already ruled out fixing via preflood height, hence not the chosen path here
either).

**Figure 8's panel layout, resolved empirically, not by eye a second time**: the previous
axial+coronal+coronal+"sagittal" layout was wrong (confirmed against the reference), but the user's
correction ("4 coronal, posterior to anterior") also didn't match what panel 1 looked like by eye
(round, no neck/jaw visible -- axial-looking). Rather than re-litigate this visually, built
`figures_jas/jas_fig8_slice_search.py` / `jas_fig8_slice_search_watershed.py`: sweep ~75 coronal
slice indices, render each (BEM contours on, index/orientation labels off, cropped tight to
content), z-score normalize against each of the 4 reference panels (also cropped + normalized), and
score with mean squared difference. Every panel's score curve came out with a single, clean
interior minimum (not a boundary artifact of the sweep range) -- both against the (noisy)
FLASH/flash5_reg render and, better, against the (clean) watershed/T1.mgz render, the one actually
used for the final indices: **slices=[54, 87, 114, 141]**. Anatomical explanation for panel 1's
axial-looking match: slice 54 sits far enough posterior that the coronal plane simply doesn't
intersect the neck -- the same underlying geometric reason an axial slice near the vertex also
misses it. Both search scripts and their diagnostic PNGs (`jas_fig8_slice_search*.png`) are kept as
permanent, re-runnable evidence, not deleted after use.

## Other things noticed, not severity-ranked

- `09-time_frequency.py`'s docstring says "Only channel 'EEG070' is used" but the code indexes
  `'EEG065'` — a real inconsistency in the original repo (comment vs. code), harmless to us but
  worth not being misled by if we ever cite the docstring.
- `config.py`'s `study_path` branches on `os.environ['USER']` matching specific original
  developers (`gramfort`, `mjas`, `alex`, `larsoner`) — none of which will match here, so we
  always hit the `else` branch (`study_path` = the script's own grandparent directory) — fine,
  just needs `study_path` overridden explicitly for our setup rather than relying on that default.
- `00-fetch_data.py` is non-idempotent shell-scripted tarball wrangling (`os.system('wget ...')`,
  `mv`, `rmdir`) — not something to run as-is; we're bridging to already-downloaded BIDS data
  instead, consistent with the plan's symlink-farm approach.
