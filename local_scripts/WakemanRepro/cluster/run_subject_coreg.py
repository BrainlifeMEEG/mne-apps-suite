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
coregistration. This is the standard, well-documented substitute for
manual `mne coreg` when no pre-existing trans is available -- the same
approach MNE-BIDS-pipeline itself defaults to.

**Real, dataset-wide bug found and fixed here (2026-08-29), not the
original recipe below** -- flagged by the user visually on Figure 9 (a
~30-45 degree helmet tilt) and confirmed numerically (38.7 degree pitch on
S09, computed from the written trans matrix's Euler angles). Root cause,
verified with real data, not guessed:
  - This dataset's "extra" head-shape digitization points are confirmed,
    across every subject checked (S02/S04/S09/S15), to cover ONLY the
    anterior/facial region (head-frame Y >= ~0.05m -- essentially zero
    posterior or lateral coverage at all). That's squarely the region
    `run_subject_anatomy.py`'s docstring already documents as corrupted by
    this dataset's MRI defacing.
  - Consequence: `fit_icp()`'s head-shape-to-scalp-surface matching has
    *only* corrupted-region points to work with -- confirmed it's not an
    initialization problem (tried ICP from both the fiducial-based initial
    guess and from identity; both converged to a similarly large,
    ~40-degree pitch), it's a genuine bad local optimum given the only
    available matching data sits on a distorted part of the mesh.
  - The nasion fiducial (front of face) has the same problem one level up:
    with `nasion_weight` at any nonzero value (tested 10, 1, 0.1, 0.01),
    `fit_fiducials()` alone already gives ~23 degrees of pitch; at exactly
    `nasion_weight=0` it drops to ~0 degrees -- a clean on/off effect, not
    a gradual one, pointing straight at the nasion constraint itself as
    the problem, not a weighting-balance issue.
  - Fix: exclude the nasion fiducial and all head-shape points from
    fitting entirely (`nasion_weight=0` throughout, no head-shape ICP
    matching) -- rely only on LPA/RPA, which sit near the ears and aren't
    touched by facial defacing. Confirmed this brings S09 down to a few
    degrees of residual rotation on every axis (physically normal for a
    seated recording), not just the one axis originally flagged.
  - This is dataset-wide, not S09-specific (same all-anterior head-shape
    pattern confirmed on 3 other subjects) -- applied uniformly below, not
    special-cased to one subject.
  - **Second bug found running this fix across all 16 subjects**: 7 of 16
    (S03/S04/S07/S12/S15/S17/S19) came out with ~160-176 degree pitch --
    essentially upside-down. Root cause: LPA+RPA alone are only 2 points,
    which under-determine a rigid transform -- specifically, roll around
    the LPA-RPA axis itself is left completely unconstrained (a 180-degree
    roll leaves both points exactly fixed in place, since they sit ON that
    axis by definition of the head coordinate system). The optimizer picks
    whichever of the two equally-valid-to-LPA/RPA solutions it lands on --
    a genuine mathematical ambiguity, not a numerical fluke, and it's why
    excluding nasion entirely (the fix above) trades one real bug for
    another. Fixed with a coarse, sign-only disambiguation instead of a
    position fit: after the LPA/RPA-only ICP result, the *digitized*
    (head-frame) nasion is transformed through the fitted trans into MRI
    space and checked for whether it lands anterior (Y>0) or posterior
    (Y<0) in FreeSurfer's own surface-RAS convention (Y+ is always
    anterior there, a fixed geometric fact independent of any
    subject-specific fiducial estimate). If posterior, a 180-degree
    rotation around the fitted LPA-RPA axis is applied to correct it --
    confirmed this only flips the ambiguous roll DOF and leaves LPA/RPA
    exactly where ICP put them (they're the rotation axis). This uses the
    nasion only as a binary direction check, not a metric position
    constraint -- much more robust to defacing-driven imprecision than
    fitting to its exact coordinates would be, while still resolving a
    real ambiguity that pure LPA/RPA fitting can't.

Needs `<subject>-head.fif` (the low-res head surface `make_watershed_bem`
already writes as part of run_subject_anatomy.py, `copy=True` default) --
run anatomy before coreg for a given subject.

Usage: python3 run_subject_coreg.py <openfmri_subject_id>
"""
import math
import os
import sys
import time

import numpy as np
import mne
from mne.coreg import Coregistration


def _euler_deg(trans_mat):
    """Extrinsic XYZ Euler angles (degrees) of a 3x3/4x4 rotation matrix --
    pitch (X), yaw (Y), roll (Z). Used as the real fit-quality signal here
    (head-shape point distances aren't meaningful once those points are
    excluded from fitting, see docstring) -- a seated MEG recording should
    show at most a few degrees on each axis; anything like the ~39 degree
    pitch this caught originally is a real red flag, not normal variation.
    """
    R = np.asarray(trans_mat)[:3, :3]
    sy = math.sqrt(R[0, 0] ** 2 + R[1, 0] ** 2)
    if sy >= 1e-6:
        x = math.atan2(R[2, 1], R[2, 2])
        y = math.atan2(-R[2, 0], sy)
        z = math.atan2(R[1, 0], R[0, 0])
    else:
        x = math.atan2(-R[1, 2], R[1, 1])
        y = math.atan2(-R[2, 0], sy)
        z = 0.0
    return math.degrees(x), math.degrees(y), math.degrees(z)

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
    log("fitting fiducials (nasion excluded, see docstring) ...")
    coreg.fit_fiducials(nasion_weight=0.0, verbose=False)
    log("ICP refinement (LPA/RPA only -- nasion + all head-shape points excluded) ...")
    coreg.fit_icp(n_iterations=30, lpa_weight=1.0, nasion_weight=0.0, rpa_weight=1.0,
                 hsp_weight=0.0, verbose=False)

    dists = coreg.compute_dig_mri_distances() * 1e3  # meters -> mm
    log(f"head-shape<->MRI distances (not a meaningful QC signal here -- these points are "
        f"excluded from fitting, see docstring): mean={np.mean(dists):.2f}mm "
        f"median={np.median(dists):.2f}mm max={np.max(dists):.2f}mm")

    # Roll-around-LPA/RPA-axis disambiguation (see docstring's "Second bug"
    # section) -- LPA/RPA alone leave this DOF unconstrained, so check which
    # of the two equally-valid solutions this converged to using the
    # digitized nasion as a coarse sign check (not a position fit). Builds a
    # corrected Transform directly rather than mutating `coreg`'s internal
    # state -- `Coregistration.trans` reads from a separately-cached
    # `_head_mri_t` attribute, not recomputed from `_parameters` on access
    # (confirmed by reading its source), so editing `_parameters` alone
    # would silently not take effect.
    trans_mat = coreg.trans["trans"].copy()
    nasion_head = next(d["r"] for d in info["dig"]
                       if d["kind"] == mne.io.constants.FIFF.FIFFV_POINT_CARDINAL and d["ident"] == 2)
    nasion_mri = trans_mat[:3, :3] @ nasion_head + trans_mat[:3, 3]
    if nasion_mri[1] < 0:  # posterior in FreeSurfer surface-RAS -> flipped
        log(f"nasion lands posterior (Y={nasion_mri[1]:.3f}m) after LPA/RPA-only fit -- "
            "flipped solution, correcting with a 180deg roll around the LPA-RPA axis")
        Rx180 = np.diag([1.0, -1.0, -1.0])  # leaves LPA/RPA (on this axis) fixed
        trans_mat[:3, :3] = trans_mat[:3, :3] @ Rx180
    final_trans = mne.Transform("head", "mri", trans_mat)  # top-level export --
    # mne.transforms.Transform needs an explicit `import mne.transforms` first
    # due to lazy loading (same class of issue as mne.evoked elsewhere in
    # this project), mne.Transform avoids it

    pitch, yaw, roll = _euler_deg(trans_mat)
    log(f"fit rotation (the real QC signal): pitch={pitch:.1f}deg yaw={yaw:.1f}deg "
        f"roll={roll:.1f}deg")
    if max(abs(pitch), abs(yaw), abs(roll)) > 15:
        log("WARNING: rotation exceeds 15 degrees on at least one axis -- physically unusual "
            "for a seated recording, worth a visual check via jas_fig9_coregistration.py")

    mne.write_trans(fname_trans, final_trans)
    log(f"wrote {fname_trans}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    main(int(sys.argv[1]))
