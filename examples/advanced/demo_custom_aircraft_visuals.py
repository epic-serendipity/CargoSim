#!/usr/bin/env python3
"""
Demo script to showcase enhanced custom aircraft visual effects in CargoSim.
This script demonstrates the unique visual representation of custom aircraft
including star shapes, glow effects, motion trails, and enhanced animations.
"""

import sys
import os

# Add the cargosim package to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'cargosim'))

from cargosim.core.config import SimConfig
from cargosim.ui.fleet_builder import AircraftType
from cargosim.core.simulation import LogisticsSim
from cargosim.main import run_sim

def create_custom_aircraft_demo():
    """Create a demo configuration with custom aircraft to showcase visuals."""
    
    # Get the aircraft config manager
    from cargosim.ui.fleet_builder import get_aircraft_config_manager, FleetPreset
    config_manager = get_aircraft_config_manager()
    
    # Create custom aircraft type with enhanced capabilities
    custom_aircraft = AircraftType(
        id="Custom_Transport",
        name="Custom Transport",
        description="High-capacity custom transport aircraft with unique visual effects",
        base_capacity=6,
        rest_periods=6,
        range_factor=1.2,
        fuel_efficiency=0.9,
        maintenance_cost=1.2,
        special_capabilities=["high_capacity", "long_range", "custom_visuals"],
        color="#8b5cf6",  # Purple color for custom aircraft
        icon="Custom",
        default_count=3,  # Default count for this aircraft type
        is_custom=True,
        custom_attributes={
            "capacity": 6.0,
            "rest_periods": 6.0,
            "range_factor": 1.2,
            "fuel_efficiency": 0.9,
            "maintenance_cost": 1.2
        }
    )
    
    # Update the custom aircraft in the config manager
    config_manager.aircraft_types["Custom_Transport"] = custom_aircraft
    
    # Create a fleet preset with custom aircraft
    custom_fleet_preset = FleetPreset(
        name="Custom Aircraft Demo",
        description="Demo fleet showcasing enhanced custom aircraft visuals",
        aircraft={"Custom_Transport": 3}  # 3 custom aircraft for better visualization
    )
    
    # Add the fleet preset to the config manager
    config_manager.fleet_presets["Custom Aircraft Demo"] = custom_fleet_preset
    
    # Save the configuration
    config_manager.save_config()
    
    # Create simulation configuration
    config = SimConfig(
        fleet_label="Custom Aircraft Demo",
        periods=30,  # Longer simulation to see more movement
        period_seconds=5.0,  # Slower simulation to see effects
        fps=60,  # Higher FPS for smooth animations
        debug_mode=True,  # Enable debug mode to see more info
        orient_aircraft=True,  # Enable aircraft orientation
        show_aircraft_labels=True,  # Show aircraft names
        viz_include_side_panels=True,  # Include side panels
        launch_fullscreen=False  # Use windowed mode for demo
    )
    
    # Set the theme to Midnight Purple for better custom aircraft visibility
    from cargosim.config import apply_theme_preset
    apply_theme_preset(config.theme, "Midnight Purple")
    
    return config

def main():
    """Run the custom aircraft visual demo."""
    print("=== CargoSim Custom Aircraft Visual Demo ===")
    print()
    print("This demo showcases the simplified visual representation of custom aircraft:")
    print("• Airplane-like shape (pointed front, wider back with wings)")
    print("• Purple color scheme with simple border")
    print("• Simple motion trails")
    print("• Basic transit indicators")
    print("• No fancy visual effects or animations")
    print()
    print("Starting simulation...")
    print("Look for the distinctive airplane-shaped aircraft with purple color!")
    print()
    
    try:
        # Create and run the demo
        config = create_custom_aircraft_demo()
        exit_code, live_out = run_sim(config, force_windowed=True)
        
        print(f"Simulation completed with exit code: {exit_code}")
        
    except Exception as e:
        print(f"Demo failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
