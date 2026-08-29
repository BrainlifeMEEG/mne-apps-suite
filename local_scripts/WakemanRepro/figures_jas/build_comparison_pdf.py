#!/usr/bin/env python3
"""Build a side-by-side comparison PDF: each page shows the actual
published Jas et al. 2018 figure (top, fetched from frontiersin.org --
see paper_figure*_reference.png/.webp, gitignored, not redistributed in
the repo) against this project's own reproduction (bottom).

Run after all jas_fig*.py scripts have produced their outputs. Self-contained:
PDF outputs are rendered to PNG via `pdftoppm` into a temp dir on the fly
(not left lying around in figures_jas/ as stray intermediate files).
"""
import os
import subprocess
import tempfile

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from matplotlib.backends.backend_pdf import PdfPages

HERE = os.path.dirname(os.path.abspath(__file__))

PAGES = [
    dict(n=1, title="Maxwell filtering comparison",
         paper="paper_figure1_reference.png",
         ours=["jas_fig1_maxfilter_comparison_S09.png"],
         note=None),
    dict(n=2, title="PSD quality control",
         paper="paper_figure2_reference.png",
         ours=["jas_fig2_psd_S09.png"],
         note=None),
    dict(n=3, title="Filter response (old vs. current MNE)",
         paper="paper_figure3_reference.png",
         ours=["jas_fig3_filter_response.png"],
         note=None),
    dict(n=4, title="Baseline vs. highpass vs. tSSS (subject 3, famous faces)",
         paper="paper_figure4_reference.png",
         ours=["jas_fig4_tsss_analysis_sub003_famous.pdf"],
         note=None),
    dict(n=5, title="Grand-average evoked (EEG065)",
         paper="paper_figure5_reference.png",
         ours=["jas_fig5_grand_average_highpass-NoneHz.pdf",
              "jas_fig5_grand_average_highpass-1Hz.pdf"],
         note=None),
    dict(n=6, title="Sensor-space statistics: cluster stats (A) + decoding (B)",
         paper="paper_figure6_reference.png",
         ours=["jas_fig6a_sensor_cluster_stats_highpass-NoneHz.pdf",
              "jas_fig6b_decoding_highpass-NoneHz.pdf"],
         note=None),
    dict(n=7, title="Spatiotemporal sensor cluster",
         paper="paper_figure7_reference.png",
         ours=["jas_fig7_spatiotemporal_cluster_highpass-NoneHz-00.pdf"],
         note=None),
    dict(n=8, title="BEM surfaces (subject 4)",
         paper="paper_figure8_reference.png",
         ours=["jas_fig8_bem_surfaces_sub004.pdf"],
         note="Real FLASH BEM (convert_flash_mris/make_flash_bem, the paper's own method) "
              "rendered on plain T1.mgz rather than the noisy synthesized flash5_reg.mgz "
              "-- see GLITCHES.md's \"FLASH MRI was never actually absent\" section."),
    dict(n=9, title="Coregistration (our S09)",
         paper="paper_figure9_reference.png",
         ours=["jas_fig9_coregistration_sub010.png"],
         note="Trans file from this project's own automated ICP coregistration "
              "(mne.coreg.Coregistration) -- no pre-existing trans ships with this "
              "dataset release. Fit quality logged at coreg time, see GLITCHES.md. "
              "Head/inner-skull surfaces are the same real FLASH BEM used for Figure 8."),
    dict(n=10, title="Whitened MEG data + GFP (subject 4)",
         paper="paper_figure10_reference.png",
         ours=["jas_fig10_whitened_gfp_sub004.pdf"],
         note=None),
    dict(n=11, title="Group-average source reconstruction: dSPM (left) + LCMV (right)",
         paper="paper_figure11_reference.png",
         ours=["jas_fig11_group_source_highpass-NoneHz.pdf"],
         note=None),
    dict(n=12, title="Spatio-temporal source-space clusters",
         paper="paper_figure12_reference.png",
         ours=["jas_fig12_source_cluster_stats_highpass-NoneHz.png"],
         note=None),
]


def load(fname, tmpdir):
    path = os.path.join(HERE, fname)
    if fname.endswith(".pdf"):
        stem = os.path.join(tmpdir, os.path.splitext(fname)[0])
        subprocess.run(["pdftoppm", "-png", "-r", "150", path, stem], check=True)
        rendered = stem + "-1.png"
        return mpimg.imread(rendered)
    return mpimg.imread(path)


out_path = os.path.join(HERE, "jas_figures_comparison.pdf")
tmpdir_ctx = tempfile.TemporaryDirectory()
tmpdir = tmpdir_ctx.name
with PdfPages(out_path) as pdf:
    for page in PAGES:
        paper_img = load(page["paper"], tmpdir)
        our_imgs = [load(f, tmpdir) for f in page["ours"]]

        n_our = len(our_imgs)
        fig = plt.figure(figsize=(11, 4 + 3.5 * max(1, (n_our + 1) // 1)))
        gs = fig.add_gridspec(2, n_our, height_ratios=[1.3, 1])

        ax_top = fig.add_subplot(gs[0, :])
        ax_top.imshow(paper_img)
        ax_top.axis("off")
        ax_top.set_title(f"Jas et al. 2018, Figure {page['n']} -- {page['title']}\n"
                         f"(published figure, frontiersin.org)", fontsize=10)

        for i, im in enumerate(our_imgs):
            ax = fig.add_subplot(gs[1, i])
            ax.imshow(im)
            ax.axis("off")
            if n_our > 1:
                ax.set_title(f"our reproduction ({page['ours'][i]})", fontsize=8)
        if n_our == 1:
            fig.axes[-1].set_title("our reproduction", fontsize=9)

        if page["note"]:
            fig.text(0.5, 0.01, page["note"], ha="center", fontsize=8,
                     style="italic", wrap=True)

        fig.tight_layout(rect=[0, 0.03, 1, 1])
        pdf.savefig(fig)
        plt.close(fig)
        print(f"[comparison] page {page['n']} done")

tmpdir_ctx.cleanup()
print(f"[comparison] saved {out_path}")
