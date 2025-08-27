"""Performance optimization and monitoring for CargoSim."""

import time
import logging
import weakref
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field
from collections import OrderedDict
import gc

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance metrics for monitoring."""
    simulation_time: float = 0.0
    memory_usage_mb: float = 0.0
    cache_hit_rate: float = 0.0
    calculation_time: float = 0.0
    gui_update_time: float = 0.0
    frame_rate: float = 0.0
    last_update: float = 0.0


@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    value: Any
    timestamp: float
    access_count: int = 0
    size_bytes: int = 0


class MemoryMonitor:
    """Monitor memory usage and provide optimization recommendations."""
    
    def __init__(self, warning_threshold_mb: float = 400.0, critical_threshold_mb: float = 500.0):
        self.warning_threshold = warning_threshold_mb
        self.critical_threshold = critical_threshold_mb
        self.memory_history: List[Tuple[float, float]] = []
        self.max_history_size = 100
        
    def get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            return memory_info.rss / 1024 / 1024  # Convert to MB
        except ImportError:
            # Fallback to basic memory monitoring
            return self._get_basic_memory_usage()
    
    def _get_basic_memory_usage(self) -> float:
        """Basic memory usage estimation using gc module."""
        try:
            gc.collect()  # Force garbage collection
            objects = gc.get_objects()
            total_size = sum(self._estimate_object_size(obj) for obj in objects)
            return total_size / 1024 / 1024  # Convert to MB
        except Exception:
            return 0.0
    
    def _estimate_object_size(self, obj: Any) -> int:
        """Estimate object size in bytes."""
        try:
            import sys
            return sys.getsizeof(obj)
        except Exception:
            return 0
    
    def check_memory_status(self) -> Dict[str, Any]:
        """Check memory status and return recommendations."""
        current_memory = self.get_memory_usage()
        timestamp = time.time()
        
        # Store in history
        self.memory_history.append((timestamp, current_memory))
        if len(self.memory_history) > self.max_history_size:
            self.memory_history.pop(0)
        
        status = {
            'current_memory_mb': current_memory,
            'status': 'normal',
            'warnings': [],
            'recommendations': []
        }
        
        if current_memory > self.critical_threshold:
            status['status'] = 'critical'
            status['warnings'].append(f"Memory usage critical: {current_memory:.1f} MB")
            status['recommendations'].append("Consider reducing spoke count or simplifying operations")
            status['recommendations'].append("Force garbage collection")
        elif current_memory > self.warning_threshold:
            status['status'] = 'warning'
            status['warnings'].append(f"Memory usage high: {current_memory:.1f} MB")
            status['recommendations'].append("Monitor memory usage closely")
        
        return status
    
    def get_memory_trend(self) -> Dict[str, Any]:
        """Analyze memory usage trend."""
        if len(self.memory_history) < 2:
            return {'trend': 'insufficient_data', 'change_rate': 0.0}
        
        # Calculate change rate over last 10 measurements
        recent_history = self.memory_history[-10:]
        if len(recent_history) >= 2:
            time_diff = recent_history[-1][0] - recent_history[0][0]
            memory_diff = recent_history[-1][1] - recent_history[0][1]
            
            if time_diff > 0:
                change_rate = memory_diff / time_diff  # MB per second
                
                if change_rate > 1.0:
                    trend = 'increasing_rapidly'
                elif change_rate > 0.1:
                    trend = 'increasing'
                elif change_rate < -1.0:
                    trend = 'decreasing_rapidly'
                elif change_rate < -0.1:
                    trend = 'decreasing'
                else:
                    trend = 'stable'
                
                return {
                    'trend': trend,
                    'change_rate': change_rate,
                    'memory_diff_mb': memory_diff,
                    'time_diff_seconds': time_diff
                }
        
        return {'trend': 'insufficient_data', 'change_rate': 0.0}


class DistanceCache:
    """Efficient cache for distance calculations."""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.cache: OrderedDict = OrderedDict()
        self.hits = 0
        self.misses = 0
        
    def get(self, key: Tuple[int, int]) -> Optional[float]:
        """Get cached distance value."""
        # Normalize key (smaller index first)
        normalized_key = (min(key[0], key[1]), max(key[0], key[1]))
        
        if normalized_key in self.cache:
            # Move to end (most recently used)
            value = self.cache.pop(normalized_key)
            self.cache[normalized_key] = value
            self.hits += 1
            return value.value
        
        self.misses += 1
        return None
    
    def set(self, key: Tuple[int, int], value: float) -> None:
        """Set cached distance value."""
        # Normalize key
        normalized_key = (min(key[0], key[1]), max(key[0], key[1]))
        
        # Remove if exists
        if normalized_key in self.cache:
            self.cache.pop(normalized_key)
        
        # Add new entry
        entry = CacheEntry(
            value=value,
            timestamp=time.time(),
            size_bytes=self._estimate_size(value)
        )
        self.cache[normalized_key] = entry
        
        # Maintain max size
        if len(self.cache) > self.max_size:
            # Remove oldest entry
            self.cache.popitem(last=False)
    
    def _estimate_size(self, value: float) -> int:
        """Estimate memory size of cache entry."""
        return 64  # Rough estimate for float + metadata
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.hits + self.misses
        hit_rate = self.hits / total_requests if total_requests > 0 else 0.0
        
        total_size_bytes = sum(entry.size_bytes for entry in self.cache.values())
        
        return {
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': hit_rate,
            'size': len(self.cache),
            'max_size': self.max_size,
            'memory_usage_bytes': total_size_bytes,
            'memory_usage_mb': total_size_bytes / 1024 / 1024
        }
    
    def clear(self) -> None:
        """Clear all cached values."""
        self.cache.clear()
        self.hits = 0
        self.misses = 0


class FlightTimeCache:
    """Cache for flight time calculations."""
    
    def __init__(self, max_size: int = 500):
        self.max_size = max_size
        self.cache: OrderedDict = OrderedDict()
        self.hits = 0
        self.misses = 0
        
    def get(self, key: Tuple[int, int, float]) -> Optional[float]:
        """Get cached flight time value."""
        if key in self.cache:
            # Move to end (most recently used)
            value = self.cache.pop(key)
            self.cache[key] = value
            self.hits += 1
            return value.value
        
        self.misses += 1
        return None
    
    def set(self, key: Tuple[int, int, float], value: float) -> None:
        """Set cached flight time value."""
        # Remove if exists
        if key in self.cache:
            self.cache.pop(key)
        
        # Add new entry
        entry = CacheEntry(
            value=value,
            timestamp=time.time(),
            size_bytes=self._estimate_size(key, value)
        )
        self.cache[key] = entry
        
        # Maintain max size
        if len(self.cache) > self.max_size:
            # Remove oldest entry
            self.cache.popitem(last=False)
    
    def _estimate_size(self, key: Tuple[int, int, float], value: float) -> int:
        """Estimate memory size of cache entry."""
        return 80  # Rough estimate for tuple + float + metadata
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.hits + self.misses
        hit_rate = self.hits / total_requests if total_requests > 0 else 0.0
        
        total_size_bytes = sum(entry.size_bytes for entry in self.cache.values())
        
        return {
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': hit_rate,
            'size': len(self.cache),
            'max_size': self.max_size,
            'memory_usage_bytes': total_size_bytes,
            'memory_usage_mb': total_size_bytes / 1024 / 1024
        }
    
    def clear(self) -> None:
        """Clear all cached values."""
        self.cache.clear()
        self.hits = 0
        self.misses = 0


class PerformanceOptimizer:
    """Main performance optimization engine."""
    
    def __init__(self):
        self.distance_cache = DistanceCache()
        self.flight_time_cache = FlightTimeCache()
        self.memory_monitor = MemoryMonitor()
        self.metrics = PerformanceMetrics()
        self.optimization_enabled = True
        self.last_optimization_check = 0.0
        self.optimization_check_interval = 60.0  # Check every 60 seconds
        
    def get_cached_distance(self, spoke_a: int, spoke_b: int) -> Optional[float]:
        """Get cached distance between spokes."""
        if not self.optimization_enabled:
            return None
        
        return self.distance_cache.get((spoke_a, spoke_b))
    
    def cache_distance(self, spoke_a: int, spoke_b: int, distance: float) -> None:
        """Cache calculated distance."""
        if not self.optimization_enabled:
            return
        
        self.distance_cache.set((spoke_a, spoke_b), distance)
    
    def get_cached_flight_time(self, spoke_a: int, spoke_b: int, speed_mach: float) -> Optional[float]:
        """Get cached flight time between spokes."""
        if not self.optimization_enabled:
            return None
        
        return self.flight_time_cache.get((spoke_a, spoke_b, speed_mach))
    
    def cache_flight_time(self, spoke_a: int, spoke_b: int, speed_mach: float, flight_time: float) -> None:
        """Cache calculated flight time."""
        if not self.optimization_enabled:
            return
        
        self.flight_time_cache.set((spoke_a, spoke_b, speed_mach), flight_time)
    
    def calculate_distance(self, spoke_a: int, spoke_b: int, spoke_distances: List[float]) -> float:
        """Calculate distance between spokes with caching."""
        # Try cache first
        cached_distance = self.get_cached_distance(spoke_a, spoke_b)
        if cached_distance is not None:
            return cached_distance
        
        # Calculate distance
        if spoke_a == 0:  # Hub
            distance = spoke_distances[spoke_b - 1]
        elif spoke_b == 0:  # Hub
            distance = spoke_distances[spoke_a - 1]
        else:
            # Spoke to spoke (via hub)
            distance = spoke_distances[spoke_a - 1] + spoke_distances[spoke_b - 1]
        
        # Cache the result
        self.cache_distance(spoke_a, spoke_b, distance)
        return distance
    
    def calculate_flight_time(self, spoke_a: int, spoke_b: int, speed_mach: float, 
                            spoke_distances: List[float]) -> float:
        """Calculate flight time between spokes with caching."""
        # Try cache first
        cached_time = self.get_cached_flight_time(spoke_a, spoke_b, speed_mach)
        if cached_time is not None:
            return cached_time
        
        # Calculate distance
        distance = self.calculate_distance(spoke_a, spoke_b, spoke_distances)
        
        # Calculate flight time (assuming 0.45 Mach = 340 mph)
        speed_mph = speed_mach * 340
        flight_time_hours = distance / speed_mph
        
        # Cache the result
        self.cache_flight_time(spoke_a, spoke_b, speed_mach, flight_time_hours)
        return flight_time_hours
    
    def check_performance(self) -> Dict[str, Any]:
        """Check overall performance and provide optimization recommendations."""
        current_time = time.time()
        
        # Check memory status
        memory_status = self.memory_monitor.check_memory_status()
        memory_trend = self.memory_monitor.get_memory_trend()
        
        # Get cache statistics
        distance_cache_stats = self.distance_cache.get_stats()
        flight_time_cache_stats = self.flight_time_cache.get_stats()
        
        # Overall cache performance
        total_cache_hits = distance_cache_stats['hits'] + flight_time_cache_stats['hits']
        total_cache_requests = (distance_cache_stats['hits'] + distance_cache_stats['misses'] + 
                               flight_time_cache_stats['hits'] + flight_time_cache_stats['misses'])
        overall_hit_rate = total_cache_hits / total_cache_requests if total_cache_requests > 0 else 0.0
        
        # Performance recommendations
        recommendations = []
        
        if memory_status['status'] == 'critical':
            recommendations.append("CRITICAL: Reduce spoke count or simplify operations immediately")
            recommendations.append("Force garbage collection")
            self.optimization_enabled = False  # Disable optimization to save memory
        
        if memory_status['status'] == 'warning':
            recommendations.append("Monitor memory usage closely")
            recommendations.append("Consider reducing spoke count")
        
        if overall_hit_rate < 0.5:
            recommendations.append("Cache hit rate is low - consider adjusting cache size")
        
        if memory_trend['trend'] == 'increasing_rapidly':
            recommendations.append("Memory usage increasing rapidly - check for memory leaks")
        
        # Update metrics
        self.metrics.memory_usage_mb = memory_status['current_memory_mb']
        self.metrics.cache_hit_rate = overall_hit_rate
        self.metrics.last_update = current_time
        
        return {
            'memory_status': memory_status,
            'memory_trend': memory_trend,
            'cache_performance': {
                'distance_cache': distance_cache_stats,
                'flight_time_cache': flight_time_cache_stats,
                'overall_hit_rate': overall_hit_rate
            },
            'recommendations': recommendations,
            'optimization_enabled': self.optimization_enabled
        }
    
    def optimize_for_large_scale(self, spoke_count: int) -> Dict[str, Any]:
        """Apply optimizations for large-scale operations."""
        optimizations = {
            'cache_size_increased': False,
            'memory_monitoring_enabled': True,
            'garbage_collection_forced': False,
            'performance_mode': 'standard'
        }
        
        if spoke_count > 12:
            # Increase cache sizes for large operations
            self.distance_cache.max_size = 2000
            self.flight_time_cache.max_size = 1000
            optimizations['cache_size_increased'] = True
            optimizations['performance_mode'] = 'optimized'
        
        if spoke_count > 15:
            # Critical performance mode
            optimizations['performance_mode'] = 'critical'
            # Force garbage collection
            gc.collect()
            optimizations['garbage_collection_forced'] = True
        
        return optimizations
    
    def force_cleanup(self) -> None:
        """Force cleanup of caches and memory."""
        logger.info("Forcing performance optimization cleanup")
        
        # Clear caches
        self.distance_cache.clear()
        self.flight_time_cache.clear()
        
        # Force garbage collection
        gc.collect()
        
        # Reset metrics
        self.metrics = PerformanceMetrics()
        
        logger.info("Performance optimization cleanup completed")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary."""
        performance_check = self.check_performance()
        
        return {
            'metrics': self.metrics.__dict__,
            'performance_check': performance_check,
            'optimization_status': {
                'enabled': self.optimization_enabled,
                'last_check': self.last_optimization_check,
                'check_interval': self.optimization_check_interval
            }
        }


class PerformanceDecorator:
    """Decorator for performance monitoring."""
    
    def __init__(self, optimizer: PerformanceOptimizer):
        self.optimizer = optimizer
    
    def monitor_performance(self, func: Callable) -> Callable:
        """Decorator to monitor function performance."""
        def wrapper(*args, **kwargs):
            start_time = time.time()
            start_memory = self.optimizer.memory_monitor.get_memory_usage()
            
            try:
                result = func(*args, **kwargs)
                
                # Record performance metrics
                end_time = time.time()
                end_memory = self.optimizer.memory_monitor.get_memory_usage()
                
                execution_time = end_time - start_time
                memory_delta = end_memory - start_memory
                
                # Update metrics
                self.optimizer.metrics.calculation_time = execution_time
                
                # Log performance if significant
                if execution_time > 1.0:  # More than 1 second
                    logger.warning(f"Slow operation detected: {func.__name__} took {execution_time:.2f}s")
                
                if memory_delta > 50:  # More than 50MB increase
                    logger.warning(f"High memory usage detected: {func.__name__} used {memory_delta:.1f}MB")
                
                return result
                
            except Exception as e:
                logger.error(f"Error in {func.__name__}: {e}")
                raise
        
        return wrapper


class SimulationPerformanceOptimizer(PerformanceOptimizer):
    """Specialized performance optimizer for simulation operations."""
    
    def __init__(self):
        super().__init__()
        self.simulation_metrics = SimulationPerformanceMetrics()
        self.adaptive_optimization = True
        self.last_adaptation_check = 0.0
        self.adaptation_interval = 60.0  # 1 minute
        self.performance_history: List[Dict[str, Any]] = []
        self.max_history_size = 50
        
    def optimize_for_simulation(self, spoke_count: int, aircraft_count: int, 
                              current_performance: Dict[str, Any]) -> Dict[str, Any]:
        """Apply simulation-specific optimizations."""
        current_time = time.time()
        
        # Check if we need to adapt
        if (self.adaptive_optimization and 
            current_time - self.last_adaptation_check > self.adaptation_interval):
            
            self.last_adaptation_check = current_time
            return self._adapt_simulation_optimization(spoke_count, aircraft_count, current_performance)
        
        # Return current optimization status
        return self._get_current_optimization_status(spoke_count, aircraft_count)
    
    def _adapt_simulation_optimization(self, spoke_count: int, aircraft_count: int,
                                     current_performance: Dict[str, Any]) -> Dict[str, Any]:
        """Adapt optimization based on current performance."""
        logger.info("Adapting simulation performance optimization")
        
        # Store performance data
        performance_data = {
            'timestamp': time.time(),
            'spoke_count': spoke_count,
            'aircraft_count': aircraft_count,
            'memory_usage': current_performance.get('memory_usage_mb', 0),
            'response_time': current_performance.get('response_time_ms', 0),
            'optimization_level': self._calculate_optimization_level(spoke_count, aircraft_count)
        }
        
        self.performance_history.append(performance_data)
        if len(self.performance_history) > self.max_history_size:
            self.performance_history.pop(0)
        
        # Apply adaptive optimizations
        optimizations = self._apply_adaptive_optimizations(spoke_count, aircraft_count, current_performance)
        
        # Update simulation metrics
        self.simulation_metrics.update_metrics(performance_data)
        
        return optimizations
    
    def _calculate_optimization_level(self, spoke_count: int, aircraft_count: int) -> int:
        """Calculate required optimization level."""
        if spoke_count > 15 or aircraft_count > 20:
            return 3  # Maximum optimization
        elif spoke_count > 12 or aircraft_count > 15:
            return 2  # High optimization
        elif spoke_count > 8 or aircraft_count > 10:
            return 1  # Moderate optimization
        else:
            return 0  # Standard optimization
    
    def _apply_adaptive_optimizations(self, spoke_count: int, aircraft_count: int,
                                    current_performance: Dict[str, Any]) -> Dict[str, Any]:
        """Apply adaptive optimizations based on current conditions."""
        optimizations = {
            'cache_size_increased': False,
            'memory_monitoring_enabled': True,
            'garbage_collection_forced': False,
            'performance_mode': 'standard',
            'optimization_level': 0,
            'recommendations': []
        }
        
        # Level 0: Standard optimization
        if spoke_count <= 8 and aircraft_count <= 10:
            optimizations['performance_mode'] = 'standard'
            optimizations['optimization_level'] = 0
        
        # Level 1: Moderate optimization
        elif spoke_count <= 12 and aircraft_count <= 15:
            optimizations['performance_mode'] = 'optimized'
            optimizations['optimization_level'] = 1
            
            # Increase cache sizes
            self.distance_cache.max_size = 1500
            self.flight_time_cache.max_size = 750
            optimizations['cache_size_increased'] = True
            optimizations['recommendations'].append("Increased cache sizes for moderate complexity")
        
        # Level 2: High optimization
        elif spoke_count <= 15 and aircraft_count <= 20:
            optimizations['performance_mode'] = 'high_optimization'
            optimizations['optimization_level'] = 2
            
            # Maximum cache sizes
            self.distance_cache.max_size = 2000
            self.flight_time_cache.max_size = 1000
            optimizations['cache_size_increased'] = True
            
            # Enable aggressive memory management
            if current_performance.get('memory_usage_mb', 0) > 300:
                gc.collect()
                optimizations['garbage_collection_forced'] = True
                optimizations['recommendations'].append("Forced garbage collection due to high memory usage")
            
            optimizations['recommendations'].append("Maximum cache sizes enabled for high complexity")
        
        # Level 3: Maximum optimization
        else:
            optimizations['performance_mode'] = 'critical_optimization'
            optimizations['optimization_level'] = 3
            
            # Maximum cache sizes
            self.distance_cache.max_size = 2500
            self.flight_time_cache.max_size = 1200
            optimizations['cache_size_increased'] = True
            
            # Force cleanup
            gc.collect()
            optimizations['garbage_collection_forced'] = True
            
            # Enable emergency mode
            optimizations['recommendations'].append("Emergency optimization mode activated")
            optimizations['recommendations'].append("Consider reducing complexity for better performance")
        
        # Memory pressure handling
        memory_usage = current_performance.get('memory_usage_mb', 0)
        if memory_usage > 400:
            optimizations['recommendations'].append("High memory usage detected - monitor closely")
            if memory_usage > 450:
                optimizations['recommendations'].append("Critical memory usage - consider reducing complexity")
        
        return optimizations
    
    def _get_current_optimization_status(self, spoke_count: int, aircraft_count: int) -> Dict[str, Any]:
        """Get current optimization status."""
        return {
            'cache_size_increased': False,
            'memory_monitoring_enabled': True,
            'garbage_collection_forced': False,
            'performance_mode': 'standard',
            'optimization_level': self._calculate_optimization_level(spoke_count, aircraft_count),
            'recommendations': []
        }
    
    def get_simulation_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive simulation performance summary."""
        base_summary = self.get_performance_summary()
        
        simulation_summary = {
            'simulation_metrics': self.simulation_metrics.get_summary(),
            'performance_history': self._get_performance_history_summary(),
            'adaptive_optimization': {
                'enabled': self.adaptive_optimization,
                'last_adaptation': self.last_adaptation_check,
                'adaptation_interval': self.adaptation_interval
            },
            'optimization_recommendations': self._get_optimization_recommendations()
        }
        
        base_summary.update(simulation_summary)
        return base_summary
    
    def _get_performance_history_summary(self) -> Dict[str, Any]:
        """Get summary of performance history."""
        if not self.performance_history:
            return {'message': 'No performance history available'}
        
        recent_history = self.performance_history[-10:]  # Last 10 entries
        
        # Calculate trends
        if len(recent_history) >= 2:
            first_entry = recent_history[0]
            last_entry = recent_history[-1]
            
            memory_trend = last_entry['memory_usage'] - first_entry['memory_usage']
            response_trend = last_entry['response_time'] - first_entry['response_time']
            
            trends = {
                'memory_trend_mb': memory_trend,
                'response_time_trend_ms': response_trend,
                'memory_increasing': memory_trend > 0,
                'response_time_increasing': response_trend > 0
            }
        else:
            trends = {'message': 'Insufficient data for trend analysis'}
        
        return {
            'total_entries': len(self.performance_history),
            'recent_entries': len(recent_history),
            'trends': trends,
            'recent_performance': recent_history
        }
    
    def _get_optimization_recommendations(self) -> List[str]:
        """Get optimization recommendations based on performance history."""
        recommendations = []
        
        if not self.performance_history:
            return ["No performance data available for recommendations"]
        
        recent_history = self.performance_history[-5:]  # Last 5 entries
        
        # Memory usage recommendations
        memory_usage_trend = [entry['memory_usage'] for entry in recent_history]
        if len(memory_usage_trend) >= 2:
            if memory_usage_trend[-1] > memory_usage_trend[0] + 50:  # 50MB increase
                recommendations.append("Memory usage increasing rapidly - consider reducing complexity")
            
            if memory_usage_trend[-1] > 400:
                recommendations.append("High memory usage - monitor closely and consider optimization")
        
        # Response time recommendations
        response_time_trend = [entry['response_time'] for entry in recent_history]
        if len(response_time_trend) >= 2:
            if response_time_trend[-1] > response_time_trend[0] + 100:  # 100ms increase
                recommendations.append("Response time increasing - consider performance optimization")
        
        # Complexity recommendations
        if recent_history:
            latest = recent_history[-1]
            if latest['spoke_count'] > 12:
                recommendations.append("High spoke count - consider reducing for better performance")
            
            if latest['aircraft_count'] > 15:
                recommendations.append("Large fleet - monitor performance impact")
        
        if not recommendations:
            recommendations.append("Performance appears stable - no immediate action required")
        
        return recommendations
    
    def force_simulation_cleanup(self) -> None:
        """Force cleanup specifically for simulation operations."""
        logger.info("Forcing simulation performance cleanup")
        
        # Clear caches
        self.distance_cache.clear()
        self.flight_time_cache.clear()
        
        # Force garbage collection
        gc.collect()
        
        # Reset performance history
        self.performance_history.clear()
        
        # Reset simulation metrics
        self.simulation_metrics = SimulationPerformanceMetrics()
        
        logger.info("Simulation performance cleanup completed")


@dataclass
class SimulationPerformanceMetrics:
    """Performance metrics specific to simulation operations."""
    total_simulation_steps: int = 0
    average_step_time: float = 0.0
    peak_memory_usage: float = 0.0
    total_errors: int = 0
    recovery_attempts: int = 0
    performance_degradations: int = 0
    last_step_time: float = 0.0
    step_time_history: List[float] = field(default_factory=list)
    max_history_size: int = 20
    
    def update_metrics(self, performance_data: Dict[str, Any]) -> None:
        """Update metrics with new performance data."""
        self.total_simulation_steps += 1
        
        # Update step time
        if 'response_time' in performance_data:
            step_time = performance_data['response_time'] / 1000.0  # Convert to seconds
            self.last_step_time = step_time
            self.step_time_history.append(step_time)
            
            # Maintain history size
            if len(self.step_time_history) > self.max_history_size:
                self.step_time_history.pop(0)
            
            # Update average
            self.average_step_time = sum(self.step_time_history) / len(self.step_time_history)
        
        # Update peak memory usage
        if 'memory_usage' in performance_data:
            memory_usage = performance_data['memory_usage']
            if memory_usage > self.peak_memory_usage:
                self.peak_memory_usage = memory_usage
    
    def record_error(self) -> None:
        """Record an error occurrence."""
        self.total_errors += 1
    
    def record_recovery_attempt(self) -> None:
        """Record a recovery attempt."""
        self.recovery_attempts += 1
    
    def record_performance_degradation(self) -> None:
        """Record a performance degradation."""
        self.performance_degradations += 1
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of simulation performance metrics."""
        return {
            'total_simulation_steps': self.total_simulation_steps,
            'average_step_time': self.average_step_time,
            'last_step_time': self.last_step_time,
            'peak_memory_usage': self.peak_memory_usage,
            'total_errors': self.total_errors,
            'recovery_attempts': self.recovery_attempts,
            'performance_degradations': self.performance_degradations,
            'error_rate': self.total_errors / max(self.total_simulation_steps, 1),
            'recovery_success_rate': (self.recovery_attempts - self.performance_degradations) / max(self.recovery_attempts, 1) if self.recovery_attempts > 0 else 0.0
        }


# Enhanced performance decorator for simulation functions
class SimulationPerformanceDecorator(PerformanceDecorator):
    """Performance decorator specialized for simulation operations."""
    
    def __init__(self, optimizer: SimulationPerformanceOptimizer):
        super().__init__(optimizer)
        self.optimizer = optimizer
    
    def monitor_simulation_performance(self, func: Callable) -> Callable:
        """Decorator to monitor simulation function performance."""
        def wrapper(*args, **kwargs):
            start_time = time.time()
            start_memory = self.optimizer.memory_monitor.get_memory_usage()
            
            try:
                result = func(*args, **kwargs)
                
                # Record performance metrics
                end_time = time.time()
                end_memory = self.optimizer.memory_monitor.get_memory_usage()
                
                execution_time = end_time - start_time
                memory_delta = end_memory - start_memory
                
                # Update simulation metrics
                performance_data = {
                    'response_time_ms': execution_time * 1000,
                    'memory_usage_mb': end_memory,
                    'memory_delta_mb': memory_delta,
                    'function_name': func.__name__
                }
                
                # Update optimizer metrics
                self.optimizer.simulation_metrics.update_metrics(performance_data)
                
                # Log performance if significant
                if execution_time > 2.0:  # More than 2 seconds
                    logger.warning(f"Slow simulation operation: {func.__name__} took {execution_time:.2f}s")
                
                if memory_delta > 100:  # More than 100MB increase
                    logger.warning(f"High memory usage in simulation: {func.__name__} used {memory_delta:.1f}MB")
                
                return result
                
            except Exception as e:
                # Record error in metrics
                self.optimizer.simulation_metrics.record_error()
                logger.error(f"Error in simulation function {func.__name__}: {e}")
                raise
        
        return wrapper
