#!/usr/bin/env python3
"""Find the best-matching coronal slice index (per panel) for Jas et al.
2018 Figure 8, by rendering a sweep of coronal BEM-contour slices for
sub004 and comparing each against the 4 reference panels pixel-wise.

Why this exists: the user is confident all 4 published panels are coronal
(posterior to anterior), contradicting what panel 1 visually looked like on
inspection (no neck/jaw in view -- axial-looking). Rather than resolve that
by eye a second time, this does it empirically: sweep a wide range of
coronal slice indices, score each against each reference panel with a
normalized sum-of-squares metric, and let the numbers pick the slice index
-- the same "verify numerically, don't just eyeball it" discipline used for
the Figure 9 coregistration tilt bug (see run_subject_coreg.py).

Rendered on `mri/flash/parameter_maps/flash5_reg.mgz` (the FLASH-derived,
T1-registered volume), not plain T1.mgz -- the paper's own Figure 8 caption
says "on flash MRI images", and this project now has a real FLASH BEM for
sub004 (see run_subject_flash_bem.py) to match that with.

Metric: both the candidate render (cropped tight to its black-background
MRI content, orientation/index labels turned off) and each reference panel
are grayscale, z-score normalized (zero mean, unit variance) then resized
to a common shape, so overall brightness/contrast differences between a
matplotlib render and a JPEG-compressed published figure don't dominate the
score -- then mean squared difference ("sum of squares", normalized by
pixel count so it's comparable across panels of different native size).

Output: `jas_fig8_slice_search.png` -- top: reference figure; middle: our
best-matched coronal slices at the same 4 positions; bottom: one
score-vs-slice-index curve per panel, with the chosen minimum marked.
"""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

import mne

HERE = os.path.dirname(os.path.abspath(__file__))
ORIGINAL_SCRIPTS = os.path.normpath(os.path.join(HERE, "..", "original_scripts"))
sys.path.insert(0, ORIGINAL_SCRIPTS)
from library.config import subjects_dir  # noqa: E402

SUBJECT = "sub004"
REFERENCE = os.path.join(HERE, "paper_figure8_reference.png")
FLASH5_REG = os.path.join(subjects_dir, SUBJECT, "mri", "flash", "parameter_maps", "flash5_reg.mgz")
TMP_DIR = os.path.join(HERE, "_tmp_fig8_slice_search")
os.makedirs(TMP_DIR, exist_ok=True)

CANDIDATE_INDICES = list(range(15, 245, 3))
TARGET_SHAPE = (200, 200)  # (rows, cols) for the normalized comparison


def crop_tight(im):
    """Crop a PIL RGB image to the bounding box of its non-white pixels
    (removes matplotlib's white figure margin, keeps the black-background
    MRI panel exactly as MNE drew it)."""
    arr = np.asarray(im)
    nonwhite = np.any(arr < 250, axis=2)
    rows = np.where(nonwhite.any(axis=1))[0]
    cols = np.where(nonwhite.any(axis=0))[0]
    if len(rows) == 0 or len(cols) == 0:
        return im
    return im.crop((cols[0], rows[0], cols[-1] + 1, rows[-1] + 1))


def norm_gray(arr, shape=TARGET_SHAPE):
    im = Image.fromarray(arr.astype(np.uint8)).resize((shape[1], shape[0]))
    a = np.asarray(im, dtype=float)
    a = (a - a.mean()) / (a.std() + 1e-8)
    return a


# 1) Reference: split into 4 equal-width panels, grayscale, normalized.
ref_im = Image.open(REFERENCE).convert("L")
w, h = ref_im.size
panel_w = w // 4
ref_panels_raw = []
for p in range(4):
    x0 = p * panel_w
    x1 = w if p == 3 else (p + 1) * panel_w
    ref_panels_raw.append(np.asarray(ref_im.crop((x0, 0, x1, h)), dtype=float))
ref_norm = [norm_gray(rp) for rp in ref_panels_raw]

# 2) Render + crop each candidate coronal slice once, reused for all 4 panels.
print(f"[slice_search] rendering {len(CANDIDATE_INDICES)} candidate coronal slices ...")
cand_norm = {}
cand_raw = {}
for i, idx in enumerate(CANDIDATE_INDICES):
    fig = mne.viz.plot_bem(
        subject=SUBJECT, subjects_dir=subjects_dir, orientation="coronal",
        slices=[idx], mri=FLASH5_REG, show_indices=False, show_orientation=False, show=False)
    png_path = os.path.join(TMP_DIR, f"cand_{idx:03d}.png")
    fig.savefig(png_path, dpi=100)
    plt.close(fig)
    cropped = crop_tight(Image.open(png_path).convert("RGB")).convert("L")
    cand_raw[idx] = cropped
    cand_norm[idx] = norm_gray(np.asarray(cropped, dtype=float))
    if (i + 1) % 20 == 0:
        print(f"[slice_search]  ... {i + 1}/{len(CANDIDATE_INDICES)} rendered")
print("[slice_search] rendering done")

# 3) Score every candidate against every reference panel.
scores = np.zeros((4, len(CANDIDATE_INDICES)))
for p in range(4):
    for j, idx in enumerate(CANDIDATE_INDICES):
        d = cand_norm[idx] - ref_norm[p]
        scores[p, j] = np.mean(d ** 2)

best_j = scores.argmin(axis=1)
best_idx = [CANDIDATE_INDICES[j] for j in best_j]
print(f"[slice_search] best-matching coronal slice indices: {best_idx}")
for p in range(4):
    print(f"[slice_search]   panel {p + 1}: slice {best_idx[p]} (score {scores[p, best_j[p]]:.4f}, "
          f"range {scores[p].min():.4f}-{scores[p].max():.4f})")

# 4) Build the comparison figure: reference row / matched-slice row / score curves.
fig = plt.figure(figsize=(16, 11))
gs = fig.add_gridspec(3, 4, height_ratios=[1, 1, 0.8], hspace=0.35, wspace=0.15)

ax_ref = fig.add_subplot(gs[0, :])
ax_ref.imshow(np.asarray(Image.open(REFERENCE)))
ax_ref.axis("off")
ax_ref.set_title("Published Figure 8 (reference)")

for p in range(4):
    ax = fig.add_subplot(gs[1, p])
    ax.imshow(np.asarray(cand_raw[best_idx[p]]), cmap="gray")
    ax.axis("off")
    ax.set_title(f"panel {p + 1}: slice {best_idx[p]}")

for p in range(4):
    ax = fig.add_subplot(gs[2, p])
    ax.plot(CANDIDATE_INDICES, scores[p], color="C0")
    ax.axvline(best_idx[p], color="C3", linestyle="--")
    ax.set_title(f"panel {p + 1} match score", fontsize=9)
    ax.set_xlabel("coronal slice index")
    if p == 0:
        ax.set_ylabel("normalized SSD")

fig.suptitle(f"{SUBJECT} (paper subject 4): coronal slice-wise match search", y=0.995)

out_path = os.path.join(HERE, "jas_fig8_slice_search.png")
fig.savefig(out_path, dpi=150)
plt.close(fig)
print(f"[slice_search] saved {out_path}")

import shutil  # noqa: E402
shutil.rmtree(TMP_DIR, ignore_errors=True)
