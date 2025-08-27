"""Unit tests for edge case handling and validation in Phase 5."""

import pytest
import time
from unittest.mock import Mock, patch
from cargosim.core.validation import (
    ValidationRule, ValidationResult, ValidationError,
    validate_speed_mach, validate_spoke_distance, validate_turnover_time,
    validate_cost_per_hour, validate_spoke_count, cross_validate_aircraft_performance,
    validate_config_comprehensive
)
from cargosim.core.performance import (
    PerformanceOptimizer, DistanceCache, FlightTimeCache,
    MemoryMonitor, PerformanceMetrics
)
from cargosim.core.error_handler import (
    ErrorHandler, ErrorSeverity, RecoveryStrategy,
    GracefulDegradation, SelfHealingSystem
)
from cargosim.core.edge_case_handler import (
    EdgeCaseHandler, StressTester, StressLevel
)
from cargosim.core.data_validator import (
    DataValidator, DataIntegrityStatus, ValidationIssue
)


class TestValidationModule:
    """Test the validation module functionality."""
    
    def test_validation_rule_creation(self):
        """Test ValidationRule dataclass creation."""
        rule = ValidationRule(
            field_name="test_field",
            min_value=0.0,
            max_value=100.0,
            allowed_types=(int, float),
            error_message="Test error",
            warning_threshold=50.0,
            warning_message="Test warning"
        )
        
        assert rule.field_name == "test_field"
        assert rule.min_value == 0.0
        assert rule.max_value == 100.0
        assert rule.allowed_types == (int, float)
        assert rule.error_message == "Test error"
        assert rule.warning_threshold == 50.0
        assert rule.warning_message == "Test warning"
    
    def test_validation_result_creation(self):
        """Test ValidationResult dataclass creation."""
        result = ValidationResult(
            is_valid=True,
            errors=["error1"],
            warnings=["warning1"],
            field_issues={"field1": ["issue1"]}
        )
        
        assert result.is_valid is True
        assert result.errors == ["error1"]
        assert result.warnings == ["warning1"]
        assert result.field_issues == {"field1": ["issue1"]}
    
    def test_validate_speed_mach_valid(self):
        """Test speed validation with valid values."""
        result = validate_speed_mach(0.45)
        assert result.is_valid is True
        assert len(result.errors) == 0
        assert len(result.warnings) == 0
    
    def test_validate_speed_mach_too_low(self):
        """Test speed validation with too low value."""
        result = validate_speed_mach(0.05)
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert "must be at least 0.1" in result.errors[0]
    
    def test_validate_speed_mach_too_high(self):
        """Test speed validation with too high value."""
        result = validate_speed_mach(2.5)
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert "must be at most 2.0" in result.errors[0]
    
    def test_validate_speed_mach_warning_threshold(self):
        """Test speed validation warning threshold."""
        result = validate_speed_mach(1.6)
        assert result.is_valid is True
        assert len(result.warnings) == 1
        assert "Supersonic speeds" in result.warnings[0]
    
    def test_validate_spoke_distance_valid(self):
        """Test spoke distance validation with valid values."""
        result = validate_spoke_distance(500.0, 0)
        assert result.is_valid is True
        assert len(result.errors) == 0
    
    def test_validate_spoke_distance_too_low(self):
        """Test spoke distance validation with too low value."""
        result = validate_spoke_distance(50.0, 0)
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert "must be between 100 and 1200" in result.errors[0]
    
    def test_validate_spoke_distance_too_high(self):
        """Test spoke distance validation with too high value."""
        result = validate_spoke_distance(1500.0, 0)
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert "must be between 100 and 1200" in result.errors[0]
    
    def test_validate_spoke_distance_warning(self):
        """Test spoke distance validation warning for long distances."""
        result = validate_spoke_distance(900.0, 0)
        assert result.is_valid is True
        assert len(result.warnings) == 1
        assert "very long" in result.warnings[0]
    
    def test_validate_turnover_time_valid(self):
        """Test turnover time validation with valid values."""
        result = validate_turnover_time(4.0)
        assert result.is_valid is True
        assert len(result.errors) == 0
    
    def test_validate_turnover_time_too_low(self):
        """Test turnover time validation with too low value."""
        result = validate_turnover_time(0.05)
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert "must be between 0.1 and 24" in result.errors[0]
    
    def test_validate_turnover_time_warning(self):
        """Test turnover time validation warning threshold."""
        result = validate_turnover_time(10.0)
        assert result.is_valid is True
        assert len(result.warnings) == 1
        assert "exceeds 8 hours" in result.warnings[0]
    
    def test_validate_cost_per_hour_valid(self):
        """Test cost per hour validation with valid values."""
        result = validate_cost_per_hour(15000.0)
        assert result.is_valid is True
        assert len(result.errors) == 0
    
    def test_validate_cost_per_hour_too_low(self):
        """Test cost per hour validation with too low value."""
        result = validate_cost_per_hour(2000.0)
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert "must be between $3,000 and $50,000" in result.errors[0]
    
    def test_validate_spoke_count_valid(self):
        """Test spoke count validation with valid values."""
        result = validate_spoke_count(8)
        assert result.is_valid is True
        assert len(result.errors) == 0
    
    def test_validate_spoke_count_too_high(self):
        """Test spoke count validation with too high value."""
        result = validate_spoke_count(25)
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert "must be between 1 and 15" in result.errors[0]
    
    def test_validate_spoke_count_warning(self):
        """Test spoke count validation warning threshold."""
        result = validate_spoke_count(12)
        assert result.is_valid is True
        assert len(result.warnings) == 1
        assert "may impact performance" in result.warnings[0]
    
    def test_cross_validate_aircraft_performance_c130(self):
        """Test cross-validation for C-130 aircraft."""
        result = cross_validate_aircraft_performance(0.7, [500, 600, 700], "C-130")
        assert result.is_valid is True
        assert len(result.warnings) == 1
        assert "exceeds typical operational range" in result.warnings[0]
    
    def test_cross_validate_aircraft_performance_c27(self):
        """Test cross-validation for C-27 aircraft."""
        result = cross_validate_aircraft_performance(0.6, [800, 900, 1000], "C-27")
        assert result.is_valid is True
        assert len(result.warnings) == 2  # Speed and range warnings
    
    def test_validate_config_comprehensive(self):
        """Test comprehensive configuration validation."""
        config_data = {
            "speed_mach": 0.45,
            "spoke_distances": [300, 400, 500],
            "turnover_time_hours": 3.0,
            "cost_per_flight_hour": 15000.0
        }
        
        result = validate_config_comprehensive(config_data)
        assert result.is_valid is True
        assert len(result.errors) == 0


class TestPerformanceModule:
    """Test the performance optimization module."""
    
    def test_performance_metrics_creation(self):
        """Test PerformanceMetrics dataclass creation."""
        metrics = PerformanceMetrics(
            simulation_time=1.5,
            memory_usage_mb=250.0,
            cache_hit_rate=0.85
        )
        
        assert metrics.simulation_time == 1.5
        assert metrics.memory_usage_mb == 250.0
        assert metrics.cache_hit_rate == 0.85
    
    def test_distance_cache_operations(self):
        """Test DistanceCache basic operations."""
        cache = DistanceCache(max_size=5)
        
        # Test set and get
        cache.set((1, 2), 300.0)
        assert cache.get((1, 2)) == 300.0
        assert cache.get((2, 1)) == 300.0  # Should normalize key
        
        # Test cache stats
        stats = cache.get_stats()
        assert stats['hits'] == 2
        assert stats['misses'] == 0
        assert stats['size'] == 1
    
    def test_flight_time_cache_operations(self):
        """Test FlightTimeCache basic operations."""
        cache = FlightTimeCache(max_size=3)
        
        # Test set and get
        cache.set((1, 2, 0.45), 2.5)
        assert cache.get((1, 2, 0.45)) == 2.5
        
        # Test cache stats
        stats = cache.get_stats()
        assert stats['hits'] == 1
        assert stats['misses'] == 0
    
    def test_memory_monitor_basic(self):
        """Test MemoryMonitor basic functionality."""
        monitor = MemoryMonitor(warning_threshold=100.0, critical_threshold=200.0)
        
        # Test memory status check
        status = monitor.check_memory_status()
        assert 'current_memory_mb' in status
        assert 'status' in status
        assert 'warnings' in status
        assert 'recommendations' in status
    
    def test_performance_optimizer_initialization(self):
        """Test PerformanceOptimizer initialization."""
        optimizer = PerformanceOptimizer()
        
        assert optimizer.optimization_enabled is True
        assert optimizer.distance_cache is not None
        assert optimizer.flight_time_cache is not None
        assert optimizer.memory_monitor is not None
    
    def test_performance_optimizer_distance_calculation(self):
        """Test PerformanceOptimizer distance calculation."""
        optimizer = PerformanceOptimizer()
        spoke_distances = [300, 400, 500]
        
        # Test hub to spoke distance
        distance = optimizer.calculate_distance(0, 1, spoke_distances)
        assert distance == 300.0
        
        # Test spoke to spoke distance
        distance = optimizer.calculate_distance(1, 2, spoke_distances)
        assert distance == 700.0  # 400 + 300
    
    def test_performance_optimizer_flight_time_calculation(self):
        """Test PerformanceOptimizer flight time calculation."""
        optimizer = PerformanceOptimizer()
        spoke_distances = [300, 400, 500]
        
        flight_time = optimizer.calculate_flight_time(0, 1, 0.45, spoke_distances)
        assert flight_time > 0
        
        # Test caching
        cached_time = optimizer.get_cached_flight_time(0, 1, 0.45)
        assert cached_time == flight_time
    
    def test_performance_optimizer_large_scale(self):
        """Test PerformanceOptimizer large scale optimizations."""
        optimizer = PerformanceOptimizer()
        
        # Test with high spoke count
        optimizations = optimizer.optimize_for_large_scale(16)
        assert optimizations['performance_mode'] == 'critical'
        assert optimizations['garbage_collection_forced'] is True


class TestErrorHandler:
    """Test the error handling and recovery module."""
    
    def test_error_handler_initialization(self):
        """Test ErrorHandler initialization."""
        handler = ErrorHandler()
        
        assert handler.error_count == 0
        assert handler.fallback_mode is False
        assert handler.error_threshold == 5
        assert len(handler.recovery_actions) == 5
    
    def test_error_severity_assessment(self):
        """Test error severity assessment."""
        handler = ErrorHandler()
        
        # Test critical error
        context = {'function_name': 'test_function'}
        error = MemoryError("Out of memory")
        severity = handler._assess_error_severity(error, context)
        assert severity == ErrorSeverity.CRITICAL
        
        # Test high severity error
        error = ValueError("Invalid value")
        severity = handler._assess_error_severity(error, context)
        assert severity == ErrorSeverity.HIGH
    
    def test_recovery_strategy_determination(self):
        """Test recovery strategy determination."""
        handler = ErrorHandler()
        
        # Test critical error strategy
        error = MemoryError("Out of memory")
        context = {'function_name': 'test_function'}
        strategy = handler._determine_recovery_strategy(error, context)
        assert strategy == RecoveryStrategy.ABORT
        
        # Test high severity error strategy
        error = ValueError("Invalid value")
        strategy = handler._determine_recovery_strategy(error, context)
        assert strategy == RecoveryStrategy.RETRY
    
    def test_fallback_mode_activation(self):
        """Test fallback mode activation."""
        handler = ErrorHandler()
        
        # Create error context
        error_context = Mock()
        error_context.function_name = "test_function"
        error_context.recovery_strategy = RecoveryStrategy.FALLBACK
        
        # Activate fallback mode
        success = handler._activate_fallback_mode(error_context)
        assert success is True
        assert handler.fallback_mode is True
    
    def test_graceful_degradation(self):
        """Test graceful degradation functionality."""
        error_handler = ErrorHandler()
        degradation = GracefulDegradation(error_handler)
        
        # Test degradation levels
        degradation.degrade_functionality('reduced')
        assert degradation.current_level == 'reduced'
        
        # Test operation capability
        assert degradation.can_perform_operation(50) is True
        assert degradation.can_perform_operation(100) is False
    
    def test_self_healing_system(self):
        """Test self-healing system functionality."""
        error_handler = ErrorHandler()
        healing = SelfHealingSystem(error_handler)
        
        # Test healing attempt
        success = healing.attempt_healing()
        assert success is True  # Should succeed when system is stable


class TestEdgeCaseHandler:
    """Test the edge case handling module."""
    
    def test_edge_case_handler_initialization(self):
        """Test EdgeCaseHandler initialization."""
        handler = EdgeCaseHandler()
        
        assert len(handler.edge_case_scenarios) == 5
        assert handler.current_stress_level == StressLevel.NORMAL
    
    def test_handle_large_spoke_count(self):
        """Test handling of large spoke counts."""
        handler = EdgeCaseHandler()
        
        # Test normal spoke count
        result = handler.handle_large_spoke_count(8)
        assert result['warning_level'] == 'none'
        assert result['performance_mode'] == 'standard'
        
        # Test high spoke count
        result = handler.handle_large_spoke_count(13)
        assert result['warning_level'] == 'high'
        assert result['performance_mode'] == 'optimized'
        assert len(result['recommendations']) > 0
    
    def test_validate_extreme_speeds(self):
        """Test validation of extreme speeds."""
        handler = EdgeCaseHandler()
        
        # Test normal speed
        result = handler.validate_extreme_speeds(0.45, "C-130")
        assert result['warning_level'] == 'none'
        assert result['cost_impact'] == 'normal'
        
        # Test extreme speed
        result = handler.validate_extreme_speeds(1.8, "C-130")
        assert result['warning_level'] == 'critical'
        assert result['cost_impact'] == 'extreme'
        assert result['safety_check'] == 'required'
    
    def test_handle_extreme_distances(self):
        """Test handling of extreme distances."""
        handler = EdgeCaseHandler()
        
        # Test normal distances
        distances = [300, 400, 500]
        result = handler.handle_extreme_distances(distances)
        assert result['warning_level'] == 'none'
        
        # Test extreme distances
        distances = [1000, 1100, 1200]
        result = handler.handle_extreme_distances(distances)
        assert result['warning_level'] == 'high'
        assert len(result['warnings']) > 0
    
    def test_validate_zero_negative_values(self):
        """Test validation of zero and negative values."""
        handler = EdgeCaseHandler()
        
        # Test valid config
        config = {
            'periods': 10,
            'cap_c130': 5,
            'speed_mach': 0.45
        }
        result = handler.validate_zero_negative_values(config)
        assert result['validation_passed'] is True
        
        # Test invalid config
        config = {
            'periods': 0,
            'cap_c130': -1,
            'speed_mach': -0.1
        }
        result = handler.validate_zero_negative_values(config)
        assert result['validation_passed'] is False
        assert len(result['invalid_fields']) == 3
    
    def test_stress_tester_initialization(self):
        """Test StressTester initialization."""
        edge_handler = EdgeCaseHandler()
        tester = StressTester(edge_handler)
        
        assert tester.edge_case_handler == edge_handler
        assert len(tester.test_results) == 0
        assert tester.current_test is None
    
    def test_stress_test_execution(self):
        """Test stress test execution."""
        edge_handler = EdgeCaseHandler()
        tester = StressTester(edge_handler)
        
        # Test maximum spoke count scenario
        result = tester.run_stress_test("Maximum Spoke Count")
        assert result.scenario_name == "Maximum Spoke Count"
        assert result.success is True  # Should pass validation
        assert result.test_duration > 0
    
    def test_stress_test_summary(self):
        """Test stress test summary generation."""
        edge_handler = EdgeCaseHandler()
        tester = StressTester(edge_handler)
        
        # Run a test first
        tester.run_stress_test("Maximum Spoke Count")
        
        # Get summary
        summary = tester.get_stress_test_summary()
        assert summary['total_tests'] == 1
        assert summary['successful_tests'] == 1
        assert summary['failed_tests'] == 0
        assert summary['success_rate'] == 1.0


class TestDataValidator:
    """Test the data validation and integrity module."""
    
    def test_data_validator_initialization(self):
        """Test DataValidator initialization."""
        validator = DataValidator()
        
        assert len(validator.validation_rules) == 3
        assert validator.validation_interval == 300.0
        assert len(validator.checksum_cache) == 0
    
    def test_validation_rules_structure(self):
        """Test validation rules structure."""
        validator = DataValidator()
        
        # Check aircraft config rules
        aircraft_rules = validator.validation_rules['aircraft_config']
        assert 'required_fields' in aircraft_rules
        assert 'field_types' in aircraft_rules
        assert aircraft_rules['nested_validation'] is True
        
        # Check simulation config rules
        sim_rules = validator.validation_rules['simulation_config']
        assert 'periods' in sim_rules['required_fields']
        assert 'spoke_distances' in sim_rules['required_fields']
    
    def test_version_compatibility_check(self):
        """Test version compatibility checking."""
        validator = DataValidator()
        
        # Test current version
        data = {'config_version': 9}
        compatible = validator._check_version_compatibility(data)
        assert compatible is True
        
        # Test backward compatibility
        data = {'config_version': 7}
        compatible = validator._check_version_compatibility(data)
        assert compatible is True
        
        # Test incompatible version
        data = {'config_version': 5}
        compatible = validator._check_version_compatibility(data)
        assert compatible is False
    
    def test_validation_summary(self):
        """Test validation summary generation."""
        validator = DataValidator()
        
        summary = validator.get_validation_summary()
        assert 'last_validation_time' in summary
        assert 'validation_interval' in summary
        assert 'cached_checksums' in summary
        assert 'validation_rules' in summary


class TestIntegration:
    """Integration tests for Phase 5 components."""
    
    def test_full_validation_pipeline(self):
        """Test the complete validation pipeline."""
        # Create validation components
        validator = DataValidator()
        edge_handler = EdgeCaseHandler()
        error_handler = ErrorHandler()
        optimizer = PerformanceOptimizer()
        
        # Test configuration validation
        config_data = {
            "speed_mach": 0.45,
            "spoke_distances": [300, 400, 500],
            "turnover_time_hours": 3.0,
            "cost_per_flight_hour": 15000.0
        }
        
        # Validate configuration
        validation_result = validate_config_comprehensive(config_data)
        assert validation_result.is_valid is True
        
        # Test edge case handling
        spoke_result = edge_handler.handle_large_spoke_count(8)
        assert spoke_result['warning_level'] == 'none'
        
        # Test performance optimization
        distance = optimizer.calculate_distance(0, 1, config_data['spoke_distances'])
        assert distance == 300.0
    
    def test_error_recovery_integration(self):
        """Test error recovery integration."""
        error_handler = ErrorHandler()
        degradation = GracefulDegradation(error_handler)
        
        # Simulate error
        context = {'function_name': 'test_function', 'module_name': 'test_module'}
        error = ValueError("Test error")
        
        # Handle error
        recovery_success = error_handler.handle_error(error, context)
        assert recovery_success is True
        
        # Check degradation
        assert degradation.current_level == 'full'
    
    def test_stress_testing_integration(self):
        """Test stress testing integration."""
        edge_handler = EdgeCaseHandler()
        tester = StressTester(edge_handler)
        
        # Run all stress tests
        results = tester.run_all_stress_tests()
        assert len(results) == 5  # All 5 scenarios
        
        # Check results
        for result in results:
            assert result.scenario_name in [s.name for s in edge_handler.edge_case_scenarios]
            assert result.test_duration > 0
            assert result.timestamp > 0


if __name__ == "__main__":
    pytest.main([__file__])
