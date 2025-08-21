"""CargoSim - Hub-and-spoke logistics simulator."""

__version__ = "0.1.0"

from .config import (
    SimConfig, load_config, save_config, apply_theme_preset,
    THEME_PRESETS, AIRFRAME_COLORSETS, CURSOR_COLORS, validate_config
)
from .simulation import LogisticsSim, Aircraft
from .renderer import Renderer
from .recorder import Recorder, NullRecorder
from .gui import ControlGUI
from .utils import clamp, ellipsize, setup_logging, get_logger

__all__ = [
    "SimConfig", "LogisticsSim", "Aircraft", "Renderer",
    "Recorder", "NullRecorder", "ControlGUI", "load_config",
    "save_config", "apply_theme_preset", "THEME_PRESETS",
    "AIRFRAME_COLORSETS", "CURSOR_COLORS", "clamp", "ellipsize",
    "validate_config", "setup_logging", "get_logger"
]
