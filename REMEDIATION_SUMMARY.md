# Remediation Summary — COMPLIANCE_AUDIT.md fixes

Everything catalogued in `COMPLIANCE_AUDIT.md` has been addressed. One commit per app (plus a parent-repo pointer bump), so any regression is individually bisectable/revertable. This file documents what changed and — more importantly — what was deliberately **not** changed and needs a human decision.

## What was fixed

- **1 broken app made functional again**: `ICA-plot` imported from `brainlife_utils` but the submodule was never checked out — `ModuleNotFoundError` on every run. Same root cause found and fixed in `maxwell-filter`.
- **Repo-wide config-validation gap closed**: added `require_config_keys()` to the shared `brainlife_utils` library (pushed to `brainlifeMEEG_utils` master) and adopted it in every app touched this pass (~30 apps). Apps not otherwise touched this pass were intentionally left alone — that was an explicit scope decision, not an oversight.
- **8 apps with a forbidden local `helper.py`** (`filter-epo`, `plot_proj_topomaps-raw`, `SSP-projectors-ECG`, `SSP-projectors-EOG`, `resampling`, `head-pos`, `make-watershed-bem`, `maxwell-filter`): helper removed, replaced with the equivalent `brainlife_utils` functions (`convert_parameters_to_None` → built into `load_config()`; `read_optional_files`, `update_data_info_bads`, `define_kwargs` all have direct equivalents).
- **19 apps migrated onto the brainlife_utils framework**: `average-channels`, `average-erp`, `emptyroom-proj`, `epoch-psd`, `peak-amplitude`, `peak-frequency`, `psd`, `info-epo`, `info-evoked`, `meegflow-app`, `make-watershed-bem`, `SSP-apply`, `SSP-projectors-ECG`, `SSP-projectors-EOG`, `plot_proj_topomaps-raw`, `head-pos`, `resampling`, `filter-epo`, `maxwell-filter`. All core scientific/processing logic preserved unchanged — only config loading, output-dir creation, and product.json construction were rewired.
- **2 apps got a real `main.py` entrypoint** (`head-pos`, `resampling`): renamed from `head_pos.py`/`resampling.py`, `main` bash script updated to match, and their ad-hoc `def main()`/helper functions inlined into flat scripts.
- **All catalogued output-naming violations fixed**, plus a few more found along the way that the original audit sample didn't catch: `filter-raw` and `ICA-apply`'s missing `report.save()` call (report was built via `mne.Report`+`add_ica` but never written to disk — `out_report/` was created but always empty).
- **Misc bugs**: `average-erp`'s `average-all`/`average_all` config key mismatch, plus (confirmed with you) two logic bugs found while migrating it — an `epo`/`evo` variable mix-up that would crash with `NameError`, and a boolean-vs-string comparison that meant the `average-all` option never actually triggered even when set. `meegflow-app`'s hardcoded `/home/maximilien.chaumon/...` path replaced with a path derived from the actual input file. `concat`'s `config.json`/`.example` cleaned of runtime metadata and comment keys. `eeglab2mne` got its missing `README.md`. Two stale `.gitmodules` entries (`maxfilter`, `mean-transformation-matrix`) removed.

## What was deliberately left alone (needs a decision, not a guess)

- **`make-watershed-bem`**: `config.json`'s keys (`subject`, `subjects_dir`, `overwrite`, `volume`, ...) don't match what `main.py` actually reads (only `config['output']`). Config and code have drifted apart; resolving it requires knowing which side reflects current intent.
- **`filter-epo`**: `config.json`'s input key is `mne`, but `main.py` reads `config['epo']` — the app cannot run today without a config that happens to also have an `epo` key. Also, `raw.notch_filter(...)` references an undefined `raw` variable (only `epo`/`epo_orig` exist) — guaranteed `NameError` whenever `config['notch']` is set.
- **`epoch-psd` and `psd`**: both call `mne.time_frequency.psd_multitaper`/`psd_welch` and `Epochs.plot_psd`/`Raw.plot_psd`, all removed in current MNE-Python (replaced by `.compute_psd()`). These apps only run against older MNE releases. Updating the API calls is a logic change, out of scope for a structure-only pass.
- **`plot_proj_topomaps-raw`**: never saved its plotted figure(s) to disk or built a meaningful product.json, even before this migration — `out_figs` wasn't created and no `savefig` call existed. What to persist (one figure vs. a list, depending on `ch_type`) is a design decision, not a mechanical fix.
- **`ICA-plot` and `ICA-fit`'s `main` bash scripts**: both regenerate `product.json` themselves via a `base64`-encoded heredoc *after* `main.py` already wrote a correct one, silently overwriting it. Pre-existing pattern shared across this small app family, not introduced or fixed in this pass — flagging since it means the accumulator-built product.json in these two apps never actually reaches Brainlife.io as written.

## Compliance count vs. the original audit

| | Before | After |
|---|---|---|
| Apps with a forbidden helper module | 8 | 0 |
| Apps missing/not using `brainlife_utils` | 19 (16 missing + 3 copied) | 0 |
| Apps bypassing the framework entirely | 19 | 0 |
| Catalogued output-naming violations | 15 | 0 |
| Apps that couldn't run at all (missing submodule) | 2 (`ICA-plot`, `maxwell-filter`) | 0 |
| Repo-wide config-validation gap | 46/46 apps | Closed for the ~30 apps touched this pass; remaining ~17 apps deferred by choice |

Four issues above are flagged rather than fixed — worth a follow-up pass once you decide the intended behavior for each.
