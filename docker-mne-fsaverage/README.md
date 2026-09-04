# brainlife-mne-fsaverage Docker image (MNE 1.12.1 + fsaverage)

`brainlifemeeg/mne:1.12.1` with the **fsaverage template head model** baked in,
and nothing else. Published as **`docker://brainlifemeeg/mne-fsaverage:1.12.1`**.

## Why

Some sensor-space apps need a *template* forward solution / reference leadfield
but not a subject MRI or FreeSurfer. The first case is **`gedai` / `gedai-epo`**
(unsupervised EEG denoising by leadfield filtering): when the EEG montage does
not use standard 10-05 names, GEDAI's bundled 10-05 leadfield can't be
name-matched, so the app builds a forward solution for the actual electrode
positions with

```python
mne.make_forward_solution(info, trans='fsaverage',
                          src='<fsaverage>/bem/fsaverage-ico-5-src.fif',
                          bem='<fsaverage>/bem/fsaverage-5120-5120-5120-bem-sol.fif',
                          eeg=True, meg=False)
```

That needs the fsaverage BEM surfaces, BEM solution and source spaces (~760 MB).
Fetching them at run time (`mne.datasets.fetch_fsaverage()`) risks a TIMEOUT on
a walltime-constrained job — the same failure class the un-cached
`brainlifemeeg/mne` image hit on its first run — so they are baked in here.

## Why not `brainlifemeeg/mne-freesurfer`

That image (8.4 GB) also has fsaverage, but carries a full FreeSurfer 7.4.1
install (CentOS userland, `recon-all`, `mkheadsurf`, watershed BEM) and Qt
surface-rendering deps. This image is ~1.5 GB compressed (brainlifemeeg/mne 509 MB + ~760 MB of
fsaverage data files, no binaries). Use `mne-freesurfer` when an app actually
needs `recon-all` / `mkheadsurf` / watershed BEM / `pyvistaqt` brain surfaces
(`make-watershed-bem`, the coreg/forward/source-estimate apps); use this image
for template-forward work on the lean base.

## Recipe

```dockerfile
FROM brainlifemeeg/mne:1.12.1
ENV MNE_DATA=/opt/mne_data
ENV SUBJECTS_DIR=/opt/mne_data/subjects
RUN python3 -c "from pathlib import Path; import mne; \
mne.datasets.fetch_fsaverage(subjects_dir=Path('${SUBJECTS_DIR}'), verbose=True)"
```

`fetch_fsaverage` writes to `${SUBJECTS_DIR}/fsaverage`. At run time an app
recovers the path with `mne.datasets.fetch_fsaverage()` (no network hit — the
files are already there) or directly from `${SUBJECTS_DIR}/fsaverage`.

## Build / publish

```bash
cd docker-mne-fsaverage
docker build -t brainlifemeeg/mne-fsaverage:1.12.1 .
docker push brainlifemeeg/mne-fsaverage:1.12.1
```

Bump the tag to match the `brainlifemeeg/mne` base version it is built from.
