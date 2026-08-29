"""
Real FLASH-based BEM extraction (`mne.bem.convert_flash_mris` +
`mne.bem.make_flash_bem`) for ONE subject -- the paper's own, literal
method (`original_scripts/01-anatomy.py`'s "Make BEMs" section), not the
watershed substitute `run_subject_anatomy.py` uses for the full 16-subject
group pipeline.

Why this exists (correction to a standing project claim, 2026-08-29): both
`run_subject_anatomy.py`'s docstring and `GLITCHES.md` asserted FLASH MRI
is "confirmed absent" from this ds000117 release, based on
`find ... -iname "*flash*"` over `study_path/ds117/*/anatomy/` -- that tree
is an empty, never-populated scaffold (00-fetch_data.py was skipped
project-wide, Step 0), so the search always would have found nothing there
regardless of whether FLASH data exists. It does: the REAL, actually
downloaded BIDS dataset
(`/network/iss/cenir/analyse/meeg/BRAINLIFE/datasets/ds000117/sub-NN/ses-mri/anat/`)
ships complete multi-echo FLASH data for every one of this project's 16
subjects -- 14 files each, `run-1_echo-{1..7}_FLASH.nii.gz` (5 degree flip
angle per the dataset's own sidecar JSON) and `run-2_echo-{1..7}_FLASH.nii.gz`
(30 degree) -- verified directly, not assumed, before writing this script.

Scope, deliberately narrow: this script is used for exactly the two
subjects Figures 8/9 illustrate (sub004 = paper "subject 4", sub010 = this
project's "S09" reference subject), NOT the full 16-subject group
pipeline. Justification: 12-make_forward.py only ever reads the 1-layer
(inner-skull-only) BEM solution (see run_subject_anatomy.py's docstring --
the 3-layer FLASH BEM was already "unreliable" per the original script's
own comment, and every forward/inverse call here is MEG-only), and
coregistration doesn't fit against the outer-skin/head surface either
(hsp_weight=0, see run_subject_coreg.py's docstring) -- so the
outer_skull/outer_skin quality problem visible in Figure 8 (nearly
coincident surfaces) has never affected any already-computed forward/
inverse/LCMV result. It is a Figure 8/9 visual-fidelity problem only,
which is exactly the two subjects this script touches.

One real remaining gap, handled here: `make_flash_bem` requires
`mri/brain.mgz` (skull-stripped brain volume, a standard recon-all
product) to exist -- our partial recon-all derivatives don't ship it (only
`mri/{T1,aseg}.mgz`, see run_subject_anatomy.py's docstring). Synthesized
here as `T1.mgz` masked by `aseg.mgz > 0` -- aseg IS a real FreeSurfer
segmentation already computed for these subjects (not a guess), so this is
a documented, reasonable substitute for the missing skull-strip step, same
class of substitution as the `sphere.reg` -> `sphere` symlink already used
in `run_subject_anatomy.py`.

Toolchain: needs both FreeSurfer (`mri_convert`, `mri_ms_fitparms`,
`mri_synthesize`, `mri_make_bem_surfaces` -- same module as
`run_subject_anatomy.py`'s `mri_watershed`) AND FSL (`fsl_rigid_register`,
for the flash5-to-T1 registration step) on PATH. Not loaded here --
caller's job (see `run_flash_bem.sh` wrapper) must `module load
FreeSurfer/7.4.1` and `module load FSL/6.0.7.15` first.

Usage: python3 run_subject_flash_bem.py <openfmri_subject_id>
"""
import os
import sys
import time

import mne
import nibabel as nib
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ORIGINAL_SCRIPTS = os.path.normpath(os.path.join(HERE, "..", "original_scripts"))
DATASETS_ANAT = "/network/iss/cenir/analyse/meeg/BRAINLIFE/datasets/ds000117"
sys.path.insert(0, HERE)
sys.path.insert(0, ORIGINAL_SCRIPTS)

from crosswalk import bids_id  # noqa: E402
from library.config import subjects_dir  # noqa: E402


def rss_gb():
    import resource
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6


def main(subject_id):
    t0 = time.time()

    def log(msg):
        print(f"[{time.time() - t0:7.1f}s][mem {rss_gb():.2f}GB] {msg}", flush=True)

    subject = "sub%03d" % subject_id
    bids = bids_id(subject_id)
    subject_dir = os.path.join(subjects_dir, subject)
    mri_dir = os.path.join(subject_dir, "mri")
    if not os.path.isdir(subject_dir):
        raise RuntimeError(f"{subject_dir} missing -- run run_subject_anatomy.py first")

    anat_dir = os.path.join(DATASETS_ANAT, bids, "ses-mri", "anat")

    def flash_files(run):
        files = {}
        for fname in os.listdir(anat_dir):
            marker = f"run-{run}_echo-"
            if marker in fname and fname.endswith("_FLASH.nii.gz"):
                echo = int(fname.split("echo-")[1].split("_")[0])
                files[echo] = os.path.join(anat_dir, fname)
        if len(files) != 7:
            raise RuntimeError(f"expected 7 echoes for run-{run}, found {len(files)} in {anat_dir}")
        return [files[e] for e in sorted(files)]

    flash5_files = flash_files(1)   # 5 degree flip angle
    flash30_files = flash_files(2)  # 30 degree flip angle
    log(f"found {len(flash5_files)} flash5 + {len(flash30_files)} flash30 echoes in {anat_dir}")

    # 1) Synthesize mri/brain.mgz (see docstring) -- required by make_flash_bem,
    # not present in our partial recon-all derivatives.
    fname_brain = os.path.join(mri_dir, "brain.mgz")
    if os.path.isfile(fname_brain):
        log("brain.mgz already exists, skipping synthesis")
    else:
        log("synthesizing brain.mgz from T1.mgz masked by aseg.mgz>0 ...")
        t1_img = nib.load(os.path.join(mri_dir, "T1.mgz"))
        aseg_img = nib.load(os.path.join(mri_dir, "aseg.mgz"))
        t1_data = np.asanyarray(t1_img.dataobj)
        aseg_data = np.asanyarray(aseg_img.dataobj)
        brain_data = np.where(aseg_data > 0, t1_data, 0).astype(t1_data.dtype)
        brain_img = nib.MGHImage(brain_data, t1_img.affine, t1_img.header)
        nib.save(brain_img, fname_brain)
        log("brain.mgz written")

    # 2) Pre-convert each echo to mgz via `mri_convert`, explicitly stamping
    # TR/TE/flip-angle into the header (from this dataset's own FLASH sidecar
    # JSONs: TR=20ms, TE=1.85ms, FlipAngle=5 or 30 degrees). Required: passing
    # raw NIfTI paths straight to `convert_flash_mris(flash5=[...])` lets it
    # do a naive nibabel load/save (no TR/FA/TE) -- `mri_ms_fitparms` then
    # fails with "invalid TR or FA for image 0" (hit for real, first attempt
    # here). `mri_convert`'s own `-tr`/-te`/`-flip_angle` flags are the
    # documented way to embed this metadata into an mgz header; `flip_angle`
    # wants radians, not degrees.
    fname_flash5 = os.path.join(mri_dir, "flash", "parameter_maps", "flash5.mgz")
    if os.path.isfile(fname_flash5):
        log("flash5.mgz already exists, skipping convert_flash_mris")
    else:
        import math
        import subprocess
        flash_mri_dir = os.path.join(mri_dir, "flash")
        os.makedirs(flash_mri_dir, exist_ok=True)
        for angle_deg, angle_tag, files in ((5, "05", flash5_files), (30, "30", flash30_files)):
            flip_rad = math.radians(angle_deg)
            for idx, src in enumerate(files, 1):
                dst = os.path.join(flash_mri_dir, f"mef{angle_tag}_{idx:03d}.mgz")
                subprocess.run(
                    ["mri_convert", "-tr", "20", "-te", "1.85",
                     "-flip_angle", f"{flip_rad:.6f}", src, dst],
                    check=True, capture_output=True, text=True)
        log("pre-converted 14 FLASH echoes to mgz with TR/TE/flip-angle headers")

        log("running convert_flash_mris (mri_ms_fitparms + mri_synthesize) ...")
        mne.bem.convert_flash_mris(
            subject, flash5=True, flash30=True,
            subjects_dir=subjects_dir, verbose=False)
        log("convert_flash_mris done")

    # 3) make_flash_bem: register flash5 to T1 (fsl_rigid_register), extract
    # inner_skull/outer_skull/outer_skin (mri_make_bem_surfaces). Overwrites
    # the watershed-derived bem/{surf}.surf files this subject already has.
    log("running make_flash_bem (fsl_rigid_register + mri_make_bem_surfaces) ...")
    mne.bem.make_flash_bem(subject, overwrite=True, show=False, subjects_dir=subjects_dir, verbose=False)
    log("make_flash_bem done")

    log(f"subject {subject_id} FLASH BEM DONE")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    main(int(sys.argv[1]))
