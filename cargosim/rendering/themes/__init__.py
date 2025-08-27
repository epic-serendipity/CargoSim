"""
Theme management module for CargoSim.

This module contains the visual theme system, UI styling, and theme
configuration management.
"""

from .ui_theme import apply_theme, create_palette_from_theme_config
from .unified_theme_manager import UnifiedThemeManager

# Try to import Qt theme manager, but don't fail if PyQt6 is not available
try:
    from .qt_theme_manager import QtThemeManager
    QT_THEME_AVAILABLE = True
except ImportError:
    QtThemeManager = None
    QT_THEME_AVAILABLE = False

__all__ = [
    'apply_theme',
    'create_palette_from_theme_config',
    'UnifiedThemeManager',
    'QtThemeManager'
]
