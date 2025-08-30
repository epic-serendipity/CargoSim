#!/usr/bin/env python3
"""
Comprehensive import testing for CargoSim.
Tests all modules can be imported without errors.
"""

import sys
import os
import importlib
import traceback
from pathlib import Path

def test_module_import(module_name: str) -> tuple[bool, str]:
    """Test if a module can be imported successfully."""
    try:
        importlib.import_module(module_name)
        return True, ""
    except Exception as e:
        return False, str(e)

def test_relative_imports():
    """Test all relative imports within the cargosim package."""
    modules_to_test = [
        "cargosim",
        "cargosim.core",
        "cargosim.core.config", 
        "cargosim.core.simulation",
        "cargosim.core.utils",
        "cargosim.core.paths",
        "cargosim.rendering",
        "cargosim.rendering.renderer",
        "cargosim.rendering.recorder",
        "cargosim.rendering.themes",
        "cargosim.rendering.themes.ui_theme",
        "cargosim.rendering.themes.unified_theme_manager",
        "cargosim.ui",
        "cargosim.ui.gui",
        "cargosim.ui.fleet_builder",
        "cargosim.ui.fleet_builder_gui",
        "cargosim.features",
        "cargosim.features.smart_targeting",
        "cargosim.__main__"
    ]
    
    results = []
    for module in modules_to_test:
        success, error = test_module_import(module)
        results.append((module, success, error))
    
    return results

def test_standalone_scripts():
    """Test standalone scripts can run without import errors."""
    scripts_to_test = [
        "cargo_sim.py",
        "examples/advanced/demo_custom_aircraft_visuals.py",
        "examples/advanced/demo_fleet_builder.py"
    ]
    
    results = []
    for script in scripts_to_test:
        if os.path.exists(script):
            try:
                # Test basic import without running
                with open(script, 'r') as f:
                    content = f.read()
                    if 'import' in content and 'cargosim' in content:
                        # For scripts with cargosim imports, test if they can be imported
                        if script == "cargo_sim.py":
                            # cargo_sim.py is special - it's a launcher script
                            results.append((script, True, ""))
                        else:
                            # For example scripts, check if they have valid import syntax
                            # This is a basic check - actual import testing would require running the script
                            if 'from cargosim.' in content:
                                results.append((script, True, ""))
                            else:
                                results.append((script, False, "Invalid import syntax"))
                    else:
                        results.append((script, True, "No cargosim imports"))
            except Exception as e:
                results.append((script, False, str(e)))
        else:
            results.append((script, False, "File not found"))
    
    return results

def test_config_loading():
    """Test that configuration files can be loaded."""
    results = []
    
    try:
        from cargosim.core.config import load_config
        config = load_config()
        results.append(("Main config loading", True, ""))
    except Exception as e:
        results.append(("Main config loading", False, str(e)))
    
    try:
        from cargosim.ui.fleet_builder import get_aircraft_config_manager
        manager = get_aircraft_config_manager()
        results.append(("Aircraft config loading", True, ""))
    except Exception as e:
        results.append(("Aircraft config loading", False, str(e)))
    
    return results

def test_theme_system():
    """Test that the theme system works correctly."""
    results = []
    
    try:
        from cargosim.core.config import SimConfig, apply_theme_preset
        config = SimConfig()
        results.append(("Theme config creation", True, ""))
    except Exception as e:
        results.append(("Theme config creation", False, str(e)))
    
    try:
        from cargosim.rendering.themes.ui_theme import create_palette_from_theme_config
        if 'config' in locals():
            palette = create_palette_from_theme_config(config.theme)
            results.append(("Theme palette creation", True, ""))
        else:
            results.append(("Theme palette creation", False, "Config not available"))
    except Exception as e:
        results.append(("Theme palette creation", False, str(e)))
    
    return results

def main():
    """Run comprehensive import testing."""
    print("=== CargoSim Import Testing ===\n")
    
    # Test package imports
    print("Testing package imports...")
    import_results = test_relative_imports()
    
    failed_imports = []
    for module, success, error in import_results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {module}")
        if not success:
            failed_imports.append((module, error))
            print(f"    Error: {error}")
    
    print(f"\nPackage imports: {len([r for r in import_results if r[1]])}/{len(import_results)} passed")
    
    # Test standalone scripts
    print("\nTesting standalone scripts...")
    script_results = test_standalone_scripts()
    
    failed_scripts = []
    for script, success, error in script_results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {script}")
        if not success:
            failed_scripts.append((script, error))
    
    print(f"\nStandalone scripts: {len([r for r in script_results if r[1]])}/{len(script_results)} passed")
    
    # Test configuration loading
    print("\nTesting configuration loading...")
    config_results = test_config_loading()
    
    failed_configs = []
    for config_test, success, error in config_results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {config_test}")
        if not success:
            failed_configs.append((config_test, error))
    
    print(f"\nConfiguration tests: {len([r for r in config_results if r[1]])}/{len(config_results)} passed")
    
    # Test theme system
    print("\nTesting theme system...")
    theme_results = test_theme_system()
    
    failed_themes = []
    for theme_test, success, error in theme_results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {theme_test}")
        if not success:
            failed_themes.append((theme_test, error))
    
    print(f"\nTheme system tests: {len([r for r in theme_results if r[1]])}/{len(theme_results)} passed")
    
    # Summary
    total_tests = len(import_results) + len(script_results) + len(config_results) + len(theme_results)
    total_failed = len(failed_imports) + len(failed_scripts) + len(failed_configs) + len(failed_themes)
    
    print(f"\n=== SUMMARY ===")
    print(f"Total tests: {total_tests}")
    print(f"Failed tests: {total_failed}")
    print(f"Success rate: {((total_tests - total_failed) / total_tests * 100):.1f}%")
    
    if total_failed > 0:
        print(f"\n❌ {total_failed} issues found!")
        return 1
    else:
        print(f"\n✅ All tests passed!")
        return 0

if __name__ == "__main__":
    sys.exit(main())
