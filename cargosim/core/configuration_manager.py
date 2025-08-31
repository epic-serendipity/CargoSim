"""
Centralized Configuration Management System for CargoSim.

This module provides a robust configuration management system that eliminates
dependencies on widget hierarchy and provides reliable configuration persistence.
"""

import os
import json
import logging
import threading
import time
from typing import Dict, Any, Optional, List, Callable, Union
from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime
import shutil
import traceback

from cargosim.core.config import SimConfig, load_config, save_config
from cargosim.core.paths import get_config_dir, get_user_config_dir
from cargosim.core.health import ConfigurationStatus, ConfigurationHealth

logger = logging.getLogger(__name__)

@dataclass
class ConfigurationChange:
    """Represents a configuration change event."""
    timestamp: datetime
    section: str
    key: str
    old_value: Any
    new_value: Any
    source: str

@dataclass
class ConfigurationBackup:
    """Represents a configuration backup."""
    timestamp: datetime
    file_path: str
    size_bytes: int
    checksum: str
    description: str

class ConfigurationManager:
    """
    Centralized configuration management system.
    
    This class provides:
    - Direct file I/O operations without widget hierarchy dependencies
    - Configuration validation and integrity checking
    - Change notification system using observer pattern
    - Automatic backup and recovery mechanisms
    - Thread-safe operations
    """
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize the ConfigurationManager.
        
        Args:
            config_dir: Optional custom configuration directory
        """
        self.config_dir = Path(config_dir) if config_dir else get_user_config_dir()
        self.backup_dir = self.config_dir / "backups"
        self.backup_dir.mkdir(exist_ok=True)
        
        # Thread safety
        self._lock = threading.RLock()
        self._config_cache: Optional[SimConfig] = None
        self._last_modified: float = 0
        
        # Change notification system
        self._observers: Dict[str, List[Callable[[ConfigurationChange], None]]] = {}
        self._change_history: List[ConfigurationChange] = []
        self._max_history_size = 1000
        
        # Configuration validation
        self._validation_rules: Dict[str, Dict[str, Any]] = {}
        self._setup_validation_rules()
        
        # Performance monitoring
        self._start_time = time.time()
        self._operation_times: Dict[str, List[float]] = {}
        self._error_counts: Dict[str, int] = {}
        
        # Health status
        self._health_status = ConfigurationHealth(
            status=ConfigurationStatus.VALID,
            last_validated=datetime.now(),
            validation_errors=[],
            backup_count=0,
            last_backup=None,
            corruption_detected=False,
            recovery_attempts=0
        )
        
        # Load initial configuration
        self._load_configuration()
        
        logger.info(f"ConfigurationManager initialized with config dir: {self.config_dir}")
    
    def _setup_validation_rules(self):
        """Setup validation rules for different configuration sections."""
        self._validation_rules = {
            'spoke_config': {
                'max_spokes': {'min': 1, 'max': 20, 'type': int},
                'variable_spoke_count': {'type': bool},
                'spoke_distances': {'min_length': 1, 'max_length': 20, 'type': list}
            },
            'fleet_config': {
                'max_aircraft': {'min': 1, 'max': 100, 'type': int},
                'aircraft_types': {'type': list, 'min_length': 1}
            },
            'simulation_config': {
                'time_scale': {'min': 0.1, 'max': 10.0, 'type': float},
                'max_simulation_time': {'min': 1, 'max': 1000, 'type': int}
            }
        }
    
    def _load_configuration(self):
        """Load configuration from disk."""
        try:
            with self._lock:
                config_path = self.config_dir / "cargo_sim_config.json"
                if config_path.exists():
                    self._config_cache = load_config()
                    self._last_modified = config_path.stat().st_mtime
                    logger.info("Configuration loaded from disk")
                else:
                    # Create default configuration
                    self._config_cache = SimConfig()
                    self._save_configuration_internal()
                    logger.info("Default configuration created")
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            # Fallback to default configuration
            self._config_cache = SimConfig()
    
    def _save_configuration_internal(self) -> bool:
        """Internal method to save configuration to disk."""
        try:
            config_path = self.config_dir / "cargo_sim_config.json"
            
            # Create backup before saving
            if self._config_cache:
                self._create_backup("Pre-save backup")
            
            # Save configuration
            if self._config_cache:
                save_config(self._config_cache)
                self._last_modified = time.time()
                logger.info("Configuration saved to disk")
                return True
            return False
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
            return False
    
    def _create_backup(self, description: str) -> Optional[ConfigurationBackup]:
        """Create a backup of the current configuration."""
        try:
            if not self._config_cache:
                return None
            
            timestamp = datetime.now()
            backup_filename = f"config_backup_{timestamp.strftime('%Y%m%d_%H%M%S')}.json"
            backup_path = self.backup_dir / backup_filename
            
            # Save backup
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(self._config_cache.to_json(), f, indent=2)
            
            # Get file info
            stat = backup_path.stat()
            
            backup = ConfigurationBackup(
                timestamp=timestamp,
                file_path=str(backup_path),
                size_bytes=stat.st_size,
                checksum=self._calculate_checksum(backup_path),
                description=description
            )
            
            logger.info(f"Configuration backup created: {backup_path}")
            return backup
            
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            return None
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate a simple checksum for a file."""
        try:
            import hashlib
            hash_md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception:
            return "unknown"
    
    def _load_configuration_with_recovery(self):
        """Load configuration with automatic recovery mechanisms."""
        try:
            with self._lock:
                config_path = self.config_dir / "cargo_sim_config.json"
                
                if config_path.exists():
                    # Try to load existing configuration
                    try:
                        self._config_cache = load_config()
                        self._last_modified = config_path.stat().st_mtime
                        
                        # Validate loaded configuration
                        if self._validate_full_configuration():
                            self._health_status.status = ConfigurationStatus.VALID
                            self._health_status.last_validated = datetime.now()
                            logger.info("Configuration loaded and validated successfully")
                        else:
                            self._health_status.status = ConfigurationStatus.INVALID
                            logger.warning("Configuration loaded but validation failed")
                            
                    except Exception as load_error:
                        logger.error(f"Error loading configuration: {load_error}")
                        self._health_status.status = ConfigurationStatus.CORRUPTED
                        self._health_status.corruption_detected = True
                        
                        # Attempt recovery
                        if self._attempt_configuration_recovery():
                            logger.info("Configuration recovered successfully")
                        else:
                            logger.error("Configuration recovery failed, using defaults")
                            self._create_default_configuration()
                else:
                    # Create default configuration
                    self._create_default_configuration()
                
                # Update health status
                self._update_health_status()
                
        except Exception as e:
            logger.error(f"Critical error in configuration loading: {e}")
            self._health_status.status = ConfigurationStatus.CORRUPTED
            self._create_default_configuration()
    
    def _validate_full_configuration(self) -> bool:
        """Validate the entire configuration against all rules."""
        try:
            if not self._config_cache:
                return False
            
            validation_errors = []
            
            # Validate spoke configuration
            if hasattr(self._config_cache, 'spoke_distances'):
                spoke_config = {
                    'spoke_distances': self._config_cache.spoke_distances,
                    'max_spokes': getattr(self._config_cache, 'max_spokes', 0),
                    'variable_spoke_count': getattr(self._config_cache, 'variable_spoke_count', True)
                }
                
                if not self._validate_spoke_config(spoke_config):
                    validation_errors.append("Spoke configuration validation failed")
            
            # Validate other sections as needed
            # Add more validation logic here for other configuration sections
            
            # Update health status
            self._health_status.validation_errors = validation_errors
            self._health_status.last_validated = datetime.now()
            
            return len(validation_errors) == 0
            
        except Exception as e:
            logger.error(f"Error in full configuration validation: {e}")
            self._health_status.validation_errors.append(f"Validation error: {str(e)}")
            return False
    
    def _attempt_configuration_recovery(self) -> bool:
        """Attempt to recover corrupted configuration."""
        try:
            self._health_status.status = ConfigurationStatus.RECOVERING
            self._health_status.recovery_attempts += 1
            
            logger.info(f"Attempting configuration recovery (attempt {self._health_status.recovery_attempts})")
            
            # Try to restore from most recent backup
            backups = self.get_backups()
            if backups:
                latest_backup = backups[0]
                logger.info(f"Attempting recovery from backup: {latest_backup.file_path}")
                
                if self.restore_from_backup(latest_backup):
                    self._health_status.status = ConfigurationStatus.VALID
                    self._health_status.corruption_detected = False
                    return True
            
            # Try to repair configuration file
            if self._repair_configuration_file():
                self._health_status.status = ConfigurationStatus.VALID
                return True
            
            # If all recovery attempts fail
            self._health_status.status = ConfigurationStatus.CORRUPTED
            return False
            
        except Exception as e:
            logger.error(f"Error during configuration recovery: {e}")
            self._health_status.status = ConfigurationStatus.CORRUPTED
            return False
    
    def _repair_configuration_file(self) -> bool:
        """Attempt to repair a corrupted configuration file."""
        try:
            config_path = self.config_dir / "cargo_sim_config.json"
            
            if not config_path.exists():
                return False
            
            # Try to read and parse the file
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Try to parse JSON
                try:
                    data = json.loads(content)
                    
                    # Validate basic structure
                    if isinstance(data, dict):
                        # Create new SimConfig with valid data
                        repaired_config = SimConfig()
                        for key, value in data.items():
                            if hasattr(repaired_config, key):
                                setattr(repaired_config, key, value)
                        
                        # Validate repaired configuration
                        self._config_cache = repaired_config
                        if self._validate_full_configuration():
                            # Save repaired configuration
                            self._save_configuration_internal()
                            logger.info("Configuration file repaired successfully")
                            return True
                        
                except json.JSONDecodeError as json_error:
                    logger.warning(f"JSON parsing error: {json_error}")
                    
                    # Try to extract valid JSON from corrupted file
                    if self._extract_valid_json_from_corrupted_file(config_path):
                        return True
            
            except Exception as read_error:
                logger.warning(f"File read error: {read_error}")
            
            return False
            
        except Exception as e:
            logger.error(f"Error repairing configuration file: {e}")
            return False
    
    def _extract_valid_json_from_corrupted_file(self, config_path: Path) -> bool:
        """Extract valid JSON from a corrupted configuration file."""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Try to find valid JSON structure
            # This is a simplified approach - in production, you might want more sophisticated parsing
            
            # Look for opening and closing braces
            start_idx = content.find('{')
            end_idx = content.rfind('}')
            
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                try:
                    json_content = content[start_idx:end_idx + 1]
                    data = json.loads(json_content)
                    
                    if isinstance(data, dict):
                        # Create minimal valid configuration
                        repaired_config = SimConfig()
                        for key, value in data.items():
                            if hasattr(repaired_config, key):
                                setattr(repaired_config, key, value)
                        
                        self._config_cache = repaired_config
                        self._save_configuration_internal()
                        logger.info("Extracted valid JSON from corrupted file")
                        return True
                        
                except json.JSONDecodeError:
                    pass
            
            return False
            
        except Exception as e:
            logger.error(f"Error extracting JSON from corrupted file: {e}")
            return False
    
    def _create_default_configuration(self):
        """Create a default configuration when recovery fails."""
        try:
            logger.info("Creating default configuration")
            self._config_cache = SimConfig()
            self._health_status.status = ConfigurationStatus.VALID
            self._health_status.corruption_detected = False
            
            # Save default configuration
            self._save_configuration_internal()
            
        except Exception as e:
            logger.error(f"Error creating default configuration: {e}")
            self._health_status.status = ConfigurationStatus.CORRUPTED
    
    def _update_health_status(self):
        """Update configuration health status."""
        try:
            # Count backups
            self._health_status.backup_count = len(self.get_backups())
            
            # Get last backup time
            backups = self.get_backups()
            if backups:
                self._health_status.last_backup = backups[0].timestamp
            
        except Exception as e:
            logger.error(f"Error updating health status: {e}")
    
    def _monitor_operation(self, operation_name: str):
        """Monitor operation performance and timing."""
        start_time = time.time()
        
        def finish_operation():
            duration = time.time() - start_time
            if operation_name not in self._operation_times:
                self._operation_times[operation_name] = []
            self._operation_times[operation_name].append(duration)
            
            # Keep only last 100 measurements
            if len(self._operation_times[operation_name]) > 100:
                self._operation_times[operation_name] = self._operation_times[operation_name][-100:]
        
        return finish_operation
    
    def _log_operation_error(self, operation_name: str, error: Exception):
        """Log operation errors for monitoring."""
        if operation_name not in self._error_counts:
            self._error_counts[operation_name] = 0
        self._error_counts[operation_name] += 1
        
        logger.error(f"Operation '{operation_name}' failed: {error}")
        logger.debug(f"Operation error details: {traceback.format_exc()}")
    
    def get_configuration_health(self) -> ConfigurationHealth:
        """Get current configuration health status."""
        with self._lock:
            return ConfigurationHealth(
                status=self._health_status.status,
                last_validated=self._health_status.last_validated,
                validation_errors=self._health_status.validation_errors.copy(),
                backup_count=self._health_status.backup_count,
                last_backup=self._health_status.last_backup,
                corruption_detected=self._health_status.corruption_detected,
                recovery_attempts=self._health_status.recovery_attempts
            )
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for monitoring."""
        try:
            with self._lock:
                metrics = {
                    'uptime_seconds': time.time() - self._start_time,
                    'operation_times': {},
                    'error_counts': self._error_counts.copy(),
                    'total_operations': sum(len(times) for times in self._operation_times.values()),
                    'health_status': self._health_status.status.value
                }
                
                # Calculate average operation times
                for operation, times in self._operation_times.items():
                    if times:
                        metrics['operation_times'][operation] = {
                            'count': len(times),
                            'average_ms': sum(times) / len(times) * 1000,
                            'min_ms': min(times) * 1000,
                            'max_ms': max(times) * 1000
                        }
                
                return metrics
                
        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            return {}
    
    def force_configuration_validation(self) -> bool:
        """Force a full configuration validation."""
        try:
            with self._lock:
                logger.info("Forcing configuration validation")
                is_valid = self._validate_full_configuration()
                
                if is_valid:
                    self._health_status.status = ConfigurationStatus.VALID
                    logger.info("Configuration validation passed")
                else:
                    self._health_status.status = ConfigurationStatus.INVALID
                    logger.warning("Configuration validation failed")
                
                return is_valid
                
        except Exception as e:
            logger.error(f"Error during forced validation: {e}")
            return False
    
    def emergency_configuration_reset(self) -> bool:
        """Emergency reset of configuration to defaults."""
        try:
            with self._lock:
                logger.warning("Performing emergency configuration reset")
                
                # Create backup of current state
                self._create_backup("Emergency reset backup")
                
                # Reset to defaults
                self._create_default_configuration()
                
                # Reset health status
                self._health_status = ConfigurationHealth(
                    status=ConfigurationStatus.VALID,
                    last_validated=datetime.now(),
                    validation_errors=[],
                    backup_count=0,
                    last_backup=None,
                    corruption_detected=False,
                    recovery_attempts=0
                )
                
                logger.info("Emergency configuration reset completed")
                return True
                
        except Exception as e:
            logger.error(f"Emergency configuration reset failed: {e}")
            return False
    
    def get_configuration(self) -> SimConfig:
        """
        Get the current configuration.
        
        Returns:
            Current SimConfig instance
        """
        with self._lock:
            return self._config_cache
    
    def set_configuration(self, config: SimConfig) -> bool:
        """
        Set the current configuration.
        
        Args:
            config: SimConfig instance to set
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self._lock:
                self._config_cache = config
                self._last_modified = time.time()
                logger.info("Configuration set successfully")
                return True
        except Exception as e:
            logger.error(f"Error setting configuration: {e}")
            return False
    
    def save_spoke_config(self, spoke_config: Dict[str, Any]) -> bool:
        """
        Save spoke configuration.
        
        Args:
            spoke_config: Spoke configuration dictionary
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self._lock:
                if not self._config_cache:
                    logger.error("No configuration available")
                    return False
                
                # Validate spoke configuration
                if not self._validate_spoke_config(spoke_config):
                    logger.error("Spoke configuration validation failed")
                    return False
                
                # Update configuration
                old_spoke_distances = getattr(self._config_cache, 'spoke_distances', [])
                old_max_spokes = getattr(self._config_cache, 'max_spokes', 0)
                
                # Update spoke-related attributes
                if 'spoke_distances' in spoke_config:
                    self._config_cache.spoke_distances = spoke_config['spoke_distances']
                
                if 'max_spokes' in spoke_config:
                    self._config_cache.max_spokes = spoke_config['max_spokes']
                
                if 'variable_spoke_count' in spoke_config:
                    self._config_cache.variable_spoke_count = spoke_config['variable_spoke_count']
                
                if 'spoke_config' in spoke_config:
                    self._config_cache.spoke_config = spoke_config['spoke_config']
                
                # Generate pair order if needed
                if hasattr(self._config_cache, 'spoke_distances') and self._config_cache.spoke_distances:
                    self._config_cache.pair_order = self._generate_pair_order(
                        len(self._config_cache.spoke_distances)
                    )
                
                # Save to disk
                success = self._save_configuration_internal()
                
                if success:
                    # Notify observers of changes
                    self._notify_spoke_config_changed(
                        old_spoke_distances, 
                        self._config_cache.spoke_distances,
                        old_max_spokes,
                        getattr(self._config_cache, 'max_spokes', 0)
                    )
                    
                    logger.info(f"Spoke configuration saved successfully: {len(spoke_config.get('spoke_distances', []))} spokes")
                
                return success
                
        except Exception as e:
            logger.error(f"Error saving spoke configuration: {e}")
            return False
    
    def _validate_spoke_config(self, spoke_config: Dict[str, Any]) -> bool:
        """Validate spoke configuration against rules."""
        try:
            rules = self._validation_rules.get('spoke_config', {})
            
            # Validate max_spokes
            if 'max_spokes' in spoke_config:
                max_spokes = spoke_config['max_spokes']
                if not isinstance(max_spokes, int):
                    logger.error(f"max_spokes must be an integer, got {type(max_spokes)}")
                    return False
                if max_spokes < rules['max_spokes']['min'] or max_spokes > rules['max_spokes']['max']:
                    logger.error(f"max_spokes must be between {rules['max_spokes']['min']} and {rules['max_spokes']['max']}")
                    return False
            
            # Validate spoke_distances
            if 'spoke_distances' in spoke_config:
                distances = spoke_config['spoke_distances']
                if not isinstance(distances, list):
                    logger.error(f"spoke_distances must be a list, got {type(distances)}")
                    return False
                if len(distances) < rules['spoke_distances']['min_length']:
                    logger.error(f"spoke_distances must have at least {rules['spoke_distances']['min_length']} elements")
                    return False
                if len(distances) > rules['spoke_distances']['max_length']:
                    logger.error(f"spoke_distances must have at most {rules['spoke_distances']['max_length']} elements")
                    return False
                
                # Validate individual distances
                for i, distance in enumerate(distances):
                    if not isinstance(distance, (int, float)) or distance <= 0:
                        logger.error(f"Distance at index {i} must be a positive number, got {distance}")
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating spoke configuration: {e}")
            return False
    
    def _generate_pair_order(self, spoke_count: int) -> List[tuple]:
        """Generate pair order for spokes."""
        try:
            pair_order = []
            for i in range(0, spoke_count - 1, 2):
                if i + 1 < spoke_count:
                    pair_order.append((i, i + 1))
            
            if spoke_count % 2 == 1:  # Odd number of spokes
                pair_order.append((spoke_count - 1, 0))
            
            return pair_order
        except Exception as e:
            logger.error(f"Error generating pair order: {e}")
            return []
    
    def subscribe_to_changes(self, section: str, callback: Callable[[ConfigurationChange], None]):
        """
        Subscribe to configuration changes for a specific section.
        
        Args:
            section: Configuration section to monitor
            callback: Function to call when changes occur
        """
        with self._lock:
            if section not in self._observers:
                self._observers[section] = []
            self._observers[section].append(callback)
            logger.debug(f"Observer subscribed to {section} changes")
    
    def unsubscribe_from_changes(self, section: str, callback: Callable[[ConfigurationChange], None]):
        """
        Unsubscribe from configuration changes.
        
        Args:
            section: Configuration section
            callback: Function to remove
        """
        with self._lock:
            if section in self._observers and callback in self._observers[section]:
                self._observers[section].remove(callback)
                logger.debug(f"Observer unsubscribed from {section} changes")
    
    def _notify_spoke_config_changed(self, old_distances: List, new_distances: List, 
                                   old_max_spokes: int, new_max_spokes: int):
        """Notify observers of spoke configuration changes."""
        try:
            if 'spoke_config' not in self._observers:
                return
            
            # Create change events
            changes = []
            
            if old_distances != new_distances:
                changes.append(ConfigurationChange(
                    timestamp=datetime.now(),
                    section='spoke_config',
                    key='spoke_distances',
                    old_value=old_distances,
                    new_value=new_distances,
                    source='ConfigurationManager'
                ))
            
            if old_max_spokes != new_max_spokes:
                changes.append(ConfigurationChange(
                    timestamp=datetime.now(),
                    section='spoke_config',
                    key='max_spokes',
                    old_value=old_max_spokes,
                    new_value=new_max_spokes,
                    source='ConfigurationManager'
                ))
            
            # Notify observers
            for change in changes:
                self._change_history.append(change)
                if len(self._change_history) > self._max_history_size:
                    self._change_history.pop(0)
                
                for callback in self._observers['spoke_config']:
                    try:
                        callback(change)
                    except Exception as e:
                        logger.error(f"Error in configuration change callback: {e}")
                        
        except Exception as e:
            logger.error(f"Error notifying spoke config changes: {e}")
    
    def get_change_history(self, section: Optional[str] = None) -> List[ConfigurationChange]:
        """
        Get configuration change history.
        
        Args:
            section: Optional section filter
            
        Returns:
            List of configuration changes
        """
        with self._lock:
            if section:
                return [change for change in self._change_history if change.section == section]
            return self._change_history.copy()
    
    def get_backups(self) -> List[ConfigurationBackup]:
        """Get list of available configuration backups."""
        try:
            backups = []
            for backup_file in self.backup_dir.glob("config_backup_*.json"):
                try:
                    stat = backup_file.stat()
                    timestamp = datetime.fromtimestamp(stat.st_mtime)
                    
                    backup = ConfigurationBackup(
                        timestamp=timestamp,
                        file_path=str(backup_file),
                        size_bytes=stat.st_size,
                        checksum=self._calculate_checksum(backup_file),
                        description=f"Auto-backup from {timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
                    )
                    backups.append(backup)
                except Exception as e:
                    logger.warning(f"Error reading backup file {backup_file}: {e}")
            
            # Sort by timestamp (newest first)
            backups.sort(key=lambda x: x.timestamp, reverse=True)
            return backups
            
        except Exception as e:
            logger.error(f"Error getting backups: {e}")
            return []
    
    def restore_from_backup(self, backup: ConfigurationBackup) -> bool:
        """
        Restore configuration from a backup.
        
        Args:
            backup: ConfigurationBackup instance to restore from
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self._lock:
                # Create backup of current configuration
                self._create_backup("Pre-restore backup")
                
                # Load backup configuration
                backup_path = Path(backup.file_path)
                if not backup_path.exists():
                    logger.error(f"Backup file not found: {backup_path}")
                    return False
                
                # Load and validate backup
                with open(backup_path, 'r', encoding='utf-8') as f:
                    backup_data = json.load(f)
                
                # Create new SimConfig from backup
                restored_config = SimConfig()
                for key, value in backup_data.items():
                    if hasattr(restored_config, key):
                        setattr(restored_config, key, value)
                
                # Replace current configuration
                self._config_cache = restored_config
                
                # Save restored configuration
                success = self._save_configuration_internal()
                
                if success:
                    logger.info(f"Configuration restored from backup: {backup_path}")
                    
                    # Notify observers of major change
                    self._notify_configuration_restored()
                
                return success
                
        except Exception as e:
            logger.error(f"Error restoring from backup: {e}")
            return False
    
    def _notify_configuration_restored(self):
        """Notify observers that configuration was restored."""
        try:
            change = ConfigurationChange(
                timestamp=datetime.now(),
                section='system',
                key='configuration_restored',
                old_value=None,
                new_value='restored',
                source='ConfigurationManager'
            )
            
            # Notify all observers
            for section, callbacks in self._observers.items():
                for callback in callbacks:
                    try:
                        callback(change)
                    except Exception as e:
                        logger.error(f"Error in configuration restore callback: {e}")
                        
        except Exception as e:
            logger.error(f"Error notifying configuration restore: {e}")
    
    def cleanup_old_backups(self, keep_count: int = 10) -> int:
        """
        Clean up old backup files, keeping only the most recent ones.
        
        Args:
            keep_count: Number of backups to keep
            
        Returns:
            Number of backups removed
        """
        try:
            backups = self.get_backups()
            if len(backups) <= keep_count:
                return 0
            
            # Remove old backups
            removed_count = 0
            for backup in backups[keep_count:]:
                try:
                    backup_path = Path(backup.file_path)
                    if backup_path.exists():
                        backup_path.unlink()
                        removed_count += 1
                        logger.info(f"Removed old backup: {backup_path}")
                except Exception as e:
                    logger.warning(f"Error removing backup {backup.file_path}: {e}")
            
            logger.info(f"Cleaned up {removed_count} old backup files")
            return removed_count
            
        except Exception as e:
            logger.error(f"Error cleaning up old backups: {e}")
            return 0

# Global instance
_configuration_manager: Optional[ConfigurationManager] = None

def get_configuration_manager() -> ConfigurationManager:
    """Get the global ConfigurationManager instance."""
    global _configuration_manager
    if _configuration_manager is None:
        _configuration_manager = ConfigurationManager()
    return _configuration_manager
