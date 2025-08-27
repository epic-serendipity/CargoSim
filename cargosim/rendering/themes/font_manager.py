"""Centralized font management for CargoSim UI."""

import tkinter as tk
from typing import Dict, Tuple, Optional
from .default_fonts import (
    DEFAULT_FONT, DEFAULT_FONT_BOLD, DEFAULT_FONT_ITALIC, DEFAULT_FONT_BOLD_ITALIC,
    SYSTEM_FONT, SYSTEM_FONT_BOLD, TEXT_FONT, TEXT_FONT_BOLD,
    FIXED_FONT, FIXED_FONT_BOLD, MENU_FONT, MENU_FONT_BOLD, ICON_FONT,
    get_font, get_all_fonts
)

class FontManager:
    """Manages font configurations across the application using default tkinter fonts."""
    
    # Font configurations using default tkinter fonts (no custom sizes)
    FONT_CONFIGS = {
        'tiny': DEFAULT_FONT,
        'small': DEFAULT_FONT,
        'normal': DEFAULT_FONT,
        'medium': DEFAULT_FONT,
        'large': DEFAULT_FONT,
        'header': DEFAULT_FONT_BOLD,
        'title': DEFAULT_FONT_BOLD,
        'icon': ICON_FONT
    }
    
    # Font families using default tkinter fonts
    FONT_FAMILIES = {
        'default': DEFAULT_FONT,
        'monospace': FIXED_FONT,
        'system': SYSTEM_FONT
    }
    
    def __init__(self):
        self._current_scale = 1.0  # Font scaling factor (kept for compatibility)
        self._user_preferences = {}
    
    def get_font(self, size_key: str = "normal", weight: str = "normal", family: str = "default") -> Tuple:
        """
        Get a font tuple using default tkinter fonts.
        
        Args:
            size_key: Font size key (ignored - always uses default tkinter size)
            weight: Font weight ("normal", "bold", "italic")
            family: Font family ("default", "monospace", "system")
            
        Returns:
            Font tuple using default tkinter fonts
        """
        # Map weight to appropriate default font
        if weight == "bold":
            if family == "monospace":
                return FIXED_FONT_BOLD
            elif family == "system":
                return SYSTEM_FONT_BOLD
            else:
                return DEFAULT_FONT_BOLD
        elif weight == "italic":
            if family == "monospace":
                return FIXED_FONT  # Fallback to normal for italic
            elif family == "system":
                return SYSTEM_FONT  # Fallback to normal for italic
            else:
                return DEFAULT_FONT_ITALIC
        else:
            # Normal weight
            if family == "monospace":
                return FIXED_FONT
            elif family == "system":
                return SYSTEM_FONT
            else:
                return DEFAULT_FONT
    
    def set_scale(self, scale: float):
        """
        Set font scaling factor (kept for compatibility but no longer affects sizing).
        
        Args:
            scale: Font scaling factor (0.8 = 80%, 1.2 = 120%, etc.)
        """
        self._current_scale = max(0.5, min(2.0, scale))
        # Note: Scaling is no longer applied since we use default tkinter fonts
    
    def get_compact_fonts(self) -> Dict[str, Tuple]:
        """Get fonts optimized for compact layouts using default tkinter sizes."""
        return {
            'small': DEFAULT_FONT,
            'normal': DEFAULT_FONT,
            'header': DEFAULT_FONT_BOLD
        }
    
    def get_standard_fonts(self) -> Dict[str, Tuple]:
        """Get standard font sizes using default tkinter fonts."""
        return {
            'small': DEFAULT_FONT,
            'normal': DEFAULT_FONT,
            'header': DEFAULT_FONT_BOLD
        }
    
    def get_fullscreen_fonts(self) -> Dict[str, Tuple]:
        """Get fonts optimized for fullscreen layouts using default tkinter fonts."""
        return {
            'small': DEFAULT_FONT,
            'normal': DEFAULT_FONT,
            'header': DEFAULT_FONT_BOLD
        }
    
    def get_default_fonts(self) -> Dict[str, Tuple]:
        """Get all default tkinter fonts for consistent usage."""
        return get_all_fonts()

# Global instance
font_manager = FontManager()

