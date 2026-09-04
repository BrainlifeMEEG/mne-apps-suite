FROM brainlifemeeg/mne:1.12.1

# brainlifemeeg/mne + the fsaverage template head model, and nothing else.
#
# Apps that build a *template* forward solution -- currently gedai / gedai-epo,
# which need a reference leadfield when the EEG montage is not standard 10-05 --
# call mne.make_forward_solution(..., trans='fsaverage', src=<fsaverage src>,
# bem=<fsaverage bem>). That needs the fsaverage BEM surfaces, BEM solution and
# source spaces (~760 MB). Fetching them at run time risks a TIMEOUT on a
# walltime-constrained job (the same failure class that hit the un-cached
# brainlifemeeg/mne image on its first run), so they are baked in here.
#
# This is the lean alternative to brainlifemeeg/mne-freesurfer (8.4 GB): no
# FreeSurfer binaries, no CentOS userland, just the fsaverage data files
# MNE-Python needs. Use brainlifemeeg/mne-freesurfer instead when an app needs
# recon-all, mkheadsurf, watershed BEM, or Qt surface rendering.

ENV MNE_DATA=/opt/mne_data
ENV SUBJECTS_DIR=/opt/mne_data/subjects

# Single RUN, self-contained: the download lands in one layer with nothing after
# it touching the same files (see docker-mne/README.md for why that matters).
# The full fsaverage subject dir is kept -- fetch_fsaverage() re-downloads the
# whole thing if any expected subdir (surf/, label/, ...) is missing, and would
# then hit the read-only container filesystem.
#
# Also update the README "surf/label/mri stripped" note if you change this.
RUN python3 -c "from pathlib import Path; import mne; \
mne.datasets.fetch_fsaverage(subjects_dir=Path('${SUBJECTS_DIR}'), verbose=True)"

CMD ["python3"]
