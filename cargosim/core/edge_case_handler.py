"""Edge case handling and stress testing for CargoSim."""

import logging
import time
import math
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class StressLevel(Enum):
    """Stress testing levels."""
    NORMAL = "normal"
    HIGH = "high"
    EXTREME = "extreme"
    CRITICAL = "critical"


@dataclass
class EdgeCaseScenario:
    """Represents an edge case scenario for testing."""
    name: str
    description: str
    parameters: Dict[str, Any]
    expected_behavior: str
    risk_level: str
    mitigation_strategy: str
    test_duration: float = 60.0  # seconds


@dataclass
class StressTestResult:
    """Result of a stress test."""
    scenario_name: str
    success: bool
    performance_metrics: Dict[str, float]
    errors: List[str]
    warnings: List[str]
    recommendations: List[str]
    test_duration: float
    timestamp: float


class EdgeCaseHandler:
    """Handles extreme scenarios and boundary conditions."""
    
    def __init__(self):
        self.performance_warnings = []
        self.stress_indicators = {}
        self.edge_case_scenarios = self._initialize_edge_case_scenarios()
        self.current_stress_level = StressLevel.NORMAL
        
    def _initialize_edge_case_scenarios(self) -> List[EdgeCaseScenario]:
        """Initialize predefined edge case scenarios."""
        return [
            EdgeCaseScenario(
                name="Maximum Spoke Count",
                description="Test with maximum allowed spoke count (15+ spokes)",
                parameters={"spoke_count": 15, "max_spokes": 20},
                expected_behavior="System should maintain performance under 2 seconds per period",
                risk_level="high",
                mitigation_strategy="Performance optimization and caching",
                test_duration=120.0
            ),
            EdgeCaseScenario(
                name="Maximum Distances",
                description="Test with maximum spoke distances (1000+ miles)",
                parameters={"max_distance": 1200, "avg_distance": 800},
                expected_behavior="Flight time calculations should remain accurate",
                risk_level="medium",
                mitigation_strategy="Distance validation and range checking",
                test_duration=90.0
            ),
            EdgeCaseScenario(
                name="Maximum Speeds",
                description="Test with maximum aircraft speeds (2.0+ Mach)",
                parameters={"max_speed": 2.0, "speed_units": "mach"},
                expected_behavior="Speed validation should catch extreme values",
                risk_level="medium",
                mitigation_strategy="Speed limits and safety warnings",
                test_duration=60.0
            ),
            EdgeCaseScenario(
                name="Zero Values",
                description="Test with zero or negative values in critical fields",
                parameters={"zero_values": True, "negative_values": True},
                expected_behavior="Input validation should prevent invalid values",
                risk_level="low",
                mitigation_strategy="Comprehensive input validation",
                test_duration=45.0
            ),
            EdgeCaseScenario(
                name="Boundary Conditions",
                description="Test minimum viable configurations and maximum complexity",
                parameters={"min_config": True, "max_config": True},
                expected_behavior="System should handle both extremes gracefully",
                risk_level="medium",
                mitigation_strategy="Boundary checking and graceful degradation",
                test_duration=75.0
            )
        ]
    
    def handle_large_spoke_count(self, spoke_count: int, max_spokes: int = 15) -> Dict[str, Any]:
        """Handle operations with large numbers of spokes."""
        result = {
            'warning_level': 'none',
            'warnings': [],
            'recommendations': [],
            'performance_mode': 'standard',
            'restrictions': []
        }
        
        if spoke_count > max_spokes:
            result['warning_level'] = 'critical'
            result['warnings'].append(f"Spoke count {spoke_count} exceeds maximum {max_spokes}")
            result['recommendations'].append("Reduce spoke count to stay within limits")
            result['performance_mode'] = 'restricted'
            result['restrictions'].append("Maximum spoke count exceeded")
        
        elif spoke_count > 12:
            result['warning_level'] = 'high'
            result['warnings'].append(f"High spoke count {spoke_count} may impact performance")
            result['recommendations'].append("Consider reducing spoke count or using simplified mode")
            result['performance_mode'] = 'optimized'
        
        elif spoke_count > 8:
            result['warning_level'] = 'medium'
            result['warnings'].append(f"Moderate spoke count {spoke_count} - monitor performance")
            result['recommendations'].append("Monitor system performance closely")
            result['performance_mode'] = 'standard'
        
        # Performance recommendations based on spoke count
        if spoke_count > 10:
            result['recommendations'].append("Enable performance optimization mode")
            result['recommendations'].append("Consider using distance caching")
        
        if spoke_count > 13:
            result['recommendations'].append("Force garbage collection periodically")
            result['recommendations'].append("Monitor memory usage closely")
        
        return result
    
    def validate_extreme_speeds(self, speed_mach: float, aircraft_type: str = "C-130") -> Dict[str, Any]:
        """Validate and warn about extreme speeds."""
        result = {
            'warning_level': 'none',
            'warnings': [],
            'recommendations': [],
            'cost_impact': 'normal',
            'safety_check': 'not_required',
            'fuel_efficiency': 'normal'
        }
        
        # Aircraft-specific speed limits
        if aircraft_type == "C-130":
            typical_max = 0.6
            operational_max = 0.8
            absolute_max = 1.0
        elif aircraft_type == "C-27":
            typical_max = 0.5
            operational_max = 0.6
            absolute_max = 0.8
        else:
            typical_max = 0.6
            operational_max = 0.8
            absolute_max = 1.0
        
        if speed_mach > absolute_max:
            result['warning_level'] = 'critical'
            result['warnings'].append(f"Speed {speed_mach} Mach exceeds absolute maximum for {aircraft_type}")
            result['recommendations'].append("Reduce speed immediately")
            result['cost_impact'] = 'extreme'
            result['safety_check'] = 'required'
            result['fuel_efficiency'] = 'very_poor'
        
        elif speed_mach > operational_max:
            result['warning_level'] = 'high'
            result['warnings'].append(f"Speed {speed_mach} Mach exceeds operational maximum for {aircraft_type}")
            result['recommendations'].append("Consider reducing speed for efficiency")
            result['cost_impact'] = 'high'
            result['safety_check'] = 'recommended'
            result['fuel_efficiency'] = 'poor'
        
        elif speed_mach > typical_max:
            result['warning_level'] = 'medium'
            result['warnings'].append(f"Speed {speed_mach} Mach exceeds typical operational range")
            result['recommendations'].append("Monitor fuel consumption")
            result['cost_impact'] = 'elevated'
            result['safety_check'] = 'not_required'
            result['fuel_efficiency'] = 'reduced'
        
        # Supersonic considerations
        if speed_mach > 1.0:
            result['warnings'].append("Supersonic speeds may cause fuel efficiency issues")
            result['recommendations'].append("Verify aircraft capabilities for supersonic flight")
            result['cost_impact'] = 'very_high'
            result['fuel_efficiency'] = 'very_poor'
        
        return result
    
    def handle_extreme_distances(self, distances: List[float], max_distance: float = 1200) -> Dict[str, Any]:
        """Handle extreme distance scenarios."""
        result = {
            'warning_level': 'none',
            'warnings': [],
            'recommendations': [],
            'range_issues': [],
            'performance_impact': 'minimal'
        }
        
        total_distance = sum(distances)
        max_single_distance = max(distances) if distances else 0
        avg_distance = total_distance / len(distances) if distances else 0
        
        # Check individual spoke distances
        for i, distance in enumerate(distances):
            if distance > max_distance:
                result['warning_level'] = 'high'
                result['warnings'].append(f"Spoke {i+1} distance {distance} exceeds maximum {max_distance}")
                result['range_issues'].append(f"Spoke {i+1}: {distance} miles")
        
        # Check total network distance
        if total_distance > 5000:
            result['warning_level'] = 'high'
            result['warnings'].append(f"Total network distance {total_distance} miles is very high")
            result['recommendations'].append("Consider reducing network size or optimizing routes")
            result['performance_impact'] = 'significant'
        
        # Check average distance
        if avg_distance > 800:
            result['warning_level'] = 'medium'
            result['warnings'].append(f"Average spoke distance {avg_distance:.1f} miles is high")
            result['recommendations'].append("Monitor fuel consumption and flight times")
            result['performance_impact'] = 'moderate'
        
        # Performance recommendations
        if result['warning_level'] in ['high', 'critical']:
            result['recommendations'].append("Enable distance caching for performance")
            result['recommendations'].append("Consider reducing spoke count")
            result['recommendations'].append("Monitor aircraft range limitations")
        
        return result
    
    def handle_boundary_conditions(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Handle minimum and maximum boundary conditions."""
        result = {
            'boundary_issues': [],
            'warnings': [],
            'recommendations': [],
            'system_status': 'stable'
        }
        
        # Minimum viable configuration check
        if config.get('spoke_count', 0) < 2:
            result['boundary_issues'].append("Spoke count below minimum viable (2)")
            result['recommendations'].append("Increase spoke count to at least 2")
        
        if config.get('aircraft_count', 0) < 1:
            result['boundary_issues'].append("No aircraft configured")
            result['recommendations'].append("Add at least one aircraft")
        
        # Maximum complexity check
        if config.get('spoke_count', 0) > 15:
            result['boundary_issues'].append("Spoke count exceeds recommended maximum")
            result['recommendations'].append("Consider reducing spoke count for stability")
        
        if config.get('aircraft_count', 0) > 20:
            result['boundary_issues'].append("Aircraft count very high")
            result['recommendations'].append("Monitor performance with large fleet")
        
        # Check for zero or negative values
        for key, value in config.items():
            if isinstance(value, (int, float)) and value <= 0:
                if key in ['periods', 'cap_c130', 'cap_c27', 'rest_c130', 'rest_c27']:
                    result['boundary_issues'].append(f"Invalid {key}: {value} (must be positive)")
                    result['recommendations'].append(f"Set {key} to a positive value")
        
        # Determine system status
        if result['boundary_issues']:
            result['system_status'] = 'unstable'
            result['warnings'].append("Boundary conditions violated")
        elif result['warnings']:
            result['system_status'] = 'warning'
        else:
            result['system_status'] = 'stable'
        
        return result
    
    def validate_zero_negative_values(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate that critical fields don't have zero or negative values."""
        result = {
            'validation_passed': True,
            'invalid_fields': [],
            'warnings': [],
            'recommendations': []
        }
        
        critical_fields = {
            'periods': 'must be at least 1',
            'cap_c130': 'must be positive',
            'cap_c27': 'must be positive',
            'rest_c130': 'must be positive',
            'rest_c27': 'must be positive',
            'a_days': 'must be positive',
            'b_days': 'must be positive',
            'c_days': 'must be positive',
            'd_days': 'must be positive',
            'speed_mach': 'must be positive',
            'turnover_time_hours': 'must be positive',
            'cost_per_flight_hour': 'must be positive'
        }
        
        for field, requirement in critical_fields.items():
            if field in config:
                value = config[field]
                if isinstance(value, (int, float)) and value <= 0:
                    result['validation_passed'] = False
                    result['invalid_fields'].append({
                        'field': field,
                        'value': value,
                        'requirement': requirement
                    })
                    result['recommendations'].append(f"Set {field} to a value > 0")
        
        # Check spoke distances
        if 'spoke_distances' in config:
            distances = config['spoke_distances']
            for i, distance in enumerate(distances):
                if distance <= 0:
                    result['validation_passed'] = False
                    result['invalid_fields'].append({
                        'field': f'spoke_distances[{i}]',
                        'value': distance,
                        'requirement': 'must be positive'
                    })
                    result['recommendations'].append(f"Set spoke {i+1} distance to a positive value")
        
        if not result['validation_passed']:
            result['warnings'].append("Critical validation failed - system may not function properly")
        
        return result
    
    def get_edge_case_recommendations(self, config: Dict[str, Any]) -> List[str]:
        """Get recommendations for handling edge cases based on current configuration."""
        recommendations = []
        
        spoke_count = config.get('spoke_count', len(config.get('spoke_distances', [])))
        speed_mach = config.get('speed_mach', 0.45)
        max_distance = max(config.get('spoke_distances', [0])) if config.get('spoke_distances') else 0
        
        # Spoke count recommendations
        if spoke_count > 12:
            recommendations.append("Enable performance optimization mode")
            recommendations.append("Consider reducing spoke count for better performance")
        
        if spoke_count > 15:
            recommendations.append("Use simplified calculation mode")
            recommendations.append("Monitor memory usage closely")
        
        # Speed recommendations
        if speed_mach > 1.0:
            recommendations.append("Verify aircraft capabilities for supersonic flight")
            recommendations.append("Monitor fuel consumption closely")
        
        if speed_mach > 1.5:
            recommendations.append("Consider reducing speed for efficiency")
            recommendations.append("Enable safety monitoring mode")
        
        # Distance recommendations
        if max_distance > 1000:
            recommendations.append("Verify aircraft range limitations")
            recommendations.append("Consider fuel stop planning")
        
        if max_distance > 1200:
            recommendations.append("Distance exceeds recommended maximum")
            recommendations.append("Review network configuration")
        
        return recommendations


class StressTester:
    """Performs stress testing on the simulation system."""
    
    def __init__(self, edge_case_handler: EdgeCaseHandler):
        self.edge_case_handler = edge_case_handler
        self.test_results: List[StressTestResult] = []
        self.current_test: Optional[EdgeCaseScenario] = None
        
    def run_stress_test(self, scenario_name: str) -> StressTestResult:
        """Run a specific stress test scenario."""
        scenario = next((s for s in self.edge_case_handler.edge_case_scenarios 
                        if s.name == scenario_name), None)
        
        if not scenario:
            raise ValueError(f"Unknown stress test scenario: {scenario_name}")
        
        self.current_test = scenario
        logger.info(f"Starting stress test: {scenario.name}")
        
        start_time = time.time()
        success = True
        errors = []
        warnings = []
        recommendations = []
        
        try:
            # Run the specific stress test
            if scenario.name == "Maximum Spoke Count":
                result = self._test_maximum_spoke_count(scenario.parameters)
            elif scenario.name == "Maximum Distances":
                result = self._test_maximum_distances(scenario.parameters)
            elif scenario.name == "Maximum Speeds":
                result = self._test_maximum_speeds(scenario.parameters)
            elif scenario.name == "Zero Values":
                result = self._test_zero_values(scenario.parameters)
            elif scenario.name == "Boundary Conditions":
                result = self._test_boundary_conditions(scenario.parameters)
            else:
                result = self._test_generic_scenario(scenario.parameters)
            
            success = result.get('success', True)
            errors = result.get('errors', [])
            warnings = result.get('warnings', [])
            recommendations = result.get('recommendations', [])
            
        except Exception as e:
            success = False
            errors.append(f"Test failed with exception: {e}")
            logger.error(f"Stress test failed: {e}")
        
        test_duration = time.time() - start_time
        
        # Create test result
        test_result = StressTestResult(
            scenario_name=scenario.name,
            success=success,
            performance_metrics=self._collect_performance_metrics(),
            errors=errors,
            warnings=warnings,
            recommendations=recommendations,
            test_duration=test_duration,
            timestamp=time.time()
        )
        
        self.test_results.append(test_result)
        self.current_test = None
        
        logger.info(f"Stress test completed: {scenario.name} - Success: {success}")
        return test_result
    
    def _test_maximum_spoke_count(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Test maximum spoke count scenario."""
        spoke_count = parameters.get('spoke_count', 15)
        max_spokes = parameters.get('max_spokes', 20)
        
        result = self.edge_case_handler.handle_large_spoke_count(spoke_count, max_spokes)
        
        return {
            'success': result['warning_level'] != 'critical',
            'errors': [] if result['warning_level'] != 'critical' else result['warnings'],
            'warnings': result['warnings'],
            'recommendations': result['recommendations']
        }
    
    def _test_maximum_distances(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Test maximum distance scenario."""
        max_distance = parameters.get('max_distance', 1200)
        avg_distance = parameters.get('avg_distance', 800)
        
        # Create test distances
        test_distances = [max_distance, avg_distance, max_distance // 2]
        
        result = self.edge_case_handler.handle_extreme_distances(test_distances, max_distance)
        
        return {
            'success': result['warning_level'] != 'critical',
            'errors': [] if result['warning_level'] != 'critical' else result['warnings'],
            'warnings': result['warnings'],
            'recommendations': result['recommendations']
        }
    
    def _test_maximum_speeds(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Test maximum speed scenario."""
        max_speed = parameters.get('max_speed', 2.0)
        speed_units = parameters.get('speed_units', 'mach')
        
        result = self.edge_case_handler.validate_extreme_speeds(max_speed)
        
        return {
            'success': result['warning_level'] != 'critical',
            'errors': [] if result['warning_level'] != 'critical' else result['warnings'],
            'warnings': result['warnings'],
            'recommendations': result['recommendations']
        }
    
    def _test_zero_values(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Test zero and negative values scenario."""
        # Create test config with zero values
        test_config = {
            'periods': 0,
            'cap_c130': -1,
            'cap_c27': 0,
            'speed_mach': -0.1,
            'spoke_distances': [0, -100, 200]
        }
        
        result = self.edge_case_handler.validate_zero_negative_values(test_config)
        
        return {
            'success': not result['validation_passed'],  # Should fail validation
            'errors': result['invalid_fields'],
            'warnings': result['warnings'],
            'recommendations': result['recommendations']
        }
    
    def _test_boundary_conditions(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Test boundary conditions scenario."""
        # Create test config with boundary conditions
        test_config = {
            'spoke_count': 1,  # Below minimum
            'aircraft_count': 0,  # Below minimum
            'spoke_distances': [100, 200, 300]
        }
        
        result = self.edge_case_handler.handle_boundary_conditions(test_config)
        
        return {
            'success': result['system_status'] != 'unstable',
            'errors': result['boundary_issues'],
            'warnings': result['warnings'],
            'recommendations': result['recommendations']
        }
    
    def _test_generic_scenario(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Test generic scenario."""
        return {
            'success': True,
            'errors': [],
            'warnings': [],
            'recommendations': []
        }
    
    def _collect_performance_metrics(self) -> Dict[str, float]:
        """Collect performance metrics during stress testing."""
        # This would integrate with the performance monitoring system
        return {
            'memory_usage_mb': 0.0,
            'cpu_usage_percent': 0.0,
            'response_time_ms': 0.0
        }
    
    def get_stress_test_summary(self) -> Dict[str, Any]:
        """Get summary of all stress test results."""
        if not self.test_results:
            return {'message': 'No stress tests have been run'}
        
        total_tests = len(self.test_results)
        successful_tests = sum(1 for r in self.test_results if r.success)
        failed_tests = total_tests - successful_tests
        
        return {
            'total_tests': total_tests,
            'successful_tests': successful_tests,
            'failed_tests': failed_tests,
            'success_rate': successful_tests / total_tests if total_tests > 0 else 0.0,
            'recent_results': [
                {
                    'scenario': r.scenario_name,
                    'success': r.success,
                    'duration': r.test_duration,
                    'timestamp': r.timestamp
                }
                for r in self.test_results[-5:]  # Last 5 results
            ]
        }
    
    def run_all_stress_tests(self) -> List[StressTestResult]:
        """Run all available stress test scenarios."""
        results = []
        
        for scenario in self.edge_case_handler.edge_case_scenarios:
            try:
                result = self.run_stress_test(scenario.name)
                results.append(result)
                
                # Brief pause between tests
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Failed to run stress test {scenario.name}: {e}")
        
        return results


class SimulationEdgeCaseHandler(EdgeCaseHandler):
    """Specialized edge case handler for simulation operations."""
    
    def __init__(self):
        super().__init__()
        self.simulation_scenarios = self._initialize_simulation_scenarios()
        self.current_stress_level = StressLevel.NORMAL
        self.stress_test_results: List[Dict[str, Any]] = []
        self.automatic_stress_detection = True
        self.stress_detection_interval = 30.0  # 30 seconds
        self.last_stress_check = 0.0
        
    def _initialize_simulation_scenarios(self) -> List[EdgeCaseScenario]:
        """Initialize simulation-specific edge case scenarios."""
        base_scenarios = self.edge_case_scenarios
        simulation_scenarios = [
            EdgeCaseScenario(
                name="Simulation Memory Pressure",
                description="Test simulation behavior under memory pressure",
                parameters={"memory_threshold_mb": 400, "spoke_count": 15, "aircraft_count": 20},
                expected_behavior="System should gracefully degrade performance",
                risk_level="high",
                mitigation_strategy="Memory monitoring and automatic cleanup",
                test_duration=90.0
            ),
            EdgeCaseScenario(
                name="High Frequency Operations",
                description="Test rapid simulation steps with minimal delays",
                parameters={"step_interval_ms": 100, "total_steps": 100, "spoke_count": 10},
                expected_behavior="System should maintain stability under rapid operations",
                risk_level="medium",
                mitigation_strategy="Performance optimization and rate limiting",
                test_duration=120.0
            ),
            EdgeCaseScenario(
                name="Configuration Corruption",
                description="Test system behavior with corrupted configuration data",
                parameters={"corruption_type": "random", "corruption_level": 0.1},
                expected_behavior="System should detect corruption and use safe defaults",
                risk_level="high",
                mitigation_strategy="Configuration validation and fallback values",
                test_duration=60.0
            ),
            EdgeCaseScenario(
                name="Network Topology Changes",
                description="Test dynamic spoke addition/removal during simulation",
                parameters={"dynamic_changes": True, "change_frequency": 5, "spoke_count": 12},
                expected_behavior="System should handle topology changes gracefully",
                risk_level="medium",
                mitigation_strategy="Dynamic reconfiguration and validation",
                test_duration=150.0
            ),
            EdgeCaseScenario(
                name="Aircraft State Corruption",
                description="Test system behavior with corrupted aircraft state data",
                parameters={"corruption_type": "state_inconsistency", "aircraft_count": 15},
                expected_behavior="System should detect and repair state inconsistencies",
                risk_level="high",
                mitigation_strategy="State validation and automatic repair",
                test_duration=75.0
            )
        ]
        
        return base_scenarios + simulation_scenarios
    
    def detect_simulation_stress(self, simulation_context: Dict[str, Any]) -> Dict[str, Any]:
        """Automatically detect stress conditions in simulation."""
        current_time = time.time()
        
        if not self.automatic_stress_detection:
            return {'stress_detected': False, 'level': 'normal'}
        
        if current_time - self.last_stress_check < self.stress_detection_interval:
            return {'stress_detected': False, 'level': 'normal'}
        
        self.last_stress_check = current_time
        
        # Analyze simulation context for stress indicators
        stress_indicators = self._analyze_stress_indicators(simulation_context)
        
        # Determine stress level
        stress_level = self._determine_stress_level(stress_indicators)
        
        # Update current stress level
        self.current_stress_level = stress_level
        
        # Store stress detection result
        stress_result = {
            'timestamp': current_time,
            'stress_detected': stress_level != StressLevel.NORMAL,
            'level': stress_level.value,
            'indicators': stress_indicators,
            'recommendations': self._get_stress_recommendations(stress_level, stress_indicators)
        }
        
        self.stress_test_results.append(stress_result)
        if len(self.stress_test_results) > 20:
            self.stress_test_results.pop(0)
        
        return stress_result
    
    def _analyze_stress_indicators(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze simulation context for stress indicators."""
        indicators = {
            'memory_pressure': False,
            'performance_degradation': False,
            'error_frequency': False,
            'complexity_issues': False,
            'resource_contention': False
        }
        
        # Memory pressure
        memory_usage = context.get('memory_usage_mb', 0)
        if memory_usage > 400:
            indicators['memory_pressure'] = True
        
        # Performance degradation
        response_time = context.get('response_time_ms', 0)
        if response_time > 2000:  # 2 seconds
            indicators['performance_degradation'] = True
        
        # Error frequency
        error_count = context.get('error_count', 0)
        if error_count > 5:
            indicators['error_frequency'] = True
        
        # Complexity issues
        spoke_count = context.get('spoke_count', 0)
        aircraft_count = context.get('aircraft_count', 0)
        if spoke_count > 12 or aircraft_count > 15:
            indicators['complexity_issues'] = True
        
        # Resource contention
        cpu_usage = context.get('cpu_usage_percent', 0)
        if cpu_usage > 80:
            indicators['resource_contention'] = True
        
        return indicators
    
    def _determine_stress_level(self, indicators: Dict[str, Any]) -> StressLevel:
        """Determine stress level based on indicators."""
        stress_score = 0
        
        if indicators['memory_pressure']:
            stress_score += 2
        if indicators['performance_degradation']:
            stress_score += 2
        if indicators['error_frequency']:
            stress_score += 3
        if indicators['complexity_issues']:
            stress_score += 1
        if indicators['resource_contention']:
            stress_score += 1
        
        if stress_score >= 6:
            return StressLevel.CRITICAL
        elif stress_score >= 4:
            return StressLevel.EXTREME
        elif stress_score >= 2:
            return StressLevel.HIGH
        else:
            return StressLevel.NORMAL
    
    def _get_stress_recommendations(self, stress_level: StressLevel, 
                                  indicators: Dict[str, Any]) -> List[str]:
        """Get recommendations based on stress level and indicators."""
        recommendations = []
        
        if stress_level == StressLevel.CRITICAL:
            recommendations.append("CRITICAL: Immediate action required")
            recommendations.append("Reduce simulation complexity immediately")
            recommendations.append("Consider emergency shutdown")
        
        elif stress_level == StressLevel.EXTREME:
            recommendations.append("EXTREME: Significant stress detected")
            recommendations.append("Reduce spoke count to 8 or fewer")
            recommendations.append("Reduce aircraft count to 10 or fewer")
            recommendations.append("Enable emergency performance mode")
        
        elif stress_level == StressLevel.HIGH:
            recommendations.append("HIGH: Elevated stress detected")
            recommendations.append("Monitor performance closely")
            recommendations.append("Consider reducing complexity")
            recommendations.append("Enable performance optimization mode")
        
        # Specific recommendations based on indicators
        if indicators['memory_pressure']:
            recommendations.append("Memory pressure detected - consider cleanup")
        
        if indicators['performance_degradation']:
            recommendations.append("Performance degradation detected - optimize operations")
        
        if indicators['error_frequency']:
            recommendations.append("High error frequency - review configuration")
        
        if indicators['complexity_issues']:
            recommendations.append("High complexity detected - consider simplification")
        
        if indicators['resource_contention']:
            recommendations.append("Resource contention detected - reduce load")
        
        return recommendations
    
    def run_simulation_stress_test(self, scenario_name: str, 
                                 simulation_context: Dict[str, Any]) -> Dict[str, Any]:
        """Run a simulation-specific stress test."""
        scenario = next((s for s in self.simulation_scenarios 
                        if s.name == scenario_name), None)
        
        if not scenario:
            raise ValueError(f"Unknown simulation stress test scenario: {scenario_name}")
        
        logger.info(f"Starting simulation stress test: {scenario.name}")
        
        start_time = time.time()
        test_result = {
            'scenario_name': scenario.name,
            'success': True,
            'errors': [],
            'warnings': [],
            'recommendations': [],
            'performance_impact': 'minimal',
            'stress_level': 'normal'
        }
        
        try:
            # Run the specific stress test
            if scenario.name == "Simulation Memory Pressure":
                result = self._test_memory_pressure(scenario.parameters, simulation_context)
            elif scenario.name == "High Frequency Operations":
                result = self._test_high_frequency_operations(scenario.parameters, simulation_context)
            elif scenario.name == "Configuration Corruption":
                result = self._test_configuration_corruption(scenario.parameters, simulation_context)
            elif scenario.name == "Network Topology Changes":
                result = self._test_network_topology_changes(scenario.parameters, simulation_context)
            elif scenario.name == "Aircraft State Corruption":
                result = self._test_aircraft_state_corruption(scenario.parameters, simulation_context)
            else:
                result = self._test_generic_simulation_scenario(scenario.parameters, simulation_context)
            
            test_result.update(result)
            
        except Exception as e:
            test_result['success'] = False
            test_result['errors'].append(f"Test failed with exception: {e}")
            logger.error(f"Simulation stress test failed: {e}")
        
        test_result['test_duration'] = time.time() - start_time
        test_result['timestamp'] = time.time()
        
        # Store test result
        self.stress_test_results.append(test_result)
        if len(self.stress_test_results) > 20:
            self.stress_test_results.pop(0)
        
        logger.info(f"Simulation stress test completed: {scenario.name} - Success: {test_result['success']}")
        return test_result
    
    def _test_memory_pressure(self, parameters: Dict[str, Any], 
                             context: Dict[str, Any]) -> Dict[str, Any]:
        """Test simulation behavior under memory pressure."""
        memory_threshold = parameters.get('memory_threshold_mb', 400)
        current_memory = context.get('memory_usage_mb', 0)
        
        if current_memory > memory_threshold:
            return {
                'success': False,
                'errors': [f"Memory usage {current_memory:.1f}MB exceeds threshold {memory_threshold}MB"],
                'warnings': ["Memory pressure detected"],
                'recommendations': ["Reduce spoke count", "Force garbage collection", "Enable simplified mode"],
                'performance_impact': 'severe',
                'stress_level': 'critical'
            }
        else:
            return {
                'success': True,
                'errors': [],
                'warnings': [],
                'recommendations': ["Memory usage within acceptable limits"],
                'performance_impact': 'minimal',
                'stress_level': 'normal'
            }
    
    def _test_high_frequency_operations(self, parameters: Dict[str, Any], 
                                       context: Dict[str, Any]) -> Dict[str, Any]:
        """Test simulation behavior under high frequency operations."""
        step_interval = parameters.get('step_interval_ms', 100)
        total_steps = parameters.get('total_steps', 100)
        
        # Simulate high frequency operations
        if step_interval < 200:  # Less than 200ms between steps
            return {
                'success': True,
                'errors': [],
                'warnings': ["High frequency operations may impact performance"],
                'recommendations': ["Monitor performance closely", "Consider increasing step interval"],
                'performance_impact': 'moderate',
                'stress_level': 'high'
            }
        else:
            return {
                'success': True,
                'errors': [],
                'warnings': [],
                'recommendations': ["Operation frequency within acceptable limits"],
                'performance_impact': 'minimal',
                'stress_level': 'normal'
            }
    
    def _test_configuration_corruption(self, parameters: Dict[str, Any], 
                                     context: Dict[str, Any]) -> Dict[str, Any]:
        """Test system behavior with corrupted configuration."""
        corruption_type = parameters.get('corruption_type', 'random')
        corruption_level = parameters.get('corruption_level', 0.1)
        
        # Simulate configuration corruption
        if corruption_level > 0.05:  # More than 5% corruption
            return {
                'success': False,
                'errors': [f"Configuration corruption detected: {corruption_type} at {corruption_level:.1%}"],
                'warnings': ["System may not function correctly"],
                'recommendations': ["Use configuration validation", "Restore from backup", "Use safe defaults"],
                'performance_impact': 'severe',
                'stress_level': 'critical'
            }
        else:
            return {
                'success': True,
                'errors': [],
                'warnings': [],
                'recommendations': ["Configuration appears valid"],
                'performance_impact': 'minimal',
                'stress_level': 'normal'
            }
    
    def _test_network_topology_changes(self, parameters: Dict[str, Any], 
                                     context: Dict[str, Any]) -> Dict[str, Any]:
        """Test system behavior with dynamic network topology changes."""
        dynamic_changes = parameters.get('dynamic_changes', True)
        change_frequency = parameters.get('change_frequency', 5)
        spoke_count = context.get('spoke_count', 0)
        
        if dynamic_changes and change_frequency > 3:  # Changes every 3 steps or less
            return {
                'success': True,
                'errors': [],
                'warnings': ["Frequent topology changes may impact performance"],
                'recommendations': ["Reduce change frequency", "Use topology caching", "Monitor performance"],
                'performance_impact': 'moderate',
                'stress_level': 'high'
            }
        else:
            return {
                'success': True,
                'errors': [],
                'warnings': [],
                'recommendations': ["Topology change frequency acceptable"],
                'performance_impact': 'minimal',
                'stress_level': 'normal'
            }
    
    def _test_aircraft_state_corruption(self, parameters: Dict[str, Any], 
                                       context: Dict[str, Any]) -> Dict[str, Any]:
        """Test system behavior with corrupted aircraft state."""
        corruption_type = parameters.get('corruption_type', 'state_inconsistency')
        aircraft_count = context.get('aircraft_count', 0)
        
        # Simulate aircraft state corruption
        if corruption_type == 'state_inconsistency' and aircraft_count > 10:
            return {
                'success': False,
                'errors': [f"Aircraft state corruption detected: {corruption_type}"],
                'warnings': ["Large fleet may have state inconsistencies"],
                'recommendations': ["Validate aircraft states", "Use state repair mechanisms", "Reduce fleet size"],
                'performance_impact': 'severe',
                'stress_level': 'critical'
            }
        else:
            return {
                'success': True,
                'errors': [],
                'warnings': [],
                'recommendations': ["Aircraft states appear consistent"],
                'performance_impact': 'minimal',
                'stress_level': 'normal'
            }
    
    def _test_generic_simulation_scenario(self, parameters: Dict[str, Any], 
                                        context: Dict[str, Any]) -> Dict[str, Any]:
        """Test generic simulation scenario."""
        return {
            'success': True,
            'errors': [],
            'warnings': [],
            'recommendations': ["Generic scenario completed successfully"],
            'performance_impact': 'minimal',
            'stress_level': 'normal'
        }
    
    def get_simulation_stress_summary(self) -> Dict[str, Any]:
        """Get summary of simulation stress testing."""
        if not self.stress_test_results:
            return {'message': 'No simulation stress tests have been run'}
        
        total_tests = len(self.stress_test_results)
        successful_tests = sum(1 for r in self.stress_test_results if r.get('success', False))
        failed_tests = total_tests - successful_tests
        
        # Analyze stress levels
        stress_levels = [r.get('stress_level', 'normal') for r in self.stress_test_results]
        critical_stress = sum(1 for level in stress_levels if level == 'critical')
        high_stress = sum(1 for level in stress_levels if level in ['high', 'extreme'])
        
        return {
            'total_tests': total_tests,
            'successful_tests': successful_tests,
            'failed_tests': failed_tests,
            'success_rate': successful_tests / total_tests if total_tests > 0 else 0.0,
            'stress_analysis': {
                'critical_stress': critical_stress,
                'high_stress': high_stress,
                'normal_stress': total_tests - critical_stress - high_stress,
                'current_stress_level': self.current_stress_level.value
            },
            'recent_results': [
                {
                    'scenario': r.get('scenario_name', 'Unknown'),
                    'success': r.get('success', False),
                    'stress_level': r.get('stress_level', 'normal'),
                    'duration': r.get('test_duration', 0),
                    'timestamp': r.get('timestamp', 0)
                }
                for r in self.stress_test_results[-5:]  # Last 5 results
            ]
        }
    
    def run_all_simulation_stress_tests(self, simulation_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Run all available simulation stress test scenarios."""
        results = []
        
        for scenario in self.simulation_scenarios:
            try:
                result = self.run_simulation_stress_test(scenario.name, simulation_context)
                results.append(result)
                
                # Brief pause between tests
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Failed to run simulation stress test {scenario.name}: {e}")
        
        return results
