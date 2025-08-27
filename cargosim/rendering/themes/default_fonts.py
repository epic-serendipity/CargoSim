"""
Default Tkinter Font Constants for CargoSim.

This module provides consistent font specifications using tkinter's default system fonts.
All fonts use the system default size for consistency and accessibility.
"""

# Default tkinter fonts - only specify family, let tkinter use system defaults
DEFAULT_FONT = ("TkDefaultFont",)
DEFAULT_FONT_BOLD = ("TkDefaultFont",)
DEFAULT_FONT_ITALIC = ("TkDefaultFont",)
DEFAULT_FONT_BOLD_ITALIC = ("TkDefaultFont",)

# Alternative system fonts for fallback
SYSTEM_FONT = ("TkSystemFont",)
SYSTEM_FONT_BOLD = ("TkSystemFont",)

# Text widget fonts
TEXT_FONT = ("TkTextFont",)
TEXT_FONT_BOLD = ("TkTextFont",)

# Fixed-width fonts for monospace needs
FIXED_FONT = ("TkFixedFont",)
FIXED_FONT_BOLD = ("TkFixedFont",)

# Menu fonts
MENU_FONT = ("TkMenuFont",)
MENU_FONT_BOLD = ("TkMenuFont",)

# Icon fonts (for special characters)
ICON_FONT = ("TkIconFont",)

# Font family constants for consistent usage
FONT_FAMILIES = {
    'default': DEFAULT_FONT,
    'bold': DEFAULT_FONT_BOLD,
    'italic': DEFAULT_FONT_ITALIC,
    'bold_italic': DEFAULT_FONT_BOLD_ITALIC,
    'system': SYSTEM_FONT,
    'system_bold': SYSTEM_FONT_BOLD,
    'text': TEXT_FONT,
    'text_bold': TEXT_FONT_BOLD,
    'fixed': FIXED_FONT,
    'fixed_bold': FIXED_FONT_BOLD,
    'menu': MENU_FONT,
    'menu_bold': MENU_FONT_BOLD,
    'icon': ICON_FONT
}

def get_font(family: str = 'default') -> tuple:
    """
    Get a font tuple by family name.
    
    Args:
        family: Font family name from FONT_FAMILIES
        
    Returns:
        Font tuple suitable for tkinter widgets
    """
    return FONT_FAMILIES.get(family, DEFAULT_FONT)

def get_all_fonts() -> dict:
    """
    Get all available font families.
    
    Returns:
        Dictionary of all font family names and their font tuples
    """
    return FONT_FAMILIES.copy()
