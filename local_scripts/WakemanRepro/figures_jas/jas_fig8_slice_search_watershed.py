#!/usr/bin/env python3
"""Same slice-wise match search as jas_fig8_slice_search.py, but on
watershed BEM surfaces + plain T1.mgz instead of FLASH BEM + flash5_reg.mgz.

Why this variant exists: a direct 3-way comparison (reference vs.
watershed-on-T1 vs. FLASH-on-flash5_reg, see jas_fig8_3way_compare.png)
showed our own flash5_reg.mgz synthesis came out visibly noisy/degraded --
`mri_ms_fitparms` logged "non-equal flip_angle found ... Flip_angle is set
to zero" while combining the 5deg/30deg echoes, meaning the dual-flip-angle
T1 synthesis likely didn't work as intended. Plain T1.mgz, by contrast,
visually matches the reference's contrast style closely. Per user
direction (2026-08-29): re-run the slice search against the
watershed-on-T1 renders instead, before spending more effort fixing the
FLASH synthesis.

Assumes `bem/{inner_skull,outer_skull,outer_skin}.surf` currently hold the
WATERSHED surfaces for SUBJECT (swap them in from
`bem/watershed_backup_preflash/` first if the FLASH ones are in place --
see run_subject_flash_bem.py's docstring for why both copies exist).

See jas_fig8_slice_search.py for the full method docstring (identical
here, only the rendered MRI source differs).
"""
import os
import shutil
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
TMP_DIR = os.path.join(HERE, "_tmp_fig8_slice_search_ws")
os.makedirs(TMP_DIR, exist_ok=True)

CANDIDATE_INDICES = list(range(15, 245, 3))
TARGET_SHAPE = (200, 200)


def crop_tight(im):
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


ref_im = Image.open(REFERENCE).convert("L")
w, h = ref_im.size
panel_w = w // 4
ref_panels_raw = []
for p in range(4):
    x0 = p * panel_w
    x1 = w if p == 3 else (p + 1) * panel_w
    ref_panels_raw.append(np.asarray(ref_im.crop((x0, 0, x1, h)), dtype=float))
ref_norm = [norm_gray(rp) for rp in ref_panels_raw]

print(f"[slice_search_ws] rendering {len(CANDIDATE_INDICES)} candidate coronal slices "
      "(watershed BEM on T1.mgz) ...")
cand_norm = {}
cand_raw = {}
for i, idx in enumerate(CANDIDATE_INDICES):
    fig = mne.viz.plot_bem(
        subject=SUBJECT, subjects_dir=subjects_dir, orientation="coronal",
        slices=[idx], mri=MRI_SRC, show_indices=False, show_orientation=False, show=False)
    png_path = os.path.join(TMP_DIR, f"cand_{idx:03d}.png")
    fig.savefig(png_path, dpi=100)
    plt.close(fig)
    cropped = crop_tight(Image.open(png_path).convert("RGB")).convert("L")
    cand_raw[idx] = cropped
    cand_norm[idx] = norm_gray(np.asarray(cropped, dtype=float))
    if (i + 1) % 20 == 0:
        print(f"[slice_search_ws]  ... {i + 1}/{len(CANDIDATE_INDICES)} rendered")
print("[slice_search_ws] rendering done")

scores = np.zeros((4, len(CANDIDATE_INDICES)))
for p in range(4):
    for j, idx in enumerate(CANDIDATE_INDICES):
        d = cand_norm[idx] - ref_norm[p]
        scores[p, j] = np.mean(d ** 2)

best_j = scores.argmin(axis=1)
best_idx = [CANDIDATE_INDICES[j] for j in best_j]
print(f"[slice_search_ws] best-matching coronal slice indices: {best_idx}")
for p in range(4):
    print(f"[slice_search_ws]   panel {p + 1}: slice {best_idx[p]} (score {scores[p, best_j[p]]:.4f}, "
          f"range {scores[p].min():.4f}-{scores[p].max():.4f})")

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

fig.suptitle(f"{SUBJECT} (paper subject 4): coronal slice-wise match search (watershed BEM on T1.mgz)", y=0.995)

out_path = os.path.join(HERE, "jas_fig8_slice_search_watershed.png")
fig.savefig(out_path, dpi=150)
plt.close(fig)
print(f"[slice_search_ws] saved {out_path}")

shutil.rmtree(TMP_DIR, ignore_errors=True)
