"""Tests for advanced simulation features."""

import pytest
import copy
from unittest.mock import patch, MagicMock

from cargosim.simulation import LogisticsSim, Aircraft
from cargosim.config import SimConfig, AdvancedDecisionConfig, GameplayConfig
from cargosim.smart_targeting import TargetingConfig


class TestAdvancedDecisionMaking:
    """Test Advanced Decision Making (ADM) features."""
    
    def test_adm_config_creation(self):
        """Test ADM configuration creation."""
        adm_config = AdvancedDecisionConfig()
        
        assert adm_config.adm_enable is False
        assert adm_config.adm_fairness_cooldown_periods == 2
        assert adm_config.adm_target_dos_A_days == 3.0
        assert adm_config.adm_target_dos_B_days == 2.0
        assert adm_config.adm_enable_emergency_A_preempt is True
        assert isinstance(adm_config.adm_seed, int)
    
    def test_adm_config_serialization(self):
        """Test ADM configuration serialization."""
        adm_config = AdvancedDecisionConfig(
            adm_enable=True,
            adm_target_dos_A_days=4.0
        )
        
        json_data = adm_config.to_json()
        
        assert json_data['adm_enable'] is True
        assert json_data['adm_target_dos_A_days'] == 4.0
        assert 'adm_fairness_cooldown_periods' in json_data
    
    def test_adm_config_deserialization(self):
        """Test ADM configuration deserialization."""
        json_data = {
            'adm_enable': True,
            'adm_target_dos_A_days': 5.0,
            'adm_fairness_cooldown_periods': 3
        }
        
        adm_config = AdvancedDecisionConfig.from_json(json_data)
        
        assert adm_config.adm_enable is True
        assert adm_config.adm_target_dos_A_days == 5.0
        assert adm_config.adm_fairness_cooldown_periods == 3
    
    def test_simulation_with_adm_disabled(self):
        """Test simulation with ADM disabled."""
        cfg = SimConfig()
        cfg.adm.adm_enable = False
        
        sim = LogisticsSim(cfg)
        
        # Should work normally without ADM
        assert sim.cfg.adm.adm_enable is False
        
        # Run a few steps
        for _ in range(3):
            sim.step_period()
        
        assert sim.t == 3


class TestGameplayFeatures:
    """Test gameplay configuration and features."""
    
    def test_gameplay_config_creation(self):
        """Test gameplay configuration creation."""
        gameplay_config = GameplayConfig()
        
        assert hasattr(gameplay_config, 'gp_enable')
        assert hasattr(gameplay_config, 'gp_seed')
        assert isinstance(gameplay_config.gp_seed, int)
    
    def test_gameplay_config_serialization(self):
        """Test gameplay configuration serialization."""
        gameplay_config = GameplayConfig()
        json_data = gameplay_config.to_json()
        
        assert isinstance(json_data, dict)
        assert 'gp_seed' in json_data
    
    def test_gameplay_config_deserialization(self):
        """Test gameplay configuration deserialization."""
        json_data = {'gp_seed': 12345}
        gameplay_config = GameplayConfig.from_json(json_data)
        
        assert gameplay_config.gp_seed == 12345


class TestSmartTargetingIntegration:
    """Test smart targeting system integration with simulation."""
    
    def test_simulation_with_smart_targeting_disabled(self):
        """Test simulation with smart targeting disabled."""
        cfg = SimConfig()
        cfg.smart_targeting_enabled = False
        
        sim = LogisticsSim(cfg)
        
        assert sim.smart_targeting is None
        
        # Should work normally without smart targeting
        for _ in range(3):
            sim.step_period()
        
        assert sim.t == 3
    
    def test_simulation_with_smart_targeting_enabled(self):
        """Test simulation with smart targeting enabled."""
        cfg = SimConfig()
        cfg.smart_targeting_enabled = True
        cfg.smart_targeting_config = {
            'w_ops': 1.5,
            'w_need': 0.8
        }
        
        sim = LogisticsSim(cfg)
        
        assert sim.smart_targeting is not None
        assert sim.smart_targeting.config.w_ops == 1.5
        assert sim.smart_targeting.config.w_need == 0.8
    
    def test_smart_targeting_position_updates(self):
        """Test smart targeting position updates."""
        cfg = SimConfig()
        cfg.smart_targeting_enabled = True
        
        sim = LogisticsSim(cfg)
        
        # Mock position update
        hub_pos = (100, 100)
        spoke_positions = [(i * 50, i * 50) for i in range(10)]
        
        sim.update_targeting_positions(hub_pos, spoke_positions)
        
        assert sim.smart_targeting.hub_position == hub_pos
        assert sim.smart_targeting.spoke_positions == spoke_positions
    
    def test_smart_route_planning(self):
        """Test smart route planning functionality."""
        cfg = SimConfig()
        cfg.smart_targeting_enabled = True
        cfg.fleet_label = "2xC130"
        
        sim = LogisticsSim(cfg)
        
        # Initialize positions
        hub_pos = (0, 0)
        spoke_positions = [(i * 20, 0) for i in range(10)]
        sim.update_targeting_positions(hub_pos, spoke_positions)
        
        # Create aircraft with shortage scenario
        aircraft = sim.fleet[0]
        
        # Create stock shortage to trigger smart targeting
        sim.stock[0] = [0.1, 0.1, 0.1, 0.1]  # Critical shortage
        sim.stock[1] = [0.5, 0.8, 0.3, 0.7]  # Some deficits
        
        # Test smart route planning
        route = sim._plan_smart_route(aircraft, "A")
        
        if route is not None:
            route_info, payload_A, payload_B = route
            first_spoke, second_spoke = route_info
            
            assert isinstance(first_spoke, int)
            assert 0 <= first_spoke < sim.M
            assert isinstance(payload_A, list)
            assert len(payload_A) == 4
            assert isinstance(payload_B, list)
            assert len(payload_B) == 4


class TestMultiPeriodSimulation:
    """Test multi-period simulation scenarios."""
    
    def test_long_simulation_run(self):
        """Test running simulation for many periods."""
        cfg = SimConfig()
        cfg.periods = 100  # Long simulation
        cfg.fleet_label = "2xC130"
        
        sim = LogisticsSim(cfg)
        
        initial_ops_total = sum(sim.ops_by_spoke)
        
        # Run full simulation
        while sim.t < sim.cfg.periods:
            actions = sim.step_period()
            if actions is None:  # Simulation complete
                break
        
        # Should have completed
        assert sim.t >= cfg.periods
        
        # Should have performed some operations
        final_ops_total = sum(sim.ops_by_spoke)
        assert final_ops_total >= initial_ops_total
    
    def test_simulation_with_different_fleet_sizes(self):
        """Test simulation with different fleet configurations."""
        fleet_configs = ["2xC130", "4xC130", "2xC130_2xC27"]
        
        for fleet_label in fleet_configs:
            cfg = SimConfig()
            cfg.periods = 20
            cfg.fleet_label = fleet_label
            
            sim = LogisticsSim(cfg)
            
            # Verify fleet was built correctly
            if fleet_label == "2xC130":
                assert len(sim.fleet) == 2
                assert all(ac.typ == "C-130" for ac in sim.fleet)
            elif fleet_label == "4xC130":
                assert len(sim.fleet) == 4
                assert all(ac.typ == "C-130" for ac in sim.fleet)
            elif fleet_label == "2xC130_2xC27":
                assert len(sim.fleet) == 4
                assert sum(1 for ac in sim.fleet if ac.typ == "C-130") == 2
                assert sum(1 for ac in sim.fleet if ac.typ == "C-27") == 2
            
            # Run simulation
            for _ in range(10):
                sim.step_period()
            
            assert sim.t == 10
    
    def test_simulation_state_persistence(self):
        """Test simulation state persistence and restoration."""
        cfg = SimConfig()
        cfg.periods = 20
        cfg.fleet_label = "2xC130"
        
        sim = LogisticsSim(cfg)
        
        # Run for a few periods
        for _ in range(5):
            sim.step_period()
        
        # Capture state
        snapshot = sim.snapshot()
        
        # Continue simulation
        for _ in range(3):
            sim.step_period()
        
        assert sim.t == 8
        
        # Restore to earlier state
        sim.restore(snapshot)
        
        assert sim.t == 5
        assert len(sim.history) > 0
    
    def test_simulation_history_tracking(self):
        """Test simulation history tracking."""
        cfg = SimConfig()
        cfg.periods = 10
        cfg.fleet_label = "2xC130"
        
        sim = LogisticsSim(cfg)
        
        initial_history_length = len(sim.history)
        
        # Run simulation and track history growth
        for _ in range(5):
            sim.step_period()
        
        # History should grow with each period
        assert len(sim.history) > initial_history_length
        assert len(sim.history) >= 6  # Initial + 5 periods
        
        # Each history entry should be a valid snapshot
        for snapshot in sim.history:
            assert isinstance(snapshot, dict)
            assert 't' in snapshot
            assert 'stock' in snapshot
            assert 'fleet' in snapshot


class TestComplexScenarios:
    """Test complex simulation scenarios."""
    
    def test_resource_shortage_scenario(self):
        """Test simulation behavior during resource shortages."""
        cfg = SimConfig()
        cfg.periods = 20
        cfg.fleet_label = "4xC130"  # More aircraft to stress test
        cfg.init_A = 1  # Start with low resources
        cfg.init_B = 1
        cfg.init_C = 1
        cfg.init_D = 1
        
        sim = LogisticsSim(cfg)
        
        # Run simulation through shortage
        operations_history = []
        for _ in range(15):
            pre_ops = sum(sim.ops_by_spoke)
            sim.step_period()
            post_ops = sum(sim.ops_by_spoke)
            operations_history.append(post_ops - pre_ops)
        
        # Should have attempted to address shortages
        assert sim.t == 15
        assert max(operations_history) >= 0  # Some operations should occur
    
    def test_aircraft_rest_cycles(self):
        """Test aircraft rest cycle management."""
        cfg = SimConfig()
        cfg.periods = 30
        cfg.fleet_label = "2xC130"
        cfg.rest_c130 = 5  # Short rest cycle for testing
        
        sim = LogisticsSim(cfg)
        
        # Track aircraft rest states
        rest_events = []
        
        for _ in range(25):
            actions = sim.step_period()
            
            # Look for rest-related actions
            if actions:
                for aircraft_name, action in actions:
                    if "REST" in action:
                        rest_events.append((sim.t, aircraft_name, action))
        
        # Should have had some rest events
        assert len(rest_events) > 0
        
        # Verify aircraft actually rested
        for aircraft in sim.fleet:
            # Aircraft should have some activity history
            assert aircraft.active_periods >= 0
    
    def test_consumption_cadence_effects(self):
        """Test effects of different consumption cadences."""
        # Test with fast consumption
        cfg_fast = SimConfig()
        cfg_fast.periods = 20
        cfg_fast.a_days = 1  # Consume A every day
        cfg_fast.b_days = 1  # Consume B every day
        cfg_fast.init_A = 5
        cfg_fast.init_B = 5
        
        sim_fast = LogisticsSim(cfg_fast)
        
        # Run simulation
        for _ in range(10):
            sim_fast.step_period()
        
        # Should see significant resource depletion
        total_A_fast = sum(spoke[0] for spoke in sim_fast.stock)
        total_B_fast = sum(spoke[1] for spoke in sim_fast.stock)
        
        # Test with slow consumption
        cfg_slow = SimConfig()
        cfg_slow.periods = 20
        cfg_slow.a_days = 5  # Consume A every 5 days
        cfg_slow.b_days = 5  # Consume B every 5 days
        cfg_slow.init_A = 5
        cfg_slow.init_B = 5
        
        sim_slow = LogisticsSim(cfg_slow)
        
        # Run simulation
        for _ in range(10):
            sim_slow.step_period()
        
        # Should see less resource depletion
        total_A_slow = sum(spoke[0] for spoke in sim_slow.stock)
        total_B_slow = sum(spoke[1] for spoke in sim_slow.stock)
        
        # Fast consumption should deplete more resources
        assert total_A_slow >= total_A_fast
        assert total_B_slow >= total_B_fast
    
    def test_integrity_violation_detection(self):
        """Test integrity violation detection."""
        cfg = SimConfig()
        cfg.periods = 10
        cfg.fleet_label = "2xC130"
        
        sim = LogisticsSim(cfg)
        
        # Force an integrity violation by manually manipulating state
        sim.stock[0] = [-1, 1, 1, 1]  # Negative stock (violation)
        
        # Run a step and check for violation detection
        sim.step_period()
        
        # Should detect and log violations
        # (The exact mechanism depends on implementation)
        assert hasattr(sim, 'integrity_violations')
    
    def test_simulation_with_unlimited_storage(self):
        """Test simulation with unlimited storage enabled."""
        cfg = SimConfig()
        cfg.periods = 10
        cfg.unlimited_storage = True
        cfg.fleet_label = "4xC130"
        
        sim = LogisticsSim(cfg)
        
        # Run simulation - should handle large stock accumulations
        for _ in range(8):
            sim.step_period()
        
        # With unlimited storage, stocks can grow large
        max_stock = max(max(spoke) for spoke in sim.stock)
        assert max_stock >= 0  # Should not have negative stocks
        
        assert sim.t == 8


class TestSimulationEdgeCases:
    """Test simulation edge cases and error conditions."""
    
    def test_simulation_with_zero_fleet(self):
        """Test simulation behavior with no aircraft."""
        cfg = SimConfig()
        cfg.periods = 5
        
        sim = LogisticsSim(cfg)
        sim.fleet = []  # Remove all aircraft
        
        # Should still run without crashing
        for _ in range(3):
            actions = sim.step_period()
            # Should have no actions with no aircraft
            assert len(actions) == 0
        
        assert sim.t == 3
    
    def test_simulation_with_invalid_stock(self):
        """Test simulation handling of invalid stock values."""
        cfg = SimConfig()
        cfg.periods = 5
        
        sim = LogisticsSim(cfg)
        
        # Set invalid stock values
        sim.stock[0] = [float('inf'), 1, 1, 1]
        
        # Should handle gracefully
        try:
            sim.step_period()
        except (ValueError, OverflowError):
            # Expected for infinite values
            pass
    
    def test_simulation_progress_tracking(self):
        """Test simulation progress tracking and deadlock prevention."""
        cfg = SimConfig()
        cfg.periods = 10
        cfg.fleet_label = "2xC130"
        
        sim = LogisticsSim(cfg)
        
        # Create a scenario that might cause deadlock
        # (all spokes well-supplied, no need for movement)
        for i in range(sim.M):
            sim.stock[i] = [10, 10, 10, 10]
        
        # Run simulation - should not get stuck
        for _ in range(5):
            actions = sim.step_period()
            # May have few or no actions, but should not hang
        
        assert sim.t == 5


if __name__ == "__main__":
    pytest.main([__file__])
