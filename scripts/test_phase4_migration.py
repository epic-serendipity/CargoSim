#!/usr/bin/env python3
"""Test script for Phase 4: Configuration File Migration.

This script tests the complete migration system including:
- Configuration migration manager
- Aircraft config migration
- Simulation config migration
- Configuration validation
- Backup and rollback functionality
"""

import sys
import os
import json
import shutil
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from cargosim.core.config_migration import (
    ConfigMigrationManager, 
    MigrationResult, 
    migrate_configurations,
    get_migration_status
)
from cargosim.core.config_validator import (
    ConfigValidator, 
    ValidationResult, 
    validate_config_file,
    get_validation_report
)

def print_header(title: str):
    """Print a formatted header."""
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)

def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n--- {title} ---")

def test_migration_manager_creation():
    """Test the creation and initialization of the migration manager."""
    print_section("Testing Migration Manager Creation")
    
    try:
        manager = ConfigMigrationManager()
        print("✓ Migration manager created successfully")
        print(f"  Config directory: {manager.config_dir}")
        print(f"  Backup directory: {manager.backup_dir}")
        return True
    except Exception as e:
        print(f"✗ Failed to create migration manager: {e}")
        return False

def test_backup_creation():
    """Test backup creation functionality."""
    print_section("Testing Backup Creation")
    
    try:
        manager = ConfigMigrationManager()
        
        # Create a test file
        test_file = Path("test_config.json")
        test_data = {"test": "data", "version": 1}
        with open(test_file, 'w') as f:
            json.dump(test_data, f)
        
        # Test backup creation
        success, backup_path = manager.create_backup(test_file)
        
        if success:
            print("✓ Backup created successfully")
            print(f"  Backup path: {backup_path}")
            
            # Verify backup exists and has content
            if os.path.exists(backup_path):
                with open(backup_path, 'r') as f:
                    backup_data = json.load(f)
                if backup_data == test_data:
                    print("✓ Backup content verified")
                else:
                    print("✗ Backup content mismatch")
                    return False
            else:
                print("✗ Backup file not found")
                return False
        else:
            print("✗ Backup creation failed")
            return False
        
        # Cleanup
        test_file.unlink()
        if backup_path and os.path.exists(backup_path):
            os.unlink(backup_path)
        
        return True
        
    except Exception as e:
        print(f"✗ Backup test failed: {e}")
        return False

def test_config_validation():
    """Test configuration validation functionality."""
    print_section("Testing Configuration Validation")
    
    try:
        validator = ConfigValidator()
        print("✓ Config validator created successfully")
        
        # Test aircraft config validation
        test_aircraft_config = {
            "config_version": 2,
            "aircraft_types": {
                "C-130": {
                    "name": "C-130 Hercules",
                    "description": "Test aircraft",
                    "base_capacity": 6,
                    "rest_periods": 6,
                    "range_factor": 1.0,
                    "fuel_efficiency": 1.0,
                    "maintenance_cost": 1.0,
                    "cruise_speed_mach": 0.45,
                    "turnover_time_base": 2.0,
                    "fuel_consumption_per_hour": 1.2,
                    "operational_range_miles": 1000.0,
                    "cost_per_flight_hour": 15.0
                }
            },
            "fleet_presets": {
                "Test Fleet": {
                    "description": "Test fleet",
                    "aircraft": {"C-130": 2}
                }
            }
        }
        
        result = validator.validate_aircraft_config(test_aircraft_config)
        if result.is_valid:
            print("✓ Aircraft config validation passed")
        else:
            print("✗ Aircraft config validation failed")
            print(get_validation_report(result))
            return False
        
        # Test sim config validation
        test_sim_config = {
            "config_version": 9,
            "fleet_label": "Test Fleet",
            "periods": 30,
            "spoke_distances": [100.0] * 10,
            "variable_spoke_count": False,
            "max_spokes": 15,
            "cost_per_flight_hour": 5000.0,
            "turnover_time_multiplier": 1.0,
            "speed_units": "mach"
        }
        
        result = validator.validate_sim_config(test_sim_config)
        if result.is_valid:
            print("✓ Simulation config validation passed")
        else:
            print("✗ Simulation config validation failed")
            print(get_validation_report(result))
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ Config validation test failed: {e}")
        return False

def test_aircraft_config_migration():
    """Test aircraft configuration migration."""
    print_section("Testing Aircraft Config Migration")
    
    try:
        # Create a test v1 aircraft config
        test_v1_config = {
            "config_version": 1,
            "aircraft_types": {
                "C-130": {
                    "name": "C-130 Hercules",
                    "description": "Test aircraft",
                    "base_capacity": 6,
                    "rest_periods": 6,
                    "range_factor": 1.0,
                    "fuel_efficiency": 1.0,
                    "maintenance_cost": 1.0,
                    "special_capabilities": ["tactical"],
                    "color": "#3b82f6",
                    "icon": "C130",
                    "default_count": 2,
                    "is_custom": False,
                    "custom_attributes": {},
                    "cruise_speed_mach": 0.45,
                    "turnover_time_base": 2.0,
                    "fuel_consumption_per_hour": 1.2,
                    "operational_range_miles": 1000.0
                }
            },
            "fleet_presets": {
                "Test Fleet": {
                    "description": "Test fleet",
                    "aircraft": {"C-130": 2}
                }
            }
        }
        
        # Save test config
        test_file = Path("test_aircraft_v1.json")
        with open(test_file, 'w') as f:
            json.dump(test_v1_config, f)
        
        # Test migration
        manager = ConfigMigrationManager()
        result = manager.migrate_aircraft_config(test_file)
        
        if result.success:
            print("✓ Aircraft config migration completed successfully")
            print(f"  Migrated from v{result.source_version} to v{result.target_version}")
            print(f"  Backup created: {result.backup_path}")
            
            # Verify migrated config
            with open(test_file, 'r') as f:
                migrated_config = json.load(f)
            
            if migrated_config["config_version"] == 2:
                print("✓ Config version updated to 2")
            else:
                print(f"✗ Config version not updated: {migrated_config['config_version']}")
                return False
            
            if "cost_per_flight_hour" in migrated_config["aircraft_types"]["C-130"]:
                print("✓ Cost per flight hour field added")
            else:
                print("✗ Cost per flight hour field not added")
                return False
            
            if "migration_info" in migrated_config:
                print("✓ Migration info added")
            else:
                print("✗ Migration info not added")
                return False
            
        else:
            print("✗ Aircraft config migration failed")
            for error in result.errors:
                print(f"  Error: {error}")
            return False
        
        # Cleanup
        test_file.unlink()
        if result.backup_path and os.path.exists(result.backup_path):
            os.unlink(result.backup_path)
        
        return True
        
    except Exception as e:
        print(f"✗ Aircraft config migration test failed: {e}")
        return False

def test_sim_config_migration():
    """Test simulation configuration migration."""
    print_section("Testing Simulation Config Migration")
    
    try:
        # Create a test v8 sim config
        test_v8_config = {
            "config_version": 8,
            "fleet_label": "Test Fleet",
            "periods": 30,
            "init": [4, 4, 2, 2],
            "cadence": [2, 2, 3, 4],
            "capacities": {"C130": 6, "C27": 3},
            "rest": {"C130": 6, "C27": 12},
            "pair_order": [[0, 1], [2, 3], [4, 5], [6, 7], [8, 9]],
            "period_seconds": 0.5,
            "show_aircraft_labels": False,
            "unlimited_storage": True,
            "debug_mode": False,
            "stats_mode": "total",
            "right_panel_view": "ops_total_number",
            "orient_aircraft": True,
            "show_dos_tooltips": True,
            "hud_show_churn": True,
            "cursor_color": "Cobalt",
            "advanced_decision_making": False,
            "advanced_decision_interval": 10,
            "viz_include_side_panels": True,
            "viz_show_stats_overlay": False,
            "viz_show_aircraft_trails": True,
            "viz_right_panel_mode": "ops_total_sparkline",
            "fps": 60,
            "seed": 42,
            "launch_fullscreen": True,
            "smart_targeting_enabled": True,
            "smart_targeting_config": None,
            "bar_scale": {"denom_A": 2, "denom_B": 2, "denom_C": 2, "denom_D": 2},
            "theme": {"preset": "Classic Light"},
            "recording": {"enabled": False},
            "adm": {"enabled": False},
            "gameplay": {"seed": 42}
        }
        
        # Save test config
        test_file = Path("test_sim_v8.json")
        with open(test_file, 'w') as f:
            json.dump(test_v8_config, f)
        
        # Test migration
        manager = ConfigMigrationManager()
        result = manager.migrate_sim_config(test_file)
        
        if result.success:
            print("✓ Simulation config migration completed successfully")
            print(f"  Migrated from v{result.source_version} to v{result.target_version}")
            print(f"  Backup created: {result.backup_path}")
            
            # Verify migrated config
            with open(test_file, 'r') as f:
                migrated_config = json.load(f)
            
            if migrated_config["config_version"] == 9:
                print("✓ Config version updated to 9")
            else:
                print(f"✗ Config version not updated: {migrated_config['config_version']}")
                return False
            
            required_fields = ["spoke_distances", "variable_spoke_count", "max_spokes", 
                             "cost_per_flight_hour", "turnover_time_multiplier", "speed_units"]
            
            for field in required_fields:
                if field in migrated_config:
                    print(f"✓ {field} field added")
                else:
                    print(f"✗ {field} field not added")
                    return False
            
            if "migration_info" in migrated_config:
                print("✓ Migration info added")
            else:
                print("✗ Migration info not added")
                return False
            
        else:
            print("✗ Simulation config migration failed")
            for error in result.errors:
                print(f"  Error: {error}")
            return False
        
        # Cleanup
        test_file.unlink()
        if result.backup_path and os.path.exists(result.backup_path):
            os.unlink(result.backup_path)
        
        return True
        
    except Exception as e:
        print(f"✗ Simulation config migration test failed: {e}")
        return False

def test_migration_status():
    """Test migration status checking."""
    print_section("Testing Migration Status")
    
    try:
        manager = ConfigMigrationManager()
        
        # Test with a valid config file
        test_config = {
            "config_version": 2,
            "aircraft_types": {"test": "data"}
        }
        
        test_file = Path("test_status.json")
        with open(test_file, 'w') as f:
            json.dump(test_config, f)
        
        status = manager.get_migration_status(test_file)
        
        if status["current_version"] == 2:
            print("✓ Migration status retrieved correctly")
            print(f"  Current version: {status['current_version']}")
            print(f"  Latest version: {status['latest_version']}")
            print(f"  Needs migration: {status['needs_migration']}")
        else:
            print(f"✗ Migration status incorrect: {status}")
            return False
        
        # Cleanup
        test_file.unlink()
        
        return True
        
    except Exception as e:
        print(f"✗ Migration status test failed: {e}")
        return False

def test_rollback_functionality():
    """Test rollback functionality."""
    print_section("Testing Rollback Functionality")
    
    try:
        manager = ConfigMigrationManager()
        
        # Create test config
        test_config = {"version": 1, "data": "test"}
        test_file = Path("test_rollback.json")
        with open(test_file, 'w') as f:
            json.dump(test_config, f)
        
        # Create backup
        success, backup_path = manager.create_backup(test_file)
        if not success:
            print("✗ Failed to create backup for rollback test")
            return False
        
        # Modify the file
        modified_config = {"version": 2, "data": "modified"}
        with open(test_file, 'w') as f:
            json.dump(modified_config, f)
        
        # Test rollback
        rollback_success = manager.rollback_migration(test_file, backup_path)
        
        if rollback_success:
            print("✓ Rollback completed successfully")
            
            # Verify rollback
            with open(test_file, 'r') as f:
                restored_config = json.load(f)
            
            if restored_config == test_config:
                print("✓ File restored to original state")
            else:
                print("✗ File not restored correctly")
                return False
        else:
            print("✗ Rollback failed")
            return False
        
        # Cleanup
        test_file.unlink()
        if backup_path and os.path.exists(backup_path):
            os.unlink(backup_path)
        
        return True
        
    except Exception as e:
        print(f"✗ Rollback test failed: {e}")
        return False

def test_comprehensive_migration():
    """Test comprehensive migration of all config files."""
    print_section("Testing Comprehensive Migration")
    
    try:
        # Test the convenience function
        results = migrate_configurations()
        
        if results:
            print(f"✓ Migration completed for {len(results)} files")
            
            successful = sum(1 for r in results.values() if r.success)
            total = len(results)
            
            print(f"  Successful: {successful}/{total}")
            
            for filename, result in results.items():
                status = "✓" if result.success else "✗"
                print(f"  {status} {filename}: v{result.source_version} → v{result.target_version}")
                
                if not result.success:
                    for error in result.errors:
                        print(f"    Error: {error}")
            
            return successful == total
        else:
            print("✓ No configuration files found to migrate")
            return True
            
    except Exception as e:
        print(f"✗ Comprehensive migration test failed: {e}")
        return False

def main():
    """Run all Phase 4 migration tests."""
    print_header("Phase 4: Configuration File Migration - Test Suite")
    
    tests = [
        ("Migration Manager Creation", test_migration_manager_creation),
        ("Backup Creation", test_backup_creation),
        ("Configuration Validation", test_config_validation),
        ("Aircraft Config Migration", test_aircraft_config_migration),
        ("Simulation Config Migration", test_sim_config_migration),
        ("Migration Status", test_migration_status),
        ("Rollback Functionality", test_rollback_functionality),
        ("Comprehensive Migration", test_comprehensive_migration)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Print summary
    print_header("Test Results Summary")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"Tests Passed: {passed}/{total}")
    
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"  {status}: {test_name}")
    
    if passed == total:
        print("\n🎉 All Phase 4 migration tests passed!")
        return 0
    else:
        print(f"\n❌ {total - passed} test(s) failed. Please review the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
