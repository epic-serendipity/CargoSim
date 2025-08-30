"""CargoSim - Hub-and-spoke logistics simulator."""

__version__ = "0.1.0"

# Core functionality
from cargosim.core.config import (
    SimConfig, load_config, save_config, apply_theme_preset,
    THEME_PRESETS, AIRFRAME_COLORSETS, CURSOR_COLORS, validate_config
)
from cargosim.core.simulation import LogisticsSim, Aircraft
from cargosim.core.utils import clamp, ellipsize, setup_logging, get_logger

# Rendering and visualization
from cargosim.rendering.renderer import Renderer
from cargosim.rendering.recorder import Recorder, NullRecorder

# User interface
from cargosim.ui.gui import ControlGUI

# Advanced features
from cargosim.features.smart_targeting import SmartTargeting

__all__ = [
    # Core
    "SimConfig", "LogisticsSim", "Aircraft", "validate_config",
    "load_config", "save_config", "apply_theme_preset", "THEME_PRESETS",
    "AIRFRAME_COLORSETS", "CURSOR_COLORS", "clamp", "ellipsize",
    "setup_logging", "get_logger",
    
    # Rendering
    "Renderer", "Recorder", "NullRecorder",
    
    # UI
    "ControlGUI",
    
    # Features
    "SmartTargeting"
]
