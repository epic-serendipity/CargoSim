"""Time-based animation management for CargoSim."""

import time
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass

@dataclass
class FlightAnimation:
    """Flight animation data."""
    start_time: float
    end_time: float
    start_pos: Tuple[float, float]
    end_pos: Tuple[float, float]
    progress: float = 0.0

@dataclass
class LoadingAnimation:
    """Loading animation data."""
    start_time: float
    duration: float
    progress: float = 0.0

class CostVisualization:
    """Handles cost visualization data."""
    
    def __init__(self):
        self.cost_history: List[float] = []
        self.cost_trend: float = 0.0
    
    def update_cost(self, cost: float):
        """Update cost history and trend."""
        self.cost_history.append(cost)
        if len(self.cost_history) > 100:  # Keep last 100 entries
            self.cost_history.pop(0)
        
        # Calculate simple trend (last 10 entries)
        if len(self.cost_history) >= 10:
            recent = self.cost_history[-10:]
            self.cost_trend = (recent[-1] - recent[0]) / len(recent)

class TimeBasedAnimationManager:
    """Manages time-based animations for aircraft and UI elements."""
    
    def __init__(self):
        self.flight_animations: Dict[str, FlightAnimation] = {}
        self.loading_animations: Dict[str, LoadingAnimation] = {}
        self.performance_metrics: Dict[str, Any] = {}
        self.cost_visualization = CostVisualization()
    
    def update_animations(self, delta_time: float):
        """Update all active animations."""
        current_time = time.time()
        
        # Update flight animations
        for ac_name, anim in list(self.flight_animations.items()):
            if current_time >= anim.end_time:
                del self.flight_animations[ac_name]
            else:
                anim.progress = (current_time - anim.start_time) / (anim.end_time - anim.start_time)
        
        # Update loading animations
        for ac_name, anim in list(self.loading_animations.items()):
            if current_time >= anim.start_time + anim.duration:
                del self.loading_animations[ac_name]
            else:
                anim.progress = (current_time - anim.start_time) / anim.duration
    
    def get_aircraft_position(self, ac_name: str) -> Optional[Tuple[float, float]]:
        """Get current interpolated position for aircraft."""
        if ac_name in self.flight_animations:
            anim = self.flight_animations[ac_name]
            # Linear interpolation between start and end positions
            x = anim.start_pos[0] + (anim.end_pos[0] - anim.start_pos[0]) * anim.progress
            y = anim.start_pos[1] + (anim.end_pos[1] - anim.start_pos[1]) * anim.progress
            return (x, y)
        return None
    
    def add_loading_animation(self, ac_name: str, duration: float):
        """Add a loading animation for an aircraft."""
        self.loading_animations[ac_name] = LoadingAnimation(
            start_time=time.time(),
            duration=duration
        )
    
    def get_loading_progress(self, ac_name: str) -> float:
        """Get loading progress for an aircraft (0.0 to 1.0)."""
        if ac_name in self.loading_animations:
            return self.loading_animations[ac_name].progress
        return 0.0
    
    def update_performance_metrics(self, sim_data: Dict[str, Any]):
        """Update performance metrics."""
        self.performance_metrics.update(sim_data)
    
    def update_cost_data(self, total_cost: float):
        """Update cost data."""
        self.cost_visualization.update_cost(total_cost)
