# CargoSim Configuration Files

This directory contains configuration files for CargoSim simulations.

## Directory Structure

### `default/`
Default configuration files that ship with CargoSim:
- `cargo_sim_config.json` - Main simulation configuration
- `aircraft_config.json` - Aircraft fleet definitions

### `examples/`
Example configuration files demonstrating different scenarios:
- `cargo_sim_smart_targeting_config.json` - Smart targeting example

### `user/`
User-specific configuration files (not tracked in git):
- Custom configurations
- User preferences
- Experimental setups

## Configuration Types

### 1. Main Simulation Config (`cargo_sim_config.json`)
Controls the core simulation parameters:
- Fleet configuration
- Initial resource stocks
- Simulation duration
- Resource consumption rates

### 2. Aircraft Config (`aircraft_config.json`)
Defines aircraft types and capabilities:
- Aircraft specifications
- Fleet compositions
- Performance characteristics

### 3. Smart Targeting Config (`cargo_sim_smart_targeting_config.json`)
Advanced targeting and decision-making:
- Resource targeting strategies
- Emergency preemption rules
- Fairness cooldown settings

## Usage

### Loading Configurations
```python
from cargosim.core import SimConfig

# Load default configuration
config = SimConfig.from_file("configs/default/cargo_sim_config.json")

# Load custom configuration
config = SimConfig.from_file("configs/user/my_config.json")
```

### Creating Custom Configs
1. Copy an existing config file to `configs/user/`
2. Modify the parameters as needed
3. Save with a descriptive name
4. Load in your simulation

### Resetting Generated Configs
When you want to wipe **all** user-generated configuration files (including backups and migration metadata) and start fresh, run:
```bash
python -m cargosim --reset-configs
```
This command deletes everything inside `configs/user/` and any stray migration artifacts, then exits. On the next launch CargoSim will recreate fresh defaults.

### Configuration Validation
```python
from cargosim.core import validate_config

issues = validate_config(config)
if issues:
    print("Configuration issues:", issues)
```

## File Locations

### Default Configs
- **Path**: `configs/default/`
- **Purpose**: Standard configurations
- **Git Status**: Tracked
- **Usage**: Reference and fallback

### Example Configs
- **Path**: `configs/examples/`
- **Purpose**: Demonstration and learning
- **Git Status**: Tracked
- **Usage**: Learning and testing

### User Configs
- **Path**: `configs/user/`
- **Purpose**: Personal customizations
- **Git Status**: Ignored
- **Usage**: Personal simulations

## Configuration Schema

### Main Config Structure
```json
{
  "fleet_label": "2xC130",
  "periods": 60,
  "initial_stocks": {
    "A": 10,
    "B": 10,
    "C": 10,
    "D": 10
  },
  "consumption_cadence": "PM"
}
```

### Aircraft Config Structure
```json
{
  "aircraft_types": {
    "C130": {
      "capacity": 4,
      "speed": 1.0,
      "color": "#FF6B6B"
    }
  }
}
```

## Best Practices

1. **Backup**: Keep backups of working configurations
2. **Validation**: Always validate configs before use
3. **Documentation**: Document custom configurations
4. **Versioning**: Include version information in configs
5. **Testing**: Test configs with small simulations first

## Troubleshooting

### Common Issues
- **Invalid JSON**: Check syntax with a JSON validator
- **Missing Fields**: Compare with default configs
- **Type Errors**: Ensure numeric fields contain numbers
- **Path Issues**: Use absolute paths or relative to project root

### Validation Errors
- **Resource Values**: Must be non-negative integers
- **Period Count**: Must be positive integer
- **Aircraft Types**: Must exist in aircraft config
- **Color Codes**: Must be valid hex colors

## Contributing

When adding new configurations:
1. Place in appropriate subdirectory
2. Include clear documentation
3. Test thoroughly
4. Update this README if needed
