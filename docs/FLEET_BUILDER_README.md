# CargoSim Fleet Builder

The Fleet Builder is a powerful new feature in CargoSim that allows users to visually design custom fleet compositions using a drag-and-drop interface. It replaces the old hardcoded fleet system with a flexible, JSON-based configuration system that makes it easy to add new aircraft types and create custom fleet combinations.

## Features

### 🎨 Visual Fleet Composition Builder
- **Drag-and-Drop Interface**: Click on aircraft types to add them to your fleet
- **Real-Time Preview**: See fleet statistics update as you build
- **Interactive Controls**: Add/remove aircraft with simple buttons
- **Fleet Summary**: View total capacity, cost, and efficiency metrics

### 🚁 Flexible Aircraft Configuration
- **JSON-Based**: All aircraft types defined in `aircraft_config.json`
- **Easy to Extend**: Add new aircraft types without code changes
- **Rich Metadata**: Each aircraft has capacity, rest periods, capabilities, and more
- **Customizable**: Modify existing aircraft stats or add completely new types

### 📋 Fleet Presets
- **Pre-Built Configurations**: Standard fleet combinations ready to use
- **Save Custom Fleets**: Save your designs as reusable presets
- **Import/Export**: Share fleet configurations between users
- **Legacy Compatibility**: Works with existing fleet labels

### 🔄 Backward Compatibility
- **Legacy Support**: All existing fleet labels still work
- **Seamless Integration**: Fleet Builder integrates with existing simulation
- **Export Function**: Convert custom fleets to legacy format

## Getting Started

### 1. Access the Fleet Builder
1. Launch CargoSim with the GUI: `python -m cargosim`
2. Click on the **"Fleet Builder"** tab
3. The interface is divided into three main sections:
   - **Left**: Aircraft Palette (available aircraft types)
   - **Center**: Fleet Canvas (your current fleet)
   - **Right**: Fleet Presets (saved configurations)

### 2. Build Your Fleet
1. **Add Aircraft**: Click on any aircraft type in the Aircraft Palette
2. **View Statistics**: See real-time updates in the Fleet Summary
3. **Modify Fleet**: Use the +/- buttons to adjust aircraft counts
4. **Clear Fleet**: Use the "Clear Fleet" button to start over

### 3. Save and Use
1. **Name Your Fleet**: Enter a custom name in the Fleet Name field
2. **Save as Preset**: Click "Save as Preset" to store your design
3. **Export to Legacy**: Use "Export to Legacy Format" for compatibility
4. **Start Simulation**: Your fleet will be automatically used when you start

## Aircraft Types

### Current Aircraft
- **C-130 Hercules**: Medium tactical transport (Capacity: 6, Rest: 6 periods)
- **C-27J Spartan**: Light tactical transport (Capacity: 3, Rest: 12 periods)
- **C-17 Globemaster III**: Heavy strategic transport (Capacity: 15, Rest: 8 periods)
- **C-5 Galaxy**: Super heavy strategic transport (Capacity: 25, Rest: 10 periods)

### Aircraft Properties
Each aircraft type has the following properties:
- **Base Capacity**: How many resource units it can carry
- **Rest Periods**: How many periods it must rest after operations
- **Range Factor**: Relative range capability
- **Fuel Efficiency**: Relative fuel consumption
- **Maintenance Cost**: Relative maintenance requirements
- **Special Capabilities**: Unique features (tactical, strategic, etc.)

## Adding New Aircraft Types

### Method 1: Edit the JSON File
1. Open `cargosim/aircraft_config.json`
2. Add a new entry to the `aircraft_types` section:

```json
{
  "aircraft_types": {
    "C-295": {
      "name": "C-295 Medium Transport",
      "description": "Medium tactical transport aircraft",
      "base_capacity": 5,
      "rest_periods": 8,
      "range_factor": 0.9,
      "fuel_efficiency": 1.1,
      "maintenance_cost": 0.9,
      "special_capabilities": ["tactical", "medium_range"],
      "color": "#f59e0b",
      "icon": "C295",
      "default_count": 0
    }
  }
}
```

### Method 2: Programmatic Addition
```python
from cargosim.fleet_builder import get_aircraft_config_manager, AircraftType

config_manager = get_aircraft_config_manager()

new_aircraft = AircraftType(
    id="C-295",
    name="C-295 Medium Transport",
    description="Medium tactical transport aircraft",
    base_capacity=5,
    rest_periods=8,
    range_factor=0.9,
    fuel_efficiency=1.1,
    maintenance_cost=0.9,
    special_capabilities=["tactical", "medium_range"],
    color="#f59e0b",
    icon="C295",
    default_count=0
)

config_manager.add_aircraft_type(new_aircraft)
```

## Fleet Presets

### Built-in Presets
- **Light Fleet**: 2× C-27 for small operations
- **Standard Fleet**: 2× C-130 for typical operations
- **Heavy Fleet**: 4× C-130 for high-capacity operations
- **Mixed Fleet**: 2× C-130 + 2× C-27 for flexibility
- **Strategic Fleet**: 2× C-17 + 2× C-130 for long-range operations

### Creating Custom Presets
1. Build your fleet using the Fleet Builder
2. Enter a name for your fleet
3. Click "Save as Preset"
4. Your preset will appear in the Fleet Presets panel
5. Click "Load Preset" to use it later

## Advanced Features

### Fleet Optimization
The Fleet Builder provides real-time analysis of your fleet:
- **Total Capacity**: Combined resource carrying capacity
- **Maintenance Cost**: Relative operational cost
- **Efficiency Score**: Average fuel efficiency
- **Capabilities**: Special features available

### Custom Fleet Formats
The system supports various fleet specification formats:
- **Legacy Labels**: `2xC130`, `4xC130`, `2xC130_2xC27`
- **Custom Formats**: `3xC130_1xC27_2xC17`
- **Preset Names**: `"Heavy Fleet"`, `"Mixed Fleet"`

### Integration with Simulation
- **Automatic Loading**: Fleet Builder fleets automatically load into simulation
- **Configuration Sync**: Fleet changes are saved with your configuration
- **Performance Impact**: Fleet composition affects simulation behavior

## Troubleshooting

### Common Issues

**Fleet Builder tab not showing**
- Ensure all required modules are installed
- Check that `aircraft_config.json` exists and is valid JSON
- Look for import errors in the console

**Aircraft not appearing**
- Verify the aircraft is defined in `aircraft_config.json`
- Check that the JSON syntax is correct
- Ensure the aircraft ID matches exactly

**Fleet not loading in simulation**
- Use "Export to Legacy Format" to get the correct fleet label
- Copy the exported format to the Configuration tab
- Check that the fleet label is valid

### Debug Mode
Enable debug logging to see detailed information:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## File Structure

```
cargosim/
├── aircraft_config.json          # Aircraft definitions and presets
├── fleet_builder.py             # Core fleet building logic
├── fleet_builder_gui.py         # GUI components
└── ...
```

## API Reference

### Core Classes

#### `AircraftType`
Represents an aircraft type with all its properties.

#### `FleetComposition`
Represents a user-defined fleet with performance metrics.

#### `FleetBuilder`
Main class for creating and managing fleet compositions.

#### `AircraftConfigManager`
Manages aircraft type configurations and fleet presets.

### Key Methods

#### `FleetBuilder.add_aircraft(aircraft_id, count)`
Add aircraft to the current fleet.

#### `FleetBuilder.remove_aircraft(aircraft_id, count)`
Remove aircraft from the current fleet.

#### `FleetBuilder.export_fleet_to_legacy_format()`
Export the current fleet to legacy format for compatibility.

#### `AircraftConfigManager.add_aircraft_type(aircraft_type)`
Add a new aircraft type to the configuration.

## Contributing

### Adding New Features
1. **Fork the repository**
2. **Create a feature branch**
3. **Implement your changes**
4. **Add tests** (see `test_fleet_builder.py`)
5. **Submit a pull request**

### Testing
Run the test suite to ensure everything works:
```bash
python test_fleet_builder.py
```

### Code Style
- Follow PEP 8 guidelines
- Add type hints for all functions
- Include docstrings for all classes and methods
- Write comprehensive tests

## Future Enhancements

### Planned Features
- **3D Fleet Visualization**: 3D models of aircraft in fleet
- **Performance Analytics**: Detailed performance predictions
- **Mission Planning**: Assign specific aircraft to specific routes
- **Fleet Rotation**: Schedule maintenance and rest periods
- **Cost Analysis**: Detailed operational cost breakdown

### Community Contributions
We welcome contributions! Some areas that could use help:
- **New Aircraft Types**: Add more realistic aircraft specifications
- **Fleet Presets**: Create useful preset combinations
- **UI Improvements**: Enhance the visual interface
- **Performance Metrics**: Add more sophisticated analysis tools

## Support

### Getting Help
- **Documentation**: Check this README and the main CargoSim documentation
- **Issues**: Report bugs and feature requests on GitHub
- **Community**: Join discussions in the project repository

### Reporting Bugs
When reporting issues, please include:
- CargoSim version
- Operating system
- Python version
- Steps to reproduce
- Error messages or logs
- Screenshots (if applicable)

---

The Fleet Builder represents a significant evolution in CargoSim's fleet management capabilities. It provides the flexibility and ease of use that users have requested while maintaining full backward compatibility with existing simulations. Enjoy building your perfect fleet!
