# Brainlife.io MNE Apps Suite

A comprehensive collection of Brainlife.io applications for MEG/EEG data processing using MNE-Python. This meta-repository coordinates all apps in the suite with shared utilities and standardized workflows.

## Overview

This project provides a modular, containerized infrastructure for neuroimaging data analysis on the Brainlife.io cloud platform. All apps follow consistent design patterns and share common utilities for configuration management, data processing, and reporting.

**Repository**: https://github.com/BrainlifeMEEG/mne-apps-suite  
**Platform**: [Brainlife.io](https://brainlife.io/)  
**Primary Library**: [MNE-Python](https://mne.tools/)

## Quick Start

### Clone with All Submodules

```bash
git clone --recurse-submodules https://github.com/BrainlifeMEEG/mne-apps-suite.git
cd mne-apps-suite
```

### Update Submodules

```bash
# Initialize and update all submodules
git submodule update --init --recursive

# Update all submodules to latest commit
git submodule update --remote --recursive

# Update specific submodule
git submodule update --remote brainlife_utils
```

## Repository Structure

```
mne-apps-suite/
├── brainlife_utils/              # Shared utility library (git submodule)
├── app_*2mne/                    # Data format conversion apps
├── app-*filter*/                 # Filtering & preprocessing
├── app-ICA-*/                    # Independent Component Analysis
├── app-SSP-*/                    # Signal Space Projection
├── app-epoch*                    # Epoching & event handling
├── app-*-epo/                    # Epoched data processing
├── app-info-*/                   # Data information viewers
├── app-psd/                      # Power spectral analysis
├── .gitmodules                   # Git submodule configuration
├── .gitignore                    # Git ignore rules
├── README.md                     # This file
├── REFACTORING_STATUS.md         # Refactoring progress tracker
├── .copilot-instructions.md      # AI assistant guidelines
└── BrainlifeMEEG/                # Meta-repository documentation
```

## App Categories

### Data Conversion (7 apps)
Convert various neuroimaging formats to MNE-compatible `.fif` files:
- `app_bdf2mne` - Biodat BDF conversion
- `app_brainvision2mne` - Brain Vision format
- `app_ctf2mne` - CTF MEG system
- `app_edf2mne` - EDF (EEG Data Format)
- `app_eeglab2mne` - EEGLAB format
- `app_fif2mne` - FIF file refinement
- `app-egi2mne` - EGI NetStation format

### Preprocessing & Channel Operations (5 apps)
- `app-add_flat_chan` - Add flat channel markers
- `app-add-montage` - Set electrode positions
- `app-average-channels` - Channel averaging
- `app-interpolate-raw` - Interpolate bad channels
- `app-mark_bad-raw` - Mark bad channels and segments

### Filtering (4 apps)
- `app-filter-raw` - Temporal filtering on raw data
- `app-filter-epo` - Filtering on epochs
- `app-notch-filter` - Notch filter for line noise
- `app-temporal-filtering` - Advanced temporal filtering

### Epoching & Events (6 apps)
- `app-epoch` - Create epochs from raw data
- `app-drop-bad-epo` - Remove bad epochs
- `app-events` - Detect/extract events
- `app-eventslog` - Event logging and visualization
- `app-evoked-averaged` - Compute evoked averages
- `app-epoch-psd` - Power spectral density of epochs

### ICA (5 apps)
Independent Component Analysis for artifact removal:
- `app-ICA-fit` - Compute ICA on raw data
- `app-ICA-fit-epo` - Compute ICA on epochs
- `app-ICA-apply` - Apply ICA to raw data
- `app-ICA-apply-epo` - Apply ICA to epochs
- `app-ICA-plot` - Visualize ICA components

### SSP (4 apps)
Signal Space Projection for artifact removal:
- `app-SSP-projectors-ECG` - ECG artifact detection
- `app-SSP-projectors-EOG` - EOG artifact detection
- `app-SSP-apply` - Apply SSP projectors
- `app-plot_proj_topomaps-raw` - Visualize projectors

### Analysis & Features (3 apps)
- `app-psd` - Power spectral density analysis
- `app-peak-amplitude` - Peak amplitude detection
- `app-detect-alpha-peak` - Alpha peak frequency detection

### Data Management (4 apps)
- `app-concat` - Concatenate multiple files
- `app-resampling` - Resample data
- `app-info-raw` - Display raw data information
- `app-info-epo` - Display epoch information
- `app-info-evoked` - Display evoked information

### Advanced Processing (4 apps)
- `app-head-pos` - Head position tracking
- `app-maxfilter` - Maxwell filtering (MEG)
- `app-make-watershed-bem` - BEM surface creation
- `app-mean-transformation-matrix` - Compute transformation
- `app-emptyroom-proj` - Empty room projector
- `app-average-erp` - Average event-related potentials

## Shared Utilities

The `brainlife_utils` package provides common functionality across all apps:

- **Configuration Management** - Standardized config.json loading
- **File Operations** - Directory creation, optional file handling
- **Data Processing** - Validation, channel summaries, bad channel handling
- **Report Generation** - product.json creation for Brainlife interface
- **Plotting** - Matplotlib headless setup, figure conversion

See [brainlife_utils/README.md](brainlife_utils/README.md) for detailed documentation.

## Development

### Adding a New App

1. Create app repository with standard structure
2. Add as submodule: `git submodule add <repo-url> <app-name>`
3. Follow refactoring guidelines in `.copilot-instructions.md`
4. Use shared utilities from `brainlife_utils`
5. Update documentation

### Refactoring Progress

See [REFACTORING_STATUS.md](REFACTORING_STATUS.md) for the current status of app refactorings to use shared utilities.

**Completed**: 14 apps ✅
**In Progress**: Additional apps
**Planned**: Full suite integration

### Development Guidelines

- Follow MNE-Python conventions
- Use consistent error handling
- Generate informative output messages
- Create comprehensive documentation
- Test with sample data before release

## Installation & Deployment

### Local Development

```bash
# Clone repository
git clone --recurse-submodules https://github.com/BrainlifeMEEG/mne-apps-suite.git
cd mne-apps-suite

```

### Brainlife.io Deployment

Each app includes:
- `main` - Bash script for job submission
- `config.json` - Parameter templates
- `product.json` - Output interface definition

Apps are containerized using Docker/Singularity and executed on Brainlife.io infrastructure.

## Configuration

Each app uses a `config.json` file with:
- Input file paths
- Processing parameters
- Optional settings

See individual app README.md files for specific parameter documentation.

## Output Structure

Standard output directories generated by apps:
```
out_dir/        # Primary output data files
out_figs/       # PNG visualizations
out_report/     # HTML reports (MNE Report objects)
product.json    # Brainlife interface metadata
```

## Troubleshooting

### Submodule Issues

```bash
# If submodules don't clone properly
git submodule sync --recursive
git submodule update --init --recursive

# Remove problematic submodule
git submodule deinit <path>
git rm <path>
```

### Permission Issues

Some apps may have restricted write permissions. Use:
```bash
git config core.fileMode false
```

### Configuration Errors

Ensure `config.json` is properly formatted JSON with all required fields. Check app-specific documentation for required parameters.

## Contributing

We welcome contributions! Please:

1. Fork the appropriate app repository
2. Create a feature branch (`git checkout -b feature/improvement`)
3. Follow development guidelines
4. Test thoroughly
5. Create a pull request with clear description

## Citation

If you use these apps in research, please cite:

@article{Hayashi2024,
  author  = {Hayashi, Soichi and Caron, Bradley A. and Heinsfeld, Anibal S. and others},
  title   = {brainlife.io: a decentralized and open-source cloud platform to support neuroscience research},
  journal = {Nature Methods},
  year    = {2024},
  volume  = {21},
  number  = {5},
  pages   = {809--813},
  doi     = {10.1038/s41592-024-02237-2},
  url     = {https://doi.org/10.1038/s41592-024-02237-2}
}

And cite the MNE-Python library:

```bibtex
@article{gramfort2013meg,
  title={MEG and EEG data analysis with MNE-Python},
  author={Gramfort, A. and Luessi, M. and Larson, E. and others},
  journal={Frontiers in Neuroscience},
  year={2013}
}
```

## License

All apps are licensed under AGPLv3 or later, as stated in the license.txt file in this repository and the underlying app repositories.

This project uses the following third-party libraries:

## Dependencies
- **MNE-Python**
  Copyright (c) 2011-2026 MNE-Python developers
  Licensed under the 3-Clause BSD License.
  (See https://mne.tools/stable/license.html for details)

## Support & Resources

- **Brainlife.io Documentation**: https://brainlife.io/docs
- **MNE-Python Documentation**: https://mne.tools/
- **GitHub Issues**: Report bugs in individual app repositories
- **Discussions**: Community support on Brainlife forums on https://brainlife.slack.com

## Authors & Acknowledgments

### Core Team
- Maximilien Chaumon (https://github.com/dnacombo)
- Guiomar Niso (https://github.com/guiomar)
- Kami Salibayeva (https://github.com/KSalibay)
- Saeed Zahran (https://github.com/zahransa/)
- Aurore Bussalb (https://github.com/abussalb)
- Franco Pestilli (https://github.com/francopestilli)

### Contributors
See individual app repositories for detailed contributor lists.

## Changelog

### v1.0.0 (January 2026)
- Initial meta-repository setup
- 14 apps refactored to use shared utilities
- Comprehensive documentation
- Git submodule organization

### v1.1.0 (March 2026)
- Updated documentation and license

For detailed changes, see individual app repositories and REFACTORING_STATUS.md.

## Related Projects

- [MNE-Python](https://github.com/mne-tools/mne-python)
- [Brainlife.io](https://github.com/brainlife/)
- [Brainlife Apps Helper](https://github.com/brainlife/brainlife_apps_helper)

---

**Last Updated**: March 20, 2026  
**Repository**: https://github.com/BrainlifeMEEG/mne-apps-suite
