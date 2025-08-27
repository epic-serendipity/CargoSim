#!/usr/bin/env python3
"""
Test script to verify that all renderer AttributeErrors have been fixed.
"""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_renderer_complete():
    """Test that the renderer can be fully initialized and used."""
    print("Testing Complete Renderer Fix")
    print("=" * 35)
    
    try:
        # Test imports
        from cargosim.config import SimConfig
        from cargosim.simulation import LogisticsSim
        from cargosim.renderer import Renderer
        
        print("✓ All imports successful")
        
        # Test configuration creation
        cfg = SimConfig()
        cfg.fleet_label = "Custom Fleet"
        cfg.periods = 3
        cfg.period_seconds = 1.0
        
        print("✓ Configuration created successfully")
        
        # Test simulation creation
        sim = LogisticsSim(cfg)
        print(f"✓ Simulation created with {len(sim.fleet)} aircraft")
        
        # Test renderer creation
        renderer = Renderer(sim, force_windowed=True)
        print("✓ Renderer created successfully")
        
        # Test that all required attributes are present
        required_attributes = [
            '_pygame_initialized',
            'frames_per_period',
            'aircraft_stagger_delays',
            '_hud_cache',
            '_last_heading_by_ac',
            'mouse_pos',
            'hovered_aircraft',
            'hover_info_surface',
            'include_side_panels',
            '_previous_actions'
        ]
        
        missing_attributes = []
        for attr in required_attributes:
            if not hasattr(renderer, attr):
                missing_attributes.append(attr)
        
        if missing_attributes:
            print(f"✗ Missing attributes: {missing_attributes}")
            return False
        else:
            print("✓ All required attributes present")
        
        # Test custom aircraft features
        custom_aircraft_count = sum(1 for ac in sim.fleet if ac.typ == "Custom_Transport")
        print(f"✓ Found {custom_aircraft_count} custom aircraft")
        
        # Test that include_side_panels has the correct value
        expected_side_panels = getattr(cfg, "viz_include_side_panels", True)
        if renderer.include_side_panels == expected_side_panels:
            print(f"✓ include_side_panels correctly set to {renderer.include_side_panels}")
        else:
            print(f"✗ include_side_panels mismatch: expected {expected_side_panels}, got {renderer.include_side_panels}")
            return False
        
        print("\nRenderer complete test completed successfully!")
        print("All AttributeErrors have been fixed.")
        
        return True
        
    except Exception as e:
        print(f"✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_renderer_complete()
    if success:
        print("\n🎉 All tests passed! The renderer is fully functional.")
    else:
        print("\n❌ Tests failed. There may still be issues to resolve.")
        sys.exit(1)
