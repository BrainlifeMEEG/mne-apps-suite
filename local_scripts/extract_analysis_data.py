#!/usr/bin/env python3
"""
Extract analysis data from AnalysisSheet.txt files.
Creates individual output files per sample:
- S##_T##_pass1_bad_epochs.txt: pass 1 rejected epoch indices (0-indexed, comma-separated)
- S##_T##_pass2_bad_epochs.txt: pass 2 rejected epoch indices (0-indexed, comma-separated)
- S##_T##_bad_channels.tsv: bad channel information (tab-separated)
- S##_T##_bad_channels.txt: bad channel names (comma-separated)
"""

import re
import glob
import json
import csv
from pathlib import Path
from typing import Dict, List, Any


def extract_bad_channels(content: str) -> List[int]:
    """Extract bad channels from the content."""
    match = re.search(r'Bad channels:\s*([\d\s]+)', content)
    if match:
        channels_str = match.group(1).strip()
        # Split by whitespace and convert to integers
        channels = [int(ch) for ch in channels_str.split() if ch.isdigit()]
        return channels
    return []


def extract_bad_trials_pass(content: str, pass_num: int = 1) -> Dict[str, Any]:
    """
    Extract bad trials for a specific pass.
    pass_num: 1 for first pass, 2 for second pass
    """
    # Split content into lines
    lines = content.split('\n')
    
    # Find all occurrences of "Total No. of rejected epochs:"
    rejection_count = 0
    rejected_indices_list = []
    trials_left_list = []
    
    for i, line in enumerate(lines):
        if 'Total No. of rejected epochs:' in line:
            rejection_count += 1
            
            # Extract count
            match = re.search(r'Total No. of rejected epochs:\s*(\d+)', line)
            if match:
                count = int(match.group(1))
                
                # Find the next "Indices of rejected epochs:" line
                for j in range(i, min(i + 5, len(lines))):
                    if 'Indices of rejected epochs:' in lines[j]:
                        # Extract indices (may span multiple lines)
                        indices_str = lines[j].replace('Indices of rejected epochs:', '').strip()
                        # Continue reading next lines if indices span multiple lines
                        k = j + 1
                        while k < len(lines) and lines[k].strip() and not any(
                            keyword in lines[k] for keyword in [
                                'marked epochs file:', 'rejected file:', 'Total No.', 
                                'ICA file:', 'Subtracted', 'Converted', 'Low-pass',
                                'SEPARATED INTO:', 'Direct:', 'Extreme:', 'Intermediate:'
                            ]
                        ):
                            indices_str += ' ' + lines[k].strip()
                            k += 1
                        
                        indices = [int(idx) for idx in indices_str.split() if idx.isdigit()]
                        rejected_indices_list.append(indices)
                        break
                
                # Find the next "Total No. of trials left:" line
                for j in range(i, min(i + 10, len(lines))):
                    if 'Total No. of trials left:' in lines[j]:
                        match_left = re.search(r'Total No. of trials left:\s*(\d+)', lines[j])
                        if match_left:
                            trials_left = int(match_left.group(1))
                            trials_left_list.append(trials_left)
                        break
    
    result = {
        'rejected_count': None,
        'rejected_indices': None,
        'trials_left': None
    }
    
    if pass_num <= len(rejected_indices_list):
        idx = pass_num - 1
        result['rejected_count'] = len(rejected_indices_list[idx])
        result['rejected_indices'] = rejected_indices_list[idx]
    
    if pass_num <= len(trials_left_list):
        idx = pass_num - 1
        result['trials_left'] = trials_left_list[idx]
    
    return result


def extract_subject_task(filepath: str) -> tuple:
    """Extract subject and task IDs from filename."""
    basename = Path(filepath).stem  # e.g., "Gaze2_S01_T1_Face1"
    
    # Extract S## and T##(_Face1)? from filename
    s_match = re.search(r'S(\d+)', basename)
    t_match = re.search(r'(T\d+(?:_Face1)?)', basename)
    
    if s_match and t_match:
        subject = s_match.group(1)
        task = t_match.group(1)
        return subject, task
    return None, None


def create_bad_channels_file(bad_channels: List[int], subject: str, task: str, output_dir: Path):
    """Create TSV file with bad channels information."""
    # Create TSV file
    filename_tsv = output_dir / f"S{subject}_{task}_bad_channels.tsv"
    
    with open(filename_tsv, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['name', 'status'], delimiter='\t')
        writer.writeheader()
        
        for channel_num in bad_channels:
            writer.writerow({
                'name': f'E{channel_num}',
                'status': 'bad'
            })
    
    # Create comma-separated text file
    filename_txt = output_dir / f"S{subject}_{task}_bad_channels.txt"
    
    with open(filename_txt, 'w') as f:
        if bad_channels:
            channel_names = [f'E{ch}' for ch in bad_channels]
            f.write(','.join(channel_names))


def create_bad_epochs_file_pass1(indices: List[int], subject: str, task: str, output_dir: Path):
    """Create text file with pass 1 rejected epoch indices (0-indexed)."""
    filename = output_dir / f"S{subject}_{task}_pass1_bad_epochs.txt"
    
    with open(filename, 'w') as f:
        if indices:
            # Subtract 1 to convert to 0-based indexing
            zero_indexed = [i - 1 for i in indices]
            f.write(','.join(map(str, zero_indexed)))


def create_bad_epochs_file_pass2(indices: List[int], subject: str, task: str, output_dir: Path):
    """Create text file with pass 2 rejected epoch indices (0-indexed)."""
    filename = output_dir / f"S{subject}_{task}_pass2_bad_epochs.txt"
    
    with open(filename, 'w') as f:
        if indices:
            # Subtract 1 to convert to 0-based indexing
            zero_indexed = [i - 1 for i in indices]
            f.write(','.join(map(str, zero_indexed)))


def process_file(filepath: str, output_dir: Path) -> Dict[str, Any]:
    """Process a single AnalysisSheet.txt file."""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        bad_channels = extract_bad_channels(content)
        pass1 = extract_bad_trials_pass(content, pass_num=1)
        pass2 = extract_bad_trials_pass(content, pass_num=2)
        
        # Extract subject and task
        subject, task = extract_subject_task(filepath)
        
        if subject and task:
            # Create output files
            create_bad_channels_file(bad_channels, subject, task, output_dir)
            create_bad_epochs_file_pass1(pass1['rejected_indices'] or [], subject, task, output_dir)
            create_bad_epochs_file_pass2(pass2['rejected_indices'] or [], subject, task, output_dir)
        
        return {
            'filepath': filepath,
            'subject': subject,
            'task': task,
            'bad_channels': bad_channels,
            'pass1_rejected_count': pass1['rejected_count'],
            'pass1_trials_left': pass1['trials_left'],
            'pass2_rejected_count': pass2['rejected_count'],
            'pass2_trials_left': pass2['trials_left'],
        }
    except Exception as e:
        return {
            'filepath': filepath,
            'error': str(e)
        }


def main():
    """Main function to process all files."""
    base_path = Path.home() / 'liensNet/analyse/BRAINLIFE/datasets/Latinus Data'
    output_dir = Path.cwd() / 'bad_epochs_channels'
    output_dir.mkdir(exist_ok=True)
    
    # Find all AnalysisSheet.txt files matching the pattern
    pattern = str(base_path / 'S*/*AnalysisExplanation/*AnalysisSheet.txt')
    files = sorted(glob.glob(pattern))
    
    print(f"Found {len(files)} files")
    print(f"Output directory: {output_dir}\n")
    
    results = []
    
    for filepath in files:
        data = process_file(filepath, output_dir)
        results.append(data)
        
        # Print summary for each file
        rel_path = filepath.replace(str(base_path), '')
        print(f"File: {rel_path}")
        
        if 'error' in data:
            print(f"  ERROR: {data['error']}\n")
        else:
            print(f"  Subject: S{data['subject']}, Task: {data['task']}")
            print(f"  Bad channels: {len(data['bad_channels'])} channels")
            print(f"  Pass 1 - Rejected count: {data['pass1_rejected_count']}, Trials left: {data['pass1_trials_left']}")
            print(f"  Pass 2 - Rejected count: {data['pass2_rejected_count']}, Trials left: {data['pass2_trials_left']}")
            print()
    
    # Save summary to JSON
    output_json = output_dir / 'summary.json'
    with open(output_json, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"Summary saved to {output_json}")
    
    # Print statistics
    successful = len([r for r in results if 'error' not in r])
    print(f"\nProcessed {successful}/{len(files)} files successfully")
    print(f"Generated {successful} S##_T##_pass1_bad_epochs.txt files")
    print(f"Generated {successful} S##_T##_pass2_bad_epochs.txt files")
    print(f"Generated {successful} S##_T##_bad_channels.tsv files")
    print(f"Generated {successful} S##_T##_bad_channels.txt files")


if __name__ == '__main__':
    main()
