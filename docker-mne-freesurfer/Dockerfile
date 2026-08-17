FROM brainlifemeeg/mne:1.12.1

# FreeSurfer + Qt/offscreen-3D system deps, on top of what brainlifemeeg/mne
# already has (libgl1, libglib2.0-0t64, libsm6, libxext6, libxrender1,
# libgomp1, mesa-utils, xvfb). tcsh/bc/gawk/perl back FreeSurfer's own
# shell/Perl scripts (mkheadsurf, used by the coreg app's make_scalp_surfaces
# call). libegl1/libglu1-mesa/libxmu6/libxi6/libfreetype6/libxft2/xauth +
# libxcb-* are Qt's offscreen-platform-plugin runtime deps, needed by
# pyvistaqt-based brain-surface rendering (coreg, forward, source-estimate,
# label-timecourse). wget fetches the FreeSurfer tarball below (this base
# has neither wget nor curl).
RUN apt-get update && apt-get install -y --no-install-recommends \
        libegl1 \
        libglu1-mesa \
        libxmu6 \
        libxi6 \
        libfreetype6 \
        libxft2 \
        libxcb-xinerama0 \
        libxcb-cursor0 \
        libxcb-icccm4 \
        libxcb-image0 \
        libxcb-keysyms1 \
        libxcb-randr0 \
        libxcb-render-util0 \
        xauth \
        bc \
        tcsh \
        gawk \
        perl \
        wget \
    && rm -rf /var/lib/apt/lists/*

ENV FREESURFER_HOME=/opt/freesurfer
ENV PATH="${FREESURFER_HOME}/bin:${PATH}"
ENV MNE_DATA=/opt/mne_data
ENV SUBJECTS_DIR=/opt/mne_data/subjects

# Single RUN: download, extract, and strip unneeded components together, so
# nothing duplicates the extracted content the way brainlife/mne-freesurfer:
# 7.3.2-1.2.1's separate `chmod -R` layers did (see docker-mne/README.md for
# the root-cause writeup). Strip list proven safe by
# aunnikri642/app-freesurfer-mne-source-recon. NOT stripping `mni/`
# (mkheadsurf's Perl5 libs live there) or `average/`/`subjects/` (used by
# BEM/coreg default-template fallbacks).
RUN mkdir -p "${FREESURFER_HOME}" && \
    wget -qO /tmp/freesurfer.tar.gz \
        https://surfer.nmr.mgh.harvard.edu/pub/dist/freesurfer/7.4.1/freesurfer-linux-centos7_x86_64-7.4.1.tar.gz && \
    tar --no-same-owner -xzf /tmp/freesurfer.tar.gz -C /opt && \
    rm /tmp/freesurfer.tar.gz && \
    rm -rf "${FREESURFER_HOME}/trctrain" \
           "${FREESURFER_HOME}/diffusion" \
           "${FREESURFER_HOME}/docs" \
           "${FREESURFER_HOME}/fsafd" \
           "${FREESURFER_HOME}/matlab" \
           "${FREESURFER_HOME}/models" \
           "${FREESURFER_HOME}/tktools"

# Qt-based offscreen 3D rendering, needed by coreg/forward/source-estimate/
# label-timecourse (mne.viz.set_3d_backend('pyvistaqt') + QT_QPA_PLATFORM=offscreen).
RUN pip install --no-cache-dir pyvistaqt qtpy PyQt5

# Bake in fsaverage so apps with a fsaverage-fallback path don't hit a
# runtime download on a walltime-constrained job (same TIMEOUT class of
# problem hit with the un-cached brainlifemeeg/mne image on its first run).
RUN python3 -c "from pathlib import Path; import mne; mne.datasets.fetch_fsaverage(subjects_dir=Path('${SUBJECTS_DIR}'), verbose=True)"

CMD ["python3"]
