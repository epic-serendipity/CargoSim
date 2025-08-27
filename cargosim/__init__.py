"""CargoSim - Hub-and-spoke logistics simulator."""

__version__ = "0.1.0"

# Core functionality
from .core.config import (
    SimConfig, load_config, save_config, apply_theme_preset,
    THEME_PRESETS, AIRFRAME_COLORSETS, CURSOR_COLORS, validate_config
)
from .core.simulation import LogisticsSim, Aircraft
from .core.utils import clamp, ellipsize, setup_logging, get_logger

# Rendering and visualization
from .rendering.renderer import Renderer
from .rendering.recorder import Recorder, NullRecorder

# User interface
from .ui.gui import ControlGUI

# Advanced features
from .features.smart_targeting import SmartTargeting

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
