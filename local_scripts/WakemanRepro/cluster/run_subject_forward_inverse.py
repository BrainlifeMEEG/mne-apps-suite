"""
Per-subject 12-make_forward.py + 13-make_inverse.py, run verbatim via the
AST-strip technique (see load_verbatim() in cluster/run_subject_lfreq1_epochs.py
for the established pattern) -- neither script needs a real rewrite, both
already MEG-only (eeg=False / 1-layer BEM) and their function bodies don't
call anything API-broken. Only gap: `write_inverse_operator()` and
`SourceEstimate.save()`/etc default `overwrite=False` in current MNE and
neither call passes it -- monkeypatched here (same pattern used throughout
this project, see GLITCHES.md). `write_forward_solution()` already gets
`overwrite=True` explicitly in the original script -- no patch needed there.

Needs run_subject_anatomy.py (BEM+source space) and run_subject_coreg.py
(trans file) already done for this subject.

Usage: python3 run_subject_forward_inverse.py <openfmri_subject_id>
"""
import ast
import os
import sys
import time

import mne


def main(subject_id):
    t0 = time.time()

    def log(msg):
        print(f"[{time.time() - t0:7.1f}s] {msg}", flush=True)

    HERE = os.path.dirname(os.path.abspath(__file__))
    ORIGINAL_SCRIPTS = os.path.normpath(os.path.join(HERE, "..", "original_scripts"))
    sys.path.insert(0, HERE)
    sys.path.insert(0, ORIGINAL_SCRIPTS)
    os.chdir(ORIGINAL_SCRIPTS)

    from crosswalk import EXCLUDED  # noqa: E402

    if subject_id in EXCLUDED:
        log(f"subject_id {subject_id} excluded, nothing to do.")
        return

    from mne.minimum_norm import write_inverse_operator
    import mne.minimum_norm as mn

    _orig = mn.write_inverse_operator

    def _write_inverse_operator_overwrite(fname, inv, *, overwrite=False, verbose=None):
        return _orig(fname, inv, overwrite=True, verbose=verbose)

    mn.write_inverse_operator = _write_inverse_operator_overwrite
    # 13-make_inverse.py imports write_inverse_operator by name at module
    # level (`from mne.minimum_norm import write_inverse_operator`) -- that
    # binds a local name in *this* module's exec namespace when load_verbatim
    # runs it, so patching mne.minimum_norm's attribute before exec is enough
    # (the import inside the exec'd source re-reads the patched attribute).

    # 13-make_inverse.py's apply_inverse(..., pick_ori='vector') returns a
    # VectorSourceEstimate, not a plain SourceEstimate -- a DIFFERENT class
    # with its own .save() also defaulting overwrite=False. Patching only
    # SourceEstimate.save (as originally done here) missed it; hit for real
    # when subjects 2 and 10 (already computed once, during the smoke test)
    # got reprocessed by the full array and crashed with FileExistsError.
    _orig_stc_save = mne.SourceEstimate.save
    _orig_vec_stc_save = mne.VectorSourceEstimate.save

    def _stc_save_overwrite(self, fname, ftype="stc", *, overwrite=False, verbose=None):
        return _orig_stc_save(self, fname, ftype=ftype, overwrite=True, verbose=verbose)

    def _vec_stc_save_overwrite(self, fname, ftype="h5", *, overwrite=False, verbose=None):
        return _orig_vec_stc_save(self, fname, ftype=ftype, overwrite=True, verbose=verbose)

    mne.SourceEstimate.save = _stc_save_overwrite
    mne.VectorSourceEstimate.save = _vec_stc_save_overwrite

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

    log("=== 12-make_forward ===")
    ns12 = load_verbatim("12-make_forward.py", 2, ["Assign", "Expr"])
    ns12["run_forward"](subject_id)
    log("forward solution done")

    log("=== 13-make_inverse ===")
    ns13 = load_verbatim("13-make_inverse.py", 2, ["Assign", "Expr"])
    ns13["run_inverse"](subject_id)
    log("inverse operator + dSPM stcs done")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    main(int(sys.argv[1]))
