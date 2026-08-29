"""
One-time (not per-subject) fsaverage setup, needed as the morph target for
14/16-group_average_source*.py. Adapted from the tail of 01-anatomy.py.

Deviation from the original: symlinks fsaverage's individual mri/surf/label/
bem files into our project-local subjects_dir (matching every other
subject's file-level-symlink setup, see run_subject_anatomy.py's docstring)
instead of a full `shutil.copytree` of $FREESURFER_HOME/subjects/fsaverage
(the original script's approach -- copies because it needs to *write* into
fsaverage's own bem/ dir, which a directory-level symlink farm can't do
without touching the shared FreeSurfer install; a file-level symlink
achieves the same writability without duplicating ~700MB of template data).

Usage: python3 setup_fsaverage.py
"""
import os
import sys

import numpy as np
import mne

HERE = os.path.dirname(os.path.abspath(__file__))
ORIGINAL_SCRIPTS = os.path.normpath(os.path.join(HERE, "..", "original_scripts"))
sys.path.insert(0, ORIGINAL_SCRIPTS)
from library.config import subjects_dir  # noqa: E402

fs_home = os.environ.get("FREESURFER_HOME")
if not fs_home:
    raise RuntimeError("FREESURFER_HOME not set -- module load FreeSurfer/7.4.1 first")

src_root = os.path.join(fs_home, "subjects", "fsaverage")
dst_root = os.path.join(subjects_dir, "fsaverage")

for sub in ("mri", "surf", "label"):
    src_dir = os.path.join(src_root, sub)
    dst_dir = os.path.join(dst_root, sub)
    os.makedirs(dst_dir, exist_ok=True)
    for f in os.listdir(src_dir):
        dst_f = os.path.join(dst_dir, f)
        if not os.path.exists(dst_f):
            os.symlink(os.path.join(src_dir, f), dst_f)
os.makedirs(os.path.join(dst_root, "bem"), exist_ok=True)
print(f"fsaverage linked into {dst_root}")

fsaverage_src = os.path.join(dst_root, "bem", "fsaverage-5-src.fif")
if not os.path.isfile(fsaverage_src):
    print("setting up source space for fsaverage (ico5) ...")
    src = mne.setup_source_space("fsaverage", "ico5", subjects_dir=subjects_dir)
    for s in src:
        assert np.array_equal(s["vertno"], np.arange(10242))
    mne.write_source_spaces(fsaverage_src, src)
    print("fsaverage source space written")
else:
    print("fsaverage source space already exists")
