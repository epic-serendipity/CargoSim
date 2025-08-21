# CargoSim - Hub-and-Spoke Logistics Simulator

A professional, modular Python package for simulating hub-and-spoke airlift networks with daily AM/PM cadence. Aircraft ferry supplies to spokes and operations consume resources.

## 🚀 Quickstart

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
python -m cargosim --headless --periods 10 --seed 42

# Windowed mode
python -m cargosim --windowed
```

## 🏗️ Architecture

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

## 🎮 Core Concepts

- **Periods**: Alternate AM/PM; arrivals apply at the next period
- **Operations**: Can run only when a spoke has A, B, C, and D resources on hand
- **Resource Consumption**: Each operation consumes one unit of C and D
- **Resource Gating**: A and B gate operations per PM but are not consumed

## ✨ Features

### 🎨 Visual Themes
- **Five Built-in Themes**: GitHub Dark, Classic Light, Solarized Light, Night Ops, Cyber
- **Customizable**: Cursor colors, overlay presets, aircraft color schemes
- **Responsive**: Fullscreen and windowed modes with dynamic layout

### 📹 Recording System
- **Live Recording**: MP4 or PNG with async processing
- **Offline Rendering**: Batch processing with progress tracking
- **Flexible Output**: Customizable resolution, FPS, and format options
- **Performance**: Dropped-frame detection and queue management

### 🎯 Control Panel
- **Configuration Tab**: Fleet settings, initial stocks, consumption cadence
- **Scheduling Tab**: Pair order, advanced decision making, statistics
- **Visual Tab**: Display options, side panels, cursor customization
- **Theme Tab**: Theme presets, color schemes, menu styling
- **Gameplay Tab**: Performance settings, debug options, launch preferences
- **Recording Tab**: Live and offline recording configuration
- **Start Tab**: Save configuration and launch simulation

### 🎮 Gameplay Controls
- **SPACE**: Pause/Resume
- **←/→**: Step forward/backward
- **+/-**: Adjust simulation speed
- **R**: Reset simulation
- **D**: Toggle debug mode
- **ESC**: Open pause menu
- **F11**: Toggle fullscreen

## 🔧 Advanced Features

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

## 🧪 Testing

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_simulation.py

# Run with coverage
pytest --cov=cargosim tests/
```

## 📚 API Reference

### Core Classes
```python
from cargosim import SimConfig, LogisticsSim, Aircraft, Renderer

# Configuration
cfg = SimConfig()
cfg.fleet_label = "2xC130"
cfg.periods = 60

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

## 🚨 Troubleshooting

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

## 🤝 Contributing

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

## 📄 License

This project is open source. See LICENSE file for details.

## 🆘 Support

- **Issues**: Report bugs and feature requests on GitHub
- **Documentation**: Check the code docstrings and this README
- **Community**: Join discussions in the project repository

---

*CargoSim - Professional logistics simulation with a modular, maintainable architecture.*
