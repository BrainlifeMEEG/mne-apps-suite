# brainlife-mne-freesurfer Docker image (MNE 1.12.1 + FreeSurfer 7.4.1)

Reverse-engineered lean replacement for
`docker://brainlife/mne-freesurfer:7.3.2-1.2.1`, bumped to MNE-Python 1.12.1
and FreeSurfer 7.4.1. Built `FROM` our own `brainlifemeeg/mne:1.12.1` (see
`../docker-mne/`), so the MNE/Python stack stays in lockstep with the plain
MNE image. Built and smoke-tested locally, published as
**`docker://brainlifemeeg/mne-freesurfer:1.12.1-7.4.1`**.

Tag order is `<mne-version>-<freesurfer-version>` (MNE is the primary library
here; the old image used the reverse order, `7.3.2-1.2.1`).

## What this image is for

The MEG/EEG source-localization apps need FreeSurfer surfaces/tools in
addition to MNE. In *this* repo that's currently just `make-watershed-bem`,
but a whole source pipeline is being onboarded (the `obVdo/app-*-v2` family:
bem, coreg, source-space, forward, inverse, source-estimate,
label-timecourse). Reading all of their `main.py` files, the actual runtime
requirements beyond plain MNE are:

| Need | Which apps | Provided by |
|---|---|---|
| `mri_watershed` binary | make-watershed-bem, bem | FreeSurfer install |
| `mkheadsurf` (Perl script) | coreg (`make_scalp_surfaces`) | FreeSurfer install + `perl` + `mni/` Perl5 libs |
| Qt offscreen 3D render (`pyvistaqt`) | coreg, forward, source-estimate, label-timecourse | `pyvistaqt`+`qtpy`+`PyQt5` + Qt/XCB libs |
| `fsaverage` template subject | forward, source-estimate, label-timecourse (fallback paths) | baked in at `/opt/mne_data/subjects` |

No app calls an MCR/MATLAB-runtime-dependent FreeSurfer tool
(`mri_normalize`, `talairach_avi`, `mris_ca_label`, `qatools.sh`, …), so the
MATLAB Compiler Runtimes that dominate the old image are not installed.

## Why the old image is 15.52 GB (and this one is ~8.4 GB)

Recovered `brainlife/mne-freesurfer:7.3.2-1.2.1`'s recipe from its published
config blob (same technique as `../docker-mne/README.md`: `docker manifest
inspect` for layer sizes + pull the config blob from the registry API for the
full `history`). It's the same bloat pattern diagnosed for `brainlife/mne:1.8.0`:
built on a CentOS7 base with FreeSurfer 7.3.2, then a **second** full MATLAB
Compiler Runtime bolted on, each runtime duplicated by a separate `chmod -R`
layer:

| size | layer |
|---|---|
| 6.57 GB | `curl .../freesurfer-...-7.3.2.tar.gz \| tar xvz` |
| 2.69 GB | `fs_install_mcr R2019b` (installs 2nd MCR, MCRv97) |
| 2.69 GB | `chmod -R +rx /usr/local/freesurfer/MCRv97` |
| 0.97 GB | `git clone mne-bids-pipeline` (unused by any app) |
| 0.61 GB | `chmod -R +rx /usr/local/freesurfer/MCRv84` |
| 0.61 GB | download of MCRv84 (the runtime FreeSurfer already ships) |
| ... | `yum groupinstall Development Tools`, build Python 3.10.2 from source, ImageMagick, etc. |

`chmod -R` in its own `RUN` after the install rewrites a second full copy of
every file it touches, because Docker layers are additive content diffs — that
duplication alone is the 2.69+2.69 and 0.61+0.61 GB near-identical pairs.
Twelve-plus GB of that image is two MATLAB runtimes that no app in scope even
uses. Full root-cause writeup: `../docker-mne/README.md`.

## The new image

```dockerfile
FROM brainlifemeeg/mne:1.12.1

RUN apt-get update && apt-get install -y --no-install-recommends \
        libegl1 libglu1-mesa libxmu6 libxi6 libfreetype6 libxft2 \
        libxcb-xinerama0 libxcb-cursor0 libxcb-icccm4 libxcb-image0 \
        libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 \
        xauth bc tcsh gawk perl wget \
    && rm -rf /var/lib/apt/lists/*

ENV FREESURFER_HOME=/opt/freesurfer
ENV PATH="${FREESURFER_HOME}/bin:${PATH}"
ENV MNE_DATA=/opt/mne_data
ENV SUBJECTS_DIR=/opt/mne_data/subjects

RUN mkdir -p "${FREESURFER_HOME}" && \
    wget -qO /tmp/freesurfer.tar.gz \
        https://surfer.nmr.mgh.harvard.edu/pub/dist/freesurfer/7.4.1/freesurfer-linux-centos7_x86_64-7.4.1.tar.gz && \
    tar --no-same-owner -xzf /tmp/freesurfer.tar.gz -C /opt && \
    rm /tmp/freesurfer.tar.gz && \
    rm -rf "${FREESURFER_HOME}"/{trctrain,diffusion,docs,fsafd,matlab,models,tktools}

RUN pip install --no-cache-dir pyvistaqt qtpy PyQt5

RUN python3 -c "from pathlib import Path; import mne; mne.datasets.fetch_fsaverage(subjects_dir=Path('${SUBJECTS_DIR}'), verbose=True)"

CMD ["python3"]
```

Key differences from the old recipe, each evidence-based (not guessed):
- `FROM brainlifemeeg/mne:1.12.1` instead of a fresh CentOS/Python build —
  reuses the already-solved MNE stack, keeps versions in lockstep.
- **No MCR** — nothing in scope calls an MCR-dependent tool. This alone is
  ~-12 GB.
- FreeSurfer installed in a **single** download+extract+strip `RUN`, so no
  separate `chmod -R` layer duplicates the extracted tree. Strip list
  (`trctrain diffusion docs fsafd matlab models tktools`) matches the one
  proven working by `aunnikri642/app-freesurfer-mne-source-recon`. `mni/`
  and `average/`/`subjects/` are deliberately **kept** (`mkheadsurf`'s Perl5
  libs, and BEM/coreg default-template fallbacks).
- `7.3.2 → 7.4.1` — the version already proven working on this Debian base by
  `aunnikri642`. Note BEM surface geometry from `mri_watershed` can shift
  slightly across FreeSurfer point releases vs. the old `7.3.2` image.
- Dropped the unused `mne-bids-pipeline` clone (inherited-clean from the base
  image, which never had it).
- No baked-in `FS_LICENSE` — every app injects it at runtime
  (`singularity exec --env FS_LICENSE=...` or `-B .../license.txt:/opt/freesurfer/license.txt`);
  the old image didn't bake one either.

## Verification (all passed locally)

- All FreeSurfer binaries present and report 7.4.1: `mri_watershed`,
  `mkheadsurf`, `recon-all`, `mri_convert`, `mri_info`,
  `mris_anatomical_stats`.
- `perl` runs; `pyvistaqt` 3D backend initializes under
  `QT_QPA_PLATFORM=offscreen`.
- `mne.datasets.fetch_fsaverage()` (no args) resolves to the baked-in copy at
  `/opt/mne_data/subjects/fsaverage` without re-downloading.
- **End-to-end**: `mne.bem.make_watershed_bem('fsaverage', ...)` (with a
  license bind-mounted, as the apps do) runs `mri_watershed` to completion
  and produces all four BEM surfaces (`inner_skull`, `outer_skull`,
  `outer_skin`, `brain`) — the exact code path `make-watershed-bem` and
  `app-bem-v2` use. Without a license it fails only at FreeSurfer's license
  gate, confirming the wiring is otherwise complete.
- Final image ~8.4 GB compressed vs. 15.52 GB for the old image (~46%
  smaller), with no MCR and no chmod-duplication artifacts.

## Investigation commands (no local image pull needed)

```bash
# tag list + sizes
curl -s "https://hub.docker.com/v2/repositories/brainlife/mne-freesurfer/tags?page_size=100"

# per-layer sizes for a tag
docker manifest inspect brainlife/mne-freesurfer:7.3.2-1.2.1

# full build history (reconstructed Dockerfile) — pull the config blob directly
TOKEN=$(curl -s "https://auth.docker.io/token?service=registry.docker.io&scope=repository:brainlife/mne-freesurfer:pull" \
  | python3 -c "import json,sys;print(json.load(sys.stdin)['token'])")
curl -sL -H "Authorization: Bearer $TOKEN" \
  "https://registry-1.docker.io/v2/brainlife/mne-freesurfer/blobs/sha256:<config-digest-from-manifest>" \
  | python3 -m json.tool
```

## Still open

- **Only `make-watershed-bem` is switched to this image so far** — it's the
  one FreeSurfer-using app currently in this repo. The `obVdo/app-*-v2`
  source-pipeline apps still point at `brainlife/mne-freesurfer:7.3.2-1.2.1`
  or `aunnikri642/app-freesurfer-mne-source-recon`; repoint them here once
  they're onboarded into this repo.
- **`app-bem-v2` looks like a superset of `make-watershed-bem`** (watershed
  BEM + BEM model/solution in one app). `make-watershed-bem` may be
  retired/merged once `app-bem-v2` lands — TBD.
- **Further FreeSurfer stripping** (`average/`, `fsfast/`, `sessions/`) could
  shave more, but risks breaking BEM/coreg fallback paths — needs its own
  build+test cycle before attempting.
- **`make-watershed-bem/main` resource directives** (`ppn=8`,
  `walltime=10:00:00`, `vmem=20gb`, no `#SBATCH --mem`) follow the same stale
  pattern fixed for `evoked-averaged` — worth right-sizing against a real
  cached-image run.
