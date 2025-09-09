# CargoSim - Hub-and-Spoke Logistics Simulator

A professional, modular Python package for simulating hub-and-spoke airlift networks with a 24-hour clock down to the minute. Aircraft ferry supplies to spokes and operations consume resources.

## Quickstart

### Installation
```bash
# Development installation
pip install -e .

# With video support
pip install -e .[video]
```

### Running
```bash
# GUI Control Panel
python -m cargosim

# Legacy entry point
python cargo_sim.py

# Headless mode
python -m cargosim --headless --duration-minutes 600 --seed 42

# Windowed mode
python -m cargosim --windowed

# Custom aircraft demo
python demo_custom_aircraft_visuals.py
```

## Architecture

CargoSim is built with a professional, modular architecture:

```
cargosim/
├── __init__.py          # Package initialization and exports
├── __main__.py          # CLI entry point
├── config.py            # Configuration management and validation
├── simulation.py        # Core simulation logic
├── renderer.py          # Pygame rendering and visualization
├── recorder.py          # Recording functionality (MP4/PNG)
├── gui.py              # Tkinter control panel
├── utils.py            # Utility functions and logging
└── main.py             # Main entry points and dependency management
```

## Core Concepts

- **Time**: Continuous 24-hour clock; simulation advances in minutes
- **Operations**: Can run only when a spoke has A, B, C, and D resources on hand
- **Resource Consumption**: Each operation consumes one unit of C and D
- **Arrivals**: Cargo arrivals apply immediately on unloading

## Features

### Visual Themes
- **Five Built-in Themes**: GitHub Dark, Classic Light, Solarized Light, Night Ops, Cyber
- **Customizable**: Cursor colors, overlay presets, aircraft color schemes
- **Responsive**: Fullscreen and windowed modes with dynamic layout

### Custom Aircraft
- **Unique Visual Representation**: Airplane-like shape (pointed front, wider back with wings)
- **Simple Design**: Clean appearance with subtle border, no fancy visual effects
- **Motion Trails**: Simple, subtle trails during transit
- **Basic Indicators**: Simple transit indicators without animations
- **Color Schemes**: Dedicated colors for all aircraft types including custom aircraft

### Recording System
- **Live Recording**: MP4 or PNG with async processing
- **Offline Rendering**: Batch processing with progress tracking
- **Flexible Output**: Customizable resolution, FPS, and format options
- **Performance**: Dropped-frame detection and queue management

### Control Panel
- **Configuration Tab**: Fleet settings, initial stocks, consumption cadence
- **Scheduling Tab**: Pair order, advanced decision making, statistics
- **Visual Tab**: Display options, side panels, cursor customization
- **Theme Tab**: Theme presets, color schemes, menu styling
- **Gameplay Tab**: Performance settings, debug options, launch preferences
- **Recording Tab**: Live and offline recording configuration
- **Start Tab**: Save configuration and launch simulation

### Gameplay Controls
- **SPACE**: Pause/Resume
- **←/→**: Step forward/backward
- **+/-**: Adjust simulation speed
- **R**: Reset simulation
- **D**: Toggle debug mode
- **ESC**: Open pause menu
- **F11**: Toggle fullscreen

## Advanced Features

### Decision Making
- **Fairness Cooldown**: Prevents aircraft from being overworked
- **Resource Targeting**: A/B target depth of supply management
- **Emergency Preemption**: Priority handling for critical resources
- **Deterministic RNG**: Reproducible simulation results

### Performance
- **Caching**: Optimized spoke position and aircraft rendering
- **Async Processing**: Non-blocking recording and file operations
- **Memory Management**: Efficient history tracking and state management

### Configuration
- **Validation**: Comprehensive configuration validation with helpful error messages
- **Persistence**: Automatic saving of user preferences and settings
- **Flexibility**: Support for custom fleet configurations and scenarios

## Testing

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_simulation.py

# Run with coverage
pytest --cov=cargosim tests/
```

## API Reference

### Core Classes
```python
from cargosim import SimConfig, LogisticsSim, Aircraft, Renderer

# Configuration
cfg = SimConfig()
cfg.fleet_label = "2xC130"
cfg.duration_minutes = 60 * 24

# Simulation
sim = LogisticsSim(cfg)
sim.step_period()

# Rendering
renderer = Renderer(sim)
renderer.run()
```

### Configuration Validation
```python
from cargosim import validate_config

issues = validate_config(cfg)
if issues:
    print("Configuration issues found:", issues)
```

### Logging
```python
from cargosim import setup_logging, get_logger

# Setup logging
logger = setup_logging(level="DEBUG", log_file="cargo_sim.log")

# Use in modules
logger = get_logger("simulation")
logger.info("Simulation started")
```

## Troubleshooting

### Missing Dependencies
```bash
# Install pygame (required)
pip install pygame

# Install MP4 support (optional)
pip install imageio-ffmpeg
```

### Common Issues
- **Import Errors**: Ensure you're using the package structure (`from cargosim import ...`)
- **Configuration Issues**: Use `validate_config()` to check for problems
- **Performance**: Check debug logs for dropped frames or memory issues
- **Recording**: Verify file permissions and available disk space

## Contributing

We welcome contributions! The modular architecture makes it easy to:

1. **Add New Features**: Extend existing modules or create new ones
2. **Improve Performance**: Optimize rendering, caching, or algorithms
3. **Enhance UI**: Improve the control panel or visualization
4. **Add Tests**: Expand test coverage for better quality assurance

### Development Setup
```bash
git clone <repository>
cd CargoSim
pip install -e .[dev]
pytest tests/
```

## License

This project is open source. See LICENSE file for details.

## Support

- **Issues**: Report bugs and feature requests on GitHub
- **Documentation**: Check the code docstrings and this README
- **Community**: Join discussions in the project repository

--- *CargoSim - Professional logistics simulation with a modular, maintainable architecture.*

### Fleet Builder
The Fleet Builder provides a visual interface for creating and managing aircraft fleets:

```bash
# Launch the Fleet Builder GUI
python demo_fleet_builder.py

# Or use the integrated Fleet Builder tab in the main GUI
python cargosim.py
```

**Features:**
- Drag-and-drop aircraft placement
- Fleet composition management
- Preset fleet configurations
- Custom aircraft configuration
- Fleet performance metrics

### Temporary Fleet System
The temporary fleet system allows users to test custom fleets without saving them permanently:

**Two Options:**
1. **Save as Preset**: Saves fleet permanently to `aircraft_config.json`
2. **Use Current Fleet**: Uses fleet temporarily for current session only

**Benefits:**
- Quick testing of experimental fleet configurations
- No clutter in permanent presets
- Session-based fleet management
- Seamless integration with simulation

**Usage:**
1. Create fleet in Fleet Builder GUI
2. Click "Use Current Fleet" for temporary use
3. Fleet is immediately available for simulation
4. Custom aircraft are fully visible and functional
5. Use "Save as Preset" to make it permanent

**Example Temporary Fleet:**
```json
{
  "fleet_label": "TEMP_2xCustom_Transport_1xC130",
  "duration_minutes": 30 * 24 * 60
}
```

This creates a fleet with 2 Custom_Transport aircraft and 1 C-130, available only for the current session.
