#!/usr/bin/env python3
"""
Complete Phase 8 Test Suite
Tests all advanced features, integration, and production readiness.
"""

import sys
import os
import time
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_phase8_complete():
    """Run complete Phase 8 test suite."""
    print("=" * 80)
    print("Phase 8 Complete Test Suite - Production Readiness")
    print("=" * 80)
    
    test_suites = [
        test_core_components,
        test_gui_integration,
        test_performance_monitoring,
        test_analytics_engine,
        test_export_system,
        test_integration_features,
        test_help_system,
        test_production_readiness
    ]
    
    total_tests = 0
    passed_tests = 0
    failed_tests = []
    
    for test_suite in test_suites:
        print(f"\n🧪 Running {test_suite.__name__}...")
        suite_tests, suite_passed, suite_failed = test_suite()
        
        total_tests += suite_tests
        passed_tests += suite_passed
        failed_tests.extend(suite_failed)
        
        if suite_failed:
            print(f"❌ {test_suite.__name__}: {len(suite_failed)} tests failed")
        else:
            print(f"✅ {test_suite.__name__}: All {suite_passed} tests passed")
    
    # Print summary
    print("\n" + "=" * 80)
    print("PHASE 8 COMPLETE TEST RESULTS")
    print("=" * 80)
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {len(failed_tests)}")
    print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
    
    if failed_tests:
        print(f"\n❌ FAILED TESTS:")
        for test in failed_tests:
            print(f"  - {test}")
        return False
    else:
        print(f"\n🎉 ALL TESTS PASSED! Phase 8 is production ready!")
        return True

def test_core_components():
    """Test core Phase 8 components."""
    tests = []
    passed = 0
    failed = []
    
    try:
        # Test PerformanceMonitor
        from cargosim.core.utils import performance_monitor
        performance_monitor.track_metric('test', 42.0)
        assert performance_monitor.get_current_metric('test') == 42.0
        tests.append("PerformanceMonitor basic functionality")
        passed += 1
    except Exception as e:
        failed.append(f"PerformanceMonitor: {e}")
    
    try:
        # Test AnalyticsEngine
        from cargosim.core.utils import analytics_engine
        forecast = analytics_engine.predict_demand(0, 'A', 24.0)
        assert 'predicted_demand' in forecast
        tests.append("AnalyticsEngine demand forecasting")
        passed += 1
    except Exception as e:
        failed.append(f"AnalyticsEngine: {e}")
    
    try:
        # Test ExportManager
        from cargosim.core.utils import export_manager
        test_data = {'test': 'data'}
        filename = export_manager.export_simulation_data(test_data, 'json')
        assert os.path.exists(filename)
        os.remove(filename)  # Cleanup
        tests.append("ExportManager basic export")
        passed += 1
    except Exception as e:
        failed.append(f"ExportManager: {e}")
    
    return len(tests), passed, failed

def test_gui_integration():
    """Test GUI integration of advanced features."""
    tests = []
    passed = 0
    failed = []
    
    try:
        import tkinter as tk
        from cargosim.ui.gui import ControlGUI
        from cargosim.core.config import SimConfig
        
        # Create minimal GUI for testing
        root = tk.Tk()
        root.withdraw()
        
        config = SimConfig()
        gui = ControlGUI(root, config)
        
        # Test advanced systems initialization
        assert hasattr(gui, 'performance_monitor')
        assert hasattr(gui, 'analytics_engine')
        assert hasattr(gui, 'export_manager')
        tests.append("Advanced systems initialization")
        passed += 1
        
        # Test help system
        assert hasattr(gui, '_show_help_system')
        tests.append("Help system integration")
        passed += 1
        
        root.destroy()
        
    except Exception as e:
        failed.append(f"GUI Integration: {e}")
    
    return len(tests), passed, failed

def test_performance_monitoring():
    """Test performance monitoring system."""
    tests = []
    passed = 0
    failed = []
    
    try:
        from cargosim.core.utils import performance_monitor
        
        # Test metric tracking
        performance_monitor.track_metric('cpu_test', 50.0)
        performance_monitor.track_metric('memory_test', 1024.0)
        
        # Test metric retrieval
        assert performance_monitor.get_current_metric('cpu_test') == 50.0
        assert performance_monitor.get_current_metric('memory_test') == 1024.0
        tests.append("Metric tracking and retrieval")
        passed += 1
        
        # Test performance summary
        summary = performance_monitor.get_performance_summary()
        assert 'uptime_hours' in summary
        assert 'current_metrics' in summary
        tests.append("Performance summary generation")
        passed += 1
        
        # Test trend calculation
        trend = performance_monitor.calculate_trend('cpu_test', 1.0)
        assert isinstance(trend, (int, float))
        tests.append("Trend calculation")
        passed += 1
        
    except Exception as e:
        failed.append(f"Performance Monitoring: {e}")
    
    return len(tests), passed, failed

def test_analytics_engine():
    """Test analytics engine functionality."""
    tests = []
    passed = 0
    failed = []
    
    try:
        from cargosim.core.utils import analytics_engine
        
        # Test demand forecasting
        forecast = analytics_engine.predict_demand(0, 'A', 24.0)
        assert 'predicted_demand' in forecast
        assert 'confidence' in forecast
        assert 'model_type' in forecast
        tests.append("Demand forecasting")
        passed += 1
        
        # Test cost prediction
        cost_pred = analytics_engine.predict_cost('flight', 100.0, 'C-130')
        assert 'predicted_cost' in cost_pred
        assert 'confidence' in cost_pred
        tests.append("Cost prediction")
        passed += 1
        
        # Test performance prediction
        perf_pred = analytics_engine.predict_performance('operations_per_second', 1.0, 24.0)
        assert 'predicted_value' in perf_pred
        assert 'trend' in perf_pred
        tests.append("Performance prediction")
        passed += 1
        
    except Exception as e:
        failed.append(f"Analytics Engine: {e}")
    
    return len(tests), passed, failed

def test_export_system():
    """Test export system functionality."""
    tests = []
    passed = 0
    failed = []
    
    try:
        from cargosim.core.utils import export_manager
        
        test_data = {
            'simulation': 'test',
            'timestamp': time.time(),
            'metrics': {'cpu': 50.0, 'memory': 1024.0}
        }
        
        # Test JSON export
        json_file = export_manager.export_simulation_data(test_data, 'json')
        assert os.path.exists(json_file)
        assert json_file.endswith('.json')
        tests.append("JSON export")
        passed += 1
        
        # Test CSV export
        csv_file = export_manager.export_simulation_data(test_data, 'csv')
        assert os.path.exists(csv_file)
        assert csv_file.endswith('.csv')
        tests.append("CSV export")
        passed += 1
        
        # Test export history
        history = export_manager.get_export_history()
        assert len(history) >= 2  # At least our two exports
        tests.append("Export history tracking")
        passed += 1
        
        # Test export statistics
        stats = export_manager.get_export_statistics()
        assert 'total_exports' in stats
        assert 'formats_used' in stats
        tests.append("Export statistics")
        passed += 1
        
        # Cleanup
        for file in [json_file, csv_file]:
            if os.path.exists(file):
                os.remove(file)
        
    except Exception as e:
        failed.append(f"Export System: {e}")
    
    return len(tests), passed, failed

def test_integration_features():
    """Test integration features."""
    tests = []
    passed = 0
    failed = []
    
    try:
        from cargosim.core.utils import export_manager
        
        # Test integration configuration
        test_config = {
            'url': 'https://example.com/webhook',
            'method': 'POST',
            'headers': {'Content-Type': 'application/json'},
            'timeout': 10
        }
        
        export_manager.configure_integration('webhook', test_config)
        assert export_manager.integration_endpoints['webhook']['enabled']
        tests.append("Integration configuration")
        passed += 1
        
        # Test integration status
        status = export_manager.get_integration_status()
        assert 'webhook' in status
        tests.append("Integration status")
        passed += 1
        
        # Test configuration validation
        is_valid, message = export_manager.validate_integration_config('webhook', test_config)
        assert is_valid
        tests.append("Configuration validation")
        passed += 1
        
    except Exception as e:
        failed.append(f"Integration Features: {e}")
    
    return len(tests), passed, failed

def test_help_system():
    """Test help system functionality."""
    tests = []
    passed = 0
    failed = []
    
    try:
        from cargosim.ui.help_system import HelpSystem
        
        # Create mock parent
        mock_parent = Mock()
        
        # Test help system creation
        help_system = HelpSystem(mock_parent)
        assert help_system.help_data is not None
        assert 'getting_started' in help_system.help_data
        tests.append("Help system initialization")
        passed += 1
        
        # Test help content loading
        content = help_system.help_data['getting_started']['content']
        assert len(content) > 0
        assert 'Welcome' in content
        tests.append("Help content loading")
        passed += 1
        
        # Test help data structure
        for topic in help_system.help_data.values():
            assert 'title' in topic
            assert 'content' in topic
            assert 'sections' in topic
        tests.append("Help data structure")
        passed += 1
        
    except Exception as e:
        failed.append(f"Help System: {e}")
    
    return len(tests), passed, failed

def test_production_readiness():
    """Test production readiness requirements."""
    tests = []
    passed = 0
    failed = []
    
    try:
        # Test import stability
        import cargosim.core.utils
        import cargosim.core.simulation
        import cargosim.ui.gui
        tests.append("Import stability")
        passed += 1
        
        # Test configuration loading
        from cargosim.core.config import SimConfig
        config = SimConfig()
        assert config is not None
        tests.append("Configuration loading")
        passed += 1
        
        # Test error handling
        from cargosim.core.utils import log_exception
        try:
            log_exception(Exception("Test exception"), "Test error")
            tests.append("Error handling")
            passed += 1
        except:
            failed.append("Error handling failed")
        
        # Test performance impact (basic)
        start_time = time.time()
        from cargosim.core.utils import performance_monitor
        performance_monitor.track_metric('test', 42.0)
        end_time = time.time()
        
        # Should complete in under 100ms
        if (end_time - start_time) < 0.1:
            tests.append("Performance impact acceptable")
            passed += 1
        else:
            failed.append("Performance impact too high")
        
    except Exception as e:
        failed.append(f"Production Readiness: {e}")
    
    return len(tests), passed, failed

def main():
    """Main test execution."""
    print("Starting Phase 8 Complete Test Suite...")
    
    try:
        success = test_phase8_complete()
        return 0 if success else 1
    except Exception as e:
        print(f"Test suite execution failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
