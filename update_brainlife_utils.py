#!/usr/bin/env python3
"""
Update and manage brainlife_utils submodules across multiple directories.

This script finds all submodules named 'brainlife_utils' in the current
directory and its subdirectories, and can update their remote URL or pull
the latest changes.
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def run_command(cmd, cwd=None, capture=False):
    """
    Run a shell command and return the result.
    
    Args:
        cmd: Command to run (string or list)
        cwd: Working directory for the command
        capture: If True, return output; if False, print to console
    
    Returns:
        CompletedProcess object or output string if capture=True
    """
    try:
        if capture:
            result = subprocess.run(cmd, cwd=cwd, shell=isinstance(cmd, str), 
                                  capture_output=True, text=True, check=True)
            return result.stdout.strip()
        else:
            result = subprocess.run(cmd, cwd=cwd, shell=isinstance(cmd, str), 
                                  check=True)
            return result
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {cmd}", file=sys.stderr)
        if capture:
            return ""
        return None


def file_contains(filepath, pattern):
    """Check if a file contains a pattern."""
    try:
        with open(filepath, 'r') as f:
            return pattern in f.read()
    except FileNotFoundError:
        return False


def update_submodule_url(target_dir):
    """
    Update the URL for brainlife_utils submodule in the target directory.
    
    Args:
        target_dir: Directory path to search for .gitmodules
    """
    gitmodules_file = Path(target_dir) / ".gitmodules"
    
    if not gitmodules_file.exists():
        return
    
    # Read the .gitmodules file
    with open(gitmodules_file, 'r') as f:
        content = f.read()
    
    # Check if it contains the brainlife_utils submodule
    if "path = brainlife_utils" not in content:
        return
    
    print(f"Found brainlife_utils submodule in {target_dir}")
    
    # Check if URL needs updating
    old_url = "https://github.com/BrainlifeMEEG/brainlife_utils"
    new_url = "https://github.com/BrainlifeMEEG/BrainlifeMEEG_utils"
    
    if old_url in content:
        print(f"Updating URL for brainlife_utils submodule in {target_dir}")
        
        # Create backup
        backup_file = Path(str(gitmodules_file) + ".bak")
        shutil.copy2(gitmodules_file, backup_file)
        
        # Replace URL
        new_content = content.replace(old_url, new_url)
        with open(gitmodules_file, 'w') as f:
            f.write(new_content)
        
        # Sync submodule
        if target_dir == ".":
            run_command("git submodule sync")
        else:
            run_command("git submodule sync", cwd=target_dir)
        
        print(f"URL updated and synced for {target_dir}/brainlife_utils. "
              f"A backup of .gitmodules was created as .gitmodules.bak")
    else:
        print(f"URL for brainlife_utils submodule in {target_dir} is already "
              f"up to date or different.")


def pull_submodule_changes(target_dir):
    """
    Pull the latest changes from the remote repository for the brainlife_utils submodule.
    
    Args:
        target_dir: Directory path containing the brainlife_utils submodule
    """
    brainlife_utils_path = Path(target_dir) / "brainlife_utils"
    
    if not brainlife_utils_path.exists():
        return
    
    print(f"Pulling latest changes for brainlife_utils submodule in {target_dir}")
    # if we're not on a branch, check out master
    current_branch = run_command("git rev-parse --abbrev-ref HEAD", cwd=brainlife_utils_path, capture=True)
    if current_branch == "HEAD":
        run_command("git checkout master", cwd=brainlife_utils_path)
    # Pull latest changes
    run_command("git pull", cwd=str(brainlife_utils_path))
    
    # Commit changes in parent repository
    run_command("git add brainlife_utils", cwd=target_dir)
    run_command(["git", "commit", "-m", "Update brainlife_utils submodule to latest version"], 
                cwd=target_dir)
    
    print(f"Changes committed for {target_dir}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Update and manage brainlife_utils submodules"
    )
    parser.add_argument(
        "--pull",
        action="store_true",
        help="Pull the latest changes for brainlife_utils submodule"
    )
    parser.add_argument(
        "--url",
        action="store_true",
        help="Update the URL for brainlife_utils submodule"
    )
    parser.add_argument(
        "target_directory",
        nargs="?",
        default=".",
        help="The directory to search for submodules (default: current directory)"
    )
    
    args = parser.parse_args()
    
    # Determine which operation to perform
    if not args.pull and not args.url:
        # Default behavior: pull changes
        args.pull = True
    
    # If target_directory is provided and not ".", process it
    if args.target_directory != ".":
        if args.url:
            update_submodule_url(args.target_directory)
        if args.pull:
            pull_submodule_changes(args.target_directory)
    else:
        # Iterate over all directories in the current directory
        for item in Path(".").iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                if args.url:
                    update_submodule_url(str(item))
                if args.pull:
                    pull_submodule_changes(str(item))
    
    print("Script finished.")


if __name__ == "__main__":
    main()
