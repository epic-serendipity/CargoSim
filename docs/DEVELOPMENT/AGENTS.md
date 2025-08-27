# Agent Notes - CargoSim Development Guidelines

##  **Architecture Overview**

CargoSim is now a professional, modular Python package. When making changes:

- **Import Structure**: Use `from cargosim import ...` for public APIs, `from .module import ...` for internal imports
- **Module Responsibilities**: Each module has a single, clear purpose - don't mix concerns
- **Configuration**: All new settings go through `SimConfig` with proper validation
- **Testing**: Add tests for new functionality in the appropriate test file

##  **Adding a Theme Preset**

### Core Requirements
- Provide all core tokens: `menu_theme`, `game_bg`, `game_fg`, `game_muted`,
  `hub_color`, `good_spoke`, `bad_spoke`, `bar_A`, `bar_B`, `bar_C`, `bar_D`
- Ensure contrast between `game_fg` and `game_bg` is ≥ 4.5:1 for HUD text
- Bars A/B/C/D must be perceptually distinct
- Never override a user's selected airframe color map (`ac_colors`)

### Implementation Details
- Renderer derives `panel_bg`, `panel_btn`, `panel_btn_fg` and `overlay_backdrop_rgba` from `game_bg` + `hub_color`
- Avoid hardcoded greys; always use theme tokens
- Cyber theme must use only green on black; bad spokes pulse with a dashed ring
- New presets must not introduce hardcoded colors elsewhere

### Location
- Add new presets to `cargosim/config.py` in the `THEME_PRESETS` dictionary
- Update `CONFIG_VERSION` if changing the theme schema

##  **Cursor Color System**

- UI shows only color names; hex codes live in `CURSOR_COLORS` in `config.py`
- Exactly five options are supported: Cobalt, Red, Green, Blue, Yellow
- No greys or neutrals allowed
- Colors are applied in the renderer via `hex2rgb()` conversion

##  **Overlay and Recording Stats**

### Recording Overlays
- When adding recording overlay stats, draw them in both interactive and headless renderers
- Use the `Renderer` class methods for consistency
- Respect the `include_hud`, `include_panels`, and `include_debug` recording flags

### Performance Considerations
- Cache expensive calculations using `@lru_cache` decorator
- Use the existing `_hud_cache` system for text surfaces
- Avoid creating new objects in render loops

##  **Coding Standards**

### Style and Structure
- Follow existing snake_case style and keep functions compact
- Use comprehensive type hints for all public functions
- Add docstrings for all public methods and classes
- Keep modules focused on single responsibilities

### Configuration Management
- Persist new `SimConfig` fields via `to_json` / `from_json` methods
- Bump `CONFIG_VERSION` when changing schema
- Add validation rules to `validate_config()` function
- Use `hasattr()` checks for backward compatibility

### Error Handling
- Use the new logging system: `from cargosim import get_logger`
- Provide user-friendly error messages
- Validate inputs early and fail gracefully
- Log errors with appropriate levels (DEBUG, INFO, WARNING, ERROR)

### Non-blocking Design
- Prefer non-blocking design for recording operations
- Respect queue limits and dropping behavior controlled by config
- Use async processing where appropriate
- Don't block the GUI thread with long operations

##  **Testing Requirements**

### Test Structure
- All new functionality must have corresponding tests
- Tests go in `tests/test_*.py` files
- Use pytest fixtures for common setup
- Test both success and failure cases

### Test Commands
```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_simulation.py

# Run with coverage
pytest --cov=cargosim tests/

# Syntax check
python -m py_compile cargosim/*.py
```

### Legacy Testing
- `python cargo_sim.py --offline-render` (may fail if pygame missing)
- `python -m cargosim --help` to verify CLI functionality

##  **Module-Specific Guidelines**

### `config.py`
- Add new configuration fields to appropriate dataclasses
- Update validation functions for new fields
- Maintain backward compatibility in `from_json` methods
- Use constants for magic numbers and limits

### `simulation.py`
- Keep simulation logic pure and testable
- Use type hints for all parameters and return values
- Add logging for important state changes
- Maintain history for undo/redo functionality

### `renderer.py`
- Cache expensive calculations and surfaces
- Use the constants defined at the top of the file
- Handle window resizing gracefully
- Maintain consistent theme application

### `gui.py`
- Keep tab implementations focused and organized
- Use the existing style system for consistency
- Validate user inputs before applying changes
- Provide helpful tooltips and error messages

### `utils.py`
- Add utility functions that could be used across modules
- Use the logging system for debug information
- Keep functions pure and testable
- Document performance characteristics

##  **Performance Guidelines**

### Caching
- Use `@lru_cache` for expensive calculations
- Cache rendered surfaces and text elements
- Avoid recreating objects in render loops
- Use the existing caching systems in the renderer

### Memory Management
- Bound data structures to prevent unbounded growth
- Use efficient data types (lists vs. generators)
- Clean up resources properly in destructors
- Monitor memory usage in debug mode

### Rendering Optimization
- Batch similar drawing operations
- Use dirty rectangle techniques where appropriate
- Minimize surface conversions and copies
- Profile performance-critical sections

##  **Debugging and Logging**

### Logging System
```python
from cargosim import get_logger

logger = get_logger("module_name")
logger.debug("Debug information")
logger.info("General information")
logger.warning("Warning message")
logger.error("Error message")
```

### Debug Mode
- Use `cfg.debug_mode` to control debug features
- Add debug overlays that can be toggled
- Log important state changes and decisions
- Provide debug information in the HUD when enabled

##  **Documentation Requirements**

### Code Documentation
- All public functions must have docstrings
- Include type hints for all parameters
- Document return values and exceptions
- Provide usage examples for complex functions

### API Documentation
- Update `cargosim/__init__.py` when adding new public APIs
- Keep the `__all__` list current
- Document breaking changes clearly
- Maintain backward compatibility where possible

---

*These guidelines ensure CargoSim maintains its professional, modular architecture while adding new features and improvements.*
