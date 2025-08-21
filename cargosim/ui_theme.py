"""Comprehensive theme enforcement for Tkinter/ttk applications.

This module enforces the existing color palette across the entire application,
ensuring no widgets fall back to OS gray colors. It centralizes all theming
in one place and removes per-widget color leaks.
"""

import tkinter as tk
from tkinter import ttk
from typing import Dict, Any
import logging

from .utils import log_runtime_event, log_exception

logger = logging.getLogger(__name__)


def apply_theme(root: tk.Misc, palette: Dict[str, str]):
    """
    Apply theme palette to the entire Tkinter/ttk application.
    
    This function reads the current palette and applies those tokens to every
    widget, ensuring consistent theming across the entire application.
    
    Args:
        root: Root Tkinter widget (usually Tk())
        palette: Dictionary containing color tokens
                Expected keys: bg, fg, field_bg, field_fg, caret, accent, border, muted
                If names differ, they will be mapped appropriately
    """
    try:
        log_runtime_event("Starting theme application", f"palette_keys={list(palette.keys())}")
        
        style = ttk.Style()
        style.theme_use("clam")  # Required for reliable color overrides
        
        # Map palette keys to expected names (handle different naming conventions)
        BG = palette.get("bg") or palette.get("ui_bg") or palette.get("background") or "#ffffff"
        FG = palette.get("fg") or palette.get("ui_fg") or palette.get("foreground") or "#000000"
        FBG = palette.get("field_bg") or palette.get("ui_field_bg") or palette.get("field") or BG
        FFG = palette.get("field_fg") or palette.get("ui_field_fg") or FG
        CARET = palette.get("caret") or palette.get("insertcolor") or FFG
        ACCENT = palette.get("accent") or palette.get("accent_primary") or palette.get("primary") or "#3b82f6"
        BORDER = palette.get("border") or palette.get("ui_border") or "#c8c8c8"
        MUTED = palette.get("muted") or palette.get("ui_muted") or FG
        
        # Additional derived colors
        CARD_BG = palette.get("ui_card_bg") or palette.get("card") or BG
        HOVER_BG = palette.get("ui_hover_bg") or palette.get("hover") or BG
        ACTIVE_BG = palette.get("ui_active_bg") or palette.get("active") or ACCENT
        DISABLED_BG = palette.get("ui_disabled_bg") or palette.get("disabled_bg") or BG
        DISABLED_FG = palette.get("ui_disabled_fg") or palette.get("disabled_fg") or MUTED
        SELECTION_BG = palette.get("ui_selection_bg") or palette.get("selection_bg") or ACCENT
        SELECTION_FG = palette.get("ui_selection_fg") or palette.get("selection_fg") or BG
        
        log_runtime_event("Color mapping completed", f"BG={BG}, FG={FG}, ACCENT={ACCENT}")
        
        # Apply colors to root window
        try:
            root.configure(bg=BG)
            log_runtime_event("Root window background configured")
        except Exception as e:
            log_runtime_event("Failed to configure root background", f"error={e}", level="WARNING")
        
        # Configure ttk styles
        log_runtime_event("Configuring ttk styles")
        _configure_ttk_styles(style, root, BG, FG, FBG, FFG, CARET, ACCENT, BORDER, MUTED,
                             CARD_BG, HOVER_BG, ACTIVE_BG, DISABLED_BG, DISABLED_FG,
                             SELECTION_BG, SELECTION_FG)
        
        log_runtime_event("Theme application completed successfully")
        
    except Exception as e:
        log_exception(e, "apply_theme")
        raise


def _configure_ttk_styles(style, root, bg, fg, fbg, ffg, caret, accent, border, muted,
                          card_bg, hover_bg, active_bg, disabled_bg, disabled_fg,
                          selection_bg, selection_fg):
    """
    Helper function to configure all ttk styles with theme colors.
    This function is called by apply_theme and handles the specific
    configuration of each style.
    """
    # ---- Global surfaces (non-inputs) ----
    for name in (
        "TFrame", "TLabel", "TLabelframe", "TLabelframe.Label",
        "TButton", "TCheckbutton", "TRadiobutton",
        "TNotebook", "TNotebook.Tab", "TProgressbar", "TSeparator",
        "Treeview", "Treeview.Heading", "TScrollbar"
    ):
        style.configure(name, background=bg, foreground=fg)
    
    # Labelframe specific styling
    style.configure("TLabelframe", bordercolor=border)
    
    # Notebook styling
    style.configure("TNotebook", background=bg, borderwidth=0)
    style.configure("TNotebook.Tab",
                   background=bg, foreground=fg, padding=(10, 4))
    style.map("TNotebook.Tab",
              background=[("selected", bg)], foreground=[("selected", fg)])
    
    # ---- Inputs (entries/combos/spinboxes) ----
    for name in ("TEntry", "TCombobox", "TSpinbox"):
        style.configure(name, fieldbackground=fbg, foreground=ffg)
    
    style.configure("TEntry", insertcolor=caret)
    style.map("TCombobox", fieldbackground=[("readonly", fbg)])
    style.configure("TCombobox", background=fbg, arrowcolor=accent)
    
    # ---- Buttons/Checks/Radio: use accent for active/checked ----
    style.map("TButton",
              background=[("active", hover_bg)], foreground=[("active", fg)])
    
    style.configure("TCheckbutton", focuscolor=bg)
    style.map("TCheckbutton",
              indicatorcolor=[("selected", accent)],
              foreground=[("disabled", disabled_fg)])
    
    style.map("TRadiobutton",
              indicatorcolor=[("selected", accent)],
              foreground=[("disabled", disabled_fg)])
    
    # ---- Scale/Slider: trough uses BG; knob uses ACCENT ----
    style.configure("Accent.Horizontal.TScale", troughcolor=bg, background=accent)
    style.configure("Accent.Vertical.TScale", troughcolor=bg, background=accent)
    
    # Ensure app uses these styles when constructing scales
    # (No-op if callers already set style.)
    style.configure("Horizontal.TScale", troughcolor=bg, background=accent)
    style.configure("Vertical.TScale", troughcolor=bg, background=accent)
    
    # ---- Progressbar uses accent ----
    style.configure("TProgressbar", troughcolor=bg, background=accent)
    
    # ---- Treeview ----
    style.configure("Treeview",
                   background=bg, fieldbackground=bg,
                   foreground=fg, bordercolor=border)
    style.configure("Treeview.Heading",
                   background=bg, foreground=fg, bordercolor=border)
    
    # ---- Scrollbars ----
    style.configure("TScrollbar", troughcolor=bg, background=muted)
    style.map("TScrollbar", background=[("active", accent)])
    
    # ---- Classic Tk widgets (combobox listbox, menus, text, etc.) ----
    # These are not ttk-stylable; use option database.
    try:
        # Combobox dropdown
        root.option_add("*TCombobox*Listbox.background", fbg)
        root.option_add("*TCombobox*Listbox.foreground", ffg)
        root.option_add("*TCombobox*Listbox.selectBackground", accent)
        root.option_add("*TCombobox*Listbox.selectForeground", bg)
        
        # Menus
        root.option_add("*Menu.background", bg)
        root.option_add("*Menu.foreground", fg)
        root.option_add("*Menu.activeBackground", accent)
        root.option_add("*Menu.activeForeground", bg)
        
        # Generic classic widgets
        root.option_add("*Listbox.background", bg)
        root.option_add("*Listbox.foreground", fg)
        root.option_add("*Text.background", bg)
        root.option_add("*Text.foreground", fg)
        root.option_add("*Canvas.background", bg)
    except tk.TclError:
        pass
    
    # ---- Remove OS focus glow everywhere sensible ----
    def _defang_focus(widget):
        try:
            widget.configure(highlightthickness=0)
        except tk.TclError:
            pass
        for c in widget.winfo_children():
            _defang_focus(c)
    
    _defang_focus(root)
    
    # ---- Apply theme to existing widgets ----
    _apply_theme_to_existing_widgets(root, bg, fg, fbg, ffg, accent, border, muted)


def _apply_theme_to_existing_widgets(root, bg, fg, fbg, ffg, accent, border, muted):
    """Apply theme colors to existing widgets in the widget tree."""
    def _apply_to_widget(widget):
        try:
            widget_type = widget.winfo_class()
            
            # Apply background/foreground to all widgets
            if hasattr(widget, 'configure'):
                try:
                    # Background
                    if 'background' in widget.configure():
                        widget.configure(background=bg)
                    if 'bg' in widget.configure():
                        widget.configure(bg=bg)
                    
                    # Foreground
                    if 'foreground' in widget.configure():
                        widget.configure(foreground=fg)
                    if 'fg' in widget.configure():
                        widget.configure(fg=fg)
                    
                    # Field-specific colors for input widgets
                    if widget_type in ['Entry', 'Text', 'Listbox', 'Canvas']:
                        if 'insertbackground' in widget.configure():
                            widget.configure(insertbackground=ffg)
                        if 'selectbackground' in widget.configure():
                            widget.configure(selectbackground=accent)
                        if 'selectforeground' in widget.configure():
                            widget.configure(selectforeground=bg)
                        if 'highlightbackground' in widget.configure():
                            widget.configure(highlightbackground=bg)
                        if 'highlightcolor' in widget.configure():
                            widget.configure(highlightcolor=accent)
                    
                    # Button-specific colors
                    if widget_type in ['Button', 'Checkbutton', 'Radiobutton']:
                        if 'activebackground' in widget.configure():
                            widget.configure(activebackground=accent)
                        if 'activeforeground' in widget.configure():
                            widget.configure(activeforeground=bg)
                        if 'selectcolor' in widget.configure():
                            widget.configure(selectcolor=accent)
                    
                    # Scale-specific colors
                    if widget_type == 'Scale':
                        if 'troughcolor' in widget.configure():
                            widget.configure(troughcolor=bg)
                        if 'activebackground' in widget.configure():
                            widget.configure(activebackground=accent)
                    
                    # Progressbar-specific colors
                    if widget_type == 'Progressbar':
                        if 'troughcolor' in widget.configure():
                            widget.configure(troughcolor=bg)
                        if 'background' in widget.configure():
                            widget.configure(background=accent)
                    
                except (tk.TclError, AttributeError) as e:
                    logger.debug(f"Could not configure widget {widget_type}: {e}")
            
            # Apply to children recursively
            for child in widget.winfo_children():
                _apply_to_widget(child)
                
        except Exception as e:
            logger.debug(f"Error applying theme to widget: {e}")
    
    _apply_to_widget(root)


def create_palette_from_theme_config(theme_config) -> Dict[str, str]:
    """
    Create a palette dictionary from a ThemeConfig object.
    
    This function maps the existing theme configuration to the expected
    palette keys used by apply_theme().
    
    Args:
        theme_config: ThemeConfig object from cargosim.config
        
    Returns:
        Dictionary with palette keys: bg, fg, field_bg, field_fg, caret, accent, border, muted
    """
    try:
        log_runtime_event("Creating theme palette from configuration")
        
        palette = {
            "bg": theme_config.ui_bg,
            "fg": theme_config.ui_fg,
            "field_bg": theme_config.ui_field_bg,
            "field_fg": theme_config.ui_fg,  # Use main foreground for field text
            "caret": theme_config.ui_fg,     # Use main foreground for caret
            "accent": theme_config.accent_primary,
            "border": theme_config.ui_border,
            "muted": theme_config.ui_muted,
            # Additional mappings for backward compatibility
            "ui_bg": theme_config.ui_bg,
            "ui_fg": theme_config.ui_fg,
            "ui_field_bg": theme_config.ui_field_bg,
            "ui_field_fg": theme_config.ui_fg,
            "accent_primary": theme_config.accent_primary,
            "ui_border": theme_config.ui_border,
            "ui_muted": theme_config.ui_muted,
            "ui_card_bg": theme_config.ui_card_bg,
            "ui_hover_bg": theme_config.ui_hover_bg,
            "ui_active_bg": theme_config.ui_active_bg,
            "ui_disabled_bg": theme_config.ui_disabled_bg,
            "ui_disabled_fg": theme_config.ui_disabled_fg,
            "ui_selection_bg": theme_config.ui_selection_bg,
            "ui_selection_fg": theme_config.ui_selection_fg,
        }
        
        log_runtime_event("Theme palette created successfully", f"palette_keys={list(palette.keys())}")
        return palette
        
    except Exception as e:
        log_exception(e, "create_palette_from_theme_config")
        raise
