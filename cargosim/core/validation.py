"""Validation utilities and decorators for CargoSim."""

import functools
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
import time

logger = logging.getLogger(__name__)


@dataclass
class ValidationRule:
    """Represents a validation rule with constraints and error messages."""
    field_name: str
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    allowed_types: Optional[Tuple[type, ...]] = None
    custom_validator: Optional[Callable[[Any], bool]] = None
    error_message: str = ""
    warning_threshold: Optional[float] = None
    warning_message: str = ""


@dataclass
class ValidationResult:
    """Result of a validation operation."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    field_issues: Dict[str, List[str]]


class ValidationError(Exception):
    """Raised when validation fails."""
    def __init__(self, message: str, errors: List[str], warnings: List[str]):
        super().__init__(message)
        self.errors = errors
        self.warnings = warnings


def validate_range(value: float, min_val: Optional[float], max_val: Optional[float], 
                  field_name: str) -> Tuple[bool, List[str], List[str]]:
    """Validate a value is within specified range."""
    errors = []
    warnings = []
    
    if min_val is not None and value < min_val:
        errors.append(f"{field_name} must be at least {min_val}")
    
    if max_val is not None and value > max_val:
        errors.append(f"{field_name} must be at most {max_val}")
    
    return len(errors) == 0, errors, warnings


def validate_type(value: Any, allowed_types: Tuple[type, ...], field_name: str) -> Tuple[bool, List[str], List[str]]:
    """Validate a value is of allowed types."""
    errors = []
    warnings = []
    
    if not isinstance(value, allowed_types):
        errors.append(f"{field_name} must be of type {', '.join(t.__name__ for t in allowed_types)}")
    
    return len(errors) == 0, errors, warnings


def validate_speed_mach(speed: float) -> ValidationResult:
    """Validate aircraft speed in Mach."""
    rule = ValidationRule(
        field_name="speed_mach",
        min_value=0.1,
        max_value=2.0,
        allowed_types=(float, int),
        error_message="Speed must be between 0.1 and 2.0 Mach",
        warning_threshold=1.5,
        warning_message="Supersonic speeds may cause fuel efficiency issues"
    )
    
    errors = []
    warnings = []
    field_issues = {"speed_mach": []}
    
    # Type validation
    is_valid, type_errors, type_warnings = validate_type(speed, (float, int), rule.field_name)
    if not is_valid:
        errors.extend(type_errors)
        field_issues[rule.field_name].extend(type_errors)
    
    # Range validation
    is_valid, range_errors, range_warnings = validate_range(speed, rule.min_value, rule.max_value, rule.field_name)
    if not is_valid:
        errors.extend(range_errors)
        field_issues[rule.field_name].extend(range_errors)
    
    # Warning threshold check
    if rule.warning_threshold and speed > rule.warning_threshold:
        warnings.append(rule.warning_message)
        field_issues[rule.field_name].append(rule.warning_message)
    
    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        field_issues=field_issues
    )


def validate_spoke_distance(distance: float, spoke_index: int) -> ValidationResult:
    """Validate spoke distance."""
    rule = ValidationRule(
        field_name=f"spoke_{spoke_index}_distance",
        min_value=100.0,
        max_value=1200.0,
        allowed_types=(float, int),
        error_message=f"Spoke {spoke_index} distance must be between 100 and 1200 miles"
    )
    
    errors = []
    warnings = []
    field_issues = {rule.field_name: []}
    
    # Type validation
    is_valid, type_errors, type_warnings = validate_type(distance, (float, int), rule.field_name)
    if not is_valid:
        errors.extend(type_errors)
        field_issues[rule.field_name].extend(type_errors)
    
    # Range validation
    is_valid, range_errors, range_warnings = validate_range(distance, rule.min_value, rule.max_value, rule.field_name)
    if not is_valid:
        errors.extend(range_errors)
        field_issues[rule.field_name].extend(range_errors)
    
    # Warning for very long distances
    if distance > 800:
        warnings.append(f"Spoke {spoke_index} distance is very long and may impact performance")
        field_issues[rule.field_name].append(f"Spoke {spoke_index} distance is very long and may impact performance")
    
    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        field_issues=field_issues
    )


def validate_turnover_time(turnover_time: float) -> ValidationResult:
    """Validate turnover time."""
    rule = ValidationRule(
        field_name="turnover_time",
        min_value=0.1,
        max_value=24.0,
        allowed_types=(float, int),
        error_message="Turnover time must be between 0.1 and 24 hours",
        warning_threshold=8.0,
        warning_message="Turnover time exceeds 8 hours - consider if this is reasonable"
    )
    
    errors = []
    warnings = []
    field_issues = {rule.field_name: []}
    
    # Type validation
    is_valid, type_errors, type_warnings = validate_type(turnover_time, (float, int), rule.field_name)
    if not is_valid:
        errors.extend(type_errors)
        field_issues[rule.field_name].extend(type_errors)
    
    # Range validation
    is_valid, range_errors, range_warnings = validate_range(turnover_time, rule.min_value, rule.max_value, rule.field_name)
    if not is_valid:
        errors.extend(range_errors)
        field_issues[rule.field_name].extend(range_errors)
    
    # Warning threshold check
    if rule.warning_threshold and turnover_time > rule.warning_threshold:
        warnings.append(rule.warning_message)
        field_issues[rule.field_name].append(rule.warning_message)
    
    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        field_issues=field_issues
    )


def validate_cost_per_hour(cost: float) -> ValidationResult:
    """Validate cost per flight hour."""
    rule = ValidationRule(
        field_name="cost_per_flight_hour",
        min_value=3000.0,
        max_value=50000.0,
        allowed_types=(float, int),
        error_message="Cost per flight hour must be between $3,000 and $50,000",
        warning_threshold=25000.0,
        warning_message="Cost per flight hour is very high - verify this is correct"
    )
    
    errors = []
    warnings = []
    field_issues = {rule.field_name: []}
    
    # Type validation
    is_valid, type_errors, type_warnings = validate_type(cost, (float, int), rule.field_name)
    if not is_valid:
        errors.extend(type_errors)
        field_issues[rule.field_name].extend(type_errors)
    
    # Range validation
    is_valid, range_errors, range_warnings = validate_range(cost, rule.min_value, rule.max_value, rule.field_name)
    if not is_valid:
        errors.extend(range_errors)
        field_issues[rule.field_name].extend(range_errors)
    
    # Warning threshold check
    if rule.warning_threshold and cost > rule.warning_threshold:
        warnings.append(rule.warning_message)
        field_issues[rule.field_name].append(rule.warning_message)
    
    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        field_issues=field_issues
    )


def validate_spoke_count(spoke_count: int, max_spokes: int = 15) -> ValidationResult:
    """Validate spoke count and provide performance warnings."""
    import logging
    logger = logging.getLogger("cargosim.core.validation")
    
    logger.debug(f"Validating spoke count: {spoke_count}, max_spokes: {max_spokes}")
    
    rule = ValidationRule(
        field_name="spoke_count",
        min_value=1,
        max_value=max_spokes,
        allowed_types=(int,),
        error_message=f"Spoke count must be between 1 and {max_spokes}",
        warning_threshold=10,
        warning_message="High spoke count may impact performance - consider optimization"
    )
    
    errors = []
    warnings = []
    field_issues = {rule.field_name: []}
    
    # Type validation
    is_valid, type_errors, type_warnings = validate_type(spoke_count, (int,), rule.field_name)
    if not is_valid:
        logger.warning(f"Spoke count type validation failed: {type_errors}")
        errors.extend(type_errors)
        field_issues[rule.field_name].extend(type_errors)
    
    # Range validation
    is_valid, range_errors, range_warnings = validate_range(spoke_count, rule.min_value, rule.max_value, rule.field_name)
    if not is_valid:
        logger.warning(f"Spoke count range validation failed: {range_errors}")
        errors.extend(range_errors)
        field_issues[rule.field_name].extend(range_errors)
    
    # Warning threshold check
    if rule.warning_threshold and spoke_count > rule.warning_threshold:
        logger.info(f"Spoke count {spoke_count} exceeds warning threshold {rule.warning_threshold}")
        warnings.append(rule.warning_message)
        field_issues[rule.field_name].append(rule.warning_message)
    
    # Critical performance warning
    if spoke_count > 12:
        logger.warning(f"Very high spoke count {spoke_count} - performance may be significantly impacted")
        warnings.append("Very high spoke count - performance may be significantly impacted")
        field_issues[rule.field_name].append("Very high spoke count - performance may be significantly impacted")
    
    validation_result = ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        field_issues=field_issues
    )
    
    if validation_result.is_valid:
        logger.debug(f"Spoke count validation passed: {spoke_count}")
    else:
        logger.error(f"Spoke count validation failed: {errors}")
    
    return validation_result


def cross_validate_aircraft_performance(speed_mach: float, spoke_distances: List[float], 
                                       aircraft_type: str) -> ValidationResult:
    """Cross-validate aircraft performance parameters."""
    errors = []
    warnings = []
    field_issues = {"cross_validation": []}
    
    # Aircraft-specific validations
    if aircraft_type == "C-130":
        if speed_mach > 0.6:
            warnings.append("C-130 speed exceeds typical operational range")
            field_issues["cross_validation"].append("C-130 speed exceeds typical operational range")
        
        # Check if distances are reasonable for C-130 range
        max_operational_distance = 2000  # miles
        total_network_distance = sum(spoke_distances)
        if total_network_distance > max_operational_distance:
            warnings.append("Total network distance may exceed C-130 operational range")
            field_issues["cross_validation"].append("Total network distance may exceed C-130 operational range")
    
    elif aircraft_type == "C-27":
        if speed_mach > 0.5:
            warnings.append("C-27 speed exceeds typical operational range")
            field_issues["cross_validation"].append("C-27 speed exceeds typical operational range")
        
        # C-27 has shorter range
        max_operational_distance = 1000  # miles
        total_network_distance = sum(spoke_distances)
        if total_network_distance > max_operational_distance:
            warnings.append("Total network distance may exceed C-27 operational range")
            field_issues["cross_validation"].append("Total network distance may exceed C-27 operational range")
    
    # High-speed operations with many spokes
    if speed_mach > 1.5 and len(spoke_distances) > 10:
        warnings.append("High-speed operations with many spokes may cause performance issues")
        field_issues["cross_validation"].append("High-speed operations with many spokes may cause performance issues")
    
    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        field_issues=field_issues
    )


def validate_config_comprehensive(config_data: Dict[str, Any]) -> ValidationResult:
    """Comprehensive configuration validation."""
    all_errors = []
    all_warnings = []
    all_field_issues = {}
    
    # Validate speed
    if "speed_mach" in config_data:
        result = validate_speed_mach(config_data["speed_mach"])
        all_errors.extend(result.errors)
        all_warnings.extend(result.warnings)
        all_field_issues.update(result.field_issues)
    
    # Validate spoke distances
    if "spoke_distances" in config_data:
        spoke_distances = config_data["spoke_distances"]
        for i, distance in enumerate(spoke_distances):
            result = validate_spoke_distance(distance, i)
            all_errors.extend(result.errors)
            all_warnings.extend(result.warnings)
            all_field_issues.update(result.field_issues)
        
        # Validate spoke count
        result = validate_spoke_count(len(spoke_distances))
        all_errors.extend(result.errors)
        all_warnings.extend(result.warnings)
        all_field_issues.update(result.field_issues)
    
    # Validate turnover time
    if "turnover_time_hours" in config_data:
        result = validate_turnover_time(config_data["turnover_time_hours"])
        all_errors.extend(result.errors)
        all_warnings.extend(result.warnings)
        all_field_issues.update(result.field_issues)
    
    # Validate cost per hour
    if "cost_per_flight_hour" in config_data:
        result = validate_cost_per_hour(config_data["cost_per_flight_hour"])
        all_errors.extend(result.errors)
        all_warnings.extend(result.warnings)
        all_field_issues.update(result.field_issues)
    
    # Cross-validation
    if all(key in config_data for key in ["speed_mach", "spoke_distances", "aircraft_type"]):
        result = cross_validate_aircraft_performance(
            config_data["speed_mach"],
            config_data["spoke_distances"],
            config_data.get("aircraft_type", "C-130")
        )
        all_warnings.extend(result.warnings)
        all_field_issues.update(result.field_issues)
    
    return ValidationResult(
        is_valid=len(all_errors) == 0,
        errors=all_errors,
        warnings=all_warnings,
        field_issues=all_field_issues
    )


def validate_aircraft_config_comprehensive(aircraft_config: Dict[str, Any]) -> ValidationResult:
    """Validate complete aircraft configuration with cross-field checks."""
    all_errors = []
    all_warnings = []
    all_field_issues = {}
    
    # Validate basic aircraft fields
    if "aircraft_type" in aircraft_config:
        aircraft_type = aircraft_config["aircraft_type"]
        if aircraft_type not in ["C-130", "C-27", "C-17", "Custom"]:
            all_errors.append(f"Invalid aircraft type: {aircraft_type}")
            all_field_issues.setdefault("aircraft_type", []).append(f"Invalid aircraft type: {aircraft_type}")
    
    # Validate capacity
    if "capacity" in aircraft_config:
        capacity = aircraft_config["capacity"]
        if not isinstance(capacity, (int, float)) or capacity <= 0:
            all_errors.append("Capacity must be a positive number")
            all_field_issues.setdefault("capacity", []).append("Capacity must be a positive number")
        elif capacity > 100:
            all_warnings.append("Very high capacity - verify this is correct")
            all_field_issues.setdefault("capacity", []).append("Very high capacity - verify this is correct")
    
    # Validate speed if present
    if "speed_mach" in aircraft_config:
        result = validate_speed_mach(aircraft_config["speed_mach"])
        all_errors.extend(result.errors)
        all_warnings.extend(result.warnings)
        all_field_issues.update(result.field_issues)
    
    # Validate cost if present
    if "cost_per_flight_hour" in aircraft_config:
        result = validate_cost_per_hour(aircraft_config["cost_per_flight_hour"])
        all_errors.extend(result.errors)
        all_warnings.extend(result.warnings)
        all_field_issues.update(result.field_issues)
    
    # Validate turnover time if present
    if "turnover_time_hours" in aircraft_config:
        result = validate_turnover_time(aircraft_config["turnover_time_hours"])
        all_errors.extend(result.errors)
        all_warnings.extend(result.warnings)
        all_field_issues.update(result.field_issues)
    
    # Cross-validate aircraft-specific parameters
    if "aircraft_type" in aircraft_config and "speed_mach" in aircraft_config:
        aircraft_type = aircraft_config["aircraft_type"]
        speed_mach = aircraft_config["speed_mach"]
        
        if aircraft_type == "C-130" and speed_mach > 0.8:
            all_warnings.append("C-130 speed exceeds typical operational range")
            all_field_issues.setdefault("cross_validation", []).append("C-130 speed exceeds typical operational range")
        
        elif aircraft_type == "C-27" and speed_mach > 0.6:
            all_warnings.append("C-27 speed exceeds typical operational range")
            all_field_issues.setdefault("cross_validation", []).append("C-27 speed exceeds typical operational range")
    
    return ValidationResult(
        is_valid=len(all_errors) == 0,
        errors=all_errors,
        warnings=all_warnings,
        field_issues=all_field_issues
    )


def validate_simulation_config_comprehensive(sim_config: Dict[str, Any]) -> ValidationResult:
    """Validate complete simulation configuration."""
    all_errors = []
    all_warnings = []
    all_field_issues = {}
    
    # Validate basic simulation parameters
    if "periods" in sim_config:
        periods = sim_config["periods"]
        if not isinstance(periods, int) or periods <= 0:
            all_errors.append("Periods must be a positive integer")
            all_field_issues.setdefault("periods", []).append("Periods must be a positive integer")
        elif periods > 1000:
            all_warnings.append("Very high period count - consider if this is necessary")
            all_field_issues.setdefault("periods", []).append("Very high period count - consider if this is necessary")
    
    # Validate fleet configuration
    fleet_fields = ["cap_c130", "cap_c27", "rest_c130", "rest_c27"]
    for field in fleet_fields:
        if field in sim_config:
            value = sim_config[field]
            if not isinstance(value, (int, float)) or value < 0:
                all_errors.append(f"{field} must be a non-negative number")
                all_field_issues.setdefault(field, []).append(f"{field} must be a non-negative number")
    
    # Validate spoke configuration
    if "spoke_distances" in sim_config:
        spoke_distances = sim_config["spoke_distances"]
        if not isinstance(spoke_distances, list):
            all_errors.append("Spoke distances must be a list")
            all_field_issues.setdefault("spoke_distances", []).append("Spoke distances must be a list")
        else:
            # Validate individual spoke distances
            for i, distance in enumerate(spoke_distances):
                result = validate_spoke_distance(distance, i)
                all_errors.extend(result.errors)
                all_warnings.extend(result.warnings)
                all_field_issues.update(result.field_issues)
            
            # Validate spoke count
            result = validate_spoke_count(len(spoke_distances))
            all_errors.extend(result.errors)
            all_warnings.extend(result.warnings)
            all_field_issues.update(result.field_issues)
    
    # Validate time parameters
    time_fields = ["a_days", "b_days", "c_days", "d_days"]
    for field in time_fields:
        if field in sim_config:
            value = sim_config[field]
            if not isinstance(value, (int, float)) or value <= 0:
                all_errors.append(f"{field} must be a positive number")
                all_field_issues.setdefault(field, []).append(f"{field} must be a positive number")
    
    # Validate aircraft-specific parameters
    if "speed_mach" in sim_config:
        result = validate_speed_mach(sim_config["speed_mach"])
        all_errors.extend(result.errors)
        all_warnings.extend(result.warnings)
        all_field_issues.update(result.field_issues)
    
    if "turnover_time_hours" in sim_config:
        result = validate_turnover_time(sim_config["turnover_time_hours"])
        all_errors.extend(result.errors)
        all_warnings.extend(result.warnings)
        all_field_issues.update(result.field_issues)
    
    if "cost_per_flight_hour" in sim_config:
        result = validate_cost_per_hour(sim_config["cost_per_flight_hour"])
        all_errors.extend(result.errors)
        all_warnings.extend(result.warnings)
        all_field_issues.update(result.field_issues)
    
    # Cross-validate configuration consistency
    if all(key in sim_config for key in ["speed_mach", "spoke_distances", "aircraft_type"]):
        result = cross_validate_aircraft_performance(
            sim_config["speed_mach"],
            sim_config["spoke_distances"],
            sim_config.get("aircraft_type", "C-130")
        )
        all_warnings.extend(result.warnings)
        all_field_issues.update(result.field_issues)
    
    # Validate fleet composition
    if "cap_c130" in sim_config and "cap_c27" in sim_config:
        total_aircraft = sim_config["cap_c130"] + sim_config["cap_c27"]
        if total_aircraft == 0:
            all_errors.append("No aircraft configured in fleet")
            all_field_issues.setdefault("fleet", []).append("No aircraft configured in fleet")
        elif total_aircraft > 50:
            all_warnings.append("Very large fleet - performance may be impacted")
            all_field_issues.setdefault("fleet", []).append("Very large fleet - performance may be impacted")
    
    return ValidationResult(
        is_valid=len(all_errors) == 0,
        errors=all_errors,
        warnings=all_warnings,
        field_issues=all_field_issues
    )


def validate_spoke_distances_array(distances: List[float]) -> ValidationResult:
    """Validate array of spoke distances."""
    errors = []
    warnings = []
    field_issues = {"spoke_distances": []}
    
    if not isinstance(distances, list):
        errors.append("Spoke distances must be a list")
        field_issues["spoke_distances"].append("Spoke distances must be a list")
        return ValidationResult(False, errors, warnings, field_issues)
    
    if len(distances) == 0:
        errors.append("Spoke distances list cannot be empty")
        field_issues["spoke_distances"].append("Spoke distances list cannot be empty")
        return ValidationResult(False, errors, warnings, field_issues)
    
    if len(distances) > 20:
        errors.append("Maximum 20 spokes allowed")
        field_issues["spoke_distances"].append("Maximum 20 spokes allowed")
        return ValidationResult(False, errors, warnings, field_issues)
    
    # Validate individual distances
    for i, distance in enumerate(distances):
        if not isinstance(distance, (int, float)):
            errors.append(f"Spoke {i+1} distance must be a number")
            field_issues["spoke_distances"].append(f"Spoke {i+1} distance must be a number")
        elif distance <= 0:
            errors.append(f"Spoke {i+1} distance must be positive")
            field_issues["spoke_distances"].append(f"Spoke {i+1} distance must be positive")
        elif distance > 1200:
            errors.append(f"Spoke {i+1} distance exceeds maximum (1200 miles)")
            field_issues["spoke_distances"].append(f"Spoke {i+1} distance exceeds maximum (1200 miles)")
        elif distance > 800:
            warnings.append(f"Spoke {i+1} distance is very long ({distance} miles)")
            field_issues["spoke_distances"].append(f"Spoke {i+1} distance is very long ({distance} miles)")
    
    # Check for duplicate distances (potential configuration error)
    unique_distances = set(distances)
    if len(unique_distances) != len(distances):
        warnings.append("Duplicate spoke distances detected - verify configuration")
        field_issues["spoke_distances"].append("Duplicate spoke distances detected - verify configuration")
    
    # Check total network distance
    total_distance = sum(distances)
    if total_distance > 5000:
        warnings.append(f"Total network distance ({total_distance:.1f} miles) is very high")
        field_issues["spoke_distances"].append(f"Total network distance ({total_distance:.1f} miles) is very high")
    
    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        field_issues=field_issues
    )


def validate_aircraft_type_compatibility(aircraft_type: str, speed_mach: float, 
                                       max_distance: float) -> ValidationResult:
    """Validate aircraft type compatibility with speed and distance."""
    errors = []
    warnings = []
    field_issues = {"aircraft_compatibility": []}
    
    # Aircraft-specific limitations
    if aircraft_type == "C-130":
        max_safe_speed = 0.6
        max_operational_distance = 2000
        typical_range = 1500
    elif aircraft_type == "C-27":
        max_safe_speed = 0.5
        max_operational_distance = 1000
        typical_range = 800
    elif aircraft_type == "C-17":
        max_safe_speed = 0.8
        max_operational_distance = 5000
        typical_range = 3000
    else:
        # Custom aircraft - use conservative limits
        max_safe_speed = 0.6
        max_operational_distance = 1500
        typical_range = 1000
    
    # Speed validation
    if speed_mach > max_safe_speed:
        warnings.append(f"{aircraft_type} speed {speed_mach} Mach exceeds typical safe range")
        field_issues["aircraft_compatibility"].append(f"{aircraft_type} speed {speed_mach} Mach exceeds typical safe range")
    
    if speed_mach > 1.0:
        warnings.append(f"{aircraft_type} supersonic speed may cause fuel efficiency issues")
        field_issues["aircraft_compatibility"].append(f"{aircraft_type} supersonic speed may cause fuel efficiency issues")
    
    # Distance validation
    if max_distance > max_operational_distance:
        errors.append(f"{aircraft_type} cannot operate at {max_distance} miles (max: {max_operational_distance})")
        field_issues["aircraft_compatibility"].append(f"{aircraft_type} cannot operate at {max_distance} miles (max: {max_operational_distance})")
    
    if max_distance > typical_range:
        warnings.append(f"{aircraft_type} operating at {max_distance} miles exceeds typical range ({typical_range})")
        field_issues["aircraft_compatibility"].append(f"{aircraft_type} operating at {max_distance} miles exceeds typical range ({typical_range})")
    
    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        field_issues=field_issues
    )


# Enhanced validation decorator with caching
def cached_validation_decorator(validation_func: Callable, cache_size: int = 100) -> Callable:
    """Decorator to add validation with result caching."""
    cache = {}
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key from function arguments
            cache_key = str((func.__name__, args, sorted(kwargs.items())))
            
            # Check cache first
            if cache_key in cache:
                cached_result = cache[cache_key]
                if time.time() - cached_result['timestamp'] < 300:  # 5 minute cache
                    logger.debug(f"Using cached validation result for {func.__name__}")
                    return func(*args, **kwargs)
            
            # Run validation
            try:
                result = validation_func(*args, **kwargs)
                if not result.is_valid:
                    logger.error(f"Validation failed: {result.errors}")
                    raise ValidationError("Validation failed", result.errors, result.warnings)
                
                if result.warnings:
                    logger.warning(f"Validation warnings: {result.warnings}")
                
                # Cache successful result
                cache[cache_key] = {
                    'timestamp': time.time(),
                    'result': result
                }
                
                # Maintain cache size
                if len(cache) > cache_size:
                    # Remove oldest entries
                    oldest_keys = sorted(cache.keys(), key=lambda k: cache[k]['timestamp'])[:len(cache) - cache_size]
                    for key in oldest_keys:
                        del cache[key]
                
                # Call original function
                return func(*args, **kwargs)
            
            except Exception as e:
                logger.error(f"Validation error: {e}")
                raise
        
        return wrapper
    return decorator


def validation_decorator(validation_func: Callable) -> Callable:
    """Decorator to add validation to functions."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Run validation
            try:
                result = validation_func(*args, **kwargs)
                if not result.is_valid:
                    logger.error(f"Validation failed: {result.errors}")
                    raise ValidationError("Validation failed", result.errors, result.warnings)
                
                if result.warnings:
                    logger.warning(f"Validation warnings: {result.warnings}")
                
                # Call original function
                return func(*args, **kwargs)
            
            except Exception as e:
                logger.error(f"Validation error: {e}")
                raise
        
        return wrapper
    return decorator


def require_valid_config(func: Callable) -> Callable:
    """Decorator to ensure configuration is valid before function execution."""
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        if hasattr(self, 'cfg'):
            # Validate configuration
            result = validate_config_comprehensive(self.cfg.__dict__)
            if not result.is_valid:
                logger.error(f"Configuration validation failed: {result.errors}")
                raise ValidationError("Configuration validation failed", result.errors, result.warnings)
            
            if result.warnings:
                logger.warning(f"Configuration warnings: {result.warnings}")
        
        return func(self, *args, **kwargs)
    
    return wrapper
