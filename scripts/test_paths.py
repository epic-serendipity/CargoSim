#!/usr/bin/env python3
"""
Path validation testing for CargoSim.
Tests all file paths referenced in the code exist.
"""

import os
import re
from pathlib import Path

def find_path_references():
    """Find all hardcoded path references in Python files."""
    path_patterns = [
        r'os\.path\.join\([^)]*__file__[^)]*\)',
        r'os\.path\.join\([^)]*"[^"]*\.json"[^)]*\)',
        r'os\.path\.join\([^)]*"[^"]*\.log"[^)]*\)',
        r'sys\.path\.insert\([^)]*\)',
        r'Path\([^)]*__file__[^)]*\)'
    ]
    
    references = []
    for root, dirs, files in os.walk('.'):
        # Skip git and cache directories
        if any(skip in root for skip in ['.git', '__pycache__', '.pytest_cache']):
            continue
            
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        for pattern in path_patterns:
                            matches = re.finditer(pattern, content)
                            for match in matches:
                                references.append({
                                    'file': filepath,
                                    'line': content[:match.start()].count('\n') + 1,
                                    'pattern': match.group(),
                                    'context': content[max(0, match.start()-50):match.end()+50]
                                })
                except Exception as e:
                    print(f"Error reading {filepath}: {e}")
    
    return references

def validate_config_files():
    """Validate that all configuration files exist."""
    config_files = [
        "configs/default/cargo_sim_config.json",
        "configs/default/aircraft_config.json"
    ]
    
    results = []
    for config_file in config_files:
        exists = os.path.exists(config_file)
        results.append({
            'file': config_file,
            'exists': exists,
            'type': 'config'
        })
    
    return results

def validate_log_directories():
    """Validate that log directories exist and are writable."""
    log_dirs = [
        "logs",
        "logs/debug",
        "logs/runtime"
    ]
    
    results = []
    for log_dir in log_dirs:
        exists = os.path.exists(log_dir)
        writable = False
        if exists:
            try:
                test_file = os.path.join(log_dir, "test_write.tmp")
                with open(test_file, 'w') as f:
                    f.write("test")
                os.remove(test_file)
                writable = True
            except Exception:
                writable = False
        
        results.append({
            'directory': log_dir,
            'exists': exists,
            'writable': writable,
            'type': 'log'
        })
    
    return results

def validate_import_paths():
    """Validate that import paths are correct."""
    import_patterns = [
        r'from \.([a-zA-Z_][a-zA-Z0-9_]*) import',
        r'from \.\.([a-zA-Z_][a-zA-Z0-9_]*) import',
        r'from \.\.\.([a-zA-Z_][a-zA-Z0-9_]*) import'
    ]
    
    results = []
    for root, dirs, files in os.walk('.'):
        if any(skip in root for skip in ['.git', '__pycache__', '.pytest_cache']):
            continue
            
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        for pattern in import_patterns:
                            matches = re.finditer(pattern, content)
                            for match in matches:
                                relative_path = match.group(1)
                                # Check if the relative import path is valid
                                current_dir = Path(filepath).parent
                                
                                # Handle different levels of relative imports
                                if '..' in match.group():
                                    levels = match.group().count('..')
                                    target_dir = current_dir
                                    for _ in range(levels):
                                        target_dir = target_dir.parent
                                    target_path = target_dir / relative_path
                                else:
                                    target_path = current_dir / relative_path
                                
                                # Check if the target exists as a file or package
                                exists = (target_path.exists() or 
                                        (target_path / '__init__.py').exists() or
                                        (target_path.with_suffix('.py')).exists())
                                
                                results.append({
                                    'file': filepath,
                                    'import': match.group(),
                                    'target': str(target_path),
                                    'exists': exists,
                                    'type': 'import'
                                })
                except Exception as e:
                    print(f"Error reading {filepath}: {e}")
    
    return results

def main():
    """Run path validation testing."""
    print("=== CargoSim Path Validation ===\n")
    
    # Find path references
    print("Analyzing path references...")
    path_refs = find_path_references()
    
    print(f"Found {len(path_refs)} hardcoded path references:")
    for ref in path_refs:
        print(f"  {ref['file']}:{ref['line']} - {ref['pattern'][:50]}...")
    
    # Validate config files
    print("\nValidating configuration files...")
    config_results = validate_config_files()
    
    for result in config_results:
        status = "✅ EXISTS" if result['exists'] else "❌ MISSING"
        print(f"{status}: {result['file']}")
    
    # Validate log directories
    print("\nValidating log directories...")
    log_results = validate_log_directories()
    
    for result in log_results:
        if result['exists']:
            status = "✅ WRITABLE" if result['writable'] else "❌ NOT WRITABLE"
        else:
            status = "❌ MISSING"
        print(f"{status}: {result['directory']}")
    
    # Validate import paths
    print("\nValidating import paths...")
    import_results = validate_import_paths()
    
    failed_imports = [r for r in import_results if not r['exists']]
    if failed_imports:
        print(f"\n❌ {len(failed_imports)} import path issues found:")
        for result in failed_imports:
            print(f"  {result['file']}: {result['import']} -> {result['target']}")
    else:
        print("✅ All import paths are valid")
    
    # Summary
    total_configs = len([r for r in config_results if r['exists']])
    total_logs = len([r for r in log_results if r['exists'] and r['writable']])
    total_imports = len([r for r in import_results if r['exists']])
    
    print(f"\n=== SUMMARY ===")
    print(f"Configuration files: {total_configs}/{len(config_results)} exist")
    print(f"Log directories: {total_logs}/{len(log_results)} exist and writable")
    print(f"Import paths: {total_imports}/{len(import_results)} valid")
    print(f"Hardcoded path references: {len(path_refs)} found")
    
    if len(failed_imports) > 0:
        print(f"\n❌ {len(failed_imports)} issues found!")
        return 1
    else:
        print(f"\n✅ All paths validated successfully!")
        return 0

if __name__ == "__main__":
    main()
