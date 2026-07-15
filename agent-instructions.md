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

2. **`main.py`** - Main Python script that:
   - No ad-hoc definitions for "main" or "generate-report" or "apply_filter" functions, but rather a single main.py that handles all processing steps for the app
   - Loads configuration from `config.json`
   - Ensure required output directories exist (e.g. `out_dir`, `out_figs`, `out_report`)
   - Processes neuroimaging data using MNE-Python
   - Ensure required output directories exist (e.g. `out_dir`, `out_figs`, `out_report`)
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
- Apps use Brainlife.io Docker images.
- Executed via Singularity for HPC compatibility

### Output Structure
- `out_dir/` - Primary data outputs (e.g., `raw.fif`, `meg-epo.fif`)
- `out_figs/` - PNG plots and visualizations
- `out_report/` - HTML reports (MNE Report html)
- `product.json` - Metadata for Brainlife.io interface

### Configuration Handling
- JSON configurations with parameter validation
- Helper functions for None value conversion

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
- Use `create_product_json()` and `add_image_to_product()` for Brainlife.io outputs
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
- Apps should add a warning to product.json upon missing or invalid inputs.
- Include parameter validation
- Test with various data formats and configurations
- Ensure outputs are compatible with downstream apps

