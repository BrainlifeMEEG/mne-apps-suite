# Compliance Audit — agent-instructions.md

Full audit of all 46 app directories against the revised `agent-instructions.md`. Read-only audit, no fixes applied. Grouped by violation type; an app can appear in multiple sections.

Generated 2026-07-15.

## Summary

- **17 apps** are fully compliant (aside from the repo-wide config-validation gap, see below).
- **8 apps** are compliant except for a single output-filename violation.
- **~19 apps** substantially bypass the `brainlife_utils` framework entirely (no `load_config`/`setup_matplotlib_backend`/`ensure_output_dirs`/`product_items` accumulator) — mostly older apps.
- **8 apps** contain a forbidden local helper module.
- **Every app checked** has the same gap: no clean-exit/warning behavior on missing or invalid required config keys (raises uncaught `KeyError` instead). This is universal enough to treat as one repo-wide fix rather than 46 individual ones.

## 1. Forbidden local helper module (any name)

All must be removed; logic upstreamed to `brainlife_utils` first if not already there.

| App | Detail |
|---|---|
| `filter-epo` | `import helper` at main.py:9, used at :21 |
| `plot_proj_topomaps-raw` | `import helper` at main.py:5, used at :16 |
| `SSP-projectors-ECG` | `import helper` at main.py:12, used at :25 |
| `SSP-projectors-EOG` | `import helper` at main.py:12, used at :25 |
| `resampling` | `from brainlife_apps_helper import helper` at resampling.py:12, used throughout |
| `head-pos` | `from brainlife_apps_helper import helper` at head_pos.py:6 |
| `make-watershed-bem` | `brainlife_apps_helper/helper.py` present but not even imported — dead file, still a violation of presence |
| `maxwell-filter` | imports point at a nonexistent `brainlife_utils` path; ships its own `brainlife_apps_helper/helper.py` instead |

## 2. `brainlife_utils` missing or not a real submodule

**Missing entirely (no directory at all):** `average-channels`, `average-erp`, `emptyroom-proj`, `epoch-psd`, `head-pos`, `info-epo`, `info-evoked`, `maxwell-filter`, `peak-amplitude`, `peak-frequency`, `plot_proj_topomaps-raw`, `psd`, `resampling`, `SSP-apply`, `SSP-projectors-ECG`, `SSP-projectors-EOG` (16 apps)

**Present but plain copy, not a git submodule (no `.git`):** `ICA-apply`, `ICA-apply-epo`, `interpolate-raw`

**Present but unused by main.py:** `meegflow-app` (dir exists, never imported — uses raw `os.makedirs` instead), `make-watershed-bem`

**Needs manual re-check:** `ICA-plot` — structural pass flagged no `brainlife_utils/` directory, but the code-level pass found it correctly calling `load_config`/`setup_matplotlib_backend`/`ensure_output_dirs`/`product_items`. Worth confirming how it's importing `brainlife_utils` before trusting either finding.

## 3. Apps bypassing the brainlife_utils framework entirely

No `load_config()`, `setup_matplotlib_backend()`, `ensure_output_dirs()`, or `product_items` accumulator — config read via raw `json.load`/manual dict indexing, product.json (if produced at all) hand-rolled or absent:

`average-channels`, `average-erp`, `emptyroom-proj`, `epoch-psd`, `peak-amplitude`, `peak-frequency`, `psd`, `info-epo`, `info-evoked`, `meegflow-app`, `make-watershed-bem`, `SSP-apply`, `SSP-projectors-ECG`, `SSP-projectors-EOG`, `plot_proj_topomaps-raw`, `head-pos`, `resampling`, `filter-epo`, `maxwell-filter`

This is the largest and most consequential finding — 19 of 46 apps (41%) predate the shared-utilities convention and need a real migration, not a spot-fix.

## 4. Output filename violations (otherwise-compliant apps)

| App | Wrong name | Should be | Location |
|---|---|---|---|
| `maxwell-filter` | `meg.fif` | `raw.fif` | main.py:224 |
| `maxwell-filter` | `report_maxwell_filter.html` | `report.html` | main.py:298 |
| `ICA-apply` | `meg.fif` | `raw.fif` | main.py:140 |
| `epoch` | `meg-epo.fif` | `epo.fif` | main.py:190 |
| `drop-bad-epo` | `meg-epo.fif` | `epo.fif` | main.py:143 |
| `ICA-apply-epo` | `meg-epo.fif` | `epo.fif` | main.py:162 |
| `filter-epo` | `meg-epo.fif` | `epo.fif` | main.py:75 |
| `filter-epo` | `report_filter.html` | `report.html` | main.py:72 |
| `filter-raw` | `meg.fif` | `raw.fif` | main.py:120 |
| `evoked-averaged` | `evokeds_ave.fif` | `ave.fif` | main.py:101 |
| `ICA-fit` | `report_ica.html` | `report.html` | main.py:154 |
| `ICA-plot` | `report_ica.html` | `report.html` | main.py:74-75 |
| `SSP-apply` | `meg.fif` | `raw.fif` | main.py:36 |
| `resampling` | `meg.fif` | `raw.fif` | resampling.py:87 |
| `make-watershed-bem` | `out_dir_report/report.html` | `out_report/report.html` | main.py:46 (wrong *directory*, not filename) |

## 5. Entrypoint not named `main.py`

- `head-pos` → `head_pos.py`
- `resampling` → `resampling.py`

## 6. Ad-hoc function definitions (violates flat-script rule)

- `resampling.py`: `def resampling(...)` (line 15), `def main():` (line 92)
- `head_pos.py`: `def head_pos(...)` (line 9), `def main():` (line 76)

No other apps in the full 46-app audit define ad-hoc functions.

## 7. Missing real `config.json`

Beyond the apps already listed in §3 (which lack config.json as part of bypassing the framework entirely), note:

- `resampling`, `head-pos`, `maxwell-filter` only have `config.json.example` — explicitly violates the "example alone is insufficient" rule since these apps do have real configurable parameters.
- `bdf2mne`, `brainvision2mne`, `edf2mne`, `eeglab2mne`, `fif2mne` have no `config.json` but *are* otherwise fully compliant, correctly call `load_config()`, and take their one parameter (input file path) from the Brainlife-injected config at runtime — likely fine as-is; flagging for a judgment call rather than as a hard violation.

## 8. Repo-wide gap: no clean exit on missing/invalid config keys

Every single app audited reads required config keys via direct `config['key']` indexing with no validation or try/except — a missing key raises an uncaught `KeyError` instead of the required `add_info_to_product` warning + clean exit. Given how universal this is, the efficient fix is a shared helper in `brainlife_utils` (e.g. `require_config_keys(config, [...])`) that all apps adopt, rather than 46 bespoke fixes.

## 9. Other notable issues found (not directly a documented rule, but worth fixing)

- `average-erp`: `config.json` key is `average-all` (hyphen) but `main.py:34` pops `average_all` (underscore) — likely a real functional bug, not just a style issue.
- `concat`: checked-in `config.json` is polluted with Brainlife runtime metadata (`_app`, `_tid`, `_inputs`, `_outputs`) rather than a clean example config.
- `meegflow-app`: hardcoded absolute path `/home/maximilien.chaumon/liensNet/...` in main.py:69 — not portable.
- `eeglab2mne`: missing `README.md` entirely.
- Root `.gitmodules`: two stale entries with no checked-out directory — `maxfilter`, `mean-transformation-matrix`.

## Fully compliant apps (aside from §8)

`ctf2mne`, `egi2mne`, `fif2mne`, `crop-raw`, `events`, `notch-filter`, `add-flat-chan`, `add-montage`, `bdf2mne`, `brainvision2mne`, `edf2mne`, `eeglab2mne`, `eventslog`, `info-raw`, `mark-bad-raw`, `plot-epochs`, `ICA-fit-epo`
