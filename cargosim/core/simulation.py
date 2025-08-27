"""Core simulation logic for CargoSim."""

import copy
import math
import random
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import List, Tuple, Optional

from .config import M, PAIR_ORDER_DEFAULT, A_PERIOD_DAYS_DFLT, B_PERIOD_DAYS_DFLT, C_PERIOD_DAYS_DFLT, D_PERIOD_DAYS_DFLT, DEFAULT_BAR_SCALE_DENOMINATORS
from .config import SimConfig
from ..features.smart_targeting import SmartTargeting, TargetingConfig
from ..ui.fleet_builder import FleetComposition


def _row_to_spoke(row: List[float]) -> SimpleNamespace:
    return SimpleNamespace(A=row[0], B=row[1], C=row[2], D=row[3])


def is_ops_capable(spoke, eps=1e-9) -> bool:
    # Must reflect ONLY inventory available **now**, not in-flight or next-period arrivals.
    return (spoke.A > eps and spoke.B > eps and spoke.C > eps and spoke.D > eps)


@dataclass
class Aircraft:
    typ: str           # "C-130" or "C-27"
    cap: int           # capacity
    name: str
    location: str = "HUB"  # "HUB" or "S{1..10}"
    state: str = "IDLE"    # IDLE, LEG1_ENROUTE, AT_SPOKEA, AT_SPOKEB_ENROUTE, AT_SPOKEB, RETURN_ENROUTE
    plan: Optional[Tuple[int, Optional[int]]] = None  # (i, j|None)
    payload_A: List[int] = field(default_factory=lambda: [0,0,0,0])
    payload_B: List[int] = field(default_factory=lambda: [0,0,0,0])
    active_periods: int = 0
    rest_cooldown: int = 0
    
    # New time and distance mechanics attributes
    speed_mach: float = 0.45  # Default speed in Mach (0.45 for C-130, 0.35 for C-27)
    turnover_time_hours: float = 2.0  # Base turnover time in hours
    current_flight_time: float = 0.0  # Accumulated flight time for current mission
    total_flight_hours: float = 0.0   # Total flight hours for cost calculation
    fuel_consumption_rate: float = 1.0  # Fuel consumption rate multiplier
    
    # Time-based state machine attributes
    time_remaining: float = 0.0  # Remaining time for current state (ENROUTE, LOADING, MAINTENANCE)
    loading_time_remaining: float = 0.0  # Remaining loading/unloading time
    maintenance_time_remaining: float = 0.0  # Remaining maintenance time

    def max_active_before_rest(self, cfg: SimConfig) -> int:
        return cfg.rest_c130 if self.typ == "C-130" else cfg.rest_c27

    def at_hub(self) -> bool:
        return self.location == "HUB"
    
    def calculate_turnover_time(self) -> float:
        """Calculate turnover time based on cargo capacity."""
        return self.turnover_time_hours * (self.cap / 2.0)  # 1/2 hour per cargo
    
    def update_flight_time(self, elapsed_hours: float) -> None:
        """Update current and total flight time."""
        self.current_flight_time += elapsed_hours
        self.total_flight_hours += elapsed_hours
    
    def reset_current_flight_time(self) -> None:
        """Reset current flight time after mission completion."""
        self.current_flight_time = 0.0

    def set_enroute_state(self, flight_time_hours: float) -> None:
        """Set aircraft to ENROUTE state with specified flight time.
        
        Args:
            flight_time_hours: Total flight time for this leg in hours
        """
        self.state = "ENROUTE"
        self.time_remaining = flight_time_hours
    
    def set_loading_state(self, loading_time_hours: float) -> None:
        """Set aircraft to LOADING state with specified loading time.
        
        Args:
            loading_time_hours: Time required for loading/unloading in hours
        """
        self.state = "LOADING"
        self.loading_time_remaining = loading_time_hours
    
    def set_maintenance_state(self, maintenance_time_hours: float) -> None:
        """Set aircraft to MAINTENANCE state with specified maintenance time.
        
        Args:
            maintenance_time_hours: Time required for maintenance in hours
        """
        self.state = "MAINTENANCE"
        self.maintenance_time_remaining = maintenance_time_hours
    
    def is_time_based_state(self) -> bool:
        """Check if aircraft is in a time-based state."""
        return self.state in ["ENROUTE", "LOADING", "MAINTENANCE"]
    
    def update_time_remaining(self, delta_hours: float) -> bool:
        """Update remaining time for current state.
        
        Args:
            delta_hours: Time increment in hours
            
        Returns:
            True if state transition should occur, False otherwise
        """
        if self.state == "ENROUTE":
            self.time_remaining = max(0.0, self.time_remaining - delta_hours)
            return self.time_remaining <= 0.0
        elif self.state == "LOADING":
            self.loading_time_remaining = max(0.0, self.loading_time_remaining - delta_hours)
            return self.loading_time_remaining <= 0.0
        elif self.state == "MAINTENANCE":
            self.maintenance_time_remaining = max(0.0, self.maintenance_time_remaining - delta_hours)
            return self.maintenance_time_remaining <= 0.0
        
        return False


class LogisticsSim:
    def __init__(self, cfg: SimConfig):
        self.cfg = cfg
        self.M = M
        self.PAIR_ORDER = list(cfg.pair_order)
        self.A_PERIOD_DAYS = cfg.a_days
        self.B_PERIOD_DAYS = cfg.b_days
        self.C_PERIOD_DAYS = cfg.c_days
        self.D_PERIOD_DAYS = cfg.d_days
        # Use configurable bar scale denominators instead of hardcoded VIS_CAPS
        self.bar_scale = cfg.bar_scale

        # Initialize smart targeting system if enabled
        self.smart_targeting = None
        if cfg.smart_targeting_enabled:
            targeting_config = TargetingConfig()
            if cfg.smart_targeting_config:
                # Apply custom config if provided
                for key, value in cfg.smart_targeting_config.items():
                    if hasattr(targeting_config, key):
                        setattr(targeting_config, key, value)
            self.smart_targeting = SmartTargeting(targeting_config)
        
        # Force enable smart targeting for better aircraft distribution
        if self.smart_targeting is None:
            targeting_config = TargetingConfig()
            self.smart_targeting = SmartTargeting(targeting_config)

        # Initialize special capability effects tracking
        self.special_capability_effects = {}

        self.reset_world()

    def reset_world(self):
        self.t = 0  # current period
        self.day = 0
        self.half = "AM"  # AM for even t, PM for odd t
        
        # Time-based movement system
        self.current_time_hours: float = 0.0  # Current simulation time in hours
        
        # Cost tracking system
        self.total_operational_cost: float = 0.0
        self.total_fuel_cost: float = 0.0
        self.total_maintenance_cost: float = 0.0
        self.cost_history: List[dict] = []  # Cost history for analysis
        
        self.stock = [[self.cfg.init_A, self.cfg.init_B, self.cfg.init_C, self.cfg.init_D] for _ in range(self.M)]
        # Initialize operational flags based on initial stock levels
        self.op = [is_ops_capable(_row_to_spoke(stock_row)) for stock_row in self.stock]
        self.arrivals_next = [[] for _ in range(self.M)]
        self.pair_cursor = 0
        self.fleet = self.build_fleet(self.cfg.fleet_label)
        self.actions_log: List[List[Tuple[str,str]]] = []

        # Stats
        self.ops_by_spoke = [0]*self.M  # counts of OFFLOAD occurrences per spoke
        self.ops_total_history = [0]
        self.integrity_violations: List[str] = []
        self._integrity_logged = False

        # History for rewind
        self.history: List[dict] = []
        self.push_snapshot()  # store initial state (period 0 before any action)
        
        # Initialize smart targeting positions if available
        if self.smart_targeting:
            self._initialize_targeting_positions()
            self.smart_targeting.reset_recent_service()

        # Initialize distance cache for performance optimization
        self._initialize_distance_cache()
        
        # Phase 8: Advanced Simulation Features
        self.advanced_routing_enabled = True
        self.multi_objective_optimization = True
        self.predictive_analytics_enabled = True
        self.weather_considerations = False
        self.traffic_management = False
        
        # Advanced cost modeling
        self.fuel_price_volatility = 0.1  # 10% volatility
        self.fuel_price_trend = 0.0  # Price trend per period
        self.maintenance_scheduling_enabled = True
        self.predictive_maintenance_threshold = 0.8
        
        # Performance monitoring
        self.performance_metrics = {
            'operations_per_second': 0.0,
            'efficiency_ratio': 0.0,
            'resource_utilization': 0.0,
            'cost_per_operation': 0.0,
            'route_optimization_score': 0.0
        }
        
        # Route optimization cache
        self.route_cache = {}
        self.optimization_history = []

    def can_run_op(self, s: int) -> bool:
        return is_ops_capable(_row_to_spoke(self.stock[s]))

    def run_op(self, s: int, amount: int = 1) -> bool:
        if not is_ops_capable(_row_to_spoke(self.stock[s])):
            return False
        # Immediately consume C and D resources when operation is launched
        self.stock[s][2] = max(0.0, self.stock[s][2] - amount)
        self.stock[s][3] = max(0, self.stock[s][3] - amount)
        # Increment operation counter
        self.ops_by_spoke[s] += amount
        
        # Apply special capability effects
        for aircraft in self.fleet:
            if aircraft.location == f"S{s}" or aircraft.location == "HUB":
                self.apply_special_capability_effects(aircraft)
        
        return True

    def _initialize_aircraft_attributes(self, aircraft: Aircraft) -> None:
        """Initialize aircraft with proper time and distance mechanics attributes."""
        # Set speed based on aircraft type
        if aircraft.typ == "C-130":
            aircraft.speed_mach = 0.45
            aircraft.turnover_time_hours = 2.0
            aircraft.fuel_consumption_rate = 1.2
        elif aircraft.typ == "C-27":
            aircraft.speed_mach = 0.35
            aircraft.turnover_time_hours = 1.5
            aircraft.fuel_consumption_rate = 0.8
        elif aircraft.typ == "C-17":
            aircraft.speed_mach = 0.77
            aircraft.turnover_time_hours = 3.0
            aircraft.fuel_consumption_rate = 2.5
        elif aircraft.typ == "C-5":
            aircraft.speed_mach = 0.77
            aircraft.turnover_time_hours = 4.0
            aircraft.fuel_consumption_rate = 4.0
        elif aircraft.typ == "C-295":
            aircraft.speed_mach = 0.4
            aircraft.turnover_time_hours = 1.8
            aircraft.fuel_consumption_rate = 0.9
        elif aircraft.typ == "Custom_Transport":
            aircraft.speed_mach = 0.5
            aircraft.turnover_time_hours = 2.5
            aircraft.fuel_consumption_rate = 1.1
        else:
            # Default values for unknown aircraft types
            aircraft.speed_mach = 0.45
            aircraft.turnover_time_hours = 2.0
            aircraft.fuel_consumption_rate = 1.0
        
        # Initialize time tracking
        aircraft.current_flight_time = 0.0
        aircraft.total_flight_hours = 0.0

    def calculate_flight_time(self, from_location: str, to_location: str, aircraft: Aircraft) -> float:
        """Calculate flight time between two locations for a given aircraft.
        
        Args:
            from_location: Starting location ("HUB" or "S{1..10}")
            to_location: Destination location ("HUB" or "S{1..10}")
            aircraft: Aircraft object with speed_mach attribute
            
        Returns:
            Flight time in hours
        """
        # Calculate distance between locations
        distance_miles = self._calculate_distance_from_locations(from_location, to_location)
        
        # Convert Mach to miles per hour: speed_mph = speed_mach * 767.269
        speed_mph = aircraft.speed_mach * 767.269
        
        # Return flight time: flight_time = distance / speed_mph
        flight_time = distance_miles / speed_mph
        
        return flight_time
    
    def _calculate_distance_from_locations(self, from_location: str, to_location: str) -> float:
        """Calculate distance between two locations in miles.
        
        Args:
            from_location: Starting location ("HUB" or "S{1..10}")
            to_location: Destination location ("HUB" or "S{1..10}")
            
        Returns:
            Distance in miles
        """
        try:
            # Validate input parameters
            if not isinstance(from_location, str) or not isinstance(to_location, str):
                return 0.0
            
            # Get coordinates for both locations
            from_coords = self._get_location_coordinates(from_location)
            to_coords = self._get_location_coordinates(to_location)
            
            if not from_coords or not to_coords:
                return 0.0
            
            # Use the coordinate-based distance calculation
            return self._calculate_distance(from_coords, to_coords)
        except Exception:
            # Return 0.0 for any errors
            return 0.0

    def update_simulation_time(self, delta_hours: float) -> None:
        """Update simulation time and handle time progression for all aircraft.
        
        Args:
            delta_hours: Time increment in hours
        """
        # Optimize time step to minimize floating-point errors
        delta_hours = self._optimize_time_step(delta_hours)
        
        if delta_hours <= 0.0:
            return
        
        # Update current simulation time
        self.current_time_hours += delta_hours
        
        # Handle time progression for all aircraft
        for aircraft in self.fleet:
            # Update flight time for aircraft in flight
            if aircraft.state in ["LEG1_ENROUTE", "AT_SPOKEB_ENROUTE", "RETURN_ENROUTE"]:
                aircraft.update_flight_time(delta_hours)
            
            # Handle state transitions based on time
            self._update_aircraft_state_timing(aircraft, delta_hours)
        
        # Maintain period boundaries for compatibility
        # Each period represents 12 hours (AM/PM)
        hours_per_period = 12.0
        new_period = int(self.current_time_hours / hours_per_period)
        
        if new_period != self.t:
            # Period has changed, update period-based tracking
            self.t = new_period
            self.day = new_period // 2
            self.half = "AM" if new_period % 2 == 0 else "PM"
        
        # Monitor memory usage and perform cleanup if necessary
        self._monitor_memory_usage()
    
    def _update_aircraft_state_timing(self, aircraft: Aircraft, delta_hours: float) -> None:
        """Update aircraft state based on elapsed time.
        
        Args:
            aircraft: Aircraft to update
            delta_hours: Time increment in hours
        """
        # Check if aircraft is in a time-based state
        if not aircraft.is_time_based_state():
            return
        
        # Update remaining time and check if state transition should occur
        if aircraft.update_time_remaining(delta_hours):
            # State transition needed
            if aircraft.state == "ENROUTE":
                # Aircraft has completed its flight leg
                self._complete_flight_leg(aircraft)
            elif aircraft.state == "LOADING":
                # Aircraft has completed loading/unloading
                self._complete_loading(aircraft)
            elif aircraft.state == "MAINTENANCE":
                # Aircraft has completed maintenance
                self._complete_maintenance(aircraft)
    
    def _complete_flight_leg(self, aircraft: Aircraft) -> None:
        """Complete a flight leg and transition to next state."""
        if aircraft.plan is None:
            # No plan, return to IDLE at current location
            aircraft.state = "IDLE"
            return
        
        i, j = aircraft.plan
        
        if aircraft.location == "HUB":
            # Starting from HUB, heading to first spoke
            aircraft.location = f"S{i+1}"
            aircraft.state = "AT_SPOKEA"
            # Set loading state for cargo operations
            loading_time = aircraft.calculate_turnover_time()
            aircraft.set_loading_state(loading_time)
        elif aircraft.location.startswith("S") and aircraft.location == f"S{i+1}":
            # At first spoke, check if going to second spoke
            if j is not None:
                # Continue to second spoke
                aircraft.state = "AT_SPOKEB_ENROUTE"
                # Calculate flight time to second spoke
                flight_time = self.calculate_flight_time(f"S{i+1}", f"S{j+1}", aircraft)
                aircraft.set_enroute_state(flight_time)
            else:
                # Return to HUB
                aircraft.state = "RETURN_ENROUTE"
                # Calculate flight time back to HUB
                flight_time = self.calculate_flight_time(f"S{i+1}", "HUB", aircraft)
                aircraft.set_enroute_state(flight_time)
        elif aircraft.location.startswith("S") and aircraft.location == f"S{j+1}":
            # At second spoke, return to HUB
            aircraft.state = "RETURN_ENROUTE"
            # Calculate flight time back to HUB
            flight_time = self.calculate_flight_time(f"S{j+1}", "HUB", aircraft)
            aircraft.set_enroute_state(flight_time)
        else:
            # Unexpected location, reset to IDLE
            aircraft.state = "IDLE"
            aircraft.location = "HUB"
    
    def _complete_loading(self, aircraft: Aircraft) -> None:
        """Complete loading/unloading operations."""
        if aircraft.location == "HUB":
            # At HUB, start flight to first spoke
            if aircraft.plan and aircraft.plan[0] is not None:
                i = aircraft.plan[0]
                flight_time = self.calculate_flight_time("HUB", f"S{i+1}", aircraft)
                aircraft.set_enroute_state(flight_time)
            else:
                aircraft.state = "IDLE"
        elif aircraft.location.startswith("S"):
            # At spoke, check if going to second spoke or returning to HUB
            if aircraft.plan and aircraft.plan[1] is not None:
                # Going to second spoke
                i, j = aircraft.plan
                if aircraft.location == f"S{i+1}":
                    flight_time = self.calculate_flight_time(f"S{i+1}", f"S{j+1}", aircraft)
                    aircraft.set_enroute_state(flight_time)
                else:
                    # Return to HUB
                    flight_time = self.calculate_flight_time(aircraft.location, "HUB", aircraft)
                    aircraft.set_enroute_state(flight_time)
            else:
                # Return to HUB
                flight_time = self.calculate_flight_time(aircraft.location, "HUB", aircraft)
                aircraft.set_enroute_state(flight_time)
    
    def _complete_maintenance(self, aircraft: Aircraft) -> None:
        """Complete maintenance and return to IDLE state."""
        aircraft.state = "IDLE"
        aircraft.maintenance_time_remaining = 0.0

    def calculate_operational_cost(self, aircraft: Aircraft, flight_hours: float) -> float:
        """Calculate operational cost for an aircraft based on flight hours.
        
        Args:
            aircraft: Aircraft object
            flight_hours: Number of flight hours
            
        Returns:
            Operational cost in currency units
        """
        # Base cost per flight hour from configuration
        base_cost = self.cfg.cost_per_flight_hour
        
        # Aircraft-specific multipliers
        aircraft_multiplier = 1.0
        if aircraft.typ == "C-130":
            aircraft_multiplier = 1.0  # Baseline
        elif aircraft.typ == "C-27":
            aircraft_multiplier = 0.8  # Smaller, more efficient
        elif aircraft.typ == "C-17":
            aircraft_multiplier = 2.5  # Larger, more expensive
        elif aircraft.typ == "C-5":
            aircraft_multiplier = 4.0  # Largest, most expensive
        elif aircraft.typ == "C-295":
            aircraft_multiplier = 0.9  # Modern, efficient
        elif aircraft.typ == "Custom_Transport":
            aircraft_multiplier = 1.2  # Custom aircraft premium
        
        # Special capability cost adjustments
        capability_multiplier = 1.0
        if hasattr(aircraft, 'special_capabilities'):
            for capability in aircraft.special_capabilities:
                if capability == "tactical":
                    capability_multiplier += 0.3  # Tactical capability premium
                elif capability == "fuel_efficient":
                    capability_multiplier -= 0.1  # Fuel efficiency discount
                elif capability == "high_capacity":
                    capability_multiplier += 0.2  # High capacity premium
                elif capability == "all_weather":
                    capability_multiplier += 0.15  # All-weather capability premium
                elif capability == "long_range":
                    capability_multiplier += 0.25  # Long range premium
        
        # Calculate total operational cost
        total_cost = base_cost * flight_hours * aircraft_multiplier * capability_multiplier
        
        return total_cost
    
    def calculate_fuel_cost(self, aircraft: Aircraft, flight_hours: float) -> float:
        """Calculate fuel cost for an aircraft based on flight hours.
        
        Args:
            aircraft: Aircraft object
            flight_hours: Number of flight hours
            
        Returns:
            Fuel cost in currency units
        """
        # Base fuel price per gallon (configurable)
        fuel_price_per_gallon = 3.50  # Default fuel price
        
        # Aircraft-specific fuel consumption rates
        fuel_consumption_gph = aircraft.fuel_consumption_rate * 100  # Gallons per hour
        
        # Special capability adjustments
        if hasattr(aircraft, 'special_capabilities'):
            for capability in aircraft.special_capabilities:
                if capability == "fuel_efficient":
                    fuel_consumption_gph *= 0.8  # 20% reduction
                elif capability == "high_capacity":
                    fuel_consumption_gph *= 1.1  # 10% increase due to weight
        
        # Calculate total fuel cost
        total_fuel_cost = fuel_consumption_gph * flight_hours * fuel_price_per_gallon
        
        return total_fuel_cost
    
    def calculate_maintenance_cost(self, aircraft: Aircraft, flight_hours: float) -> float:
        """Calculate maintenance cost for an aircraft based on flight hours.
        
        Args:
            aircraft: Aircraft object
            flight_hours: Number of flight hours
            
        Returns:
            Maintenance cost in currency units
        """
        # Base maintenance cost per flight hour
        base_maintenance_rate = 500.0  # Currency units per flight hour
        
        # Aircraft-specific maintenance rates
        maintenance_multiplier = 1.0
        if aircraft.typ == "C-130":
            maintenance_multiplier = 1.0  # Baseline
        elif aircraft.typ == "C-27":
            maintenance_multiplier = 0.7  # Smaller, simpler maintenance
        elif aircraft.typ == "C-17":
            maintenance_multiplier = 2.0  # Larger, complex maintenance
        elif aircraft.typ == "C-5":
            maintenance_multiplier = 3.0  # Largest, most complex maintenance
        elif aircraft.typ == "C-295":
            maintenance_multiplier = 0.8  # Modern, reliable
        elif aircraft.typ == "Custom_Transport":
            maintenance_multiplier = 1.5  # Custom aircraft maintenance premium
        
        # Special capability maintenance requirements
        capability_maintenance_multiplier = 1.0
        if hasattr(aircraft, 'special_capabilities'):
            for capability in aircraft.special_capabilities:
                if capability == "tactical":
                    capability_maintenance_multiplier += 0.4  # Tactical capability maintenance
                elif capability == "all_weather":
                    capability_maintenance_multiplier += 0.2  # All-weather capability maintenance
                elif capability == "rough_field":
                    capability_maintenance_multiplier += 0.3  # Rough field capability maintenance
        
        # Calculate total maintenance cost
        total_maintenance_cost = (base_maintenance_rate * flight_hours * 
                                maintenance_multiplier * capability_maintenance_multiplier)
        
        return total_maintenance_cost
    
    def calculate_total_aircraft_cost(self, aircraft: Aircraft, flight_hours: float) -> float:
        """Calculate total cost for an aircraft including operational, fuel, and maintenance costs.
        
        Args:
            aircraft: Aircraft object
            flight_hours: Number of flight hours
            
        Returns:
            Total cost in currency units
        """
        operational_cost = self.calculate_operational_cost(aircraft, flight_hours)
        fuel_cost = self.calculate_fuel_cost(aircraft, flight_hours)
        maintenance_cost = self.calculate_maintenance_cost(aircraft, flight_hours)
        
        total_cost = operational_cost + fuel_cost + maintenance_cost
        
        return total_cost

    def update_aircraft_costs(self, aircraft: Aircraft, flight_hours: float) -> None:
        """Update total costs for an aircraft and add to cost history.
        
        Args:
            aircraft: Aircraft object
            flight_hours: Number of flight hours to calculate costs for
        """
        # Calculate costs for this aircraft
        operational_cost = self.calculate_operational_cost(aircraft, flight_hours)
        fuel_cost = self.calculate_fuel_cost(aircraft, flight_hours)
        maintenance_cost = self.calculate_maintenance_cost(aircraft, flight_hours)
        
        # Update total costs
        self.total_operational_cost += operational_cost
        self.total_fuel_cost += fuel_cost
        self.total_maintenance_cost += maintenance_cost
        
        # Add to cost history
        cost_entry = {
            'period': self.t,
            'time_hours': self.current_time_hours,
            'aircraft_name': aircraft.name,
            'aircraft_type': aircraft.typ,
            'flight_hours': flight_hours,
            'operational_cost': operational_cost,
            'fuel_cost': fuel_cost,
            'maintenance_cost': maintenance_cost,
            'total_cost': operational_cost + fuel_cost + maintenance_cost
        }
        self.cost_history.append(cost_entry)
        
        # Limit cost history size to prevent memory issues
        if len(self.cost_history) > 10000:
            self.cost_history = self.cost_history[-5000:]
    
    def get_total_simulation_cost(self) -> float:
        """Get total cost for the entire simulation.
        
        Returns:
            Total cost in currency units
        """
        return self.total_operational_cost + self.total_fuel_cost + self.total_maintenance_cost
    
    def get_cost_summary(self) -> dict:
        """Get a summary of all costs for the simulation.
        
        Returns:
            Dictionary containing cost summary
        """
        return {
            'total_operational_cost': self.total_operational_cost,
            'total_fuel_cost': self.total_fuel_cost,
            'total_maintenance_cost': self.total_maintenance_cost,
            'total_cost': self.get_total_simulation_cost(),
            'cost_history_count': len(self.cost_history)
        }

    def build_fleet(self, label: str) -> List[Aircraft]:
        """Build fleet from label or custom fleet composition."""
        # Use the Fleet Builder pallet as the single source of truth
        try:
            from ..ui.fleet_builder import get_fleet_builder
            fleet_builder = get_fleet_builder()
            
            # Get the current fleet from the Fleet Builder pallet
            current_fleet = fleet_builder.get_current_fleet()
            if current_fleet:
                # Create fleet composition from current pallet
                fleet_composition = FleetComposition("Current Fleet", current_fleet)
                fleet_composition.calculate_metrics(fleet_builder.config_manager.aircraft_types)
                return self._build_fleet_from_composition(fleet_composition)
                
        except ImportError:
            # Fallback to legacy system if fleet builder not available
            pass
        
        # Legacy fleet label handling
        if label == "2xC130":
            aircraft = [Aircraft("C-130", self.cfg.cap_c130, "C-130 #1"),
                    Aircraft("C-130", self.cfg.cap_c130, "C-130 #2")]
            for ac in aircraft:
                self._initialize_aircraft_attributes(ac)
            return aircraft
        if label == "4xC130":
            aircraft = [Aircraft("C-130", self.cfg.cap_c130, "C-130 #1"),
                    Aircraft("C-130", self.cfg.cap_c130, "C-130 #2"),
                    Aircraft("C-130", self.cfg.cap_c130, "C-130 #3"),
                    Aircraft("C-130", self.cfg.cap_c130, "C-130 #4")]
            for ac in aircraft:
                self._initialize_aircraft_attributes(ac)
            return aircraft
        if label == "2xC130_2xC27":
            aircraft = [Aircraft("C-130", self.cfg.cap_c130, "C-130 #1"),
                    Aircraft("C-130", self.cfg.cap_c130, "C-130 #2"),
                    Aircraft("C-27", self.cfg.cap_c27, "C-27 #1"),
                    Aircraft("C-27", self.cfg.cap_c27, "C-27 #2")]
            for ac in aircraft:
                self._initialize_aircraft_attributes(ac)
            return aircraft
        if label == "2xCustom_Transport":
            # Handle custom transport with its configured attributes
            try:
                from ..ui.fleet_builder import get_aircraft_config_manager
                config_manager = get_aircraft_config_manager()
                if "Custom_Transport" in config_manager.aircraft_types:
                    custom_type = config_manager.aircraft_types["Custom_Transport"]
                    aircraft = [
                        Aircraft("Custom_Transport", custom_type.base_capacity, "Custom Transport #1"),
                        Aircraft("Custom_Transport", custom_type.base_capacity, "Custom Transport #2")
                    ]
                    for ac in aircraft:
                        self._initialize_aircraft_attributes(ac)
                    return aircraft
                else:
                    # Fallback to default custom transport
                    aircraft = [
                        Aircraft("Custom_Transport", 4, "Custom Transport #1"),
                        Aircraft("Custom_Transport", 4, "Custom Transport #2")
                    ]
                    for ac in aircraft:
                        self._initialize_aircraft_attributes(ac)
                    return aircraft
            except Exception:
                # Fallback to default custom transport
                aircraft = [
                    Aircraft("Custom_Transport", 4, "Custom Transport #1"),
                    Aircraft("Custom_Transport", 4, "Custom Transport #2")
                ]
                for ac in aircraft:
                    self._initialize_aircraft_attributes(ac)
                return aircraft
        if label == "3xCustom_Transport":
            # Handle custom transport with its configured attributes
            try:
                from ..ui.fleet_builder import get_aircraft_config_manager
                config_manager = get_aircraft_config_manager()
                if "Custom_Transport" in config_manager.aircraft_types:
                    custom_type = config_manager.aircraft_types["Custom_Transport"]
                    aircraft = [
                        Aircraft("Custom_Transport", custom_type.base_capacity, "Custom Transport #1"),
                        Aircraft("Custom_Transport", custom_type.base_capacity, "Custom Transport #2"),
                        Aircraft("Custom_Transport", custom_type.base_capacity, "Custom Transport #3")
                    ]
                    for ac in aircraft:
                        self._initialize_aircraft_attributes(ac)
                    return aircraft
                else:
                    # Fallback to default custom transport
                    aircraft = [
                        Aircraft("Custom_Transport", 4, "Custom Transport #1"),
                        Aircraft("Custom_Transport", 4, "Custom Transport #2"),
                        Aircraft("Custom_Transport", 4, "Custom Transport #3")
                    ]
                    for ac in aircraft:
                        self._initialize_aircraft_attributes(ac)
                    return aircraft
            except Exception:
                # Fallback to default custom transport
                aircraft = [
                    Aircraft("Custom_Transport", 4, "Custom Transport #1"),
                    Aircraft("Custom_Transport", 4, "Custom Transport #2"),
                    Aircraft("Custom_Transport", 4, "Custom Transport #3")
                ]
                for ac in aircraft:
                    self._initialize_aircraft_attributes(ac)
                return aircraft
        if label == "1xC130_1xCustom_Transport":
            # Handle mixed fleet with custom transport
            try:
                from ..ui.fleet_builder import get_aircraft_config_manager
                config_manager = get_aircraft_config_manager()
                if "Custom_Transport" in config_manager.aircraft_types:
                    custom_type = config_manager.aircraft_types["Custom_Transport"]
                    aircraft = [
                        Aircraft("C-130", self.cfg.cap_c130, "C-130 #1"),
                        Aircraft("Custom_Transport", custom_type.base_capacity, "Custom Transport #1")
                    ]
                    for ac in aircraft:
                        self._initialize_aircraft_attributes(ac)
                    return aircraft
                else:
                    # Fallback to default custom transport
                    aircraft = [
                        Aircraft("C-130", self.cfg.cap_c130, "C-130 #1"),
                        Aircraft("Custom_Transport", 4, "Custom Transport #1")
                    ]
                    for ac in aircraft:
                        self._initialize_aircraft_attributes(ac)
                    return aircraft
            except Exception:
                # Fallback to default custom transport
                aircraft = [
                    Aircraft("C-130", self.cfg.cap_c130, "C-130 #1"),
                    Aircraft("Custom_Transport", 4, "Custom Transport #1")
                ]
                for ac in aircraft:
                    self._initialize_aircraft_attributes(ac)
                return aircraft
        
        # If we get here, try to parse as custom format
        try:
            aircraft = []
            aircraft_counter = {}
            parts = label.split("_")
            for part in parts:
                if "x" in part:
                    count_str, aircraft_type = part.split("x", 1)
                    count = int(count_str)
                    
                    # Initialize counter for this aircraft type if not exists
                    if aircraft_type not in aircraft_counter:
                        aircraft_counter[aircraft_type] = 1
                    
                    if aircraft_type == "C-130":
                        for i in range(count):
                            ac = Aircraft("C-130", self.cfg.cap_c130, f"C-130 #{aircraft_counter[aircraft_type]}")
                            self._initialize_aircraft_attributes(ac)
                            aircraft.append(ac)
                            aircraft_counter[aircraft_type] += 1
                    elif aircraft_type == "C-27":
                        for i in range(count):
                            ac = Aircraft("C-27", self.cfg.cap_c27, f"C-27 #{aircraft_counter[aircraft_type]}")
                            self._initialize_aircraft_attributes(ac)
                            aircraft.append(ac)
                            aircraft_counter[aircraft_type] += 1
                    elif aircraft_type == "Custom_Transport":
                        # Handle custom transport with its configured attributes
                        try:
                            from ..ui.fleet_builder import get_aircraft_config_manager
                            config_manager = get_aircraft_config_manager()
                            if aircraft_type in config_manager.aircraft_types:
                                custom_type = config_manager.aircraft_types[aircraft_type]
                                for i in range(count):
                                    custom_aircraft = Aircraft(
                                        aircraft_type, 
                                        custom_type.base_capacity, 
                                        f"Custom Transport #{aircraft_counter[aircraft_type]}"
                                    )
                                    custom_aircraft.special_capabilities = custom_type.special_capabilities
                                    self._initialize_aircraft_attributes(custom_aircraft)
                                    aircraft.append(custom_aircraft)
                                    aircraft_counter[aircraft_type] += 1
                            else:
                                # Fallback to default custom transport
                                for i in range(count):
                                    ac = Aircraft(aircraft_type, 4, f"Custom Transport #{aircraft_counter[aircraft_type]}")
                                    self._initialize_aircraft_attributes(ac)
                                    aircraft.append(ac)
                                    aircraft_counter[aircraft_type] += 1
                        except Exception:
                            # Fallback to default custom transport
                            for i in range(count):
                                ac = Aircraft(aircraft_type, 4, f"Custom Transport #{aircraft_counter[aircraft_type]}")
                                self._initialize_aircraft_attributes(ac)
                                aircraft.append(ac)
                                aircraft_counter[aircraft_type] += 1
                    else:
                        # For other aircraft types, try to get from fleet builder
                        try:
                            from ..ui.fleet_builder import get_aircraft_config_manager
                            config_manager = get_aircraft_config_manager()
                            if aircraft_type in config_manager.aircraft_types:
                                aircraft_type_config = config_manager.aircraft_types[aircraft_type]
                                for i in range(count):
                                    new_aircraft = Aircraft(
                                        aircraft_type, 
                                        aircraft_type_config.base_capacity, 
                                        f"{aircraft_type} #{aircraft_counter[aircraft_type]}"
                                    )
                                    # Add special capabilities
                                    new_aircraft.special_capabilities = aircraft_type_config.special_capabilities
                                    self._initialize_aircraft_attributes(new_aircraft)
                                    aircraft.append(new_aircraft)
                                    aircraft_counter[aircraft_type] += 1
                            else:
                                # Fallback to default capacity
                                for i in range(count):
                                    ac = Aircraft(aircraft_type, 5, f"{aircraft_type} #{aircraft_counter[aircraft_type]}")
                                    self._initialize_aircraft_attributes(ac)
                                    aircraft.append(ac)
                                    aircraft_counter[aircraft_type] += 1
                        except Exception:
                            # Fallback to default capacity
                            for i in range(count):
                                ac = Aircraft(aircraft_type, 5, f"{aircraft_type} #{aircraft_counter[aircraft_type]}")
                                self._initialize_aircraft_attributes(ac)
                                aircraft.append(ac)
                                aircraft_counter[aircraft_type] += 1
            
            if aircraft:
                return aircraft
        except (ValueError, KeyError):
            pass
        
        raise ValueError(f"Unknown fleet label: {label}")
    
    def _build_fleet_from_composition(self, fleet_composition) -> List[Aircraft]:
        """Build fleet from FleetComposition object."""
        aircraft = []
        aircraft_counter = {}
        
        for aircraft_id, count in fleet_composition.aircraft.items():
            if aircraft_id not in aircraft_counter:
                aircraft_counter[aircraft_id] = 1
            
            for i in range(count):
                if aircraft_id == "C-130":
                    ac = Aircraft("C-130", self.cfg.cap_c130, f"C-130 #{aircraft_counter[aircraft_id]}")
                    self._initialize_aircraft_attributes(ac)
                    aircraft.append(ac)
                elif aircraft_id == "C-27":
                    ac = Aircraft("C-27", self.cfg.cap_c27, f"C-27 #{aircraft_counter[aircraft_id]}")
                    self._initialize_aircraft_attributes(ac)
                    aircraft.append(ac)
                elif aircraft_id == "Custom_Transport":
                    # Handle custom transport with its configured attributes
                    try:
                        from ..ui.fleet_builder import get_aircraft_config_manager
                        config_manager = get_aircraft_config_manager()
                        if aircraft_id in config_manager.aircraft_types:
                            custom_type = config_manager.aircraft_types[aircraft_id]
                            custom_aircraft = Aircraft(
                                aircraft_id, 
                                custom_type.base_capacity, 
                                f"Custom Transport #{aircraft_counter[aircraft_id]}"
                            )
                            # Add special capabilities as an attribute
                            custom_aircraft.special_capabilities = custom_type.special_capabilities
                            self._initialize_aircraft_attributes(custom_aircraft)
                            aircraft.append(custom_aircraft)
                        else:
                            # Fallback to default custom transport
                            ac = Aircraft(aircraft_id, 4, f"Custom Transport #{aircraft_counter[aircraft_id]}")
                            self._initialize_aircraft_attributes(ac)
                            aircraft.append(ac)
                    except Exception:
                        # Fallback to default custom transport
                        ac = Aircraft(aircraft_id, 4, f"Custom Transport #{aircraft_counter[aircraft_id]}")
                        self._initialize_aircraft_attributes(ac)
                        aircraft.append(ac)
                else:
                    # For other aircraft types, try to get from fleet builder
                    try:
                        from ..ui.fleet_builder import get_aircraft_config_manager
                        config_manager = get_aircraft_config_manager()
                        if aircraft_id in config_manager.aircraft_types:
                            aircraft_type = config_manager.aircraft_types[aircraft_id]
                            new_aircraft = Aircraft(
                                aircraft_id, 
                                aircraft_type.base_capacity, 
                                f"{aircraft_id} #{aircraft_counter[aircraft_id]}"
                            )
                            # Add special capabilities
                            new_aircraft.special_capabilities = aircraft_type.special_capabilities
                            self._initialize_aircraft_attributes(new_aircraft)
                            aircraft.append(new_aircraft)
                        else:
                            # Fallback to default capacity
                            ac = Aircraft(aircraft_id, 5, f"{aircraft_id} #{aircraft_counter[aircraft_id]}")
                            self._initialize_aircraft_attributes(ac)
                            aircraft.append(ac)
                    except Exception:
                        # Fallback to default capacity
                        ac = Aircraft(aircraft_id, 5, f"{aircraft_id} #{aircraft_counter[aircraft_id]}")
                        self._initialize_aircraft_attributes(ac)
                        aircraft.append(ac)
                
                aircraft_counter[aircraft_id] += 1
        
        return aircraft
    
    def _initialize_targeting_positions(self):
        """Initialize smart targeting system with hub and spoke positions."""
        if not self.smart_targeting:
            return
            
        # Use approximate positions based on the circular layout
        # In a real implementation, these would come from the renderer
        hub_pos = (0, 0)  # Center
        spoke_positions = []
        
        for i in range(self.M):
            # Approximate circular layout (radius 100, starting from top)
            theta = 2 * 3.14159 * i / self.M
            x = int(100 * math.cos(theta))
            y = int(100 * math.sin(theta))
            spoke_positions.append((x, y))
            
        self.smart_targeting.initialize_positions(hub_pos, spoke_positions)
    
    def update_targeting_positions(self, hub_pos: Tuple[int, int], spoke_positions: List[Tuple[int, int]]):
        """Update hub and spoke positions for smart targeting (called from renderer)."""
        if self.smart_targeting:
            self.smart_targeting.initialize_positions(hub_pos, spoke_positions)
    
    def _plan_smart_route(self, aircraft: Aircraft, stage: str) -> Optional[Tuple[Tuple[int, Optional[int]], List[int], List[int]]]:
        """Plan a route for an aircraft using smart targeting with distance and cost optimization."""
        if not self.smart_targeting:
            return None
            
        # Get aircraft location
        location = aircraft.location
        
        # Find best route using smart targeting
        first_leg, second_leg = self.smart_targeting.find_best_two_legs(
            location, self.stock, stage, aircraft.cap
        )
        
        if first_leg is None:
            return None
        
        # Validate route range and find optimal path
        first_spoke_idx = first_leg.spoke_idx
        first_spoke = f"S{first_spoke_idx+1}"
        
        # Check if first leg is within range
        if location == "HUB":
            distance, flight_time = self.calculate_optimal_route("HUB", first_spoke, aircraft)
        else:
            distance, flight_time = self.calculate_optimal_route(location, first_spoke, aircraft)
        
        # If first leg is not feasible, try to find alternative routes
        if not self._validate_route_range(distance, aircraft):
            # Try to find a closer spoke that's within range
            alternative_spoke = self._find_closest_feasible_spoke(location, aircraft, stage)
            if alternative_spoke is not None:
                first_spoke_idx = alternative_spoke
                first_spoke = f"S{first_spoke_idx+1}"
            else:
                # No feasible route found
                return None
        
        # Reserve the first spoke
        self.smart_targeting.reserve_spoke(first_spoke_idx)
        
        # Plan payload for first leg
        payload_A = self._plan_payload_for_spoke(first_spoke_idx, aircraft.cap, stage)
        
        if second_leg is not None:
            second_spoke_idx = second_leg.spoke_idx
            second_spoke = f"S{second_spoke_idx+1}"
            
            # Check if second leg is within range from first spoke
            distance, flight_time = self.calculate_optimal_route(first_spoke, second_spoke, aircraft)
            
            if not self._validate_route_range(distance, aircraft):
                # Second leg not feasible, try to find alternative
                alternative_second = self._find_closest_feasible_spoke(first_spoke, aircraft, stage)
                if alternative_second is not None:
                    second_spoke_idx = alternative_second
                    second_spoke = f"S{second_spoke_idx+1}"
                else:
                    # No feasible second leg, make it a single-leg mission
                    second_leg = None
            
            if second_leg is not None:
                # Reserve the second spoke
                self.smart_targeting.reserve_spoke(second_spoke_idx)
                payload_B = self._plan_payload_for_spoke(second_spoke_idx, aircraft.cap, stage)
                return (first_spoke_idx, second_spoke_idx), payload_A, payload_B
        
        # Single-leg mission
        return (first_spoke_idx, None), payload_A, [0, 0, 0, 0]
    
    def _find_closest_feasible_spoke(self, from_location: str, aircraft: Aircraft, stage: str) -> Optional[int]:
        """Find the closest spoke that's within aircraft range and has operational needs.
        
        Args:
            from_location: Starting location
            aircraft: Aircraft object
            stage: Current simulation stage
            
        Returns:
            Index of closest feasible spoke, or None if none found
        """
        best_spoke = None
        best_distance = float('inf')
        
        for i in range(self.M):
            spoke_location = f"S{i+1}"
            
            # Calculate distance to this spoke
            distance = self._calculate_distance_from_locations(from_location, spoke_location)
            
            # Check if within range
            if not self._validate_route_range(distance, aircraft):
                continue
            
            # Check if this spoke has operational needs
            if self._has_operational_needs(i, stage):
                if distance < best_distance:
                    best_distance = distance
                    best_spoke = i
        
        return best_spoke
    
    def _has_operational_needs(self, spoke_idx: int, stage: str) -> bool:
        """Check if a spoke has operational needs based on current stage.
        
        Args:
            spoke_idx: Spoke index
            stage: Current simulation stage
            
        Returns:
            True if spoke has operational needs, False otherwise
        """
        stock = self.stock[spoke_idx]
        
        if stage == "A":
            # Need A and B resources
            return stock[0] < 1 or stock[1] < 1
        elif stage == "B":
            # Need B resources, maintain A
            return stock[1] < 1 or stock[0] < 2
        else:  # "OPS"
            # Need C and D for operations
            return stock[2] < 1 or stock[3] < 1
    
    def _plan_payload_for_spoke(self, spoke_idx: int, capacity: int, stage: str) -> List[int]:
        """Plan payload for a specific spoke based on current needs and stage."""
        payload = [0, 0, 0, 0]
        remaining_capacity = capacity
        
        # Initialize all need variables to avoid UnboundLocalError
        need_A = max(0, 1 - self.stock[spoke_idx][0])
        need_B = max(0, 1 - self.stock[spoke_idx][1])
        need_C = max(0, 1 - self.stock[spoke_idx][2])
        need_D = max(0, 1 - self.stock[spoke_idx][3])
        
        if stage == "A":
            # Focus on A and B resources
            # need_A and need_B are already calculated above
            
            # Prioritize A deficits
            if need_A > 0 and remaining_capacity > 0:
                amount = min(need_A, remaining_capacity)
                payload[0] = amount
                remaining_capacity -= amount
                
            if need_B > 0 and remaining_capacity > 0:
                amount = min(need_B, remaining_capacity)
                payload[1] = amount
                remaining_capacity -= amount
                
        elif stage == "B":
            # Focus on B resources, maintain A
            # Update need_A to maintain 2 units (need_B is already calculated above)
            need_A = max(0, 2 - self.stock[spoke_idx][0])  # Maintain 2 units
            
            if need_B > 0 and remaining_capacity > 0:
                amount = min(need_B, remaining_capacity)
                payload[1] = amount
                remaining_capacity -= amount
                
            if need_A > 0 and remaining_capacity > 0:
                amount = min(need_A, remaining_capacity)
                payload[0] = amount
                remaining_capacity -= amount
                
        else:  # "OPS"
            # Focus on C and D for operations
            # need_C and need_D are already calculated above
            
            if need_C > 0 and remaining_capacity > 0:
                amount = min(need_C, remaining_capacity)
                payload[2] = amount
                remaining_capacity -= amount
                
            if need_D > 0 and remaining_capacity > 0:
                amount = min(need_D, remaining_capacity)
                payload[3] = amount
                remaining_capacity -= amount
                
            # Also maintain A and B (update need_A and need_B to maintain 2 units)
            need_A = max(0, 2 - self.stock[spoke_idx][0])
            need_B = max(0, 2 - self.stock[spoke_idx][1])
            
            if need_A > 0 and remaining_capacity > 0:
                amount = min(need_A, remaining_capacity)
                payload[0] = amount
                remaining_capacity -= amount
                
            if need_B > 0 and remaining_capacity > 0:
                amount = min(need_B, remaining_capacity)
                payload[1] = amount
                remaining_capacity -= amount
        
        # Enhanced payload planning for plentiful resource scenarios
        # When resources are plentiful, consider maintenance flights
        if remaining_capacity > 0 and all(need <= 0 for need in [need_A, need_B, need_C, need_D]):
            # All immediate needs are met, but we can still optimize resource levels
            current_stock = self.stock[spoke_idx]
            
            # Target optimal levels for maintenance
            optimal_A = 2.0
            optimal_B = 2.0
            optimal_C = 1.0
            optimal_D = 1.0
            
            # Calculate how much we can add to get closer to optimal
            if remaining_capacity > 0 and current_stock[0] < optimal_A:
                add_A = min(remaining_capacity, optimal_A - current_stock[0])
                payload[0] += add_A
                remaining_capacity -= add_A
                
            if remaining_capacity > 0 and current_stock[1] < optimal_B:
                add_B = min(remaining_capacity, optimal_B - current_stock[1])
                payload[1] += add_B
                remaining_capacity -= add_B
                
            if remaining_capacity > 0 and current_stock[2] < optimal_C:
                add_C = min(remaining_capacity, optimal_C - current_stock[2])
                payload[2] += add_C
                remaining_capacity -= add_C
                
            if remaining_capacity > 0 and current_stock[3] < optimal_D:
                add_D = min(remaining_capacity, optimal_D - current_stock[3])
                payload[3] += add_D
                remaining_capacity -= add_D
        
        return payload

    def calculate_optimal_route(self, from_location: str, to_location: str, aircraft: Aircraft) -> Tuple[float, float]:
        """Calculate optimal route between two locations considering aircraft capabilities.
        
        Args:
            from_location: Starting location ("HUB" or "S{1..10}")
            to_location: Destination location ("HUB" or "S{1..10}")
            aircraft: Aircraft object with performance attributes
            
        Returns:
            Tuple of (distance_miles, flight_time_hours)
        """
        # Get coordinates for both locations
        from_coords = self._get_location_coordinates(from_location)
        to_coords = self._get_location_coordinates(to_location)
        
        if not from_coords or not to_coords:
            # Fallback to simple distance calculation
            return 0.0, 0.0
        
        # Calculate direct distance
        direct_distance = self._calculate_distance(from_coords, to_coords)
        direct_flight_time = self.calculate_flight_time(from_location, to_location, aircraft)
        
        # Check if aircraft can make the direct flight
        if self._validate_route_range(direct_distance, aircraft):
            return direct_distance, direct_flight_time
        
        # If direct route is not possible, find alternative routes
        if from_location == "HUB" and to_location.startswith("S"):
            # HUB to spoke: check if we need to refuel at intermediate spoke
            return self._find_optimal_hub_to_spoke_route(to_location, aircraft)
        elif from_location.startswith("S") and to_location == "HUB":
            # Spoke to HUB: check if we need to refuel at intermediate spoke
            return self._find_optimal_spoke_to_hub_route(from_location, aircraft)
        elif from_location.startswith("S") and to_location.startswith("S"):
            # Spoke to spoke: find optimal route through HUB or direct
            return self._find_optimal_spoke_to_spoke_route(from_location, to_location, aircraft)
        
        # Fallback to direct route
        return direct_distance, direct_flight_time
    
    def _validate_route_range(self, distance_miles: float, aircraft: Aircraft) -> bool:
        """Validate if an aircraft can fly a given distance.
        
        Args:
            distance_miles: Distance to fly in miles
            aircraft: Aircraft object
            
        Returns:
            True if aircraft can fly the distance, False otherwise
        """
        # Get aircraft range from configuration
        aircraft_range = 1000.0  # Default range
        
        # Try to get range from aircraft type configuration
        try:
            from ..ui.fleet_builder import get_aircraft_config_manager
            config_manager = get_aircraft_config_manager()
            if aircraft.typ in config_manager.aircraft_types:
                aircraft_type = config_manager.aircraft_types[aircraft.typ]
                aircraft_range = aircraft_type.operational_range_miles
        except Exception:
            pass
        
        # Apply special capability adjustments
        if hasattr(aircraft, 'special_capabilities'):
            for capability in aircraft.special_capabilities:
                if capability == "fuel_efficient":
                    aircraft_range *= 1.2  # 20% range increase
                elif capability == "long_range":
                    aircraft_range *= 1.4  # 40% range increase
        
        # Check if distance is within range
        return distance_miles <= aircraft_range
    
    def _find_optimal_hub_to_spoke_route(self, target_spoke: str, aircraft: Aircraft) -> Tuple[float, float]:
        """Find optimal route from HUB to target spoke.
        
        Args:
            target_spoke: Target spoke location (e.g., "S1")
            aircraft: Aircraft object
            
        Returns:
            Tuple of (distance_miles, flight_time_hours)
        """
        target_idx = int(target_spoke[1:]) - 1
        direct_distance = self.cfg.spoke_distances[target_idx]
        
        if self._validate_route_range(direct_distance, aircraft):
            # Direct route is possible
            flight_time = self.calculate_flight_time("HUB", target_spoke, aircraft)
            return direct_distance, flight_time
        
        # Find intermediate spoke for refueling
        best_intermediate = None
        best_total_distance = float('inf')
        
        for i in range(self.M):
            if i == target_idx:
                continue
            
            # Route: HUB -> S{i+1} -> S{target_idx+1}
            leg1_distance = self.cfg.spoke_distances[i]
            # Get coordinates for both spokes
            intermediate_coords = self._get_location_coordinates(f"S{i+1}")
            target_coords = self._get_location_coordinates(target_spoke)
            if intermediate_coords and target_coords:
                leg2_distance = self._calculate_distance(intermediate_coords, target_coords)
                total_distance = leg1_distance + leg2_distance
            else:
                continue
            
            if (self._validate_route_range(leg1_distance, aircraft) and 
                self._validate_route_range(leg2_distance, aircraft) and
                total_distance < best_total_distance):
                best_intermediate = i
                best_total_distance = total_distance
        
        if best_intermediate is not None:
            # Use intermediate spoke route
            flight_time = (self.calculate_flight_time("HUB", f"S{best_intermediate+1}", aircraft) +
                          self.calculate_flight_time(f"S{best_intermediate+1}", target_spoke, aircraft))
            return best_total_distance, flight_time
        
        # Fallback to direct route (may fail in simulation)
        flight_time = self.calculate_flight_time("HUB", target_spoke, aircraft)
        return direct_distance, flight_time
    
    def _find_optimal_spoke_to_hub_route(self, source_spoke: str, aircraft: Aircraft) -> Tuple[float, float]:
        """Find optimal route from source spoke to HUB.
        
        Args:
            source_spoke: Source spoke location (e.g., "S1")
            aircraft: Aircraft object
            
        Returns:
            Tuple of (distance_miles, flight_time_hours)
        """
        source_idx = int(source_spoke[1:]) - 1
        direct_distance = self.cfg.spoke_distances[source_idx]
        
        if self._validate_route_range(direct_distance, aircraft):
            # Direct route is possible
            flight_time = self.calculate_flight_time(source_spoke, "HUB", aircraft)
            return direct_distance, flight_time
        
        # Find intermediate spoke for refueling
        best_intermediate = None
        best_total_distance = float('inf')
        
        for i in range(self.M):
            if i == source_idx:
                continue
            
            # Route: S{source_idx+1} -> S{i+1} -> HUB
            # Get coordinates for both spokes
            source_coords = self._get_location_coordinates(source_spoke)
            intermediate_coords = self._get_location_coordinates(f"S{i+1}")
            if source_coords and intermediate_coords:
                leg1_distance = self._calculate_distance(source_coords, intermediate_coords)
                leg2_distance = self.cfg.spoke_distances[i]
                total_distance = leg1_distance + leg2_distance
            else:
                continue
            
            if (self._validate_route_range(leg1_distance, aircraft) and 
                self._validate_route_range(leg2_distance, aircraft) and
                total_distance < best_total_distance):
                best_intermediate = i
                best_total_distance = total_distance
        
        if best_intermediate is not None:
            # Use intermediate spoke route
            flight_time = (self.calculate_flight_time(source_spoke, f"S{best_intermediate+1}", aircraft) +
                          self.calculate_flight_time(f"S{best_intermediate+1}", "HUB", aircraft))
            return best_total_distance, flight_time
        
        # Fallback to direct route (may fail in simulation)
        flight_time = self.calculate_flight_time(source_spoke, "HUB", aircraft)
        return direct_distance, flight_time
    
    def _find_optimal_spoke_to_spoke_route(self, from_spoke: str, to_spoke: str, aircraft: Aircraft) -> Tuple[float, float]:
        """Find optimal route between two spokes.
        
        Args:
            from_spoke: Source spoke location (e.g., "S1")
            to_spoke: Target spoke location (e.g., "S2")
            aircraft: Aircraft object
            
        Returns:
            Tuple of (distance_miles, flight_time_hours)
        """
        # Option 1: Direct route
        # Get coordinates for both spokes
        from_coords = self._get_location_coordinates(from_spoke)
        to_coords = self._get_location_coordinates(to_spoke)
        if from_coords and to_coords:
            direct_distance = self._calculate_distance(from_coords, to_coords)
            if self._validate_route_range(direct_distance, aircraft):
                flight_time = self.calculate_flight_time(from_spoke, to_spoke, aircraft)
                return direct_distance, flight_time
        else:
            direct_distance = 0.0
        
        # Option 2: Route through HUB
        from_idx = int(from_spoke[1:]) - 1
        to_idx = int(to_spoke[1:]) - 1
        
        hub_route_distance = (self.cfg.spoke_distances[from_idx] + 
                             self.cfg.spoke_distances[to_idx])
        
        if (self._validate_route_range(self.cfg.spoke_distances[from_idx], aircraft) and
            self._validate_route_range(self.cfg.spoke_distances[to_idx], aircraft)):
            # HUB route is possible
            flight_time = (self.calculate_flight_time(from_spoke, "HUB", aircraft) +
                          self.calculate_flight_time("HUB", to_spoke, aircraft))
            return hub_route_distance, flight_time
        
        # Fallback to direct route (may fail in simulation)
        flight_time = self.calculate_flight_time(from_spoke, to_spoke, aircraft)
        return direct_distance, flight_time
    
    def detect_stage(self) -> str:
        # Check for critical shortages (at or below 0.5)
        if any(self.stock[i][0] <= 0.5 for i in range(self.M)):
            return "A"
        if any(self.stock[i][1] <= 0.5 for i in range(self.M)):
            return "B"
        
        # Check for low resources (below 1.5) to be proactive
        if any(self.stock[i][0] < 1.5 for i in range(self.M)):
            return "A"
        if any(self.stock[i][1] < 1.5 for i in range(self.M)):
            return "B"
            
        return "OPS"

    def plan_for_pair_stage(self, i: int, j: int, cap_left: int, stage: str):
        p_i = [0,0,0,0]; p_j = [0,0,0,0]; rem = cap_left
        def give(target_idx: int, k: int, need: int):
            nonlocal rem
            if rem <= 0 or need <= 0: return
            x = min(rem, need)
            if target_idx == i: p_i[k] += x
            else: p_j[k] += x
            rem -= x

        needA_i = max(0, 1 - self.stock[i][0]); needB_i = max(0, 1 - self.stock[i][1])
        needA_j = max(0, 1 - self.stock[j][0]); needB_j = max(0,  1 - self.stock[j][1])
        needC_i = max(0, 1 - self.stock[i][2]); needD_i = max(0,  1 - self.stock[i][3])
        needC_j = max(0,  1 - self.stock[j][2]); needD_j = max(0,  1 - self.stock[j][3])

        if stage == "A":
            give(i,0,needA_i); give(j,0,needA_j)
            give(i,1,needB_i); give(j,1,needB_j)
            give(i,0, max(0, 2 - (self.stock[i][0] + p_i[0])))
            give(j,0, max(0, 2 - (self.stock[j][0] + p_j[0])))
        elif stage == "B":
            give(i,1,needB_i); give(j,1,needB_j)
            give(i,0, max(0, 2 - self.stock[i][0]))
            give(j,0, max(0, 2 - self.stock[j][0]))
        else:  # "OPS"
            give(i,2,needC_i); give(j,2,needC_j)
            give(i,3,needD_i); give(j,3,needD_j)
            give(i,2, max(0, 2 - (self.stock[i][2] + p_i[2])))
            give(j,2, max(0, 2 - (self.stock[j][2] + p_j[2])))
            give(i,3, max(0, 2 - (self.stock[i][3] + p_i[3])))
            give(j,3, max(0, 2 - (self.stock[j][3] + p_j[3])))

        return p_i, p_j

    def snapshot(self) -> dict:
        return {
            "t": self.t,
            "day": self.day,
            "half": self.half,
            "stock": copy.deepcopy(self.stock),
            "op": self.op.copy(),
            "arrivals_next": copy.deepcopy(self.arrivals_next),
            "pair_cursor": self.pair_cursor,
            "fleet": copy.deepcopy(self.fleet),
            "actions_log": copy.deepcopy(self.actions_log),
            "ops_by_spoke": self.ops_by_spoke[:],
            "ops_total_history": self.ops_total_history[:],
        }

    def restore(self, snap: dict):
        self.t = snap["t"]
        self.day = snap["day"]
        self.half = snap["half"]
        self.stock = copy.deepcopy(snap["stock"])
        self.op = snap["op"].copy()
        self.arrivals_next = copy.deepcopy(snap["arrivals_next"])
        self.pair_cursor = snap["pair_cursor"]
        self.fleet = copy.deepcopy(snap["fleet"])
        self.actions_log = copy.deepcopy(snap["actions_log"])
        self.ops_by_spoke = snap.get("ops_by_spoke", [0]*self.M)[:]
        self.ops_total_history = snap.get("ops_total_history", [0])[:]

    def push_snapshot(self):
        self.history.append(self.snapshot())

    def step_period(self):
        if self.t >= self.cfg.periods:
            return None  # Simulation complete - reached max periods

        pre_stock = [row[:] for row in self.stock]
        ops_before = self.ops_by_spoke[:]
        pre_ops_total = sum(self.ops_by_spoke)

        # 1) APPLY_ARRIVALS_FROM_PREVIOUS_PERIOD
        for s in range(self.M):
            if self.arrivals_next[s]:
                add = [0,0,0,0]
                for vec in self.arrivals_next[s]:
                    for k in range(4): add[k] += vec[k]
                self.arrivals_next[s].clear()
                for k in range(4): self.stock[s][k] += add[k]

        # 2) RECOMPUTE_STATE_SNAPSHOTS (flags derived from stock)
        stage = self.detect_stage()
        
        # Update operational flags after launching operations
        for s in range(self.M):
            self.op[s] = is_ops_capable(_row_to_spoke(self.stock[s]))
        
        actions_this_period: List[Tuple[str,str]] = []
        pairs_used = set()  # ensure unique pair per period across all aircraft
        
        # 2.5) LAUNCH OPERATIONS IMMEDIATELY when spokes are operational
        for s in range(self.M):
            if is_ops_capable(_row_to_spoke(self.stock[s])):
                # Launch operation if this spoke is operational
                self.run_op(s)
                actions_this_period.append((f"SPOKE{s+1}", "OPERATION LAUNCHED"))

        # 3) Aircraft actions
        for ac in sorted(self.fleet, key=lambda a: (-a.cap, a.name)):
            if ac.rest_cooldown > 0:
                actions_this_period.append((ac.name, "REST at HUB"))
                ac.rest_cooldown -= 1
                continue

            events = 0
            def consume_event():
                nonlocal events, ac
                events += 1
                if events == 1:
                    ac.active_periods += 1

            # rest if due
            if ac.at_hub() and ac.active_periods >= ac.max_active_before_rest(self.cfg) and ac.state in ("IDLE","REST"):
                actions_this_period.append((ac.name, "INITIATE REST at HUB"))
                ac.active_periods = 0
                ac.rest_cooldown = 1
                continue

            # progress in-flight states
            if ac.state == "LEG1_ENROUTE":
                i = ac.plan[0] if ac.plan else 0
                ac.state = "AT_SPOKEA"
                ac.location = f"S{i+1}"
                continue
            elif ac.state == "AT_SPOKEA":
                i = ac.plan[0]
                self.arrivals_next[i].append(ac.payload_A[:])
                if is_ops_capable(_row_to_spoke(self.stock[i])):
                    self.run_op(i)
                actions_this_period.append((ac.name, f"OFFLOAD@S{i+1}"))
                ac.payload_A = [0,0,0,0]
                consume_event()
                if events < 2:
                    if ac.plan[1] is not None:
                        j = ac.plan[1]
                        ac.state = "AT_SPOKEB_ENROUTE"
                        actions_this_period.append((ac.name, f"MOVE S{i+1}→S{j+1}"))
                        consume_event()
                    else:
                        ac.plan = None
                        ac.state = "RETURN_ENROUTE"
                        actions_this_period.append((ac.name, f"MOVE S{i+1}→HUB"))
                        consume_event()
                continue
            elif ac.state == "AT_SPOKEB_ENROUTE":
                j = ac.plan[1] if ac.plan else 0
                ac.state = "AT_SPOKEB"
                ac.location = f"S{j+1}"
                continue
            elif ac.state == "AT_SPOKEB":
                j = ac.plan[1]
                self.arrivals_next[j].append(ac.payload_B[:])
                if is_ops_capable(_row_to_spoke(self.stock[j])):
                    self.run_op(j)
                actions_this_period.append((ac.name, f"OFFLOAD@S{j+1}"))
                ac.payload_B = [0,0,0,0]
                consume_event()
                if events < 2:
                    ac.plan = None
                    ac.state = "RETURN_ENROUTE"
                    actions_this_period.append((ac.name, f"MOVE S{j+1}→HUB"))
                    consume_event()
                continue
            elif ac.state == "RETURN_ENROUTE":
                # Complete return flight in next period, not immediately
                # This allows the renderer to animate the return journey
                ac.location = "HUB"
                ac.state = "IDLE"
                continue

            # new sortie
            if ac.at_hub() and ac.state == "IDLE":
                if ac.active_periods >= ac.max_active_before_rest(self.cfg):
                    actions_this_period.append((ac.name, "INITIATE REST at HUB"))
                    ac.active_periods = 0
                    ac.rest_cooldown = 1
                    continue

                # Try smart targeting first if enabled
                if self.smart_targeting:
                    smart_route = self._plan_smart_route(ac, stage)
                    if smart_route:
                        route, payload_A, payload_B = smart_route
                        i, j = route
                        
                        # Update aircraft plan and payload
                        ac.plan = route
                        ac.payload_A = payload_A[:]
                        ac.payload_B = payload_B[:]
                        
                        # Log actions
                        actions_this_period.append((ac.name, f"ONLOAD@HUB→S{i+1}"))
                        ac.state = "LEG1_ENROUTE"
                        actions_this_period.append((ac.name, f"MOVE HUB→S{i+1}"))
                        consume_event(); consume_event()
                        
                        # Update service tracking
                        self.smart_targeting.update_recent_service(i)
                        if j is not None:
                            self.smart_targeting.update_recent_service(j)
                        continue

                # Fall back to original pair-based planning
                tried = 0
                cursor = self.pair_cursor
                chosen_pair = None
                while tried < len(self.PAIR_ORDER):
                    i, j = self.PAIR_ORDER[cursor]
                    p_i, p_j = self.plan_for_pair_stage(i, j, ac.cap, stage)
                    key = (i, j if p_j and sum(p_j)>0 else -1)
                    if (sum(p_i) + sum(p_j)) > 0 and key not in pairs_used:
                        chosen_pair = (i, j)
                        break
                    cursor = (cursor + 1) % len(self.PAIR_ORDER)
                    tried += 1

                if chosen_pair is None:
                    continue

                i, j = chosen_pair
                p_i, p_j = self.plan_for_pair_stage(i, j, ac.cap, stage)
                if sum(p_i) == 0 and sum(p_j) == 0:
                    continue
                leg2_none = False
                if sum(p_j) == 0:
                    chosen_pair = (i, None)
                    leg2_none = True

                key = (i, (j if not leg2_none else -1))
                pairs_used.add(key)
                self.pair_cursor = (cursor + 1) % len(self.PAIR_ORDER)

                ac.plan = chosen_pair
                ac.payload_A = p_i[:]
                ac.payload_B = p_j[:] if not leg2_none else [0,0,0,0]
                actions_this_period.append((ac.name, f"ONLOAD@HUB→S{i+1}"))
                ac.state = "LEG1_ENROUTE"
                actions_this_period.append((ac.name, f"MOVE HUB→S{i+1}"))
                consume_event(); consume_event()

        # 4) PM_CONSUMPTION
        if self.t % 2 == 1:
            self.day = self.t // 2
            if (self.day % self.A_PERIOD_DAYS) == (self.A_PERIOD_DAYS - 1):
                for s in range(self.M):
                    if self.stock[s][0] > 0 and self.stock[s][1] > 0:
                        self.stock[s][0] = max(0, self.stock[s][0] - 1)
            if (self.day % self.B_PERIOD_DAYS) == (self.B_PERIOD_DAYS - 1):
                for s in range(self.M):
                    if self.stock[s][0] > 0 and self.stock[s][1] > 0:
                        self.stock[s][1] = max(0, self.stock[s][1] - 1)

        # Note: Operational flags are already updated earlier in the method

        self.check_invariants(pre_stock, ops_before)
        self.actions_log.append(actions_this_period)
        self.t += 1
        self.half = "AM" if self.t % 2 == 0 else "PM"
        self.ops_total_history.append(sum(self.ops_by_spoke))
        if len(self.ops_total_history) > 2000:
            self.ops_total_history = self.ops_total_history[-2000:]

        self.push_snapshot()

        if self.cfg.debug_mode:
            from .utils import append_debug
            lines = [f"[t={self.t} {self.half} day={self.t//2}] ops={self.ops_count()}"]
            lines += [f"  {nm}: {act}" for (nm, act) in actions_this_period]
            append_debug(lines)

        # Progress check to prevent infinite loops
        current_ops_total = sum(self.ops_by_spoke)
        if current_ops_total == pre_ops_total and len(actions_this_period) == 0:
            # No progress made this period, check if we need to intervene
            if self.t > 1:  # Skip this check for the first few periods to allow startup
                # Only force action if we've been stuck for multiple periods
                if not hasattr(self, '_stuck_periods'):
                    self._stuck_periods = 0
                self._stuck_periods += 1
                
                if self._stuck_periods >= 3:  # Only force action after 3 stuck periods
                    # Force at least one aircraft to move to prevent deadlock
                    for ac in self.fleet:
                        if ac.at_hub() and ac.state == "IDLE":
                            ac.state = "LEG1_ENROUTE"
                            ac.plan = (0, None)
                            ac.payload_A = [1, 1, 0, 0]
                            actions_this_period.append((ac.name, "FORCED MOVE HUB→S1"))
                            break
            else:
                # Reset stuck counter for early periods
                if hasattr(self, '_stuck_periods'):
                    self._stuck_periods = 0
        else:
            # Reset stuck counter when progress is made
            if hasattr(self, '_stuck_periods'):
                self._stuck_periods = 0

        # Smart targeting cleanup and maintenance
        if self.smart_targeting:
            self.smart_targeting.clear_period_reservations()
            self.smart_targeting.decay_recent_service()

        # Initialize distance cache for performance optimization
        self._initialize_distance_cache()

        return actions_this_period

    def apply_special_capability_effects(self, aircraft: Aircraft):
        """Apply special capability effects to aircraft operations."""
        if not hasattr(aircraft, 'special_capabilities'):
            return
        
        effects = {}
        
        for capability in aircraft.special_capabilities:
            if capability == "tactical":
                # Tactical aircraft can operate in more challenging conditions
                effects["operational_threshold"] = 0.5  # Lower resource threshold
            elif capability == "fuel_efficient":
                # Fuel efficient aircraft have longer range
                effects["range_multiplier"] = 1.2
            elif capability == "high_capacity":
                # High capacity aircraft can carry more cargo
                effects["capacity_multiplier"] = 1.3
            elif capability == "all_weather":
                # All-weather aircraft are more reliable
                effects["reliability_multiplier"] = 1.15
            elif capability == "short_field":
                # Short field aircraft can operate from smaller runways
                effects["field_requirement"] = "short"
            elif capability == "long_range":
                # Long range aircraft can reach further destinations
                effects["range_multiplier"] = 1.4
            elif capability == "night_ops":
                # Night operations capability
                effects["night_ops"] = True
            elif capability == "rough_field":
                # Rough field capability
                effects["rough_field"] = True
        
        self.special_capability_effects[aircraft.name] = effects

    def ops_count(self) -> int:
        return sum(self.op)

    def check_invariants(self, pre_stock, ops_before):
        violations: List[str] = []
        for s in range(self.M):
            row = self.stock[s]
            assert all(v >= -1e-9 for v in row)
            hud_flag = is_ops_capable(_row_to_spoke(row))
            node_flag = self.op[s]
            if hud_flag != node_flag:
                violations.append(f"ops-cap mismatch at S{s+1}")
            if self.ops_by_spoke[s] > ops_before[s]:
                delta_c = pre_stock[s][2] - row[2]
                delta_d = pre_stock[s][3] - row[3]
                delta_ops = self.ops_by_spoke[s] - ops_before[s]
                if not (delta_c >= delta_ops - 1e-6 and delta_d >= delta_ops - 1e-6):
                    violations.append(f"C/D not consumed for ops at S{s+1}")
        self.integrity_violations = violations
        if violations and not self._integrity_logged:
            from .utils import append_debug
            append_debug(["Integrity violations:"] + violations)
            self._integrity_logged = True

    def _initialize_distance_cache(self) -> None:
        """Initialize distance lookup table for performance optimization."""
        self._distance_cache = {}
        
        # Pre-calculate common distances
        locations = ["HUB"] + [f"S{i+1}" for i in range(self.M)]
        
        for from_loc in locations:
            for to_loc in locations:
                if from_loc == to_loc:
                    self._distance_cache[(from_loc, to_loc)] = 0.0
                else:
                    # Get coordinates for both locations first
                    from_coords = self._get_location_coordinates(from_loc)
                    to_coords = self._get_location_coordinates(to_loc)
                    
                    if from_coords and to_coords:
                        distance = self._calculate_distance(from_coords, to_coords)
                        self._distance_cache[(from_loc, to_loc)] = distance
                    else:
                        # Handle case where coordinates couldn't be determined
                        self._distance_cache[(from_loc, to_loc)] = float('inf')
    
    def _get_cached_distance(self, from_location: str, to_location: str) -> float:
        """Get cached distance between two locations.
        
        Args:
            from_location: Starting location
            to_location: Destination location
            
        Returns:
            Cached distance in miles
        """
        # Initialize cache if not exists
        if not hasattr(self, '_distance_cache'):
            self._initialize_distance_cache()
        
        # Check cache first
        cache_key = (from_location, to_location)
        if cache_key in self._distance_cache:
            return self._distance_cache[cache_key]
        
        # Calculate and cache if not found
        from_coords = self._get_location_coordinates(from_location)
        to_coords = self._get_location_coordinates(to_location)
        
        if from_coords and to_coords:
            distance = self._calculate_distance(from_coords, to_coords)
            self._distance_cache[cache_key] = distance
            return distance
        else:
            return float('inf')
    
    def _optimize_time_step(self, delta_hours: float) -> float:
        """Optimize time step to minimize floating-point errors.
        
        Args:
            delta_hours: Proposed time increment
            
        Returns:
            Optimized time increment
        """
        # Validate time step
        if delta_hours <= 0.0:
            return 0.0
        
        # Limit time step to prevent large jumps
        max_time_step = 6.0  # Maximum 6 hours per step
        if delta_hours > max_time_step:
            delta_hours = max_time_step
        
        # Round to reasonable precision to minimize floating-point errors
        # Use 0.1 hour (6 minute) precision
        precision = 0.1
        delta_hours = round(delta_hours / precision) * precision
        
        return delta_hours
    
    def _monitor_memory_usage(self) -> None:
        """Monitor memory usage and perform cleanup if necessary."""
        import gc
        
        # Check if we have too many cost history entries
        if hasattr(self, 'cost_history') and len(self.cost_history) > 8000:
            # Keep only recent entries
            self.cost_history = self.cost_history[-4000:]
            gc.collect()  # Force garbage collection
        
        # Check if we have too many snapshots
        if hasattr(self, 'history') and len(self.history) > 1000:
            # Keep only recent snapshots
            self.history = self.history[-500:]
            gc.collect()  # Force garbage collection
        
        # Check if distance cache is too large
        if hasattr(self, '_distance_cache') and len(self._distance_cache) > 200:
            # Distance cache should be small, but if it grows, clear it
            self._distance_cache.clear()
            gc.collect()  # Force garbage collection

    def _initialize_advanced_features(self):
        """Initialize advanced simulation features."""
        # Initialize predictive analytics
        if self.predictive_analytics_enabled:
            self._initialize_predictive_analytics()
        
        # Initialize maintenance scheduling
        if self.maintenance_scheduling_enabled:
            self._initialize_maintenance_scheduling()
        
        # Initialize weather system if enabled
        if self.weather_considerations:
            self._initialize_weather_system()

    def _initialize_predictive_analytics(self):
        """Initialize predictive analytics system."""
        self.demand_forecast = {}
        self.maintenance_prediction = {}
        self.cost_projection = {}
        
        # Initialize forecasting models
        for spoke_idx in range(self.M):
            self.demand_forecast[spoke_idx] = {
                'A': {'trend': 0.0, 'seasonality': 0.0, 'confidence': 0.8},
                'B': {'trend': 0.0, 'seasonality': 0.0, 'confidence': 0.8},
                'C': {'trend': 0.0, 'seasonality': 0.0, 'confidence': 0.8},
                'D': {'trend': 0.0, 'seasonality': 0.0, 'confidence': 0.8}
            }

    def _initialize_maintenance_scheduling(self):
        """Initialize predictive maintenance scheduling."""
        self.maintenance_schedule = {}
        self.maintenance_history = {}
        
        for aircraft in self.fleet:
            self.maintenance_schedule[aircraft.name] = {
                'next_maintenance': 100.0,  # Hours until next maintenance
                'maintenance_type': 'routine',
                'priority': 'normal'
            }

    def _initialize_weather_system(self):
        """Initialize weather consideration system."""
        self.weather_conditions = {}
        self.weather_forecast = {}
        
        # Initialize weather for all locations
        locations = ['HUB'] + [f'S{i+1}' for i in range(self.M)]
        for location in locations:
            self.weather_conditions[location] = {
                'visibility': 'good',
                'wind_speed': 0.0,
                'turbulence': 'low',
                'impact_factor': 1.0
            }

    def optimize_route_multi_objective(self, start: str, end: str, aircraft: Aircraft) -> dict:
        """Multi-objective route optimization considering cost, time, and fuel efficiency."""
        if not self.advanced_routing_enabled:
            return self._simple_route_planning(start, end, aircraft)
        
        # Check cache first
        cache_key = f"{start}_{end}_{aircraft.typ}"
        if cache_key in self.route_cache:
            return self.route_cache[cache_key]
        
        # Calculate route options
        routes = self._calculate_route_options(start, end, aircraft)
        
        if not routes:
            return None
        
        # Multi-objective optimization
        best_route = self._evaluate_routes_multi_objective(routes, aircraft)
        
        # Cache result
        self.route_cache[cache_key] = best_route
        
        return best_route

    def _calculate_route_options(self, start: str, end: str, aircraft: Aircraft) -> List[dict]:
        """Calculate multiple route options between two points."""
        routes = []
        
        # Direct route
        direct_route = self._calculate_direct_route(start, end, aircraft)
        if direct_route:
            routes.append(direct_route)
        
        # Alternative routes (if applicable)
        if start != 'HUB' and end != 'HUB':
            # Via hub route
            hub_route = self._calculate_via_hub_route(start, end, aircraft)
            if hub_route:
                routes.append(hub_route)
        
        # Weather-affected routes
        if self.weather_considerations:
            weather_routes = self._calculate_weather_affected_routes(start, end, aircraft)
            routes.extend(weather_routes)
        
        return routes

    def _calculate_direct_route(self, start: str, end: str, aircraft: Aircraft) -> dict:
        """Calculate direct route between two points."""
        # Get coordinates (simplified - in real implementation, these would be actual coordinates)
        start_coords = self._get_location_coordinates(start)
        end_coords = self._get_location_coordinates(end)
        
        if not start_coords or not end_coords:
            return None
        
        # Calculate distance
        distance = self._calculate_distance(start_coords, end_coords)
        
        # Calculate flight time
        speed_mach = getattr(aircraft, 'speed_mach', 0.45)
        flight_time = distance / (speed_mach * 340.29)  # Mach to m/s conversion
        
        # Calculate fuel consumption
        fuel_consumption = self._calculate_fuel_consumption(distance, aircraft)
        
        # Calculate operational cost
        operational_cost = self._calculate_operational_cost(flight_time, aircraft)
        
        return {
            'type': 'direct',
            'start': start,
            'end': end,
            'distance': distance,
            'flight_time': flight_time,
            'fuel_consumption': fuel_consumption,
            'operational_cost': operational_cost,
            'total_cost': fuel_consumption + operational_cost,
            'efficiency_score': self._calculate_efficiency_score(distance, flight_time, fuel_consumption)
        }

    def _calculate_via_hub_route(self, start: str, end: str, aircraft: Aircraft) -> dict:
        """Calculate route via hub."""
        # Calculate start to hub
        start_hub = self._calculate_direct_route(start, 'HUB', aircraft)
        if not start_hub:
            return None
        
        # Calculate hub to end
        hub_end = self._calculate_direct_route('HUB', end, aircraft)
        if not hub_end:
            return None
        
        # Combine routes
        total_distance = start_hub['distance'] + hub_end['distance']
        total_flight_time = start_hub['flight_time'] + hub_end['flight_time']
        total_fuel = start_hub['fuel_consumption'] + hub_end['fuel_consumption']
        total_cost = start_hub['total_cost'] + hub_end['total_cost']
        
        return {
            'type': 'via_hub',
            'start': start,
            'end': end,
            'distance': total_distance,
            'flight_time': total_flight_time,
            'fuel_consumption': total_fuel,
            'operational_cost': start_hub['operational_cost'] + hub_end['operational_cost'],
            'total_cost': total_cost,
            'efficiency_score': self._calculate_efficiency_score(total_distance, total_flight_time, total_fuel)
        }

    def _calculate_weather_affected_routes(self, start: str, end: str, aircraft: Aircraft) -> List[dict]:
        """Calculate weather-affected route alternatives."""
        if not self.weather_considerations:
            return []
        
        routes = []
        
        # Check weather conditions
        start_weather = self.weather_conditions.get(start, {})
        end_weather = self.weather_conditions.get(end, {})
        
        # If weather is poor, calculate alternative routes
        if start_weather.get('visibility') == 'poor' or end_weather.get('visibility') == 'poor':
            # Calculate detour routes
            detour_routes = self._calculate_detour_routes(start, end, aircraft)
            routes.extend(detour_routes)
        
        return routes

    def _calculate_detour_routes(self, start: str, end: str, aircraft: Aircraft) -> List[dict]:
        """Calculate detour routes to avoid poor weather."""
        # This is a simplified implementation
        # In a real system, this would use actual weather data and routing algorithms
        
        detour_routes = []
        
        # Find intermediate points that could serve as detours
        intermediate_points = [f'S{i+1}' for i in range(self.M) if f'S{i+1}' not in [start, end]]
        
        for intermediate in intermediate_points[:2]:  # Limit to 2 detour options
            # Calculate route via intermediate point
            route_via_intermediate = self._calculate_via_point_route(start, end, intermediate, aircraft)
            if route_via_intermediate:
                detour_routes.append(route_via_intermediate)
        
        return detour_routes

    def _calculate_via_point_route(self, start: str, end: str, via: str, aircraft: Aircraft) -> dict:
        """Calculate route via an intermediate point."""
        # Calculate start to intermediate
        start_via = self._calculate_direct_route(start, via, aircraft)
        if not start_via:
            return None
        
        # Calculate intermediate to end
        via_end = self._calculate_direct_route(via, end, aircraft)
        if not via_end:
            return None
        
        # Combine routes
        total_distance = start_via['distance'] + via_end['distance']
        total_flight_time = start_via['flight_time'] + via_end['flight_time']
        total_fuel = start_via['fuel_consumption'] + via_end['fuel_consumption']
        total_cost = start_via['total_cost'] + via_end['total_cost']
        
        return {
            'type': f'via_{via}',
            'start': start,
            'end': end,
            'via': via,
            'distance': total_distance,
            'flight_time': total_flight_time,
            'fuel_consumption': total_fuel,
            'operational_cost': start_via['operational_cost'] + via_end['operational_cost'],
            'total_cost': total_cost,
            'efficiency_score': self._calculate_efficiency_score(total_distance, total_flight_time, total_fuel)
        }

    def _evaluate_routes_multi_objective(self, routes: List[dict], aircraft: Aircraft) -> dict:
        """Evaluate routes using multi-objective optimization."""
        if not routes:
            return None
        
        # Normalize scores for each objective
        normalized_routes = self._normalize_route_scores(routes)
        
        # Calculate weighted scores
        weights = {
            'cost': 0.4,
            'time': 0.3,
            'efficiency': 0.3
        }
        
        for route in normalized_routes:
            route['weighted_score'] = (
                weights['cost'] * route['normalized_cost'] +
                weights['time'] * route['normalized_time'] +
                weights['efficiency'] * route['normalized_efficiency']
            )
        
        # Return best route
        best_route = min(normalized_routes, key=lambda x: x['weighted_score'])
        
        # Store optimization history
        self.optimization_history.append({
            'timestamp': self.current_time_hours,
            'aircraft': aircraft.name,
            'start': best_route['start'],
            'end': best_route['end'],
            'selected_route': best_route['type'],
            'score': best_route['weighted_score']
        })
        
        return best_route

    def _normalize_route_scores(self, routes: List[dict]) -> List[dict]:
        """Normalize route scores for multi-objective comparison."""
        if not routes:
            return []
        
        # Extract values for normalization
        costs = [r['total_cost'] for r in routes]
        times = [r['flight_time'] for r in routes]
        efficiencies = [r['efficiency_score'] for r in routes]
        
        # Calculate min/max for normalization
        min_cost, max_cost = min(costs), max(costs)
        min_time, max_time = min(times), max(times)
        min_eff, max_eff = min(efficiencies), max(efficiencies)
        
        normalized_routes = []
        for route in routes:
            # Normalize to 0-1 scale (lower is better for cost and time, higher is better for efficiency)
            normalized_cost = (route['total_cost'] - min_cost) / (max_cost - min_cost) if max_cost > min_cost else 0.5
            normalized_time = (route['flight_time'] - min_time) / (max_time - min_time) if max_time > min_time else 0.5
            normalized_efficiency = (route['efficiency_score'] - min_eff) / (max_eff - min_eff) if max_eff > min_eff else 0.5
            
            # Invert cost and time so lower values are better
            normalized_cost = 1.0 - normalized_cost
            normalized_time = 1.0 - normalized_time
            
            normalized_routes.append({
                **route,
                'normalized_cost': normalized_cost,
                'normalized_time': normalized_time,
                'normalized_efficiency': normalized_efficiency
            })
        
        return normalized_routes

    def _calculate_efficiency_score(self, distance: float, flight_time: float, fuel_consumption: float) -> float:
        """Calculate efficiency score for a route."""
        if flight_time <= 0 or fuel_consumption <= 0:
            return 0.0
        
        # Efficiency = distance / (fuel_consumption * flight_time)
        # Higher values indicate better efficiency
        efficiency = distance / (fuel_consumption * flight_time)
        
        # Normalize to 0-1 scale
        return min(1.0, efficiency / 1000.0)  # Arbitrary normalization factor

    def _get_location_coordinates(self, location: str) -> Optional[Tuple[float, float]]:
        """Get coordinates for a location."""
        try:
            if not isinstance(location, str):
                return None
                
            if location == 'HUB':
                return (0.0, 0.0)  # Hub at origin
            
            if location.startswith('S'):
                try:
                    # Ensure self.M is properly initialized
                    if not hasattr(self, 'M') or self.M <= 0:
                        # Fallback to default value if M is not properly set
                        self.M = 10
                    
                    # Extract spoke number and validate
                    spoke_str = location[1:]
                    if not spoke_str.isdigit():
                        return None
                        
                    spoke_idx = int(spoke_str) - 1
                    if 0 <= spoke_idx < self.M:
                        # Calculate spoke position in a circle around hub
                        angle = 2 * math.pi * spoke_idx / self.M
                        radius = 100.0  # Arbitrary radius
                        x = radius * math.cos(angle)
                        y = radius * math.sin(angle)
                        return (x, y)
                except (ValueError, AttributeError, TypeError, IndexError):
                    pass
            
            return None
        except Exception:
            return None

    def _calculate_distance(self, coord1: Tuple[float, float], coord2: Tuple[float, float]) -> float:
        """Calculate Euclidean distance between two coordinates."""
        try:
            # Ensure coordinates are valid tuples of numbers
            if (not isinstance(coord1, tuple) or not isinstance(coord2, tuple) or
                len(coord1) != 2 or len(coord2) != 2 or
                not isinstance(coord1[0], (int, float)) or not isinstance(coord1[1], (int, float)) or
                not isinstance(coord2[0], (int, float)) or not isinstance(coord2[1], (int, float))):
                return 0.0
            
            dx = coord2[0] - coord1[0]
            dy = coord2[1] - coord1[1]
            return math.sqrt(dx * dx + dy * dy)
        except (TypeError, ValueError, AttributeError):
            # Return 0.0 for any calculation errors
            return 0.0

    def _calculate_fuel_consumption(self, distance: float, aircraft: Aircraft) -> float:
        """Calculate fuel consumption for a flight."""
        base_consumption = getattr(aircraft, 'fuel_consumption_rate', 1.0)
        
        # Base fuel consumption per km
        fuel_per_km = 0.1  # Arbitrary value
        
        # Apply aircraft-specific modifiers
        if aircraft.typ == "C-130":
            fuel_per_km *= 1.2  # C-130 uses more fuel
        elif aircraft.typ == "C-27":
            fuel_per_km *= 0.8  # C-27 is more fuel efficient
        
        # Apply fuel price volatility
        fuel_price_modifier = 1.0 + (self.fuel_price_volatility * self.fuel_price_trend)
        
        return distance * fuel_per_km * base_consumption * fuel_price_modifier

    def _calculate_operational_cost(self, flight_time: float, aircraft: Aircraft) -> float:
        """Calculate operational cost for a flight."""
        # Base operational cost per hour
        base_cost_per_hour = 1000.0  # Arbitrary value
        
        # Apply aircraft-specific modifiers
        if aircraft.typ == "C-130":
            base_cost_per_hour *= 1.5  # C-130 is more expensive to operate
        elif aircraft.typ == "C-27":
            base_cost_per_hour *= 1.0  # C-27 baseline
        
        # Calculate total operational cost
        operational_cost = flight_time * base_cost_per_hour
        
        # Add maintenance cost if approaching maintenance threshold
        if hasattr(aircraft, 'total_flight_hours'):
            maintenance_ratio = aircraft.total_flight_hours / 1000.0  # Arbitrary threshold
            if maintenance_ratio > self.predictive_maintenance_threshold:
                maintenance_multiplier = 1.0 + (maintenance_ratio - self.predictive_maintenance_threshold) * 2.0
                operational_cost *= maintenance_multiplier
        
        return operational_cost

    def _simple_route_planning(self, start: str, end: str, aircraft: Aircraft) -> dict:
        """Simple route planning fallback."""
        # Basic route calculation without advanced features
        start_coords = self._get_location_coordinates(start)
        end_coords = self._get_location_coordinates(end)
        
        if not start_coords or not end_coords:
            return None
        
        distance = self._calculate_distance(start_coords, end_coords)
        speed_mach = getattr(aircraft, 'speed_mach', 0.45)
        flight_time = distance / (speed_mach * 340.29)
        
        return {
            'type': 'simple',
            'start': start,
            'end': end,
            'distance': distance,
            'flight_time': flight_time,
            'fuel_consumption': self._calculate_fuel_consumption(distance, aircraft),
            'operational_cost': self._calculate_operational_cost(flight_time, aircraft),
            'total_cost': 0.0,  # Will be calculated
            'efficiency_score': 0.5  # Default score
        }

    def update_advanced_features(self, delta_time: float):
        """Update advanced simulation features."""
        # Update fuel price trends
        self._update_fuel_prices(delta_time)
        
        # Update weather conditions
        if self.weather_considerations:
            self._update_weather_conditions(delta_time)
        
        # Update predictive analytics
        if self.predictive_analytics_enabled:
            self._update_predictive_analytics(delta_time)
        
        # Update maintenance scheduling
        if self.maintenance_scheduling_enabled:
            self._update_maintenance_scheduling(delta_time)
        
        # Update performance metrics
        self._update_performance_metrics(delta_time)

    def _update_fuel_prices(self, delta_time: float):
        """Update fuel prices with volatility and trends."""
        # Simulate fuel price changes
        price_change = (random.random() - 0.5) * 2.0 * self.fuel_price_volatility
        self.fuel_price_trend += price_change * delta_time / 24.0  # Daily changes
        
        # Limit trend to reasonable bounds
        self.fuel_price_trend = max(-0.5, min(0.5, self.fuel_price_trend))

    def _update_weather_conditions(self, delta_time: float):
        """Update weather conditions for all locations."""
        # Simplified weather simulation
        for location in self.weather_conditions:
            # Random weather changes
            if random.random() < 0.01:  # 1% chance of weather change per update
                visibility_options = ['good', 'fair', 'poor']
                self.weather_conditions[location]['visibility'] = random.choice(visibility_options)
                
                # Update impact factor
                if self.weather_conditions[location]['visibility'] == 'poor':
                    self.weather_conditions[location]['impact_factor'] = 1.5
                else:
                    self.weather_conditions[location]['impact_factor'] = 1.0

    def _update_predictive_analytics(self, delta_time: float):
        """Update predictive analytics models."""
        # Update demand forecasting
        for spoke_idx in range(self.M):
            for resource in ['A', 'B', 'C', 'D']:
                # Simulate demand changes
                current_stock = self.stock[spoke_idx][['A', 'B', 'C', 'D'].index(resource)]
                
                # Simple trend calculation
                if len(self.history) > 1:
                    prev_stock = self.history[-2]['stock'][spoke_idx][['A', 'B', 'C', 'D'].index(resource)]
                    trend = (current_stock - prev_stock) / delta_time
                    self.demand_forecast[spoke_idx][resource]['trend'] = trend

    def _update_maintenance_scheduling(self, delta_time: float):
        """Update predictive maintenance scheduling."""
        for aircraft in self.fleet:
            if aircraft.name in self.maintenance_schedule:
                schedule = self.maintenance_schedule[aircraft.name]
                
                # Update maintenance countdown
                if hasattr(aircraft, 'total_flight_hours'):
                    schedule['next_maintenance'] = max(0.0, schedule['next_maintenance'] - delta_time)
                    
                    # Check if maintenance is needed
                    if schedule['next_maintenance'] <= 0.0:
                        schedule['maintenance_type'] = 'urgent'
                        schedule['priority'] = 'high'
                    elif schedule['next_maintenance'] <= 50.0:  # 50 hours warning
                        schedule['maintenance_type'] = 'scheduled'
                        schedule['priority'] = 'medium'

    def _update_performance_metrics(self, delta_time: float):
        """Update performance metrics."""
        # Calculate operations per second
        if delta_time > 0:
            self.performance_metrics['operations_per_second'] = len(self.actions_log) / delta_time
        
        # Calculate efficiency ratio
        if self.total_operational_cost > 0:
            self.performance_metrics['efficiency_ratio'] = len(self.actions_log) / self.total_operational_cost
        
        # Calculate resource utilization
        active_aircraft = len([ac for ac in self.fleet if ac.state != "IDLE"])
        self.performance_metrics['resource_utilization'] = active_aircraft / len(self.fleet) if self.fleet else 0.0
        
        # Calculate cost per operation
        if len(self.actions_log) > 0:
            total_cost = self.total_operational_cost + self.total_fuel_cost + self.total_maintenance_cost
            self.performance_metrics['cost_per_operation'] = total_cost / len(self.actions_log)
        
        # Calculate route optimization score
        if self.optimization_history:
            recent_optimizations = [opt for opt in self.optimization_history 
                                  if opt['timestamp'] > self.current_time_hours - 24.0]  # Last 24 hours
            if recent_optimizations:
                avg_score = sum(opt['score'] for opt in recent_optimizations) / len(recent_optimizations)
                self.performance_metrics['route_optimization_score'] = avg_score

    def get_advanced_features_status(self) -> dict:
        """Get status of advanced simulation features."""
        return {
            'advanced_routing': self.advanced_routing_enabled,
            'multi_objective_optimization': self.multi_objective_optimization,
            'predictive_analytics': self.predictive_analytics_enabled,
            'weather_considerations': self.weather_considerations,
            'traffic_management': self.traffic_management,
            'maintenance_scheduling': self.maintenance_scheduling_enabled,
            'performance_metrics': self.performance_metrics.copy(),
            'route_cache_size': len(self.route_cache),
            'optimization_history_size': len(self.optimization_history)
        }

    def _calculate_coordinate_distance(self, coord1: Tuple[float, float], coord2: Tuple[float, float]) -> float:
        """Calculate Euclidean distance between two coordinates."""
        dx = coord2[0] - coord1[0]
        dy = coord2[1] - coord1[1]
        return math.sqrt(dx * dx + dy * dy)
