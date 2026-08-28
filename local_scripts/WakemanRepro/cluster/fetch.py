"""
Ensure one subject's raw + proc-sss git-annex content is actually present
on disk (not just symlinked). ds000117 is a git-annex/datalad checkout --
Step 0 found that only S09's content had ever been pulled from the S3
remote; every other subject needs the same `git annex get` treatment
before the symlink farm's links will resolve to real files.

Checks presence first and is a no-op (no subprocess call at all) when
content is already there -- deliberately, not just as an optimization:
compute nodes were found to have neither internet egress nor `git-annex`
on PATH by default (it exists only as an unloaded module), so a live
`git annex get` from a compute node is not reliable. Real fetching should
happen via prefetch_raw.sh from a machine with both (e.g. the dev desktop,
confirmed working during Step 0); this function's job on the cluster side
is to verify, and fail with an actionable message if something's missing,
not to be the fetch mechanism itself.
"""
import shutil
import subprocess

from crosswalk import bids_id

DATASET_ROOT = "/network/iss/cenir/analyse/meeg/BRAINLIFE/datasets/ds000117"


def _all_present(sub_bids):
    import os

    for run in range(1, 7):
        raw = os.path.join(
            DATASET_ROOT, sub_bids, "ses-meg", "meg",
            f"{sub_bids}_ses-meg_task-facerecognition_run-{run:02d}_meg.fif",
        )
        sss = os.path.join(
            DATASET_ROOT, "derivatives", "meg_derivatives", sub_bids,
            "ses-meg", "meg",
            f"{sub_bids}_ses-meg_task-facerecognition_run-{run:02d}_proc-sss_meg.fif",
        )
        if not (os.path.exists(raw) and os.path.exists(sss)):
            return False
    return True


def ensure_raw_fetched(openfmri_subject_id):
    sub_bids = bids_id(openfmri_subject_id)

    if _all_present(sub_bids):
        print(f"[fetch] {sub_bids}: all 6 runs' raw+proc-sss content already "
              f"present, skipping git annex get.")
        return sub_bids

    if shutil.which("git-annex") is None:
        raise RuntimeError(
            f"[fetch] {sub_bids}: raw/proc-sss content is missing AND "
            f"git-annex isn't on PATH here (no internet egress on compute "
            f"nodes either, most likely) -- run ./prefetch_raw.sh from a "
            f"machine with both (e.g. the dev desktop) before retrying this "
            f"subject."
        )

    for rel in (
        f"{sub_bids}/ses-meg/meg",
        f"derivatives/meg_derivatives/{sub_bids}/ses-meg/meg",
    ):
        print(f"[fetch] git annex get {rel}")
        subprocess.run(
            ["git", "annex", "get", rel, "--from=s3-PUBLIC"],
            cwd=DATASET_ROOT, check=True,
        )
    return sub_bids
