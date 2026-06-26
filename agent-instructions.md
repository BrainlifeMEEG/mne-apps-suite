# Brainlife.io MNE Apps - Copilot Instructions

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
   - May generate `product.json` for visualization outputs

2. **`main.py`** - Main Python script that:
   - No ad-hoc definitions for "main" or "generate-report" or "apply_filter" functions, but rather a single main.py that handles all processing steps for the app
   - Loads configuration from `config.json`
   - Processes neuroimaging data using MNE-Python
   - Ensure required output directories exist (e.g. `out_dir`, `out_figs`, `out_report`)
   - Saves outputs to designated directories
   - Generates reports and visualizations
   - Creates `product.json` for Brainlife.io interface

3. **`config.json`** - Configuration file containing example:
   - Input file paths
   - Processing parameters such as
    - Channel selections
    - Filter settings
    - Event mappings
   - No comment fields

4. **`README.md`** - Documentation including:
   - App description and functionality
   - Input/output specifications
   - Citations and acknowledgments: "Hayashi, S., Caron, B.A., Heinsfeld, A.S. et al. brainlife.io: a decentralized and open-source cloud platform to support neuroscience research. Nat Methods 21, 809–813 (2024). https://doi.org/10.1038/s41592-024-02237-2"
   - Brainlife.io badges and metadata

5. **`brainlife_utils/`** - Shared utility library containing:
   - should be a submodule: git submodule add git@github.com:BrainlifeMEEG/brainlifeMEEG_utils.git brainlife_utils
   - Configuration handling (`config_utils.py`)
   - File operations (`file_utils.py`)
   - Data processing helpers (`data_utils.py`)
   - Report generation (`report_utils.py`)
   - Plotting utilities (`plot_utils.py`)
   - NO **`helper.py`** should be used. Remove if existing.

## Common Patterns

### Data Flow
1. Input: EEG/MEG data files: always `.fif` except for conversion apps (e.g. egi2mne)
2. Processing: MNE-Python analysis functions
3. Output: Processed data files, reports, and visualizations

### Container Usage
- Apps use Brainlife.io Docker images: `brainlife/mne:x.x.x`
- Executed via Singularity for HPC compatibility
- Matplotlib backend set to 'Agg' for headless rendering

### Output Structure
- `out_dir/` - Primary data outputs (e.g., `raw.fif`, `meg-epo.fif`)
- `out_figs/` - PNG plots and visualizations
- `out_report/` - HTML reports (MNE Report objects)
- `product.json` - Metadata for Brainlife.io interface

### Configuration Handling
- JSON configurations with parameter validation
- Helper functions for None value conversion
- Support for complex parameter mappings (e.g., event IDs)

## App Categories

### Data Conversion Apps (`*2mne`)
- Convert various formats to MNE-compatible `.fif` files
- Examples: `bdf2mne`, `edf2mne`, `ctf2mne`

### Preprocessing Apps (`filter-*`, `*-filter`)
- Apply temporal and spatial filters
- Examples: `filter-raw`, `notch-filter`, `temporal-filtering`

### Projector computation for artifact removal (`ICA-*`, `SSP-*`)
- Independent Component Analysis and Signal Space Projection
- Examples: `ICA-fit`, `ICA-apply`, `SSP-projectors-ECG`

### Epoching and Events (`epoch*`, `events*`)
- Event detection and epoch extraction
- Examples: `epoch`, `events`, `evoked-averaged`

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
- Use `create_product_json()` and `add_image_to_product()` for Brainlife.io outputs
- Handle matplotlib backend for headless execution
- Generate base64-encoded images for web display

### Output file naming conventions:
- Raw data files should be called raw.fif
- Epoched data files should be called epo.fif
- Evoked data files should be called ave.fif
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
ensure_output_dirs('out_dir', 'out_figs', 'out_report')

# Add metadata to product
product_items = []
add_raw_info_to_product(product_items, raw)  # For raw data information
add_image_to_product(product_items, fig, 'plot.png')  # For figures
add_info_to_product(product_items, "Processing message")  # For text messages
create_product_json(product_items)
```

## Product Metadata Convention (Required)

For all refactored apps, always build `product.json` using an explicit list accumulator.

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
- Apps should handle missing or invalid inputs gracefully
- Include parameter validation
- Test with various data formats and configurations
- Ensure outputs are compatible with downstream apps

## App Refactoring Strategy

### Overview
Systematically refactor existing apps to use the shared `brainlife_utils` package, eliminating code duplication and improving maintainability. This follows a consistent 5-step process per app.

### Refactoring Process (5 Steps Per App)

**Step 1: Create Feature Branch**
```bash
git checkout -b refactor-shared-utils
```

**Step 2: Refactor Code**
- Update `main.py` to use `brainlife_utils` instead of local helper.py
- Add module docstring describing inputs/outputs
- Replace direct config loading with `load_config()`
- Replace direct file operations with utility functions
- Use `add_raw_info_to_product()` for raw data reporting
- Use `add_image_to_product()` for figures
- Use `add_info_to_product()` for messages
- Update `README.md` with consistent documentation structure
- Update `config.json` with all supported parameters
- Remove lecacy `helpers.py`


**Author Updates**
- Add Maximilien Chaumon as co-author in README.md Authors section
- If affiliation listed, move it in parentheses after first author (e.g., "Author (Indiana University)")
- Use GitHub handles instead of emails: https://github.com/dnacombo (Maximilien), https://github.com/KSalibay (Kamilya), https://github.com/guiomar (Guiomar), https://github.com/zahransa (Saeed)
- Update copyright year to 2026 in both main.py and README.md
- In main.py, add copyright and authors block after module docstring:
  ```python
  # Copyright (c) 2026 brainlife.io
  #
  # Description of what the app does
  #
  # Authors:
  # - Author Name (https://github.com/username)
  # - Maximilien Chaumon (https://github.com/dnacombo)
  ```

**Step 3: Commit Code Changes**
```bash
git add main.py README.md config.json
git commit -m "refactor: use shared brainlife_utils library"
```

**Step 4: Add Submodule**

Navigate inside the app's directory (e.g., `cd my-app`) and run the following commands:

```bash
git submodule add https://github.com/BrainlifeMEEG/BrainlifeMEEG_utils.git brainlife_utils
git add .gitmodules BrainlifeMEEG_utils
git commit -m "feat: add BrainlifeMEEG_utils as git submodule"
git push
```
**Step 5: Update License to AGPL-3.0**
See license.txt file for details. Copy it to the repo.
Remove legacy MIT LICENSE file.


### Critical Notes
- **product.json is RUNTIME-ONLY**: Never commit product.json to the repository. It is generated at runtime by main.py when executed on Brainlife.io platform. Only the code that creates it (in main.py) should be committed.
- Always follow the module docstring pattern from refactored apps
- Always update README.md to match established documentation structure

### Refactored Apps (Reference Examples)
- `egi2mne`: Complete refactoring with bad channel support
- `interpolate-raw`: Complete refactoring with structured output
- `add-montage`: Complete refactoring with electrode positioning
- `mark_bad-raw`: Complete refactoring with bad channel and annotation handling
- `ICA-apply`: Complete refactoring with component exclusion and artifact detection
- `ICA-fit`: Complete refactoring with EOG/ECG artifact detection
- `ICA-fit-epo`: Complete refactoring for epoched data ICA fitting
- `ICA-apply-epo`: Complete refactoring for epoched ICA application
- `ICA-plot`: Complete refactoring for ICA visualization
- `drop-bad-epo`: Complete refactoring with epoch dropping and file handling

### Documentation Structure in README.md
Use this consistent structure for all refactored apps:
1. **Description** - What the app does
2. **Inputs** - Input files and formats
3. **Outputs** - Output files generated
4. **Configuration Parameters** - List of config.json parameters
5. **Usage** - How to run the app
6. **Technical Details** - MNE-specific details
7. **Authors** - Contribution information
8. **Citations** - Academic citations: "Hayashi, S., Caron, B.A., Heinsfeld, A.S. et al. brainlife.io: a decentralized and open-source cloud platform to support neuroscience research. Nat Methods 21, 809–813 (2024). https://doi.org/10.1038/s41592-024-02237-2"
9. **Funding** - Funding acknowledgments

## Key Dependencies
- MNE-Python (primary neuroimaging library)
- NumPy, SciPy (numerical computing)
- Matplotlib (visualization)
- JSON (configuration handling)
- Brainlife.io platform integration

This project represents a comprehensive suite of neuroimaging analysis tools designed for reproducible, containerized execution on the Brainlife.io cloud platform.
