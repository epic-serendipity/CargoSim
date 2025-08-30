#!/usr/bin/env python3
"""
Enhanced test runner for CargoSim.

This script demonstrates the enhanced testing capabilities including:
- JSON logging format
- Correlation ID tracking
- Property-based testing
- Coverage reporting
- Parallel test execution
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

from cargosim.core.logging_config import (
    setup_comprehensive_logging, 
    set_correlation_id, 
    get_correlation_id
)


def setup_logging_for_tests(use_json=False, log_level="INFO"):
    """Setup logging for test execution."""
    print(f"Setting up logging: format={'JSON' if use_json else 'Human'}, level={log_level}")
    
    # Set a correlation ID for this test run
    test_run_id = f"test-run-{os.getpid()}-{os.environ.get('USER', 'unknown')}"
    set_correlation_id(test_run_id)
    
    # Setup logging
    log_manager = setup_comprehensive_logging(
        level=log_level,
        use_json=use_json
    )
    
    print(f"Test run correlation ID: {get_correlation_id()}")
    return log_manager


def run_basic_tests():
    """Run basic unit tests."""
    print("\n=== Running Basic Unit Tests ===")
    
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/unit/core/test_logging_config.py",
        "-v",
        "--tb=short"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    print("STDOUT:")
    print(result.stdout)
    if result.stderr:
        print("STDERR:")
        print(result.stderr)
    
    return result.returncode == 0


def run_property_based_tests():
    """Run property-based tests using Hypothesis."""
    print("\n=== Running Property-Based Tests ===")
    
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/unit/core/test_simulation_properties.py",
        "-v",
        "--tb=short",
        "--hypothesis-show-statistics"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    print("STDOUT:")
    print(result.stdout)
    if result.stderr:
        print("STDERR:")
        print(result.stderr)
    
    return result.returncode == 0


def run_config_validation_tests():
    """Run configuration validation tests."""
    print("\n=== Running Configuration Validation Tests ===")
    
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/unit/core/test_config_validation.py",
        "-v",
        "--tb=short"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    print("STDOUT:")
    print(result.stdout)
    if result.stderr:
        print("STDERR:")
        print(result.stderr)
    
    return result.returncode == 0


def run_coverage_tests():
    """Run tests with coverage reporting."""
    print("\n=== Running Tests with Coverage ===")
    
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/unit/core/",
        "--cov=cargosim",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov",
        "--cov-report=xml",
        "-v"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    print("STDOUT:")
    print(result.stdout)
    if result.stderr:
        print("STDERR:")
        print(result.stderr)
    
    return result.returncode == 0


def run_parallel_tests():
    """Run tests in parallel using pytest-xdist."""
    print("\n=== Running Tests in Parallel ===")
    
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/unit/core/",
        "-n", "auto",
        "--dist=worksteal",
        "-v"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    print("STDOUT:")
    print(result.stdout)
    if result.stderr:
        print("STDERR:")
        print(result.stderr)
    
    return result.returncode == 0


def run_all_tests():
    """Run all test suites."""
    print("\n=== Running All Test Suites ===")
    
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/",
        "-v",
        "--tb=short"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    print("STDOUT:")
    print(result.stdout)
    if result.stderr:
        print("STDERR:")
        print(result.stderr)
    
    return result.returncode == 0


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description="Enhanced CargoSim Test Runner")
    parser.add_argument(
        "--format", 
        choices=["json", "human"], 
        default="human",
        help="Log format (default: human)"
    )
    parser.add_argument(
        "--level", 
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Log level (default: INFO)"
    )
    parser.add_argument(
        "--suite",
        choices=["basic", "property", "config", "coverage", "parallel", "all"],
        default="all",
        help="Test suite to run (default: all)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    
    args = parser.parse_args()
    
    print("CargoSim Enhanced Test Runner")
    print("=" * 40)
    
    # Setup logging
    use_json = args.format == "json"
    log_manager = setup_logging_for_tests(use_json, args.level)
    
    # Run selected test suite
    success = True
    
    try:
        if args.suite == "basic":
            success = run_basic_tests()
        elif args.suite == "property":
            success = run_property_based_tests()
        elif args.suite == "config":
            success = run_config_validation_tests()
        elif args.suite == "coverage":
            success = run_coverage_tests()
        elif args.suite == "parallel":
            success = run_parallel_tests()
        elif args.suite == "all":
            # Run all suites
            suites = [
                ("Basic Tests", run_basic_tests),
                ("Property-Based Tests", run_property_based_tests),
                ("Config Validation", run_config_validation_tests),
                ("Coverage Tests", run_coverage_tests),
                ("Parallel Tests", run_parallel_tests)
            ]
            
            for suite_name, suite_func in suites:
                print(f"\n{'='*20} {suite_name} {'='*20}")
                if not suite_func():
                    success = False
                    if not args.verbose:
                        break  # Stop on first failure unless verbose
        
        print(f"\n{'='*40}")
        if success:
            print("✅ All tests passed!")
        else:
            print("❌ Some tests failed!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\nTest run interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\nTest run failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
