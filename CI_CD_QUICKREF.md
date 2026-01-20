# CI/CD Quick Reference

## What Was Set Up

**3 GitHub Actions Workflows** + **Local Pre-commit Hooks** for comprehensive testing and code quality

### Workflows

| Workflow | Trigger | Tests | Time |
|----------|---------|-------|------|
| `test.yml` | push, PR, weekly | Python 3.10/3.11/3.12, linting, configs | ~2 min |
| `app-tests.yml` | on app changes | App structure, imports, config | ~2 min |
| `quality.yml` | push, PR | Security, types, docstrings | ~2 min |

## Getting Started

### 1. Initialize Local Development
```bash
./setup-ci.sh
```

### 2. Make Changes
Code normally - pre-commit hooks run automatically

### 3. Push to GitHub
```bash
git push origin master
```

### 4. Watch Workflows
Go to GitHub Actions tab - workflows run automatically

## Commands

### Local Testing
```bash
# Run all checks
pre-commit run --all-files

# Fix formatting automatically
black . && isort .

# Check specific tool
flake8 .           # Linting
mypy app-*/main.py # Type checking
bandit -r app-*    # Security
```

### Install Tools Manually
```bash
pip install black isort flake8 mypy bandit pre-commit

# Initialize hooks
pre-commit install
```

## Files Created

### Workflows (3)
- `.github/workflows/test.yml` - Main tests
- `.github/workflows/app-tests.yml` - Per-app testing
- `.github/workflows/quality.yml` - Code quality

### Config (4)
- `pyproject.toml` - Python tools
- `.flake8` - Linting rules
- `.isort.cfg` - Import sorting
- `.pre-commit-config.yaml` - Pre-commit hooks

### Tools (1)
- `setup-ci.sh` - Setup script

### Docs (2)
- `CI_CD_SETUP.md` - Detailed guide
- `CI_CD_COMPLETE.md` - Full summary

## Customization

### Change Line Length (120 → 100)
Edit these files:
```
pyproject.toml:           line-length = 100
.flake8:                  max-line-length = 100
.isort.cfg:               line_length = 100
.github/workflows/*.yml:  args: [--max-line-length=100]
```

### Skip Pre-commit Check
```bash
git commit --no-verify
```
(Not recommended!)

### Disable a Workflow
```bash
mv .github/workflows/quality.yml .github/workflows/quality.yml.disabled
```

## Status Badges

Add to README.md:
```markdown
[![Tests](https://github.com/YOUR/REPO/actions/workflows/test.yml/badge.svg)](https://github.com/YOUR/REPO/actions)
[![Code Quality](https://github.com/YOUR/REPO/actions/workflows/quality.yml/badge.svg)](https://github.com/YOUR/REPO/actions)
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Pre-commit not running | Run `./setup-ci.sh` |
| Workflows not showing | Enable Actions in Settings |
| Tests failing locally | Run `pre-commit run --all-files` |
| Black conflicts | Run `black . && git add .` |
| Missing imports | Run `isort .` |

## Total Setup

- **9 files created/modified**
- **~800 lines of code**
- **12 pre-commit hooks**
- **3 GitHub workflows**
- **7 tools configured**

## Next Steps

1. Run `./setup-ci.sh`
2. Make a test commit
3. Push to GitHub
4. Check Actions tab

---

📖 See `CI_CD_SETUP.md` for complete documentation
