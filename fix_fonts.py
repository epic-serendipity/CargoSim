#!/usr/bin/env python3
"""
Script to fix font specifications with empty strings in CargoSim UI files.
"""

import re
import os

def fix_font_specs(file_path):
    """Fix font specifications with empty strings in a file."""
    print(f"Fixing fonts in {file_path}...")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Count how many font specs with empty strings we found
    empty_font_count = len(re.findall(r'font=\("", [0-9]', content))
    print(f"Found {empty_font_count} font specifications with empty strings")
    
    # Fix font specifications with empty strings
    # Replace font=("", size) with font=("TkDefaultFont", size)
    content = re.sub(r'font=\("", (\d+)(?:, "([^"]*)")?\)', r'font=("TkDefaultFont", \1\2)', content)
    
    # Write the fixed content back
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Fixed font specs in {file_path}")

def main():
    """Main function to fix fonts in all UI files."""
    # Fix the fleet builder GUI file
    fleet_builder_file = 'cargosim/ui/fleet_builder_gui.py'
    if os.path.exists(fleet_builder_file):
        fix_font_specs(fleet_builder_file)
    else:
        print(f"File not found: {fleet_builder_file}")
    
    # Check if there are any remaining font issues
    print("\nChecking for remaining font issues...")
    
    with open(fleet_builder_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    remaining_empty_fonts = re.findall(r'font=\("", [0-9]', content)
    if remaining_empty_fonts:
        print(f"Warning: {len(remaining_empty_fonts)} font specifications with empty strings still remain:")
        for match in remaining_empty_fonts:
            print(f"  {match}")
    else:
        print("All font specifications with empty strings have been fixed!")

if __name__ == "__main__":
    main()
