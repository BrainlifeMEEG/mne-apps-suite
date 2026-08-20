#!/usr/bin/env python3
"""Compute MNE 0.12's highpass/lowpass filter impulse responses, for the
"old MNE" comparison curves in fig3_filter_response.py -- matching the
paper's original Figure 3 (MNE 0.12 vs >=0.16).

Must be run with an MNE 0.12 environment, NOT the main MNE 1.x env this
project otherwise uses. Old MNE needs old numpy/scipy internals that
current numpy has removed; the two compatibility shims below (np.float
alias, numpy.testing.dec stub) are the minimum needed to get mne==0.12.0
importing and running its filter functions under a *current* Python/numpy
(there's no cp3.10+/3.11 wheel history for numpy old enough to have these
natively, so patching current numpy is more practical than hunting for a
genuinely period-correct interpreter).

One-time environment setup (creates an isolated venv, does not touch the
project's main environment):
    python3 -m venv /tmp/mne012_venv
    /tmp/mne012_venv/bin/pip install numpy scipy
    /tmp/mne012_venv/bin/pip install --no-build-isolation mne==0.12.0

Then run this script with that venv's python:
    /tmp/mne012_venv/bin/python3 compute_old_mne_012_filters.py

Method: old MNE's high_pass_filter()/low_pass_filter() apply a filter to
a data array directly -- there's no standalone "give me the coefficients"
function like modern create_filter(). Filtering a unit impulse (a zero
array with a single 1 at its center) through any LTI filter yields
exactly that filter's impulse response, which is what we actually want
to plot (and its FFT gives the frequency response) -- works regardless
of old MNE's internal implementation (FFT overlap-add, in this case).
"""
import numpy as np

np.float = float  # removed alias old MNE's filter.py still references

import numpy.testing
import types
numpy.testing.dec = types.SimpleNamespace(skipif=lambda *a, **kw: (lambda f: f))  # old nose-based decorator, unused here

import mne  # noqa: E402

assert mne.__version__ == "0.12.0", f"expected mne 0.12.0, got {mne.__version__}"

SFREQ = 1100.0
L_FREQ = 1.0
H_FREQ = 40.0
FILTER_LENGTH = "10s"  # old MNE's default (vs modern's adaptive 'auto')
TRANS_BANDWIDTH = 0.5  # Hz, old MNE's default (vs modern's adaptive 'auto')

N = int(44 * SFREQ)  # comfortably > 2x the 10s filter length, avoids edge truncation
delta = np.zeros((1, N))
delta[0, N // 2] = 1.0

hp = mne.filter.high_pass_filter(
    delta.copy(), SFREQ, Fp=L_FREQ, filter_length=FILTER_LENGTH,
    trans_bandwidth=TRANS_BANDWIDTH, method="fft", verbose=False,
)[0]
lp = mne.filter.low_pass_filter(
    delta.copy(), SFREQ, Fp=H_FREQ, filter_length=FILTER_LENGTH,
    trans_bandwidth=TRANS_BANDWIDTH, method="fft", verbose=False,
)[0]

out_dir = __import__("pathlib").Path(__file__).parent / "old_mne_012_reference"
out_dir.mkdir(exist_ok=True)
np.save(out_dir / "highpass_impulse_response.npy", hp)
np.save(out_dir / "lowpass_impulse_response.npy", lp)
print(f"saved highpass ({hp.shape[0]} samples, peak @ {np.argmax(np.abs(hp))}) "
      f"and lowpass ({lp.shape[0]} samples, peak @ {np.argmax(np.abs(lp))}) to {out_dir}")
