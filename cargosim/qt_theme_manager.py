"""
Qt Theme Manager using QPalette for CargoSim.
Demonstrates how to apply consistent theming using palette overrides.
"""

from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtCore import Qt


class QtThemeManager:
    """Manages Qt application theming using QPalette."""
    
    def __init__(self, app: QApplication, theme_config):
        """Initialize with QApplication and theme config."""
        self.app = app
        self.theme_config = theme_config
        self._apply_theme()
    
    def _apply_theme(self):
        """Apply theme using QPalette."""
        palette = self._create_palette()
        self.app.setPalette(palette)
        
        # Apply to existing widgets
        for widget in self.app.topLevelWidgets():
            self._apply_palette_to_widget(widget, palette)
    
    def _create_palette(self) -> QPalette:
        """Create QPalette from theme configuration."""
        palette = QPalette()
        
        # Convert hex colors to QColor
        bg_color = QColor(self.theme_config.ui_bg)
        fg_color = QColor(self.theme_config.ui_fg)
        field_bg = QColor(self.theme_config.ui_field_bg)
        button_bg = QColor(self.theme_config.ui_button_bg)
        button_fg = QColor(self.theme_config.ui_button_fg)
        accent = QColor(self.theme_config.accent_primary)
        muted = QColor(self.theme_config.ui_muted)
        
        # Set palette colors
        palette.setColor(QPalette.ColorRole.Window, bg_color)
        palette.setColor(QPalette.ColorRole.WindowText, fg_color)
        palette.setColor(QPalette.ColorRole.Base, field_bg)
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(self.theme_config.ui_card_bg))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(self.theme_config.ui_card_bg))
        palette.setColor(QPalette.ColorRole.ToolTipText, fg_color)
        
        # Text and button colors
        palette.setColor(QPalette.ColorRole.Text, fg_color)
        palette.setColor(QPalette.ColorRole.Button, button_bg)
        palette.setColor(QPalette.ColorRole.ButtonText, button_fg)
        
        # Selection colors
        palette.setColor(QPalette.ColorRole.Highlight, accent)
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
        
        # Link colors
        palette.setColor(QPalette.ColorRole.Link, accent)
        palette.setColor(QPalette.ColorRole.LinkVisited, QColor(self.theme_config.accent_secondary))
        
        # Disabled states
        disabled_bg = QColor(self.theme_config.ui_disabled_bg)
        disabled_fg = QColor(self.theme_config.ui_disabled_fg)
        palette.setColor(QPalette.ColorRole.WindowText, disabled_fg, QPalette.ColorGroup.Disabled)
        palette.setColor(QPalette.ColorRole.Text, disabled_fg, QPalette.ColorGroup.Disabled)
        palette.setColor(QPalette.ColorRole.Button, disabled_bg, QPalette.ColorGroup.Disabled)
        palette.setColor(QPalette.ColorRole.ButtonText, disabled_fg, QPalette.ColorGroup.Disabled)
        
        return palette
    
    def _apply_palette_to_widget(self, widget: QWidget, palette: QPalette):
        """Recursively apply palette to widget and children."""
        if widget is None:
            return
        
        widget.setPalette(palette)
        
        # Apply to all child widgets
        for child in widget.findChildren(QWidget):
            child.setPalette(palette)
    
    def update_theme(self, new_theme_config):
        """Update theme with new configuration."""
        self.theme_config = new_theme_config
        self._apply_theme()


def apply_theme_to_widget(widget: QWidget, theme_config):
    """Apply theme to a single widget."""
    palette = QPalette()
    
    # Set basic colors
    palette.setColor(QPalette.ColorRole.Window, QColor(theme_config.ui_bg))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(theme_config.ui_fg))
    palette.setColor(QPalette.ColorRole.Base, QColor(theme_config.ui_field_bg))
    palette.setColor(QPalette.ColorRole.Button, QColor(theme_config.ui_button_bg))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(theme_config.ui_button_fg))
    
    widget.setPalette(palette)


def create_theme_palette(theme_config) -> QPalette:
    """Create QPalette from theme configuration."""
    palette = QPalette()
    
    # Base colors
    palette.setColor(QPalette.ColorRole.Window, QColor(theme_config.ui_bg))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(theme_config.ui_fg))
    palette.setColor(QPalette.ColorRole.Base, QColor(theme_config.ui_field_bg))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(theme_config.ui_card_bg))
    
    # Button colors
    palette.setColor(QPalette.ColorRole.Button, QColor(theme_config.ui_button_bg))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(theme_config.ui_button_fg))
    
    # Selection colors
    palette.setColor(QPalette.ColorRole.Highlight, QColor(theme_config.accent_primary))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    
    return palette
