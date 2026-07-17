FROM python:3.11-slim

# System libraries required for headless PyVista/VTK 3D rendering (topomaps,
# source plots) via Xvfb — matches the OpenGL deps used by brainlife/mne:1.2.1,
# renamed for Debian 13 (trixie): libgl1-mesa-glx -> libgl1, libglib2.0-0 -> libglib2.0-0t64.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0t64 \
        libsm6 \
        libxext6 \
        libxrender1 \
        libgomp1 \
        mesa-utils \
        xvfb \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
        mne==1.12.1 \
        pyvista \
        nibabel \
        matplotlib \
        scikit-learn \
        pandas \
        seaborn \
        jupyter \
        ipyvtklink \
        mne-bids \
        coloredlogs \
        tqdm \
        json_tricks \
        fire \
        IPython \
        ipywidgets \
    && pip install --no-cache-dir "https://api.github.com/repos/autoreject/autoreject/zipball/master"

ENV PYVISTA_OFF_SCREEN=true
ENV PYVISTA_USE_IPYVTK=true

CMD ["python3"]
