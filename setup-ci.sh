#!/bin/bash
# Setup CI/CD infrastructure for local development
# Usage: ./setup-ci.sh

set -e

echo "🚀 Setting up CI/CD Infrastructure"
echo "===================================="
echo ""

# Check if pre-commit is installed
if ! command -v pre-commit &> /dev/null; then
    echo "📦 Installing pre-commit..."
    pip install pre-commit
else
    echo "✓ pre-commit already installed"
fi

# Install pre-commit hooks
echo ""
echo "🔧 Installing pre-commit hooks..."
pre-commit install

# Run against all files
echo ""
echo "🔍 Running pre-commit checks on all files..."
echo "   (This may take a moment...)"
pre-commit run --all-files || {
    echo ""
    echo "⚠️  Some pre-commit checks failed."
    echo "   Review the output above and fix issues before committing."
    echo ""
    echo "   You can:"
    echo "   1. Manually fix issues and run: pre-commit run --all-files"
    echo "   2. Auto-fix some issues: black . && isort ."
    echo "   3. Review specific tool output for guidance"
    exit 1
}

echo ""
echo "✅ CI/CD Setup Complete!"
echo ""
echo "Next steps:"
echo "  1. Commit changes: git add . && git commit -m 'ci: add CI/CD infrastructure'"
echo "  2. Push to GitHub: git push origin master"
echo "  3. Go to GitHub Actions to watch workflows run"
echo ""
echo "To run checks manually:"
echo "  - All checks: pre-commit run --all-files"
echo "  - Specific tool: black . || isort . || flake8 ."
echo ""
echo "GitHub Workflows:"
echo "  - Test Suite: Python 3.10/3.11/3.12, linting, validation"
echo "  - App Integration: Test changed apps"
echo "  - Code Quality: Linting, type checking, security scan"
echo ""
