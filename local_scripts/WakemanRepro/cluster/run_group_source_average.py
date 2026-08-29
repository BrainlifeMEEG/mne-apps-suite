"""
Adapted 14-group_average_source.py + 16-group_average_lcmv.py, combined and
rewritten. Run once, after all 16 subjects have 13 (dSPM) and 15 (LCMV) done.

Real rewrites, not AST-strips of the verbatim originals:
- `mne.compute_morph_matrix()` + `stc.morph_precomputed()` no longer exist in
  current MNE at all (confirmed, see GLITCHES.md's Step 0 audit) -- replaced
  with `mne.compute_source_morph(stc, subject_from=subject,
  subject_to='fsaverage', spacing=fsaverage_vertices, smooth=smooth,
  subjects_dir=subjects_dir).apply(stc)`, the modern equivalent
  (`spacing=fsaverage_vertices` -- a list of two `arange(10242)` vertex
  arrays -- reproduces the same ico5 target vertex set the original's
  `fsaverage_vertices` constant specified, not a different morph target).
- 14's original per-subject loop (`for subject_id in range(1, 20)`) has no
  `if subject_id in exclude_subjects: continue` guard -- unlike every other
  per-subject script in this pipeline (including 16, right next to it) --
  so run as originally written it would crash trying to load nonexistent
  files for the 3 excluded subjects. Fixed to skip them from the start,
  matching 16's own (correct) pattern right next to it.
- `stc.save()` needs `overwrite=True` (current MNE default `overwrite=False`,
  neither original script passes it) -- same pattern as every other
  overwrite-gap fix already documented in GLITCHES.md.

Usage: python3 run_group_source_average.py
"""
import os
import sys
import time

import numpy as np
import mne

HERE = os.path.dirname(os.path.abspath(__file__))
ORIGINAL_SCRIPTS = os.path.normpath(os.path.join(HERE, "..", "original_scripts"))
sys.path.insert(0, HERE)
sys.path.insert(0, ORIGINAL_SCRIPTS)

from crosswalk import EXCLUDED  # noqa: E402
from library.config import (meg_dir, subjects_dir, smooth, fsaverage_vertices,
                            l_freq)  # noqa: E402

t0 = time.time()


def log(msg):
    print(f"[{time.time() - t0:7.1f}s] {msg}", flush=True)


def morph(stc, subject):
    morph_obj = mne.compute_source_morph(
        stc, subject_from=subject, subject_to="fsaverage",
        spacing=fsaverage_vertices, smooth=smooth, subjects_dir=subjects_dir)
    return morph_obj.apply(stc)


# --- 14: dSPM group average (vector source estimates) ---
dspm_contrast_stcs = []
for subject_id in range(1, 20):
    if subject_id in EXCLUDED:
        continue
    subject = "sub%03d" % subject_id
    log(f"dSPM morph: {subject}")
    data_path = os.path.join(meg_dir, subject)
    out = None
    for condition in ("contrast", "faces_eq", "scrambled_eq"):
        stc = mne.read_source_estimate(
            os.path.join(data_path, f"mne_dSPM_inverse_highpass-{l_freq}Hz-{condition}"),
            subject)
        morphed = morph(stc, subject)
        morphed.save(
            os.path.join(data_path, f"mne_dSPM_inverse_morph_highpass-{l_freq}Hz-{condition}"),
            overwrite=True)
        if condition == "contrast":
            out = morphed
    dspm_contrast_stcs.append(out)

data = np.average([s.data for s in dspm_contrast_stcs], axis=0)
stc = mne.VectorSourceEstimate(
    data, dspm_contrast_stcs[0].vertices, dspm_contrast_stcs[0].tmin,
    dspm_contrast_stcs[0].tstep, dspm_contrast_stcs[0].subject)
out_path = os.path.join(meg_dir, f"contrast-average_highpass-{l_freq}Hz")
stc.save(out_path, overwrite=True)
log(f"saved dSPM group average: {out_path} ({len(dspm_contrast_stcs)} subjects)")

# --- 16: LCMV group average (scalar source estimates) ---
lcmv_stcs = []
for subject_id in range(1, 20):
    if subject_id in EXCLUDED:
        continue
    subject = "sub%03d" % subject_id
    log(f"LCMV morph: {subject}")
    data_path = os.path.join(meg_dir, subject)
    stc = mne.read_source_estimate(
        os.path.join(data_path, f"mne_LCMV_inverse_highpass-{l_freq}Hz-contrast"), subject)
    lcmv_stcs.append(morph(stc, subject))

data = np.average([s.data for s in lcmv_stcs], axis=0)
stc = mne.SourceEstimate(data, lcmv_stcs[0].vertices, lcmv_stcs[0].tmin, lcmv_stcs[0].tstep)
out_path = os.path.join(meg_dir, f"contrast-average-lcmv_highpass-{l_freq}Hz")
stc.save(out_path, overwrite=True)
log(f"saved LCMV group average: {out_path} ({len(lcmv_stcs)} subjects)")
