#!/usr/bin/env python3
"""Fourth attempt at finding Figure 8's coronal slice indices -- combines
the previous two failed metrics' complementary strengths instead of using
either alone.

History (why neither earlier metric was trustworthy on its own):
- `jas_fig8_slice_search.py`/`_watershed.py`: whole-panel grayscale SSD.
  Dominated by the large, high-contrast gyral/skull texture -- ignores the
  thin neck sliver at the bottom of frame, so it can't reliably tell
  "coronal slice with no neck in view" from "with neck in view" (this is
  what actually failed: picked slice 54 for panel 1, which DOES show a
  neck in the full-resolution render, confirmed by user review).
- `jas_fig8_slice_search_shape.py`: binary head/background silhouette +
  Dice overlap, meant to fix exactly that -- but Dice needs the two
  silhouettes properly scaled/aligned first, and naive threshold+bbox+
  resize-to-square distorts aspect ratio inconsistently between our
  256x256 MNE canvas (lots of surrounding black margin, size depends on
  where the crop lands) and the reference's own tightly-pre-cropped
  panels. Best achievable Dice only ~0.5-0.75, and panel 4 picked a
  slice (186) that isn't even a single connected head shape -- a
  stray-pixel/threshold robustness problem, not a real match.

Fix here: two complementary, more targeted signals, combined by rank sum
instead of trusting either alone:
1. **Aspect ratio of the (largest-connected-component-cleaned) foreground
   bounding box** (height/width). This directly encodes "does the frame
   extend down into a narrower neck or stop at a round head" without
   being thrown by resize distortion (compared before any resizing) or by
   stray noise pixels (a scipy connected-component pass keeps only the
   single largest foreground blob before computing the bbox).
2. **Grayscale SSD within that same cleaned bounding box** (z-scored,
   resized to a common shape) -- keeps the earlier metric's sensitivity to
   actual anatomical content (ventricle shape, gyral depth) as a
   tiebreaker/refinement once the aspect ratio has narrowed things down to
   the right general neck-vs-no-neck neighborhood.

Combined score = rank(aspect_diff) + rank(ssd), both computed per
candidate per panel, summed, minimized. Rank sum rather than a weighted
raw-value combination because the two metrics have unrelated, non-
comparable scales and this avoids having to hand-tune a weight.

Output: `jas_fig8_slice_search_combined.png`.
"""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from scipy import ndimage

import mne

HERE = os.path.dirname(os.path.abspath(__file__))
ORIGINAL_SCRIPTS = os.path.normpath(os.path.join(HERE, "..", "original_scripts"))
sys.path.insert(0, ORIGINAL_SCRIPTS)
from library.config import subjects_dir  # noqa: E402

SUBJECT = "sub004"
REFERENCE = os.path.join(HERE, "paper_figure8_reference.png")
MRI_SRC = os.path.join(subjects_dir, SUBJECT, "mri", "T1.mgz")
TMP_DIR = os.path.join(HERE, "_tmp_fig8_slice_search_combined")
os.makedirs(TMP_DIR, exist_ok=True)

CANDIDATE_INDICES = list(range(15, 245, 3))
TARGET_SHAPE = (200, 200)
FOREGROUND_THRESH = 12


def crop_tight_rgb(im):
    arr = np.asarray(im)
    nonwhite = np.any(arr < 250, axis=2)
    rows = np.where(nonwhite.any(axis=1))[0]
    cols = np.where(nonwhite.any(axis=0))[0]
    if len(rows) == 0 or len(cols) == 0:
        return im
    return im.crop((cols[0], rows[0], cols[-1] + 1, rows[-1] + 1))


def clean_bbox(gray_arr, thresh=FOREGROUND_THRESH):
    """Threshold, keep only the largest connected component, return its
    tight bounding box (r0, r1, c0, c1) and aspect ratio (height/width)."""
    mask = gray_arr > thresh
    labeled, n = ndimage.label(mask)
    if n == 0:
        h, w = gray_arr.shape
        return (0, h, 0, w), 1.0
    sizes = ndimage.sum(mask, labeled, range(1, n + 1))
    biggest = np.argmax(sizes) + 1
    clean = labeled == biggest
    rows = np.where(clean.any(axis=1))[0]
    cols = np.where(clean.any(axis=0))[0]
    r0, r1, c0, c1 = rows[0], rows[-1] + 1, cols[0], cols[-1] + 1
    aspect = (r1 - r0) / max(c1 - c0, 1)
    return (r0, r1, c0, c1), aspect


def norm_crop(gray_arr, bbox, shape=TARGET_SHAPE):
    r0, r1, c0, c1 = bbox
    cropped = gray_arr[r0:r1, c0:c1]
    im = Image.fromarray(cropped.astype(np.uint8)).resize((shape[1], shape[0]))
    a = np.asarray(im, dtype=float)
    a = (a - a.mean()) / (a.std() + 1e-8)
    return a


# 1) Reference panels: grayscale, cleaned bbox, aspect ratio, normalized crop.
ref_im = Image.open(REFERENCE).convert("L")
w, h = ref_im.size
panel_w = w // 4
ref_gray, ref_bbox, ref_aspect, ref_norm = [], [], [], []
for p in range(4):
    x0 = p * panel_w
    x1 = w if p == 3 else (p + 1) * panel_w
    arr = np.asarray(ref_im.crop((x0, 0, x1, h)), dtype=float)
    bbox, aspect = clean_bbox(arr)
    ref_gray.append(arr)
    ref_bbox.append(bbox)
    ref_aspect.append(aspect)
    ref_norm.append(norm_crop(arr, bbox))

# 2) Render + process each candidate coronal slice once.
print(f"[slice_search_combined] rendering {len(CANDIDATE_INDICES)} candidate coronal slices ...")
cand_raw, cand_aspect, cand_norm = {}, {}, {}
for i, idx in enumerate(CANDIDATE_INDICES):
    fig = mne.viz.plot_bem(
        subject=SUBJECT, subjects_dir=subjects_dir, orientation="coronal",
        slices=[idx], mri=MRI_SRC, show_indices=False, show_orientation=False, show=False)
    png_path = os.path.join(TMP_DIR, f"cand_{idx:03d}.png")
    fig.savefig(png_path, dpi=100)
    plt.close(fig)
    cropped = crop_tight_rgb(Image.open(png_path).convert("RGB")).convert("L")
    arr = np.asarray(cropped, dtype=float)
    bbox, aspect = clean_bbox(arr)
    cand_raw[idx] = cropped
    cand_aspect[idx] = aspect
    cand_norm[idx] = norm_crop(arr, bbox)
    if (i + 1) % 20 == 0:
        print(f"[slice_search_combined]  ... {i + 1}/{len(CANDIDATE_INDICES)} rendered")
print("[slice_search_combined] rendering done")

# 3) Score: rank(aspect_diff) + rank(ssd), summed, per panel.
n = len(CANDIDATE_INDICES)
aspect_diff = np.zeros((4, n))
ssd = np.zeros((4, n))
for p in range(4):
    for j, idx in enumerate(CANDIDATE_INDICES):
        aspect_diff[p, j] = abs(cand_aspect[idx] - ref_aspect[p])
        ssd[p, j] = np.mean((cand_norm[idx] - ref_norm[p]) ** 2)

combined = np.zeros((4, n))
for p in range(4):
    rank_aspect = aspect_diff[p].argsort().argsort()
    rank_ssd = ssd[p].argsort().argsort()
    combined[p] = rank_aspect + rank_ssd

best_j = combined.argmin(axis=1)
best_idx = [CANDIDATE_INDICES[j] for j in best_j]
print(f"[slice_search_combined] best-matching coronal slice indices: {best_idx}")
for p in range(4):
    j = best_j[p]
    print(f"[slice_search_combined]   panel {p + 1}: slice {best_idx[p]} "
          f"(aspect_diff={aspect_diff[p, j]:.3f}, ssd={ssd[p, j]:.3f}, "
          f"combined_rank_sum={combined[p, j]:.0f})")

# 4) Comparison figure.
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
    ax.plot(CANDIDATE_INDICES, aspect_diff[p], color="C1", label="aspect diff")
    ax.axvline(best_idx[p], color="C3", linestyle="--")
    ax.set_title(f"panel {p + 1} aspect diff", fontsize=9)
    ax.set_xlabel("coronal slice index")
    if p == 0:
        ax.set_ylabel("|aspect - ref aspect|")

for p in range(4):
    ax = fig.add_subplot(gs[3, p])
    ax.plot(CANDIDATE_INDICES, combined[p], color="C0")
    ax.axvline(best_idx[p], color="C3", linestyle="--")
    ax.set_title(f"panel {p + 1} combined rank sum", fontsize=9)
    ax.set_xlabel("coronal slice index")
    if p == 0:
        ax.set_ylabel("rank(aspect) + rank(ssd)")

fig.suptitle(f"{SUBJECT} (paper subject 4): coronal slice-wise match search "
            "(aspect ratio + grayscale SSD, rank-combined)", y=0.995)

out_path = os.path.join(HERE, "jas_fig8_slice_search_combined.png")
fig.savefig(out_path, dpi=150)
plt.close(fig)
print(f"[slice_search_combined] saved {out_path}")

import shutil  # noqa: E402
shutil.rmtree(TMP_DIR, ignore_errors=True)
