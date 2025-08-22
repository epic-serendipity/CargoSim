# Smart Aircraft Targeting System for CargoSim

## Overview

The Smart Aircraft Targeting System replaces the old pair-based routing with an intelligent, scoring-based approach that:

- **Spreads aircraft out** rather than dog-piling on the same spokes
- **Prefers nearer spokes** (lower travel time/cost)
- **Chases the best operational payoff** (delivering what actually unlocks ops)
- **Is extensible** to real time-based movement later
- **Maintains fairness** by tracking recent service history

## Key Features

### 1. Scoring-Based Routing
Each aircraft evaluates all possible destinations using a transparent scoring function:

```
score(S) = w_ops × ops_gain_score(S) + w_need × need_score(S) - w_dist × dist_norm - w_cong × cong_penalty
```

### 2. Benefit Signals
- **Need Score**: How "hungry" a spoke is for resources
- **Ops Gain Score**: Likelihood of unlocking operations
- **Marginal Benefit**: Combined benefit considering aircraft capacity

### 3. Cost Signals
- **Distance Penalty**: Normalized distance from current location
- **Congestion Penalty**: Soft penalty for multiple aircraft heading to same spoke
- **Fairness Penalty**: Penalty for recently serviced spokes

### 4. Stage-Aware Planning
- **A-Priming Stage**: Prioritizes A resource deficits
- **B-Priming Stage**: Prioritizes B resource deficits  
- **OPS Stage**: Prioritizes C/D resources for operations

## Configuration

Enable smart targeting in your `cargo_sim_config.json`:

```json
{
  "smart_targeting_enabled": true,
  "smart_targeting_config": {
    "w_ops": 1.0,                    // Weight for ops unlock potential
    "w_need": 0.6,                   // Weight for resource deficits
    "w_dist": 0.8,                   // Weight for distance penalty
    "w_cong": 0.7,                   // Weight for congestion penalty
    "max_aircraft_per_spoke_per_period": 2,  // Max aircraft per spoke (null = unlimited)
    "second_leg_multiplier": 0.7,    // Benefit multiplier for second leg
    "fairness_decay": 0.8,           // How fast recent-service penalty fades
    "jitter_percent": 0.01           // Random variation for tie-breaking
  }
}
```

## Default Weights

The default weights are tuned for balanced performance:

- **w_ops = 1.0**: Unlocking operations is the highest priority
- **w_need = 0.6**: Feeding hungry spokes matters
- **w_dist = 0.8**: Prefer nearer spokes (will become travel time later)
- **w_cong = 0.7**: Discourage stampedes to the same spoke

## How It Works

### 1. Per-Period Planning Loop
For each idle aircraft:
1. Compute benefit signals for all spokes
2. Compute cost signals from aircraft's current location
3. Score all possible destinations
4. Choose the best spoke and reserve it
5. Optionally plan a second leg

### 2. Benefit Calculation
```python
# Resource deficits
deficit_A = max(0, 1 - stock[spoke][0])
deficit_B = max(0, 1 - stock[spoke][1])
deficit_C = max(0, 1 - stock[spoke][2])
deficit_D = max(0, 1 - stock[spoke][3])

# Stage-specific ops gain
if stage == "A":
    ops_gain = deficit_A
elif stage == "B":
    ops_gain = deficit_B
else:  # "OPS"
    ops_gain = (deficit_C + deficit_D) / 2
```

### 3. Cost Calculation
```python
# Distance penalty (normalized by P90 distance)
distance_norm = distance / distance_normalizer

# Congestion penalty
if spoke in period_reservations:
    congestion_penalty = count * 0.5  # Soft penalty
else:
    congestion_penalty = 0.0

# Fairness penalty
fairness_penalty = recent_service_count * (1 - fairness_decay)
```

### 4. Route Planning
```python
# Find best two-leg route
first_leg, second_leg = targeting.find_best_two_legs(
    aircraft_location, stock, stage, aircraft_capacity
)

# Reserve spokes
targeting.reserve_spoke(first_leg.spoke_idx)
if second_leg:
    targeting.reserve_spoke(second_leg.spoke_idx)
```

## Integration Points

### Simulation Integration
The system integrates seamlessly with the existing simulation:

- **Automatic Fallback**: Falls back to pair-based planning if smart targeting fails
- **State Tracking**: Tracks reservations, recent service, and fairness
- **Period Cleanup**: Clears reservations and decays service counts each period

### Renderer Integration
Positions are automatically synchronized:

```python
# Called from renderer when graphics pipeline initializes
sim.update_targeting_positions(hub_pos, spoke_positions)
```

## Future Extensions

### 1. Real Travel Time
When you introduce real travel time:

```python
# Replace distance with ETA
eta = distance / aircraft_speed
eta_norm = eta / eta_normalizer

# Mark aircraft as busy until arrival
aircraft.busy_until = current_time + eta
```

### 2. Value Per Time
For more realistic routing:

```python
# Score based on value per unit time
leg_value_rate = (benefit_score) / (epsilon + ETA)
```

### 3. Dynamic Weights
Adjust weights based on simulation state:

```python
# Increase distance penalty in later stages
if stage == "OPS":
    w_dist *= 1.2  # Prefer efficiency in ops stage
```

## Testing

### Unit Tests
```bash
python test_smart_targeting.py
```

### Integration Tests
```bash
python test_simulation_integration.py
```

### Configuration Test
Use the provided `cargo_sim_smart_targeting_config.json` to test with the GUI.

## Performance Considerations

- **Distance Matrix**: Precomputed once at startup, O(M²) space
- **Scoring**: O(M) per aircraft per period
- **Reservations**: O(1) hash set operations
- **Memory**: Minimal overhead (~1KB per spoke for tracking)

## Troubleshooting

### Common Issues

1. **No routes found**: Check if all spokes are fully stocked
2. **Poor distribution**: Adjust `w_dist` and `w_cong` weights
3. **Oscillations**: Increase `fairness_decay` or adjust `w_cong`

### Debug Mode
Enable debug mode to see detailed scoring:

```python
# In your config
"debug_mode": true

# The system will log scoring breakdowns
```

## Migration from Pair-Based Planning

The system is designed for easy migration:

1. **Enable smart targeting** in config
2. **Keep existing pair_order** as fallback
3. **Gradually adjust weights** based on performance
4. **Monitor operations** to ensure improvement

## Contributing

To extend the smart targeting system:

1. **Add new benefit signals** in `compute_spoke_benefits()`
2. **Add new cost signals** in `compute_spoke_costs()`
3. **Modify scoring function** in `score_spoke()`
4. **Update configuration** in `TargetingConfig`

The system is designed to be modular and extensible while maintaining the core scoring approach.
