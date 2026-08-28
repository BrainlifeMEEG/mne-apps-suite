"""
Run the full verbatim 02 -> 04 (x2) -> 05 -> 06 -> 07 -> 08 -> 10 chain for
ONE subject. (11-group_average_sensors.py has no per-subject function --
it processes all subjects inline -- so it's NOT here; run it once, after
all subjects have 07 output, via run_grand_average.py.)

This is the per-subject unit of work submitted by the Slurm array in
submit_pipeline.slurm.sh. It reuses, consolidated into one script, exactly
the AST-strip technique validated interactively for S09 during Step 0 (see
original_scripts/GLITCHES.md): each original script's source is parsed,
its module-level batch-driver statements (the "loop over all 19 subjects"
tail) are removed, and the resulting run_*() function is called directly
for just this subject_id. No line inside any original script is edited.

Usage:
    python3 run_subject_chain.py <openfmri_subject_id>

Exit code 0 = full chain succeeded; non-zero = failed (see stderr/log).
"""
import ast
import os
import resource
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ORIGINAL_SCRIPTS = os.path.normpath(os.path.join(HERE, "..", "original_scripts"))
sys.path.insert(0, HERE)               # crosswalk, farm, fetch
sys.path.insert(0, ORIGINAL_SCRIPTS)   # library.config

from crosswalk import EXCLUDED  # noqa: E402
from farm import ensure_farm, FARM_ROOT  # noqa: E402
from fetch import ensure_raw_fetched  # noqa: E402


def rss_gb():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6


def load_verbatim(script_name, strip_last_n, expect_kinds=None):
    """Exec an original script's source with its trailing module-level
    batch-driver statement(s) removed, returning its namespace. Function
    bodies are untouched -- only the tail is cut, and only by a count
    verified interactively against this exact script during Step 0."""
    path = os.path.join(ORIGINAL_SCRIPTS, script_name)
    src = open(path).read()
    tree = ast.parse(src, filename=path)
    tail = tree.body[-strip_last_n:]
    kinds = [type(n).__name__ for n in tail]
    if expect_kinds is not None and kinds != expect_kinds:
        raise RuntimeError(
            f"{script_name}: expected trailing {expect_kinds}, found "
            f"{kinds} -- original script may have changed, re-verify "
            f"before trusting this run."
        )
    tree.body = tree.body[: len(tree.body) - strip_last_n]
    code = compile(tree, path, "exec")
    ns = {"__name__": "__main__", "__file__": path}
    exec(code, ns)
    return ns


def run_chain(subject_id):
    t0 = time.time()

    def log(msg):
        print(f"[{time.time() - t0:7.1f}s][mem {rss_gb():.2f}GB] {msg}", flush=True)

    if subject_id in EXCLUDED:
        log(f"subject_id {subject_id} is excluded (bad EEG per README / "
            f"config.exclude_subjects) -- nothing to do.")
        return

    log(f"=== subject_id {subject_id}: ensure data + farm ===")
    sub_bids = ensure_raw_fetched(subject_id)
    ensure_farm(subject_id)
    log(f"data + farm ready ({sub_bids})")

    # Idempotency fix, not a pipeline logic change: only 04's raw.save()
    # passes overwrite=True -- 02/05/06's write/save calls don't, and
    # current MNE defaults to refusing to overwrite (see GLITCHES.md,
    # "Cluster smoke test" section). meg_out_dir is entirely OUR generated
    # output (never original/downloaded data), so clearing it before each
    # run is safe and makes every run behave like a genuine first run.
    meg_out_dir = os.path.join(FARM_ROOT, "MEG", "sub%03d" % subject_id)
    if os.path.isdir(meg_out_dir):
        shutil.rmtree(meg_out_dir)
        log(f"cleared stale outputs at {meg_out_dir} for a clean rerun")
    os.makedirs(meg_out_dir, exist_ok=True)  # farm.py creates this too, but
    # we just rmtree'd it -- 02 needs it to exist and creates nothing itself

    # 06-make_epochs.py reads bads/<mapping>/run_NN_raw_tr.fif_bad via a
    # RELATIVE path -- must run from original_scripts/ for that to resolve
    # (same fix as the interactive S09 test).
    os.chdir(ORIGINAL_SCRIPTS)

    import library.config as cfgmod

    log("=== 02-extract_events ===")
    ns02 = load_verbatim("02-extract_events.py", 2, ["Assign", "Expr"])
    ns02["run_events"](subject_id)

    log("=== 04-python_filtering, pass 1 (l_freq=%r, config default) ===" % cfgmod.l_freq)
    ns04a = load_verbatim("04-python_filtering.py", 1, ["Expr"])
    ns04a["run_filter"](subject_id)

    log("=== 04-python_filtering, pass 2 (l_freq patched to 1, for ICA) ===")
    cfgmod.l_freq = 1
    ns04b = load_verbatim("04-python_filtering.py", 1, ["Expr"])
    ns04b["run_filter"](subject_id)
    cfgmod.l_freq = None  # restore config default before 06 imports it

    log("=== 05-run_ica ===")
    ns05 = load_verbatim("05-run_ica.py", 2, ["Expr", "Expr"])
    ns05["run_ica"](subject_id)

    log("=== 06-make_epochs ===")
    ns06 = load_verbatim("06-make_epochs.py", 2, ["Expr", "If"])
    ns06["run_epochs"](subject_id)

    log("=== 07-make_evoked ===")
    ns07 = load_verbatim("07-make_evoked.py", 2, ["Expr", "If"])
    ns07["run_evoked"](subject_id)

    log("=== 08-make_cov ===")
    ns08 = load_verbatim("08-make_cov.py", 2, ["Expr", "If"])
    ns08["run_covariance"](subject_id)

    log("=== 10-sliding_estimator ===")
    ns10 = load_verbatim("10-sliding_estimator.py", 1, ["For"])
    for cond1, cond2 in (("face", "scrambled"), ("face/famous", "face/unfamiliar")):
        ns10["run_time_decoding"](subject_id, cond1, cond2)

    log(f"=== subject_id {subject_id} DONE, peak RSS {rss_gb():.2f} GB ===")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    run_chain(int(sys.argv[1]))
