"""
Per-subject adaptation of 01-anatomy.py (Figures 8/9/11/12's anatomical
prerequisites): BEM surfaces + BEM model/solution + source space.

Real deviations from the original script, both forced by what this specific
ds000117 BIDS release actually ships (checked directly, not assumed):

- **No `recon-all -all` run.** The original script runs a full multi-hour
  FreeSurfer reconstruction per subject. ds000117's own
  `derivatives/freesurfer/sub-XX/ses-mri/anat/` already ships a *partial*
  recon-all output per subject -- `mri/{T1,aseg}.mgz`,
  `surf/{lh,rh}.{pial,white,sphere.reg}`, `label/*.annot` -- confirmed by
  directory listing, no `orig.mgz`/`brain.mgz`/`wm.mgz`/inflated surfaces,
  so genuinely partial, but exactly the pieces this pipeline's own
  downstream scripts (`make_bem_model`, `setup_source_space`,
  `compute_source_morph`) actually read. Matches this project's established
  "bridge to already-downloaded/available data" precedent (00-fetch_data.py
  was skipped the same way, Step 0).
- **No `<hemi>.sphere` (only `<hemi>.sphere.reg`).** `setup_source_space()`
  needs the subject's own natural inflated-sphere surface (`mris_sphere`'s
  output) to distribute oct/ico source points evenly -- ds000117's
  FreeSurfer derivatives only ship the *registered* sphere (`sphere.reg`,
  aligned to the fsaverage template, used for morphing) -- confirmed by
  directory listing, `sphere` genuinely absent. Symlinked `sphere.reg` as
  a stand-in: both are valid closed spherical meshes with the same
  topology/vertex count, just differently deformed (natural inflation vs.
  template-registered) -- geometrically valid input to the same algorithm,
  not identical to a real `mris_sphere` run. Verified empirically, not
  just assumed to work: the resulting oct6 source space has exactly
  4098 vertices/hemisphere, the correct count for this spacing -- a
  broken/degenerate substitute would very likely have produced something
  visibly wrong here (crash, or an obviously-off vertex count), not this.
- **Watershed BEM used for the 16-subject group pipeline** (`mne.bem.make_watershed_bem()`,
  FreeSurfer's `mri_watershed`, needs only `mri/T1.mgz`, present) rather than
  `convert_flash_mris`/`make_flash_bem`. CORRECTION (2026-08-29, see GLITCHES.md's "FLASH MRI was
  never actually absent" section): this was originally justified by "FLASH multi-echo MRI is
  confirmed absent from this dataset" -- that claim was WRONG. The `find` check behind it searched
  `ds117/*/anatomy/`, a scaffold directory this project never populated (00-fetch_data.py was
  skipped, Step 0) -- it would have found nothing there regardless. FLASH data is actually present
  for every subject in the real downloaded BIDS tree
  (`datasets/ds000117/sub-NN/ses-mri/anat/*_FLASH.nii.gz`), just as git-annex symlinks whose
  content hadn't been fetched yet. `cluster/run_subject_flash_bem.py` now builds the real FLASH BEM
  for the two subjects Figures 8/9 illustrate (sub004, sub010) -- watershed remains in use here,
  for the full 16-subject group pipeline, because forward/inverse only ever reads the 1-layer
  (inner-skull-only) solution and coregistration doesn't use the outer-skin surface either
  (`hsp_weight=0`), so watershed's own known outer_skull/outer_skin quality issue has never affected
  any group-level scientific result -- only Figure 8/9's own visual fidelity, which is what
  `run_subject_flash_bem.py` fixes for those two illustration subjects specifically.
- **Only the 1-layer BEM model/solution is built** (conductivity=(0.3,)),
  not the 3-layer one the original script also builds. `12-make_forward.py`
  only ever reads the 1-layer solution anyway -- its own comment says the
  3-layer BEM "is unreliable" (that's about the FLASH-derived 3-layer
  specifically) and every downstream forward/inverse call is MEG-only
  (`eeg=False`), so the 3-layer solution is pure unused compute here. The
  3 watershed surfaces (inner_skull/outer_skull/outer_skin) still get
  produced regardless -- Figure 8 (BEM surfaces on MRI) only needs the raw
  surfaces, not a conductor model, so this doesn't cost anything there.
- **No `mri/transforms/talairach.xfm`.** Found only once coregistration
  actually needed it: `mne.coreg.Coregistration`'s default fiducial
  estimation (`get_mni_fiducials()`) reads this FreeSurfer file (the
  affine registration to the MNI305 atlas -- also a standard recon-all
  substep we don't have, since we skip `-all`). Generated directly here
  via FreeSurfer's own `talairach_avi` binary on `mri/T1.mgz` -- confirmed
  fast (~25s/subject, not a real recon-all substep's usual cost) since
  it's a coarse 12-parameter affine search, not a full nonlinear warp.
- **subjects_dir is NOT the raw `ds000117/derivatives/freesurfer/` tree.**
  Rebuilt as a project-local dir per subject
  (`derivatives/biomag_repro/subjects/subXXX/`) with `mri/`, `surf/`,
  `label/` populated by FILE-level symlinks into the read-only dataset
  copy, and a real (non-symlinked) `bem/` -- every write this script (and
  every later source-space script) makes lands in project space, never in
  the shared `datasets/` tree. The original directory-level symlink farm
  (`subXXX -> .../sub-YY/ses-mri/anat`) would have written straight into
  that shared, not-ours dataset directory; rebuilt once, before this script
  was ever run, not per-invocation.

Runs `make_watershed_bem` with `overwrite=False` (idempotent -- skip if a
subject's watershed surfaces already exist, matches this project's general
low-friction-rerun convention) and `SourceSpaces`/`BEM solution` writes
guarded with an existence check the same way the original script's own
`if not op.isfile(...)` guards work (kept, not removed).

Usage: python3 run_subject_anatomy.py <openfmri_subject_id>
"""
import os
import sys
import time

import mne

HERE = os.path.dirname(os.path.abspath(__file__))
ORIGINAL_SCRIPTS = os.path.normpath(os.path.join(HERE, "..", "original_scripts"))
sys.path.insert(0, HERE)
sys.path.insert(0, ORIGINAL_SCRIPTS)

from crosswalk import EXCLUDED  # noqa: E402
from library.config import subjects_dir, spacing  # noqa: E402


def rss_gb():
    import resource
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6


def main(subject_id):
    t0 = time.time()

    def log(msg):
        print(f"[{time.time() - t0:7.1f}s][mem {rss_gb():.2f}GB] {msg}", flush=True)

    if subject_id in EXCLUDED:
        log(f"subject_id {subject_id} excluded, nothing to do.")
        return

    subject = "sub%03d" % subject_id
    subject_dir = os.path.join(subjects_dir, subject)
    if not os.path.isdir(subject_dir):
        raise RuntimeError(f"{subject_dir} missing -- subjects_dir symlink farm not built for this subject")

    # 1) Watershed BEM surfaces (inner_skull/outer_skull/outer_skin), needs
    # only mri/T1.mgz. Skip if already done (mri_watershed takes a few
    # minutes; this script may be re-run after a partial failure).
    fname_outer_skin = os.path.join(subject_dir, "bem", "watershed", f"{subject}_outer_skin_surface")
    if os.path.isfile(fname_outer_skin):
        log("watershed BEM already exists, skipping make_watershed_bem")
    else:
        log("running make_watershed_bem (mri_watershed) ...")
        mne.bem.make_watershed_bem(subject, subjects_dir=subjects_dir, overwrite=False, show=False)
        log("make_watershed_bem done")

    # 2) 1-layer BEM model + solution (MEG-only forward/inverse downstream
    # only ever reads this one -- see docstring above).
    fname_bem_surfaces = os.path.join(subject_dir, "bem", f"{subject}-5120-bem.fif")
    if not os.path.isfile(fname_bem_surfaces):
        log("building 1-layer BEM model ...")
        bem_surfaces = mne.make_bem_model(subject, ico=4, conductivity=(0.3,), subjects_dir=subjects_dir)
        mne.write_bem_surfaces(fname_bem_surfaces, bem_surfaces)
        log("BEM model written")
    fname_bem = os.path.join(subject_dir, "bem", f"{subject}-5120-bem-sol.fif")
    if not os.path.isfile(fname_bem):
        log("computing 1-layer BEM solution ...")
        bem_model = mne.read_bem_surfaces(fname_bem_surfaces)
        bem = mne.make_bem_solution(bem_model)
        mne.write_bem_solution(fname_bem, bem)
        log("BEM solution written")

    # 3) Talairach (MNI305) affine registration -- needed by
    # Coregistration's default MNI-based fiducial estimation. Not part of
    # `make_watershed_bem`/`make_bem_model`, a separate FreeSurfer call.
    fname_talxfm = os.path.join(subject_dir, "mri", "transforms", "talairach.xfm")
    if not os.path.isfile(fname_talxfm):
        import subprocess
        log("running talairach_avi (MNI305 affine registration) ...")
        os.makedirs(os.path.dirname(fname_talxfm), exist_ok=True)
        subprocess.run(
            ["talairach_avi", "--i", os.path.join(subject_dir, "mri", "T1.mgz"),
             "--xfm", fname_talxfm],
            check=True, cwd=subject_dir,
            stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        log("talairach_avi done")

    # sphere.reg -> sphere stand-in (see docstring). Symlink, not a copy --
    # cheap, and keeps the substitution visible/inspectable on disk.
    for hemi in ("lh", "rh"):
        sphere_path = os.path.join(subject_dir, "surf", f"{hemi}.sphere")
        sphere_reg_path = os.path.join(subject_dir, "surf", f"{hemi}.sphere.reg")
        if not os.path.exists(sphere_path) and os.path.isfile(sphere_reg_path):
            os.symlink(f"{hemi}.sphere.reg", sphere_path)
            log(f"linked {hemi}.sphere -> {hemi}.sphere.reg (see docstring)")

    # 4) Source space (surface-based, spacing from config -- 'oct6').
    fname_src = os.path.join(subject_dir, "bem", f"{subject}-{spacing}-src.fif")
    if not os.path.isfile(fname_src):
        log(f"setting up source space ({spacing}) ...")
        src = mne.setup_source_space(subject, spacing, subjects_dir=subjects_dir)
        mne.write_source_spaces(fname_src, src)
        log("source space written")

    log(f"subject {subject_id} anatomy DONE")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    main(int(sys.argv[1]))
