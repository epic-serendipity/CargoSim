"""Configuration validation system for CargoSim.

This module provides comprehensive validation of configuration files,
ensuring data integrity and proper field values.
"""

import json
import logging
from typing import Dict, Any, List, Tuple, Optional, Union
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum

logger = logging.getLogger(__name__)

class ValidationLevel(Enum):
    """Validation severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class ValidationIssue:
    """Represents a validation issue found in configuration."""
    level: ValidationLevel
    field_path: str
    message: str
    current_value: Any = None
    expected_value: Any = None
    suggestion: Optional[str] = None

@dataclass
class ValidationResult:
    """Result of a configuration validation operation."""
    is_valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    warnings: List[ValidationIssue] = field(default_factory=list)
    errors: List[ValidationIssue] = field(default_factory=list)
    critical_issues: List[ValidationIssue] = field(default_factory=list)
    
    def add_issue(self, issue: ValidationIssue):
        """Add a validation issue to the result."""
        self.issues.append(issue)
        
        if issue.level == ValidationLevel.CRITICAL:
            self.critical_issues.append(issue)
            self.is_valid = False
        elif issue.level == ValidationLevel.ERROR:
            self.errors.append(issue)
            self.is_valid = False
        elif issue.level == ValidationLevel.WARNING:
            self.warnings.append(issue)
        else:
            # INFO level doesn't affect validity
            pass
    
    def has_critical_issues(self) -> bool:
        """Check if there are any critical validation issues."""
        return len(self.critical_issues) > 0
    
    def has_errors(self) -> bool:
        """Check if there are any validation errors."""
        return len(self.errors) > 0
    
    def get_summary(self) -> str:
        """Get a summary of validation results."""
        total_issues = len(self.issues)
        critical_count = len(self.critical_issues)
        error_count = len(self.errors)
        warning_count = len(self.warnings)
        info_count = len(self.issues) - critical_count - error_count - warning_count
        
        summary = f"Validation Summary: {total_issues} total issues\n"
        if critical_count > 0:
            summary += f"  Critical: {critical_count}\n"
        if error_count > 0:
            summary += f"  Errors: {error_count}\n"
        if warning_count > 0:
            summary += f"  Warnings: {warning_count}\n"
        if info_count > 0:
            summary += f"  Info: {info_count}\n"
        
        return summary

class ConfigValidator:
    """Validates configuration files for integrity and correctness."""
    
    def __init__(self):
        # Aircraft configuration validation rules
        self.aircraft_validation_rules = {
            "config_version": {"type": int, "min": 2, "max": 10},
            "aircraft_types": {"type": dict, "required": True},
            "fleet_presets": {"type": dict, "required": True}
        }
        
        # Aircraft type validation rules
        self.aircraft_type_rules = {
            "name": {"type": str, "required": True},
            "description": {"type": str, "required": True},
            "base_capacity": {"type": (int, float), "min": 1, "max": 100},
            "rest_periods": {"type": (int, float), "min": 1, "max": 24},
            "range_factor": {"type": (int, float), "min": 0.1, "max": 5.0},
            "fuel_efficiency": {"type": (int, float), "min": 0.1, "max": 3.0},
            "maintenance_cost": {"type": (int, float), "min": 0.1, "max": 5.0},
            "cruise_speed_mach": {"type": (int, float), "min": 0.1, "max": 2.0},
            "turnover_time_base": {"type": (int, float), "min": 0.5, "max": 10.0},
            "fuel_consumption_per_hour": {"type": (int, float), "min": 0.1, "max": 10.0},
            "operational_range_miles": {"type": (int, float), "min": 100, "max": 5000},
            "cost_per_flight_hour": {"type": (int, float), "min": 1.0, "max": 100.0}
        }
        
        # Simulation configuration validation rules
        self.sim_validation_rules = {
            "config_version": {"type": int, "min": 9, "max": 20},
            "fleet_label": {"type": str, "required": True},
            "periods": {"type": int, "min": 1, "max": 1000},
            "spoke_distances": {"type": list, "min_length": 5, "max_length": 20},
            "variable_spoke_count": {"type": bool},
            "max_spokes": {"type": int, "min": 5, "max": 20},
            "cost_per_flight_hour": {"type": (int, float), "min": 100, "max": 50000},
            "turnover_time_multiplier": {"type": (int, float), "min": 0.5, "max": 3.0},
            "speed_units": {"type": str, "allowed_values": ["mach", "knots"]}
        }
    
    def validate_aircraft_config(self, config_data: Dict[str, Any]) -> ValidationResult:
        """Validate aircraft configuration file."""
        logger.info("Validating aircraft configuration")
        result = ValidationResult(is_valid=True)
        
        # Validate top-level structure
        self._validate_structure(config_data, self.aircraft_validation_rules, "", result)
        
        # Validate aircraft types
        if "aircraft_types" in config_data:
            self._validate_aircraft_types(config_data["aircraft_types"], result)
        
        # Validate fleet presets
        if "fleet_presets" in config_data:
            self._validate_fleet_presets(config_data["fleet_presets"], config_data.get("aircraft_types", {}), result)
        
        # Validate migration info if present
        if "migration_info" in config_data:
            self._validate_migration_info(config_data["migration_info"], result)
        
        return result
    
    def validate_sim_config(self, config_data: Dict[str, Any]) -> ValidationResult:
        """Validate simulation configuration file."""
        logger.info("Validating simulation configuration")
        result = ValidationResult(is_valid=True)
        
        # Validate top-level structure
        self._validate_structure(config_data, self.sim_validation_rules, "", result)
        
        # Validate spoke distances
        if "spoke_distances" in config_data:
            self._validate_spoke_distances(config_data["spoke_distances"], result)
        
        # Validate cross-field dependencies
        self._validate_cross_field_dependencies(config_data, result)
        
        # Validate migration info if present
        if "migration_info" in config_data:
            self._validate_migration_info(config_data["migration_info"], result)
        
        return result
    
    def _validate_structure(self, data: Any, rules: Dict[str, Any], field_path: str, result: ValidationResult):
        """Validate the structure of configuration data against rules."""
        for field_name, rule in rules.items():
            current_path = f"{field_path}.{field_name}" if field_path else field_name
            
            if field_name not in data:
                if rule.get("required", False):
                    result.add_issue(ValidationIssue(
                        level=ValidationLevel.ERROR,
                        field_path=current_path,
                        message=f"Required field '{field_name}' is missing",
                        suggestion=f"Add the missing field '{field_name}'"
                    ))
                continue
            
            field_value = data[field_name]
            self._validate_field_value(field_value, rule, current_path, result)
    
    def _validate_field_value(self, value: Any, rule: Dict[str, Any], field_path: str, result: ValidationResult):
        """Validate a single field value against its rule."""
        # Type validation
        expected_type = rule.get("type")
        if expected_type:
            if not isinstance(value, expected_type):
                result.add_issue(ValidationIssue(
                    level=ValidationLevel.ERROR,
                    field_path=field_path,
                    message=f"Field has wrong type. Expected {expected_type}, got {type(value).__name__}",
                    current_value=value,
                    suggestion=f"Change the value to match the expected type {expected_type}"
                ))
                return
        
        # Range validation for numeric values
        if isinstance(value, (int, float)):
            if "min" in rule and value < rule["min"]:
                result.add_issue(ValidationIssue(
                    level=ValidationLevel.ERROR,
                    field_path=field_path,
                    message=f"Value {value} is below minimum {rule['min']}",
                    current_value=value,
                    expected_value=f">= {rule['min']}",
                    suggestion=f"Increase the value to at least {rule['min']}"
                ))
            
            if "max" in rule and value > rule["max"]:
                result.add_issue(ValidationIssue(
                    level=ValidationLevel.ERROR,
                    field_path=field_path,
                    message=f"Value {value} is above maximum {rule['max']}",
                    current_value=value,
                    expected_value=f"<= {rule['max']}",
                    suggestion=f"Decrease the value to at most {rule['max']}"
                ))
        
        # Length validation for lists
        if isinstance(value, list):
            if "min_length" in rule and len(value) < rule["min_length"]:
                result.add_issue(ValidationIssue(
                    level=ValidationLevel.ERROR,
                    field_path=field_path,
                    message=f"List has {len(value)} elements, minimum required is {rule['min_length']}",
                    current_value=len(value),
                    expected_value=f">= {rule['min_length']}",
                    suggestion=f"Add more elements to reach the minimum length"
                ))
            
            if "max_length" in rule and len(value) > rule["max_length"]:
                result.add_issue(ValidationIssue(
                    level=ValidationLevel.WARNING,
                    field_path=field_path,
                    message=f"List has {len(value)} elements, maximum recommended is {rule['max_length']}",
                    current_value=len(value),
                    expected_value=f"<= {rule['max_length']}",
                    suggestion=f"Consider reducing the number of elements for better performance"
                ))
        
        # Allowed values validation for strings
        if isinstance(value, str) and "allowed_values" in rule:
            if value not in rule["allowed_values"]:
                result.add_issue(ValidationIssue(
                    level=ValidationLevel.ERROR,
                    field_path=field_path,
                    message=f"Value '{value}' is not allowed. Allowed values: {rule['allowed_values']}",
                    current_value=value,
                    expected_value=rule["allowed_values"],
                    suggestion=f"Change the value to one of: {', '.join(rule['allowed_values'])}"
                ))
    
    def _validate_aircraft_types(self, aircraft_types: Dict[str, Any], result: ValidationResult):
        """Validate aircraft type definitions."""
        for aircraft_id, aircraft_data in aircraft_types.items():
            if not isinstance(aircraft_data, dict):
                result.add_issue(ValidationIssue(
                    level=ValidationLevel.ERROR,
                    field_path=f"aircraft_types.{aircraft_id}",
                    message=f"Aircraft data must be a dictionary, got {type(aircraft_data).__name__}",
                    suggestion="Fix the aircraft data structure"
                ))
                continue
            
            # Validate each aircraft type against rules
            for field_name, rule in self.aircraft_type_rules.items():
                if field_name in aircraft_data:
                    field_path = f"aircraft_types.{aircraft_id}.{field_name}"
                    self._validate_field_value(aircraft_data[field_name], rule, field_path, result)
                elif rule.get("required", False):
                    result.add_issue(ValidationIssue(
                        level=ValidationLevel.ERROR,
                        field_path=f"aircraft_types.{aircraft_id}.{field_name}",
                        message=f"Required field '{field_name}' is missing from aircraft '{aircraft_id}'",
                        suggestion=f"Add the missing field '{field_name}' to aircraft '{aircraft_id}'"
                    ))
    
    def _validate_fleet_presets(self, fleet_presets: Dict[str, Any], aircraft_types: Dict[str, Any], result: ValidationResult):
        """Validate fleet preset definitions."""
        for fleet_name, fleet_data in fleet_presets.items():
            if not isinstance(fleet_data, dict):
                result.add_issue(ValidationIssue(
                    level=ValidationLevel.ERROR,
                    field_path=f"fleet_presets.{fleet_name}",
                    message=f"Fleet data must be a dictionary, got {type(fleet_data).__name__}",
                    suggestion="Fix the fleet data structure"
                ))
                continue
            
            # Validate required fields
            required_fields = ["description", "aircraft"]
            for field_name in required_fields:
                if field_name not in fleet_data:
                    result.add_issue(ValidationIssue(
                        level=ValidationLevel.ERROR,
                        field_path=f"fleet_presets.{fleet_name}.{field_name}",
                        message=f"Required field '{field_name}' is missing from fleet '{fleet_name}'",
                        suggestion=f"Add the missing field '{field_name}' to fleet '{fleet_name}'"
                    ))
            
            # Validate aircraft composition
            if "aircraft" in fleet_data:
                aircraft_composition = fleet_data["aircraft"]
                if not isinstance(aircraft_composition, dict):
                    result.add_issue(ValidationIssue(
                        level=ValidationLevel.ERROR,
                        field_path=f"fleet_presets.{fleet_name}.aircraft",
                        message=f"Aircraft composition must be a dictionary, got {type(aircraft_composition).__name__}",
                        suggestion="Fix the aircraft composition structure"
                    ))
                else:
                    for aircraft_type, count in aircraft_composition.items():
                        if aircraft_type not in aircraft_types:
                            result.add_issue(ValidationIssue(
                                level=ValidationLevel.WARNING,
                                field_path=f"fleet_presets.{fleet_name}.aircraft.{aircraft_type}",
                                message=f"Aircraft type '{aircraft_type}' referenced in fleet '{fleet_name}' is not defined",
                                suggestion=f"Define aircraft type '{aircraft_type}' or remove it from the fleet"
                            ))
                        
                        if not isinstance(count, (int, float)) or count <= 0:
                            result.add_issue(ValidationIssue(
                                level=ValidationLevel.ERROR,
                                field_path=f"fleet_presets.{fleet_name}.aircraft.{aircraft_type}",
                                message=f"Aircraft count must be positive, got {count}",
                                suggestion="Use a positive number for aircraft count"
                            ))
            
            # Validate cost analysis if present
            if "cost_analysis" in fleet_data:
                cost_analysis = fleet_data["cost_analysis"]
                if isinstance(cost_analysis, dict):
                    cost_fields = ["total_cost_per_hour", "total_capacity", "aircraft_count", "cost_per_capacity_unit"]
                    for field_name in cost_fields:
                        if field_name in cost_analysis:
                            field_path = f"fleet_presets.{fleet_name}.cost_analysis.{field_name}"
                            value = cost_analysis[field_name]
                            if not isinstance(value, (int, float)) or value < 0:
                                result.add_issue(ValidationIssue(
                                    level=ValidationLevel.WARNING,
                                    field_path=field_path,
                                    message=f"Cost analysis field '{field_name}' should be a non-negative number, got {value}",
                                    suggestion="Use a non-negative number for cost analysis"
                                ))
    
    def _validate_spoke_distances(self, spoke_distances: List[Any], result: ValidationResult):
        """Validate spoke distances configuration."""
        if not isinstance(spoke_distances, list):
            result.add_issue(ValidationIssue(
                level=ValidationLevel.ERROR,
                field_path="spoke_distances",
                message="Spoke distances must be a list",
                suggestion="Change spoke_distances to a list format"
            ))
            return
        
        if len(spoke_distances) < 5:
            result.add_issue(ValidationIssue(
                level=ValidationLevel.ERROR,
                field_path="spoke_distances",
                message=f"Spoke distances must have at least 5 elements, got {len(spoke_distances)}",
                suggestion="Add more spoke distance elements"
            ))
        
        if len(spoke_distances) > 20:
            result.add_issue(ValidationIssue(
                level=ValidationLevel.WARNING,
                field_path="spoke_distances",
                message=f"Spoke distances has {len(spoke_distances)} elements, maximum recommended is 20",
                suggestion="Consider reducing the number of spokes for better performance"
            ))
        
        for i, distance in enumerate(spoke_distances):
            if not isinstance(distance, (int, float)):
                result.add_issue(ValidationIssue(
                    level=ValidationLevel.ERROR,
                    field_path=f"spoke_distances[{i}]",
                    message=f"Spoke distance must be a number, got {type(distance).__name__}",
                    current_value=distance,
                    suggestion="Use a number for spoke distance"
                ))
            elif distance < 100:
                result.add_issue(ValidationIssue(
                    level=ValidationLevel.WARNING,
                    field_path=f"spoke_distances[{i}]",
                    message=f"Spoke distance {distance} miles is very short (minimum recommended: 100 miles)",
                    current_value=distance,
                    expected_value=">= 100",
                    suggestion="Consider increasing the spoke distance for more realistic operations"
                ))
            elif distance > 1000:
                result.add_issue(ValidationIssue(
                    level=ValidationLevel.WARNING,
                    field_path=f"spoke_distances[{i}]",
                    message=f"Spoke distance {distance} miles is very long (maximum recommended: 1000 miles)",
                    current_value=distance,
                    expected_value="<= 1000",
                    suggestion="Consider reducing the spoke distance for more realistic operations"
                ))
    
    def _validate_cross_field_dependencies(self, config_data: Dict[str, Any], result: ValidationResult):
        """Validate cross-field dependencies and logical consistency."""
        # Check if spoke count matches spoke distances length
        if "spoke_distances" in config_data and "max_spokes" in config_data:
            spoke_count = len(config_data["spoke_distances"])
            max_spokes = config_data["max_spokes"]
            
            if spoke_count > max_spokes:
                result.add_issue(ValidationIssue(
                    level=ValidationLevel.ERROR,
                    field_path="spoke_distances",
                    message=f"Spoke distances has {spoke_count} elements but max_spokes is set to {max_spokes}",
                    current_value=spoke_count,
                    expected_value=f"<= {max_spokes}",
                    suggestion="Either reduce the number of spoke distances or increase max_spokes"
                ))
        
        # Check if variable spoke count is enabled but max_spokes is too low
        if config_data.get("variable_spoke_count", False) and "max_spokes" in config_data:
            max_spokes = config_data["max_spokes"]
            if max_spokes < 10:
                result.add_issue(ValidationIssue(
                    level=ValidationLevel.WARNING,
                    field_path="max_spokes",
                    message=f"Variable spoke count is enabled but max_spokes is only {max_spokes}",
                    current_value=max_spokes,
                    expected_value=">= 10",
                    suggestion="Consider increasing max_spokes for better variable spoke count functionality"
                ))
    
    def _validate_migration_info(self, migration_info: Dict[str, Any], result: ValidationResult):
        """Validate migration information if present."""
        required_fields = ["migrated_from_version", "migration_date", "migration_type"]
        for field_name in required_fields:
            if field_name not in migration_info:
                result.add_issue(ValidationIssue(
                    level=ValidationLevel.WARNING,
                    field_path=f"migration_info.{field_name}",
                    message=f"Migration info field '{field_name}' is missing",
                    suggestion=f"Add the missing migration info field '{field_name}'"
                ))
        
        # Validate migration date format
        if "migration_date" in migration_info:
            migration_date = migration_info["migration_date"]
            if not isinstance(migration_date, str):
                result.add_issue(ValidationIssue(
                    level=ValidationLevel.WARNING,
                    field_path="migration_info.migration_date",
                    message=f"Migration date should be a string, got {type(migration_date).__name__}",
                    suggestion="Use ISO format string for migration date"
                ))
    
    def validate_config_file(self, file_path: Path) -> ValidationResult:
        """Validate a configuration file from disk."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # Determine config type and validate accordingly
            if "aircraft_types" in config_data:
                return self.validate_aircraft_config(config_data)
            elif "fleet_label" in config_data:
                return self.validate_sim_config(config_data)
            else:
                result = ValidationResult(is_valid=False)
                result.add_issue(ValidationIssue(
                    level=ValidationLevel.ERROR,
                    field_path="",
                    message="Unknown configuration file type",
                    suggestion="Check if this is a valid CargoSim configuration file"
                ))
                return result
                
        except json.JSONDecodeError as e:
            result = ValidationResult(is_valid=False)
            result.add_issue(ValidationIssue(
                level=ValidationLevel.CRITICAL,
                field_path="",
                message=f"Invalid JSON format: {e}",
                suggestion="Fix the JSON syntax errors in the configuration file"
            ))
            return result
        except Exception as e:
            result = ValidationResult(is_valid=False)
            result.add_issue(ValidationIssue(
                level=ValidationLevel.CRITICAL,
                field_path="",
                message=f"Failed to read configuration file: {e}",
                suggestion="Check file permissions and file integrity"
            ))
            return result
    
    def get_validation_report(self, result: ValidationResult) -> str:
        """Generate a detailed validation report."""
        report = result.get_summary()
        report += "\n" + "="*50 + "\n"
        
        if result.critical_issues:
            report += "\nCRITICAL ISSUES:\n"
            for issue in result.critical_issues:
                report += f"  {issue.field_path}: {issue.message}\n"
                if issue.suggestion:
                    report += f"    Suggestion: {issue.suggestion}\n"
        
        if result.errors:
            report += "\nERRORS:\n"
            for issue in result.errors:
                report += f"  {issue.field_path}: {issue.message}\n"
                if issue.suggestion:
                    report += f"    Suggestion: {issue.suggestion}\n"
        
        if result.warnings:
            report += "\nWARNINGS:\n"
            for issue in result.warnings:
                report += f"  {issue.field_path}: {issue.message}\n"
                if issue.suggestion:
                    report += f"    Suggestion: {issue.suggestion}\n"
        
        if result.issues and not any([result.critical_issues, result.errors, result.warnings]):
            report += "\nINFO:\n"
            for issue in result.issues:
                report += f"  {issue.field_path}: {issue.message}\n"
                if issue.suggestion:
                    report += f"    Suggestion: {issue.suggestion}\n"
        
        return report

# Global validator instance
config_validator = ConfigValidator()

def validate_config_file(file_path: str) -> ValidationResult:
    """Convenience function to validate a configuration file."""
    return config_validator.validate_config_file(Path(file_path))

def get_validation_report(result: ValidationResult) -> str:
    """Convenience function to get a validation report."""
    return config_validator.get_validation_report(result)
