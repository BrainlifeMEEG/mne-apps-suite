# Cluster pipeline: `02 -> 04(x2) -> 05 -> 06` for all subjects

Runs the verbatim mne-biomag-group-demo scripts (`../original_scripts/`,
unmodified -- see `../original_scripts/GLITCHES.md`) across all non-excluded
ds000117 subjects in parallel, one Slurm array task per subject.

This directory is our own tooling, kept separate from `original_scripts/`
(which stays an exact, unedited mirror of the downloaded demo scripts).

## Files

- `crosswalk.py` -- openfMRI subject_id <-> BIDS subject id mapping, plus
  which subjects are excluded (matches `library/config.py`'s
  `exclude_subjects`). **Only subject_id 10 (S09) is independently
  verified**; the rest rest on ds000117's README table alone.
- `farm.py` -- builds one subject's slice of the
  `../derivatives/biomag_repro/` symlink farm (idempotent).
- `fetch.py` -- `git annex get`s a subject's raw + proc-sss content if not
  already present locally (idempotent; needs internet egress).
- `run_subject_chain.py` -- runs `02` -> `04` (default `l_freq`, then
  patched to `1` for ICA) -> `05` -> `06` for one subject, via the
  AST-strip technique validated interactively for S09 during Step 0 (parses
  each original script, drops only its trailing module-level "loop over all
  19 subjects" statement(s), calls the resulting function directly -- no
  line inside any original script is edited).
- `submit_pipeline.slurm.sh` -- the Slurm array submission script.
- `prefetch_raw.sh` -- run from a machine with internet access (e.g. the
  dev desktop) before submitting, in case compute nodes don't have egress.

## Usage

```bash
# optional, if compute nodes lack internet access:
./prefetch_raw.sh

# smoke test first -- known-good subject, then one unverified one:
sbatch --array=10 submit_pipeline.slurm.sh
sbatch --array=2   submit_pipeline.slurm.sh

# once those look right:
sbatch submit_pipeline.slurm.sh   # full array, see #SBATCH --array in the script
```

Logs land in `logs/subject_<id>.out` / `.err`.

## Known caveats (carried over from Step 0)

- **Crosswalk unverified for 15/16 subjects.** Don't trust downstream
  results for a subject until its row has been through the Stage 1/2
  cross-check described in the Step 0 plan.
- **Memory sizing (`--mem=32G`) is calibrated from S09 only.** `06` peaked
  at 20.82 GB for S09; other subjects may differ. Check `sacct` after the
  first few array tasks.
- **`05-run_ica.py` hardcodes `highpass-1Hz` regardless of `l_freq`** --
  worked around in `run_subject_chain.py` by running `04` twice (see
  `GLITCHES.md` for the full writeup); not a bug in our tooling.
