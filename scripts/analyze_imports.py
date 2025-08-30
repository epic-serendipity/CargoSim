#!/usr/bin/env python3
"""Script to analyze relative imports in the CargoSim codebase."""

import os
import re
from pathlib import Path

def find_relative_imports(directory):
    """Find all relative imports in Python files."""
    single_dot_imports = []
    double_dot_imports = []
    triple_dot_imports = []
    
    # Patterns for different types of relative imports
    single_dot_pattern = r'from \.(\w+) import'
    double_dot_pattern = r'from \.\.(\w+) import'
    triple_dot_pattern = r'from \.\.\.(\w+) import'
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        lines = content.split('\n')
                        
                        for line_num, line in enumerate(lines, 1):
                            # Check for single dot imports
                            if re.search(single_dot_pattern, line):
                                single_dot_imports.append({
                                    'file': file_path,
                                    'line': line_num,
                                    'content': line.strip()
                                })
                            
                            # Check for double dot imports
                            if re.search(double_dot_pattern, line):
                                double_dot_imports.append({
                                    'file': file_path,
                                    'line': line_num,
                                    'content': line.strip()
                                })
                            
                            # Check for triple dot imports
                            if re.search(triple_dot_pattern, line):
                                triple_dot_imports.append({
                                    'file': file_path,
                                    'line': line_num,
                                    'content': line.strip()
                                })
                                
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")
    
    return single_dot_imports, double_dot_imports, triple_dot_imports

def categorize_imports(single_dot, double_dot, triple_dot):
    """Categorize imports by complexity and file."""
    categories = {
        'simple': [],
        'medium': [],
        'complex': []
    }
    
    # Simple: single-dot imports
    for imp in single_dot:
        categories['simple'].append({
            'type': 'single_dot',
            'file': imp['file'],
            'line': imp['line'],
            'content': imp['content']
        })
    
    # Medium: double-dot imports
    for imp in double_dot:
        categories['medium'].append({
            'type': 'double_dot',
            'file': imp['file'],
            'line': imp['line'],
            'content': imp['content']
        })
    
    # Complex: triple-dot imports
    for imp in triple_dot:
        categories['complex'].append({
            'type': 'triple_dot',
            'file': imp['file'],
            'line': imp['line'],
            'content': imp['content']
        })
    
    return categories

def generate_report(categories):
    """Generate a comprehensive import analysis report."""
    report = []
    report.append("=" * 80)
    report.append("CARGOSIM RELATIVE IMPORT ANALYSIS REPORT")
    report.append("=" * 80)
    report.append("")
    
    # Summary
    total_imports = sum(len(cat) for cat in categories.values())
    report.append(f"TOTAL RELATIVE IMPORTS FOUND: {total_imports}")
    report.append(f"Simple (single-dot): {len(categories['simple'])}")
    report.append(f"Medium (double-dot): {len(categories['medium'])}")
    report.append(f"Complex (triple-dot): {len(categories['complex'])}")
    report.append("")
    
    # Simple imports
    if categories['simple']:
        report.append("SIMPLE IMPORTS (from .module import ...)")
        report.append("-" * 50)
        for imp in categories['simple']:
            rel_path = os.path.relpath(imp['file'], '.')
            report.append(f"{rel_path}:{imp['line']} - {imp['content']}")
        report.append("")
    
    # Medium imports
    if categories['medium']:
        report.append("MEDIUM IMPORTS (from ..module import ...)")
        report.append("-" * 50)
        for imp in categories['medium']:
            rel_path = os.path.relpath(imp['file'], '.')
            report.append(f"{rel_path}:{imp['line']} - {imp['content']}")
        report.append("")
    
    # Complex imports
    if categories['complex']:
        report.append("COMPLEX IMPORTS (from ...module import ...)")
        report.append("-" * 50)
        for imp in categories['complex']:
            rel_path = os.path.relpath(imp['file'], '.')
            report.append(f"{rel_path}:{imp['line']} - {imp['content']}")
        report.append("")
    
    # Conversion recommendations
    report.append("CONVERSION RECOMMENDATIONS")
    report.append("-" * 50)
    report.append("1. Simple imports: Change 'from .module' to 'from cargosim.module'")
    report.append("2. Medium imports: Change 'from ..module' to 'from cargosim.module'")
    report.append("3. Complex imports: Change 'from ...module' to 'from cargosim.module'")
    report.append("")
    report.append("Priority order:")
    report.append("- Phase 1: Fix complex imports (most error-prone)")
    report.append("- Phase 2: Fix medium imports")
    report.append("- Phase 3: Fix simple imports")
    
    return "\n".join(report)

def main():
    """Main function to analyze imports."""
    print("Analyzing relative imports in CargoSim codebase...")
    
    # Find all relative imports
    single_dot, double_dot, triple_dot = find_relative_imports('cargosim')
    
    # Categorize imports
    categories = categorize_imports(single_dot, double_dot, triple_dot)
    
    # Generate report
    report = generate_report(categories)
    
    # Save report to file
    with open('relative_imports_analysis.txt', 'w', encoding='utf-8') as f:
        f.write(report)
    
    # Also save individual category files
    with open('relative_imports_simple.txt', 'w', encoding='utf-8') as f:
        for imp in categories['simple']:
            f.write(f"{imp['file']}:{imp['line']} - {imp['content']}\n")
    
    with open('relative_imports_medium.txt', 'w', encoding='utf-8') as f:
        for imp in categories['medium']:
            f.write(f"{imp['file']}:{imp['line']} - {imp['content']}\n")
    
    with open('relative_imports_complex.txt', 'w', encoding='utf-8') as f:
        for imp in categories['complex']:
            f.write(f"{imp['file']}:{imp['line']} - {imp['content']}\n")
    
    print("Analysis complete!")
    print(f"Report saved to: relative_imports_analysis.txt")
    print(f"Simple imports: {len(categories['simple'])}")
    print(f"Medium imports: {len(categories['medium'])}")
    print(f"Complex imports: {len(categories['complex'])}")
    
    # Print summary to console
    print("\n" + "="*50)
    print("QUICK SUMMARY")
    print("="*50)
    print(f"Total relative imports found: {sum(len(cat) for cat in categories.values())}")
    
    if categories['complex']:
        print(f"\n⚠️  {len(categories['complex'])} COMPLEX IMPORTS (highest priority to fix):")
        for imp in categories['complex'][:5]:  # Show first 5
            rel_path = os.path.relpath(imp['file'], '.')
            print(f"  {rel_path}:{imp['line']}")
        if len(categories['complex']) > 5:
            print(f"  ... and {len(categories['complex']) - 5} more")
    
    if categories['medium']:
        print(f"\n🔶 {len(categories['medium'])} MEDIUM IMPORTS:")
        for imp in categories['medium'][:3]:  # Show first 3
            rel_path = os.path.relpath(imp['file'], '.')
            print(f"  {rel_path}:{imp['line']}")
        if len(categories['medium']) > 3:
            print(f"  ... and {len(categories['medium']) - 3} more")
    
    if categories['simple']:
        print(f"\n🔵 {len(categories['simple'])} SIMPLE IMPORTS:")
        for imp in categories['simple'][:3]:  # Show first 3
            rel_path = os.path.relpath(imp['file'], '.')
            print(f"  {rel_path}:{imp['line']}")
        if len(categories['simple']) > 3:
            print(f"  ... and {len(categories['simple']) - 3} more")

if __name__ == "__main__":
    main()
