"""
Unified Theme Manager for CargoSim.
Integrates existing Tkinter theming with QPalette-based Qt theming.
Provides consistent theme management across both widget systems.
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional, Dict, Any
import sys
import logging

# Set up logging
logger = logging.getLogger(__name__)

# Try to import Qt components (optional)
try:
    from PyQt6.QtWidgets import QApplication, QWidget
    from PyQt6.QtGui import QPalette, QColor
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False
    QApplication = None
    QWidget = None
    QPalette = None
    QColor = None

from .config import ThemeConfig, apply_theme_preset


class UnifiedThemeManager:
    """
    Unified theme manager that handles both Tkinter and Qt theming.
    Integrates with existing CargoSim theme system.
    """
    
    def __init__(self, tk_root: Optional[tk.Tk] = None, qt_app: Optional[QApplication] = None):
        """
        Initialize the unified theme manager.
        
        Args:
            tk_root: Tkinter root window (optional)
            qt_app: Qt application instance (optional)
        """
        self.tk_root = tk_root
        self.qt_app = qt_app
        self.current_theme: Optional[ThemeConfig] = None
        self.qt_theme_manager = None
        
        # Initialize Qt theme manager if available
        if QT_AVAILABLE and qt_app:
            self._init_qt_theme_manager()
    
    def _init_qt_theme_manager(self):
        """Initialize Qt theme manager if Qt is available."""
        if not QT_AVAILABLE or not self.qt_app:
            return
            
        try:
            from .qt_theme_manager import QtThemeManager
            if self.current_theme:
                self.qt_theme_manager = QtThemeManager(self.qt_app, self.current_theme)
        except ImportError:
            logger.warning("Qt theme manager not available")
    
    def set_theme(self, theme_config: ThemeConfig, force_refresh: bool = True):
        """
        Set the current theme and apply it to all widget systems.
        
        Args:
            theme_config: Theme configuration to apply
            force_refresh: Whether to force refresh all widgets
        """
        self.current_theme = theme_config
        
        # Apply to Tkinter if available
        if self.tk_root:
            self._apply_tkinter_theme(theme_config, force_refresh)
        
        # Apply to Qt if available
        if self.qt_theme_manager:
            self._apply_qt_theme(theme_config)
    
    def apply_theme_preset(self, preset_name: str, force_refresh: bool = True):
        """
        Apply a theme preset by name.
        
        Args:
            preset_name: Name of the theme preset to apply
            force_refresh: Whether to force refresh all widgets
        """
        if not self.current_theme:
            # Create default theme if none exists
            self.current_theme = ThemeConfig()
        
        # Apply the preset
        apply_theme_preset(self.current_theme, preset_name)
        
        # Apply the updated theme
        self.set_theme(self.current_theme, force_refresh)
    
    def _apply_tkinter_theme(self, theme_config: ThemeConfig, force_refresh: bool = True):
        """Apply theme to Tkinter widgets using existing system."""
        if not self.tk_root:
            return
        
        try:
            # Get the style object
            style = ttk.Style()
            
            # Apply base colors
            bg = theme_config.ui_bg
            fg = theme_config.ui_fg
            primary = theme_config.accent_primary
            secondary = theme_config.accent_secondary
            success = theme_config.success
            warning = theme_config.warning
            error = theme_config.error
            info = theme_config.info
            
            # Derived colors
            border_color = theme_config.ui_border
            card_bg = theme_config.ui_card_bg
            field_bg = theme_config.ui_field_bg
            hover_bg = theme_config.ui_hover_bg
            active_bg = theme_config.ui_active_bg
            disabled_bg = theme_config.ui_disabled_bg
            disabled_fg = theme_config.ui_disabled_fg
            
            # Configure base styles
            style.configure("TFrame", background=bg)
            style.configure("TLabel", background=bg, foreground=fg)
            style.configure("Header.TLabel", background=bg, foreground=primary, 
                          font=("TkDefaultFont", 10, "bold"))
            style.configure("Muted.TLabel", background=bg, foreground=theme_config.ui_muted)
            style.configure("Card.TFrame", background=card_bg, relief="flat", 
                          borderwidth=1, bordercolor=border_color)
            
            # Button styles
            self._configure_tkinter_buttons(style, theme_config)
            
            # Input control styles
            self._configure_tkinter_inputs(style, theme_config)
            
            # Selection control styles
            self._configure_tkinter_selections(style, theme_config)
            
            # Scale and progress styles
            self._configure_tkinter_scales(style, theme_config)
            
            # Tab and notebook styles
            self._configure_tkinter_tabs(style, theme_config)
            
            # Treeview and other complex widgets
            self._configure_tkinter_complex(style, theme_config)
            
            # Update root window
            self.tk_root.configure(bg=bg)
            
            # Set global options
            self._set_tkinter_global_options(theme_config)
            
            # Force refresh if requested
            if force_refresh:
                self._force_tkinter_refresh()
                
        except Exception as e:
            logger.warning(f"Could not apply Tkinter theme: {e}")
    
    def _configure_tkinter_buttons(self, style: ttk.Style, theme_config: ThemeConfig):
        """Configure Tkinter button styles."""
        # Standard button
        style.configure("TButton", 
                       padding=(12, 6), 
                       relief="flat", 
                       background=theme_config.ui_button_bg, 
                       foreground=theme_config.ui_button_fg,
                       borderwidth=1,
                       bordercolor=theme_config.ui_button_border,
                       focusthickness=2)
        
        style.map("TButton",
                   background=[("active", theme_config.ui_button_hover_bg), 
                              ("disabled", theme_config.ui_disabled_bg)],
                   foreground=[("disabled", theme_config.ui_disabled_fg)],
                   bordercolor=[("active", theme_config.accent_primary), 
                               ("focus", theme_config.accent_primary)],
                   relief=[("pressed", "sunken")])
        
        # Primary button
        style.configure("Primary.TButton", 
                       background=theme_config.ui_button_primary_bg, 
                       foreground=theme_config.ui_button_primary_fg, 
                       padding=(16, 8), 
                       relief="flat", 
                       bordercolor=theme_config.ui_button_primary_border,
                       focusthickness=3,
                       font=("TkDefaultFont", 9, "bold"))
        
        # Secondary button
        style.configure("Secondary.TButton", 
                       background=theme_config.ui_button_secondary_bg, 
                       foreground=theme_config.ui_button_secondary_fg, 
                       padding=(16, 8), 
                       relief="flat", 
                       bordercolor=theme_config.ui_button_secondary_border,
                       focusthickness=3,
                       font=("TkDefaultFont", 9, "bold"))
        
        # Success, Warning, Error buttons
        for btn_type, color in [("Success", theme_config.success), 
                               ("Warning", theme_config.warning), 
                               ("Error", theme_config.error)]:
            style.configure(f"{btn_type}.TButton", 
                           background=getattr(theme_config, f"ui_button_{btn_type.lower()}_bg"),
                           foreground=getattr(theme_config, f"ui_button_{btn_type.lower()}_fg"),
                           padding=(16, 8), 
                           relief="flat", 
                           bordercolor=color,
                           focusthickness=3,
                           font=("TkDefaultFont", 9, "bold"))
    
    def _configure_tkinter_inputs(self, style: ttk.Style, theme_config: ThemeConfig):
        """Configure Tkinter input control styles."""
        # Entry
        style.configure("TEntry", 
                       fieldbackground=theme_config.ui_entry_bg, 
                       foreground=theme_config.ui_entry_fg,
                       bordercolor=theme_config.ui_entry_border,
                       focuscolor=theme_config.ui_entry_focus_border,
                       insertcolor=theme_config.ui_entry_fg)
        
        # Spinbox
        style.configure("TSpinbox", 
                       fieldbackground=theme_config.ui_spinbox_bg, 
                       foreground=theme_config.ui_spinbox_fg,
                       bordercolor=theme_config.ui_spinbox_border,
                       focuscolor=theme_config.ui_spinbox_focus_border,
                       insertcolor=theme_config.ui_spinbox_fg,
                       arrowsize=16,
                       buttonbackground=theme_config.ui_spinbox_bg,
                       buttonforeground=theme_config.accent_primary,
                       buttonuprelief="flat",
                       buttondownrelief="flat")
        
        # Combobox
        style.configure("TCombobox", 
                       fieldbackground=theme_config.ui_combobox_bg, 
                       foreground=theme_config.accent_primary,
                       bordercolor=theme_config.ui_combobox_border,
                       focuscolor=theme_config.ui_combobox_focus_border,
                       insertcolor=theme_config.accent_primary,
                       selectbackground=theme_config.ui_selection_bg,
                       selectforeground=theme_config.ui_selection_fg)
    
    def _configure_tkinter_selections(self, style: ttk.Style, theme_config: ThemeConfig):
        """Configure Tkinter selection control styles."""
        # Checkbox
        style.configure("TCheckbutton", 
                       background=theme_config.ui_checkbox_bg, 
                       foreground=theme_config.ui_checkbox_fg,
                       bordercolor=theme_config.ui_checkbox_border,
                       focuscolor=theme_config.accent_primary,
                       indicatorcolor=theme_config.ui_checkbox_bg,
                       indicatorrelief="flat",
                       indicatorborderwidth=1,
                       indicatorbordercolor=theme_config.ui_checkbox_border)
        
        style.map("TCheckbutton",
                   indicatorcolor=[("selected", theme_config.ui_checkbox_selected_bg), 
                                  ("disabled", theme_config.ui_disabled_bg)],
                   foreground=[("disabled", theme_config.ui_disabled_fg)])
        
        # Radiobutton
        style.configure("TRadiobutton", 
                       background=theme_config.ui_radiobutton_bg, 
                       foreground=theme_config.ui_radiobutton_fg,
                       bordercolor=theme_config.ui_radiobutton_border,
                       focuscolor=theme_config.accent_primary,
                       indicatorcolor=theme_config.ui_radiobutton_bg,
                       indicatorrelief="flat",
                       indicatorborderwidth=1,
                       indicatorbordercolor=theme_config.ui_radiobutton_border)
        
        style.map("TRadiobutton",
                   indicatorcolor=[("selected", theme_config.ui_radiobutton_selected_bg), 
                                  ("disabled", theme_config.ui_disabled_bg)],
                   foreground=[("disabled", theme_config.ui_disabled_fg)])
    
    def _configure_tkinter_scales(self, style: ttk.Style, theme_config: ThemeConfig):
        """Configure Tkinter scale and progress styles."""
        # Horizontal scale
        style.configure("Horizontal.TScale", 
                       background=theme_config.ui_scale_bg,
                       troughcolor=theme_config.ui_scale_trough,
                       bordercolor=theme_config.ui_border,
                       focuscolor=theme_config.accent_primary,
                       sliderrelief="flat",
                       sliderlength=20,
                       sliderthickness=8)
        
        # Vertical scale
        style.configure("Vertical.TScale", 
                       background=theme_config.ui_scale_bg,
                       troughcolor=theme_config.ui_scale_trough,
                       bordercolor=theme_config.ui_border,
                       focuscolor=theme_config.accent_primary,
                       sliderrelief="flat",
                       sliderlength=20,
                       sliderthickness=8)
        
        # Progress bar
        style.configure("Horizontal.TProgressbar", 
                       background=theme_config.ui_progressbar_bg,
                       troughcolor=theme_config.ui_progressbar_trough,
                       bordercolor=theme_config.ui_border)
    
    def _configure_tkinter_tabs(self, style: ttk.Style, theme_config: ThemeConfig):
        """Configure Tkinter tab and notebook styles."""
        # Notebook
        style.configure("Tabs.TNotebook", 
                       background=theme_config.ui_notebook_bg, 
                       borderwidth=0,
                       relief="flat")
        
        # Tab
        style.configure("Tabs.TNotebook.Tab", 
                       padding=(20, 10), 
                       background=theme_config.ui_tab_bg, 
                       foreground=theme_config.ui_tab_fg, 
                       borderwidth=1,
                       bordercolor=theme_config.ui_tab_border,
                       relief="flat",
                       font=("TkDefaultFont", 9, "bold"))
        
        style.map("Tabs.TNotebook.Tab",
                   background=[("selected", theme_config.ui_tab_selected_bg), 
                              ("active", theme_config.ui_hover_bg)],
                   foreground=[("selected", theme_config.ui_tab_selected_fg), 
                              ("active", theme_config.ui_fg)],
                   bordercolor=[("selected", theme_config.accent_primary), 
                               ("active", theme_config.ui_border), 
                               ("!selected", theme_config.ui_tab_border)])
    
    def _configure_tkinter_complex(self, style: ttk.Style, theme_config: ThemeConfig):
        """Configure Tkinter complex widget styles."""
        # Treeview
        style.configure("Treeview", 
                       background=theme_config.ui_treeview_bg, 
                       foreground=theme_config.ui_treeview_fg,
                       bordercolor=theme_config.ui_treeview_border,
                       fieldbackground=theme_config.ui_treeview_bg)
        
        style.configure("Treeview.Heading", 
                       background=theme_config.ui_treeview_heading_bg, 
                       foreground=theme_config.ui_treeview_heading_fg,
                       bordercolor=theme_config.ui_treeview_heading_border)
        
        # Labelframe
        style.configure("TLabelframe", 
                       background=theme_config.ui_labelframe_bg,
                       relief="flat",
                       borderwidth=1,
                       bordercolor=theme_config.ui_labelframe_border)
        
        style.configure("TLabelframe.Label", 
                       background=theme_config.ui_labelframe_label_bg,
                       foreground=theme_config.ui_labelframe_label_fg,
                       relief="flat",
                       borderwidth=0)
    
    def _set_tkinter_global_options(self, theme_config: ThemeConfig):
        """Set global Tkinter options for consistent theming."""
        if not self.tk_root:
            return
        
        bg = theme_config.ui_bg
        
        # Set global options for all widgets
        self.tk_root.option_add('*TFrame*background', bg)
        self.tk_root.option_add('*TLabel*background', bg)
        self.tk_root.option_add('*TEntry*fieldbackground', theme_config.ui_entry_bg)
        self.tk_root.option_add('*TSpinbox*fieldbackground', theme_config.ui_spinbox_bg)
        self.tk_root.option_add('*TCheckbutton*background', theme_config.ui_checkbox_bg)
        self.tk_root.option_add('*TRadiobutton*background', theme_config.ui_radiobutton_bg)
        self.tk_root.option_add('*TMenubutton*background', theme_config.ui_menubutton_bg)
        self.tk_root.option_add('*TCombobox*fieldbackground', theme_config.ui_combobox_bg)
    
    def _force_tkinter_refresh(self):
        """Force refresh of all Tkinter widgets."""
        if not self.tk_root:
            return
        
        try:
            # Force update of root window and all children
            self.tk_root.update_idletasks()
            
            # Apply theme colors to root window and main containers
            for child in self.tk_root.winfo_children():
                if hasattr(child, 'configure'):
                    try:
                        if 'background' in child.configure():
                            child.configure(background=self.current_theme.ui_bg)
                        if 'bg' in child.configure():
                            child.configure(bg=self.current_theme.ui_bg)
                    except (tk.TclError, AttributeError):
                        pass
            
            # Force complete refresh
            self.tk_root.update_idletasks()
            self.tk_root.update()
            
        except Exception as e:
            logger.warning(f"Could not force Tkinter refresh: {e}")
    
    def _apply_qt_theme(self, theme_config: ThemeConfig):
        """Apply theme to Qt widgets."""
        if not self.qt_theme_manager:
            return
        
        try:
            self.qt_theme_manager.update_theme(theme_config)
        except Exception as e:
            logger.warning(f"Could not apply Qt theme: {e}")
    
    def get_theme_color(self, color_name: str) -> Optional[str]:
        """Get a theme color by name."""
        if not self.current_theme:
            return None
        
        if hasattr(self.current_theme, color_name):
            return getattr(self.current_theme, color_name)
        
        return None
    
    def create_custom_theme(self, **kwargs) -> ThemeConfig:
        """Create a custom theme with specified overrides."""
        if not self.current_theme:
            self.current_theme = ThemeConfig()
        
        # Create a copy and apply overrides
        custom_theme = ThemeConfig()
        for key, value in kwargs.items():
            if hasattr(custom_theme, key):
                setattr(custom_theme, key, value)
        
        return custom_theme
    
    def get_available_presets(self) -> list:
        """Get list of available theme presets."""
        from .config import THEME_PRESETS
        return list(THEME_PRESETS.keys())
    
    def export_theme(self) -> Dict[str, Any]:
        """Export current theme configuration as dictionary."""
        if not self.current_theme:
            return {}
        
        return {
            'preset': self.current_theme.preset,
            'game_bg': self.current_theme.game_bg,
            'game_fg': self.current_theme.game_fg,
            'ui_bg': self.current_theme.ui_bg,
            'ui_fg': self.current_theme.ui_fg,
            'accent_primary': self.current_theme.accent_primary,
            'accent_secondary': self.current_theme.accent_secondary,
            'success': self.current_theme.success,
            'warning': self.current_theme.warning,
            'error': self.current_theme.error,
            'info': self.current_theme.info,
        }
    
    def import_theme(self, theme_data: Dict[str, Any]):
        """Import theme configuration from dictionary."""
        if not theme_data:
            return
        
        # Create new theme config
        new_theme = ThemeConfig()
        
        # Apply imported values
        for key, value in theme_data.items():
            if hasattr(new_theme, key):
                setattr(new_theme, key, value)
        
        # Apply the imported theme
        self.set_theme(new_theme)


# Utility functions for easy theme management
def create_unified_theme_manager(tk_root: Optional[tk.Tk] = None, 
                                qt_app: Optional[QApplication] = None) -> UnifiedThemeManager:
    """Create a unified theme manager instance."""
    return UnifiedThemeManager(tk_root, qt_app)


def apply_theme_to_widget(widget: tk.Widget, theme_config: ThemeConfig):
    """Apply theme to a single Tkinter widget."""
    if not hasattr(widget, 'configure'):
        return
    
    try:
        widget.configure(
            background=theme_config.ui_bg,
            foreground=theme_config.ui_fg
        )
    except (tk.TclError, AttributeError):
        pass


def get_theme_color_scheme(theme_config: ThemeConfig) -> Dict[str, str]:
    """Get a color scheme dictionary from theme config."""
    return {
        'background': theme_config.ui_bg,
        'foreground': theme_config.ui_fg,
        'primary': theme_config.accent_primary,
        'secondary': theme_config.accent_secondary,
        'success': theme_config.success,
        'warning': theme_config.warning,
        'error': theme_config.error,
        'info': theme_config.info,
        'muted': theme_config.ui_muted,
        'border': theme_config.ui_border,
        'card': theme_config.ui_card_bg,
        'field': theme_config.ui_field_bg,
    }
