# Project Map - CargoSim Modular Architecture

## **Package Structure**

CargoSim has been refactored into a professional, modular Python package:

```
cargosim/
├── __init__.py          # Package exports and initialization
├── __main__.py          # CLI entry point with argument parsing
├── config.py            # Configuration management and validation
├── simulation.py        # Core simulation logic and aircraft management
├── renderer.py          # Pygame rendering with performance optimizations
├── recorder.py          # Recording system (MP4/PNG) with async support
├── gui.py              # Tkinter control panel with complete tab implementations
├── utils.py            # Utility functions, logging, and performance helpers
└── main.py             # Main entry points and dependency management
```

## **Theme System**

Core theme tokens are stored in `ThemeConfig`:
- `menu_theme` (dark/light)
- `game_bg`, `game_fg`, `game_muted`
- `hub_color`, `good_spoke`, `bad_spoke`
- `bar_A`, `bar_B`, `bar_C`, `bar_D`
- `ac_colors` populated from the selected airframe color map

At runtime the renderer derives:
- `panel_bg`, `panel_btn`, `panel_btn_fg`
- `overlay_backdrop_rgba`

from core tokens using shared `hex2rgb` and `blend(a,b,t)` helpers so all surfaces stay on theme.

Both the interactive `Renderer` and offline `Headless` renderer compute and use these values so offline frames match the on‑screen simulation.

Presets supply core tokens and may specify a `default_airframe_colorset` for first‑run defaults. Switching presets does not modify the user's chosen airframe colors.

Cursor highlight color is stored by name in `SimConfig.cursor_color` and mapped internally via `CURSOR_COLORS` to fixed hex values. UI elements show only the names (Cobalt, Signal Orange, Cyber Lime, Cerulean, Royal Magenta).

## **Visualization & Rendering**

### Right-side Fullscreen Panel Modes
- `ops_total_number` (default) shows a large running total of OFFLOAD operations
- `ops_total_sparkline` plots a sparkline of recent totals (up to 120 points)
- `per_spoke` shows legacy per-spoke bars

### Aircraft Rendering
- Aircraft glyphs can optionally rotate toward their current destination when `orient_aircraft` is enabled
- On departure from the hub, the heading smoothly interpolates from north to the leg heading over the first ~15% of the segment
- When parked at the hub, glyphs are forced to face north
- Performance optimizations include cached triangle vertices and spoke positions

### Layout System
- Dynamic layout computation with safe area padding and side rails
- Responsive design that adapts to window resizing
- Cached font rendering and HUD elements for performance

## **Recording System**

### Live Recording
- Disabled until the user selects an existing output folder
- Producer/consumer queue with optional asynchronous writer thread
- When the queue fills, frames may be dropped rather than blocking the GUI
- HUD shows dropped frame counts for monitoring

### Offline Rendering
- Requires explicit file path configuration
- Render button spawns background process with progress tracking
- Cancel/Reveal buttons for user control
- Polling cadence is configurable
- All saved paths are normalized to absolute form in the config file

### Headless Rendering
- Creates hidden 1×1 display using SDL "dummy" driver
- Surface conversions like `convert_alpha()` succeed without visible window
- Overlay pipeline: HUD/overlays → Pygame surface → scaling → encoding to MP4/PNG

### Performance Features
- Static text surfaces and hub/spoke geometry are cached
- `ops_total_history` is bounded to most recent 2000 points
- Async processing prevents GUI blocking during recording

## **Advanced Decision Making & Gameplay**

### Configuration Structure
- `SimConfig.adm` holds fairness cooldowns, target days-of-supply for A/B, emergency preemption toggle, and deterministic seed
- `SimConfig.gameplay` contains realism toggles, leg time radius ranges, and fleet optimization weights

### Decision Making Features
- **Fairness Cooldown**: Prevents aircraft from being overworked
- **Resource Targeting**: A/B target depth of supply management
- **Emergency Preemption**: Priority handling for critical resources
- **Deterministic RNG**: Reproducible simulation results with configurable seeds

## **Configuration & Validation**

### Configuration Management
- Comprehensive configuration validation with `validate_config()` function
- Automatic saving of user preferences and settings
- Support for custom fleet configurations and scenarios
- Theme presets and color scheme management

### Validation Features
- Basic parameter validation (periods, capacities, rest periods)
- Consumption cadence validation
- Initial stock validation
- Pair order structure validation
- Theme and color validation

## **Performance & Optimization**

### Caching System
- `@lru_cache` for spoke position calculations
- `@lru_cache` for aircraft triangle vertices
- Cached spoke positions in graphics pipeline initialization
- HUD element caching for text surfaces

### Memory Management
- Efficient history tracking and state management
- Bounded data structures to prevent unbounded growth
- Optimized rendering pipeline with minimal object creation

## **Testing & Quality Assurance**

### Test Infrastructure
- Comprehensive test suite in `tests/test_simulation.py`
- Coverage for Aircraft class, LogisticsSim, and utility functions
- Edge case testing and error condition validation
- Regression prevention through automated testing

### Code Quality
- Comprehensive type hints throughout
- Professional logging system with configurable levels
- Error handling with user-friendly messages
- Performance monitoring and optimization

## **Entry Points & Usage**

### Package Usage
```python
# Import from package
from cargosim import SimConfig, LogisticsSim, Renderer

# Direct module imports
from cargosim.simulation import Aircraft
from cargosim.config import validate_config
```

### Command Line Interface
```bash
# GUI mode
python -m cargosim

# Headless mode
python -m cargosim --headless --periods 10 --seed 42

# Windowed mode
python -m cargosim --windowed
```

### Legacy Support
- `cargo_sim.py` maintains backward compatibility
- All existing functionality preserved
- Configuration files remain compatible

## **Development Workflow**

### Modular Development
- Each module has single, clear responsibility
- Clean interfaces between modules reduce coupling
- Easy to work on specific features without affecting others
- Clear dependency management and import structure

### Testing & Validation
- Unit tests for individual modules
- Integration tests for full system functionality
- Configuration validation prevents runtime errors
- Performance monitoring and optimization

--- *This project map reflects the current state of CargoSim as a professional, modular Python package with comprehensive features, testing, and documentation.*
