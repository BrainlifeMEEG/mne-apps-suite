# Brainlife.io MNE Apps - Instructions

## Project Overview

This is a collection of Brainlife.io applications for neuroimaging data processing, specifically focused on MEG/EEG data analysis using the MNE-Python library. Each folder contains a separate app with a standardized structure for processing neuroimaging data through containerized Python scripts.

## Project Structure

### App Organization
- Each folder contains a complete Brainlife.io application
- Apps follow a consistent pattern for neuroimaging data processing workflows
- Apps are designed to run in Docker/Singularity containers via the Brainlife.io platform

### Standard App Components

Every app typically contains:

1. **`main`** - Bash script that:
   - Sets up PBS/SLURM job parameters
   - Executes the Python script via Singularity container
   - The Python entrypoint invoked must be named exactly `main.py` — no alternate entrypoint filenames are permitted

2. **`main.py`** - Main Python script that:
   - No ad-hoc definitions for "main" or "generate-report" or "apply_filter" functions, but rather a single main.py that handles all processing steps for the app
   - Loads configuration from `config.json`
   - Ensures only the output directories the app actually writes to exist — typically some subset of `out_dir`, `out_figs`, `out_report`. Do not create unused output directories
   - Processes neuroimaging data using MNE-Python
   - Saves outputs to designated directories
   - Generates reports and visualizations as needed
   - Creates `product.json` for Brainlife.io interface as needed

3. **`config.json`** - Configuration file containing example:
   - Input file paths
   - Processing parameters such as
    - Channel selections
    - Filter settings
    - Event mappings
   - No comment fields
   - Required for every app that exposes user-configurable parameters; apps with no parameters may omit it, but must still call `load_config()` with sane defaults
   - A `config.json.example` alone is never sufficient — if example values are meant to be used for testing, `config.json` itself must also exist

4. **`README.md`** - Documentation including:
   - App description and functionality
   - Input/output specifications
   - Citations and acknowledgments: "Hayashi, S., Caron, B.A., Heinsfeld, A.S. et al. brainlife.io: a decentralized and open-source cloud platform to support neuroscience research. Nat Methods 21, 809–813 (2024). https://doi.org/10.1038/s41592-024-02237-2"
   - Brainlife.io badges and metadata

5. **`brainlife_utils/`** - Shared utility library containing:
   - must be a real git submodule: git submodule add git@github.com:BrainlifeMEEG/brainlifeMEEG_utils.git brainlife_utils. A plain copied `brainlife_utils/` directory (no `.git`) is non-compliant — it cannot receive upstream fixes and will drift
   - Configuration handling (`config_utils.py`)
   - File operations (`file_utils.py`)
   - Data processing helpers (`data_utils.py`)
   - Report generation (`report_utils.py`)
   - Plotting utilities (`plot_utils.py`)
   - No local helper/utility module of any name (`helper.py`, `brainlife_apps_helper/`, or similar) is permitted. All shared logic must live in `brainlife_utils`; if a helper contains logic not yet in `brainlife_utils`, upstream it there first, then remove the local copy.

## Common Patterns

### Data Flow
1. Input: EEG/MEG data files: always `.fif` except for conversion apps (e.g. egi2mne)
2. Processing: MNE-Python analysis functions
3. Output: Processed data files, reports, and visualizations

### Container Usage
- Apps use Brainlife.io Docker images.
- Executed via Singularity for HPC compatibility

### Output Structure
- `out_dir/` - Primary data outputs (e.g., `raw.fif`, `epo.fif`)
- `out_figs/` - PNG plots and visualizations
- `out_report/` - HTML reports (MNE Report html)
- `product.json` - Metadata for Brainlife.io interface

### Configuration Handling
- JSON configurations with parameter validation
- `brainlife_utils.config_utils` provides None-value conversion for config parameters

## App Categories

### Data Conversion Apps (`*2mne`)
- Convert various formats to MNE-compatible `.fif` files
- Examples: `bdf2mne`, `edf2mne`, `ctf2mne`

### Preprocessing Apps (`filter-*`, `*-filter`)
- Apply temporal filters
- Examples: `filter-raw`, `notch-filter`, `temporal-filtering`

### Projector computation for artifact removal (`ICA-*`, `SSP-*`)
- Independent Component Analysis and Signal Space Projection
- Examples: `ICA-fit`, `ICA-apply`, `SSP-projectors-ECG`

### Epoching and Events (`epoch*`, `events*`)
- Event detection and epoch extraction
- Examples: `epoch`, `events`

### Analysis Apps (`psd`, `peak-*`)
- Spectral analysis and feature extraction
- Examples: `psd`, `peak-amplitude`, `detect-alpha-peak`

## Development Guidelines

### When Creating New Apps:
1. Follow the standard directory structure
2. Use appropriate Brainlife.io Docker images
3. Implement proper error handling and validation
4. Generate MNE Reports for quality control
5. Create informative `product.json` outputs
6. Include comprehensive documentation

### Code Conventions:
- Import MNE-Python and standard scientific libraries
- Use shared utilities from `brainlife_utils` package
- Use `load_config()` for configuration loading and preprocessing
- Use `setup_matplotlib_backend()` for headless execution
- Use `ensure_output_dirs()` for creating output directories
- Build `product.json` via the `product_items` accumulator pattern — see "Product Metadata Convention" below
- Generate base64-encoded images for web display

### Output file naming conventions:
- Raw data files should be called raw.fif
- Epoched data files should be called epo.fif
- Evoked data files should be called ave.fif
- ICA solutions should be called ica.fif
- SSP/ECG/EOG projectors should be called proj.fif
- Any other derived artifact not covered above should use `<type>.fif` with the MNE-conventional suffix — never a custom filename
- reports are all called report.html

### Shared Utilities Usage:
```python
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'brainlife_utils'))

from brainlife_utils import (
    load_config, 
    setup_matplotlib_backend, 
    ensure_output_dirs,
    create_product_json,
    add_image_to_product,
    add_info_to_product,
    add_raw_info_to_product
)

# Set up environment
setup_matplotlib_backend()
config = load_config()
ensure_output_dirs('out_dir', 'out_figs', 'out_report')  # only the dirs this app actually writes to

# Build product.json — see "Product Metadata Convention" below for the full pattern
```

## Product Metadata Convention (Required)

For all apps, always build `product.json` using an explicit list accumulator.

Required pattern:
```python
product_items = []
add_info_to_product(product_items, "message")
add_raw_info_to_product(product_items, raw)
add_image_to_product(product_items, "Figure title", filepath="out_figs/plot.png")
create_product_json(product_items)
```

Rules:
- Initialize `product_items = []` before any `add_*_to_product` call.
- Pass `product_items` as the **first argument** to all relevant helpers:
  - `add_info_to_product`
  - `add_raw_info_to_product`
  - `add_image_to_product`
  - `add_plotly_to_product`
- Do not use `product_json = create_product_json()` as an accumulator.
- Call `create_product_json(product_items)` only after all product items are added.

### Testing Considerations:
- A missing or invalid required config key must produce an `add_info_to_product` warning and a clean exit — never an uncaught stack trace.
- Every processing parameter read from `config.json` must be validated (type/range/allowed values) before use.
- Output `.fif` files must load successfully with the corresponding MNE reader (`mne.io.read_raw_fif`, `mne.read_epochs`, etc.) before the app exits successfully.

## Repository Hygiene

- When an app is renamed or retired, remove its entry from the root `.gitmodules` — do not leave orphaned submodule declarations pointing at a directory that no longer exists.

## CLI use and Brainlife documentation

### Documentation

- User/app docs live at https://brainlife.io/docs — sections cover Projects, Processes, Pipelines, Apps (registration, `config.json.schema`, `product.json`), Datatypes, Resources, Publications.
- Source for these docs (to check for very recent additions before they're indexed by search): https://github.com/brainlife/docs — e.g. `docs/user/*.md`, `docs/apps/*.md`, `docs/cli/*.md`, `docs/technical/api.md`.
- The docs site can lag behind the live platform by months — new UI features (e.g. the "save pipeline group as workflow" feature added July 2026) may only be discoverable by inspecting the deployed app directly (see "Direct API calls" below for how), not by reading the docs.

### CLI

- Install: `sudo npm install -g brainlife` (npm package name is `brainlife`, the binary is `bl`).
- Login: `bl login --ttl 7` (the `--ttl` is the token lifetime in days).
- Source: https://github.com/brainlife/cli — install/usage docs per subcommand at https://brainlife.io/docs/cli/ (`install`, `upload`, `download`, `app`, `group`, `update`).
- CLI coverage is intentionally limited — it wraps the Warehouse API for common tasks (upload/download datasets, submit/query apps, manage projects). For anything it doesn't support, fall back to direct API calls.

### Direct API calls

Brainlife is a set of microservices, each with its own base URL under `brainlife.io`. All of them expect `Authorization: Bearer <jwt>` (the JWT from `bl login`, or from the `auth` service directly).

| Service | Base URL | Purpose | API docs |
|---|---|---|---|
| Warehouse | `https://brainlife.io/api/warehouse` | Projects, datasets, apps, pipelines/rules, workflows, tasks | https://brainlife.github.io/warehouse/apidoc |
| Amaretti | `https://brainlife.io/api/amaretti` | Task submission/monitoring on compute resources | https://brainlife.github.io/amaretti/apidoc |
| Auth | `https://brainlife.io/api/auth` | Login, profile, JWT issuance | source is private; contact brainlife devs for details |
| Event | `https://brainlife.io/api/event` | Event bus (also exposed as a websocket) | — |

More detail: https://brainlife.io/docs/technical/api and the corresponding source in the docs repo (`docs/technical/api.md`).

Practical tip for reverse-engineering a feature that isn't documented yet: the warehouse UI (a Vue 2 app) is served at `brainlife.io` as `/static/js/app.<hash>.js` plus lazy-loaded numbered chunks (`/static/js/<n>.<hash>.js`, hash map is in `/static/js/manifest.<hash>.js`). Grepping the deployed bundle for a UI string (e.g. a button's tooltip text) is often faster than digging through GitHub when the public repo hasn't caught up to production yet.
