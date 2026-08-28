"""
Build (or verify) one subject's slice of the derivatives/biomag_repro
symlink farm -- the same structure built and verified by hand for S09
during Step 0 (see original_scripts/GLITCHES.md, "Symlink farm built and
verified (0c)"), generalized here to any ds000117 subject via the
openfMRI<->BIDS crosswalk.

Idempotent: safe to call every time before processing a subject, on every
array-job run. Only ever creates symlinks / directories; never touches
existing content that isn't ours.
"""
import os

from crosswalk import bids_id

DATASET_ROOT = "/network/iss/cenir/analyse/meeg/BRAINLIFE/datasets/ds000117"
FARM_ROOT = (
    "/network/iss/cenir/analyse/meeg/BRAINLIFE/code/local_scripts/"
    "WakemanRepro/derivatives/biomag_repro"
)


def _symlink(target, link_path):
    if os.path.islink(link_path):
        if os.readlink(link_path) == target:
            return  # already correct
        os.remove(link_path)
    elif os.path.exists(link_path):
        raise RuntimeError(
            f"{link_path} exists and is not a symlink -- refusing to "
            f"overwrite (looks like real content, not farm scaffolding)."
        )
    os.symlink(target, link_path)


def ensure_farm(openfmri_subject_id):
    """Build derivatives/biomag_repro/ds117/sub%03d/... for one subject.
    Returns the BIDS id used."""
    sub_bids = bids_id(openfmri_subject_id)
    sub_of = "sub%03d" % openfmri_subject_id

    meg_dir = os.path.join(FARM_ROOT, "ds117", sub_of, "MEG")
    anat_dir = os.path.join(FARM_ROOT, "ds117", sub_of, "anatomy")
    os.makedirs(meg_dir, exist_ok=True)
    os.makedirs(anat_dir, exist_ok=True)  # unused by 02/04/05/06, parity only

    # 02-extract_events.py never creates its own output dir (meg_dir/sub%03d/
    # in library.config's sense, i.e. FARM_ROOT/MEG/sub%03d/) -- it silently
    # relies on 00-fetch_data.py having created the whole MEG/ tree upfront
    # (GLITCHES.md's own path table already notes 00 "creates meg_dir,
    # subjects_dir"). We deliberately never run 00, so nothing else fills
    # that role except 04's own self-creating mkdir -- which only works if
    # 04 happens to run before 02. Create it here instead, as pure directory
    # scaffolding standing in for 00's setup role, not a logic change to any
    # original script.
    os.makedirs(os.path.join(FARM_ROOT, "MEG", sub_of), exist_ok=True)

    bids_meg = os.path.join(
        DATASET_ROOT, sub_bids, "ses-meg", "meg",
        f"{sub_bids}_ses-meg_task-facerecognition",
    )
    bids_sss = os.path.join(
        DATASET_ROOT, "derivatives", "meg_derivatives", sub_bids, "ses-meg",
        "meg", f"{sub_bids}_ses-meg_task-facerecognition",
    )

    for run in range(1, 7):
        run_tag = f"run-{run:02d}"
        _symlink(
            f"{bids_meg}_{run_tag}_meg.fif",
            os.path.join(meg_dir, f"run_{run:02d}_raw.fif"),
        )
        _symlink(
            f"{bids_sss}_{run_tag}_proc-sss_meg.fif",
            os.path.join(meg_dir, f"run_{run:02d}_sss.fif"),
        )
        _symlink(
            f"{bids_sss}_{run_tag}_proc-sss_log.txt",
            os.path.join(meg_dir, f"run_{run:02d}_sss_log.txt"),
        )

    subjects_dir = os.path.join(FARM_ROOT, "subjects")
    os.makedirs(subjects_dir, exist_ok=True)
    fs_target = os.path.join(
        DATASET_ROOT, "derivatives", "freesurfer", sub_bids, "ses-mri", "anat"
    )
    fs_link = os.path.join(subjects_dir, sub_of)
    if os.path.isdir(fs_target):
        _symlink(fs_target, fs_link)
    else:
        print(
            f"[farm] WARNING: no FreeSurfer output found at {fs_target} for "
            f"{sub_of} ({sub_bids}) -- skipping subjects/ symlink (not "
            f"needed by 02/04/05/06, only by 01-anatomy.py / source-space "
            f"scripts, out of scope here)."
        )

    print(f"[farm] {sub_of} <-> {sub_bids} ready under {FARM_ROOT}")
    return sub_bids
