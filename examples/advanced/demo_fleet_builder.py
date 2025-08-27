#!/usr/bin/env python3
"""Demonstration script for the CargoSim Fleet Builder system."""

import sys
import os

# Add the cargosim directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

def demo_basic_fleet_building():
    """Demonstrate basic fleet building functionality."""
    print("🚁 CargoSim Fleet Builder Demonstration")
    print("=" * 50)
    
    try:
        from cargosim.ui.fleet_builder import (
            AircraftType, FleetComposition, FleetPreset,
            AircraftConfigManager, FleetBuilder,
            get_aircraft_config_manager, get_fleet_builder
        )
        
        # Get the fleet builder
        fleet_builder = get_fleet_builder()
        config_manager = get_aircraft_config_manager()
        
        print("\n1. Available Aircraft Types:")
        print("-" * 30)
        for aircraft in config_manager.get_all_aircraft_types():
            print(f"  • {aircraft.name} ({aircraft.id})")
            print(f"    Capacity: {aircraft.base_capacity}, Rest: {aircraft.rest_periods} periods")
            print(f"    Capabilities: {', '.join(aircraft.special_capabilities)}")
            print()
        
        print("\n2. Fleet Presets:")
        print("-" * 30)
        for preset in config_manager.get_all_fleet_presets():
            print(f"  • {preset.name}: {preset.description}")
            aircraft_summary = []
            for aircraft_id, count in preset.aircraft.items():
                aircraft_type = config_manager.get_aircraft_type(aircraft_id)
                if aircraft_type:
                    aircraft_summary.append(f"{count}× {aircraft_type.name}")
            print(f"    Aircraft: {', '.join(aircraft_summary)}")
            print()
        
        print("\n3. Building a Custom Fleet:")
        print("-" * 30)
        
        # Start with an empty fleet
        fleet_builder.clear_fleet()
        print("  Starting with empty fleet...")
        
        # Add some aircraft
        fleet_builder.add_aircraft("C-130", 2)
        print("  Added 2× C-130 Hercules")
        
        fleet_builder.add_aircraft("C-17", 1)
        print("  Added 1× C-17 Globemaster")
        
        fleet_builder.add_aircraft("C-27", 1)
        print("  Added 1× C-27 Spartan")
        
        # Get fleet summary
        summary = fleet_builder.get_fleet_summary()
        print(f"\n  Fleet Summary:")
        print(f"    Total Aircraft: {summary['total_aircraft']}")
        print(f"    Total Capacity: {summary['total_capacity']}")
        print(f"    Maintenance Cost: {summary['total_cost']:.1f}")
        print(f"    Efficiency Score: {summary['efficiency_score']:.2f}")
        
        print(f"\n  Aircraft Breakdown:")
        for aircraft_id, info in summary['aircraft_breakdown'].items():
            print(f"    {info['name']}: {info['count']}× (Capacity: {info['total_capacity']})")
        
        print(f"\n  Special Capabilities: {', '.join(summary['capabilities'])}")
        
        # Export to legacy format
        legacy_format = fleet_builder.export_fleet_to_legacy_format()
        print(f"\n  Legacy Format: {legacy_format}")
        
        # Save as a custom preset
        fleet_builder.save_fleet_preset("Demo Fleet", "A demonstration fleet with mixed aircraft types")
        print("\n  Saved as custom preset: 'Demo Fleet'")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during demonstration: {e}")
        import traceback
        traceback.print_exc()
        return False

def demo_advanced_features():
    """Demonstrate advanced fleet builder features."""
    print("\n🔧 Advanced Features Demonstration")
    print("=" * 50)
    
    try:
        from cargosim.ui.fleet_builder import get_fleet_builder, get_aircraft_config_manager
        
        fleet_builder = get_fleet_builder()
        config_manager = get_aircraft_config_manager()
        
        print("\n1. Creating Fleet from Preset:")
        print("-" * 30)
        
        # Load a preset
        preset_name = "Strategic Fleet"
        fleet = fleet_builder.create_fleet_from_preset(preset_name)
        print(f"  Loaded '{preset_name}' preset")
        print(f"  Aircraft: {fleet.aircraft}")
        
        # Modify the fleet
        fleet_builder.add_aircraft("C-5", 1)
        print("  Added 1× C-5 Galaxy for maximum lift capability")
        
        summary = fleet_builder.get_fleet_summary()
        print(f"  New Total Capacity: {summary['total_capacity']}")
        
        print("\n2. Fleet Performance Analysis:")
        print("-" * 30)
        
        # Analyze different fleet compositions
        test_fleets = [
            ("Light Tactical", {"C-27": 3}),
            ("Medium Tactical", {"C-130": 2, "C-27": 1}),
            ("Heavy Strategic", {"C-17": 2, "C-5": 1}),
            ("Balanced", {"C-130": 2, "C-27": 2, "C-17": 1})
        ]
        
        print("  Fleet Performance Comparison:")
        print("  " + "-" * 80)
        print("  Fleet Type          | Aircraft | Capacity | Cost | Efficiency")
        print("  " + "-" * 80)
        
        for fleet_name, aircraft_composition in test_fleets:
            # Set the fleet composition
            for aircraft_id, count in aircraft_composition.items():
                fleet_builder.set_aircraft_count(aircraft_id, count)
            
            # Get summary
            summary = fleet_builder.get_fleet_summary()
            
            # Format aircraft list
            aircraft_list = []
            for aid, count in aircraft_composition.items():
                aircraft_type = config_manager.get_aircraft_type(aid)
                if aircraft_type:
                    aircraft_list.append(f"{count}×{aircraft_type.name.split()[0]}")
            
            aircraft_str = ", ".join(aircraft_list)
            
            print(f"  {fleet_name:<18} | {aircraft_str:<8} | {summary['total_capacity']:>8} | {summary['total_cost']:>4.1f} | {summary['efficiency_score']:>9.2f}")
        
        print("  " + "-" * 80)
        
        return True
        
    except Exception as e:
        print(f"❌ Error during advanced demonstration: {e}")
        import traceback
        traceback.print_exc()
        return False

def demo_aircraft_management():
    """Demonstrate aircraft configuration management."""
    print("\n⚙️ Aircraft Configuration Management")
    print("=" * 50)
    
    try:
        from cargosim.ui.fleet_builder import get_aircraft_config_manager, AircraftType
        
        config_manager = get_aircraft_config_manager()
        
        print("\n1. Current Aircraft Configuration:")
        print("-" * 30)
        
        for aircraft in config_manager.get_all_aircraft_types():
            print(f"  {aircraft.id}:")
            print(f"    Name: {aircraft.name}")
            print(f"    Capacity: {aircraft.base_capacity}")
            print(f"    Rest Periods: {aircraft.rest_periods}")
            print(f"    Range Factor: {aircraft.range_factor}")
            print(f"    Fuel Efficiency: {aircraft.fuel_efficiency}")
            print(f"    Maintenance Cost: {aircraft.maintenance_cost}")
            print(f"    Capabilities: {', '.join(aircraft.special_capabilities)}")
            print()
        
        print("\n2. Adding a New Aircraft Type:")
        print("-" * 30)
        
        # Create a new aircraft type
        new_aircraft = AircraftType(
            id="C-295",
            name="C-295 Medium Transport",
            description="Medium tactical transport aircraft with good fuel efficiency",
            base_capacity=5,
            rest_periods=8,
            range_factor=0.9,
            fuel_efficiency=1.3,
            maintenance_cost=0.7,
            special_capabilities=["tactical", "fuel_efficient", "medium_range"],
            color="#f59e0b",
            icon="C295",
            default_count=0
        )
        
        # Add it to the configuration
        config_manager.add_aircraft_type(new_aircraft)
        print("  Added new aircraft type: C-295 Medium Transport")
        print("  Configuration saved to aircraft_config.json")
        
        # Verify it was added
        aircraft = config_manager.get_aircraft_type("C-295")
        if aircraft:
            print(f"  Verified: {aircraft.name} (Capacity: {aircraft.base_capacity})")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during aircraft management demonstration: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run the complete demonstration."""
    print("🎯 CargoSim Fleet Builder Complete Demonstration")
    print("=" * 60)
    
    success = True
    
    # Run demonstrations
    if not demo_basic_fleet_building():
        success = False
    
    if not demo_advanced_features():
        success = False
    
    if not demo_aircraft_management():
        success = False
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 All demonstrations completed successfully!")
        print("\nNext steps:")
        print("1. Launch CargoSim GUI: python -m cargosim")
        print("2. Click on the 'Fleet Builder' tab")
        print("3. Start building your custom fleets!")
        print("\nFor more information, see docs/FLEET_BUILDER_README.md")
    else:
        print("❌ Some demonstrations failed. Please check the errors above.")
    print("=" * 60)

if __name__ == "__main__":
    main()
