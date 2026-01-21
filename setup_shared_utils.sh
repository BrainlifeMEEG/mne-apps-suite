#!/bin/bash

# Script to copy shared utilities to all Brainlife apps
# This script copies the brainlife_utils directory into each app for containerized deployment

UTILS_DIR="/home/maximilien.chaumon/liensNet/analyse/BRAINLIFE/code/brainlife_utils"
CODE_DIR="/home/maximilien.chaumon/liensNet/analyse/BRAINLIFE/code"

echo "Copying shared utilities to Brainlife apps..."

# Check if utils directory exists
if [ ! -d "$UTILS_DIR" ]; then
    echo "Error: Utils directory not found at $UTILS_DIR"
    exit 1
fi

# Find all app directories
for app_dir in "$CODE_DIR"/app-* "$CODE_DIR"/app_*; do
    if [ -d "$app_dir" ]; then
        app_name=$(basename "$app_dir")
        echo "Processing $app_name..."
        
        # Copy utils directory to app
        if [ -d "$app_dir/brainlife_utils" ]; then
            echo "  - Removing existing brainlife_utils..."
            rm -rf "$app_dir/brainlife_utils"
        fi
        
        cp -r "$UTILS_DIR" "$app_dir/brainlife_utils"
        echo "  ✓ Copied brainlife_utils"
        
        # Check if app has main.py and suggest import
        if [ -f "$app_dir/main.py" ]; then
            echo "  - App has main.py - remember to add imports"
        fi
    fi
done

echo ""
echo "Setup complete!"
echo ""
echo "To use in your apps, add these imports at the top of main.py:"
echo ""
echo "import sys"
echo "import os"
echo "sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'brainlife_utils'))"
echo ""
echo "# Import specific utilities you need:"
echo "from brainlife_utils import load_config, setup_matplotlib_backend, ensure_output_dirs"
echo "from brainlife_utils import create_product_json, add_image_to_product"
echo ""
echo "For Git submodule approach, see SHARED_UTILS_SETUP.md"
