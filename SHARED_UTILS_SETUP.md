# Brainlife Apps Shared Utilities

This approach uses Git submodules to share utilities across Brainlife.io apps.

## Setup for Shared Utils Repository

1. **Create a separate Git repository** for the shared utilities:
   ```bash
   cd brainlife_utils/
   git init
   git add .
   git commit -m "Initial commit of shared utilities"
   git remote add origin https://github.com/dnacombo/brainlife-utils.git
   git push -u origin main
   ```

2. **Add as submodule in each app**:
   ```bash
   cd app-your-app/
   git submodule add https://github.com/dnacombo/brainlife-utils.git brainlife_utils
   git commit -m "Add shared utilities submodule"
   ```

## Option 2: Copy Pattern with Version Control

Create a template script that copies the latest utilities into each app:

1. **Version the utilities** in a central repository
2. **Copy utilities** during app development/release
3. **Include in each app's container** 

## Option 3: Package Distribution

Create a Python package and install it in the Docker images:

1. **Create setup.py** for the utilities package
2. **Publish to PyPI** or private registry  
3. **Install via pip** in Docker containers

## Recommended Implementation

For Brainlife.io apps, with Git Submodules:

- ✅ Works with separate repositories
- ✅ Version control for utilities
- ✅ No external dependencies
- ✅ Works in Docker containers
- ✅ Automatic updates possible

## Usage in Apps

After adding submodule, use in `main.py`:

```python
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'brainlife_utils'))

from brainlife_utils import load_config, setup_matplotlib_backend, ensure_output_dirs
```
