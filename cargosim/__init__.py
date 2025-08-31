"""CargoSim - Hub-and-spoke logistics simulator.

This package exposes a convenient top-level API while keeping import-time
overhead low via lazy re-exports. Modules are imported on first attribute
access rather than at package import time.
"""

from typing import TYPE_CHECKING
import importlib

__version__ = "0.1.0"

# Public API surface
__all__ = [
    # Core
    "SimConfig",
    "LogisticsSim",
    "Aircraft",
    "validate_config",
    "load_config",
    "save_config",
    "apply_theme_preset",
    "THEME_PRESETS",
    "AIRFRAME_COLORSETS",
    "CURSOR_COLORS",
    "clamp",
    "ellipsize",
    "setup_logging",
    "get_logger",
    # Rendering
    "Renderer",
    "Recorder",
    "NullRecorder",
    # UI
    "ControlGUI",
    # Features
    "SmartTargeting",
]

_LAZY_ATTRS = {
    # Core
    "SimConfig": ("cargosim.core.config", "SimConfig"),
    "validate_config": ("cargosim.core.config", "validate_config"),
    "load_config": ("cargosim.core.config", "load_config"),
    "save_config": ("cargosim.core.config", "save_config"),
    "apply_theme_preset": ("cargosim.core.config", "apply_theme_preset"),
    "THEME_PRESETS": ("cargosim.core.config", "THEME_PRESETS"),
    "AIRFRAME_COLORSETS": ("cargosim.core.config", "AIRFRAME_COLORSETS"),
    "CURSOR_COLORS": ("cargosim.core.config", "CURSOR_COLORS"),
    "LogisticsSim": ("cargosim.core.simulation", "LogisticsSim"),
    "Aircraft": ("cargosim.core.simulation", "Aircraft"),
    "clamp": ("cargosim.core.utils", "clamp"),
    "ellipsize": ("cargosim.core.utils", "ellipsize"),
    "setup_logging": ("cargosim.core.utils", "setup_logging"),
    "get_logger": ("cargosim.core.utils", "get_logger"),
    # Rendering
    "Renderer": ("cargosim.rendering.renderer", "Renderer"),
    "Recorder": ("cargosim.rendering.recorder", "Recorder"),
    "NullRecorder": ("cargosim.rendering.recorder", "NullRecorder"),
    # UI
    "ControlGUI": ("cargosim.ui.gui", "ControlGUI"),
    # Features
    "SmartTargeting": ("cargosim.features.smart_targeting", "SmartTargeting"),
}


def __getattr__(name: str):
    target = _LAZY_ATTRS.get(name)
    if target is None:
        raise AttributeError(f"module 'cargosim' has no attribute {name!r}")
    mod_name, attr = target
    module = importlib.import_module(mod_name)
    return getattr(module, attr)


def __dir__():
    return sorted(list(globals().keys()) + list(__all__))
