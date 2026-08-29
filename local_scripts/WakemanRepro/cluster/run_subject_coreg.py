"""
Per-subject MEG-to-MRI coregistration -- produces the `<subject>-trans.fif`
that `12-make_forward.py` reads (`study_path/ds117/subXXX/MEG/subXXX-trans.fif`).

This is a genuine ADDITION, not an adaptation: mne-biomag-group-demo's own
`scripts/processing/` numbered list has no coregistration script at all --
`12-make_forward.py` just reads an existing `-trans.fif` as a given input.
The original W&H/openfMRI `ds117` FTP distribution the demo was built
against apparently shipped pre-made trans files (or expected interactive
`mne coreg` / MaxFilter-computed ones); ds000117's public BIDS/OpenNeuro
release doesn't include any (confirmed: `find ... -iname "*trans*.fif"`
across the whole dataset tree, zero matches).

Uses `mne.coreg.Coregistration` -- automated, headless, ICP-based
coregistration to the real digitized fiducials + head-shape points
(confirmed present in this dataset's dig info: cardinal fiducials, HPI,
EEG electrode positions, and ~50 extra head-shape points per subject, see
GLITCHES.md). This is the standard, well-documented substitute for manual
`mne coreg` when no pre-existing trans is available -- the same approach
MNE-BIDS-pipeline itself defaults to. Recipe follows MNE's own
"Source alignment without MRI-device co-registration" / automated-coreg
tutorial pattern:
  1. `fit_fiducials()` -- rigid fit using the 3 cardinal points alone.
  2. `fit_icp()` first pass, then drop head-shape points that are still
     >5mm away as likely digitization outliers (`omit_head_shape_points`),
     then a second, longer `fit_icp()` pass on the cleaned point set --
     the standard two-pass ICP pattern from MNE's own tutorial, not
     invented here.
  3. Logs the final MRI<->head-shape point distances (mean/max) so a
     poor fit is visible in the log rather than silently accepted --
     no manual QC step exists here, so this is the only signal before
     Figure 9's visual coregistration check.

Needs `<subject>-head.fif` (the low-res head surface `make_watershed_bem`
already writes as part of run_subject_anatomy.py, `copy=True` default) --
run anatomy before coreg for a given subject.

Usage: python3 run_subject_coreg.py <openfmri_subject_id>
"""
import os
import sys
import time

import numpy as np
import mne
from mne.coreg import Coregistration

HERE = os.path.dirname(os.path.abspath(__file__))
ORIGINAL_SCRIPTS = os.path.normpath(os.path.join(HERE, "..", "original_scripts"))
sys.path.insert(0, HERE)
sys.path.insert(0, ORIGINAL_SCRIPTS)

from crosswalk import EXCLUDED  # noqa: E402
from library.config import subjects_dir, meg_dir, study_path, l_freq  # noqa: E402


def main(subject_id):
    t0 = time.time()

    def log(msg):
        print(f"[{time.time() - t0:7.1f}s] {msg}", flush=True)

    if subject_id in EXCLUDED:
        log(f"subject_id {subject_id} excluded, nothing to do.")
        return

    subject = "sub%03d" % subject_id
    fname_ave = os.path.join(meg_dir, subject, f"{subject}_highpass-{l_freq}Hz-ave.fif")
    fname_trans_dir = os.path.join(study_path, "ds117", subject, "MEG")
    fname_trans = os.path.join(fname_trans_dir, f"{subject}-trans.fif")
    os.makedirs(fname_trans_dir, exist_ok=True)

    if os.path.isfile(fname_trans):
        log(f"{fname_trans} already exists, skipping")
        return

    info = mne.io.read_info(fname_ave)
    n_dig = len(info["dig"]) if info["dig"] else 0
    log(f"read info, {n_dig} digitization points")

    coreg = Coregistration(info, subject, subjects_dir=subjects_dir, fiducials="auto")
    log("fitting fiducials ...")
    coreg.fit_fiducials(verbose=False)
    log("first ICP pass ...")
    coreg.fit_icp(n_iterations=6, nasion_weight=2.0, verbose=False)
    coreg.omit_head_shape_points(distance=5.0 / 1000)  # drop >5mm outliers
    log("second ICP pass (post outlier removal) ...")
    coreg.fit_icp(n_iterations=20, nasion_weight=10.0, verbose=False)

    dists = coreg.compute_dig_mri_distances() * 1e3  # meters -> mm
    log(f"final head-shape<->MRI distances: mean={np.mean(dists):.2f}mm "
        f"median={np.median(dists):.2f}mm max={np.max(dists):.2f}mm")

    mne.write_trans(fname_trans, coreg.trans)
    log(f"wrote {fname_trans}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    main(int(sys.argv[1]))
