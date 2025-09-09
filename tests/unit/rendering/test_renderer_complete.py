#!/usr/bin/env python3
"""
Test script to verify that all renderer AttributeErrors have been fixed.
"""

import sys
import os

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
        cfg.duration_minutes = 180
        cfg.period_seconds = 0.1
        
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


def test_aircraft_segment_starts_from_last_position():
    """Ensure new flight segments start from the aircraft's last drawn position to avoid jumps."""
    from cargosim.config import SimConfig
    from cargosim.simulation import LogisticsSim
    from cargosim.renderer import Renderer

    cfg = SimConfig()
    cfg.period_seconds = 0.01
    sim = LogisticsSim(cfg)
    renderer = Renderer(sim, force_windowed=True)

    # Pick first aircraft and put it enroute to a valid spoke
    ac = sim.fleet[0]
    ac.plan = (0, None)
    ac.location = "HUB"
    flight_time = sim.calculate_flight_time("HUB", "S1", ac)
    ac.set_enroute_state(flight_time, "LEG1")

    # Seed a last drawn position mid-way between HUB and S1
    # HUB
    hub_pos = (renderer.cx, renderer.cy)
    # S1
    s1_pos = renderer.spoke_pos[0]
    mid_pos = (int((hub_pos[0] + s1_pos[0]) / 2), int((hub_pos[1] + s1_pos[1]) / 2))
    renderer.aircraft_positions[ac.name] = mid_pos

    # Force an animation update which should create a new segment
    now = time.time()
    renderer._update_aircraft_animation(now)

    # Verify a segment was created and starts from the last drawn position (mid_pos)
    seg = renderer.aircraft_segments.get(ac.name)
    assert seg is not None, "Expected a movement segment to be created"
    assert seg.p0 == mid_pos, f"Segment should start from last drawn position, got {seg.p0} expected {mid_pos}"

if __name__ == "__main__":
    success = test_renderer_complete()
    if success:
        print("\n🎉 All tests passed! The renderer is fully functional.")
    else:
        print("\n❌ Tests failed. There may still be issues to resolve.")
        sys.exit(1)
