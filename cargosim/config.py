"""Configuration management for CargoSim."""

import os
import json
import copy
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Literal, NamedTuple

# Configuration constants
CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cargo_sim_config.json")
CONFIG_VERSION = 8

# Default consumption cadences (PM only; day = t//2)
A_PERIOD_DAYS_DFLT = 2  # A: 1 every 2 days
B_PERIOD_DAYS_DFLT = 2  # B: 1 every 2 days
C_PERIOD_DAYS_DFLT = 3  # C: 1 every 3 days
D_PERIOD_DAYS_DFLT = 4  # D: 1 every 4 days

# Layout constants (safe area padding and side rails)
SAFE_PAD_PCT = 0.0125
SAFE_PAD_MIN_PX = 12
LEFT_RAIL_PCT = 0.09
LEFT_RAIL_MIN_PX = 120
RIGHT_RAIL_PCT = 0.14
RIGHT_RAIL_MIN_PX = 260

# Visual scaling for spoke bars (purely aesthetic; no caps)
VIS_CAPS_DFLT = (6, 2, 4, 4)  # used for relative bar heights

# Number of spokes
M = 10
PAIR_ORDER_DEFAULT = [(0,1),(2,3),(4,5),(6,7),(8,9)]  # zero-based spoke indices

# Default bar scale denominators for user-editable scaling
DEFAULT_BAR_SCALE_DENOMINATORS = (2, 2, 2, 2)  # A, B, C, D


def _hex(h):  # helper to clamp/normalize hex
    h = h.strip().lstrip("#")
    if len(h) == 3:
        h = "".join([c*2 for c in h])
    return "#" + h.lower()


def hex2rgb(h: str):
    h = h.strip().lstrip("#")
    if len(h) == 3:
        h = "".join([c*2 for c in h])
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def blend(a, b, t: float):
    return tuple(int(a[i]*(1-t) + b[i]*t) for i in range(3))


def calculate_contrast_ratio(color1, color2):
    """Calculate contrast ratio between two colors (WCAG AA requires 4.5:1)."""
    def luminance(rgb):
        def chan(c):
            c = float(c) / 255
            return c/12.92 if c <= 0.03928 else ((c+0.055)/1.055) ** 2.4
        r, g, b = [chan(x) for x in rgb]
        return 0.2126*r + 0.7152*g + 0.0722*b
    
    # Convert hex colors to RGB if needed
    if isinstance(color1, str):
        color1 = hex2rgb(color1)
    if isinstance(color2, str):
        color2 = hex2rgb(color2)
    
    l1, l2 = luminance(color1), luminance(color2)
    ratio = (max(l1, l2) + 0.05) / (min(l1, l2) + 0.05)
    return ratio


def ensure_contrast(base_color, text_color, min_ratio=4.5):
    """Ensure minimum contrast ratio by adjusting text color if needed."""
    base_rgb = hex2rgb(base_color) if isinstance(base_color, str) else base_color
    text_rgb = hex2rgb(text_color) if isinstance(text_color, str) else text_color
    
    ratio = calculate_contrast_ratio(base_rgb, text_rgb)
    if ratio >= min_ratio:
        return text_color
    
    # Adjust text color to meet contrast requirements
    if isinstance(text_color, str):
        text_rgb = hex2rgb(text_color)
    
    # Make text darker or lighter based on base color luminance
    base_lum = sum(base_rgb) / 3
    if base_lum > 128:  # Light background
        # Make text darker
        factor = 0.3
        adjusted = tuple(max(0, int(c * factor)) for c in text_rgb)
    else:  # Dark background
        # Make text lighter
        factor = 0.7
        adjusted = tuple(min(255, int(c + (255 - c) * factor)) for c in text_rgb)
    
    return "#%02x%02x%02x" % adjusted


class ThemeTokens(NamedTuple):
    text: Tuple[int, int, int]
    muted: Tuple[int, int, int]
    bg: Tuple[int, int, int]
    hub: Tuple[int, int, int]
    good_spoke: Tuple[int, int, int]
    bad_spoke: Tuple[int, int, int]
    bar_A: Tuple[int, int, int]
    bar_B: Tuple[int, int, int]
    bar_C: Tuple[int, int, int]
    bar_D: Tuple[int, int, int]
    panel_bg: Tuple[int, int, int]
    panel_btn: Tuple[int, int, int]
    panel_btn_fg: Tuple[int, int, int]


CURRENT_THEME_VERSION = 3

# Enhanced theme presets with comprehensive UI colors for every element
THEME_PRESETS = {
    "Classic Light": {
        "name": "Classic Light",
        "description": "Clean, vibrant light theme with enhanced colors for maximum visual appeal",
        "game_bg": _hex("ffffff"),
        "game_fg": _hex("1a1a1a"),
        "game_muted": _hex("4a5568"),
        "hub_color": _hex("f7fafc"),
        "good_spoke": _hex("059669"),
        "bad_spoke": _hex("dc2626"),
        "bar_A": _hex("3b82f6"),
        "bar_B": _hex("f59e0b"),
        "bar_C": _hex("10b981"),
        "bar_D": _hex("ef4444"),
        "accent_primary": _hex("3b82f6"),
        "accent_secondary": _hex("8b5cf6"),
        "success": _hex("059669"),
        "warning": _hex("f59e0b"),
        "error": _hex("dc2626"),
        "info": _hex("0891b2"),
        # Comprehensive UI colors - Vibrant light theme
        "ui_bg": _hex("ffffff"),
        "ui_fg": _hex("1a1a1a"),
        "ui_muted": _hex("4a5568"),
        "ui_border": _hex("cbd5e1"),
        "ui_card_bg": _hex("f8fafc"),
        "ui_field_bg": _hex("ffffff"),
        "ui_hover_bg": _hex("e2e8f0"),
        "ui_active_bg": _hex("dbeafe"),
        "ui_disabled_bg": _hex("f1f5f9"),
        "ui_disabled_fg": _hex("94a3b8"),
        "ui_selection_bg": _hex("dbeafe"),
        "ui_selection_fg": _hex("1e40af"),
        "ui_tab_bg": _hex("f1f5f9"),
        "ui_tab_fg": _hex("475569"),
        "ui_tab_selected_bg": _hex("ffffff"),
        "ui_tab_selected_fg": _hex("1e40af"),
        "ui_tab_border": _hex("cbd5e1"),
        "ui_button_bg": _hex("f1f5f9"),
        "ui_button_fg": _hex("1a1a1a"),
        "ui_button_border": _hex("cbd5e1"),
        "ui_button_hover_bg": _hex("e2e8f0"),
        "ui_button_active_bg": _hex("dbeafe"),
        "ui_button_primary_bg": _hex("3b82f6"),
        "ui_button_primary_fg": _hex("ffffff"),
        "ui_button_primary_border": _hex("3b82f6"),
        "ui_button_primary_hover_bg": _hex("2563eb"),
        "ui_button_secondary_bg": _hex("8b5cf6"),
        "ui_button_secondary_fg": _hex("ffffff"),
        "ui_button_secondary_border": _hex("8b5cf6"),
        "ui_button_secondary_hover_bg": _hex("7c3aed"),
        "ui_button_success_bg": _hex("10b981"),
        "ui_button_success_fg": _hex("ffffff"),
        "ui_button_success_border": _hex("10b981"),
        "ui_button_success_hover_bg": _hex("059669"),
        "ui_button_warning_bg": _hex("f59e0b"),
        "ui_button_warning_fg": _hex("ffffff"),
        "ui_button_warning_border": _hex("f59e0b"),
        "ui_button_warning_hover_bg": _hex("d97706"),
        "ui_button_error_bg": _hex("ef4444"),
        "ui_button_error_fg": _hex("ffffff"),
        "ui_button_error_border": _hex("ef4444"),
        "ui_button_error_hover_bg": _hex("dc2626"),
        "ui_entry_bg": _hex("ffffff"),
        "ui_entry_fg": _hex("1a1a1a"),
        "ui_entry_border": _hex("cbd5e1"),
        "ui_entry_focus_border": _hex("3b82f6"),
        "ui_spinbox_bg": _hex("ffffff"),
        "ui_spinbox_fg": _hex("1a1a1a"),
        "ui_spinbox_border": _hex("cbd5e1"),
        "ui_spinbox_focus_border": _hex("3b82f6"),
        "ui_scale_bg": _hex("f1f5f9"),
        "ui_scale_trough": _hex("e2e8f0"),
        "ui_scale_slider": _hex("3b82f6"),
        "ui_checkbox_bg": _hex("ffffff"),
        "ui_checkbox_fg": _hex("1a1a1a"),
        "ui_checkbox_border": _hex("cbd5e1"),
        "ui_checkbox_selected_bg": _hex("3b82f6"),
        "ui_checkbox_selected_fg": _hex("ffffff"),
        "ui_radiobutton_bg": _hex("ffffff"),
        "ui_radiobutton_fg": _hex("1a1a1a"),
        "ui_radiobutton_border": _hex("cbd5e1"),
        "ui_radiobutton_selected_bg": _hex("3b82f6"),
        "ui_radiobutton_selected_fg": _hex("ffffff"),
        "ui_menubutton_bg": _hex("f1f5f9"),
        "ui_menubutton_fg": _hex("1a1a1a"),
        "ui_menubutton_border": _hex("cbd5e1"),
        "ui_menubutton_hover_bg": _hex("e2e8f0"),
        "ui_optionmenu_bg": _hex("f1f5f9"),
        "ui_optionmenu_fg": _hex("1a1a1a"),
        "ui_optionmenu_border": _hex("cbd5e1"),
        "ui_optionmenu_hover_bg": _hex("e2e8f0"),
        "ui_combobox_bg": _hex("ffffff"),
        "ui_combobox_fg": _hex("1a1a1a"),
        "ui_combobox_border": _hex("cbd5e1"),
        "ui_combobox_focus_border": _hex("3b82f6"),
        "ui_progressbar_bg": _hex("3b82f6"),
        "ui_progressbar_trough": _hex("f1f5f9"),
        "ui_treeview_bg": _hex("ffffff"),
        "ui_treeview_fg": _hex("1a1a1a"),
        "ui_treeview_border": _hex("cbd5e1"),
        "ui_treeview_heading_bg": _hex("f1f5f9"),
        "ui_treeview_heading_fg": _hex("1a1a1a"),
        "ui_treeview_heading_border": _hex("cbd5e1"),
        "ui_separator_bg": _hex("cbd5e1"),
        "ui_labelframe_bg": _hex("ffffff"),
        "ui_labelframe_fg": _hex("1a1a1a"),
        "ui_labelframe_border": _hex("cbd5e1"),
        "ui_labelframe_label_bg": _hex("ffffff"),
        "ui_labelframe_label_fg": _hex("1a1a1a"),
        "ui_notebook_bg": _hex("ffffff"),
        "ui_notebook_border": _hex("cbd5e1"),
        "ui_notebook_pane_bg": _hex("ffffff"),
        "ui_notebook_pane_border": _hex("cbd5e1"),
        "default_airframe_colorset": "Professional Blue",
    },
    "Classic Dark": {
        "name": "Classic Dark",
        "description": "Sophisticated dark theme with high contrast for reduced eye strain",
        "game_bg": _hex("000000"),
        "game_fg": _hex("ffffff"),
        "game_muted": _hex("9ca3af"),
        "hub_color": _hex("1f2937"),
        "good_spoke": _hex("10b981"),
        "bad_spoke": _hex("f87171"),
        "bar_A": _hex("60a5fa"),
        "bar_B": _hex("fbbf24"),
        "bar_C": _hex("10b981"),
        "bar_D": _hex("f87171"),
        "accent_primary": _hex("60a5fa"),
        "accent_secondary": _hex("a78bfa"),
        "success": _hex("10b981"),
        "warning": _hex("fbbf24"),
        "error": _hex("f87171"),
        "info": _hex("22d3ee"),
        # Comprehensive UI colors - High contrast dark theme
        "ui_bg": _hex("000000"),
        "ui_fg": _hex("ffffff"),
        "ui_muted": _hex("9ca3af"),
        "ui_border": _hex("374151"),
        "ui_card_bg": _hex("111827"),
        "ui_field_bg": _hex("000000"),
        "ui_hover_bg": _hex("1f2937"),
        "ui_active_bg": _hex("1e40af"),
        "ui_disabled_bg": _hex("111827"),
        "ui_disabled_fg": _hex("6b7280"),
        "ui_selection_bg": _hex("1e40af"),
        "ui_selection_fg": _hex("ffffff"),
        "ui_tab_bg": _hex("111827"),
        "ui_tab_fg": _hex("9ca3af"),
        "ui_tab_selected_bg": _hex("000000"),
        "ui_tab_selected_fg": _hex("ffffff"),
        "ui_tab_border": _hex("374151"),
        "ui_button_bg": _hex("111827"),
        "ui_button_fg": _hex("ffffff"),
        "ui_button_border": _hex("374151"),
        "ui_button_hover_bg": _hex("1f2937"),
        "ui_button_active_bg": _hex("1e40af"),
        "ui_button_primary_bg": _hex("60a5fa"),
        "ui_button_primary_fg": _hex("000000"),
        "ui_button_primary_border": _hex("60a5fa"),
        "ui_button_primary_hover_bg": _hex("3b82f6"),
        "ui_button_secondary_bg": _hex("a78bfa"),
        "ui_button_secondary_fg": _hex("000000"),
        "ui_button_secondary_border": _hex("a78bfa"),
        "ui_button_secondary_hover_bg": _hex("8b5cf6"),
        "ui_button_success_bg": _hex("10b981"),
        "ui_button_success_fg": _hex("000000"),
        "ui_button_success_border": _hex("10b981"),
        "ui_button_success_hover_bg": _hex("059669"),
        "ui_button_warning_bg": _hex("fbbf24"),
        "ui_button_warning_fg": _hex("000000"),
        "ui_button_warning_border": _hex("fbbf24"),
        "ui_button_warning_hover_bg": _hex("f59e0b"),
        "ui_button_error_bg": _hex("f87171"),
        "ui_button_error_fg": _hex("000000"),
        "ui_button_error_border": _hex("f87171"),
        "ui_button_error_hover_bg": _hex("ef4444"),
        "ui_entry_bg": _hex("000000"),
        "ui_entry_fg": _hex("ffffff"),
        "ui_entry_border": _hex("374151"),
        "ui_entry_focus_border": _hex("60a5fa"),
        "ui_spinbox_bg": _hex("000000"),
        "ui_spinbox_fg": _hex("ffffff"),
        "ui_spinbox_border": _hex("374151"),
        "ui_spinbox_focus_border": _hex("60a5fa"),
        "ui_scale_bg": _hex("111827"),
        "ui_scale_trough": _hex("1f2937"),
        "ui_scale_slider": _hex("60a5fa"),
        "ui_checkbox_bg": _hex("000000"),
        "ui_checkbox_fg": _hex("ffffff"),
        "ui_checkbox_border": _hex("374151"),
        "ui_checkbox_selected_bg": _hex("60a5fa"),
        "ui_checkbox_selected_fg": _hex("000000"),
        "ui_radiobutton_bg": _hex("000000"),
        "ui_radiobutton_fg": _hex("ffffff"),
        "ui_radiobutton_border": _hex("374151"),
        "ui_radiobutton_selected_bg": _hex("60a5fa"),
        "ui_radiobutton_selected_fg": _hex("000000"),
        "ui_menubutton_bg": _hex("111827"),
        "ui_menubutton_fg": _hex("ffffff"),
        "ui_menubutton_border": _hex("374151"),
        "ui_menubutton_hover_bg": _hex("1f2937"),
        "ui_optionmenu_bg": _hex("111827"),
        "ui_optionmenu_fg": _hex("ffffff"),
        "ui_optionmenu_border": _hex("374151"),
        "ui_optionmenu_hover_bg": _hex("1f2937"),
        "ui_combobox_bg": _hex("000000"),
        "ui_combobox_fg": _hex("ffffff"),
        "ui_combobox_border": _hex("374151"),
        "ui_combobox_focus_border": _hex("60a5fa"),
        "ui_progressbar_bg": _hex("60a5fa"),
        "ui_progressbar_trough": _hex("111827"),
        "ui_treeview_bg": _hex("000000"),
        "ui_treeview_fg": _hex("ffffff"),
        "ui_treeview_border": _hex("374151"),
        "ui_treeview_heading_bg": _hex("111827"),
        "ui_treeview_heading_fg": _hex("ffffff"),
        "ui_treeview_heading_border": _hex("374151"),
        "ui_separator_bg": _hex("374151"),
        "ui_labelframe_bg": _hex("000000"),
        "ui_labelframe_fg": _hex("ffffff"),
        "ui_labelframe_border": _hex("374151"),
        "ui_labelframe_label_bg": _hex("000000"),
        "ui_labelframe_label_fg": _hex("ffffff"),
        "ui_notebook_bg": _hex("000000"),
        "ui_notebook_border": _hex("374151"),
        "ui_notebook_pane_bg": _hex("000000"),
        "ui_notebook_pane_border": _hex("374151"),
        "default_airframe_colorset": "Professional Blue",
    },
    "Ocean Blue": {
        "name": "Ocean Blue",
        "description": "Calming ocean-inspired theme with blue-green palette",
        "game_bg": _hex("0f172a"),
        "game_fg": _hex("e2e8f0"),
        "game_muted": _hex("64748b"),
        "hub_color": _hex("1e293b"),
        "good_spoke": _hex("14b8a6"),
        "bad_spoke": _hex("f87171"),
        "bar_A": _hex("0ea5e9"),
        "bar_B": _hex("06b6d4"),
        "bar_C": _hex("14b8a6"),
        "bar_D": _hex("8b5cf6"),
        "accent_primary": _hex("0ea5e9"),
        "accent_secondary": _hex("06b6d4"),
        "success": _hex("14b8a6"),
        "warning": _hex("fbbf24"),
        "error": _hex("f87171"),
        "info": _hex("8b5cf6"),
        # Comprehensive UI colors
        "ui_bg": _hex("0f172a"),
        "ui_fg": _hex("e2e8f0"),
        "ui_muted": _hex("64748b"),
        "ui_border": _hex("334155"),
        "ui_card_bg": _hex("1e293b"),
        "ui_field_bg": _hex("0f172a"),
        "ui_hover_bg": _hex("334155"),
        "ui_active_bg": _hex("0369a1"),
        "ui_disabled_bg": _hex("1e293b"),
        "ui_disabled_fg": _hex("475569"),
        "ui_selection_bg": _hex("0369a1"),
        "ui_selection_fg": _hex("e2e8f0"),
        "ui_tab_bg": _hex("1e293b"),
        "ui_tab_fg": _hex("64748b"),
        "ui_tab_selected_bg": _hex("0f172a"),
        "ui_tab_selected_fg": _hex("e2e8f0"),
        "ui_tab_border": _hex("334155"),
        "ui_button_bg": _hex("1e293b"),
        "ui_button_fg": _hex("e2e8f0"),
        "ui_button_border": _hex("334155"),
        "ui_button_hover_bg": _hex("334155"),
        "ui_button_active_bg": _hex("0369a1"),
        "ui_button_primary_bg": _hex("0ea5e9"),
        "ui_button_primary_fg": _hex("ffffff"),
        "ui_button_primary_border": _hex("0ea5e9"),
        "ui_button_primary_hover_bg": _hex("0284c7"),
        "ui_button_secondary_bg": _hex("06b6d4"),
        "ui_button_secondary_fg": _hex("ffffff"),
        "ui_button_secondary_border": _hex("06b6d4"),
        "ui_button_secondary_hover_bg": _hex("0891b2"),
        "ui_button_success_bg": _hex("14b8a6"),
        "ui_button_success_fg": _hex("ffffff"),
        "ui_button_success_border": _hex("14b8a6"),
        "ui_button_success_hover_bg": _hex("0d9488"),
        "ui_button_warning_bg": _hex("fbbf24"),
        "ui_button_warning_fg": _hex("ffffff"),
        "ui_button_warning_border": _hex("fbbf24"),
        "ui_button_warning_hover_bg": _hex("f59e0b"),
        "ui_button_error_bg": _hex("f87171"),
        "ui_button_error_fg": _hex("ffffff"),
        "ui_button_error_border": _hex("f87171"),
        "ui_button_error_hover_bg": _hex("ef4444"),
        "ui_entry_bg": _hex("0f172a"),
        "ui_entry_fg": _hex("e2e8f0"),
        "ui_entry_border": _hex("334155"),
        "ui_entry_focus_border": _hex("0ea5e9"),
        "ui_spinbox_bg": _hex("0f172a"),
        "ui_spinbox_fg": _hex("e2e8f0"),
        "ui_spinbox_border": _hex("334155"),
        "ui_spinbox_focus_border": _hex("0ea5e9"),
        "ui_scale_bg": _hex("1e293b"),
        "ui_scale_trough": _hex("334155"),
        "ui_scale_slider": _hex("0ea5e9"),
        "ui_checkbox_bg": _hex("0f172a"),
        "ui_checkbox_fg": _hex("e2e8f0"),
        "ui_checkbox_border": _hex("334155"),
        "ui_checkbox_selected_bg": _hex("0ea5e9"),
        "ui_checkbox_selected_fg": _hex("ffffff"),
        "ui_radiobutton_bg": _hex("0f172a"),
        "ui_radiobutton_fg": _hex("e2e8f0"),
        "ui_radiobutton_border": _hex("334155"),
        "ui_radiobutton_selected_bg": _hex("0ea5e9"),
        "ui_radiobutton_selected_fg": _hex("ffffff"),
        "ui_menubutton_bg": _hex("1e293b"),
        "ui_menubutton_fg": _hex("e2e8f0"),
        "ui_menubutton_border": _hex("334155"),
        "ui_menubutton_hover_bg": _hex("334155"),
        "ui_optionmenu_bg": _hex("1e293b"),
        "ui_optionmenu_fg": _hex("e2e8f0"),
        "ui_optionmenu_border": _hex("334155"),
        "ui_optionmenu_hover_bg": _hex("334155"),
        "ui_combobox_bg": _hex("0f172a"),
        "ui_combobox_fg": _hex("e2e8f0"),
        "ui_combobox_border": _hex("334155"),
        "ui_combobox_focus_border": _hex("0ea5e9"),
        "ui_progressbar_bg": _hex("0ea5e9"),
        "ui_progressbar_trough": _hex("1e293b"),
        "ui_treeview_bg": _hex("0f172a"),
        "ui_treeview_fg": _hex("e2e8f0"),
        "ui_treeview_border": _hex("334155"),
        "ui_treeview_heading_bg": _hex("1e293b"),
        "ui_treeview_heading_fg": _hex("e2e8f0"),
        "ui_treeview_heading_border": _hex("334155"),
        "ui_separator_bg": _hex("334155"),
        "ui_labelframe_bg": _hex("0f172a"),
        "ui_labelframe_fg": _hex("e2e8f0"),
        "ui_labelframe_border": _hex("334155"),
        "ui_labelframe_label_bg": _hex("0f172a"),
        "ui_labelframe_label_fg": _hex("e2e8f0"),
        "ui_notebook_bg": _hex("0f172a"),
        "ui_notebook_border": _hex("334155"),
        "ui_notebook_pane_bg": _hex("0f172a"),
        "ui_notebook_pane_border": _hex("334155"),
        "default_airframe_colorset": "Ocean Blue",
    },
    "Forest Green": {
        "name": "Forest Green",
        "description": "Natural, organic theme with forest green accents",
        "game_bg": _hex("f0fdf4"),
        "game_fg": _hex("14532d"),
        "game_muted": _hex("16a34a"),
        "hub_color": _hex("dcfce7"),
        "good_spoke": _hex("059669"),
        "bad_spoke": _hex("dc2626"),
        "bar_A": _hex("059669"),
        "bar_B": _hex("16a34a"),
        "bar_C": _hex("22c55e"),
        "bar_D": _hex("84cc16"),
        "accent_primary": _hex("059669"),
        "accent_secondary": _hex("a16207"),
        "success": _hex("16a34a"),
        "warning": _hex("a16207"),
        "error": _hex("dc2626"),
        "info": _hex("0891b2"),
        # Comprehensive UI colors
        "ui_bg": _hex("f0fdf4"),
        "ui_fg": _hex("14532d"),
        "ui_muted": _hex("16a34a"),
        "ui_border": _hex("bbf7d0"),
        "ui_card_bg": _hex("dcfce7"),
        "ui_field_bg": _hex("f0fdf4"),
        "ui_hover_bg": _hex("bbf7d0"),
        "ui_active_bg": _hex("86efac"),
        "ui_disabled_bg": _hex("dcfce7"),
        "ui_disabled_fg": _hex("86efac"),
        "ui_selection_bg": _hex("86efac"),
        "ui_selection_fg": _hex("14532d"),
        "ui_tab_bg": _hex("bbf7d0"),
        "ui_tab_fg": _hex("16a34a"),
        "ui_tab_selected_bg": _hex("f0fdf4"),
        "ui_tab_selected_fg": _hex("14532d"),
        "ui_tab_border": _hex("bbf7d0"),
        "ui_button_bg": _hex("bbf7d0"),
        "ui_button_fg": _hex("14532d"),
        "ui_button_border": _hex("bbf7d0"),
        "ui_button_hover_bg": _hex("86efac"),
        "ui_button_active_bg": _hex("86efac"),
        "ui_button_primary_bg": _hex("059669"),
        "ui_button_primary_fg": _hex("ffffff"),
        "ui_button_primary_border": _hex("059669"),
        "ui_button_primary_hover_bg": _hex("047857"),
        "ui_button_secondary_bg": _hex("a16207"),
        "ui_button_secondary_fg": _hex("ffffff"),
        "ui_button_secondary_border": _hex("a16207"),
        "ui_button_secondary_hover_bg": _hex("854d0e"),
        "ui_button_success_bg": _hex("16a34a"),
        "ui_button_success_fg": _hex("ffffff"),
        "ui_button_success_border": _hex("16a34a"),
        "ui_button_success_hover_bg": _hex("15803d"),
        "ui_button_warning_bg": _hex("a16207"),
        "ui_button_warning_fg": _hex("ffffff"),
        "ui_button_warning_border": _hex("a16207"),
        "ui_button_warning_hover_bg": _hex("854d0e"),
        "ui_button_error_bg": _hex("dc2626"),
        "ui_button_error_fg": _hex("ffffff"),
        "ui_button_error_border": _hex("dc2626"),
        "ui_button_error_hover_bg": _hex("b91c1c"),
        "ui_entry_bg": _hex("f0fdf4"),
        "ui_entry_fg": _hex("14532d"),
        "ui_entry_border": _hex("bbf7d0"),
        "ui_entry_focus_border": _hex("059669"),
        "ui_spinbox_bg": _hex("f0fdf4"),
        "ui_spinbox_fg": _hex("14532d"),
        "ui_spinbox_border": _hex("bbf7d0"),
        "ui_spinbox_focus_border": _hex("059669"),
        "ui_scale_bg": _hex("bbf7d0"),
        "ui_scale_trough": _hex("86efac"),
        "ui_scale_slider": _hex("059669"),
        "ui_checkbox_bg": _hex("f0fdf4"),
        "ui_checkbox_fg": _hex("14532d"),
        "ui_checkbox_border": _hex("bbf7d0"),
        "ui_checkbox_selected_bg": _hex("059669"),
        "ui_checkbox_selected_fg": _hex("ffffff"),
        "ui_radiobutton_bg": _hex("f0fdf4"),
        "ui_radiobutton_fg": _hex("14532d"),
        "ui_radiobutton_border": _hex("bbf7d0"),
        "ui_radiobutton_selected_bg": _hex("059669"),
        "ui_radiobutton_selected_fg": _hex("ffffff"),
        "ui_menubutton_bg": _hex("bbf7d0"),
        "ui_menubutton_fg": _hex("14532d"),
        "ui_menubutton_border": _hex("bbf7d0"),
        "ui_menubutton_hover_bg": _hex("86efac"),
        "ui_optionmenu_bg": _hex("bbf7d0"),
        "ui_optionmenu_fg": _hex("14532d"),
        "ui_optionmenu_border": _hex("bbf7d0"),
        "ui_optionmenu_hover_bg": _hex("86efac"),
        "ui_combobox_bg": _hex("f0fdf4"),
        "ui_combobox_fg": _hex("14532d"),
        "ui_combobox_border": _hex("bbf7d0"),
        "ui_combobox_focus_border": _hex("059669"),
        "ui_progressbar_bg": _hex("059669"),
        "ui_progressbar_trough": _hex("bbf7d0"),
        "ui_treeview_bg": _hex("f0fdf4"),
        "ui_treeview_fg": _hex("14532d"),
        "ui_treeview_border": _hex("bbf7d0"),
        "ui_treeview_heading_bg": _hex("bbf7d0"),
        "ui_treeview_heading_fg": _hex("14532d"),
        "ui_treeview_heading_border": _hex("bbf7d0"),
        "ui_separator_bg": _hex("bbf7d0"),
        "ui_labelframe_bg": _hex("f0fdf4"),
        "ui_labelframe_fg": _hex("14532d"),
        "ui_labelframe_border": _hex("bbf7d0"),
        "ui_labelframe_label_bg": _hex("f0fdf4"),
        "ui_labelframe_label_fg": _hex("14532d"),
        "ui_notebook_bg": _hex("f0fdf4"),
        "ui_notebook_border": _hex("bbf7d0"),
        "ui_notebook_pane_bg": _hex("f0fdf4"),
        "ui_notebook_pane_border": _hex("bbf7d0"),
        "default_airframe_colorset": "Forest Green",
    },
    "Sunset Orange": {
        "name": "Sunset Orange",
        "description": "Warm, energetic theme with orange and purple accents",
        "game_bg": _hex("1c1917"),
        "game_fg": _hex("fefefe"),
        "game_muted": _hex("a8a29e"),
        "hub_color": _hex("292524"),
        "good_spoke": _hex("fbbf24"),
        "bad_spoke": _hex("f87171"),
        "bar_A": _hex("f97316"),
        "bar_B": _hex("fbbf24"),
        "bar_C": _hex("a855f7"),
        "bar_D": _hex("ec4899"),
        "accent_primary": _hex("f97316"),
        "accent_secondary": _hex("a855f7"),
        "success": _hex("fbbf24"),
        "warning": _hex("f97316"),
        "error": _hex("f87171"),
        "info": _hex("a855f7"),
        # Comprehensive UI colors
        "ui_bg": _hex("1c1917"),
        "ui_fg": _hex("fefefe"),
        "ui_muted": _hex("a8a29e"),
        "ui_border": _hex("44403c"),
        "ui_card_bg": _hex("292524"),
        "ui_field_bg": _hex("1c1917"),
        "ui_hover_bg": _hex("44403c"),
        "ui_active_bg": _hex("7c2d12"),
        "ui_disabled_bg": _hex("292524"),
        "ui_disabled_fg": _hex("78716c"),
        "ui_selection_bg": _hex("7c2d12"),
        "ui_selection_fg": _hex("fefefe"),
        "ui_tab_bg": _hex("292524"),
        "ui_tab_fg": _hex("a8a29e"),
        "ui_tab_selected_bg": _hex("1c1917"),
        "ui_tab_selected_fg": _hex("fefefe"),
        "ui_tab_border": _hex("44403c"),
        "ui_button_bg": _hex("292524"),
        "ui_button_fg": _hex("fefefe"),
        "ui_button_border": _hex("44403c"),
        "ui_button_hover_bg": _hex("44403c"),
        "ui_button_active_bg": _hex("7c2d12"),
        "ui_button_primary_bg": _hex("f97316"),
        "ui_button_primary_fg": _hex("ffffff"),
        "ui_button_primary_border": _hex("f97316"),
        "ui_button_primary_hover_bg": _hex("ea580c"),
        "ui_button_secondary_bg": _hex("a855f7"),
        "ui_button_secondary_fg": _hex("ffffff"),
        "ui_button_secondary_border": _hex("a855f7"),
        "ui_button_secondary_hover_bg": _hex("9333ea"),
        "ui_button_success_bg": _hex("fbbf24"),
        "ui_button_success_fg": _hex("000000"),
        "ui_button_success_border": _hex("fbbf24"),
        "ui_button_success_hover_bg": _hex("f59e0b"),
        "ui_button_warning_bg": _hex("f97316"),
        "ui_button_warning_fg": _hex("ffffff"),
        "ui_button_warning_border": _hex("f97316"),
        "ui_button_warning_hover_bg": _hex("ea580c"),
        "ui_button_error_bg": _hex("f87171"),
        "ui_button_error_fg": _hex("ffffff"),
        "ui_button_error_border": _hex("f87171"),
        "ui_button_error_hover_bg": _hex("ef4444"),
        "ui_entry_bg": _hex("1c1917"),
        "ui_entry_fg": _hex("fefefe"),
        "ui_entry_border": _hex("44403c"),
        "ui_entry_focus_border": _hex("f97316"),
        "ui_spinbox_bg": _hex("1c1917"),
        "ui_spinbox_fg": _hex("fefefe"),
        "ui_spinbox_border": _hex("44403c"),
        "ui_spinbox_focus_border": _hex("f97316"),
        "ui_scale_bg": _hex("292524"),
        "ui_scale_trough": _hex("44403c"),
        "ui_scale_slider": _hex("f97316"),
        "ui_checkbox_bg": _hex("1c1917"),
        "ui_checkbox_fg": _hex("fefefe"),
        "ui_checkbox_border": _hex("44403c"),
        "ui_checkbox_selected_bg": _hex("f97316"),
        "ui_checkbox_selected_fg": _hex("ffffff"),
        "ui_radiobutton_bg": _hex("1c1917"),
        "ui_radiobutton_fg": _hex("fefefe"),
        "ui_radiobutton_border": _hex("44403c"),
        "ui_radiobutton_selected_bg": _hex("f97316"),
        "ui_radiobutton_selected_fg": _hex("ffffff"),
        "ui_menubutton_bg": _hex("292524"),
        "ui_menubutton_fg": _hex("fefefe"),
        "ui_menubutton_border": _hex("44403c"),
        "ui_menubutton_hover_bg": _hex("44403c"),
        "ui_optionmenu_bg": _hex("292524"),
        "ui_optionmenu_fg": _hex("fefefe"),
        "ui_optionmenu_border": _hex("44403c"),
        "ui_optionmenu_hover_bg": _hex("44403c"),
        "ui_combobox_bg": _hex("1c1917"),
        "ui_combobox_fg": _hex("fefefe"),
        "ui_combobox_border": _hex("44403c"),
        "ui_combobox_focus_border": _hex("f97316"),
        "ui_progressbar_bg": _hex("f97316"),
        "ui_progressbar_trough": _hex("292524"),
        "ui_treeview_bg": _hex("1c1917"),
        "ui_treeview_fg": _hex("fefefe"),
        "ui_treeview_border": _hex("44403c"),
        "ui_treeview_heading_bg": _hex("292524"),
        "ui_treeview_heading_fg": _hex("fefefe"),
        "ui_treeview_heading_border": _hex("44403c"),
        "ui_separator_bg": _hex("44403c"),
        "ui_labelframe_bg": _hex("1c1917"),
        "ui_labelframe_fg": _hex("fefefe"),
        "ui_labelframe_border": _hex("44403c"),
        "ui_labelframe_label_bg": _hex("1c1917"),
        "ui_labelframe_label_fg": _hex("fefefe"),
        "ui_notebook_bg": _hex("1c1917"),
        "ui_notebook_border": _hex("44403c"),
        "ui_notebook_pane_bg": _hex("1c1917"),
        "ui_notebook_pane_border": _hex("44403c"),
        "default_airframe_colorset": "Sunset Orange",
    },
    "Midnight Purple": {
        "name": "Midnight Purple",
        "description": "Deep purple theme with elegant contrast",
        "game_bg": _hex("0f0f23"),
        "game_fg": _hex("f8fafc"),
        "game_muted": _hex("94a3b8"),
        "hub_color": _hex("1e1b4b"),
        "good_spoke": _hex("a855f7"),
        "bad_spoke": _hex("f87171"),
        "bar_A": _hex("8b5cf6"),
        "bar_B": _hex("ec4899"),
        "bar_C": _hex("a855f7"),
        "bar_D": _hex("f59e0b"),
        "accent_primary": _hex("8b5cf6"),
        "accent_secondary": _hex("ec4899"),
        "success": _hex("a855f7"),
        "warning": _hex("f59e0b"),
        "error": _hex("f87171"),
        "info": _hex("06b6d4"),
        # Comprehensive UI colors
        "ui_bg": _hex("0f0f23"),
        "ui_fg": _hex("f8fafc"),
        "ui_muted": _hex("94a3b8"),
        "ui_border": _hex("312e81"),
        "ui_card_bg": _hex("1e1b4b"),
        "ui_field_bg": _hex("0f0f23"),
        "ui_hover_bg": _hex("312e81"),
        "ui_active_bg": _hex("581c87"),
        "ui_disabled_bg": _hex("1e1b4b"),
        "ui_disabled_fg": _hex("64748b"),
        "ui_selection_bg": _hex("581c87"),
        "ui_selection_fg": _hex("f8fafc"),
        "ui_tab_bg": _hex("1e1b4b"),
        "ui_tab_fg": _hex("94a3b8"),
        "ui_tab_selected_bg": _hex("0f0f23"),
        "ui_tab_selected_fg": _hex("f8fafc"),
        "ui_tab_border": _hex("312e81"),
        "ui_button_bg": _hex("1e1b4b"),
        "ui_button_fg": _hex("f8fafc"),
        "ui_button_border": _hex("312e81"),
        "ui_button_hover_bg": _hex("312e81"),
        "ui_button_active_bg": _hex("581c87"),
        "ui_button_primary_bg": _hex("8b5cf6"),
        "ui_button_primary_fg": _hex("ffffff"),
        "ui_button_primary_border": _hex("8b5cf6"),
        "ui_button_primary_hover_bg": _hex("7c3aed"),
        "ui_button_secondary_bg": _hex("ec4899"),
        "ui_button_secondary_fg": _hex("ffffff"),
        "ui_button_secondary_border": _hex("ec4899"),
        "ui_button_secondary_hover_bg": _hex("db2777"),
        "ui_button_success_bg": _hex("a855f7"),
        "ui_button_success_fg": _hex("ffffff"),
        "ui_button_success_border": _hex("a855f7"),
        "ui_button_success_hover_bg": _hex("9333ea"),
        "ui_button_warning_bg": _hex("f59e0b"),
        "ui_button_warning_fg": _hex("ffffff"),
        "ui_button_warning_border": _hex("f59e0b"),
        "ui_button_warning_hover_bg": _hex("d97706"),
        "ui_button_error_bg": _hex("f87171"),
        "ui_button_error_fg": _hex("ffffff"),
        "ui_button_error_border": _hex("f87171"),
        "ui_button_error_hover_bg": _hex("ef4444"),
        "ui_entry_bg": _hex("0f0f23"),
        "ui_entry_fg": _hex("f8fafc"),
        "ui_entry_border": _hex("312e81"),
        "ui_entry_focus_border": _hex("8b5cf6"),
        "ui_spinbox_bg": _hex("0f0f23"),
        "ui_spinbox_fg": _hex("f8fafc"),
        "ui_spinbox_border": _hex("312e81"),
        "ui_spinbox_focus_border": _hex("8b5cf6"),
        "ui_scale_bg": _hex("1e1b4b"),
        "ui_scale_trough": _hex("312e81"),
        "ui_scale_slider": _hex("8b5cf6"),
        "ui_checkbox_bg": _hex("0f0f23"),
        "ui_checkbox_fg": _hex("f8fafc"),
        "ui_checkbox_border": _hex("312e81"),
        "ui_checkbox_selected_bg": _hex("8b5cf6"),
        "ui_checkbox_selected_fg": _hex("ffffff"),
        "ui_radiobutton_bg": _hex("0f0f23"),
        "ui_radiobutton_fg": _hex("f8fafc"),
        "ui_radiobutton_border": _hex("312e81"),
        "ui_radiobutton_selected_bg": _hex("8b5cf6"),
        "ui_radiobutton_selected_fg": _hex("ffffff"),
        "ui_menubutton_bg": _hex("1e1b4b"),
        "ui_menubutton_fg": _hex("f8fafc"),
        "ui_menubutton_border": _hex("312e81"),
        "ui_menubutton_hover_bg": _hex("312e81"),
        "ui_optionmenu_bg": _hex("1e1b4b"),
        "ui_optionmenu_fg": _hex("f8fafc"),
        "ui_optionmenu_border": _hex("312e81"),
        "ui_optionmenu_hover_bg": _hex("312e81"),
        "ui_combobox_bg": _hex("0f0f23"),
        "ui_combobox_fg": _hex("f8fafc"),
        "ui_combobox_border": _hex("312e81"),
        "ui_combobox_focus_border": _hex("8b5cf6"),
        "ui_progressbar_bg": _hex("8b5cf6"),
        "ui_progressbar_trough": _hex("1e1b4b"),
        "ui_treeview_bg": _hex("0f0f23"),
        "ui_treeview_fg": _hex("f8fafc"),
        "ui_treeview_border": _hex("312e81"),
        "ui_treeview_heading_bg": _hex("1e1b4b"),
        "ui_treeview_heading_fg": _hex("f8fafc"),
        "ui_treeview_heading_border": _hex("312e81"),
        "ui_separator_bg": _hex("312e81"),
        "ui_labelframe_bg": _hex("0f0f23"),
        "ui_labelframe_fg": _hex("f8fafc"),
        "ui_labelframe_border": _hex("312e81"),
        "ui_labelframe_label_bg": _hex("0f0f23"),
        "ui_labelframe_label_fg": _hex("f8fafc"),
        "ui_notebook_bg": _hex("0f0f23"),
        "ui_notebook_border": _hex("312e81"),
        "ui_notebook_pane_bg": _hex("0f0f23"),
        "ui_notebook_pane_border": _hex("312e81"),
        "default_airframe_colorset": "Midnight Purple",
    },
    "High Contrast": {
        "name": "High Contrast",
        "description": "Maximum contrast theme for accessibility",
        "game_bg": _hex("000000"),
        "game_fg": _hex("ffffff"),
        "game_muted": _hex("cccccc"),
        "hub_color": _hex("1a1a1a"),
        "good_spoke": _hex("00ff00"),
        "bad_spoke": _hex("ff0000"),
        "bar_A": _hex("0080ff"),
        "bar_B": _hex("ffff00"),
        "bar_C": _hex("00ff00"),
        "bar_D": _hex("ff8000"),
        "accent_primary": _hex("0080ff"),
        "accent_secondary": _hex("ffff00"),
        "success": _hex("00ff00"),
        "warning": _hex("ffff00"),
        "error": _hex("ff0000"),
        "info": _hex("0080ff"),
        # Comprehensive UI colors
        "ui_bg": _hex("000000"),
        "ui_fg": _hex("ffffff"),
        "ui_muted": _hex("cccccc"),
        "ui_border": _hex("404040"),
        "ui_card_bg": _hex("1a1a1a"),
        "ui_field_bg": _hex("000000"),
        "ui_hover_bg": _hex("404040"),
        "ui_active_bg": _hex("0066cc"),
        "ui_disabled_bg": _hex("1a1a1a"),
        "ui_disabled_fg": _hex("666666"),
        "ui_selection_bg": _hex("0066cc"),
        "ui_selection_fg": _hex("ffffff"),
        "ui_tab_bg": _hex("1a1a1a"),
        "ui_tab_fg": _hex("cccccc"),
        "ui_tab_selected_bg": _hex("000000"),
        "ui_tab_selected_fg": _hex("ffffff"),
        "ui_tab_border": _hex("404040"),
        "ui_button_bg": _hex("1a1a1a"),
        "ui_button_fg": _hex("ffffff"),
        "ui_button_border": _hex("404040"),
        "ui_button_hover_bg": _hex("404040"),
        "ui_button_active_bg": _hex("0066cc"),
        "ui_button_primary_bg": _hex("0080ff"),
        "ui_button_primary_fg": _hex("ffffff"),
        "ui_button_primary_border": _hex("0080ff"),
        "ui_button_primary_hover_bg": _hex("0066cc"),
        "ui_button_secondary_bg": _hex("ffff00"),
        "ui_button_secondary_fg": _hex("000000"),
        "ui_button_secondary_border": _hex("ffff00"),
        "ui_button_secondary_hover_bg": _hex("e6e600"),
        "ui_button_success_bg": _hex("00ff00"),
        "ui_button_success_fg": _hex("000000"),
        "ui_button_success_border": _hex("00ff00"),
        "ui_button_success_hover_bg": _hex("00e600"),
        "ui_button_warning_bg": _hex("ffff00"),
        "ui_button_warning_fg": _hex("000000"),
        "ui_button_warning_border": _hex("ffff00"),
        "ui_button_warning_hover_bg": _hex("e6e600"),
        "ui_button_error_bg": _hex("ff0000"),
        "ui_button_error_fg": _hex("ffffff"),
        "ui_button_error_border": _hex("ff0000"),
        "ui_button_error_hover_bg": _hex("cc0000"),
        "ui_entry_bg": _hex("000000"),
        "ui_entry_fg": _hex("ffffff"),
        "ui_entry_border": _hex("404040"),
        "ui_entry_focus_border": _hex("0080ff"),
        "ui_spinbox_bg": _hex("000000"),
        "ui_spinbox_fg": _hex("ffffff"),
        "ui_spinbox_border": _hex("404040"),
        "ui_spinbox_focus_border": _hex("0080ff"),
        "ui_scale_bg": _hex("1a1a1a"),
        "ui_scale_trough": _hex("404040"),
        "ui_scale_slider": _hex("0080ff"),
        "ui_checkbox_bg": _hex("000000"),
        "ui_checkbox_fg": _hex("ffffff"),
        "ui_checkbox_border": _hex("404040"),
        "ui_checkbox_selected_bg": _hex("0080ff"),
        "ui_checkbox_selected_fg": _hex("ffffff"),
        "ui_radiobutton_bg": _hex("000000"),
        "ui_radiobutton_fg": _hex("ffffff"),
        "ui_radiobutton_border": _hex("404040"),
        "ui_radiobutton_selected_bg": _hex("0080ff"),
        "ui_radiobutton_selected_fg": _hex("ffffff"),
        "ui_menubutton_bg": _hex("1a1a1a"),
        "ui_menubutton_fg": _hex("ffffff"),
        "ui_menubutton_border": _hex("404040"),
        "ui_menubutton_hover_bg": _hex("404040"),
        "ui_optionmenu_bg": _hex("1a1a1a"),
        "ui_optionmenu_fg": _hex("ffffff"),
        "ui_optionmenu_border": _hex("404040"),
        "ui_optionmenu_hover_bg": _hex("404040"),
        "ui_combobox_bg": _hex("000000"),
        "ui_combobox_fg": _hex("ffffff"),
        "ui_combobox_border": _hex("404040"),
        "ui_combobox_focus_border": _hex("0080ff"),
        "ui_progressbar_bg": _hex("0080ff"),
        "ui_progressbar_trough": _hex("1a1a1a"),
        "ui_treeview_bg": _hex("000000"),
        "ui_treeview_fg": _hex("ffffff"),
        "ui_treeview_border": _hex("404040"),
        "ui_treeview_heading_bg": _hex("1a1a1a"),
        "ui_treeview_heading_fg": _hex("ffffff"),
        "ui_treeview_heading_border": _hex("404040"),
        "ui_separator_bg": _hex("404040"),
        "ui_labelframe_bg": _hex("000000"),
        "ui_labelframe_fg": _hex("ffffff"),
        "ui_labelframe_border": _hex("404040"),
        "ui_labelframe_label_bg": _hex("000000"),
        "ui_labelframe_label_fg": _hex("ffffff"),
        "ui_notebook_bg": _hex("000000"),
        "ui_notebook_border": _hex("404040"),
        "ui_notebook_pane_bg": _hex("000000"),
        "ui_notebook_pane_border": _hex("404040"),
        "default_airframe_colorset": "High Contrast",
    },
    "Cyber Green": {
        "name": "Cyber Green",
        "description": "Retro terminal aesthetic with green on true black - everything is cyber-themed",
        "game_bg": _hex("000000"),
        "game_fg": _hex("00ff41"),
        "game_muted": _hex("00cc33"),
        "hub_color": _hex("000000"),
        "good_spoke": _hex("00ff41"),
        "bad_spoke": _hex("00ff41"),
        "bar_A": _hex("00ff41"),
        "bar_B": _hex("00e63a"),
        "bar_C": _hex("00cc33"),
        "bar_D": _hex("009926"),
        "accent_primary": _hex("00ff41"),
        "accent_secondary": _hex("00e63a"),
        "success": _hex("00ff41"),
        "warning": _hex("00e63a"),
        "error": _hex("00cc33"),
        "info": _hex("009926"),
        # Comprehensive UI colors - Cyber transformation with TRUE BLACK
        "ui_bg": _hex("000000"),
        "ui_fg": _hex("00ff41"),
        "ui_muted": _hex("00cc33"),
        "ui_border": _hex("00ff41"),
        "ui_card_bg": _hex("000000"),
        "ui_field_bg": _hex("000000"),
        "ui_hover_bg": _hex("001100"),
        "ui_active_bg": _hex("002200"),
        "ui_disabled_bg": _hex("000000"),
        "ui_disabled_fg": _hex("006622"),
        "ui_selection_bg": _hex("002200"),
        "ui_selection_fg": _hex("00ff41"),
        "ui_tab_bg": _hex("000000"),
        "ui_tab_fg": _hex("00ff41"),
        "ui_tab_selected_bg": _hex("000000"),
        "ui_tab_selected_fg": _hex("00ff41"),
        "ui_tab_border": _hex("00ff41"),
        "ui_button_bg": _hex("000000"),
        "ui_button_fg": _hex("00ff41"),
        "ui_button_border": _hex("00ff41"),
        "ui_button_hover_bg": _hex("001100"),
        "ui_button_active_bg": _hex("002200"),
        "ui_button_primary_bg": _hex("00ff41"),
        "ui_button_primary_fg": _hex("000000"),
        "ui_button_primary_border": _hex("00ff41"),
        "ui_button_primary_hover_bg": _hex("00e63a"),
        "ui_button_secondary_bg": _hex("00e63a"),
        "ui_button_secondary_fg": _hex("000000"),
        "ui_button_secondary_border": _hex("00e63a"),
        "ui_button_secondary_hover_bg": _hex("00cc33"),
        "ui_button_success_bg": _hex("00ff41"),
        "ui_button_success_fg": _hex("000000"),
        "ui_button_success_border": _hex("00ff41"),
        "ui_button_success_hover_bg": _hex("00e63a"),
        "ui_button_warning_bg": _hex("00e63a"),
        "ui_button_warning_fg": _hex("000000"),
        "ui_button_warning_border": _hex("00e63a"),
        "ui_button_warning_hover_bg": _hex("00cc33"),
        "ui_button_error_bg": _hex("00cc33"),
        "ui_button_error_fg": _hex("000000"),
        "ui_button_error_border": _hex("00cc33"),
        "ui_button_error_hover_bg": _hex("009926"),
        "ui_entry_bg": _hex("000000"),
        "ui_entry_fg": _hex("00ff41"),
        "ui_entry_border": _hex("00ff41"),
        "ui_entry_focus_border": _hex("00ff41"),
        "ui_spinbox_bg": _hex("000000"),
        "ui_spinbox_fg": _hex("00ff41"),
        "ui_spinbox_border": _hex("00ff41"),
        "ui_spinbox_focus_border": _hex("00ff41"),
        "ui_scale_bg": _hex("000000"),
        "ui_scale_trough": _hex("000000"),
        "ui_scale_slider": _hex("00ff41"),
        "ui_checkbox_bg": _hex("000000"),
        "ui_checkbox_fg": _hex("00ff41"),
        "ui_checkbox_border": _hex("00ff41"),
        "ui_checkbox_selected_bg": _hex("00ff41"),
        "ui_checkbox_selected_fg": _hex("000000"),
        "ui_radiobutton_bg": _hex("000000"),
        "ui_radiobutton_fg": _hex("00ff41"),
        "ui_radiobutton_border": _hex("00ff41"),
        "ui_radiobutton_selected_bg": _hex("00ff41"),
        "ui_radiobutton_selected_fg": _hex("000000"),
        "ui_menubutton_bg": _hex("000000"),
        "ui_menubutton_fg": _hex("00ff41"),
        "ui_menubutton_border": _hex("00ff41"),
        "ui_menubutton_hover_bg": _hex("001100"),
        "ui_optionmenu_bg": _hex("000000"),
        "ui_optionmenu_fg": _hex("00ff41"),
        "ui_optionmenu_border": _hex("00ff41"),
        "ui_optionmenu_hover_bg": _hex("001100"),
        "ui_combobox_bg": _hex("000000"),
        "ui_combobox_fg": _hex("00ff41"),
        "ui_combobox_border": _hex("00ff41"),
        "ui_combobox_focus_border": _hex("00ff41"),
        "ui_progressbar_bg": _hex("00ff41"),
        "ui_progressbar_trough": _hex("000000"),
        "ui_treeview_bg": _hex("000000"),
        "ui_treeview_fg": _hex("00ff41"),
        "ui_treeview_border": _hex("00ff41"),
        "ui_treeview_heading_bg": _hex("000000"),
        "ui_treeview_heading_fg": _hex("00ff41"),
        "ui_treeview_heading_border": _hex("00ff41"),
        "ui_separator_bg": _hex("00ff41"),
        "ui_labelframe_bg": _hex("000000"),
        "ui_labelframe_fg": _hex("00ff41"),
        "ui_labelframe_border": _hex("00ff41"),
        "ui_labelframe_label_bg": _hex("000000"),
        "ui_labelframe_label_fg": _hex("00ff41"),
        "ui_notebook_bg": _hex("000000"),
        "ui_notebook_border": _hex("00ff41"),
        "ui_notebook_pane_bg": _hex("000000"),
        "ui_notebook_pane_border": _hex("00ff41"),
        "default_airframe_colorset": "Cyber Green",
    },
    "Desert Sand": {
        "name": "Desert Sand",
        "description": "Warm desert theme with sandy browns and terracotta",
        "game_bg": _hex("fef7f0"),
        "game_fg": _hex("2d1810"),
        "game_muted": _hex("8b5a3c"),
        "hub_color": _hex("f5e6d3"),
        "good_spoke": _hex("d97706"),
        "bad_spoke": _hex("dc2626"),
        "bar_A": _hex("b45309"),
        "bar_B": _hex("d97706"),
        "bar_C": _hex("a16207"),
        "bar_D": _hex("dc2626"),
        "accent_primary": _hex("b45309"),
        "accent_secondary": _hex("d97706"),
        "success": _hex("a16207"),
        "warning": _hex("d97706"),
        "error": _hex("dc2626"),
        "info": _hex("0891b2"),
        # Comprehensive UI colors
        "ui_bg": _hex("fef7f0"),
        "ui_fg": _hex("2d1810"),
        "ui_muted": _hex("8b5a3c"),
        "ui_border": _hex("d6d3d1"),
        "ui_card_bg": _hex("f5e6d3"),
        "ui_field_bg": _hex("fef7f0"),
        "ui_hover_bg": _hex("ede4d7"),
        "ui_active_bg": _hex("fef3c7"),
        "ui_disabled_bg": _hex("f5e6d3"),
        "ui_disabled_fg": _hex("a8a29e"),
        "ui_selection_bg": _hex("fef3c7"),
        "ui_selection_fg": _hex("92400e"),
        "ui_tab_bg": _hex("ede4d7"),
        "ui_tab_fg": _hex("8b5a3c"),
        "ui_tab_selected_bg": _hex("fef7f0"),
        "ui_tab_selected_fg": _hex("2d1810"),
        "ui_tab_border": _hex("d6d3d1"),
        "ui_button_bg": _hex("ede4d7"),
        "ui_button_fg": _hex("2d1810"),
        "ui_button_border": _hex("d6d3d1"),
        "ui_button_hover_bg": _hex("d6d3d1"),
        "ui_button_active_bg": _hex("fef3c7"),
        "ui_button_primary_bg": _hex("b45309"),
        "ui_button_primary_fg": _hex("ffffff"),
        "ui_button_primary_border": _hex("b45309"),
        "ui_button_primary_hover_bg": _hex("92400e"),
        "ui_button_secondary_bg": _hex("d97706"),
        "ui_button_secondary_fg": _hex("ffffff"),
        "ui_button_secondary_border": _hex("d97706"),
        "ui_button_secondary_hover_bg": _hex("b45309"),
        "ui_button_success_bg": _hex("a16207"),
        "ui_button_success_fg": _hex("ffffff"),
        "ui_button_success_border": _hex("a16207"),
        "ui_button_success_hover_bg": _hex("854d0e"),
        "ui_button_warning_bg": _hex("d97706"),
        "ui_button_warning_fg": _hex("ffffff"),
        "ui_button_warning_border": _hex("d97706"),
        "ui_button_warning_hover_bg": _hex("b45309"),
        "ui_button_error_bg": _hex("dc2626"),
        "ui_button_error_fg": _hex("ffffff"),
        "ui_button_error_border": _hex("dc2626"),
        "ui_button_error_hover_bg": _hex("b91c1c"),
        "ui_entry_bg": _hex("fef7f0"),
        "ui_entry_fg": _hex("2d1810"),
        "ui_entry_border": _hex("d6d3d1"),
        "ui_entry_focus_border": _hex("b45309"),
        "ui_spinbox_bg": _hex("fef7f0"),
        "ui_spinbox_fg": _hex("2d1810"),
        "ui_spinbox_border": _hex("d6d3d1"),
        "ui_spinbox_focus_border": _hex("b45309"),
        "ui_scale_bg": _hex("ede4d7"),
        "ui_scale_trough": _hex("d6d3d1"),
        "ui_scale_slider": _hex("b45309"),
        "ui_checkbox_bg": _hex("fef7f0"),
        "ui_checkbox_fg": _hex("2d1810"),
        "ui_checkbox_border": _hex("d6d3d1"),
        "ui_checkbox_selected_bg": _hex("b45309"),
        "ui_checkbox_selected_fg": _hex("ffffff"),
        "ui_radiobutton_bg": _hex("fef7f0"),
        "ui_radiobutton_fg": _hex("2d1810"),
        "ui_radiobutton_border": _hex("d6d3d1"),
        "ui_radiobutton_selected_bg": _hex("b45309"),
        "ui_radiobutton_selected_fg": _hex("ffffff"),
        "ui_menubutton_bg": _hex("ede4d7"),
        "ui_menubutton_fg": _hex("2d1810"),
        "ui_menubutton_border": _hex("d6d3d1"),
        "ui_menubutton_hover_bg": _hex("d6d3d1"),
        "ui_optionmenu_bg": _hex("ede4d7"),
        "ui_optionmenu_fg": _hex("2d1810"),
        "ui_optionmenu_border": _hex("d6d3d1"),
        "ui_optionmenu_hover_bg": _hex("d6d3d1"),
        "ui_combobox_bg": _hex("fef7f0"),
        "ui_combobox_fg": _hex("2d1810"),
        "ui_combobox_border": _hex("d6d3d1"),
        "ui_combobox_focus_border": _hex("b45309"),
        "ui_progressbar_bg": _hex("b45309"),
        "ui_progressbar_trough": _hex("ede4d7"),
        "ui_treeview_bg": _hex("fef7f0"),
        "ui_treeview_fg": _hex("2d1810"),
        "ui_treeview_border": _hex("d6d3d1"),
        "ui_treeview_heading_bg": _hex("ede4d7"),
        "ui_treeview_heading_fg": _hex("2d1810"),
        "ui_treeview_heading_border": _hex("d6d3d1"),
        "ui_separator_bg": _hex("d6d3d1"),
        "ui_labelframe_bg": _hex("fef7f0"),
        "ui_labelframe_fg": _hex("2d1810"),
        "ui_labelframe_border": _hex("d6d3d1"),
        "ui_labelframe_label_bg": _hex("fef7f0"),
        "ui_labelframe_label_fg": _hex("2d1810"),
        "ui_notebook_bg": _hex("fef7f0"),
        "ui_notebook_border": _hex("d6d3d1"),
        "ui_notebook_pane_bg": _hex("fef7f0"),
        "ui_notebook_pane_border": _hex("d6d3d1"),
        "default_airframe_colorset": "Desert Sand",
    },
    "Arctic Blue": {
        "name": "Arctic Blue",
        "description": "Cool, crisp theme inspired by ice and snow",
        "game_bg": _hex("f0f9ff"),
        "game_fg": _hex("0c4a6e"),
        "game_muted": _hex("0369a1"),
        "hub_color": _hex("e0f2fe"),
        "good_spoke": _hex("0891b2"),
        "bad_spoke": _hex("dc2626"),
        "bar_A": _hex("0ea5e9"),
        "bar_B": _hex("0891b2"),
        "bar_C": _hex("06b6d4"),
        "bar_D": _hex("dc2626"),
        "accent_primary": _hex("0ea5e9"),
        "accent_secondary": _hex("0891b2"),
        "success": _hex("0891b2"),
        "warning": _hex("f59e0b"),
        "error": _hex("dc2626"),
        "info": _hex("06b6d4"),
        # Comprehensive UI colors
        "ui_bg": _hex("f0f9ff"),
        "ui_fg": _hex("0c4a6e"),
        "ui_muted": _hex("0369a1"),
        "ui_border": _hex("bae6fd"),
        "ui_card_bg": _hex("e0f2fe"),
        "ui_field_bg": _hex("f0f9ff"),
        "ui_hover_bg": _hex("bae6fd"),
        "ui_active_bg": _hex("7dd3fc"),
        "ui_disabled_bg": _hex("e0f2fe"),
        "ui_disabled_fg": _hex("7dd3fc"),
        "ui_selection_bg": _hex("7dd3fc"),
        "ui_selection_fg": _hex("0c4a6e"),
        "ui_tab_bg": _hex("bae6fd"),
        "ui_tab_fg": _hex("0369a1"),
        "ui_tab_selected_bg": _hex("f0f9ff"),
        "ui_tab_selected_fg": _hex("0c4a6e"),
        "ui_tab_border": _hex("bae6fd"),
        "ui_button_bg": _hex("bae6fd"),
        "ui_button_fg": _hex("0c4a6e"),
        "ui_button_border": _hex("bae6fd"),
        "ui_button_hover_bg": _hex("7dd3fc"),
        "ui_button_active_bg": _hex("7dd3fc"),
        "ui_button_primary_bg": _hex("0ea5e9"),
        "ui_button_primary_fg": _hex("ffffff"),
        "ui_button_primary_border": _hex("0ea5e9"),
        "ui_button_primary_hover_bg": _hex("0284c7"),
        "ui_button_secondary_bg": _hex("0891b2"),
        "ui_button_secondary_fg": _hex("ffffff"),
        "ui_button_secondary_border": _hex("0891b2"),
        "ui_button_secondary_hover_bg": _hex("0e7490"),
        "ui_button_success_bg": _hex("0891b2"),
        "ui_button_success_fg": _hex("ffffff"),
        "ui_button_success_border": _hex("0891b2"),
        "ui_button_success_hover_bg": _hex("0e7490"),
        "ui_button_warning_bg": _hex("f59e0b"),
        "ui_button_warning_fg": _hex("ffffff"),
        "ui_button_warning_border": _hex("f59e0b"),
        "ui_button_warning_hover_bg": _hex("d97706"),
        "ui_button_error_bg": _hex("dc2626"),
        "ui_button_error_fg": _hex("ffffff"),
        "ui_button_error_border": _hex("dc2626"),
        "ui_button_error_hover_bg": _hex("b91c1c"),
        "ui_entry_bg": _hex("f0f9ff"),
        "ui_entry_fg": _hex("0c4a6e"),
        "ui_entry_border": _hex("bae6fd"),
        "ui_entry_focus_border": _hex("0ea5e9"),
        "ui_spinbox_bg": _hex("f0f9ff"),
        "ui_spinbox_fg": _hex("0c4a6e"),
        "ui_spinbox_border": _hex("bae6fd"),
        "ui_spinbox_focus_border": _hex("0ea5e9"),
        "ui_scale_bg": _hex("bae6fd"),
        "ui_scale_trough": _hex("7dd3fc"),
        "ui_scale_slider": _hex("0ea5e9"),
        "ui_checkbox_bg": _hex("f0f9ff"),
        "ui_checkbox_fg": _hex("0c4a6e"),
        "ui_checkbox_border": _hex("bae6fd"),
        "ui_checkbox_selected_bg": _hex("0ea5e9"),
        "ui_checkbox_selected_fg": _hex("ffffff"),
        "ui_radiobutton_bg": _hex("f0f9ff"),
        "ui_radiobutton_fg": _hex("0c4a6e"),
        "ui_radiobutton_border": _hex("bae6fd"),
        "ui_radiobutton_selected_bg": _hex("0ea5e9"),
        "ui_radiobutton_selected_fg": _hex("ffffff"),
        "ui_menubutton_bg": _hex("bae6fd"),
        "ui_menubutton_fg": _hex("0c4a6e"),
        "ui_menubutton_border": _hex("bae6fd"),
        "ui_menubutton_hover_bg": _hex("7dd3fc"),
        "ui_optionmenu_bg": _hex("bae6fd"),
        "ui_optionmenu_fg": _hex("0c4a6e"),
        "ui_optionmenu_border": _hex("bae6fd"),
        "ui_optionmenu_hover_bg": _hex("7dd3fc"),
        "ui_combobox_bg": _hex("f0f9ff"),
        "ui_combobox_fg": _hex("0c4a6e"),
        "ui_combobox_border": _hex("bae6fd"),
        "ui_combobox_focus_border": _hex("0ea5e9"),
        "ui_progressbar_bg": _hex("0ea5e9"),
        "ui_progressbar_trough": _hex("bae6fd"),
        "ui_treeview_bg": _hex("f0f9ff"),
        "ui_treeview_fg": _hex("0c4a6e"),
        "ui_treeview_border": _hex("bae6fd"),
        "ui_treeview_heading_bg": _hex("bae6fd"),
        "ui_treeview_heading_fg": _hex("0c4a6e"),
        "ui_treeview_heading_border": _hex("bae6fd"),
        "ui_separator_bg": _hex("bae6fd"),
        "ui_labelframe_bg": _hex("f0f9ff"),
        "ui_labelframe_fg": _hex("0c4a6e"),
        "ui_labelframe_border": _hex("bae6fd"),
        "ui_labelframe_label_bg": _hex("f0f9ff"),
        "ui_labelframe_label_fg": _hex("0c4a6e"),
        "ui_notebook_bg": _hex("f0f9ff"),
        "ui_notebook_border": _hex("bae6fd"),
        "ui_notebook_pane_bg": _hex("f0f9ff"),
        "ui_notebook_pane_border": _hex("bae6fd"),
        "default_airframe_colorset": "Arctic Blue",
    }
}

# Enhanced cursor colors with better contrast
CURSOR_COLORS = {
    "Cobalt": _hex("2563eb"),
    "Signal Orange": _hex("ea580c"),
    "Cyber Lime": _hex("65a30d"),
    "Cerulean": _hex("0891b2"),
    "Royal Magenta": _hex("a855f7"),
}

# Enhanced airframe colorsets with better color harmony
AIRFRAME_COLORSETS = {
    "Professional Blue": {"C-130": "#2563eb", "C-27": "#7c3aed"},
    "Ocean Blue": {"C-130": "#0ea5e9", "C-27": "#06b6d4"},
    "Forest Green": {"C-130": "#059669", "C-27": "#16a34a"},
    "Sunset Orange": {"C-130": "#f97316", "C-27": "#a855f7"},
    "Midnight Purple": {"C-130": "#8b5cf6", "C-27": "#ec4899"},
    "High Contrast": {"C-130": "#0080ff", "C-27": "#ffff00"},
    "Cyber Green": {"C-130": "#00ff41", "C-27": "#00e63a"},
    "Desert Sand": {"C-130": "#b45309", "C-27": "#d97706"},
    "Arctic Blue": {"C-130": "#0ea5e9", "C-27": "#0891b2"},
    "Classic Gray": {"C-130": "#6b7280", "C-27": "#9ca3af"},
}


def apply_theme_preset(t: "ThemeConfig", name: str):
    p = THEME_PRESETS.get(name, THEME_PRESETS["Classic Light"])
    t.preset = name
    # Game colors
    t.game_bg = p["game_bg"]
    t.game_fg = p["game_fg"]
    t.game_muted = p["game_muted"]
    t.hub_color = p["hub_color"]
    t.good_spoke = p["good_spoke"]
    t.bad_spoke = p["bad_spoke"]
    t.bar_A = p["bar_A"]
    t.bar_B = p["bar_B"]
    t.bar_C = p["bar_C"]
    t.bar_D = p["bar_D"]
    # Semantic color tokens
    t.accent_primary = p.get("accent_primary", t.accent_primary)
    t.accent_secondary = p.get("accent_secondary", t.accent_secondary)
    t.success = p.get("success", t.success)
    t.warning = p.get("warning", t.warning)
    t.error = p.get("error", t.error)
    t.info = p.get("info", t.info)
    # Comprehensive UI colors for every element
    t.ui_bg = p.get("ui_bg", t.ui_bg)
    t.ui_fg = p.get("ui_fg", t.ui_fg)
    t.ui_muted = p.get("ui_muted", t.ui_muted)
    t.ui_border = p.get("ui_border", t.ui_border)
    t.ui_card_bg = p.get("ui_card_bg", t.ui_card_bg)
    t.ui_field_bg = p.get("ui_field_bg", t.ui_field_bg)
    t.ui_hover_bg = p.get("ui_hover_bg", t.ui_hover_bg)
    t.ui_active_bg = p.get("ui_active_bg", t.ui_active_bg)
    t.ui_disabled_bg = p.get("ui_disabled_bg", t.ui_disabled_bg)
    t.ui_disabled_fg = p.get("ui_disabled_fg", t.ui_disabled_fg)
    t.ui_selection_bg = p.get("ui_selection_bg", t.ui_selection_bg)
    t.ui_selection_fg = p.get("ui_selection_fg", t.ui_selection_fg)
    t.ui_tab_bg = p.get("ui_tab_bg", t.ui_tab_bg)
    t.ui_tab_fg = p.get("ui_tab_fg", t.ui_tab_fg)
    t.ui_tab_selected_bg = p.get("ui_tab_selected_bg", t.ui_tab_selected_bg)
    t.ui_tab_selected_fg = p.get("ui_tab_selected_fg", t.ui_tab_selected_fg)
    t.ui_tab_border = p.get("ui_tab_border", t.ui_tab_border)
    t.ui_button_bg = p.get("ui_button_bg", t.ui_button_bg)
    t.ui_button_fg = p.get("ui_button_fg", t.ui_button_fg)
    t.ui_button_border = p.get("ui_button_border", t.ui_button_border)
    t.ui_button_hover_bg = p.get("ui_button_hover_bg", t.ui_button_hover_bg)
    t.ui_button_active_bg = p.get("ui_button_active_bg", t.ui_button_active_bg)
    t.ui_button_primary_bg = p.get("ui_button_primary_bg", t.ui_button_primary_bg)
    t.ui_button_primary_fg = p.get("ui_button_primary_fg", t.ui_button_primary_fg)
    t.ui_button_primary_border = p.get("ui_button_primary_border", t.ui_button_primary_border)
    t.ui_button_primary_hover_bg = p.get("ui_button_primary_hover_bg", t.ui_button_primary_hover_bg)
    t.ui_button_secondary_bg = p.get("ui_button_secondary_bg", t.ui_button_secondary_bg)
    t.ui_button_secondary_fg = p.get("ui_button_secondary_fg", t.ui_button_secondary_fg)
    t.ui_button_secondary_border = p.get("ui_button_secondary_border", t.ui_button_secondary_border)
    t.ui_button_secondary_hover_bg = p.get("ui_button_secondary_hover_bg", t.ui_button_secondary_hover_bg)
    t.ui_button_success_bg = p.get("ui_button_success_bg", t.ui_button_success_bg)
    t.ui_button_success_fg = p.get("ui_button_success_fg", t.ui_button_success_fg)
    t.ui_button_success_border = p.get("ui_button_success_border", t.ui_button_success_border)
    t.ui_button_success_hover_bg = p.get("ui_button_success_hover_bg", t.ui_button_success_hover_bg)
    t.ui_button_warning_bg = p.get("ui_button_warning_bg", t.ui_button_warning_bg)
    t.ui_button_warning_fg = p.get("ui_button_warning_fg", t.ui_button_warning_fg)
    t.ui_button_warning_border = p.get("ui_button_warning_border", t.ui_button_warning_border)
    t.ui_button_warning_hover_bg = p.get("ui_button_warning_hover_bg", t.ui_button_warning_hover_bg)
    t.ui_button_error_bg = p.get("ui_button_error_bg", t.ui_button_error_bg)
    t.ui_button_error_fg = p.get("ui_button_error_fg", t.ui_button_error_fg)
    t.ui_button_error_border = p.get("ui_button_error_border", t.ui_button_error_border)
    t.ui_button_error_hover_bg = p.get("ui_button_error_hover_bg", t.ui_button_error_hover_bg)
    t.ui_entry_bg = p.get("ui_entry_bg", t.ui_entry_bg)
    t.ui_entry_fg = p.get("ui_entry_fg", t.ui_entry_fg)
    t.ui_entry_border = p.get("ui_entry_border", t.ui_entry_border)
    t.ui_entry_focus_border = p.get("ui_entry_focus_border", t.ui_entry_focus_border)
    t.ui_spinbox_bg = p.get("ui_spinbox_bg", t.ui_spinbox_bg)
    t.ui_spinbox_fg = p.get("ui_spinbox_fg", t.ui_spinbox_fg)
    t.ui_spinbox_border = p.get("ui_spinbox_border", t.ui_spinbox_border)
    t.ui_spinbox_focus_border = p.get("ui_spinbox_focus_border", t.ui_spinbox_focus_border)
    t.ui_scale_bg = p.get("ui_scale_bg", t.ui_scale_bg)
    t.ui_scale_trough = p.get("ui_scale_trough", t.ui_scale_trough)
    t.ui_scale_slider = p.get("ui_scale_slider", t.ui_scale_slider)
    t.ui_checkbox_bg = p.get("ui_checkbox_bg", t.ui_checkbox_bg)
    t.ui_checkbox_fg = p.get("ui_checkbox_fg", t.ui_checkbox_fg)
    t.ui_checkbox_border = p.get("ui_checkbox_border", t.ui_checkbox_border)
    t.ui_checkbox_selected_bg = p.get("ui_checkbox_selected_bg", t.ui_checkbox_selected_bg)
    t.ui_checkbox_selected_fg = p.get("ui_checkbox_selected_fg", t.ui_checkbox_selected_fg)
    t.ui_radiobutton_bg = p.get("ui_radiobutton_bg", t.ui_radiobutton_bg)
    t.ui_radiobutton_fg = p.get("ui_radiobutton_fg", t.ui_radiobutton_fg)
    t.ui_radiobutton_border = p.get("ui_radiobutton_border", t.ui_radiobutton_border)
    t.ui_radiobutton_selected_bg = p.get("ui_radiobutton_selected_bg", t.ui_radiobutton_selected_bg)
    t.ui_radiobutton_selected_fg = p.get("ui_radiobutton_selected_fg", t.ui_radiobutton_selected_fg)
    t.ui_menubutton_bg = p.get("ui_menubutton_bg", t.ui_menubutton_bg)
    t.ui_menubutton_fg = p.get("ui_menubutton_fg", t.ui_menubutton_fg)
    t.ui_menubutton_border = p.get("ui_menubutton_border", t.ui_menubutton_border)
    t.ui_menubutton_hover_bg = p.get("ui_menubutton_hover_bg", t.ui_menubutton_hover_bg)
    t.ui_optionmenu_bg = p.get("ui_optionmenu_bg", t.ui_optionmenu_bg)
    t.ui_optionmenu_fg = p.get("ui_optionmenu_fg", t.ui_optionmenu_fg)
    t.ui_optionmenu_border = p.get("ui_optionmenu_border", t.ui_optionmenu_border)
    t.ui_optionmenu_hover_bg = p.get("ui_optionmenu_hover_bg", t.ui_optionmenu_hover_bg)
    t.ui_combobox_bg = p.get("ui_combobox_bg", t.ui_combobox_bg)
    t.ui_combobox_fg = p.get("ui_combobox_fg", t.ui_combobox_fg)
    t.ui_combobox_border = p.get("ui_combobox_border", t.ui_combobox_border)
    t.ui_combobox_focus_border = p.get("ui_combobox_focus_border", t.ui_combobox_focus_border)
    t.ui_progressbar_bg = p.get("ui_progressbar_bg", t.ui_progressbar_bg)
    t.ui_progressbar_trough = p.get("ui_progressbar_trough", t.ui_progressbar_trough)
    t.ui_treeview_bg = p.get("ui_treeview_bg", t.ui_treeview_bg)
    t.ui_treeview_fg = p.get("ui_treeview_fg", t.ui_treeview_fg)
    t.ui_treeview_border = p.get("ui_treeview_border", t.ui_treeview_border)
    t.ui_treeview_heading_bg = p.get("ui_treeview_heading_bg", t.ui_treeview_heading_bg)
    t.ui_treeview_heading_fg = p.get("ui_treeview_heading_fg", t.ui_treeview_heading_fg)
    t.ui_treeview_heading_border = p.get("ui_treeview_heading_border", t.ui_treeview_heading_border)
    t.ui_separator_bg = p.get("ui_separator_bg", t.ui_separator_bg)
    t.ui_labelframe_bg = p.get("ui_labelframe_bg", t.ui_labelframe_bg)
    t.ui_labelframe_fg = p.get("ui_labelframe_fg", t.ui_labelframe_fg)
    t.ui_labelframe_border = p.get("ui_labelframe_border", t.ui_labelframe_border)
    t.ui_labelframe_label_bg = p.get("ui_labelframe_label_bg", t.ui_labelframe_label_bg)
    t.ui_labelframe_label_fg = p.get("ui_labelframe_label_fg", t.ui_labelframe_label_fg)
    t.ui_notebook_bg = p.get("ui_notebook_bg", t.ui_notebook_bg)
    t.ui_notebook_border = p.get("ui_notebook_border", t.ui_notebook_border)
    t.ui_notebook_pane_bg = p.get("ui_notebook_pane_bg", t.ui_notebook_pane_bg)
    t.ui_notebook_pane_border = p.get("ui_notebook_pane_border", t.ui_notebook_pane_border)
    t.theme_version = CURRENT_THEME_VERSION
    if t.ac_colorset is None:
        cmap_name = p.get("default_airframe_colorset")
        if cmap_name and cmap_name in AIRFRAME_COLORSETS:
            t.ac_colorset = cmap_name
            t.ac_colors = AIRFRAME_COLORSETS[cmap_name]


@dataclass
class ThemeConfig:
    preset: str = "Classic Light"
    # Game colors
    game_bg: str = "#ffffff"
    game_fg: str = "#1f2937"
    game_muted: str = "#6b7280"
    hub_color: str = "#f3f4f6"
    good_spoke: str = "#059669"
    bad_spoke: str = "#dc2626"
    ac_colorset: Optional[str] = None
    ac_colors: Dict[str, str] = field(default_factory=lambda: {"C-130": "#2563eb", "C-27": "#7c3aed"})
    bar_A: str = "#2563eb"
    bar_B: str = "#7c3aed"
    bar_C: str = "#059669"
    bar_D: str = "#dc2626"
    # Semantic color tokens for enhanced theming
    accent_primary: str = "#2563eb"
    accent_secondary: str = "#7c3aed"
    success: str = "#059669"
    warning: str = "#d97706"
    error: str = "#dc2626"
    info: str = "#0891b2"
    # Comprehensive UI colors for every element
    ui_bg: str = "#ffffff"
    ui_fg: str = "#1f2937"
    ui_muted: str = "#6b7280"
    ui_border: str = "#d1d5db"
    ui_card_bg: str = "#f9fafb"
    ui_field_bg: str = "#ffffff"
    ui_hover_bg: str = "#f3f4f6"
    ui_active_bg: str = "#dbeafe"
    ui_disabled_bg: str = "#f3f4f6"
    ui_disabled_fg: str = "#9ca3af"
    ui_selection_bg: str = "#dbeafe"
    ui_selection_fg: str = "#1e40af"
    ui_tab_bg: str = "#f3f4f6"
    ui_tab_fg: str = "#6b7280"
    ui_tab_selected_bg: str = "#ffffff"
    ui_tab_selected_fg: str = "#1f2937"
    ui_tab_border: str = "#d1d5db"
    ui_button_bg: str = "#f3f4f6"
    ui_button_fg: str = "#1f2937"
    ui_button_border: str = "#d1d5db"
    ui_button_hover_bg: str = "#e5e7eb"
    ui_button_active_bg: str = "#dbeafe"
    ui_button_primary_bg: str = "#2563eb"
    ui_button_primary_fg: str = "#ffffff"
    ui_button_primary_border: str = "#2563eb"
    ui_button_primary_hover_bg: str = "#1d4ed8"
    ui_button_secondary_bg: str = "#7c3aed"
    ui_button_secondary_fg: str = "#ffffff"
    ui_button_secondary_border: str = "#7c3aed"
    ui_button_secondary_hover_bg: str = "#6d28d9"
    ui_button_success_bg: str = "#059669"
    ui_button_success_fg: str = "#ffffff"
    ui_button_success_border: str = "#059669"
    ui_button_success_hover_bg: str = "#047857"
    ui_button_warning_bg: str = "#d97706"
    ui_button_warning_fg: str = "#ffffff"
    ui_button_warning_border: str = "#d97706"
    ui_button_warning_hover_bg: str = "#b45309"
    ui_button_error_bg: str = "#dc2626"
    ui_button_error_fg: str = "#ffffff"
    ui_button_error_border: str = "#dc2626"
    ui_button_error_hover_bg: str = "#b91c1c"
    ui_entry_bg: str = "#ffffff"
    ui_entry_fg: str = "#1f2937"
    ui_entry_border: str = "#d1d5db"
    ui_entry_focus_border: str = "#2563eb"
    ui_spinbox_bg: str = "#ffffff"
    ui_spinbox_fg: str = "#1f2937"
    ui_spinbox_border: str = "#d1d5db"
    ui_spinbox_focus_border: str = "#2563eb"
    ui_scale_bg: str = "#f3f4f6"
    ui_scale_trough: str = "#e5e7eb"
    ui_scale_slider: str = "#2563eb"
    ui_checkbox_bg: str = "#ffffff"
    ui_checkbox_fg: str = "#1f2937"
    ui_checkbox_border: str = "#d1d5db"
    ui_checkbox_selected_bg: str = "#2563eb"
    ui_checkbox_selected_fg: str = "#ffffff"
    ui_radiobutton_bg: str = "#ffffff"
    ui_radiobutton_fg: str = "#1f2937"
    ui_radiobutton_border: str = "#d1d5db"
    ui_radiobutton_selected_bg: str = "#2563eb"
    ui_radiobutton_selected_fg: str = "#ffffff"
    ui_menubutton_bg: str = "#f3f4f6"
    ui_menubutton_fg: str = "#1f2937"
    ui_menubutton_border: str = "#d1d5db"
    ui_menubutton_hover_bg: str = "#e5e7eb"
    ui_optionmenu_bg: str = "#f3f4f6"
    ui_optionmenu_fg: str = "#1f2937"
    ui_optionmenu_border: str = "#d1d5db"
    ui_optionmenu_hover_bg: str = "#e5e7eb"
    ui_combobox_bg: str = "#ffffff"
    ui_combobox_fg: str = "#1f2937"
    ui_combobox_border: str = "#d1d5db"
    ui_combobox_focus_border: str = "#2563eb"
    ui_progressbar_bg: str = "#2563eb"
    ui_progressbar_trough: str = "#f3f4f6"
    ui_treeview_bg: str = "#ffffff"
    ui_treeview_fg: str = "#1f2937"
    ui_treeview_border: str = "#d1d5db"
    ui_treeview_heading_bg: str = "#f3f4f6"
    ui_treeview_heading_fg: str = "#1f2937"
    ui_treeview_heading_border: str = "#d1d5db"
    ui_separator_bg: str = "#d1d5db"
    ui_labelframe_bg: str = "#ffffff"
    ui_labelframe_fg: str = "#1f2937"
    ui_labelframe_border: str = "#d1d5db"
    ui_labelframe_label_bg: str = "#ffffff"
    ui_labelframe_label_fg: str = "#1f2937"
    ui_notebook_bg: str = "#ffffff"
    ui_notebook_border: str = "#d1d5db"
    ui_notebook_pane_bg: str = "#ffffff"
    ui_notebook_pane_border: str = "#d1d5db"
    theme_version: int = 3

    def to_json(self) -> dict:
        return {
            "preset": self.preset,
            "game_bg": self.game_bg,
            "game_fg": self.game_fg,
            "game_muted": self.game_muted,
            "hub_color": self.hub_color,
            "good_spoke": self.good_spoke,
            "bad_spoke": self.bad_spoke,
            "ac_colors": self.ac_colors,
            "ac_colorset": self.ac_colorset,
            "bar_A": self.bar_A,
            "bar_B": self.bar_B,
            "bar_C": self.bar_C,
            "bar_D": self.bar_D,
            "accent_primary": self.accent_primary,
            "accent_secondary": self.accent_secondary,
            "success": self.success,
            "warning": self.warning,
            "error": self.error,
            "info": self.info,
            "theme_version": self.theme_version,
            "ui_bg": self.ui_bg,
            "ui_fg": self.ui_fg,
            "ui_muted": self.ui_muted,
            "ui_border": self.ui_border,
            "ui_card_bg": self.ui_card_bg,
            "ui_field_bg": self.ui_field_bg,
            "ui_hover_bg": self.ui_hover_bg,
            "ui_active_bg": self.ui_active_bg,
            "ui_disabled_bg": self.ui_disabled_bg,
            "ui_disabled_fg": self.ui_disabled_fg,
            "ui_selection_bg": self.ui_selection_bg,
            "ui_selection_fg": self.ui_selection_fg,
            "ui_tab_bg": self.ui_tab_bg,
            "ui_tab_fg": self.ui_tab_fg,
            "ui_tab_selected_bg": self.ui_tab_selected_bg,
            "ui_tab_selected_fg": self.ui_tab_selected_fg,
            "ui_tab_border": self.ui_tab_border,
            "ui_button_bg": self.ui_button_bg,
            "ui_button_fg": self.ui_button_fg,
            "ui_button_border": self.ui_button_border,
            "ui_button_hover_bg": self.ui_button_hover_bg,
            "ui_button_active_bg": self.ui_button_active_bg,
            "ui_button_primary_bg": self.ui_button_primary_bg,
            "ui_button_primary_fg": self.ui_button_primary_fg,
            "ui_button_primary_border": self.ui_button_primary_border,
            "ui_button_primary_hover_bg": self.ui_button_primary_hover_bg,
            "ui_button_secondary_bg": self.ui_button_secondary_bg,
            "ui_button_secondary_fg": self.ui_button_secondary_fg,
            "ui_button_secondary_border": self.ui_button_secondary_border,
            "ui_button_secondary_hover_bg": self.ui_button_secondary_hover_bg,
            "ui_button_success_bg": self.ui_button_success_bg,
            "ui_button_success_fg": self.ui_button_success_fg,
            "ui_button_success_border": self.ui_button_success_border,
            "ui_button_success_hover_bg": self.ui_button_success_hover_bg,
            "ui_button_warning_bg": self.ui_button_warning_bg,
            "ui_button_warning_fg": self.ui_button_warning_fg,
            "ui_button_warning_border": self.ui_button_warning_border,
            "ui_button_warning_hover_bg": self.ui_button_warning_hover_bg,
            "ui_button_error_bg": self.ui_button_error_bg,
            "ui_button_error_fg": self.ui_button_error_fg,
            "ui_button_error_border": self.ui_button_error_border,
            "ui_button_error_hover_bg": self.ui_button_error_hover_bg,
            "ui_entry_bg": self.ui_entry_bg,
            "ui_entry_fg": self.ui_entry_fg,
            "ui_entry_border": self.ui_entry_border,
            "ui_entry_focus_border": self.ui_entry_focus_border,
            "ui_spinbox_bg": self.ui_spinbox_bg,
            "ui_spinbox_fg": self.ui_spinbox_fg,
            "ui_spinbox_border": self.ui_spinbox_border,
            "ui_spinbox_focus_border": self.ui_spinbox_focus_border,
            "ui_scale_bg": self.ui_scale_bg,
            "ui_scale_trough": self.ui_scale_trough,
            "ui_scale_slider": self.ui_scale_slider,
            "ui_checkbox_bg": self.ui_checkbox_bg,
            "ui_checkbox_fg": self.ui_checkbox_fg,
            "ui_checkbox_border": self.ui_checkbox_border,
            "ui_checkbox_selected_bg": self.ui_checkbox_selected_bg,
            "ui_checkbox_selected_fg": self.ui_checkbox_selected_fg,
            "ui_radiobutton_bg": self.ui_radiobutton_bg,
            "ui_radiobutton_fg": self.ui_radiobutton_fg,
            "ui_radiobutton_border": self.ui_radiobutton_border,
            "ui_radiobutton_selected_bg": self.ui_radiobutton_selected_bg,
            "ui_radiobutton_selected_fg": self.ui_radiobutton_selected_fg,
            "ui_menubutton_bg": self.ui_menubutton_bg,
            "ui_menubutton_fg": self.ui_menubutton_fg,
            "ui_menubutton_border": self.ui_menubutton_border,
            "ui_menubutton_hover_bg": self.ui_menubutton_hover_bg,
            "ui_optionmenu_bg": self.ui_optionmenu_bg,
            "ui_optionmenu_fg": self.ui_optionmenu_fg,
            "ui_optionmenu_border": self.ui_optionmenu_border,
            "ui_optionmenu_hover_bg": self.ui_optionmenu_hover_bg,
            "ui_combobox_bg": self.ui_combobox_bg,
            "ui_combobox_fg": self.ui_combobox_fg,
            "ui_combobox_border": self.ui_combobox_border,
            "ui_combobox_focus_border": self.ui_combobox_focus_border,
            "ui_progressbar_bg": self.ui_progressbar_bg,
            "ui_progressbar_trough": self.ui_progressbar_trough,
            "ui_treeview_bg": self.ui_treeview_bg,
            "ui_treeview_fg": self.ui_treeview_fg,
            "ui_treeview_border": self.ui_treeview_border,
            "ui_treeview_heading_bg": self.ui_treeview_heading_bg,
            "ui_treeview_heading_fg": self.ui_treeview_heading_fg,
            "ui_treeview_heading_border": self.ui_treeview_heading_border,
            "ui_separator_bg": self.ui_separator_bg,
            "ui_labelframe_bg": self.ui_labelframe_bg,
            "ui_labelframe_fg": self.ui_labelframe_fg,
            "ui_labelframe_border": self.ui_labelframe_border,
            "ui_labelframe_label_bg": self.ui_labelframe_label_bg,
            "ui_labelframe_label_fg": self.ui_labelframe_label_fg,
            "ui_notebook_bg": self.ui_notebook_bg,
            "ui_notebook_border": self.ui_notebook_border,
            "ui_notebook_pane_bg": self.ui_notebook_pane_bg,
            "ui_notebook_pane_border": self.ui_notebook_pane_border,
        }

    @staticmethod
    def from_json(d: dict) -> "ThemeConfig":
        t = ThemeConfig()
        t.preset = d.get("preset", t.preset)
        t.game_bg = d.get("game_bg", t.game_bg)
        t.game_fg = d.get("game_fg", t.game_fg)
        t.game_muted = d.get("game_muted", t.game_muted)
        t.hub_color = d.get("hub_color", t.hub_color)
        t.good_spoke = d.get("good_spoke", t.good_spoke)
        t.bad_spoke = d.get("bad_spoke", t.bad_spoke)
        t.ac_colors = d.get("ac_colors", t.ac_colors)
        t.ac_colorset = d.get("ac_colorset", t.ac_colorset)
        t.bar_A = d.get("bar_A", t.bar_A)
        t.bar_B = d.get("bar_B", t.bar_B)
        t.bar_C = d.get("bar_C", t.bar_C)
        t.bar_D = d.get("bar_D", t.bar_D)
        # Handle new semantic tokens with backward compatibility
        t.accent_primary = d.get("accent_primary", t.accent_primary)
        t.accent_secondary = d.get("accent_secondary", t.accent_secondary)
        t.success = d.get("success", t.success)
        t.warning = d.get("warning", t.warning)
        t.error = d.get("error", t.error)
        t.info = d.get("info", t.info)
        t.theme_version = int(d.get("theme_version", t.theme_version))
        t.ui_bg = d.get("ui_bg", t.ui_bg)
        t.ui_fg = d.get("ui_fg", t.ui_fg)
        t.ui_muted = d.get("ui_muted", t.ui_muted)
        t.ui_border = d.get("ui_border", t.ui_border)
        t.ui_card_bg = d.get("ui_card_bg", t.ui_card_bg)
        t.ui_field_bg = d.get("ui_field_bg", t.ui_field_bg)
        t.ui_hover_bg = d.get("ui_hover_bg", t.ui_hover_bg)
        t.ui_active_bg = d.get("ui_active_bg", t.ui_active_bg)
        t.ui_disabled_bg = d.get("ui_disabled_bg", t.ui_disabled_bg)
        t.ui_disabled_fg = d.get("ui_disabled_fg", t.ui_disabled_fg)
        t.ui_selection_bg = d.get("ui_selection_bg", t.ui_selection_bg)
        t.ui_selection_fg = d.get("ui_selection_fg", t.ui_selection_fg)
        t.ui_tab_bg = d.get("ui_tab_bg", t.ui_tab_bg)
        t.ui_tab_fg = d.get("ui_tab_fg", t.ui_tab_fg)
        t.ui_tab_selected_bg = d.get("ui_tab_selected_bg", t.ui_tab_selected_bg)
        t.ui_tab_selected_fg = d.get("ui_tab_selected_fg", t.ui_tab_selected_fg)
        t.ui_tab_border = d.get("ui_tab_border", t.ui_tab_border)
        t.ui_button_bg = d.get("ui_button_bg", t.ui_button_bg)
        t.ui_button_fg = d.get("ui_button_fg", t.ui_button_fg)
        t.ui_button_border = d.get("ui_button_border", t.ui_button_border)
        t.ui_button_hover_bg = d.get("ui_button_hover_bg", t.ui_button_hover_bg)
        t.ui_button_active_bg = d.get("ui_button_active_bg", t.ui_button_active_bg)
        t.ui_button_primary_bg = d.get("ui_button_primary_bg", t.ui_button_primary_bg)
        t.ui_button_primary_fg = d.get("ui_button_primary_fg", t.ui_button_primary_fg)
        t.ui_button_primary_border = d.get("ui_button_primary_border", t.ui_button_primary_border)
        t.ui_button_primary_hover_bg = d.get("ui_button_primary_hover_bg", t.ui_button_primary_hover_bg)
        t.ui_button_secondary_bg = d.get("ui_button_secondary_bg", t.ui_button_secondary_bg)
        t.ui_button_secondary_fg = d.get("ui_button_secondary_fg", t.ui_button_secondary_fg)
        t.ui_button_secondary_border = d.get("ui_button_secondary_border", t.ui_button_secondary_border)
        t.ui_button_secondary_hover_bg = d.get("ui_button_secondary_hover_bg", t.ui_button_secondary_hover_bg)
        t.ui_button_success_bg = d.get("ui_button_success_bg", t.ui_button_success_bg)
        t.ui_button_success_fg = d.get("ui_button_success_fg", t.ui_button_success_fg)
        t.ui_button_success_border = d.get("ui_button_success_border", t.ui_button_success_border)
        t.ui_button_success_hover_bg = d.get("ui_button_success_hover_bg", t.ui_button_success_hover_bg)
        t.ui_button_warning_bg = d.get("ui_button_warning_bg", t.ui_button_warning_bg)
        t.ui_button_warning_fg = d.get("ui_button_warning_fg", t.ui_button_warning_fg)
        t.ui_button_warning_border = d.get("ui_button_warning_border", t.ui_button_warning_border)
        t.ui_button_warning_hover_bg = d.get("ui_button_warning_hover_bg", t.ui_button_warning_hover_bg)
        t.ui_button_error_bg = d.get("ui_button_error_bg", t.ui_button_error_bg)
        t.ui_button_error_fg = d.get("ui_button_error_fg", t.ui_button_error_fg)
        t.ui_button_error_border = d.get("ui_button_error_border", t.ui_button_error_border)
        t.ui_button_error_hover_bg = d.get("ui_button_error_hover_bg", t.ui_button_error_hover_bg)
        t.ui_entry_bg = d.get("ui_entry_bg", t.ui_entry_bg)
        t.ui_entry_fg = d.get("ui_entry_fg", t.ui_entry_fg)
        t.ui_entry_border = d.get("ui_entry_border", t.ui_entry_border)
        t.ui_entry_focus_border = d.get("ui_entry_focus_border", t.ui_entry_focus_border)
        t.ui_spinbox_bg = d.get("ui_spinbox_bg", t.ui_spinbox_bg)
        t.ui_spinbox_fg = d.get("ui_spinbox_fg", t.ui_spinbox_fg)
        t.ui_spinbox_border = d.get("ui_spinbox_border", t.ui_spinbox_border)
        t.ui_spinbox_focus_border = d.get("ui_spinbox_focus_border", t.ui_spinbox_focus_border)
        t.ui_scale_bg = d.get("ui_scale_bg", t.ui_scale_bg)
        t.ui_scale_trough = d.get("ui_scale_trough", t.ui_scale_trough)
        t.ui_scale_slider = d.get("ui_scale_slider", t.ui_scale_slider)
        t.ui_checkbox_bg = d.get("ui_checkbox_bg", t.ui_checkbox_bg)
        t.ui_checkbox_fg = d.get("ui_checkbox_fg", t.ui_checkbox_fg)
        t.ui_checkbox_border = d.get("ui_checkbox_border", t.ui_checkbox_border)
        t.ui_checkbox_selected_bg = d.get("ui_checkbox_selected_bg", t.ui_checkbox_selected_bg)
        t.ui_checkbox_selected_fg = d.get("ui_checkbox_selected_fg", t.ui_checkbox_selected_fg)
        t.ui_radiobutton_bg = d.get("ui_radiobutton_bg", t.ui_radiobutton_bg)
        t.ui_radiobutton_fg = d.get("ui_radiobutton_fg", t.ui_radiobutton_fg)
        t.ui_radiobutton_border = d.get("ui_radiobutton_border", t.ui_radiobutton_border)
        t.ui_radiobutton_selected_bg = d.get("ui_radiobutton_selected_bg", t.ui_radiobutton_selected_bg)
        t.ui_radiobutton_selected_fg = d.get("ui_radiobutton_selected_fg", t.ui_radiobutton_selected_fg)
        t.ui_menubutton_bg = d.get("ui_menubutton_bg", t.ui_menubutton_bg)
        t.ui_menubutton_fg = d.get("ui_menubutton_fg", t.ui_menubutton_fg)
        t.ui_menubutton_border = d.get("ui_menubutton_border", t.ui_menubutton_border)
        t.ui_menubutton_hover_bg = d.get("ui_menubutton_hover_bg", t.ui_menubutton_hover_bg)
        t.ui_optionmenu_bg = d.get("ui_optionmenu_bg", t.ui_optionmenu_bg)
        t.ui_optionmenu_fg = d.get("ui_optionmenu_fg", t.ui_optionmenu_fg)
        t.ui_optionmenu_border = d.get("ui_optionmenu_border", t.ui_optionmenu_border)
        t.ui_optionmenu_hover_bg = d.get("ui_optionmenu_hover_bg", t.ui_optionmenu_hover_bg)
        t.ui_combobox_bg = d.get("ui_combobox_bg", t.ui_combobox_bg)
        t.ui_combobox_fg = d.get("ui_combobox_fg", t.ui_combobox_fg)
        t.ui_combobox_border = d.get("ui_combobox_border", t.ui_combobox_border)
        t.ui_combobox_focus_border = d.get("ui_combobox_focus_border", t.ui_combobox_focus_border)
        t.ui_progressbar_bg = d.get("ui_progressbar_bg", t.ui_progressbar_bg)
        t.ui_progressbar_trough = d.get("ui_progressbar_trough", t.ui_progressbar_trough)
        t.ui_treeview_bg = d.get("ui_treeview_bg", t.ui_treeview_bg)
        t.ui_treeview_fg = d.get("ui_treeview_fg", t.ui_treeview_fg)
        t.ui_treeview_border = d.get("ui_treeview_border", t.ui_treeview_border)
        t.ui_treeview_heading_bg = d.get("ui_treeview_heading_bg", t.ui_treeview_heading_bg)
        t.ui_treeview_heading_fg = d.get("ui_treeview_heading_fg", t.ui_treeview_heading_fg)
        t.ui_treeview_heading_border = d.get("ui_treeview_heading_border", t.ui_treeview_heading_border)
        t.ui_separator_bg = d.get("ui_separator_bg", t.ui_separator_bg)
        t.ui_labelframe_bg = d.get("ui_labelframe_bg", t.ui_labelframe_bg)
        t.ui_labelframe_fg = d.get("ui_labelframe_fg", t.ui_labelframe_fg)
        t.ui_labelframe_border = d.get("ui_labelframe_border", t.ui_labelframe_border)
        t.ui_labelframe_label_bg = d.get("ui_labelframe_label_bg", t.ui_labelframe_label_bg)
        t.ui_labelframe_label_fg = d.get("ui_labelframe_label_fg", t.ui_labelframe_label_fg)
        t.ui_notebook_bg = d.get("ui_notebook_bg", t.ui_notebook_bg)
        t.ui_notebook_border = d.get("ui_notebook_border", t.ui_notebook_border)
        t.ui_notebook_pane_bg = d.get("ui_notebook_pane_bg", t.ui_notebook_pane_bg)
        t.ui_notebook_pane_border = d.get("ui_notebook_pane_border", t.ui_notebook_pane_border)
        return t


@dataclass
class RecordingConfig:
    record_live_enabled: bool = False
    record_live_folder: str = ""
    record_live_format: str = "mp4"  # "mp4" | "png"
    record_async_writer: bool = True
    record_max_queue: int = 64
    record_skip_on_backpressure: bool = True
    record_use_full_resolution: bool = True
    record_apply_viz_overlays: str = "viz_settings"  # "viz_settings" | "minimal" | "custom"
    record_overlays_preset: str = "Broadcast"
    record_right_panel_view: str = "ops_total_sparkline"
    record_include_side_panels: bool = True
    record_resolution_mode: str = "display"  # "display" | "custom"
    record_custom_width: int = 1920
    record_custom_height: int = 1080
    last_fullscreen_size: Optional[Tuple[int,int]] = None
    offline_output_path: str = ""
    offline_fmt: str = "mp4"
    offline_fps: int = 30
    offline_progress_poll_ms: int = 400
    # legacy / common options
    fps: int = 30
    frames_per_period: int = 10
    include_hud: bool = True
    include_debug: bool = False
    include_panels: bool = True
    show_watermark: bool = True
    show_timestamp: bool = True
    show_frame_index: bool = False
    scale_percent: int = 100
    include_labels: bool = False

    def to_json(self) -> dict:
        return {
            "record_live_enabled": self.record_live_enabled,
            "record_live_folder": self.record_live_folder,
            "record_live_format": self.record_live_format,
            "record_async_writer": self.record_async_writer,
            "record_max_queue": self.record_max_queue,
            "record_skip_on_backpressure": self.record_skip_on_backpressure,
            "record_use_full_resolution": self.record_use_full_resolution,
            "record_apply_viz_overlays": self.record_apply_viz_overlays,
            "record_overlays_preset": self.record_overlays_preset,
            "record_right_panel_view": self.record_right_panel_view,
            "record_include_side_panels": self.record_include_side_panels,
            "include_panels": self.record_include_side_panels,
            "record_resolution_mode": self.record_resolution_mode,
            "record_custom_width": self.record_custom_width,
            "record_custom_height": self.record_custom_height,
            "last_fullscreen_size": self.last_fullscreen_size,
            "offline_output_path": self.offline_output_path,
            "offline_fmt": self.offline_fmt,
            "offline_fps": self.offline_fps,
            "offline_progress_poll_ms": self.offline_progress_poll_ms,
            "fps": self.fps,
            "frames_per_period": self.frames_per_period,
            "include_hud": self.include_hud,
            "include_debug": self.include_debug,
            "include_panels": self.include_panels,
            "show_watermark": self.show_watermark,
            "show_timestamp": self.show_timestamp,
            "show_frame_index": self.show_frame_index,
            "scale_percent": self.scale_percent,
            "include_labels": self.include_labels,
        }

    @staticmethod
    def from_json(d: dict) -> "RecordingConfig":
        r = RecordingConfig()
        r.record_live_enabled = bool(d.get("record_live_enabled", d.get("record_live", r.record_live_enabled)))
        r.record_live_format = d.get("record_live_format", d.get("record_format", r.record_live_format))
        live_dir = d.get("record_live_folder", d.get("live_out_dir", r.record_live_folder))
        r.record_live_folder = os.path.abspath(live_dir) if live_dir else ""
        off = d.get("offline_output_path", d.get("offline_out_file", r.offline_output_path))
        r.offline_output_path = os.path.abspath(off) if off else ""
        r.offline_fmt = d.get("offline_fmt", r.offline_fmt)
        r.offline_fps = int(d.get("offline_fps", r.fps))
        r.record_async_writer = bool(d.get("record_async_writer", r.record_async_writer))
        r.record_max_queue = int(d.get("record_max_queue", r.record_max_queue))
        r.record_skip_on_backpressure = bool(d.get("record_skip_on_backpressure", r.record_skip_on_backpressure))
        r.record_use_full_resolution = bool(d.get("record_use_full_resolution", r.record_use_full_resolution))
        r.record_apply_viz_overlays = d.get("record_apply_viz_overlays", r.record_apply_viz_overlays)
        r.record_overlays_preset = d.get("record_overlays_preset", r.record_overlays_preset)
        r.record_right_panel_view = d.get("record_right_panel_view", r.record_right_panel_view)
        r.record_include_side_panels = bool(d.get("record_include_side_panels", d.get("include_panels", r.record_include_side_panels)))
        r.include_panels = r.record_include_side_panels
        r.record_resolution_mode = d.get("record_resolution_mode", r.record_resolution_mode)
        r.record_custom_width = int(d.get("record_custom_width", r.record_custom_width))
        r.record_custom_height = int(d.get("record_custom_height", r.record_custom_height))
        size = d.get("last_fullscreen_size", r.last_fullscreen_size)
        r.last_fullscreen_size = tuple(size) if size else None
        r.offline_progress_poll_ms = int(d.get("offline_progress_poll_ms", r.offline_progress_poll_ms))
        r.fps = int(d.get("fps", r.fps))
        r.frames_per_period = int(d.get("frames_per_period", r.frames_per_period))
        r.include_hud = bool(d.get("include_hud", r.include_hud))
        r.include_debug = bool(d.get("include_debug", r.include_debug))
        r.show_watermark = bool(d.get("show_watermark", r.show_watermark))
        r.show_timestamp = bool(d.get("show_timestamp", r.show_timestamp))
        r.show_frame_index = bool(d.get("show_frame_index", r.show_frame_index))
        r.scale_percent = int(d.get("scale_percent", r.scale_percent))
        r.include_labels = bool(d.get("include_labels", r.include_labels))
        return r


@dataclass
class AdvancedDecisionConfig:
    adm_enable: bool = False
    adm_fairness_cooldown_periods: int = 2
    adm_target_dos_A_days: float = 3.0
    adm_target_dos_B_days: float = 2.0
    adm_enable_emergency_A_preempt: bool = True
    adm_seed: int = 12345

    def to_json(self) -> dict:
        return {
            "adm_enable": self.adm_enable,
            "adm_fairness_cooldown_periods": self.adm_fairness_cooldown_periods,
            "adm_target_dos_A_days": self.adm_target_dos_A_days,
            "adm_target_dos_B_days": self.adm_target_dos_B_days,
            "adm_enable_emergency_A_preempt": self.adm_enable_emergency_A_preempt,
            "adm_seed": self.adm_seed,
        }

    @staticmethod
    def from_json(d: dict) -> "AdvancedDecisionConfig":
        a = AdvancedDecisionConfig()
        a.adm_enable = bool(d.get("adm_enable", a.adm_enable))
        a.adm_fairness_cooldown_periods = int(d.get("adm_fairness_cooldown_periods", a.adm_fairness_cooldown_periods))
        a.adm_target_dos_A_days = float(d.get("adm_target_dos_A_days", a.adm_target_dos_A_days))
        a.adm_target_dos_B_days = float(d.get("adm_target_dos_B_days", a.adm_target_dos_B_days))
        a.adm_enable_emergency_A_preempt = bool(d.get("adm_enable_emergency_A_preempt", a.adm_enable_emergency_A_preempt))
        a.adm_seed = int(d.get("adm_seed", a.adm_seed))
        return a


@dataclass
class GameplayConfig:
    gp_realism_enable: bool = False
    gp_legtime_distance_model: bool = True
    gp_legtime_radius_min: float = 0.7
    gp_legtime_radius_max: float = 1.6
    gp_legtime_spread_seed: int = 777
    gp_fleetopt_enable: bool = False
    seed: int = 42  # Random seed for simulation
    gp_fleetopt_weights: Dict[str, float] = field(default_factory=lambda: {
        "wA": 2.0,
        "wB": 1.2,
        "wDOS": 1.0,
        "wOps": 1.5,
        "wDist": 0.6,
        "wCooldown": 0.8,
    })

    def to_json(self) -> dict:
        return {
            "gp_realism_enable": self.gp_realism_enable,
            "gp_legtime_distance_model": self.gp_legtime_distance_model,
            "gp_legtime_radius_min": self.gp_legtime_radius_min,
            "gp_legtime_radius_max": self.gp_legtime_radius_max,
            "gp_legtime_spread_seed": self.gp_legtime_spread_seed,
            "gp_fleetopt_enable": self.gp_fleetopt_enable,
            "seed": self.seed,
            "gp_fleetopt_weights": self.gp_fleetopt_weights,
        }

    @staticmethod
    def from_json(d: dict) -> "GameplayConfig":
        g = GameplayConfig()
        g.gp_realism_enable = bool(d.get("gp_realism_enable", g.gp_realism_enable))
        g.gp_legtime_distance_model = bool(d.get("gp_legtime_distance_model", g.gp_legtime_distance_model))
        g.gp_legtime_radius_min = float(d.get("gp_legtime_radius_min", g.gp_legtime_radius_min))
        g.gp_legtime_radius_max = float(d.get("gp_legtime_radius_max", g.gp_legtime_radius_max))
        g.gp_legtime_spread_seed = int(d.get("gp_legtime_spread_seed", g.gp_legtime_spread_seed))
        g.gp_fleetopt_enable = bool(d.get("gp_fleetopt_enable", g.gp_fleetopt_enable))
        g.seed = int(d.get("seed", g.seed))
        weights = d.get("gp_fleetopt_weights", g.gp_fleetopt_weights)
        for k, v in g.gp_fleetopt_weights.items():
            weights.setdefault(k, v)
        g.gp_fleetopt_weights = {k: float(weights.get(k, v)) for k, v in g.gp_fleetopt_weights.items()}
        return g


@dataclass
class BarScale:
    """Configuration for user-editable bar scale denominators."""
    denom_A: int = 2
    denom_B: int = 2
    denom_C: int = 2
    denom_D: int = 2
    
    def to_json(self) -> dict:
        return {
            "denom_A": self.denom_A,
            "denom_B": self.denom_B,
            "denom_C": self.denom_C,
            "denom_D": self.denom_D,
        }
    
    @staticmethod
    def from_json(d: dict) -> "BarScale":
        scale = BarScale()
        scale.denom_A = int(d.get("denom_A", scale.denom_A))
        scale.denom_B = int(d.get("denom_B", scale.denom_B))
        scale.denom_C = int(d.get("denom_C", scale.denom_C))
        scale.denom_D = int(d.get("denom_D", scale.denom_D))
        return scale


@dataclass
class SimConfig:
    config_version: int = CONFIG_VERSION
    fleet_label: str = "2xC130"       # "2xC130", "4xC130", "2xC130_2xC27"
    periods: int = 60                 # 30 days (AM/PM)
    init_A: int = 4
    init_B: int = 4
    init_C: int = 2
    init_D: int = 2
    a_days: int = A_PERIOD_DAYS_DFLT
    b_days: int = B_PERIOD_DAYS_DFLT
    c_days: int = C_PERIOD_DAYS_DFLT
    d_days: int = D_PERIOD_DAYS_DFLT
    cap_c130: int = 6
    cap_c27: int = 3
    rest_c130: int = 6
    rest_c27: int = 12
    pair_order: List[Tuple[int,int]] = field(default_factory=lambda: copy.deepcopy(PAIR_ORDER_DEFAULT))
    period_seconds: float = 1.0
    show_aircraft_labels: bool = False
    unlimited_storage: bool = True
    debug_mode: bool = False
    stats_mode: str = "total"         # "total" | "average"
    right_panel_view: str = "ops_total_number"  # "ops_total_number"|"ops_total_sparkline"|"per_spoke"
    orient_aircraft: bool = True
    show_dos_tooltips: bool = True
    hud_show_churn: bool = True
    cursor_color: str = "Cobalt"
    advanced_decision_making: bool = False
    advanced_decision_interval: int = 10
    viz_include_side_panels: bool = True
    viz_show_stats_overlay: bool = False
    viz_right_panel_mode: str = "ops_total_sparkline"
    fps: int = 60
    seed: int = 42
    theme: ThemeConfig = field(default_factory=ThemeConfig)
    recording: RecordingConfig = field(default_factory=RecordingConfig)
    adm: AdvancedDecisionConfig = field(default_factory=AdvancedDecisionConfig)
    gameplay: GameplayConfig = field(default_factory=GameplayConfig)
    launch_fullscreen: bool = True
    
    # Smart targeting system configuration
    smart_targeting_enabled: bool = True
    smart_targeting_config: Optional[Dict[str, any]] = None
    
    # Bar scale configuration for user-editable denominators
    bar_scale: BarScale = field(default_factory=BarScale)

    def to_json(self) -> dict:
        return {
            "config_version": self.config_version,
            "fleet_label": self.fleet_label,
            "periods": self.periods,
            "init": [self.init_A, self.init_B, self.init_C, self.init_D],
            "cadence": [self.a_days, self.b_days, self.c_days, self.d_days],
            "capacities": {"C130": self.cap_c130, "C27": self.cap_c27},
            "rest": {"C130": self.rest_c130, "C27": self.rest_c27},
            "pair_order": self.pair_order,
            "period_seconds": self.period_seconds,
            "show_aircraft_labels": self.show_aircraft_labels,
            "unlimited_storage": self.unlimited_storage,
            "debug_mode": self.debug_mode,
            "stats_mode": self.stats_mode,
            "right_panel_view": self.right_panel_view,
            "orient_aircraft": self.orient_aircraft,
            "show_dos_tooltips": self.show_dos_tooltips,
            "hud_show_churn": self.hud_show_churn,
            "cursor_color": self.cursor_color,
            "advanced_decision_making": self.advanced_decision_making,
            "advanced_decision_interval": self.advanced_decision_interval,
            "viz_include_side_panels": self.viz_include_side_panels,
            "viz_show_stats_overlay": self.viz_show_stats_overlay,
            "viz_right_panel_mode": self.viz_right_panel_mode,
            "fps": self.fps,
            "seed": self.seed,
            "launch_fullscreen": self.launch_fullscreen,
            "smart_targeting_enabled": self.smart_targeting_enabled,
            "smart_targeting_config": self.smart_targeting_config,
            "bar_scale": self.bar_scale.to_json(),
            "theme": self.theme.to_json(),
            "recording": self.recording.to_json(),
            "adm": self.adm.to_json(),
            "gameplay": self.gameplay.to_json(),
        }

    @staticmethod
    def from_json(d: dict) -> "SimConfig":
        cfg = SimConfig()
        cfg.config_version = int(d.get("config_version", cfg.config_version))
        cfg.fleet_label = d.get("fleet_label", cfg.fleet_label)
        cfg.periods = int(d.get("periods", cfg.periods))
        init = d.get("init", [cfg.init_A, cfg.init_B, cfg.init_C, cfg.init_D])
        cfg.init_A, cfg.init_B, cfg.init_C, cfg.init_D = [int(x) for x in init]
        cadence = d.get("cadence", [cfg.a_days, cfg.b_days, cfg.c_days, cfg.d_days])
        cfg.a_days, cfg.b_days, cfg.c_days, cfg.d_days = [int(x) for x in cadence]
        caps = d.get("capacities", {"C130": cfg.cap_c130, "C27": cfg.cap_c27})
        cfg.cap_c130 = int(caps.get("C130", cfg.cap_c130))
        cfg.cap_c27 = int(caps.get("C27", cfg.cap_c27))
        rest = d.get("rest", {"C130": cfg.rest_c130, "C27": cfg.rest_c27})
        cfg.rest_c130 = int(rest.get("C130", cfg.rest_c130))
        cfg.rest_c27 = int(rest.get("C27", cfg.rest_c27))
        cfg.pair_order = [tuple(x) for x in d.get("pair_order", cfg.pair_order)]
        cfg.period_seconds = float(d.get("period_seconds", cfg.period_seconds))
        cfg.show_aircraft_labels = bool(d.get("show_aircraft_labels", cfg.show_aircraft_labels))
        cfg.unlimited_storage = bool(d.get("unlimited_storage", cfg.unlimited_storage))
        cfg.debug_mode = bool(d.get("debug_mode", cfg.debug_mode))
        cfg.stats_mode = d.get("stats_mode", cfg.stats_mode)
        cfg.right_panel_view = d.get("right_panel_view", cfg.right_panel_view)
        cfg.orient_aircraft = bool(d.get("orient_aircraft", cfg.orient_aircraft))
        cfg.show_dos_tooltips = bool(d.get("show_dos_tooltips", cfg.show_dos_tooltips))
        cfg.hud_show_churn = bool(d.get("hud_show_churn", cfg.hud_show_churn))
        cfg.cursor_color = d.get("cursor_color", cfg.cursor_color)
        if cfg.cursor_color not in CURSOR_COLORS:
            cfg.cursor_color = "Cobalt"
        cfg.advanced_decision_making = bool(d.get("advanced_decision_making", cfg.advanced_decision_making))
        cfg.advanced_decision_interval = int(d.get("advanced_decision_interval", cfg.advanced_decision_interval))
        cfg.viz_include_side_panels = bool(d.get("viz_include_side_panels", cfg.viz_include_side_panels))
        cfg.viz_show_stats_overlay = bool(d.get("viz_show_stats_overlay", cfg.viz_show_stats_overlay))
        cfg.viz_right_panel_mode = d.get("viz_right_panel_mode", cfg.viz_right_panel_mode)
        cfg.fps = int(d.get("fps", cfg.fps))
        cfg.seed = int(d.get("seed", cfg.seed))
        cfg.smart_targeting_enabled = bool(d.get("smart_targeting_enabled", cfg.smart_targeting_enabled))
        cfg.smart_targeting_config = d.get("smart_targeting_config", cfg.smart_targeting_config)
        
        # Load bar scale configuration with backward compatibility
        if "bar_scale" in d:
            cfg.bar_scale = BarScale.from_json(d["bar_scale"])
        else:
            # Backward compatibility: use old VIS_CAPS_DFLT if available
            old_caps = d.get("vis_caps", DEFAULT_BAR_SCALE_DENOMINATORS)
            if isinstance(old_caps, list) and len(old_caps) == 4:
                cfg.bar_scale.denom_A = max(1, int(old_caps[0]))
                cfg.bar_scale.denom_B = max(1, int(old_caps[1]))
                cfg.bar_scale.denom_C = max(1, int(old_caps[2]))
                cfg.bar_scale.denom_D = max(1, int(old_caps[3]))
        
        cfg.theme = ThemeConfig.from_json(d.get("theme", {}))
        cfg.recording = RecordingConfig.from_json(d.get("recording", {}))
        cfg.adm = AdvancedDecisionConfig.from_json(d.get("adm", {}))
        cfg.gameplay = GameplayConfig.from_json(d.get("gameplay", {}))
        return cfg


def validate_config(cfg: SimConfig) -> List[str]:
    """Validate configuration and return list of warnings/errors."""
    issues = []
    
    # Basic validation
    if cfg.periods < 2:
        issues.append("Periods must be at least 2")
    
    if cfg.cap_c130 < 1 or cfg.cap_c27 < 1:
        issues.append("Aircraft capacities must be positive")
    
    if cfg.rest_c130 < 1 or cfg.rest_c27 < 1:
        issues.append("Rest periods must be positive")
    
    if cfg.a_days < 1 or cfg.b_days < 1 or cfg.c_days < 1 or cfg.d_days < 1:
        issues.append("Consumption cadences must be positive")
    
    if cfg.init_A < 0 or cfg.init_B < 0 or cfg.init_C < 0 or cfg.init_D < 0:
        issues.append("Initial stocks cannot be negative")
    
    if cfg.period_seconds <= 0:
        issues.append("Period duration must be positive")
    
    # Recording config validation
    if hasattr(cfg, 'recording') and hasattr(cfg.recording, 'fps'):
        if cfg.recording.fps < 1 or cfg.recording.fps > 300:
            issues.append("FPS must be between 1 and 300")
    
    # Gameplay config validation
    if hasattr(cfg, 'gameplay') and hasattr(cfg.gameplay, 'seed'):
        if cfg.gameplay.seed < 1:
            issues.append("Random seed must be positive")
    
    # Pair order validation
    if not isinstance(cfg.pair_order, list):
        issues.append("Pair order must be a list")
    else:
        for i, pair in enumerate(cfg.pair_order):
            if not isinstance(pair, tuple) or len(pair) != 2:
                issues.append(f"Pair {i} must be a tuple of length 2")
            elif not all(isinstance(x, int) and 0 <= x < M for x in pair):
                issues.append(f"Pair {i} indices must be integers between 0 and {M-1}")
    
    # Theme validation
    if cfg.cursor_color not in CURSOR_COLORS:
        issues.append(f"Invalid cursor color: {cfg.cursor_color}")
    
    if cfg.theme.preset not in THEME_PRESETS:
        issues.append(f"Invalid theme preset: {cfg.theme.preset}")
    
    if cfg.theme.ac_colorset and cfg.theme.ac_colorset not in AIRFRAME_COLORSETS:
        issues.append(f"Invalid airframe colorset: {cfg.theme.ac_colorset}")
    
    return issues


def load_config() -> SimConfig:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            cfg = SimConfig.from_json(data)
            if cfg.config_version < CONFIG_VERSION:
                cfg.config_version = CONFIG_VERSION
                save_config(cfg)
            if cfg.theme.preset not in THEME_PRESETS:
                apply_theme_preset(cfg.theme, "Classic Light")
                save_config(cfg)
            elif cfg.theme.theme_version < CURRENT_THEME_VERSION or cfg.theme.ac_colorset is None:
                apply_theme_preset(cfg.theme, cfg.theme.preset)
            else:
                if cfg.theme.ac_colorset in AIRFRAME_COLORSETS:
                    cfg.theme.ac_colors = AIRFRAME_COLORSETS[cfg.theme.ac_colorset]
                cfg.theme.theme_version = CURRENT_THEME_VERSION
            if cfg.cursor_color not in CURSOR_COLORS:
                cfg.cursor_color = "Cobalt"
                save_config(cfg)
            return cfg
        except Exception:
            pass
    cfg = SimConfig()
    apply_theme_preset(cfg.theme, cfg.theme.preset)
    return cfg


def save_config(cfg: SimConfig):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg.to_json(), f, indent=2)
    except Exception as e:
        # Note: This is a fallback warning since logging may not be available during config save
        # In a production environment, consider using proper logging here
        pass
