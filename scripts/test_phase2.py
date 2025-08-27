#!/usr/bin/env python3
"""Test script for Phase 2: Simulation Logic Overhaul."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from cargosim.core.simulation import LogisticsSim, Aircraft
from cargosim.core.config import SimConfig


def test_time_based_movement_system():
    """Test Task 2.1: Time-Based Movement System."""
    print("Testing Time-Based Movement System...")
    
    # Create simulation with time mechanics
    config = SimConfig()
    sim = LogisticsSim(config)
    
    # Test current_time_hours initialization
    assert sim.current_time_hours == 0.0, "current_time_hours should initialize to 0.0"
    print("✓ current_time_hours initialized correctly")
    
    # Test calculate_flight_time
    aircraft = Aircraft("C-130", 4, "Test Aircraft")
    sim._initialize_aircraft_attributes(aircraft)
    
    flight_time = sim.calculate_flight_time("HUB", "S1", aircraft)
    assert flight_time > 0, "Flight time should be positive"
    print(f"✓ Flight time calculation: HUB to S1 = {flight_time:.2f} hours")
    
    # Test update_simulation_time
    sim.update_simulation_time(6.0)  # 6 hours
    assert sim.current_time_hours == 6.0, "Simulation time should update correctly"
    print("✓ Simulation time update working")
    
    # Test period boundary maintenance
    sim.update_simulation_time(6.0)  # Total 12 hours = 1 period
    assert sim.t == 1, "Period should increment after 12 hours"
    print("✓ Period boundary maintenance working")
    
    print("Time-Based Movement System: PASSED\n")


def test_aircraft_state_machine():
    """Test Task 2.2: Aircraft State Machine Enhancement."""
    print("Testing Aircraft State Machine Enhancement...")
    
    # Create aircraft and test new state methods
    aircraft = Aircraft("C-130", 4, "Test Aircraft")
    sim = LogisticsSim(SimConfig())
    sim._initialize_aircraft_attributes(aircraft)
    
    # Test set_enroute_state
    aircraft.set_enroute_state(2.5)
    assert aircraft.state == "ENROUTE", "State should be ENROUTE"
    assert aircraft.time_remaining == 2.5, "Time remaining should be set"
    print("✓ set_enroute_state working")
    
    # Test set_loading_state
    aircraft.set_loading_state(1.0)
    assert aircraft.state == "LOADING", "State should be LOADING"
    assert aircraft.loading_time_remaining == 1.0, "Loading time should be set"
    print("✓ set_loading_state working")
    
    # Test set_maintenance_state
    aircraft.set_maintenance_state(3.0)
    assert aircraft.state == "MAINTENANCE", "State should be MAINTENANCE"
    assert aircraft.maintenance_time_remaining == 3.0, "Maintenance time should be set"
    print("✓ set_maintenance_state working")
    
    # Test is_time_based_state
    assert aircraft.is_time_based_state(), "Aircraft should be in time-based state"
    print("✓ is_time_based_state working")
    
    # Test update_time_remaining
    aircraft.set_enroute_state(2.0)
    should_transition = aircraft.update_time_remaining(1.0)
    assert not should_transition, "Should not transition after 1 hour"
    assert aircraft.time_remaining == 1.0, "Time remaining should be updated"
    
    should_transition = aircraft.update_time_remaining(1.5)
    assert should_transition, "Should transition after completing flight"
    print("✓ update_time_remaining working")
    
    print("Aircraft State Machine Enhancement: PASSED\n")


def test_cost_calculation_system():
    """Test Task 2.3: Cost Calculation System."""
    print("Testing Cost Calculation System...")
    
    config = SimConfig()
    sim = LogisticsSim(config)
    aircraft = Aircraft("C-130", 4, "Test Aircraft")
    sim._initialize_aircraft_attributes(aircraft)
    
    # Test operational cost calculation
    operational_cost = sim.calculate_operational_cost(aircraft, 5.0)
    assert operational_cost > 0, "Operational cost should be positive"
    print(f"✓ Operational cost: ${operational_cost:.2f}")
    
    # Test fuel cost calculation
    fuel_cost = sim.calculate_fuel_cost(aircraft, 5.0)
    assert fuel_cost > 0, "Fuel cost should be positive"
    print(f"✓ Fuel cost: ${fuel_cost:.2f}")
    
    # Test maintenance cost calculation
    maintenance_cost = sim.calculate_maintenance_cost(aircraft, 5.0)
    assert maintenance_cost > 0, "Maintenance cost should be positive"
    print(f"✓ Maintenance cost: ${maintenance_cost:.2f}")
    
    # Test total cost calculation
    total_cost = sim.calculate_total_aircraft_cost(aircraft, 5.0)
    expected_total = operational_cost + fuel_cost + maintenance_cost
    assert abs(total_cost - expected_total) < 0.01, "Total cost should match sum of components"
    print(f"✓ Total cost: ${total_cost:.2f}")
    
    # Test cost tracking
    sim.update_aircraft_costs(aircraft, 5.0)
    assert sim.total_operational_cost > 0, "Total operational cost should be tracked"
    assert sim.total_fuel_cost > 0, "Total fuel cost should be tracked"
    assert sim.total_maintenance_cost > 0, "Total maintenance cost should be tracked"
    print("✓ Cost tracking working")
    
    # Test cost summary
    cost_summary = sim.get_cost_summary()
    assert 'total_cost' in cost_summary, "Cost summary should include total cost"
    print(f"✓ Cost summary: {cost_summary}")
    
    print("Cost Calculation System: PASSED\n")


def test_flight_planning_and_routing():
    """Test Task 2.4: Flight Planning and Routing."""
    print("Testing Flight Planning and Routing...")
    
    config = SimConfig()
    sim = LogisticsSim(config)
    aircraft = Aircraft("C-130", 4, "Test Aircraft")
    sim._initialize_aircraft_attributes(aircraft)
    
    # Test calculate_optimal_route
    distance, flight_time = sim.calculate_optimal_route("HUB", "S1", aircraft)
    assert distance > 0, "Distance should be positive"
    assert flight_time > 0, "Flight time should be positive"
    print(f"✓ Optimal route: {distance:.1f} miles, {flight_time:.2f} hours")
    
    # Test route validation
    is_valid = sim._validate_route_range(distance, aircraft)
    assert is_valid, "Route should be valid for C-130"
    print("✓ Route validation working")
    
    # Test distance calculation with caching
    distance1 = sim._calculate_distance_from_locations("HUB", "S1")
    distance2 = sim._calculate_distance_from_locations("HUB", "S1")
    assert distance1 == distance2, "Cached distances should be consistent"
    print("✓ Distance caching working")
    
    print("Flight Planning and Routing: PASSED\n")


def test_performance_optimization():
    """Test Task 2.5: Performance Optimization."""
    print("Testing Performance Optimization...")
    
    config = SimConfig()
    sim = LogisticsSim(config)
    
    # Test time step optimization
    optimized_step = sim._optimize_time_step(8.0)
    assert optimized_step <= 6.0, "Time step should be limited to 6 hours"
    print(f"✓ Time step optimization: 8.0 -> {optimized_step:.1f}")
    
    # Test memory monitoring
    sim._monitor_memory_usage()
    print("✓ Memory monitoring working")
    
    # Test distance cache initialization
    assert hasattr(sim, '_distance_cache'), "Distance cache should be initialized"
    print("✓ Distance cache initialization working")
    
    print("Performance Optimization: PASSED\n")


def test_integration():
    """Test integration of all Phase 2 features."""
    print("Testing Phase 2 Integration...")
    
    config = SimConfig()
    sim = LogisticsSim(config)
    
    # Test complete workflow
    aircraft = Aircraft("C-130", 4, "Test Aircraft")
    sim._initialize_aircraft_attributes(aircraft)
    
    # Set up a mission - aircraft starts at HUB
    aircraft.location = "HUB"
    aircraft.plan = (0, None)  # HUB -> S1 -> HUB
    aircraft.set_enroute_state(2.0)
    
    # Add aircraft to simulation fleet so it gets processed
    sim.fleet.append(aircraft)
    
    # Simulate time progression
    sim.update_simulation_time(2.0)
    
    # Check that aircraft completed flight leg
    assert aircraft.state != "ENROUTE", "Aircraft should have completed flight leg"
    print("✓ Complete workflow: Aircraft state transition working")
    
    # Test cost tracking over time
    sim.update_aircraft_costs(aircraft, 2.0)
    total_cost = sim.get_total_simulation_cost()
    assert total_cost > 0, "Total cost should be tracked over time"
    print(f"✓ Complete workflow: Cost tracking working (Total: ${total_cost:.2f})")
    
    print("Phase 2 Integration: PASSED\n")


def main():
    """Run all Phase 2 tests."""
    print("=" * 60)
    print("PHASE 2: SIMULATION LOGIC OVERHAUL - TESTING")
    print("=" * 60)
    
    try:
        test_time_based_movement_system()
        test_aircraft_state_machine()
        test_cost_calculation_system()
        test_flight_planning_and_routing()
        test_performance_optimization()
        test_integration()
        
        print("=" * 60)
        print("ALL PHASE 2 TESTS PASSED! ✓")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
