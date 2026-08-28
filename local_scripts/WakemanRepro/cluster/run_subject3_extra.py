"""
Extra work for subject 3 (openfMRI id 3, BIDS sub-02) needed for Jas Figure 4
("Baseline Correction vs. High-Pass Filtering vs. tSSS"), beyond what the
regular 16-subject chain (run_subject_chain.py) already produces.

Figure 4 compares subject 3's "faces" evoked condition under THREE
conditions:
  (a) baseline correction (l_freq=None)  -- already produced by the regular
      chain (06/07's epoching/evoked under config's default l_freq=None
      applies (None, 0) baseline correction -- see 06-make_epochs.py line
      44: `baseline = (None, 0) if l_freq is None else None`).
  (b) 1 Hz highpass filtering INSTEAD of baseline correction (l_freq=1,
      config-wide -- not the same as the per-subject l_freq=1 pass
      run_subject_chain.py already does, which is ONLY for 05's ICA input
      file and never feeds 06/07/08). This needs 06/07/08 re-run with
      config.l_freq patched to 1 -- but NOT 04 again, since the
      `..._highpass-1Hz_raw.fif` file the regular chain already wrote for
      ICA purposes is the exact same file this needs too.
  (c) tSSS (03-maxwell_filtering.py's from-scratch recompute, subject-3-only
      in the official pipeline, never run before this session) -- needs 03,
      then the `tsss` branches of 05/06/07/08 (each already has an
      `if tsss:` code path, exercised for the first time here).

Preconditions: subject 3 must have already been through the regular 16-subject
chain (run_subject_chain.py) at least once, so its l_freq=None outputs and
l_freq=1-highpass raw file already exist. This script does NOT clear
meg_out_dir (unlike run_subject_chain.py) -- it only adds files alongside
what's already there; the (a)/(b)/(c) filenames never collide (l_freq and
tsss are both embedded in every output filename).

Two fixes applied here, not in the original scripts (see GLITCHES.md,
"Cluster smoke test" section for the same root cause elsewhere):
- `mne.preprocessing.ICA.save()`, `mne.Evoked.save()`, and
  `mne.Epochs.save()` all default to `overwrite=False` in current MNE
  (confirmed via inspect.signature, not assumed) -- same systemic gap
  already documented for 02/05/06 generally. For the tsss branch
  specifically, 06's own `ica_name`/`ica_out_name` are the SAME file (read
  then overwritten in one execution, by the script's own design) -- so
  that one fails on a genuinely FIRST run, not just a rerun; the
  Evoked/Epochs writes fail on RERUNS after any earlier partial failure
  (06 writes several files progressively -- ecg-ave.fif, eog-ave.fif, the
  ICA solution, then epo.fif -- so a failure partway through leaves real,
  not-actually-stale-content files behind that the next attempt must
  legitimately overwrite). All three fixed via process-scoped monkeypatches,
  not edits to the original scripts.
- 03-maxwell_filtering.py takes ~50 min for one subject (6 runs x 2
  st_durations, each a from-scratch tSSS recompute) but IS internally
  idempotent (its own raw.save() already passes overwrite=True) -- skip
  re-running it if all 12 expected output files already exist, so a retry
  after a downstream failure (like the ones these monkeypatches address)
  doesn't waste that time recomputing something already done.

Usage: python3 run_subject3_extra.py
"""
import ast
import os
import resource
import sys
import time

import mne

_orig_ica_save = mne.preprocessing.ICA.save
_orig_evoked_save = mne.Evoked.save
_orig_epochs_save = mne.Epochs.save


def _ica_save_overwrite(self, fname, overwrite=None, verbose=None):
    return _orig_ica_save(self, fname, overwrite=True, verbose=verbose)


def _evoked_save_overwrite(self, fname, *, overwrite=False, verbose=None):
    return _orig_evoked_save(self, fname, overwrite=True, verbose=verbose)


def _epochs_save_overwrite(self, fname, split_size="2GB", fmt="single",
                           overwrite=False, split_naming="neuromag", verbose=None):
    return _orig_epochs_save(self, fname, split_size=split_size, fmt=fmt,
                             overwrite=True, split_naming=split_naming, verbose=verbose)


mne.preprocessing.ICA.save = _ica_save_overwrite
mne.Evoked.save = _evoked_save_overwrite
mne.Epochs.save = _epochs_save_overwrite

HERE = os.path.dirname(os.path.abspath(__file__))
ORIGINAL_SCRIPTS = os.path.normpath(os.path.join(HERE, "..", "original_scripts"))
sys.path.insert(0, ORIGINAL_SCRIPTS)
os.chdir(ORIGINAL_SCRIPTS)

SUBJECT_ID = 3


def rss_gb():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6


def load_verbatim(script_name, strip_last_n, expect_kinds=None):
    path = os.path.join(ORIGINAL_SCRIPTS, script_name)
    src = open(path).read()
    tree = ast.parse(src, filename=path)
    tail = tree.body[-strip_last_n:]
    kinds = [type(n).__name__ for n in tail]
    if expect_kinds is not None and kinds != expect_kinds:
        raise RuntimeError(
            f"{script_name}: expected trailing {expect_kinds}, found {kinds}"
        )
    tree.body = tree.body[: len(tree.body) - strip_last_n]
    code = compile(tree, path, "exec")
    ns = {"__name__": "__main__", "__file__": path}
    exec(code, ns)
    return ns


t0 = time.time()


def log(msg):
    print(f"[{time.time() - t0:7.1f}s][mem {rss_gb():.2f}GB] {msg}", flush=True)


import library.config as cfgmod

# --- (c) tSSS path: 03, then tsss branches of 05/06/07/08 ---
_meg_dir_sub3 = os.path.join(cfgmod.meg_dir, "sub%03d" % SUBJECT_ID)
_expected_03_outputs = [
    os.path.join(_meg_dir_sub3, "run_%02d_filt_tsss_%d_raw.fif" % (run, st))
    for run in range(1, 7) for st in (10, 1)
]
if all(os.path.exists(p) for p in _expected_03_outputs):
    log("=== 03-maxwell_filtering: all 12 outputs already exist, skipping recompute ===")
else:
    log("=== 03-maxwell_filtering (subject 3 only, never run before this) ===")
    ns03 = load_verbatim("03-maxwell_filtering.py", 1, ["Expr"])
    ns03["run_maxwell_filter"](subject_id=SUBJECT_ID)
    log("03 done")

for tsss in (10, 1):
    log(f"=== 05-run_ica tsss={tsss} ===")
    ns05 = load_verbatim("05-run_ica.py", 2, ["Expr", "Expr"])
    ns05["run_ica"](SUBJECT_ID, tsss)

    log(f"=== 06-make_epochs tsss={tsss} ===")
    ns06 = load_verbatim("06-make_epochs.py", 2, ["Expr", "If"])
    ns06["run_epochs"](SUBJECT_ID, tsss=tsss)

    log(f"=== 07-make_evoked tsss={tsss} ===")
    ns07 = load_verbatim("07-make_evoked.py", 2, ["Expr", "If"])
    ns07["run_evoked"](SUBJECT_ID, tsss=tsss)

    log(f"=== 08-make_cov tsss={tsss} ===")
    ns08 = load_verbatim("08-make_cov.py", 2, ["Expr", "If"])
    ns08["run_covariance"](SUBJECT_ID, tsss=tsss)

# --- (b) l_freq=1 config-wide pass: 06/07/08 only (04's l_freq=1 raw file
# already exists from the regular per-subject chain) ---
log("=== l_freq=1 config-wide pass: 06/07/08 (reusing existing highpass-1Hz raw) ===")
cfgmod.l_freq = 1
ns06b = load_verbatim("06-make_epochs.py", 2, ["Expr", "If"])
ns06b["run_epochs"](SUBJECT_ID)
ns07b = load_verbatim("07-make_evoked.py", 2, ["Expr", "If"])
ns07b["run_evoked"](SUBJECT_ID)
ns08b = load_verbatim("08-make_cov.py", 2, ["Expr", "If"])
ns08b["run_covariance"](SUBJECT_ID)
cfgmod.l_freq = None

log(f"=== subject 3 extra work DONE, peak RSS {rss_gb():.2f} GB ===")
