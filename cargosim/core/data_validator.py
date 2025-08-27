"""Data integrity and validation system for CargoSim."""

import logging
import time
import hashlib
import json
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class DataIntegrityLevel(Enum):
    """Data integrity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ValidationStatus(Enum):
    """Validation status."""
    VALID = "valid"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class DataIntegrityCheck:
    """Represents a data integrity check."""
    field_name: str
    check_type: str
    status: ValidationStatus
    message: str
    severity: DataIntegrityLevel
    timestamp: float
    repair_attempted: bool = False
    repair_successful: bool = False


@dataclass
class DataIntegrityReport:
    """Report of data integrity validation."""
    overall_status: ValidationStatus
    checks: List[DataIntegrityCheck]
    total_checks: int
    passed_checks: int
    warnings: int
    errors: int
    critical_errors: int
    repair_recommendations: List[str]
    timestamp: float


class DataIntegrityValidator:
    """Validates data integrity and consistency."""
    
    def __init__(self):
        self.validation_history: List[DataIntegrityReport] = []
        self.max_history_size = 50
        self.auto_repair_enabled = True
        self.repair_attempts = 0
        self.max_repair_attempts = 3
        
    def validate_simulation_data(self, simulation_data: Dict[str, Any]) -> DataIntegrityReport:
        """Validate simulation data integrity."""
        logger.info("Starting simulation data integrity validation")
        
        checks = []
        repair_recommendations = []
        
        # Validate aircraft data
        aircraft_checks = self._validate_aircraft_data(simulation_data.get('aircraft', []))
        checks.extend(aircraft_checks)
        
        # Validate spoke data
        spoke_checks = self._validate_spoke_data(simulation_data.get('spokes', []))
        checks.extend(spoke_checks)
        
        # Validate configuration consistency
        config_checks = self._validate_configuration_consistency(simulation_data)
        checks.extend(config_checks)
        
        # Validate state consistency
        state_checks = self._validate_state_consistency(simulation_data)
        checks.extend(state_checks)
        
        # Validate cross-references
        reference_checks = self._validate_cross_references(simulation_data)
        checks.extend(reference_checks)
        
        # Analyze results
        overall_status = self._determine_overall_status(checks)
        
        # Generate repair recommendations
        repair_recommendations = self._generate_repair_recommendations(checks)
        
        # Create report
        report = DataIntegrityReport(
            overall_status=overall_status,
            checks=checks,
            total_checks=len(checks),
            passed_checks=sum(1 for c in checks if c.status == ValidationStatus.VALID),
            warnings=sum(1 for c in checks if c.status == ValidationStatus.WARNING),
            errors=sum(1 for c in checks if c.status == ValidationStatus.ERROR),
            critical_errors=sum(1 for c in checks if c.status == ValidationStatus.CRITICAL),
            repair_recommendations=repair_recommendations,
            timestamp=time.time()
        )
        
        # Store in history
        self.validation_history.append(report)
        if len(self.validation_history) > self.max_history_size:
            self.validation_history.pop(0)
        
        logger.info(f"Data integrity validation completed: {overall_status.value}")
        return report
    
    def _validate_aircraft_data(self, aircraft_list: List[Dict[str, Any]]) -> List[DataIntegrityCheck]:
        """Validate aircraft data integrity."""
        checks = []
        
        if not isinstance(aircraft_list, list):
            checks.append(DataIntegrityCheck(
                field_name="aircraft",
                check_type="type_validation",
                status=ValidationStatus.CRITICAL,
                message="Aircraft data must be a list",
                severity=DataIntegrityLevel.CRITICAL,
                timestamp=time.time()
            ))
            return checks
        
        for i, aircraft in enumerate(aircraft_list):
            if not isinstance(aircraft, dict):
                checks.append(DataIntegrityCheck(
                    field_name=f"aircraft[{i}]",
                    check_type="type_validation",
                    status=ValidationStatus.CRITICAL,
                    message="Aircraft must be a dictionary",
                    severity=DataIntegrityLevel.CRITICAL,
                    timestamp=time.time()
                ))
                continue
            
            # Check required fields
            required_fields = ['typ', 'cap', 'name', 'location', 'state']
            for field in required_fields:
                if field not in aircraft:
                    checks.append(DataIntegrityCheck(
                        field_name=f"aircraft[{i}].{field}",
                        check_type="required_field",
                        status=ValidationStatus.ERROR,
                        message=f"Required field '{field}' missing",
                        severity=DataIntegrityLevel.HIGH,
                        timestamp=time.time()
                    ))
            
            # Validate aircraft type
            if 'typ' in aircraft:
                valid_types = ['C-130', 'C-27', 'C-17', 'Custom']
                if aircraft['typ'] not in valid_types:
                    checks.append(DataIntegrityCheck(
                        field_name=f"aircraft[{i}].typ",
                        check_type="value_validation",
                        status=ValidationStatus.ERROR,
                        message=f"Invalid aircraft type: {aircraft['typ']}",
                        severity=DataIntegrityLevel.HIGH,
                        timestamp=time.time()
                    ))
            
            # Validate capacity
            if 'cap' in aircraft:
                if not isinstance(aircraft['cap'], (int, float)) or aircraft['cap'] <= 0:
                    checks.append(DataIntegrityCheck(
                        field_name=f"aircraft[{i}].cap",
                        check_type="value_validation",
                        status=ValidationStatus.ERROR,
                        message="Capacity must be a positive number",
                        severity=DataIntegrityLevel.HIGH,
                        timestamp=time.time()
                    ))
            
            # Validate location
            if 'location' in aircraft:
                valid_locations = ['HUB'] + [f'S{i}' for i in range(1, 16)]
                if aircraft['location'] not in valid_locations:
                    checks.append(DataIntegrityCheck(
                        field_name=f"aircraft[{i}].location",
                        check_type="value_validation",
                        status=ValidationStatus.WARNING,
                        message=f"Invalid location: {aircraft['location']}",
                        severity=DataIntegrityLevel.MEDIUM,
                        timestamp=time.time()
                    ))
            
            # Validate state
            if 'state' in aircraft:
                valid_states = ['IDLE', 'ENROUTE', 'LOADING', 'MAINTENANCE', 'LEG1_ENROUTE', 
                              'AT_SPOKEA', 'AT_SPOKEB_ENROUTE', 'AT_SPOKEB', 'RETURN_ENROUTE']
                if aircraft['state'] not in valid_states:
                    checks.append(DataIntegrityCheck(
                        field_name=f"aircraft[{i}].state",
                        check_type="value_validation",
                        status=ValidationStatus.ERROR,
                        message=f"Invalid state: {aircraft['state']}",
                        severity=DataIntegrityLevel.HIGH,
                        timestamp=time.time()
                    ))
        
        return checks
    
    def _validate_spoke_data(self, spoke_list: List[Dict[str, Any]]) -> List[DataIntegrityCheck]:
        """Validate spoke data integrity."""
        checks = []
        
        if not isinstance(spoke_list, list):
            checks.append(DataIntegrityCheck(
                field_name="spokes",
                check_type="type_validation",
                status=ValidationStatus.CRITICAL,
                message="Spoke data must be a list",
                severity=DataIntegrityLevel.CRITICAL,
                timestamp=time.time()
            ))
            return checks
        
        for i, spoke in enumerate(spoke_list):
            if not isinstance(spoke, dict):
                checks.append(DataIntegrityCheck(
                    field_name=f"spokes[{i}]",
                    check_type="type_validation",
                    status=ValidationStatus.CRITICAL,
                    message="Spoke must be a dictionary",
                    severity=DataIntegrityLevel.CRITICAL,
                    timestamp=time.time()
                ))
                continue
            
            # Check required fields
            required_fields = ['A', 'B', 'C', 'D']
            for field in required_fields:
                if field not in spoke:
                    checks.append(DataIntegrityCheck(
                        field_name=f"spokes[{i}].{field}",
                        check_type="required_field",
                        status=ValidationStatus.ERROR,
                        message=f"Required field '{field}' missing",
                        severity=DataIntegrityLevel.HIGH,
                        timestamp=time.time()
                    ))
                else:
                    # Validate field values
                    value = spoke[field]
                    if not isinstance(value, (int, float)) or value < 0:
                        checks.append(DataIntegrityCheck(
                            field_name=f"spokes[{i}].{field}",
                            check_type="value_validation",
                            status=ValidationStatus.ERROR,
                            message=f"Field '{field}' must be a non-negative number",
                            severity=DataIntegrityLevel.HIGH,
                            timestamp=time.time()
                        ))
        
        return checks
    
    def _validate_configuration_consistency(self, simulation_data: Dict[str, Any]) -> List[DataIntegrityCheck]:
        """Validate configuration consistency."""
        checks = []
        
        # Check spoke count consistency
        if 'spokes' in simulation_data and 'spoke_distances' in simulation_data:
            spoke_count = len(simulation_data['spokes'])
            distance_count = len(simulation_data['spoke_distances'])
            
            if spoke_count != distance_count:
                checks.append(DataIntegrityCheck(
                    field_name="configuration_consistency",
                    check_type="cross_field_validation",
                    status=ValidationStatus.ERROR,
                    message=f"Spoke count mismatch: {spoke_count} spokes vs {distance_count} distances",
                    severity=DataIntegrityLevel.HIGH,
                    timestamp=time.time()
                ))
        
        # Check aircraft count consistency
        if 'aircraft' in simulation_data and 'fleet_config' in simulation_data:
            aircraft_count = len(simulation_data['aircraft'])
            fleet_config = simulation_data['fleet_config']
            
            expected_count = 0
            if 'cap_c130' in fleet_config:
                expected_count += fleet_config['cap_c130']
            if 'cap_c27' in fleet_config:
                expected_count += fleet_config['cap_c27']
            
            if aircraft_count != expected_count:
                checks.append(DataIntegrityCheck(
                    field_name="fleet_consistency",
                    check_type="cross_field_validation",
                    status=ValidationStatus.WARNING,
                    message=f"Aircraft count mismatch: {aircraft_count} vs expected {expected_count}",
                    severity=DataIntegrityLevel.MEDIUM,
                    timestamp=time.time()
                ))
        
        return checks
    
    def _validate_state_consistency(self, simulation_data: Dict[str, Any]) -> List[DataIntegrityCheck]:
        """Validate state consistency."""
        checks = []
        
        if 'aircraft' not in simulation_data:
            return checks
        
        aircraft_list = simulation_data['aircraft']
        spoke_list = simulation_data.get('spokes', [])
        
        for i, aircraft in enumerate(aircraft_list):
            if not isinstance(aircraft, dict):
                continue
            
            state = aircraft.get('state', '')
            location = aircraft.get('location', '')
            
            # Validate state-location consistency
            if state == 'ENROUTE' and location not in ['HUB'] + [f'S{i}' for i in range(1, len(spoke_list) + 1)]:
                checks.append(DataIntegrityCheck(
                    field_name=f"aircraft[{i}].state_location_consistency",
                    check_type="state_validation",
                    status=ValidationStatus.ERROR,
                    message=f"ENROUTE aircraft has invalid location: {location}",
                    severity=DataIntegrityLevel.HIGH,
                    timestamp=time.time()
                ))
            
            # Validate payload consistency
            if 'payload_A' in aircraft and 'payload_B' in aircraft:
                payload_a = aircraft['payload_A']
                payload_b = aircraft['payload_B']
                
                if isinstance(payload_a, list) and isinstance(payload_b, list):
                    if len(payload_a) != 4 or len(payload_b) != 4:
                        checks.append(DataIntegrityCheck(
                            field_name=f"aircraft[{i}].payload_structure",
                            check_type="structure_validation",
                            status=ValidationStatus.ERROR,
                            message="Payload arrays must have exactly 4 elements",
                            severity=DataIntegrityLevel.HIGH,
                            timestamp=time.time()
                        ))
        
        return checks
    
    def _validate_cross_references(self, simulation_data: Dict[str, Any]) -> List[DataIntegrityCheck]:
        """Validate cross-references between data structures."""
        checks = []
        
        if 'aircraft' not in simulation_data or 'spokes' not in simulation_data:
            return checks
        
        aircraft_list = simulation_data['aircraft']
        spoke_list = simulation_data['spokes']
        
        # Check aircraft location references
        for i, aircraft in enumerate(aircraft_list):
            if not isinstance(aircraft, dict):
                continue
            
            location = aircraft.get('location', '')
            
            if location.startswith('S'):
                try:
                    spoke_index = int(location[1:]) - 1
                    if spoke_index < 0 or spoke_index >= len(spoke_list):
                        checks.append(DataIntegrityCheck(
                            field_name=f"aircraft[{i}].location_reference",
                            check_type="reference_validation",
                            status=ValidationStatus.ERROR,
                            message=f"Aircraft references non-existent spoke: {location}",
                            severity=DataIntegrityLevel.HIGH,
                            timestamp=time.time()
                        ))
                except ValueError:
                    checks.append(DataIntegrityCheck(
                        field_name=f"aircraft[{i}].location_format",
                        check_type="format_validation",
                        status=ValidationStatus.ERROR,
                        message=f"Invalid spoke location format: {location}",
                        severity=DataIntegrityLevel.HIGH,
                        timestamp=time.time()
                    ))
        
        return checks
    
    def _determine_overall_status(self, checks: List[DataIntegrityCheck]) -> ValidationStatus:
        """Determine overall validation status."""
        if any(check.status == ValidationStatus.CRITICAL for check in checks):
            return ValidationStatus.CRITICAL
        elif any(check.status == ValidationStatus.ERROR for check in checks):
            return ValidationStatus.ERROR
        elif any(check.status == ValidationStatus.WARNING for check in checks):
            return ValidationStatus.WARNING
        else:
            return ValidationStatus.VALID
    
    def _generate_repair_recommendations(self, checks: List[DataIntegrityCheck]) -> List[str]:
        """Generate repair recommendations based on validation results."""
        recommendations = []
        
        critical_checks = [c for c in checks if c.status == ValidationStatus.CRITICAL]
        error_checks = [c for c in checks if c.status == ValidationStatus.ERROR]
        warning_checks = [c for c in checks if c.status == ValidationStatus.WARNING]
        
        if critical_checks:
            recommendations.append("CRITICAL: Immediate action required to prevent system failure")
            recommendations.append("Review and fix all critical validation errors")
        
        if error_checks:
            recommendations.append("ERROR: Fix validation errors to ensure system stability")
            recommendations.append("Review error details and correct data inconsistencies")
        
        if warning_checks:
            recommendations.append("WARNING: Address warnings to improve data quality")
            recommendations.append("Consider implementing data validation rules")
        
        # Specific recommendations based on check types
        type_validation_errors = [c for c in checks if c.check_type == "type_validation"]
        if type_validation_errors:
            recommendations.append("Fix data type inconsistencies")
        
        required_field_errors = [c for c in checks if c.check_type == "required_field"]
        if required_field_errors:
            recommendations.append("Add missing required fields")
        
        cross_field_errors = [c for c in checks if c.check_type == "cross_field_validation"]
        if cross_field_errors:
            recommendations.append("Resolve cross-field validation issues")
        
        if not recommendations:
            recommendations.append("No immediate action required - data appears valid")
        
        return recommendations
    
    def attempt_auto_repair(self, report: DataIntegrityReport) -> bool:
        """Attempt automatic repair of data integrity issues."""
        if not self.auto_repair_enabled or self.repair_attempts >= self.max_repair_attempts:
            return False
        
        logger.info("Attempting automatic data repair")
        self.repair_attempts += 1
        
        repair_success = True
        
        for check in report.checks:
            if check.status in [ValidationStatus.ERROR, ValidationStatus.CRITICAL]:
                if self._attempt_check_repair(check):
                    check.repair_attempted = True
                    check.repair_successful = True
                    logger.info(f"Successfully repaired: {check.field_name}")
                else:
                    check.repair_attempted = True
                    check.repair_successful = False
                    repair_success = False
                    logger.warning(f"Failed to repair: {check.field_name}")
        
        return repair_success
    
    def _attempt_check_repair(self, check: DataIntegrityCheck) -> bool:
        """Attempt to repair a specific validation check."""
        try:
            if check.check_type == "type_validation":
                return self._repair_type_validation(check)
            elif check.check_type == "required_field":
                return self._repair_required_field(check)
            elif check.check_type == "value_validation":
                return self._repair_value_validation(check)
            else:
                return False
        except Exception as e:
            logger.error(f"Error during repair attempt: {e}")
            return False
    
    def _repair_type_validation(self, check: DataIntegrityCheck) -> bool:
        """Repair type validation issues."""
        # This would implement specific type conversion logic
        # For now, return False to indicate repair not implemented
        return False
    
    def _repair_required_field(self, check: DataIntegrityCheck) -> bool:
        """Repair missing required fields."""
        # This would implement default value assignment logic
        # For now, return False to indicate repair not implemented
        return False
    
    def _repair_value_validation(self, check: DataIntegrityCheck) -> bool:
        """Repair value validation issues."""
        # This would implement value correction logic
        # For now, return False to indicate repair not implemented
        return False
    
    def get_validation_history(self) -> List[DataIntegrityReport]:
        """Get validation history."""
        return self.validation_history.copy()
    
    def get_validation_summary(self) -> Dict[str, Any]:
        """Get summary of validation history."""
        if not self.validation_history:
            return {'message': 'No validation history available'}
        
        total_validations = len(self.validation_history)
        successful_validations = sum(1 for r in self.validation_history 
                                   if r.overall_status == ValidationStatus.VALID)
        
        return {
            'total_validations': total_validations,
            'successful_validations': successful_validations,
            'success_rate': successful_validations / total_validations if total_validations > 0 else 0.0,
            'repair_attempts': self.repair_attempts,
            'auto_repair_enabled': self.auto_repair_enabled,
            'recent_status': [r.overall_status.value for r in self.validation_history[-5:]]
        }
    
    def reset_repair_attempts(self):
        """Reset repair attempt counter."""
        self.repair_attempts = 0
        logger.info("Repair attempt counter reset")
    
    def enable_auto_repair(self):
        """Enable automatic repair."""
        self.auto_repair_enabled = True
        logger.info("Automatic data repair enabled")
    
    def disable_auto_repair(self):
        """Disable automatic repair."""
        self.auto_repair_enabled = False
        logger.info("Automatic data repair disabled")


# Data integrity decorator
def validate_data_integrity(validator: DataIntegrityValidator):
    """Decorator to validate data integrity before function execution."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Extract simulation data from arguments
            simulation_data = None
            for arg in args:
                if hasattr(arg, '__dict__') and hasattr(arg, 'get_simulation_data'):
                    simulation_data = arg.get_simulation_data()
                    break
            
            if simulation_data:
                # Validate data integrity
                report = validator.validate_simulation_data(simulation_data)
                
                if report.overall_status == ValidationStatus.CRITICAL:
                    logger.critical("Critical data integrity issues detected")
                    raise ValueError("Critical data integrity issues - cannot proceed")
                
                if report.overall_status == ValidationStatus.ERROR:
                    logger.error("Data integrity errors detected")
                    # Attempt auto-repair
                    if validator.attempt_auto_repair(report):
                        logger.info("Auto-repair successful")
                    else:
                        logger.warning("Auto-repair failed - proceeding with errors")
                
                if report.overall_status == ValidationStatus.WARNING:
                    logger.warning("Data integrity warnings detected")
            
            # Execute function
            return func(*args, **kwargs)
        
        return wrapper
    return decorator
