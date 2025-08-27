#!/usr/bin/env python3
"""
Test script for Phase 8 Advanced Features implementation.
This script tests the new performance monitoring, analytics, and export features.
"""

import sys
import os
import time
import json
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_performance_monitor():
    """Test the performance monitoring system."""
    print("Testing Performance Monitor...")
    
    try:
        from cargosim.core.utils import performance_monitor
        
        # Test basic functionality
        performance_monitor.track_metric('test_metric', 42.0)
        
        # Test metric retrieval
        current_value = performance_monitor.get_current_metric('test_metric')
        assert current_value == 42.0, f"Expected 42.0, got {current_value}"
        
        # Test performance summary
        summary = performance_monitor.get_performance_summary()
        assert 'uptime_hours' in summary, "Performance summary missing uptime"
        assert 'current_metrics' in summary, "Performance summary missing current metrics"
        
        print("✅ Performance Monitor: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Performance Monitor: FAILED - {e}")
        return False

def test_analytics_engine():
    """Test the analytics engine system."""
    print("Testing Analytics Engine...")
    
    try:
        from cargosim.core.utils import analytics_engine
        
        # Test demand forecasting
        forecast = analytics_engine.predict_demand(0, 'A', 24.0)
        assert 'predicted_demand' in forecast, "Demand forecast missing predicted_demand"
        assert 'confidence' in forecast, "Demand forecast missing confidence"
        
        # Test cost prediction
        cost_prediction = analytics_engine.predict_cost('flight', 100.0, 'C-130')
        assert 'predicted_cost' in cost_prediction, "Cost prediction missing predicted_cost"
        assert 'confidence' in cost_prediction, "Cost prediction missing confidence"
        
        # Test performance prediction
        perf_prediction = analytics_engine.predict_performance('operations_per_second', 1.0, 24.0)
        assert 'predicted_value' in perf_prediction, "Performance prediction missing predicted_value"
        assert 'trend' in perf_prediction, "Performance prediction missing trend"
        
        print("✅ Analytics Engine: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Analytics Engine: FAILED - {e}")
        return False

def test_export_manager():
    """Test the export manager system."""
    print("Testing Export Manager...")
    
    try:
        from cargosim.core.utils import export_manager
        
        # Test data export
        test_data = {
            'test_key': 'test_value',
            'numbers': [1, 2, 3, 4, 5],
            'nested': {'level1': {'level2': 'deep_value'}}
        }
        
        # Test JSON export
        json_filename = export_manager.export_simulation_data(test_data, 'json')
        assert json_filename.endswith('.json'), f"Expected .json file, got {json_filename}"
        
        # Verify file was created
        assert os.path.exists(json_filename), f"Export file {json_filename} was not created"
        
        # Test integration status
        status = export_manager.get_integration_status()
        assert isinstance(status, dict), "Integration status should be a dictionary"
        
        # Clean up test file
        if os.path.exists(json_filename):
            os.remove(json_filename)
        
        print("✅ Export Manager: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Export Manager: FAILED - {e}")
        return False

def test_advanced_simulation_features():
    """Test the advanced simulation features."""
    print("Testing Advanced Simulation Features...")
    
    try:
        from cargosim.core.simulation import LogisticsSim
        from cargosim.core.config import SimConfig
        
        # Create a minimal config for testing
        config = SimConfig()
        
        # Create simulation instance
        sim = LogisticsSim(config)
        
        # Test advanced features status
        status = sim.get_advanced_features_status()
        assert 'advanced_routing' in status, "Advanced features status missing routing info"
        assert 'multi_objective_optimization' in status, "Advanced features status missing optimization info"
        assert 'predictive_analytics' in status, "Advanced features status missing analytics info"
        
        # Test route optimization
        from cargosim.core.simulation import Aircraft
        test_aircraft = Aircraft(typ="C-130", cap=10, name="TestAircraft")
        
        route = sim.optimize_route_multi_objective("HUB", "S1", test_aircraft)
        if route:
            assert 'type' in route, "Route missing type information"
            assert 'total_cost' in route, "Route missing cost information"
        
        print("✅ Advanced Simulation Features: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Advanced Simulation Features: FAILED - {e}")
        return False

def test_gui_integration():
    """Test the GUI integration of advanced features."""
    print("Testing GUI Integration...")
    
    try:
        # Test that the advanced tab can be created
        import tkinter as tk
        from cargosim.ui.gui import ControlGUI
        from cargosim.core.config import SimConfig
        
        # Create minimal config
        config = SimConfig()
        
        # Create root window
        root = tk.Tk()
        root.withdraw()  # Hide the window
        
        # Create GUI (this will test the advanced features initialization)
        gui = ControlGUI(root, config)
        
        # Check if advanced systems were initialized
        assert hasattr(gui, 'performance_monitor'), "Performance monitor not initialized"
        assert hasattr(gui, 'analytics_engine'), "Analytics engine not initialized"
        assert hasattr(gui, 'export_manager'), "Export manager not initialized"
        
        # Clean up
        root.destroy()
        
        print("✅ GUI Integration: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ GUI Integration: FAILED - {e}")
        return False

def main():
    """Run all Phase 8 advanced features tests."""
    print("=" * 60)
    print("Phase 8 Advanced Features Test Suite")
    print("=" * 60)
    
    tests = [
        test_performance_monitor,
        test_analytics_engine,
        test_export_manager,
        test_advanced_simulation_features,
        test_gui_integration
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ {test.__name__}: CRASHED - {e}")
    
    print("\n" + "=" * 60)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All Phase 8 Advanced Features tests passed!")
        return 0
    else:
        print("⚠️  Some tests failed. Please review the implementation.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
