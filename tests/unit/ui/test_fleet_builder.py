#!/usr/bin/env python3
"""Test script for the Fleet Builder system."""

import sys
import os

# Add the cargosim directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'cargosim'))

def test_fleet_builder():
    """Test the fleet builder functionality."""
    print("Testing Fleet Builder System...")
    
    try:
        # Test importing the fleet builder
        from fleet_builder import (
            AircraftType, FleetComposition, FleetPreset,
            AircraftConfigManager, FleetBuilder,
            get_aircraft_config_manager, get_fleet_builder
        )
        print("✓ Fleet builder modules imported successfully")
        
        # Test aircraft config manager
        config_manager = get_aircraft_config_manager()
        print("✓ Aircraft config manager created")
        
        # Test getting aircraft types
        aircraft_types = config_manager.get_all_aircraft_types()
        print(f"✓ Found {len(aircraft_types)} aircraft types:")
        for aircraft in aircraft_types:
            print(f"  - {aircraft.name} (ID: {aircraft.id}, Capacity: {aircraft.base_capacity})")
        
        # Test getting fleet presets
        presets = config_manager.get_all_fleet_presets()
        print(f"✓ Found {len(presets)} fleet presets:")
        for preset in presets:
            print(f"  - {preset.name}: {preset.description}")
        
        # Test fleet builder
        fleet_builder = get_fleet_builder()
        print("✓ Fleet builder created")
        
        # Test creating fleet from preset
        if presets:
            preset_name = presets[0].name
            fleet = fleet_builder.create_fleet_from_preset(preset_name)
            print(f"✓ Created fleet from preset '{preset_name}'")
            print(f"  - Aircraft: {fleet.aircraft}")
            print(f"  - Total capacity: {fleet.total_capacity}")
        
        # Test creating fleet from legacy label
        legacy_fleet = fleet_builder.create_fleet_from_legacy_label("2xC130")
        print("✓ Created fleet from legacy label '2xC130'")
        print(f"  - Aircraft: {legacy_fleet.aircraft}")
        
        # Test adding aircraft
        fleet_builder.add_aircraft("C-27", 1)
        print("✓ Added C-27 to fleet")
        
        # Test fleet summary
        summary = fleet_builder.get_fleet_summary()
        print("✓ Got fleet summary:")
        print(f"  - Total aircraft: {summary['total_aircraft']}")
        print(f"  - Total capacity: {summary['total_capacity']}")
        print(f"  - Aircraft breakdown: {summary['aircraft_breakdown']}")
        
        # Test export to legacy format
        legacy_format = fleet_builder.export_fleet_to_legacy_format()
        print(f"✓ Exported to legacy format: {legacy_format}")
        
        print("\n🎉 All tests passed! Fleet Builder system is working correctly.")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

def test_aircraft_config():
    """Test the aircraft configuration file."""
    print("\nTesting Aircraft Configuration File...")
    
    config_file = os.path.join('cargosim', 'aircraft_config.json')
    
    if os.path.exists(config_file):
        print(f"✓ Aircraft config file exists: {config_file}")
        
        try:
            import json
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            print(f"✓ Config file loaded successfully")
            print(f"  - Version: {config.get('config_version', 'N/A')}")
            print(f"  - Aircraft types: {len(config.get('aircraft_types', {}))}")
            print(f"  - Fleet presets: {len(config.get('fleet_presets', {}))}")
            
            # Show aircraft types
            for aircraft_id, aircraft_data in config.get('aircraft_types', {}).items():
                print(f"  - {aircraft_id}: {aircraft_data.get('name', 'N/A')} "
                      f"(Capacity: {aircraft_data.get('base_capacity', 'N/A')})")
            
        except Exception as e:
            print(f"❌ Failed to load config file: {e}")
            return False
    else:
        print(f"❌ Aircraft config file not found: {config_file}")
        return False
    
    return True

if __name__ == "__main__":
    print("=" * 60)
    print("CargoSim Fleet Builder Test Suite")
    print("=" * 60)
    
    success = True
    
    # Test aircraft configuration
    if not test_aircraft_config():
        success = False
    
    # Test fleet builder functionality
    if not test_fleet_builder():
        success = False
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 All tests completed successfully!")
        print("The Fleet Builder system is ready to use.")
    else:
        print("❌ Some tests failed. Please check the errors above.")
    print("=" * 60)
    
    sys.exit(0 if success else 1)
