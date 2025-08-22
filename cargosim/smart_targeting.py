"""Smart aircraft targeting system for CargoSim.

This module implements a scoring-based approach to aircraft routing that:
- Spreads aircraft out rather than dog-piling on the same spokes
- Prefers nearer spokes (lower travel time/cost)
- Chases the best operational payoff
- Is extensible to real time-based movement later
"""

import math
import random
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Set
from .config import M


@dataclass
class TargetingConfig:
    """Configuration for the smart targeting system."""
    # Scoring weights
    w_ops: float = 1.0          # Weight for ops unlock potential
    w_need: float = 0.6         # Weight for resource deficits
    w_dist: float = 0.8         # Weight for distance penalty
    w_cong: float = 0.7         # Weight for congestion penalty
    
    # Operational parameters
    max_aircraft_per_spoke_per_period: Optional[int] = None  # None = unlimited
    second_leg_multiplier: float = 0.7  # Benefit multiplier for second leg
    distance_normalizer: Optional[float] = None  # P90 distance or fixed km, None = auto
    fairness_decay: float = 0.8  # How fast recent-service penalty fades
    
    # Random jitter for tie-breaking
    jitter_percent: float = 0.01  # ±1% random variation


@dataclass
class SpokeBenefit:
    """Benefit signals for a spoke."""
    need_score: float           # How "hungry" the spoke is [0,1]
    ops_gain_score: float       # Likelihood of unlocking ops [0,1]
    marginal_benefit: float     # Combined benefit score [0,1]


@dataclass
class SpokeCost:
    """Cost signals for a spoke."""
    distance_norm: float        # Normalized distance [0,1+]
    congestion_penalty: float   # Congestion penalty [0,1+]
    fairness_penalty: float     # Recent service penalty [0,1]


@dataclass
class LegScore:
    """Complete score for a potential leg."""
    spoke_idx: int
    score: float
    benefit: SpokeBenefit
    cost: SpokeCost
    breakdown: Dict[str, float]  # Detailed scoring breakdown


class SmartTargeting:
    """Smart aircraft targeting system."""
    
    def __init__(self, config: TargetingConfig):
        self.config = config
        self.spoke_positions: List[Tuple[int, int]] = []
        self.hub_position: Tuple[int, int] = (0, 0)
        self.distance_matrix: Dict[Tuple[str, int], float] = {}
        self.recent_service_count: List[int] = [0] * M
        self.period_reservations: Set[int] = set()  # Spokes reserved this period
        
    def initialize_positions(self, hub_pos: Tuple[int, int], spoke_positions: List[Tuple[int, int]]):
        """Initialize hub and spoke positions, compute distance matrix."""
        self.hub_position = hub_pos
        self.spoke_positions = spoke_positions
        self._compute_distance_matrix()
        
    def _compute_distance_matrix(self):
        """Precompute all distances between locations."""
        self.distance_matrix.clear()
        
        # Hub to spoke distances
        for i, spoke_pos in enumerate(self.spoke_positions):
            dist = self._euclidean_distance(self.hub_position, spoke_pos)
            self.distance_matrix[("HUB", i)] = dist
            self.distance_matrix[(i, "HUB")] = dist
            
        # Spoke to spoke distances
        for i in range(M):
            for j in range(i + 1, M):
                dist = self._euclidean_distance(self.spoke_positions[i], self.spoke_positions[j])
                self.distance_matrix[(i, j)] = dist
                self.distance_matrix[(j, i)] = dist
                
        # Auto-normalize distance if not specified
        if self.config.distance_normalizer is None:
            all_distances = [d for d in self.distance_matrix.values()]
            all_distances.sort()
            p90_idx = int(0.9 * len(all_distances))
            self.config.distance_normalizer = all_distances[p90_idx]
    
    def _euclidean_distance(self, pos1: Tuple[int, int], pos2: Tuple[int, int]) -> float:
        """Calculate Euclidean distance between two positions."""
        dx = pos1[0] - pos2[0]
        dy = pos1[1] - pos2[1]
        return math.sqrt(dx*dx + dy*dy)
    
    def _get_distance(self, from_loc: str | int, to_spoke: int) -> float:
        """Get distance from a location to a spoke."""
        if from_loc == "HUB":
            return self.distance_matrix[("HUB", to_spoke)]
        else:
            # from_loc should be a spoke index (either string or int)
            from_spoke = int(from_loc) if isinstance(from_loc, str) else from_loc
            if from_spoke == to_spoke:
                return 0.0  # Same spoke
            return self.distance_matrix[(from_spoke, to_spoke)]
    
    def compute_spoke_benefits(self, stock: List[List[float]], stage: str) -> List[SpokeBenefit]:
        """Compute benefit signals for all spokes."""
        benefits = []
        
        for i in range(M):
            # Resource deficits
            deficit_A = max(0, 1 - stock[i][0])
            deficit_B = max(0, 1 - stock[i][1])
            deficit_C = max(0, 1 - stock[i][2])
            deficit_D = max(0, 1 - stock[i][3])
            
            # Overall need score (how hungry the spoke is)
            total_deficit = deficit_A + deficit_B + deficit_C + deficit_D
            need_score = min(1.0, total_deficit / 4.0)  # Normalize to [0,1]
            
            # Ops unlock potential
            if stage == "A":
                # In A stage, focus on A deficits
                ops_gain_score = min(1.0, deficit_A)
            elif stage == "B":
                # In B stage, focus on B deficits
                ops_gain_score = min(1.0, deficit_B)
            else:  # "OPS"
                # In OPS stage, focus on C/D deficits for operations
                ops_gain_score = min(1.0, (deficit_C + deficit_D) / 2.0)
            
            # Enhanced benefit calculation for plentiful resource scenarios
            if total_deficit == 0:
                # When resources are plentiful, consider maintenance and operational readiness
                # Calculate how close each resource is to optimal levels
                optimal_A = 2.0  # Optimal A level
                optimal_B = 2.0  # Optimal B level
                optimal_C = 1.0  # Optimal C level
                optimal_D = 1.0  # Optimal D level
                
                # How far from optimal (closer to optimal = higher benefit)
                distance_from_optimal = (
                    abs(stock[i][0] - optimal_A) + 
                    abs(stock[i][1] - optimal_B) + 
                    abs(stock[i][2] - optimal_C) + 
                    abs(stock[i][3] - optimal_D)
                )
                
                # Normalize distance (closer to optimal = higher benefit)
                maintenance_score = max(0, 1.0 - (distance_from_optimal / 8.0))
                
                # Consider operational readiness (ensure we can maintain ops)
                ops_readiness = min(1.0, min(stock[i][0], stock[i][1], stock[i][2], stock[i][3]) / 1.0)
                
                # Distribution bonus: encourage spreading out when resources are plentiful
                # Spokes with lower indices get a small penalty to encourage distribution
                distribution_bonus = max(0, 0.1 - (i * 0.02))  # S1 gets -0.1, S10 gets +0.1
                
                # Combine maintenance, readiness, and distribution scores
                need_score = (maintenance_score + ops_readiness + distribution_bonus) / 3.0
                ops_gain_score = max(ops_gain_score, need_score * 0.5)
                
                # Ensure we still have a meaningful benefit even when resources are plentiful
                # This prevents aircraft from staying idle when no immediate deficits exist
                if need_score < 0.1:  # If the calculated score is too low
                    need_score = 0.1  # Set a minimum baseline benefit
                    ops_gain_score = max(ops_gain_score, 0.1)  # Ensure ops gain is also meaningful
            
            # Marginal benefit (enhanced for plentiful scenarios)
            marginal_benefit = (need_score + ops_gain_score) / 2.0
            
            benefits.append(SpokeBenefit(
                need_score=need_score,
                ops_gain_score=ops_gain_score,
                marginal_benefit=marginal_benefit
            ))
            
        return benefits
    
    def compute_spoke_costs(self, aircraft_location: str | int, stage: str, stock: List[List[float]]) -> List[SpokeCost]:
        """Compute cost signals for all spokes from an aircraft's perspective."""
        costs = []
        
        for i in range(M):
            # Distance penalty
            distance = self._get_distance(aircraft_location, i)
            distance_norm = distance / self.config.distance_normalizer
            
            # Congestion penalty
            if i in self.period_reservations:
                if self.config.max_aircraft_per_spoke_per_period is not None:
                    # Count current reservations
                    count = sum(1 for s in self.period_reservations if s == i)
                    if count >= self.config.max_aircraft_per_spoke_per_period:
                        congestion_penalty = 2.0  # Hard cap exceeded
                    else:
                        congestion_penalty = count * 0.5  # Soft penalty
                else:
                    # Simple penalty for any reservation
                    congestion_penalty = 0.5
            else:
                congestion_penalty = 0.0
            
            # Enhanced fairness penalty (recent service)
            # When resources are plentiful, increase fairness penalty to spread aircraft out
            base_fairness = self.recent_service_count[i] * (1 - self.config.fairness_decay)
            
            # Check if this is a plentiful resource scenario
            total_stock = sum(stock[i])
            if total_stock >= 6:  # Plentiful resources
                # Increase fairness penalty to encourage spreading out
                # Also add a base penalty for recently serviced spokes to prevent clustering
                fairness_penalty = base_fairness * 3.0 + (0.2 if self.recent_service_count[i] > 0 else 0.0)
            else:
                fairness_penalty = base_fairness
            
            costs.append(SpokeCost(
                distance_norm=distance_norm,
                congestion_penalty=congestion_penalty,
                fairness_penalty=fairness_penalty
            ))
            
        return costs
    
    def score_spoke(self, spoke_idx: int, benefit: SpokeBenefit, cost: SpokeCost, 
                   stage: str, is_second_leg: bool = False) -> LegScore:
        """Score a potential leg to a spoke."""
        # Apply stage-specific weighting
        w_ops = self.config.w_ops
        w_need = self.config.w_need
        
        if stage == "A":
            w_need *= 1.2  # Increase weight for A deficits
        elif stage == "B":
            w_need *= 1.2  # Increase weight for B deficits
        else:  # "OPS"
            w_ops *= 1.2   # Increase weight for ops unlock
            
        # Apply second leg multiplier
        if is_second_leg:
            w_ops *= self.config.second_leg_multiplier
            w_need *= self.config.second_leg_multiplier
            
        # Calculate score components
        ops_component = w_ops * benefit.ops_gain_score
        need_component = w_need * benefit.need_score
        distance_component = self.config.w_dist * cost.distance_norm
        congestion_component = self.config.w_cong * cost.congestion_penalty
        fairness_component = self.config.w_cong * cost.fairness_penalty
        
        # Base score
        base_score = ops_component + need_component - distance_component - congestion_component - fairness_component
        
        # Add random jitter for tie-breaking
        jitter = random.uniform(1 - self.config.jitter_percent, 1 + self.config.jitter_percent)
        final_score = base_score * jitter
        
        # Detailed breakdown for debugging
        breakdown = {
            "ops_component": ops_component,
            "need_component": need_component,
            "distance_component": -distance_component,
            "congestion_component": -congestion_component,
            "fairness_component": -fairness_component,
            "jitter": jitter,
            "final_score": final_score
        }
        
        return LegScore(
            spoke_idx=spoke_idx,
            score=final_score,
            benefit=benefit,
            cost=cost,
            breakdown=breakdown
        )
    
    def find_best_leg(self, aircraft_location: str, stock: List[List[float]], 
                      stage: str, aircraft_capacity: int, 
                      exclude_spokes: Optional[Set[int]] = None) -> Optional[LegScore]:
        """Find the best leg for an aircraft."""
        if exclude_spokes is None:
            exclude_spokes = set()
            
        # Compute benefits and costs
        benefits = self.compute_spoke_benefits(stock, stage)
        costs = self.compute_spoke_costs(aircraft_location, stage, stock)
        
        # Score all feasible spokes
        leg_scores = []
        for i in range(M):
            if i in exclude_spokes:
                continue
                
            score = self.score_spoke(i, benefits[i], costs[i], stage)
            leg_scores.append(score)
        
        if not leg_scores:
            return None
            
        # Return the best score
        return max(leg_scores, key=lambda s: s.score)
    
    def find_best_two_legs(self, aircraft_location: str, stock: List[List[float]], 
                           stage: str, aircraft_capacity: int) -> Tuple[Optional[LegScore], Optional[LegScore]]:
        """Find the best two-leg route for an aircraft."""
        # Find first leg
        first_leg = self.find_best_leg(aircraft_location, stock, stage, aircraft_capacity)
        if first_leg is None:
            return None, None
            
        # Find second leg from first spoke
        exclude_spokes = {first_leg.spoke_idx}
        second_leg = self.find_best_leg(first_leg.spoke_idx, stock, stage, 
                                       aircraft_capacity, exclude_spokes)
        
        # Only accept second leg if it's significantly beneficial
        if second_leg and second_leg.score > 0.1:  # Threshold for second leg
            return first_leg, second_leg
        else:
            return first_leg, None
    
    def reserve_spoke(self, spoke_idx: int):
        """Reserve a spoke for this period."""
        self.period_reservations.add(spoke_idx)
        
    def reset_recent_service(self):
        """Reset recent service tracking for a new simulation."""
        self.recent_service_count = [0] * M
        self.period_reservations.clear()
        
    def clear_period_reservations(self):
        """Clear all period reservations (call at end of period)."""
        self.period_reservations.clear()
        
    def update_recent_service(self, spoke_idx: int):
        """Update recent service count for a spoke."""
        self.recent_service_count[spoke_idx] += 1
        
    def decay_recent_service(self):
        """Decay recent service counts (call at end of period)."""
        for i in range(M):
            self.recent_service_count[i] = max(0, 
                int(self.recent_service_count[i] * self.config.fairness_decay))
    
    def get_debug_info(self) -> Dict[str, any]:
        """Get debug information about the targeting system."""
        return {
            "config": self.config,
            "spoke_positions": self.spoke_positions,
            "hub_position": self.hub_position,
            "distance_matrix_keys": list(self.distance_matrix.keys()),
            "recent_service_count": self.recent_service_count,
            "period_reservations": list(self.period_reservations)
        }
    
    def debug_route_planning(self, aircraft_location: str | int, stock: List[List[float]], 
                            stage: str, aircraft_capacity: int) -> Dict[str, any]:
        """Debug method to understand route planning decisions."""
        benefits = self.compute_spoke_benefits(stock, stage)
        costs = self.compute_spoke_costs(aircraft_location, stage, stock)
        
        debug_info = {
            "stage": stage,
            "aircraft_location": aircraft_location,
            "aircraft_capacity": aircraft_capacity,
            "spoke_details": []
        }
        
        for i in range(M):
            spoke_info = {
                "spoke_idx": i,
                "stock": stock[i],
                "benefit": {
                    "need_score": benefits[i].need_score,
                    "ops_gain_score": benefits[i].ops_gain_score,
                    "marginal_benefit": benefits[i].marginal_benefit
                },
                "cost": {
                    "distance_norm": costs[i].distance_norm,
                    "congestion_penalty": costs[i].congestion_penalty,
                    "fairness_penalty": costs[i].fairness_penalty
                }
            }
            
            # Calculate score for this spoke
            score = self.score_spoke(i, benefits[i], costs[i], stage)
            spoke_info["score"] = score.score
            spoke_info["score_breakdown"] = score.breakdown
            
            debug_info["spoke_details"].append(spoke_info)
        
        # Sort by score to see best options
        debug_info["spoke_details"].sort(key=lambda x: x["score"], reverse=True)
        
        return debug_info
