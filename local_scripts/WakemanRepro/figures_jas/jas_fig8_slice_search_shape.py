#!/usr/bin/env python3
"""Third attempt at finding Figure 8's coronal slice indices -- shape/
silhouette matching instead of raw grayscale SSD.

Why this exists: `jas_fig8_slice_search.py` / `_watershed.py` matched
whole-panel grayscale content (z-scored, resized, mean squared
difference). That metric is dominated by the large, high-contrast
gyral/skull texture filling most of the frame -- it under-weights the
thin sliver of neck tissue at the very bottom of the frame, which is the
actual discriminating feature between "coronal slice with no neck in
view" (reference panel 1) and "coronal slice with neck in view" (panels
2-4). Result: the previous search's panel-1 pick (slice 54) looked
neck-free in a small, normalized grayscale thumbnail but visibly shows a
neck at full resolution in the final colored render -- a real mismatch
the metric didn't catch (flagged by user review, 2026-08-29).

Fix: binarize each panel to a head/background silhouette (tissue vs. pure
black, threshold-based) instead of comparing raw intensity. A silhouette
directly encodes "does the outline taper into a neck here or stay a
closed round shape" -- exactly the feature that was getting lost -- and
is invariant to which MRI volume it's rendered on (T1 vs. flash5), so
there's no need to pick a background before searching, unlike the earlier
two scripts. Scored with the Dice coefficient (2*intersection /
(sum_a + sum_b)) between the reference panel's silhouette and each
candidate's, both cropped to their own foreground bounding box and
resized to a common shape first (so overall head size/position in the
frame doesn't matter, only the outline shape).

Rendered on T1.mgz with the current bem/*.surf surfaces (whatever's
currently swapped in -- watershed or FLASH, doesn't matter for a
silhouette match, both trace essentially the same outer_skin outline).

Output: `jas_fig8_slice_search_shape.png` -- reference / matched slices /
Dice-vs-index curves, same layout as the earlier two search scripts.
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
MRI_SRC = os.path.join(subjects_dir, SUBJECT, "mri", "T1.mgz")
TMP_DIR = os.path.join(HERE, "_tmp_fig8_slice_search_shape")
os.makedirs(TMP_DIR, exist_ok=True)

CANDIDATE_INDICES = list(range(15, 245, 3))
TARGET_SHAPE = (200, 200)  # (rows, cols)
FOREGROUND_THRESH = 12  # out of 255 -- separates real (dark) tissue from pure-black background


def crop_tight_rgb(im):
    """Crop a PIL RGB image to the bounding box of its non-white pixels
    (removes matplotlib's white figure margin)."""
    arr = np.asarray(im)
    nonwhite = np.any(arr < 250, axis=2)
    rows = np.where(nonwhite.any(axis=1))[0]
    cols = np.where(nonwhite.any(axis=0))[0]
    if len(rows) == 0 or len(cols) == 0:
        return im
    return im.crop((cols[0], rows[0], cols[-1] + 1, rows[-1] + 1))


def silhouette(gray_arr, shape=TARGET_SHAPE, thresh=FOREGROUND_THRESH):
    """Binarize to foreground (tissue) vs. background (black), crop to the
    foreground's own bounding box, resize to a common shape."""
    mask = gray_arr > thresh
    rows = np.where(mask.any(axis=1))[0]
    cols = np.where(mask.any(axis=0))[0]
    if len(rows) == 0 or len(cols) == 0:
        return np.zeros(shape, dtype=bool)
    cropped = mask[rows[0]:rows[-1] + 1, cols[0]:cols[-1] + 1]
    im = Image.fromarray((cropped * 255).astype(np.uint8)).resize((shape[1], shape[0]))
    return np.asarray(im) > 127


def dice(a, b):
    inter = np.logical_and(a, b).sum()
    return 2.0 * inter / (a.sum() + b.sum() + 1e-8)


# 1) Reference: split into 4 panels, silhouette each.
ref_im = Image.open(REFERENCE).convert("L")
w, h = ref_im.size
panel_w = w // 4
ref_sil = []
for p in range(4):
    x0 = p * panel_w
    x1 = w if p == 3 else (p + 1) * panel_w
    arr = np.asarray(ref_im.crop((x0, 0, x1, h)), dtype=float)
    ref_sil.append(silhouette(arr))

# 2) Render + silhouette each candidate coronal slice once, reused for all 4 panels.
print(f"[slice_search_shape] rendering {len(CANDIDATE_INDICES)} candidate coronal slices ...")
cand_sil = {}
cand_raw = {}
for i, idx in enumerate(CANDIDATE_INDICES):
    fig = mne.viz.plot_bem(
        subject=SUBJECT, subjects_dir=subjects_dir, orientation="coronal",
        slices=[idx], mri=MRI_SRC, show_indices=False, show_orientation=False, show=False)
    png_path = os.path.join(TMP_DIR, f"cand_{idx:03d}.png")
    fig.savefig(png_path, dpi=100)
    plt.close(fig)
    cropped = crop_tight_rgb(Image.open(png_path).convert("RGB")).convert("L")
    cand_raw[idx] = cropped
    cand_sil[idx] = silhouette(np.asarray(cropped, dtype=float))
    if (i + 1) % 20 == 0:
        print(f"[slice_search_shape]  ... {i + 1}/{len(CANDIDATE_INDICES)} rendered")
print("[slice_search_shape] rendering done")

# 3) Score every candidate against every reference panel (higher Dice = better).
scores = np.zeros((4, len(CANDIDATE_INDICES)))
for p in range(4):
    for j, idx in enumerate(CANDIDATE_INDICES):
        scores[p, j] = dice(cand_sil[idx], ref_sil[p])

best_j = scores.argmax(axis=1)
best_idx = [CANDIDATE_INDICES[j] for j in best_j]
print(f"[slice_search_shape] best-matching coronal slice indices: {best_idx}")
for p in range(4):
    print(f"[slice_search_shape]   panel {p + 1}: slice {best_idx[p]} (Dice {scores[p, best_j[p]]:.4f}, "
          f"range {scores[p].min():.4f}-{scores[p].max():.4f})")

# 4) Comparison figure: reference / matched slices / silhouette overlay / Dice curves.
fig = plt.figure(figsize=(16, 14))
gs = fig.add_gridspec(4, 4, height_ratios=[1, 1, 1, 0.8], hspace=0.4, wspace=0.15)

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
    # Overlay: reference silhouette in red, candidate silhouette in green, overlap in yellow.
    overlay = np.zeros((*TARGET_SHAPE, 3))
    overlay[..., 0] = ref_sil[p]
    overlay[..., 1] = cand_sil[best_idx[p]]
    ax.imshow(overlay)
    ax.axis("off")
    ax.set_title("silhouette overlap\n(red=ref, green=cand, yellow=both)", fontsize=8)

for p in range(4):
    ax = fig.add_subplot(gs[3, p])
    ax.plot(CANDIDATE_INDICES, scores[p], color="C0")
    ax.axvline(best_idx[p], color="C3", linestyle="--")
    ax.set_title(f"panel {p + 1} Dice score", fontsize=9)
    ax.set_xlabel("coronal slice index")
    if p == 0:
        ax.set_ylabel("Dice coefficient")

fig.suptitle(f"{SUBJECT} (paper subject 4): coronal slice-wise match search (silhouette/Dice)", y=0.995)

out_path = os.path.join(HERE, "jas_fig8_slice_search_shape.png")
fig.savefig(out_path, dpi=150)
plt.close(fig)
print(f"[slice_search_shape] saved {out_path}")

import shutil  # noqa: E402
shutil.rmtree(TMP_DIR, ignore_errors=True)
