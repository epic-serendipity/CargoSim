#!/usr/bin/env python3
"""
Test runner script for the enhanced error handling system.

This script:
1. Runs all error handling tests
2. Provides comprehensive reporting
3. Generates test coverage information
4. Validates the error handling system integrity
"""

import sys
import os
import subprocess
import time
import json
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def run_command(command, description):
    """Run a command and return the result."""
    print(f"\n{'='*60}")
    print(f"🔄 {description}")
    print(f"{'='*60}")
    print(f"Command: {command}")
    print("-" * 60)
    
    start_time = time.time()
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=project_root
        )
        
        elapsed_time = time.time() - start_time
        
        print(f"Exit Code: {result.returncode}")
        print(f"Duration: {elapsed_time:.2f} seconds")
        
        if result.stdout:
            print("\n📤 STDOUT:")
            print(result.stdout)
        
        if result.stderr:
            print("\n⚠️  STDERR:")
            print(result.stderr)
        
        success = result.returncode == 0
        print(f"\n{'✅ SUCCESS' if success else '❌ FAILED'}")
        
        return success, result
        
    except Exception as e:
        elapsed_time = time.time() - start_time
        print(f"❌ EXCEPTION: {e}")
        print(f"Duration: {elapsed_time:.2f} seconds")
        return False, None

def check_pytest_availability():
    """Check if pytest is available."""
    try:
        import pytest
        print("✅ pytest is available")
        return True
    except ImportError:
        print("❌ pytest is not available")
        print("Installing pytest...")
        
        success, _ = run_command(
            "pip install pytest pytest-cov",
            "Installing pytest and pytest-cov"
        )
        
        if success:
            print("✅ pytest installed successfully")
            return True
        else:
            print("❌ Failed to install pytest")
            return False

def run_unit_tests():
    """Run the unit tests for error handling."""
    test_files = [
        "tests/unit/ui/test_error_handling.py",
        "tests/unit/ui/test_ui_error_handling.py"
    ]
    
    all_success = True
    test_results = {}
    
    for test_file in test_files:
        if os.path.exists(test_file):
            print(f"\n🧪 Running tests in {test_file}")
            
            success, result = run_command(
                f"python -m pytest {test_file} -v --tb=short",
                f"Running {test_file} tests"
            )
            
            test_results[test_file] = {
                'success': success,
                'result': result
            }
            
            if not success:
                all_success = False
        else:
            print(f"⚠️  Test file not found: {test_file}")
    
    return all_success, test_results

def run_coverage_tests():
    """Run tests with coverage reporting."""
    print("\n📊 Running tests with coverage analysis...")
    
    success, result = run_command(
        "python -m pytest tests/unit/ui/test_error_handling.py --cov=cargosim.ui.fleet_builder_gui --cov-report=term-missing --cov-report=html",
        "Running error handling tests with coverage"
    )
    
    return success, result

def validate_error_handling_functions():
    """Validate that all error handling functions exist and are callable."""
    print("\n🔍 Validating error handling function integrity...")
    
    try:
        from cargosim.ui.fleet_builder_gui import (
            retry_operation,
            create_error_dialog,
            safe_dict_get,
            safe_list_get,
            safe_attr_get,
            validate_aircraft_info,
            validate_fleet_summary
        )
        
        # Test function callability
        functions = {
            'retry_operation': retry_operation,
            'create_error_dialog': create_error_dialog,
            'safe_dict_get': safe_dict_get,
            'safe_list_get': safe_list_get,
            'safe_attr_get': safe_attr_get,
            'validate_aircraft_info': validate_aircraft_info,
            'validate_fleet_summary': validate_fleet_summary
        }
        
        all_valid = True
        
        for name, func in functions.items():
            if callable(func):
                print(f"✅ {name}: Callable")
            else:
                print(f"❌ {name}: Not callable")
                all_valid = False
        
        return all_valid
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Validation error: {e}")
        return False

def run_syntax_check():
    """Check syntax of the main error handling file."""
    print("\n🔍 Checking syntax of error handling implementation...")
    
    success, result = run_command(
        "python -m py_compile cargosim/ui/fleet_builder_gui.py",
        "Syntax check for fleet_builder_gui.py"
    )
    
    return success, result

def generate_test_report(test_results, coverage_success, validation_success, syntax_success):
    """Generate a comprehensive test report."""
    print("\n" + "="*80)
    print("📋 COMPREHENSIVE ERROR HANDLING TEST REPORT")
    print("="*80)
    
    # Overall status
    overall_success = all([
        test_results.get('overall', False),
        coverage_success,
        validation_success,
        syntax_success
    ])
    
    print(f"\n🎯 OVERALL STATUS: {'✅ PASSED' if overall_success else '❌ FAILED'}")
    
    # Test results
    print(f"\n🧪 UNIT TESTS:")
    for test_file, result in test_results.items():
        if isinstance(result, dict):
            status = "✅ PASSED" if result.get('success', False) else "❌ FAILED"
            print(f"  {test_file}: {status}")
        else:
            print(f"  {test_file}: {result}")
    
    # Coverage status
    print(f"\n📊 COVERAGE ANALYSIS: {'✅ PASSED' if coverage_success else '❌ FAILED'}")
    
    # Validation status
    print(f"\n🔍 FUNCTION VALIDATION: {'✅ PASSED' if validation_success else '❌ PASSED'}")
    
    # Syntax status
    print(f"\n🔍 SYNTAX CHECK: {'✅ PASSED' if syntax_success else '❌ FAILED'}")
    
    # Recommendations
    print(f"\n💡 RECOMMENDATIONS:")
    if overall_success:
        print("  🎉 All tests passed! The error handling system is robust and ready for production.")
        print("  🔒 The system is protected against future issues through comprehensive testing.")
    else:
        print("  ⚠️  Some tests failed. Please review the errors above and fix them.")
        print("  🔧 Consider running individual test files to isolate issues.")
    
    print(f"\n📁 Test coverage reports are available in the htmlcov/ directory")
    print(f"📁 Individual test results are shown above")
    
    return overall_success

def main():
    """Main test execution function."""
    print("🚀 CargoSim Error Handling System Test Suite")
    print("=" * 60)
    
    # Check pytest availability
    if not check_pytest_availability():
        print("❌ Cannot proceed without pytest")
        return False
    
    # Run syntax check
    syntax_success = run_syntax_check()
    
    # Validate error handling functions
    validation_success = validate_error_handling_functions()
    
    # Run unit tests
    test_success, test_results = run_unit_tests()
    
    # Run coverage tests
    coverage_success, _ = run_coverage_tests()
    
    # Compile overall test results
    test_results['overall'] = test_success
    
    # Generate comprehensive report
    overall_success = generate_test_report(
        test_results,
        coverage_success,
        validation_success,
        syntax_success
    )
    
    print(f"\n{'='*80}")
    print(f"🏁 TEST EXECUTION COMPLETED")
    print(f"Final Result: {'✅ ALL TESTS PASSED' if overall_success else '❌ SOME TESTS FAILED'}")
    print(f"{'='*80}")
    
    return overall_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
