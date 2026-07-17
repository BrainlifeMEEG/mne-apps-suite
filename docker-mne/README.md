# brainlife-mne Docker image (MNE 1.12.1)

Reverse-engineered replacement for `docker://brainlife/mne:1.2.1`, bumped to
MNE-Python 1.12.1. Built and smoke-tested locally, published as
**`docker://brainlifemeeg/mne:1.12.1`**.

## How the recipe was reverse-engineered

`brainlife/mne` has no linked GitHub source (`is_automated: false` on Docker
Hub, `source: null`) and no Dockerfile exists in this repo, so the recipe was
recovered from the published image's config blob (`docker manifest inspect`
gives layer digests/sizes; the image config blob — pulled directly from the
registry API — includes a full `history` array with every build step's
`created_by`, i.e. the effective Dockerfile, including everything inherited
from the base image).

Reconstructed `brainlife/mne:1.2.1` Dockerfile (`FROM python:3.10-slim` plus
these app-specific layers):

```dockerfile
FROM python:3.10-slim
RUN pip3 install mne==1.2.1 pyvista nibabel
RUN pip install matplotlib scikit-learn pandas seaborn jupyter pyvista ipyvtklink
RUN pip install https://api.github.com/repos/autoreject/autoreject/zipball/master
RUN pip install mne-bids coloredlogs tqdm pandas json_tricks fire nibabel IPython ipywidgets
RUN git clone https://github.com/mne-tools/mne-bids-pipeline.git /mne-bids-pipeline
RUN apt-get update && apt-get -y install libgl1 mesa-utils libgl1-mesa-glx xvfb
ENV PYVISTA_OFF_SCREEN=true
ENV PYVISTA_USE_IPYVTK=true
```

`docker://aunnikri642/app-freesurfer-mne-source-recon` was reverse-engineered
the same way for comparison (used by 8 apps here, e.g. `make-watershed-bem`,
`emptyroom-proj`). It's a much larger (10 GB), separately-purposed image: a
modern `python:3.12-slim`(-ish, Debian trixie) base with FreeSurfer 7.4.1,
MNE/fsaverage sample datasets, and Qt bindings for source reconstruction. It
does its big installs (FreeSurfer untar: 7.4 GB, dataset download: 2.1 GB) as
single self-contained `RUN` steps with no follow-up layer touching the same
files — that's the right pattern, and why its size, while large, is all
"real" content rather than duplication.

## Why brainlife/mne jumped from 1.76 GB (1.2.1) to 15.71 GB (1.8.0)

Confirmed via the same config-blob technique — data, not guesswork:

| tag | pushed | by | size |
|---|---|---|---|
| 1.2.1 | 2022-10-24 | bacaron | 1.76 GB |
| 1.8.0 | 2024-12-21 | gamorosino | 15.71 GB |

`1.8.0`'s history shows it was **not** built `FROM python:3.10-slim` at all.
It starts from an existing CentOS 7 image already containing FreeSurfer 7.3.2
(`MAINTAINER Soichi Hayashi`) — almost certainly a brainlife FreeSurfer base
image — and the same MNE pip-install recipe from 1.2.1 was appended on top of
it, apparently to get FreeSurfer support into the same image rather than
starting a second one. Layer-by-layer:

| size | layer |
|---|---|
| 6.57 GB | `curl .../freesurfer-linux-centos7_x86_64-7.3.2.tar.gz \| tar xvz` |
| 2.69 GB | `fs_install_mcr R2019b` (installs a 2nd MATLAB Compiler Runtime, MCRv97) |
| 2.69 GB | `chmod -R +rx /usr/local/freesurfer/MCRv97` |
| 1.10 GB | `git clone mne-bids-pipeline` (same as 1.2.1 — see below) |
| 0.61 GB | `chmod -R +rx /usr/local/freesurfer/MCRv84` |
| 0.61 GB | download of MCRv84 (the MATLAB runtime FreeSurfer ships with) |
| ... | (rest is `yum install`s, building Python 3.10.2 from source, etc.) |

Two things compound here:

1. **Base image mismatch.** FreeSurfer + two full MATLAB Compiler Runtimes
   (MCRv84 *and* MCRv97 — the second added later without removing the first)
   account for ~12.6 GB by themselves. None of that is needed by the plain
   MNE apps that use this image — it belongs in a FreeSurfer-specific image
   (which already exists: `aunnikri642/app-freesurfer-mne-source-recon`).
2. **`chmod -R` in its own `RUN` layer duplicates the content it touches.**
   Docker layers are additive content diffs; running `chmod -R` on a huge
   directory tree in a separate `RUN` after the install step doesn't mutate
   the earlier layer in place — it writes a second full copy of every file
   (new metadata = new diff) into a new layer. That's exactly the
   near-identical-size pairs above (2.69+2.69 GB, 0.61+0.61 GB): each MCR's
   install layer and its later `chmod -R` layer are each carrying the
   runtime's data twice.

Even in the lean 1.2.1 image, `git clone mne-bids-pipeline` was already the
single largest app-specific layer (0.77 GB) — and grepping this repo shows
**it's never imported or used by any app's `main.py`**. It's dropped from
the new recipe below.

## Preventing recurrence

- Don't silently swap the base image for a shared/reusable Docker Hub tag.
  If FreeSurfer support is needed, extend a purpose-built image (or a
  multi-stage build), not the general-purpose `brainlife/mne` tag apps
  already depend on for lightweight jobs.
- Never `chmod -R` (or otherwise touch every file in) a large directory in a
  `RUN` layer that's separate from the one that created those files — fold
  it into the same `RUN`, e.g. `tar xvz -C /dest && chmod -R +rx /dest`.
- `rm -rf /var/lib/apt/lists/*` / `pip install --no-cache-dir` in the *same*
  `RUN` as the install, for the same reason: cleanup in a later layer doesn't
  shrink the image.
- Drop dependencies nothing in the repo actually imports (`mne-bids-pipeline`
  here).
- Periodically diff `docker manifest inspect <image>:<old>` vs `:<new>` layer
  sizes before pushing a new tag — this whole investigation was done with
  `docker manifest inspect` plus pulling the config blob directly from the
  registry API (see commands below), no local pull of the 15 GB image
  required.

## The new image

```dockerfile
FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 libglib2.0-0t64 libsm6 libxext6 libxrender1 libgomp1 \
        mesa-utils xvfb \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir \
        mne==1.12.1 pyvista nibabel matplotlib scikit-learn pandas seaborn \
        jupyter ipyvtklink mne-bids coloredlogs tqdm json_tricks fire \
        IPython ipywidgets \
    && pip install --no-cache-dir "https://api.github.com/repos/autoreject/autoreject/zipball/master"
ENV PYVISTA_OFF_SCREEN=true
ENV PYVISTA_USE_IPYVTK=true
CMD ["python3"]
```

Changes from the reconstructed 1.2.1 recipe:
- `mne==1.2.1` → `mne==1.12.1` (requires Python ≥3.10; `python:3.11-slim`
  used, matching what `mne-bids` 0.19 now requires too)
- Dropped the unused `mne-bids-pipeline` clone (−0.77 GB, zero functional
  loss for apps in this repo)
- `pip install --no-cache-dir` throughout (avoids leaving the wheel cache in
  the layer)
- `libgl1-mesa-glx` → `libgl1`, `libglib2.0-0` → `libglib2.0-0t64`: package
  renames on Debian 13 (trixie), which `python:3.11-slim` is now built on;
  the old names no longer exist there
- `apt-get ... && rm -rf /var/lib/apt/lists/*` combined into one `RUN`
  (the original recipe's apt step left the apt cache in the image)

Built and verified locally (`docker build -t brainlife-mne:1.12.1 .`):
imports (`mne`, `pyvista`, `mne_bids`, `autoreject`, `sklearn`, `nibabel`)
and a headless PyVista off-screen render all work. Compressed size ~509 MB
vs. 1.76 GB for 1.2.1 — smaller despite the newer MNE version, mainly from
dropping `mne-bids-pipeline` and `--no-cache-dir`.

## Investigation commands (no local image pull needed)

```bash
# tag list + sizes
curl -s "https://hub.docker.com/v2/repositories/brainlife/mne/tags?page_size=100"

# layer sizes for a specific tag
docker manifest inspect brainlife/mne:1.8.0

# full build history (reconstructed Dockerfile) — pull the config blob directly
TOKEN=$(curl -s "https://auth.docker.io/token?service=registry.docker.io&scope=repository:brainlife/mne:pull" \
  | python3 -c "import json,sys;print(json.load(sys.stdin)['token'])")
curl -sL -H "Authorization: Bearer $TOKEN" \
  "https://registry-1.docker.io/v2/brainlife/mne/blobs/sha256:<config-digest-from-manifest>" \
  | python3 -m json.tool
```

## Still open

- **Point apps at the new image.** This repo's `main` scripts still pull
  `docker://brainlife/mne:1.2.1` (24 apps), `:0.23dev` (12), `:1.0.2` (2), or
  the nonexistent `:1.6.0` (1, see below). None of them reference
  `brainlifemeeg/mne:1.12.1` yet — that's a separate follow-up once this
  image has been validated against the actual apps (MNE 1.2.1 → 1.12.1 spans
  many releases; some API surfaces may have changed).
- **Unrelated bug found in passing:** `notch-filter/main` references
  `docker://brainlife/mne:1.6.0`, which doesn't exist on Docker Hub (never
  did, per the tag list above — 404). That app is currently broken.
