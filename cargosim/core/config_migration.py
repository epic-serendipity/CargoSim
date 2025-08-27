"""Configuration migration management for CargoSim.

This module handles the migration of configuration files between versions,
ensuring backward compatibility and data integrity throughout the process.
"""

import os
import json
import shutil
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from pathlib import Path

from .paths import USER_MAIN_CONFIG_FILE, USER_CONFIGS_DIR, DEFAULT_CONFIGS_DIR
from .config import CONFIG_VERSION, SimConfig, ThemeConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class MigrationResult:
    """Result of a configuration migration operation."""
    success: bool
    source_version: int
    target_version: int
    messages: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    backup_path: Optional[str] = None
    rollback_data: Optional[Dict[str, Any]] = None

@dataclass
class MigrationMetadata:
    """Metadata about a migration operation."""
    timestamp: str
    source_version: int
    target_version: int
    migration_type: str
    backup_created: bool
    backup_path: Optional[str] = None
    user_modified: bool = False

class ConfigMigrationManager:
    """Manages configuration file migrations between versions."""
    
    def __init__(self, config_dir: Optional[str] = None):
        self.config_dir = Path(config_dir) if config_dir else USER_CONFIGS_DIR
        self.backup_dir = self.config_dir / "backups"
        self.backup_dir.mkdir(exist_ok=True)
        
        # Migration handlers for different version combinations
        self.migration_handlers = {
            (1, 2): self._migrate_aircraft_config_v1_to_v2,
            (8, 9): self._migrate_sim_config_v8_to_v9,
        }
    
    def create_backup(self, file_path: Path) -> Tuple[bool, Optional[str]]:
        """Create a backup of the configuration file."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{file_path.stem}_backup_{timestamp}{file_path.suffix}"
            backup_path = self.backup_dir / backup_name
            
            shutil.copy2(file_path, backup_path)
            logger.info(f"Backup created: {backup_path}")
            return True, str(backup_path)
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return False, None
    
    def validate_config_file(self, file_path: Path) -> Tuple[bool, List[str]]:
        """Validate a configuration file for integrity."""
        issues = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Basic JSON validation
            if not isinstance(data, dict):
                issues.append("Configuration file must contain a JSON object")
                return False, issues
            
            # Version field validation
            if "config_version" not in data:
                issues.append("Missing config_version field")
                return False, issues
            
            version = data.get("config_version")
            if not isinstance(version, int) or version < 1:
                issues.append("Invalid config_version value")
                return False, issues
            
            return True, issues
            
        except json.JSONDecodeError as e:
            issues.append(f"Invalid JSON format: {e}")
            return False, issues
        except Exception as e:
            issues.append(f"File read error: {e}")
            return False, issues
    
    def migrate_aircraft_config(self, file_path: Path) -> MigrationResult:
        """Migrate aircraft configuration file to latest version."""
        logger.info(f"Starting aircraft config migration: {file_path}")
        
        # Validate file
        is_valid, issues = self.validate_config_file(file_path)
        if not is_valid:
            return MigrationResult(
                success=False,
                source_version=0,
                target_version=2,
                errors=issues
            )
        
        # Load current config
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
        except Exception as e:
            return MigrationResult(
                success=False,
                source_version=0,
                target_version=2,
                errors=[f"Failed to load config: {e}"]
            )
        
        current_version = config_data.get("config_version", 1)
        if current_version >= 2:
            return MigrationResult(
                success=True,
                source_version=current_version,
                target_version=current_version,
                messages=["Configuration already at version 2 or higher"]
            )
        
        # Create backup
        backup_success, backup_path = self.create_backup(file_path)
        if not backup_success:
            return MigrationResult(
                success=False,
                source_version=current_version,
                target_version=2,
                errors=["Failed to create backup - migration aborted"]
            )
        
        # Perform migration
        try:
            migrated_data = self._migrate_aircraft_config_v1_to_v2(config_data)
            
            # Save migrated config
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(migrated_data, f, indent=2)
            
            # Create migration metadata
            metadata = MigrationMetadata(
                timestamp=datetime.now().isoformat(),
                source_version=current_version,
                target_version=2,
                migration_type="aircraft_config",
                backup_created=True,
                backup_path=backup_path
            )
            
            # Save metadata
            metadata_path = file_path.with_suffix('.migration.json')
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata.__dict__, f, indent=2)
            
            logger.info(f"Aircraft config migration completed successfully")
            
            return MigrationResult(
                success=True,
                source_version=current_version,
                target_version=2,
                messages=["Aircraft configuration migrated successfully to version 2"],
                backup_path=backup_path
            )
            
        except Exception as e:
            logger.error(f"Aircraft config migration failed: {e}")
            
            # Attempt rollback
            try:
                shutil.copy2(backup_path, file_path)
                logger.info("Rollback completed successfully")
            except Exception as rollback_error:
                logger.error(f"Rollback failed: {rollback_error}")
            
            return MigrationResult(
                success=False,
                source_version=current_version,
                target_version=2,
                errors=[f"Migration failed: {e}"],
                backup_path=backup_path
            )
    
    def _migrate_aircraft_config_v1_to_v2(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate aircraft configuration from version 1 to version 2."""
        logger.info("Migrating aircraft config v1 to v2")
        
        # C-130 baseline cost per flight hour (in thousands of dollars)
        C130_BASELINE_CPFH = 15.0
        
        # Aircraft cost factors relative to C-130
        aircraft_cost_factors = {
            "C-130": 1.0,      # Baseline
            "C-27": 0.8,       # 80% of C-130
            "C-17": 1.5,       # 150% of C-130
            "C-5": 2.0,        # 200% of C-130
            "C-295": 0.9,      # 90% of C-130
            "Custom_Transport": 1.1  # 110% of C-130
        }
        
        # Update config version
        config_data["config_version"] = 2
        
        # Add migration metadata
        config_data["migration_info"] = {
            "migrated_from_version": 1,
            "migration_date": datetime.now().isoformat(),
            "migration_type": "aircraft_config_v1_to_v2"
        }
        
        # Update aircraft types with cost calculations
        if "aircraft_types" in config_data:
            for aircraft_id, aircraft_data in config_data["aircraft_types"].items():
                # Calculate cost per flight hour
                cost_factor = aircraft_cost_factors.get(aircraft_id, 1.0)
                cost_per_flight_hour = C130_BASELINE_CPFH * cost_factor
                
                # Add cost field if not present
                if "cost_per_flight_hour" not in aircraft_data:
                    aircraft_data["cost_per_flight_hour"] = round(cost_per_flight_hour, 2)
                
                # Ensure all required fields are present
                required_fields = {
                    "cruise_speed_mach": 0.5,
                    "turnover_time_base": 2.0,
                    "fuel_consumption_per_hour": 1.0,
                    "operational_range_miles": 1000.0
                }
                
                for field_name, default_value in required_fields.items():
                    if field_name not in aircraft_data:
                        aircraft_data[field_name] = default_value
                        logger.info(f"Added missing field {field_name} to {aircraft_id}")
        
        # Add fleet cost analysis
        if "fleet_presets" in config_data:
            for fleet_name, fleet_data in config_data["fleet_presets"].items():
                if "aircraft" in fleet_data:
                    # Calculate fleet cost analysis
                    total_cost_per_hour = 0.0
                    total_capacity = 0
                    aircraft_count = 0
                    
                    for aircraft_type, count in fleet_data["aircraft"].items():
                        if aircraft_type in config_data.get("aircraft_types", {}):
                            aircraft_data = config_data["aircraft_types"][aircraft_type]
                            cost_per_hour = aircraft_data.get("cost_per_flight_hour", 15.0)
                            capacity = aircraft_data.get("base_capacity", 6)
                            
                            total_cost_per_hour += cost_per_hour * count
                            total_capacity += capacity * count
                            aircraft_count += count
                    
                    # Add cost analysis to fleet preset
                    fleet_data["cost_analysis"] = {
                        "total_cost_per_hour": round(total_cost_per_hour, 2),
                        "total_capacity": total_capacity,
                        "aircraft_count": aircraft_count,
                        "cost_per_capacity_unit": round(total_cost_per_hour / total_capacity, 2) if total_capacity > 0 else 0
                    }
        
        logger.info("Aircraft config v1 to v2 migration completed")
        return config_data
    
    def migrate_sim_config(self, file_path: Path) -> MigrationResult:
        """Migrate simulation configuration file to latest version."""
        logger.info(f"Starting sim config migration: {file_path}")
        
        # Validate file
        is_valid, issues = self.validate_config_file(file_path)
        if not is_valid:
            return MigrationResult(
                success=False,
                source_version=0,
                target_version=9,
                errors=issues
            )
        
        # Load current config
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
        except Exception as e:
            return MigrationResult(
                success=False,
                source_version=0,
                target_version=9,
                errors=[f"Failed to load config: {e}"]
            )
        
        current_version = config_data.get("config_version", 8)
        if current_version >= 9:
            return MigrationResult(
                success=True,
                source_version=current_version,
                target_version=current_version,
                messages=["Configuration already at version 9 or higher"]
            )
        
        # Create backup
        backup_success, backup_path = self.create_backup(file_path)
        if not backup_success:
            return MigrationResult(
                success=False,
                source_version=current_version,
                target_version=9,
                errors=["Failed to create backup - migration aborted"]
            )
        
        # Perform migration
        try:
            migrated_data = self._migrate_sim_config_v8_to_v9(config_data)
            
            # Save migrated config
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(migrated_data, f, indent=2)
            
            # Create migration metadata
            metadata = MigrationMetadata(
                timestamp=datetime.now().isoformat(),
                source_version=current_version,
                target_version=9,
                migration_type="sim_config",
                backup_created=True,
                backup_path=backup_path
            )
            
            # Save metadata
            metadata_path = file_path.with_suffix('.migration.json')
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata.__dict__, f, indent=2)
            
            logger.info(f"Sim config migration completed successfully")
            
            return MigrationResult(
                success=True,
                source_version=current_version,
                target_version=9,
                messages=["Simulation configuration migrated successfully to version 9"],
                backup_path=backup_path
            )
            
        except Exception as e:
            logger.error(f"Sim config migration failed: {e}")
            
            # Attempt rollback
            try:
                shutil.copy2(backup_path, file_path)
                logger.info("Rollback completed successfully")
            except Exception as rollback_error:
                logger.error(f"Rollback failed: {rollback_error}")
            
            return MigrationResult(
                success=False,
                source_version=current_version,
                target_version=9,
                errors=[f"Migration failed: {e}"],
                backup_path=backup_path
            )
    
    def _migrate_sim_config_v8_to_v9(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate simulation configuration from version 8 to version 9."""
        logger.info("Migrating sim config v8 to v9")
        
        # Update config version
        config_data["config_version"] = 9
        
        # Add migration metadata
        config_data["migration_info"] = {
            "migrated_from_version": 8,
            "migration_date": datetime.now().isoformat(),
            "migration_type": "sim_config_v8_to_v9"
        }
        
        # Add new time and distance mechanics fields with defaults
        new_fields = {
            "spoke_distances": [100.0] * 10,  # 10 spokes, 100 miles each
            "variable_spoke_count": False,
            "max_spokes": 15,
            "cost_per_flight_hour": 5000.0,
            "turnover_time_multiplier": 1.0,
            "speed_units": "mach"
        }
        
        for field_name, default_value in new_fields.items():
            if field_name not in config_data:
                config_data[field_name] = default_value
                logger.info(f"Added missing field {field_name} with default value")
        
        # Validate and fix spoke distances
        if "spoke_distances" in config_data:
            spoke_distances = config_data["spoke_distances"]
            if not isinstance(spoke_distances, list) or len(spoke_distances) != 10:
                config_data["spoke_distances"] = [100.0] * 10
                logger.info("Fixed spoke_distances to have 10 elements of 100 miles each")
            
            # Ensure all distances are within valid range (100-1000 miles)
            for i, distance in enumerate(config_data["spoke_distances"]):
                if not isinstance(distance, (int, float)) or distance < 100 or distance > 1000:
                    config_data["spoke_distances"][i] = 100.0
                    logger.info(f"Fixed spoke {i} distance to 100 miles (was {distance})")
        
        # Validate other numeric fields
        numeric_validations = {
            "max_spokes": (1, 20),
            "cost_per_flight_hour": (100, 50000),
            "turnover_time_multiplier": (0.5, 3.0)
        }
        
        for field_name, (min_val, max_val) in numeric_validations.items():
            if field_name in config_data:
                value = config_data[field_name]
                if not isinstance(value, (int, float)) or value < min_val or value > max_val:
                    # Use default value
                    config_data[field_name] = new_fields[field_name]
                    logger.info(f"Fixed {field_name} to default value (was {value})")
        
        # Validate speed units
        if "speed_units" in config_data:
            speed_units = config_data["speed_units"]
            if speed_units not in ["mach", "knots"]:
                config_data["speed_units"] = "mach"
                logger.info(f"Fixed speed_units to 'mach' (was {speed_units})")
        
        logger.info("Sim config v8 to v9 migration completed")
        return config_data
    
    def migrate_all_configs(self) -> Dict[str, MigrationResult]:
        """Migrate all configuration files in the config directory."""
        logger.info("Starting migration of all configuration files")
        
        results = {}
        
        # Find all config files
        config_files = list(self.config_dir.glob("*.json"))
        
        for config_file in config_files:
            if config_file.name.endswith('.migration.json'):
                continue  # Skip migration metadata files
            
            logger.info(f"Processing config file: {config_file.name}")
            
            try:
                if "aircraft" in config_file.name.lower():
                    result = self.migrate_aircraft_config(config_file)
                elif "cargo_sim" in config_file.name.lower():
                    result = self.migrate_sim_config(config_file)
                else:
                    logger.warning(f"Unknown config file type: {config_file.name}")
                    continue
                
                results[config_file.name] = result
                
            except Exception as e:
                logger.error(f"Failed to process {config_file.name}: {e}")
                results[config_file.name] = MigrationResult(
                    success=False,
                    source_version=0,
                    target_version=0,
                    errors=[f"Processing failed: {e}"]
                )
        
        # Generate migration summary
        successful = sum(1 for r in results.values() if r.success)
        total = len(results)
        
        logger.info(f"Migration completed: {successful}/{total} files migrated successfully")
        
        return results
    
    def rollback_migration(self, file_path: Path, backup_path: str) -> bool:
        """Rollback a migration using the backup file."""
        try:
            if os.path.exists(backup_path):
                shutil.copy2(backup_path, file_path)
                logger.info(f"Rollback completed for {file_path}")
                return True
            else:
                logger.error(f"Backup file not found: {backup_path}")
                return False
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False
    
    def get_migration_status(self, file_path: Path) -> Dict[str, Any]:
        """Get the migration status of a configuration file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            current_version = config_data.get("config_version", 1)
            
            # Check for migration metadata
            metadata_path = file_path.with_suffix('.migration.json')
            migration_info = None
            if metadata_path.exists():
                try:
                    with open(metadata_path, 'r', encoding='utf-8') as f:
                        migration_info = json.load(f)
                except:
                    pass
            
            return {
                "file_path": str(file_path),
                "current_version": current_version,
                "latest_version": 2 if "aircraft" in file_path.name.lower() else 9,
                "needs_migration": current_version < (2 if "aircraft" in file_path.name.lower() else 9),
                "migration_info": migration_info,
                "last_modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
            }
            
        except Exception as e:
            return {
                "file_path": str(file_path),
                "error": str(e),
                "needs_migration": False
            }

# Global migration manager instance
migration_manager = ConfigMigrationManager()

def migrate_configurations() -> Dict[str, MigrationResult]:
    """Convenience function to migrate all configurations."""
    return migration_manager.migrate_all_configs()

def get_migration_status(file_path: str) -> Dict[str, Any]:
    """Get migration status for a specific file."""
    return migration_manager.get_migration_status(Path(file_path))
