"""
Per-subject adaptation of 15-lcmv_beamformer.py -- Figure 11's LCMV half
(dSPM is the other half, from 13-make_inverse.py).

Real rewrite, not an AST-strip of the verbatim original: the original calls
`mne.beamformer.lcmv(evoked, forward, noise_cov, data_cov, pick_ori=...,
max_ori_out=...)`, a single one-shot function that no longer exists in
current MNE at all (confirmed: `hasattr(mne.beamformer, 'lcmv')` is False).
Replaced with the modern two-step API: `make_lcmv()` builds a reusable
spatial filter, `apply_lcmv()` applies it to the evoked data. `max_ori_out`
(old API: whether max-power orientation output keeps its sign) has no
modern equivalent -- doesn't matter here since the original script already
wraps its result in `abs()`, which erases that sign distinction either way;
kept that same `abs()` wrapping. `weight_norm`/`reg` use current MNE's own
defaults (`unit-noise-gain-invariant`, 0.05) rather than chasing the old
API's different-shaped defaults -- a version-appropriate modernization, not
an attempt at bit-identical reproduction of a removed function.

`epochs[['face', 'scrambled']]` (hierarchical event-name selection, e.g.
'face' selects all 'face/famous/*' + 'face/unfamiliar/*' sub-conditions)
still works unchanged in current MNE -- confirmed against this project's
own events_id dict in 06-make_epochs.py.

Needs 12 (forward) done for this subject; independent of 13 (dSPM).

Usage: python3 run_subject_lcmv.py <openfmri_subject_id>
"""
import os
import sys
import time

import mne
from mne.beamformer import make_lcmv, apply_lcmv

HERE = os.path.dirname(os.path.abspath(__file__))
ORIGINAL_SCRIPTS = os.path.normpath(os.path.join(HERE, "..", "original_scripts"))
sys.path.insert(0, HERE)
sys.path.insert(0, ORIGINAL_SCRIPTS)

from crosswalk import EXCLUDED  # noqa: E402
from library.config import meg_dir, spacing, l_freq  # noqa: E402


def run_lcmv(subject_id):
    t0 = time.time()

    def log(msg):
        print(f"[{time.time() - t0:7.1f}s] {msg}", flush=True)

    if subject_id in EXCLUDED:
        log(f"subject_id {subject_id} excluded, nothing to do.")
        return

    subject = "sub%03d" % subject_id
    data_path = os.path.join(meg_dir, subject)

    fname_epo = os.path.join(data_path, f"{subject}_highpass-{l_freq}Hz-epo.fif")
    fname_ave = os.path.join(data_path, f"{subject}_highpass-{l_freq}Hz-ave.fif")
    fname_cov = os.path.join(data_path, f"{subject}_highpass-{l_freq}Hz-cov.fif")
    fname_fwd = os.path.join(data_path, f"{subject}-meg-eeg-{spacing}-fwd.fif")

    epochs = mne.read_epochs(fname_epo, preload=False)
    log(f"loaded epochs ({len(epochs)})")
    data_cov = mne.compute_covariance(
        epochs[["face", "scrambled"]], tmin=0.03, tmax=0.3, method="shrunk")
    log("data covariance computed")
    evoked = mne.read_evokeds(fname_ave, condition="contrast")
    noise_cov = mne.read_cov(fname_cov)
    forward = mne.read_forward_solution(fname_fwd)
    forward = mne.convert_forward_solution(forward, surf_ori=True)

    filters = make_lcmv(evoked.info, forward, data_cov, noise_cov=noise_cov,
                        pick_ori="max-power")
    log("LCMV spatial filter built")
    stc = apply_lcmv(evoked, filters)
    stc = abs(stc)  # matches the original script's own abs() wrapping
    out_path = os.path.join(data_path, f"mne_LCMV_inverse_highpass-{l_freq}Hz-contrast")
    stc.save(out_path, overwrite=True)
    log(f"saved {out_path}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    run_lcmv(int(sys.argv[1]))
