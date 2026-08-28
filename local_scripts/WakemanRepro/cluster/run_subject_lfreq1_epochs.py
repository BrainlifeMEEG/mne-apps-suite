"""
Per-subject l_freq=1 pass of 06-make_epochs.py + 07-make_evoked.py, for
Jas Figure 5's panel B (grand-average evoked under 1 Hz highpass instead
of baseline correction).

Only 06+07 need to rerun -- NOT 03/04/05. 06's own ICA read path
(`ica_name = 'run_concat-ica.fif'`) doesn't depend on l_freq at all (only
`ica_out_name`, the exclusion-annotated copy it writes back out, does) --
the ICA solution 05 already fit once under l_freq=None is reused as-is.
04's dual-pass in run_subject_chain.py already produced the
highpass-1Hz raw file every subject needs here.

Does NOT clear meg_out_dir (unlike run_subject_chain.py) -- must preserve
the existing l_freq=None outputs sitting there. Filenames never collide:
every 06/07 output embeds l_freq in its name.

Same overwrite monkeypatches as cluster/run_subject3_extra.py, applied
defensively here too (see GLITCHES.md, "Cluster smoke test" /
"Subject-3 tSSS branch" sections for why), PLUS one more found running
this specific script: 07-make_evoked.py calls the module-level
`mne.evoked.write_evokeds()` directly (not an Evoked instance's
`.save()`), a different call path the ICA/Evoked/Epochs `.save()`
monkeypatches don't touch -- confirmed by the traceback when subject 3
(who already has this exact file from cluster/run_subject3_extra.py)
collided on a real rerun.

Usage: python3 run_subject_lfreq1_epochs.py <openfmri_subject_id>
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
_orig_write_evokeds = mne.evoked.write_evokeds


def _ica_save_overwrite(self, fname, overwrite=None, verbose=None):
    return _orig_ica_save(self, fname, overwrite=True, verbose=verbose)


def _evoked_save_overwrite(self, fname, *, overwrite=False, verbose=None):
    return _orig_evoked_save(self, fname, overwrite=True, verbose=verbose)


def _epochs_save_overwrite(self, fname, split_size="2GB", fmt="single",
                           overwrite=False, split_naming="neuromag", verbose=None):
    return _orig_epochs_save(self, fname, split_size=split_size, fmt=fmt,
                             overwrite=True, split_naming=split_naming, verbose=verbose)


def _write_evokeds_overwrite(fname, evoked, *, on_mismatch="raise", overwrite=False, verbose=None):
    return _orig_write_evokeds(fname, evoked, on_mismatch=on_mismatch,
                               overwrite=True, verbose=verbose)


mne.preprocessing.ICA.save = _ica_save_overwrite
mne.Evoked.save = _evoked_save_overwrite
mne.Epochs.save = _epochs_save_overwrite
mne.evoked.write_evokeds = _write_evokeds_overwrite
mne.write_evokeds = _write_evokeds_overwrite

HERE = os.path.dirname(os.path.abspath(__file__))
ORIGINAL_SCRIPTS = os.path.normpath(os.path.join(HERE, "..", "original_scripts"))
sys.path.insert(0, HERE)
sys.path.insert(0, ORIGINAL_SCRIPTS)
os.chdir(ORIGINAL_SCRIPTS)

from crosswalk import EXCLUDED  # noqa: E402


def rss_gb():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6


def load_verbatim(script_name, strip_last_n, expect_kinds=None):
    path = os.path.join(ORIGINAL_SCRIPTS, script_name)
    src = open(path).read()
    tree = ast.parse(src, filename=path)
    tail = tree.body[-strip_last_n:]
    kinds = [type(n).__name__ for n in tail]
    if expect_kinds is not None and kinds != expect_kinds:
        raise RuntimeError(f"{script_name}: expected trailing {expect_kinds}, found {kinds}")
    tree.body = tree.body[: len(tree.body) - strip_last_n]
    code = compile(tree, path, "exec")
    ns = {"__name__": "__main__", "__file__": path}
    exec(code, ns)
    return ns


def main(subject_id):
    t0 = time.time()

    def log(msg):
        print(f"[{time.time() - t0:7.1f}s][mem {rss_gb():.2f}GB] {msg}", flush=True)

    if subject_id in EXCLUDED:
        log(f"subject_id {subject_id} excluded, nothing to do.")
        return

    import library.config as cfgmod
    cfgmod.l_freq = 1

    log(f"=== subject {subject_id}: 06-make_epochs (l_freq=1) ===")
    ns06 = load_verbatim("06-make_epochs.py", 2, ["Expr", "If"])
    ns06["run_epochs"](subject_id)

    log(f"=== subject {subject_id}: 07-make_evoked (l_freq=1) ===")
    ns07 = load_verbatim("07-make_evoked.py", 2, ["Expr", "If"])
    ns07["run_evoked"](subject_id)

    log(f"=== subject {subject_id} DONE, peak RSS {rss_gb():.2f} GB ===")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    main(int(sys.argv[1]))
