# CI/CD Setup Guide for Brainlife.io Apps

This guide explains how to set up and manage Continuous Integration/Continuous Deployment (CI/CD) for the Brainlife.io MNE apps suite.

## Overview

The CI/CD system includes:

1. **Test Suite** (`.github/workflows/test.yml`) - Syntax, linting, and general validation
2. **App Integration Tests** (`.github/workflows/app-tests.yml`) - Test individual apps
3. **Code Quality** (`.github/workflows/quality.yml`) - Linting, type checking, security

## Quick Start

### GitHub Actions Setup

1. **Ensure .github/workflows/ exists**:
   ```bash
   mkdir -p .github/workflows
   ```

2. **Copy workflow files**:
   The CI/CD workflows are located in `.github/workflows/`:
   - `test.yml` - Main test pipeline
   - `app-tests.yml` - App-specific tests
   - `quality.yml` - Code quality checks

3. **Commit and push**:
   ```bash
   git add .github/workflows/
   git commit -m "ci: add GitHub Actions CI/CD workflows"
   git push origin master
   ```

4. **Enable Actions** (if needed):
   - Go to repository Settings → Actions → Allow all actions

## Workflow Details

### 1. Test Suite (`test.yml`)

**Triggers**: On push to master/develop/refactor-*, on PR, weekly schedule

**What it does**:
- Tests Python 3.10, 3.11, 3.12 compatibility
- Lints code with flake8
- Checks formatting with black
- Validates import order with isort
- Validates JSON configs
- Checks documentation completeness

**Key validations**:
```bash
# Syntax errors
flake8 . --select=E9,F63,F7,F82

# Code formatting
black --check .

# Import sorting
isort --check-only .

# JSON validation
for config in */config.json; do json.loads($config); done
```

**Artifacts**:
- None (validation-only)

**Success criteria**:
- No syntax errors
- Code passes formatting checks
- All JSON files are valid
- Documentation files present

### 2. App Integration Tests (`app-tests.yml`)

**Triggers**: On push/PR when app files change

**What it does**:
- Detects which apps changed
- Tests app structure (main.py, config.json, README.md)
- Validates Python imports
- Checks brainlife_utils integration
- Generates app reports

**Key validations**:
```bash
# Required files
for file in main.py main config.json README.md; do
  [ -f $file ] || exit 1
done

# Python syntax
python -m py_compile main.py

# Imports
python -c "import ast; ast.parse(open('main.py').read())"

# Config structure
json.load(open('config.json'))
```

**Test matrix**:
- Runs on multiple Python versions
- Parallelized per app
- Skips if no apps changed

**Artifacts**:
- Test reports per app

### 3. Code Quality (`quality.yml`)

**Triggers**: On push/PR

**What it does**:
- Flake8 linting
- Code formatting check (black)
- Import order check (isort)
- Security scan with bandit
- Type checking with mypy
- Docstring coverage analysis
- Dependency version checking

**Key validations**:
```bash
# Linting
flake8 . --max-line-length=120

# Type checking
mypy app-*/main.py --ignore-missing-imports

# Security
bandit -r . --skip B101,B601,B607

# Docstrings
for func in $(ast.parse(...)); do
  if not ast.get_docstring(func): warnings++
done
```

## Configuration

### Python Versions

Edit test matrix in `.github/workflows/test.yml`:
```yaml
strategy:
  matrix:
    python-version: ['3.10', '3.11', '3.12']  # Add/remove versions
```

### Linting Rules

#### Flake8 Configuration

Edit in `test.yml` and `quality.yml`:
```yaml
# E203: Whitespace before ':'
# W503: Line break before binary operator
# W504: Line break after binary operator
run: flake8 . --ignore=E203,W503,W504 --max-line-length=120
```

#### Black Configuration

Create `.black` or `pyproject.toml`:
```toml
[tool.black]
line-length = 120
target-version = ['py310', 'py311', 'py312']
```

#### Isort Configuration

Create `.isort.cfg`:
```ini
[settings]
profile = black
line_length = 120
multi_line_mode = 3
include_trailing_comma = true
force_grid_wrap = 0
use_parentheses = true
ensure_newline_before_comments = true
```

### MNE-Python Data

The workflows use `mne[data]` which downloads sample datasets. To speed up CI:

```yaml
- name: Cache MNE data
  uses: actions/cache@v3
  with:
    path: ~/.mne
    key: mne-data-v1
```

## Local Testing

### Run Tests Locally

```bash
# Install test dependencies
pip install pytest pytest-cov flake8 black isort mypy bandit

# Run linting
flake8 . --max-line-length=120
black --check .
isort --check-only .

# Run type checking
mypy app-*/main.py --ignore-missing-imports

# Run security scan
bandit -r app-* brainlife_utils
```

### Pre-commit Hooks

Set up automatic checks before commit:

```bash
# Install pre-commit
pip install pre-commit

# Create .pre-commit-config.yaml
cat > .pre-commit-config.yaml << 'EOF'
repos:
  - repo: https://github.com/psf/black
    rev: 23.12.1
    hooks:
      - id: black
        language_version: python3.11

  - repo: https://github.com/PyCQA/flake8
    rev: 6.1.0
    hooks:
      - id: flake8
        args: ['--max-line-length=120']

  - repo: https://github.com/PyCQA/isort
    rev: 5.13.2
    hooks:
      - id: isort

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.7.1
    hooks:
      - id: mypy
        args: ['--ignore-missing-imports']
EOF

# Install pre-commit hooks
pre-commit install

# Run manually on all files
pre-commit run --all-files
```

## Adding Tests to Your App

### Create test file structure

```bash
app-myapp/
├── main.py
├── config.json
├── README.md
└── tests/
    ├── __init__.py
    ├── test_main.py
    └── test_config.py
```

### Example test file (`tests/test_main.py`)

```python
"""Tests for app-myapp main.py"""

import os
import json
import tempfile
import pytest
import mne


def test_config_loading():
    """Test that config.json is valid JSON"""
    with open('config.json') as f:
        config = json.load(f)
    
    # Check required fields
    assert '_app_id' in config
    assert 'inputs' in config
    assert 'outputs' in config


def test_imports():
    """Test that main.py imports correctly"""
    import importlib.util
    spec = importlib.util.spec_from_file_location("main", "main.py")
    main = importlib.util.module_from_spec(spec)
    # Should not raise ImportError
    spec.loader.exec_module(main)


def test_mne_installed():
    """Test that MNE-Python is available"""
    assert mne.__version__


def test_brainlife_utils_available():
    """Test that brainlife_utils can be imported"""
    import sys
    sys.path.insert(0, os.path.dirname(os.getcwd()))
    import brainlife_utils
    assert hasattr(brainlife_utils, 'load_config')


@pytest.fixture
def sample_config():
    """Fixture providing sample configuration"""
    return {
        "_app_id": "test_app",
        "_app_version": "1.0.0",
        "inputs": [
            {"name": "raw", "datatype": "neuro/raw"}
        ],
        "outputs": [
            {"name": "result", "datatype": "neuro/raw"}
        ]
    }


def test_with_sample_config(sample_config):
    """Test app with sample configuration"""
    assert sample_config['_app_id'] == 'test_app'
```

### Run tests

```bash
pytest app-myapp/tests -v --cov=app-myapp
```

## Branch Protection Rules

Set up rules to require CI checks pass before merge:

### GitHub UI
1. Go to repository Settings → Branches
2. Click "Add rule"
3. Pattern: `master`
4. Require status checks:
   - ✅ test (all versions)
   - ✅ validate-configs
   - ✅ lint
   - ✅ dependencies

## Badge in README

Add CI status badge to main README.md:

```markdown
# Brainlife.io MNE Apps Suite

[![Tests](https://github.com/BrainlifeMEEG/mne-apps-suite/workflows/Test%20Suite/badge.svg)](https://github.com/BrainlifeMEEG/mne-apps-suite/actions)
[![Code Quality](https://github.com/BrainlifeMEEG/mne-apps-suite/workflows/Code%20Quality/badge.svg)](https://github.com/BrainlifeMEEG/mne-apps-suite/actions)
[![App Tests](https://github.com/BrainlifeMEEG/mne-apps-suite/workflows/App%20Integration%20Tests/badge.svg)](https://github.com/BrainlifeMEEG/mne-apps-suite/actions)
```

## Troubleshooting

### Workflow not running

1. Check Actions are enabled: Settings → Actions → Allow all actions
2. Verify file is in `.github/workflows/`
3. Check YAML syntax: `yamllint .github/workflows/test.yml`

### Tests failing locally but passing in CI

1. Clear Python cache: `find . -type d -name __pycache__ -exec rm -r {} +`
2. Clear .pytest_cache: `rm -rf .pytest_cache`
3. Reinstall dependencies: `pip install --force-reinstall -e .`

### Long running workflows

- Parallelize jobs using `matrix` strategy
- Cache dependencies: `pip cache dir` or use actions/setup-python cache
- Only run tests on changed files (see app-tests.yml pattern)

### Insufficient permissions

If workflow fails with permission issues:
1. Go to Settings → Actions → General
2. Workflow permissions: Select "Read and write permissions"

## Docker Build & Push (Optional)

Add workflow to build and push Docker images:

```yaml
# .github/workflows/docker-build.yml
name: Docker Build

on:
  push:
    branches: [master]
    tags: ['v*']

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v2
      - uses: docker/login-action@v2
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      
      - uses: docker/build-push-action@v4
        with:
          context: .
          push: true
          tags: ghcr.io/brainlifemeg/mne-apps:latest
```

## Advanced: Deploy to Brainlife.io

After testing, automatically submit updated apps:

```yaml
# .github/workflows/deploy.yml
name: Deploy to Brainlife

on:
  push:
    branches: [master]
    tags: ['v*']

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Deploy to Brainlife.io
        run: |
          ./push2bl.sh
        env:
          BRAINLIFE_API_KEY: ${{ secrets.BRAINLIFE_API_KEY }}
```

## Monitoring & Notifications

### Email Notifications (GitHub default)

Failures automatically email push author

### Slack Notifications

Add to workflow:

```yaml
- name: Slack Notification
  if: always()
  uses: slackapi/slack-github-action@v1.24.0
  with:
    webhook-url: ${{ secrets.SLACK_WEBHOOK }}
    payload: |
      {
        "text": "CI/CD Workflow: ${{ job.status }}",
        "blocks": [
          {
            "type": "section",
            "text": {
              "type": "mrkdwn",
              "text": "*Build Result*: ${{ job.status }}\n*Commit*: ${{ github.sha }}"
            }
          }
        ]
      }
```

## Summary

Your CI/CD system will now:
- ✅ Test all Python versions
- ✅ Lint and format code
- ✅ Validate configs
- ✅ Check documentation
- ✅ Detect changed apps and test them
- ✅ Generate quality reports
- ✅ Prevent merging broken code

For more info, see [GitHub Actions documentation](https://docs.github.com/en/actions)
