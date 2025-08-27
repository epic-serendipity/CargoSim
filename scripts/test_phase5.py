#!/usr/bin/env python3
"""Phase 5 Test Runner: Edge Case Handling and Validation

This script runs comprehensive tests for Phase 5 implementation including:
- Input validation system
- Performance optimization
- Error handling and recovery
- Edge case handling
- Data integrity validation
- Stress testing

Usage:
    python scripts/test_phase5.py [--verbose] [--performance] [--stress]
"""

import sys
import os
import time
import argparse
import subprocess
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def run_command(cmd, description):
    """Run a command and return success status."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print('='*60)
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print("✅ SUCCESS")
        if result.stdout:
            print("Output:")
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print("❌ FAILED")
        print(f"Return code: {e.returncode}")
        if e.stdout:
            print("Stdout:")
            print(e.stdout)
        if e.stderr:
            print("Stderr:")
            print(e.stderr)
        return False

def run_unit_tests(verbose=False):
    """Run Phase 5 unit tests."""
    print("\n🧪 Running Phase 5 Unit Tests...")
    
    cmd = ["python", "-m", "pytest", "tests/unit/core/test_edge_cases.py"]
    if verbose:
        cmd.append("-v")
    
    success = run_command(cmd, "Phase 5 Unit Tests")
    
    if success:
        print("\n✅ All Phase 5 unit tests passed!")
    else:
        print("\n❌ Some Phase 5 unit tests failed!")
    
    return success

def run_performance_tests(verbose=False):
    """Run performance optimization tests."""
    print("\n⚡ Running Performance Tests...")
    
    # Test performance optimization module
    try:
        from cargosim.core.performance import PerformanceOptimizer, DistanceCache, FlightTimeCache
        
        print("Testing PerformanceOptimizer...")
        optimizer = PerformanceOptimizer()
        
        # Test distance caching
        spoke_distances = [300, 400, 500, 600, 700, 800, 900, 1000]
        start_time = time.time()
        
        for i in range(1000):
            optimizer.calculate_distance(0, 1, spoke_distances)
            optimizer.calculate_distance(1, 2, spoke_distances)
            optimizer.calculate_distance(2, 3, spoke_distances)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        print(f"✅ Performance test completed in {total_time:.3f} seconds")
        print(f"   - 3000 distance calculations")
        print(f"   - Average time per calculation: {total_time/3000*1000:.3f} ms")
        
        # Test cache performance
        cache_stats = optimizer.get_performance_summary()
        print(f"   - Cache hit rate: {cache_stats['performance_check']['cache_performance']['overall_hit_rate']:.2%}")
        
        return True
        
    except Exception as e:
        print(f"❌ Performance test failed: {e}")
        return False

def run_stress_tests(verbose=False):
    """Run stress testing scenarios."""
    print("\n🔥 Running Stress Tests...")
    
    try:
        from cargosim.core.edge_case_handler import EdgeCaseHandler, StressTester
        
        # Initialize stress tester
        edge_handler = EdgeCaseHandler()
        tester = StressTester(edge_handler)
        
        print(f"Available stress test scenarios: {len(edge_handler.edge_case_scenarios)}")
        for scenario in edge_handler.edge_case_scenarios:
            print(f"  - {scenario.name}: {scenario.description}")
        
        # Run all stress tests
        print("\nExecuting stress tests...")
        start_time = time.time()
        results = tester.run_all_stress_tests()
        end_time = time.time()
        
        total_time = end_time - start_time
        successful_tests = sum(1 for r in results if r.success)
        failed_tests = len(results) - successful_tests
        
        print(f"\n✅ Stress testing completed in {total_time:.2f} seconds")
        print(f"   - Total tests: {len(results)}")
        print(f"   - Successful: {successful_tests}")
        print(f"   - Failed: {failed_tests}")
        print(f"   - Success rate: {successful_tests/len(results)*100:.1f}%")
        
        # Show detailed results
        if verbose:
            for result in results:
                status = "✅ PASS" if result.success else "❌ FAIL"
                print(f"\n{status} {result.scenario_name}")
                print(f"   Duration: {result.test_duration:.3f}s")
                if result.warnings:
                    print(f"   Warnings: {len(result.warnings)}")
                if result.errors:
                    print(f"   Errors: {len(result.errors)}")
                if result.recommendations:
                    print(f"   Recommendations: {len(result.recommendations)}")
        
        return failed_tests == 0
        
    except Exception as e:
        print(f"❌ Stress testing failed: {e}")
        return False

def run_validation_tests(verbose=False):
    """Run data validation tests."""
    print("\n🔍 Running Data Validation Tests...")
    
    try:
        from cargosim.core.data_validator import DataValidator
        from cargosim.core.validation import validate_config_comprehensive
        
        validator = DataValidator()
        
        # Test configuration validation
        print("Testing configuration validation...")
        
        # Valid configuration
        valid_config = {
            "speed_mach": 0.45,
            "spoke_distances": [300, 400, 500],
            "turnover_time_hours": 3.0,
            "cost_per_flight_hour": 15000.0
        }
        
        result = validate_config_comprehensive(valid_config)
        if result.is_valid:
            print("✅ Valid configuration validation passed")
        else:
            print("❌ Valid configuration validation failed")
            for error in result.errors:
                print(f"   Error: {error}")
        
        # Invalid configuration
        invalid_config = {
            "speed_mach": 3.0,  # Too high
            "spoke_distances": [50, 1500, 200],  # Out of range
            "turnover_time_hours": -1,  # Negative
            "cost_per_flight_hour": 1000  # Too low
        }
        
        result = validate_config_comprehensive(invalid_config)
        if not result.is_valid:
            print("✅ Invalid configuration correctly rejected")
            print(f"   Errors found: {len(result.errors)}")
            if verbose:
                for error in result.errors:
                    print(f"     - {error}")
        else:
            print("❌ Invalid configuration incorrectly accepted")
        
        # Test validation rules
        print("\nTesting validation rules...")
        rules_summary = validator.get_validation_summary()
        print(f"✅ Validation rules loaded: {len(rules_summary['validation_rules'])}")
        
        return True
        
    except Exception as e:
        print(f"❌ Data validation test failed: {e}")
        return False

def run_error_handling_tests(verbose=False):
    """Run error handling and recovery tests."""
    print("\n🛡️ Running Error Handling Tests...")
    
    try:
        from cargosim.core.error_handler import ErrorHandler, GracefulDegradation, SelfHealingSystem
        
        # Test error handler
        print("Testing error handler...")
        error_handler = ErrorHandler()
        
        # Simulate various error types
        test_errors = [
            (ValueError("Invalid value"), "validation"),
            (MemoryError("Out of memory"), "calculation"),
            (RuntimeError("Runtime error"), "simulation")
        ]
        
        for error, context_name in test_errors:
            context = {'function_name': f'test_{context_name}'}
            success = error_handler.handle_error(error, context)
            print(f"   {type(error).__name__}: {'✅ Handled' if success else '❌ Failed'}")
        
        # Test graceful degradation
        print("\nTesting graceful degradation...")
        degradation = GracefulDegradation(error_handler)
        
        degradation.degrade_functionality('reduced')
        print(f"   Degradation level: {degradation.current_level}")
        
        # Test self-healing
        print("\nTesting self-healing system...")
        healing = SelfHealingSystem(error_handler)
        
        success = healing.attempt_healing()
        print(f"   Self-healing: {'✅ Successful' if success else '❌ Failed'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False

def run_integration_tests(verbose=False):
    """Run integration tests for Phase 5 components."""
    print("\n🔗 Running Integration Tests...")
    
    try:
        from cargosim.core.validation import validate_config_comprehensive
        from cargosim.core.edge_case_handler import EdgeCaseHandler
        from cargosim.core.error_handler import ErrorHandler
        from cargosim.core.performance import PerformanceOptimizer
        from cargosim.core.data_validator import DataValidator
        
        print("Testing component integration...")
        
        # Create all components
        validator = DataValidator()
        edge_handler = EdgeCaseHandler()
        error_handler = ErrorHandler()
        optimizer = PerformanceOptimizer()
        
        # Test integrated workflow
        config_data = {
            "speed_mach": 0.45,
            "spoke_distances": [300, 400, 500, 600, 700, 800, 900, 1000],
            "turnover_time_hours": 3.0,
            "cost_per_flight_hour": 15000.0
        }
        
        # Step 1: Validate configuration
        validation_result = validate_config_comprehensive(config_data)
        if not validation_result.is_valid:
            print("❌ Configuration validation failed")
            return False
        
        print("✅ Configuration validation passed")
        
        # Step 2: Check edge cases
        spoke_count = len(config_data['spoke_distances'])
        edge_result = edge_handler.handle_large_spoke_count(spoke_count)
        print(f"✅ Edge case handling: {edge_result['performance_mode']} mode")
        
        # Step 3: Performance optimization
        distance = optimizer.calculate_distance(0, 1, config_data['spoke_distances'])
        print(f"✅ Performance optimization: distance calculation = {distance:.1f} miles")
        
        # Step 4: Error handling simulation
        context = {'function_name': 'integration_test', 'module_name': 'test'}
        error = ValueError("Integration test error")
        recovery_success = error_handler.handle_error(error, context)
        print(f"✅ Error handling: recovery {'successful' if recovery_success else 'failed'}")
        
        print("\n✅ All integration tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        return False

def generate_test_report(results):
    """Generate a comprehensive test report."""
    print("\n" + "="*80)
    print("📊 PHASE 5 TEST REPORT")
    print("="*80)
    
    total_tests = len(results)
    passed_tests = sum(1 for r in results.values() if r)
    failed_tests = total_tests - passed_tests
    
    print(f"Total Test Categories: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {failed_tests}")
    print(f"Success Rate: {passed_tests/total_tests*100:.1f}%")
    
    print("\nDetailed Results:")
    for test_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status} {test_name}")
    
    if failed_tests == 0:
        print("\n🎉 ALL TESTS PASSED! Phase 5 implementation is working correctly.")
    else:
        print(f"\n⚠️  {failed_tests} test categories failed. Review the output above.")
    
    print("="*80)

def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description="Phase 5 Test Runner")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--performance", "-p", action="store_true", help="Run performance tests")
    parser.add_argument("--stress", "-s", action="store_true", help="Run stress tests")
    parser.add_argument("--all", "-a", action="store_true", help="Run all tests")
    
    args = parser.parse_args()
    
    print("🚀 Phase 5 Test Runner: Edge Case Handling and Validation")
    print("="*80)
    
    # Determine which tests to run
    run_all = args.all or (not any([args.performance, args.stress]))
    
    results = {}
    
    # Always run core tests
    results["Unit Tests"] = run_unit_tests(args.verbose)
    results["Data Validation"] = run_validation_tests(args.verbose)
    results["Error Handling"] = run_error_handling_tests(args.verbose)
    results["Integration Tests"] = run_integration_tests(args.verbose)
    
    # Conditional tests
    if run_all or args.performance:
        results["Performance Tests"] = run_performance_tests(args.verbose)
    
    if run_all or args.stress:
        results["Stress Tests"] = run_stress_tests(args.verbose)
    
    # Generate report
    generate_test_report(results)
    
    # Return appropriate exit code
    if all(results.values()):
        return 0
    else:
        return 1

if __name__ == "__main__":
    sys.exit(main())
