# Changelog

All notable changes to CargoSim will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2024-12-19

### **Major Architectural Refactoring**

#### **Modular Package Structure**
- **BREAKING CHANGE**: Refactored from monolithic `cargo_sim.py` to professional Python package
- New package structure with clear separation of concerns:
  - `cargosim/config.py` - Configuration management and validation
  - `cargosim/simulation.py` - Core simulation logic
  - `cargosim/renderer.py` - Pygame rendering and visualization
  - `cargosim/recorder.py` - Recording functionality
  - `cargosim/gui.py` - Tkinter control panel
  - `cargosim/utils.py` - Utility functions and logging
  - `cargosim/main.py` - Main entry points and dependency management

#### **Package Exports and Imports**
- **NEW**: Proper package exports in `cargosim/__init__.py`
- **NEW**: Support for `from cargosim import SimConfig, LogisticsSim, Renderer`
- **NEW**: Module-specific imports: `from cargosim.simulation import Aircraft`
- **IMPROVED**: Backward compatibility maintained with `cargo_sim.py` entry point

### **Code Quality Improvements**

#### **Input Validation and Error Handling**
- **NEW**: Comprehensive input validation in renderer constructor
- **NEW**: Configuration validation with `validate_config()` function
- **NEW**: User-friendly error messages and validation feedback
- **IMPROVED**: Robust exception handling throughout the codebase

#### **Performance Optimizations**
- **NEW**: Caching system for expensive operations using `@lru_cache`
- **NEW**: Cached spoke position calculations and aircraft triangle vertices
- **NEW**: HUD element caching for text surfaces
- **IMPROVED**: Memory management with bounded data structures

#### **Magic Number Elimination**
- **NEW**: Named constants for animation, layout, menu, and rendering parameters
- **IMPROVED**: Better maintainability and readability
- **IMPROVED**: Consistent values across the application

### **GUI Enhancements**

#### **Complete Tab Implementations**
- **NEW**: Full implementation of all GUI tabs (previously stubs)
- **NEW**: Schedule tab with pair order, advanced decision making, and statistics
- **NEW**: Visual tab with display options, side panels, and cursor customization
- **NEW**: Theme tab with presets, color schemes, and menu styling
- **NEW**: Gameplay tab with performance settings, debug options, and launch preferences
- **NEW**: Recording tab with live and offline recording configuration

#### **Configuration Management**
- **NEW**: Complete `_read_back_to_cfg()` implementation
- **NEW**: File and folder browsing for recording paths
- **NEW**: Real-time theme preview functionality
- **IMPROVED**: Better user experience with comprehensive controls

### **Logging and Monitoring**

#### **Professional Logging System**
- **NEW**: `setup_logging()` function for configuration
- **NEW**: `get_logger()` function for module-specific loggers
- **NEW**: Console and file handlers with configurable levels
- **NEW**: Legacy `append_debug()` function maintained for backward compatibility
- **IMPROVED**: Better debugging, monitoring, and error tracking

### **Testing Infrastructure**

#### **Comprehensive Test Suite**
- **NEW**: `tests/test_simulation.py` with full test coverage
- **NEW**: Tests for Aircraft class, LogisticsSim, and utility functions
- **NEW**: Edge case testing and error condition validation
- **NEW**: Regression prevention through automated testing

### **Documentation and Organization**

#### **Updated Project Documentation**
- **NEW**: Comprehensive README with modular architecture overview
- **NEW**: Updated PROJECTMAP reflecting current package structure
- **NEW**: Enhanced AGENTS.md with development guidelines
- **NEW**: Professional pyproject.toml with comprehensive metadata
- **IMPROVED**: Clear documentation of all public APIs and usage patterns

### **Development Workflow**

#### **Modular Development**
- **NEW**: Each module has single, clear responsibility
- **NEW**: Clean interfaces between modules reduce coupling
- **NEW**: Easy to work on specific features without affecting others
- **NEW**: Clear dependency management and import structure

#### **Quality Assurance**
- **NEW**: Configuration validation prevents runtime errors
- **NEW**: Performance monitoring and optimization
- **NEW**: Comprehensive error handling and user feedback

## [0.1.0] - 2024-12-18

### **Initial Release**
- Basic hub-and-spoke logistics simulation
- Pygame-based visualization
- Tkinter control panel
- Recording functionality (MP4/PNG)
- Theme system with multiple presets
- Aircraft management and fleet operations

--- ## **Migration Guide**

### **From Monolithic to Modular**

#### **Import Changes**
```python
# OLD (monolithic)
from cargo_sim import LogisticsSim

# NEW (modular)
from cargosim import LogisticsSim
# OR
from cargosim.simulation import LogisticsSim
```

#### **Entry Point Changes**
```bash
# OLD
python cargo_sim.py

# NEW (recommended)
python -m cargosim

# NEW (legacy support)
python cargo_sim.py
```

#### **Configuration Validation**
```python
# NEW: Validate configuration before use
from cargosim import validate_config

issues = validate_config(cfg)
if issues:
    print("Configuration issues:", issues)
```

#### **Logging System**
```python
# NEW: Use professional logging
from cargosim import get_logger

logger = get_logger("module_name")
logger.info("Operation completed")
```

### **Backward Compatibility**

- All existing functionality preserved
- Configuration files remain compatible
- Legacy entry point (`cargo_sim.py`) still works
- Existing import patterns continue to function

--- ## **Contributing**

When contributing to CargoSim:

1. **Follow the modular architecture** - don't mix concerns between modules
2. **Add tests** for new functionality
3. **Update documentation** to reflect changes
4. **Use the logging system** for debugging and monitoring
5. **Validate configurations** with the validation system
6. **Cache expensive operations** using the existing caching infrastructure

--- *For detailed development guidelines, see [AGENTS.md](AGENTS.md)*
