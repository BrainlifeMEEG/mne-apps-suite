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
