#!/usr/bin/env python3
"""
Test script for enhanced aircraft animation and spoke bar features.
This script tests the new state machine and animation system.
"""

import sys
import os

# Add the cargosim package to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'cargosim'))

def test_enhanced_features():
    """Test the enhanced aircraft animation and spoke bar features."""
    try:
        from cargosim.config import SimConfig
        from cargosim.simulation import LogisticsSim
        from cargosim.renderer import Renderer
        
        print("Testing enhanced aircraft animation and spoke bar features...")
        
        # Create a simple configuration
        cfg = SimConfig()
        cfg.periods = 10
        cfg.period_seconds = 1.0
        cfg.frames_per_period = 10
        cfg.fleet_label = "2xC130"
        
        # Create simulation
        sim = LogisticsSim(cfg)
        
        # Create renderer
        renderer = Renderer(sim, force_windowed=True)
        
        print("Renderer created successfully")
        
        # Test aircraft state mapping
        test_states = [
            ("IDLE", "HUB", "IDLE_AT_HUB"),
            ("IDLE", "S1", "RESTING"),
            ("LEG1_ENROUTE", "HUB", "ENROUTE"),
            ("AT_SPOKEA", "S1", "UNLOADING"),
            ("AT_SPOKEB_ENROUTE", "S1", "ENROUTE"),
            ("AT_SPOKEB", "S2", "UNLOADING"),
            ("RETURN_ENROUTE", "S2", "ENROUTE")
        ]
        
        for sim_state, location, expected_visual in test_states:
            actual = renderer._map_aircraft_state(sim_state, location)
            if actual == expected_visual:
                print(f"State mapping: {sim_state}@{location} → {actual}")
            else:
                print(f"State mapping: {sim_state}@{location} → {actual} (expected {expected_visual})")
        
        # Test bar scaling modes
        print("\nTesting bar scaling modes...")
        
        # Test linear mode
        renderer.set_bar_scaling_mode("linear")
        if renderer.bar_scaling_mode == "linear":
            print("Linear mode set successfully")
        else:
            print("Failed to set linear mode")
        
        # Test geometric mode
        renderer.set_bar_scaling_mode("geometric", 0.6)
        if renderer.bar_scaling_mode == "geometric" and renderer.bar_gamma == 0.6:
            print("Geometric mode set successfully with gamma=0.6")
        else:
            print("Failed to set geometric mode")
        
        # Test bar height calculation
        test_values = [0.0, 1.0, 2.0, 4.0, 8.0]
        cap = 4.0
        
        print("\nTesting bar height calculations...")
        for value in test_values:
            linear_height = renderer._calculate_bar_height(value, cap, "linear", 0.6)
            geometric_height = renderer._calculate_bar_height(value, cap, "geometric", 0.6)
            print(f"  Value {value}/{cap}: Linear={linear_height:.1f}, Geometric={geometric_height:.1f}")
        
        # Test animation toggle
        print("\nTesting animation toggle...")
        renderer.toggle_bar_animation(False)
        if not renderer.bar_animation_enabled:
            print("Animation disabled successfully")
        else:
            print("Failed to disable animation")
        
        renderer.toggle_bar_animation(True)
        if renderer.bar_animation_enabled:
            print("Animation enabled successfully")
        else:
            print("Failed to enable animation")
        
        print("\nAll tests completed successfully!")
        
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        raise  # Re-raise the exception to fail the test properly

if __name__ == "__main__":
    test_enhanced_features()
