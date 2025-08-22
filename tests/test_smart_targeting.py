"""Tests for the smart targeting system."""

import pytest
import math
from unittest.mock import patch

from cargosim.smart_targeting import (
    TargetingConfig, SpokeBenefit, SpokeCost, LegScore, SmartTargeting
)
from cargosim.config import M


class TestTargetingConfig:
    """Test targeting configuration."""
    
    def test_targeting_config_creation(self):
        """Test TargetingConfig initialization with defaults."""
        config = TargetingConfig()
        
        assert config.w_ops == 1.0
        assert config.w_need == 0.6
        assert config.w_dist == 0.8
        assert config.w_cong == 0.7
        assert config.second_leg_multiplier == 0.7
        assert config.fairness_decay == 0.8
        assert config.jitter_percent == 0.01
    
    def test_targeting_config_custom_values(self):
        """Test TargetingConfig with custom values."""
        config = TargetingConfig(
            w_ops=2.0,
            w_need=1.5,
            w_dist=0.5,
            max_aircraft_per_spoke_per_period=2
        )
        
        assert config.w_ops == 2.0
        assert config.w_need == 1.5
        assert config.w_dist == 0.5
        assert config.max_aircraft_per_spoke_per_period == 2


class TestDataClasses:
    """Test data classes for targeting system."""
    
    def test_spoke_benefit_creation(self):
        """Test SpokeBenefit creation."""
        benefit = SpokeBenefit(
            need_score=0.8,
            ops_gain_score=0.6,
            marginal_benefit=0.7
        )
        
        assert benefit.need_score == 0.8
        assert benefit.ops_gain_score == 0.6
        assert benefit.marginal_benefit == 0.7
    
    def test_spoke_cost_creation(self):
        """Test SpokeCost creation."""
        cost = SpokeCost(
            distance_norm=0.5,
            congestion_penalty=0.3,
            fairness_penalty=0.2
        )
        
        assert cost.distance_norm == 0.5
        assert cost.congestion_penalty == 0.3
        assert cost.fairness_penalty == 0.2
    
    def test_leg_score_creation(self):
        """Test LegScore creation."""
        benefit = SpokeBenefit(0.8, 0.6, 0.7)
        cost = SpokeCost(0.5, 0.3, 0.2)
        breakdown = {"benefit": 0.7, "distance": 0.5}
        
        score = LegScore(
            spoke_idx=3,
            score=0.85,
            benefit=benefit,
            cost=cost,
            breakdown=breakdown
        )
        
        assert score.spoke_idx == 3
        assert score.score == 0.85
        assert score.benefit == benefit
        assert score.cost == cost
        assert score.breakdown == breakdown


class TestSmartTargeting:
    """Test SmartTargeting system."""
    
    def test_smart_targeting_creation(self):
        """Test SmartTargeting initialization."""
        config = TargetingConfig()
        targeting = SmartTargeting(config)
        
        assert targeting.config == config
        assert len(targeting.spoke_positions) == 0
        assert targeting.hub_position == (0, 0)
        assert len(targeting.recent_service_count) == M
        assert len(targeting.period_reservations) == 0
    
    def test_initialize_positions(self):
        """Test position initialization."""
        config = TargetingConfig()
        targeting = SmartTargeting(config)
        
        hub_pos = (100, 100)
        spoke_positions = [(i * 50, i * 50) for i in range(M)]
        
        targeting.initialize_positions(hub_pos, spoke_positions)
        
        assert targeting.hub_position == hub_pos
        assert targeting.spoke_positions == spoke_positions
        assert len(targeting.distance_matrix) > 0
    
    def test_euclidean_distance(self):
        """Test Euclidean distance calculation."""
        config = TargetingConfig()
        targeting = SmartTargeting(config)
        
        # Test basic distance calculation
        p1 = (0, 0)
        p2 = (3, 4)
        distance = targeting._euclidean_distance(p1, p2)
        
        assert abs(distance - 5.0) < 1e-6  # 3-4-5 triangle
    
    def test_distance_matrix_computation(self):
        """Test distance matrix computation."""
        config = TargetingConfig()
        targeting = SmartTargeting(config)
        
        hub_pos = (0, 0)
        spoke_positions = [(10, 0), (0, 10), (10, 10)]
        
        targeting.initialize_positions(hub_pos, spoke_positions[:3])
        
        # Check hub to spoke distances
        assert ("HUB", 0) in targeting.distance_matrix
        assert abs(targeting.distance_matrix[("HUB", 0)] - 10.0) < 1e-6
        
        # Check spoke to spoke distances
        assert (0, 1) in targeting.distance_matrix
        assert abs(targeting.distance_matrix[(0, 1)] - math.sqrt(200)) < 1e-6
    
    def test_compute_spoke_benefit(self):
        """Test spoke benefit computation."""
        config = TargetingConfig()
        targeting = SmartTargeting(config)
        
        # Mock stock data - spoke with deficits
        stock = [0.5, 0.8, 0.2, 0.9]  # Low A and C resources
        capacity = 4
        stage = "A"
        
        benefit = targeting._compute_spoke_benefit(stock, capacity, stage)
        
        assert isinstance(benefit, SpokeBenefit)
        assert 0 <= benefit.need_score <= 1
        assert 0 <= benefit.ops_gain_score <= 1
        assert 0 <= benefit.marginal_benefit <= 1
        
        # Should have higher need score due to low A resource
        assert benefit.need_score > 0.3
    
    def test_compute_spoke_cost(self):
        """Test spoke cost computation."""
        config = TargetingConfig()
        targeting = SmartTargeting(config)
        
        # Initialize positions for distance calculation
        hub_pos = (0, 0)
        spoke_positions = [(10, 0) for _ in range(M)]
        targeting.initialize_positions(hub_pos, spoke_positions)
        
        spoke_idx = 0
        aircraft_location = "HUB"
        
        cost = targeting._compute_spoke_cost(spoke_idx, aircraft_location)
        
        assert isinstance(cost, SpokeCost)
        assert cost.distance_norm >= 0
        assert cost.congestion_penalty >= 0
        assert cost.fairness_penalty >= 0
    
    def test_score_leg(self):
        """Test leg scoring."""
        config = TargetingConfig()
        targeting = SmartTargeting(config)
        
        # Initialize positions
        hub_pos = (0, 0)
        spoke_positions = [(10, 0) for _ in range(M)]
        targeting.initialize_positions(hub_pos, spoke_positions)
        
        spoke_idx = 0
        stock = [1.0, 1.0, 0.5, 0.5]  # Some resource deficits
        capacity = 4
        stage = "OPS"
        aircraft_location = "HUB"
        
        score = targeting._score_leg(spoke_idx, stock, capacity, stage, aircraft_location)
        
        assert isinstance(score, LegScore)
        assert score.spoke_idx == spoke_idx
        assert isinstance(score.score, float)
        assert isinstance(score.breakdown, dict)
        assert len(score.breakdown) > 0
    
    def test_find_best_two_legs(self):
        """Test finding best two-leg route."""
        config = TargetingConfig()
        targeting = SmartTargeting(config)
        
        # Initialize positions
        hub_pos = (0, 0)
        spoke_positions = [(i * 10, 0) for i in range(M)]
        targeting.initialize_positions(hub_pos, spoke_positions)
        
        # Mock stock data - varied resource levels
        stock = []
        for i in range(M):
            if i < 3:
                stock.append([0.2, 0.8, 0.5, 0.9])  # Low A, needs attention
            else:
                stock.append([1.0, 1.0, 1.0, 1.0])  # Well supplied
        
        aircraft_location = "HUB"
        stage = "A"
        capacity = 6
        
        first_leg, second_leg = targeting.find_best_two_legs(
            aircraft_location, stock, stage, capacity
        )
        
        # Should find at least one leg
        assert first_leg is not None
        assert isinstance(first_leg, LegScore)
        assert 0 <= first_leg.spoke_idx < M
        
        # Second leg might be None (single leg route)
        if second_leg is not None:
            assert isinstance(second_leg, LegScore)
            assert 0 <= second_leg.spoke_idx < M
            assert second_leg.spoke_idx != first_leg.spoke_idx
    
    def test_recent_service_tracking(self):
        """Test recent service count tracking."""
        config = TargetingConfig()
        targeting = SmartTargeting(config)
        
        # Initially all service counts should be zero
        assert all(count == 0 for count in targeting.recent_service_count)
        
        # Update service for a spoke
        targeting.update_recent_service(3)
        assert targeting.recent_service_count[3] == 1
        assert targeting.recent_service_count[2] == 0
        
        # Decay service counts
        targeting.decay_recent_service()
        assert targeting.recent_service_count[3] < 1  # Should be decayed
    
    def test_period_reservations(self):
        """Test period reservation system."""
        config = TargetingConfig()
        targeting = SmartTargeting(config)
        
        # Initially no reservations
        assert len(targeting.period_reservations) == 0
        
        # Reserve a spoke
        targeting.reserve_spoke(5)
        assert 5 in targeting.period_reservations
        
        # Clear reservations
        targeting.clear_period_reservations()
        assert len(targeting.period_reservations) == 0
    
    def test_jitter_application(self):
        """Test score jitter for tie-breaking."""
        config = TargetingConfig(jitter_percent=0.1)  # 10% jitter
        targeting = SmartTargeting(config)
        
        base_score = 0.5
        
        # Apply jitter multiple times - should get different results
        jittered_scores = []
        for _ in range(10):
            jittered = targeting._apply_jitter(base_score)
            jittered_scores.append(jittered)
        
        # Should have some variation
        assert len(set(jittered_scores)) > 1  # Not all the same
        
        # All should be within jitter range
        for score in jittered_scores:
            assert abs(score - base_score) <= base_score * 0.1
    
    def test_congestion_penalty(self):
        """Test congestion penalty calculation."""
        config = TargetingConfig(max_aircraft_per_spoke_per_period=2)
        targeting = SmartTargeting(config)
        
        spoke_idx = 3
        
        # No reservations - no penalty
        penalty = targeting._compute_congestion_penalty(spoke_idx)
        assert penalty == 0.0
        
        # Reserve the spoke once - some penalty
        targeting.reserve_spoke(spoke_idx)
        penalty = targeting._compute_congestion_penalty(spoke_idx)
        assert penalty > 0.0
        
        # Reserve again - higher penalty
        targeting.reserve_spoke(spoke_idx)
        penalty2 = targeting._compute_congestion_penalty(spoke_idx)
        assert penalty2 > penalty
    
    def test_stage_based_scoring(self):
        """Test that scoring varies by stage."""
        config = TargetingConfig()
        targeting = SmartTargeting(config)
        
        # Initialize positions
        hub_pos = (0, 0)
        spoke_positions = [(10, 0) for _ in range(M)]
        targeting.initialize_positions(hub_pos, spoke_positions)
        
        spoke_idx = 0
        stock = [0.2, 1.0, 0.2, 1.0]  # Low A and C
        capacity = 4
        aircraft_location = "HUB"
        
        # Score for different stages
        score_a = targeting._score_leg(spoke_idx, stock, capacity, "A", aircraft_location)
        score_ops = targeting._score_leg(spoke_idx, stock, capacity, "OPS", aircraft_location)
        
        # Scores should be different for different stages
        # A stage should prioritize A resources, OPS should prioritize C/D
        assert score_a.score != score_ops.score
        assert score_a.breakdown != score_ops.breakdown


class TestTargetingIntegration:
    """Test integration scenarios for smart targeting."""
    
    def test_full_targeting_workflow(self):
        """Test complete targeting workflow."""
        config = TargetingConfig()
        targeting = SmartTargeting(config)
        
        # Setup scenario
        hub_pos = (0, 0)
        spoke_positions = [(i * 20, 0) for i in range(M)]
        targeting.initialize_positions(hub_pos, spoke_positions)
        
        # Create varied stock situation
        stock = []
        for i in range(M):
            if i < 2:
                stock.append([0.1, 0.1, 0.1, 0.1])  # Critical shortage
            elif i < 5:
                stock.append([0.5, 0.8, 0.3, 0.7])  # Some deficits
            else:
                stock.append([2.0, 2.0, 2.0, 2.0])  # Well supplied
        
        # Find routes for multiple aircraft
        routes = []
        for aircraft_idx in range(3):
            first_leg, second_leg = targeting.find_best_two_legs(
                "HUB", stock, "A", 6
            )
            
            if first_leg:
                routes.append((first_leg.spoke_idx, 
                             second_leg.spoke_idx if second_leg else None))
                
                # Reserve spokes to test congestion avoidance
                targeting.reserve_spoke(first_leg.spoke_idx)
                if second_leg:
                    targeting.reserve_spoke(second_leg.spoke_idx)
        
        # Should have found routes
        assert len(routes) > 0
        
        # Routes should prefer spokes with shortages
        critical_spokes = {0, 1}
        route_spokes = {spoke for route in routes for spoke in route if spoke is not None}
        
        # At least some routes should target critical spokes
        assert len(route_spokes & critical_spokes) > 0
    
    def test_no_good_targets(self):
        """Test behavior when no good targets are available."""
        config = TargetingConfig()
        targeting = SmartTargeting(config)
        
        # Initialize positions
        hub_pos = (0, 0)
        spoke_positions = [(10, 0) for _ in range(M)]
        targeting.initialize_positions(hub_pos, spoke_positions)
        
        # All spokes well supplied
        stock = [[5.0, 5.0, 5.0, 5.0] for _ in range(M)]
        
        first_leg, second_leg = targeting.find_best_two_legs(
            "HUB", stock, "A", 6
        )
        
        # Should still find a route (even if benefit is low)
        # or return None if truly no benefit
        if first_leg is not None:
            assert isinstance(first_leg, LegScore)
            assert first_leg.score >= 0


if __name__ == "__main__":
    pytest.main([__file__])
