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

Usage: python3 run_subject3_extra.py
"""
import ast
import os
import resource
import sys
import time

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
