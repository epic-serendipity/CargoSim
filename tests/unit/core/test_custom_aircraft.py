#!/usr/bin/env python3
"""Test script to demonstrate custom aircraft graphics in CargoSim."""

import sys
import os

from cargosim.ui.fleet_builder import FleetBuilder, AircraftType, get_aircraft_config_manager
from cargosim.core.config import SimConfig
from cargosim.main import run_sim

def create_custom_aircraft_fleet():
    """Create a fleet with custom aircraft to test the graphics."""
    print("Creating custom aircraft fleet...")
    
    # Get the aircraft config manager
    config_manager = get_aircraft_config_manager()
    
    # Create a custom aircraft with unique attributes
    custom_aircraft = AircraftType(
        id="Custom_Transport",
        name="Custom Transport",
        description="High-capacity custom transport aircraft",
        base_capacity=6.0,  # Higher capacity than standard
        rest_periods=6.0,   # Faster recovery
        range_factor=1.2,   # Better range
        fuel_efficiency=0.9, # Slightly less fuel efficient
        maintenance_cost=1.2, # Higher maintenance
        special_capabilities=["high_capacity", "extended_range"],
        color="#8b5cf6",  # Purple
        icon="Custom",
        default_count=2,  # Add 2 custom aircraft
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
    
    # Fleet preset system removed - use Fleet Builder pallet instead
    print("Fleet preset system removed - using Fleet Builder pallet")
    
    # Save the configuration
    config_manager.save_config()
    
    print("Custom aircraft created successfully!")
    print("Fleet composition will be managed through Fleet Builder pallet")
    
    return config_manager

def test_custom_aircraft_graphics():
    """Test the custom aircraft graphics by running a simulation."""
    print("\nTesting custom aircraft graphics...")
    
    # Create the custom fleet
    config_manager = create_custom_aircraft_fleet()
    
    # Create a simulation configuration
    config = SimConfig()
    config.fleet_label = "Custom Fleet"
    config.periods = 20  # Short simulation to see the graphics
    
    # Fleet preset system removed - fleet will use Fleet Builder pallet
    
    print(f"Starting simulation with fleet: {config.fleet_label}")
    print(f"Simulation periods: {config.periods}")
    print("\nLook for the diamond-shaped custom aircraft with purple borders and glow effects!")
    print("Custom aircraft will be larger and have unique visual indicators.")
    
    try:
        # Run the simulation
        exit_code, live_out = run_sim(config, force_windowed=False)
        print(f"\nSimulation completed with exit code: {exit_code}")
        
    except Exception as e:
        print(f"Simulation failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_custom_aircraft_graphics()
