"""Tkinter GUI for CargoSim control panel."""

import os
import subprocess
import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Optional
import logging

from .config import (
    SimConfig, load_config, save_config, apply_theme_preset, 
    THEME_PRESETS, AIRFRAME_COLORSETS, CURSOR_COLORS
)
from .utils import _mp4_available, log_runtime_event, log_exception

# Set up logging
logger = logging.getLogger(__name__)

class _Tooltip:
    """Simple tooltip widget."""
    def __init__(self, widget, text: str, theme):
        self.widget = widget
        self.text = text
        self.theme = theme
        self.tip: Optional[tk.Toplevel] = None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)

    def show(self, _=None):
        if self.tip:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + 20
        self.tip = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tk.Label(tw, text=self.text, background=self.theme.game_bg,
                 foreground=self.theme.game_fg, relief="solid", borderwidth=1,
                 padx=4, pady=2).pack()

    def hide(self, _=None):
        if self.tip:
            self.tip.destroy()
            self.tip = None


class ControlGUI:
    """Main control panel GUI for CargoSim."""
    
    def __init__(self, root: tk.Tk, cfg: SimConfig, force_windowed: bool = False):
        try:
            log_runtime_event("Starting ControlGUI initialization", f"force_windowed={force_windowed}")
            
            self.root = root
            self.cfg = cfg
            self.force_windowed = force_windowed
            
            log_runtime_event("Setting up root window properties")
            root.title("CargoSim — Control Panel")
            root.geometry("860x760")
            root.minsize(760, 640)

            log_runtime_event("Setting up GUI styles")
            self._setup_style()

            log_runtime_event("Creating main notebook with tabs")
            # Create the main notebook with proper styling
            nb = ttk.Notebook(root, style="Tabs.TNotebook")
            nb.pack(fill="both", expand=True, padx=10, pady=10)
            
            # Configure the notebook to use the theme colors
            nb.configure(style="Tabs.TNotebook")
            
            # Create tab frames with proper styling
            self.tab_config = ttk.Frame(nb, padding=12, style="Card.TFrame")
            self.tab_schedule = ttk.Frame(nb, padding=12, style="Card.TFrame")
            self.tab_visual = ttk.Frame(nb, padding=12, style="Card.TFrame")
            self.tab_gameplay = ttk.Frame(nb, padding=12, style="Card.TFrame")
            self.tab_theme = ttk.Frame(nb, padding=12, style="Card.TFrame")
            self.tab_record = ttk.Frame(nb, padding=12, style="Card.TFrame")
            self.tab_start = ttk.Frame(nb, padding=12, style="Card.TFrame")

            # Add tabs with proper spacing
            nb.add(self.tab_config, text=" Configuration ")
            nb.add(self.tab_schedule, text=" Scheduling ")
            nb.add(self.tab_visual, text=" Visualization ")
            nb.add(self.tab_gameplay, text=" Gameplay ")
            nb.add(self.tab_theme, text=" Theme ")
            nb.add(self.tab_record, text=" Recording ")
            nb.add(self.tab_start, text=" Save / Start ")
            
            # Force the notebook to update its styling
            nb.update_idletasks()

            log_runtime_event("Building individual tab contents")
            self.build_config_tab(self.tab_config)
            self.build_schedule_tab(self.tab_schedule)
            self.build_visual_tab(self.tab_visual)
            self.build_theme_tab(self.tab_theme)
            self.build_gameplay_tab(self.tab_gameplay)
            self.build_record_tab(self.tab_record)
            self.build_start_tab(self.tab_start)

            log_runtime_event("Updating dependency state and applying theme")
            # After tabs are built, apply dependency gating
            self._update_dep_state()
            
            # Apply theme once after construction
            self._apply_theme_efficiently()
            
            log_runtime_event("Finalizing GUI setup")
            # Final update
            self.root.update_idletasks()
            self.root.update()
            
            log_runtime_event("ControlGUI initialization completed successfully")
            
        except Exception as e:
            log_exception(e, "ControlGUI initialization")
            raise

    def _setup_style(self):
        """Set up minimal Tkinter styles - comprehensive theming is handled by ui_theme.py."""
        # The comprehensive theming is now handled by ui_theme.py
        # This method only sets up basic structural styles that don't conflict
        
        # Mark that our theme system has been applied
        try:
            self.root._theme_system_applied = True
        except:
            pass
        
        # The comprehensive theming is now handled by ui_theme.py
        # This method only sets up basic structural styles that don't conflict
        
        # Mark that our theme system has been applied
        try:
            self.root._theme_system_applied = True
        except:
            pass
    
    def _apply_theme_efficiently(self):
        """Theme is now handled centrally by ui_theme.py - this is a no-op."""
        # The comprehensive theming is now handled by ui_theme.py
        # This method is kept for backward compatibility but does nothing
        pass

    def _add_page_note(self, parent, short, detail):
        """Add a page note with help text."""
        bar = ttk.Frame(parent, style="Card.TFrame")
        bar.grid(row=0, column=0, columnspan=4, sticky="we", pady=(0,8))
        ttk.Label(bar, text=short).pack(side="left", anchor="w")
        # Page notes are displayed inline - no popup needed

    def _add_tip(self, widget, text):
        """Add a tooltip to a widget."""
        _Tooltip(widget, text, self.cfg.theme)

    def _scale_with_entry(self, parent, label_text, from_, to_, var_type="int", init=0):
        """Create a scale with entry field combination."""
        frame = ttk.Frame(parent, style="Card.TFrame")
        frame.grid_columnconfigure(1, weight=1)

        ttk.Label(frame, text=label_text).grid(row=0, column=0, sticky="w")
        if var_type == "int":
            var = tk.IntVar(value=int(init))
            scale = ttk.Scale(frame, from_=from_, to=to_, orient="horizontal", variable=var, style="Green.Horizontal.TScale")
            entry = ttk.Entry(frame, width=8)
            entry.insert(0, str(int(init)))
            def on_scale(_):
                entry.delete(0, tk.END); entry.insert(0, str(int(var.get())))
            def on_entry(_=None):
                try: 
                    v = int(entry.get())
                except (ValueError, TypeError): 
                    v = int(init)
                v = max(int(from_), min(int(to_), v))
                var.set(v)
                entry.delete(0, tk.END); entry.insert(0, str(v))
            scale.bind("<B1-Motion>", on_scale); scale.bind("<ButtonRelease-1>", on_scale)
            entry.bind("<Return>", on_entry); entry.bind("<FocusOut>", on_entry)
        else:
            var = tk.DoubleVar(value=float(init))
            scale = ttk.Scale(frame, from_=from_, to=to_, orient="horizontal", variable=var, style="Green.Horizontal.TScale")
            entry = ttk.Entry(frame, width=8)
            entry.insert(0, f"{float(init):.2f}")
            def on_scale(_):
                entry.delete(0, tk.END); entry.insert(0, f"{float(var.get()):.2f}")
            def on_entry(_=None):
                try: 
                    v = float(entry.get())
                except (ValueError, TypeError): 
                    v = float(init)
                v = max(float(from_), min(float(to_), v))
                var.set(v)
                entry.delete(0, tk.END); entry.insert(0, f"{v:.2f}")
            scale.bind("<B1-Motion>", on_scale); scale.bind("<ButtonRelease-1>", on_scale)
            entry.bind("<Return>", on_entry); entry.bind("<FocusOut>", on_entry)

        scale.grid(row=0, column=1, sticky="we", padx=(8,6))
        entry.grid(row=0, column=2, sticky="w")
        return var, scale, entry, frame

    def _scale_with_entry_grid(self, parent, label_text, from_, to_, var_type="int", init=0, row=0):
        """Create a scale with entry field combination using grid layout."""
        # Configure the parent frame columns
        parent.grid_columnconfigure(1, weight=1)
        
        # Label
        ttk.Label(parent, text=label_text).grid(row=row, column=0, sticky="w", pady=(8, 0))
        
        if var_type == "int":
            var = tk.IntVar(value=int(init))
            scale = ttk.Scale(parent, from_=from_, to=to_, orient="horizontal", variable=var, style="Green.Horizontal.TScale")
            entry = ttk.Entry(parent, width=8)
            entry.insert(0, str(int(init)))
            
            def on_scale(_):
                entry.delete(0, tk.END)
                entry.insert(0, str(int(var.get())))
                
            def on_entry(_=None):
                try:
                    v = int(entry.get())
                except (ValueError, TypeError):
                    v = int(init)
                v = max(int(from_), min(int(to_), v))
                var.set(v)
                entry.delete(0, tk.END)
                entry.insert(0, str(v))
                
            scale.bind("<B1-Motion>", on_scale)
            scale.bind("<ButtonRelease-1>", on_scale)
            entry.bind("<Return>", on_entry)
            entry.bind("<FocusOut>", on_entry)
        else:
            var = tk.DoubleVar(value=float(init))
            scale = ttk.Scale(parent, from_=from_, to=to_, orient="horizontal", variable=var, style="Green.Horizontal.TScale")
            entry = ttk.Entry(parent, width=8)
            entry.insert(0, f"{float(init):.2f}")
            
            def on_scale(_):
                entry.delete(0, tk.END)
                entry.insert(0, f"{float(var.get()):.2f}")
                
            def on_entry(_=None):
                try:
                    v = float(entry.get())
                except (ValueError, TypeError):
                    v = float(init)
                v = max(float(from_), min(float(to_), v))
                var.set(v)
                entry.delete(0, tk.END)
                entry.insert(0, f"{v:.2f}")
                
            scale.bind("<B1-Motion>", on_scale)
            scale.bind("<ButtonRelease-1>", on_scale)
            entry.bind("<Return>", on_entry)
            entry.bind("<FocusOut>", on_entry)

        # Place scale and entry in grid
        scale.grid(row=row, column=1, sticky="ew", padx=(12, 6), pady=(8, 0))
        entry.grid(row=row, column=2, sticky="w", pady=(8, 0))
        
        return var, scale, entry, None  # Return None for frame since we're using grid

    def build_config_tab(self, tab):
        """Build the enhanced configuration tab with proper grid-based layout."""
        # Configure the main tab to use grid layout
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_columnconfigure(1, weight=1)
        tab.grid_rowconfigure(0, weight=1)
        
        # Left side - Fleet & Timing (Column 0)
        left_frame = ttk.Frame(tab, style="Card.TFrame")
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=(0, 8))
        left_frame.grid_columnconfigure(0, weight=1)
        
        # Fleet Configuration Section
        fleet_frame = ttk.LabelFrame(left_frame, text="Fleet Configuration", padding=12)
        fleet_frame.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        fleet_frame.grid_columnconfigure(1, weight=1)
        
        # Fleet selection row
        ttk.Label(fleet_frame, text="Fleet:", style="Header.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 8))
        self.fleet_var = tk.StringVar(value=self.cfg.fleet_label)
        fleet_menu = ttk.OptionMenu(fleet_frame, self.fleet_var, self.cfg.fleet_label, 
                                   "2xC130", "4xC130", "2xC130_2xC27")
        fleet_menu.grid(row=0, column=1, sticky="ew", padx=(12, 0))
        
        # Periods row
        ttk.Label(fleet_frame, text="Periods (AM/PM):", style="Header.TLabel").grid(row=1, column=0, sticky="w", pady=(8, 8))
        self.periods_var = tk.IntVar(value=self.cfg.periods)
        periods_spin = ttk.Spinbox(fleet_frame, from_=2, to=2000, textvariable=self.periods_var, width=12)
        periods_spin.grid(row=1, column=1, sticky="w", padx=(12, 0))
        
        # Capacity and rest settings with proper grid layout
        row = 2
        self.c130_cap_var, _, _, c130_cap_frame = self._scale_with_entry_grid(fleet_frame, "C-130 Capacity", 1, 20, "int", self.cfg.cap_c130, row)
        row += 1
        
        self.c27_cap_var, _, _, c27_cap_frame = self._scale_with_entry_grid(fleet_frame, "C-27 Capacity", 1, 20, "int", self.cfg.cap_c27, row)
        row += 1
        
        self.c130_rest_var, _, _, c130_rest_frame = self._scale_with_entry_grid(fleet_frame, "C-130 Rest After (periods)", 2, 30, "int", self.cfg.rest_c130, row)
        row += 1
        
        self.c27_rest_var, _, _, c27_rest_frame = self._scale_with_entry_grid(fleet_frame, "C-27 Rest After (periods)", 2, 36, "int", self.cfg.rest_c27, row)
        
        # Initial Stocks Section
        stocks_frame = ttk.LabelFrame(left_frame, text="Initial Stocks", padding=12)
        stocks_frame.grid(row=1, column=0, sticky="ew", pady=(0, 16))
        stocks_frame.grid_columnconfigure(1, weight=1)
        
        # Stock inputs in grid layout
        row = 0
        self.initA = tk.IntVar(value=self.cfg.init_A)
        ttk.Label(stocks_frame, text="Initial A (food):", style="Header.TLabel").grid(row=row, column=0, sticky="w", pady=(0, 8))
        ttk.Spinbox(stocks_frame, from_=0, to=100, textvariable=self.initA, width=12).grid(row=row, column=1, sticky="w", padx=(12, 0))
        row += 1
        
        self.initB = tk.IntVar(value=self.cfg.init_B)
        ttk.Label(stocks_frame, text="Initial B (fuel):", style="Header.TLabel").grid(row=row, column=0, sticky="w", pady=(0, 8))
        ttk.Spinbox(stocks_frame, from_=0, to=100, textvariable=self.initB, width=12).grid(row=row, column=1, sticky="w", padx=(12, 0))
        row += 1
        
        self.initC = tk.IntVar(value=self.cfg.init_C)
        ttk.Label(stocks_frame, text="Initial C (weapons):", style="Header.TLabel").grid(row=row, column=0, sticky="w", pady=(0, 8))
        ttk.Spinbox(stocks_frame, from_=0, to=100, textvariable=self.initC, width=12).grid(row=row, column=1, sticky="w", padx=(12, 0))
        row += 1
        
        self.initD = tk.IntVar(value=self.cfg.init_D)
        ttk.Label(stocks_frame, text="Initial D (spares):", style="Header.TLabel").grid(row=row, column=0, sticky="w", pady=(0, 8))
        ttk.Spinbox(stocks_frame, from_=0, to=100, textvariable=self.initD, width=12).grid(row=row, column=1, sticky="w", padx=(12, 0))
        row += 1
        
        # Unlimited storage checkbox
        self.unlimited_var = tk.BooleanVar(value=self.cfg.unlimited_storage)
        ttk.Checkbutton(stocks_frame, text="Unlimited Storage", variable=self.unlimited_var).grid(row=row, column=0, columnspan=2, sticky="w", pady=(8, 0))
        
        # Consumption Cadence Section
        cadence_frame = ttk.LabelFrame(left_frame, text="Consumption Cadence", padding=12)
        cadence_frame.grid(row=2, column=0, sticky="ew")
        cadence_frame.grid_columnconfigure(1, weight=1)
        
        # Cadence inputs in grid layout
        self.a_days = tk.IntVar(value=self.cfg.a_days)
        ttk.Label(cadence_frame, text="A cadence (days/unit):", style="Header.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 8))
        ttk.Spinbox(cadence_frame, from_=1, to=30, textvariable=self.a_days, width=12).grid(row=0, column=1, sticky="w", padx=(12, 0))
        
        self.b_days = tk.IntVar(value=self.cfg.b_days)
        ttk.Label(cadence_frame, text="B cadence (days/unit):", style="Header.TLabel").grid(row=1, column=0, sticky="w", pady=(0, 8))
        ttk.Spinbox(cadence_frame, from_=1, to=30, textvariable=self.b_days, width=12).grid(row=1, column=1, sticky="w", padx=(12, 0))
        
        # Add missing C and D cadence elements
        self.c_days = tk.IntVar(value=getattr(self.cfg, 'c_days', 2))  # Default to 2 if not in config
        ttk.Label(cadence_frame, text="C cadence (days/unit):", style="Header.TLabel").grid(row=2, column=0, sticky="w", pady=(0, 8))
        ttk.Spinbox(cadence_frame, from_=1, to=30, textvariable=self.c_days, width=12).grid(row=2, column=1, sticky="w", padx=(12, 0))
        
        self.d_days = tk.IntVar(value=getattr(self.cfg, 'd_days', 2))  # Default to 2 if not in config
        ttk.Label(cadence_frame, text="D cadence (days/unit):", style="Header.TLabel").grid(row=3, column=0, sticky="w", pady=(0, 8))
        ttk.Spinbox(cadence_frame, from_=1, to=30, textvariable=self.d_days, width=12).grid(row=3, column=1, sticky="w", padx=(12, 0))

        # Right side - Quick Reference (Column 1)
        right_frame = ttk.Frame(tab, style="Card.TFrame")
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=(0, 8))
        right_frame.grid_columnconfigure(0, weight=1)
        
        # Quick Reference Section
        ref_frame = ttk.LabelFrame(right_frame, text="Quick Reference", padding=12)
        ref_frame.grid(row=0, column=0, sticky="ew")
        ref_frame.grid_columnconfigure(0, weight=1)
        
        # Keyboard Shortcuts
        ttk.Label(ref_frame, text="Keyboard Shortcuts", style="Header.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 8))
        ttk.Separator(ref_frame, orient="horizontal").grid(row=1, column=0, sticky="ew", pady=(0, 8))
        
        shortcuts = [
            "ESC - Open pause menu",
            "G - Return to Control Panel", 
            "F11 - Toggle fullscreen",
            "D - Toggle debug mode (cycles through levels)",
            "F12 - Alternative debug toggle"
        ]
        
        for i, shortcut in enumerate(shortcuts):
            ttk.Label(ref_frame, text=f"• {shortcut}", style="Muted.TLabel").grid(row=i+2, column=0, sticky="w", pady=2)
        
        # Tips Section
        tips_frame = ttk.LabelFrame(right_frame, text="Tips", padding=12)
        tips_frame.grid(row=1, column=0, sticky="ew", pady=(16, 0))
        tips_frame.grid_columnconfigure(0, weight=1)
        
        tips = [
            "Debug Mode shows detailed actions and creates log files",
            "Press D to cycle through debug levels: OFF → BASIC → DETAILED",
            "Use F12 as an alternative debug toggle key",
            "Use the Theme tab to customize the interface appearance",
            "Recording settings can be configured in the Recording tab"
        ]
        
        for i, tip in enumerate(tips):
            ttk.Label(tips_frame, text=f"• {tip}", style="Muted.TLabel").grid(row=i, column=0, sticky="w", pady=2)

    def build_schedule_tab(self, tab):
        """Build the enhanced scheduling tab with improved styling."""
        g = ttk.Frame(tab, style="Card.TFrame")
        g.pack(fill="both", expand=True)

        # Pair order configuration
        pair_frame = ttk.LabelFrame(g, text="Pair Order Configuration", padding=12)
        pair_frame.pack(fill="x", pady=(0, 16))
        
        # Pair order input
        pair_row = ttk.Frame(pair_frame)
        pair_row.pack(fill="x", pady=(0, 8))
        ttk.Label(pair_row, text="Pair Order (zero-based spoke indices):", style="Header.TLabel").pack(side="left")
        self.pair_order_var = tk.StringVar(value=str(self.cfg.pair_order))
        pair_entry = ttk.Entry(pair_row, textvariable=self.pair_order_var, width=50)
        pair_entry.pack(side="left", padx=(12, 0), fill="x", expand=True)
        
        # Example text
        example_frame = ttk.Frame(pair_frame)
        example_frame.pack(fill="x")
        ttk.Label(example_frame, text="Example: [(0,1),(2,3),(4,5),(6,7),(8,9)]", 
                  style="Muted.TLabel", font=("TkDefaultFont", 8)).pack(anchor="w", padx=(0, 0))

        # Advanced decision making
        adv_frame = ttk.LabelFrame(g, text="Advanced Decision Making", padding=12)
        adv_frame.pack(fill="x", pady=(0, 16))
        
        # Enable advanced decision making
        adv_enable_row = ttk.Frame(adv_frame)
        adv_enable_row.pack(fill="x", pady=(0, 8))
        self.adv_decision_var = tk.BooleanVar(value=self.cfg.advanced_decision_making)
        ttk.Checkbutton(adv_enable_row, text="Enable advanced decision making", 
                       variable=self.adv_decision_var).pack(side="left")
        
        # Decision interval
        adv_interval_row = ttk.Frame(adv_frame)
        adv_interval_row.pack(fill="x", pady=(8, 0))
        ttk.Label(adv_interval_row, text="Decision interval (periods):", style="Header.TLabel").pack(side="left")
        self.adv_decision_interval_var = tk.IntVar(value=self.cfg.advanced_decision_interval)
        ttk.Spinbox(adv_interval_row, from_=1, to=100, textvariable=self.adv_decision_interval_var, width=12).pack(side="left", padx=(12, 0))

        # Statistics mode
        stats_frame = ttk.LabelFrame(g, text="Statistics Display", padding=12)
        stats_frame.pack(fill="x")
        
        stats_row = ttk.Frame(stats_frame)
        stats_row.pack(fill="x")
        ttk.Label(stats_row, text="Display mode:", style="Header.TLabel").pack(side="left")
        self.stats_mode_var = tk.StringVar(value=self.cfg.stats_mode)
        stats_menu = ttk.OptionMenu(stats_row, self.stats_mode_var, self.cfg.stats_mode, "total", "average")
        stats_menu.pack(side="left", padx=(12, 0), fill="x", expand=True)
        
        # Help text
        help_frame = ttk.Frame(g, style="Card.TFrame")
        help_frame.pack(fill="x", pady=(16, 0))
        
        ttk.Label(help_frame, text="Scheduling Help", style="Header.TLabel").pack(anchor="w", pady=(0, 8))
        ttk.Separator(help_frame).pack(fill="x", pady=(0, 8))
        
        help_text = [
            "• Pair Order: Define which spokes are serviced together",
            "• Advanced Decision Making: Enables periodic route optimization",
            "• Statistics Mode: Choose between total counts or averages"
        ]
        
        for help_line in help_text:
            ttk.Label(help_frame, text=help_line, style="Muted.TLabel").pack(anchor="w", pady=2)

    def build_visual_tab(self, tab):
        """Build the enhanced visualization tab with improved styling."""
        g = ttk.Frame(tab, style="Card.TFrame")
        g.pack(fill="both", expand=True)

        # Visual settings
        vis_frame = ttk.LabelFrame(g, text="Visual Settings", padding=12)
        vis_frame.pack(fill="x", pady=(0, 16))
        
        # Side panels setting
        side_panels_row = ttk.Frame(vis_frame)
        side_panels_row.pack(fill="x", pady=(0, 8))
        self.include_side_panels_var = tk.BooleanVar(value=getattr(self.cfg, "viz_include_side_panels", True))
        ttk.Checkbutton(side_panels_row, text="Include side panels in fullscreen", 
                       variable=self.include_side_panels_var).pack(side="left")
        
        # Stats overlay setting
        stats_overlay_row = ttk.Frame(vis_frame)
        stats_overlay_row.pack(fill="x", pady=(8, 0))
        self.show_stats_overlay_var = tk.BooleanVar(value=getattr(self.cfg, "viz_show_stats_overlay", False))
        ttk.Checkbutton(stats_overlay_row, text="Show statistics overlay", 
                       variable=self.show_stats_overlay_var).pack(side="left")
        
        # Aircraft orientation setting
        orient_row = ttk.Frame(vis_frame)
        orient_row.pack(fill="x", pady=(8, 0))
        self.orient_aircraft_var = tk.BooleanVar(value=self.cfg.orient_aircraft)
        ttk.Checkbutton(orient_row, text="Orient aircraft in flight direction", 
                       variable=self.orient_aircraft_var).pack(side="left")
        
        # Aircraft labels setting
        labels_row = ttk.Frame(vis_frame)
        labels_row.pack(fill="x", pady=(8, 0))
        self.show_aircraft_labels_var = tk.BooleanVar(value=self.cfg.show_aircraft_labels)
        ttk.Checkbutton(labels_row, text="Show aircraft labels", 
                       variable=self.show_aircraft_labels_var).pack(side="left")
        
        # Header visibility setting
        header_row = ttk.Frame(vis_frame)
        header_row.pack(fill="x", pady=(8, 0))
        self.show_header_var = tk.BooleanVar(value=getattr(self.cfg, "viz_show_header", True))
        ttk.Checkbutton(header_row, text="Show simulation header", 
                       variable=self.show_header_var).pack(side="left")

        # Right panel view
        panel_frame = ttk.LabelFrame(g, text="Right Panel View", padding=12)
        panel_frame.pack(fill="x", pady=(0, 16))
        
        panel_row = ttk.Frame(panel_frame)
        panel_row.pack(fill="x")
        ttk.Label(panel_row, text="Display mode:", style="Header.TLabel").pack(side="left")
        self.right_panel_view_var = tk.StringVar(value=getattr(self.cfg, "right_panel_view", "ops_total_sparkline"))
        panel_menu = ttk.OptionMenu(panel_row, self.right_panel_view_var, 
                                   self.right_panel_view_var.get(), 
                                   "ops_total_sparkline", "ops_total_number", "ops_by_spoke")
        panel_menu.pack(side="left", padx=(12, 0), fill="x", expand=True)

        # Cursor color
        cursor_frame = ttk.LabelFrame(g, text="Cursor Color", padding=12)
        cursor_frame.pack(fill="x")
        
        cursor_row = ttk.Frame(cursor_frame)
        cursor_row.pack(fill="x")
        ttk.Label(cursor_row, text="Color:", style="Header.TLabel").pack(side="left")
        self.cursor_color_var = tk.StringVar(value=self.cfg.cursor_color)
        cursor_menu = ttk.OptionMenu(cursor_row, self.cursor_color_var, self.cfg.cursor_color, 
                                    *list(CURSOR_COLORS.keys()))
        cursor_menu.pack(side="left", padx=(12, 0), fill="x", expand=True)
        
        # Help section
        help_frame = ttk.Frame(g, style="Card.TFrame")
        help_frame.pack(fill="x", pady=(16, 0))
        
        ttk.Label(help_frame, text="Visualization Help", style="Header.TLabel").pack(anchor="w", pady=(0, 8))
        ttk.Separator(help_frame).pack(fill="x", pady=(0, 8))
        
        help_text = [
            "• Side Panels: Show operational data during simulation",
            "• Statistics Overlay: Display real-time performance metrics",
            "• Aircraft Orientation: Rotate aircraft to show flight direction",
            "• Aircraft Labels: Show identification tags on aircraft",
            "• Header: Display simulation status and operational summary",
            "• Right Panel: Choose what operational data to display",
            "• Cursor Color: Select highlight color for better visibility"
        ]
        
        for help_line in help_text:
            ttk.Label(help_frame, text=help_line, style="Muted.TLabel").pack(anchor="w", pady=2)

    def build_theme_tab(self, tab):
        """Build the enhanced theme tab with auto-applying themes."""
        g = ttk.Frame(tab, style="Card.TFrame")
        g.pack(fill="both", expand=True)

        # Theme preset selection with descriptions
        theme_frame = ttk.LabelFrame(g, text="Theme Preset", padding=12)
        theme_frame.pack(fill="x", pady=(0, 16))
        
        # Theme selection row
        selection_row = ttk.Frame(theme_frame)
        selection_row.pack(fill="x", pady=(0, 8))
        
        ttk.Label(selection_row, text="Theme:", style="Header.TLabel").pack(side="left")
        self.theme_preset_var = tk.StringVar(value=self.cfg.theme.preset)
        theme_names = list(THEME_PRESETS.keys())
        
        theme_menu = ttk.OptionMenu(selection_row, self.theme_preset_var, self.cfg.theme.preset, *theme_names, 
                                   command=self._on_theme_change)
        theme_menu.pack(side="left", padx=(12, 0), fill="x", expand=True)
        
        # Theme description
        self.theme_description_label = ttk.Label(theme_frame, text="", style="Muted.TLabel", wraplength=400)
        self.theme_description_label.pack(fill="x", pady=(8, 0))
        
        # Update description for current theme
        self._update_theme_description()
        
        # Theme preview section
        preview_frame = ttk.LabelFrame(g, text="Theme Preview", padding=12)
        preview_frame.pack(fill="x", pady=(0, 16))
        
        # Color palette preview
        palette_frame = ttk.Frame(preview_frame)
        palette_frame.pack(fill="x", pady=(0, 8))
        
        ttk.Label(palette_frame, text="Color Palette:", style="Header.TLabel").pack(anchor="w")
        
        # Create color swatches
        swatch_frame = ttk.Frame(palette_frame)
        swatch_frame.pack(fill="x", pady=(8, 0))
        
        self.color_swatches = {}
        colors_to_show = [
            ("Primary", "accent_primary"),
            ("Secondary", "accent_secondary"), 
            ("Success", "success"),
            ("Warning", "warning"),
            ("Error", "error"),
            ("Info", "info")
        ]
        
        for i, (label, attr) in enumerate(colors_to_show):
            swatch_container = ttk.Frame(swatch_frame)
            swatch_container.pack(side="left", padx=(0, 16))
            
            ttk.Label(swatch_container, text=label, style="Muted.TLabel").pack()
            
            # Create color swatch (colored frame)
            swatch = tk.Frame(swatch_container, width=40, height=20, relief="solid", borderwidth=1)
            swatch.pack(pady=(4, 0))
            self.color_swatches[attr] = swatch
            
            # Color value label
            color_label = ttk.Label(swatch_container, text="", style="Muted.TLabel", font=("TkDefaultFont", 7))
            color_label.pack()
            self.color_swatches[f"{attr}_label"] = color_label
        
        # Airframe colorset selection
        colorset_frame = ttk.LabelFrame(g, text="Aircraft Color Scheme", padding=12)
        colorset_frame.pack(fill="x")
        
        colorset_row = ttk.Frame(colorset_frame)
        colorset_row.pack(fill="x")
        
        ttk.Label(colorset_row, text="Color scheme:", style="Header.TLabel").pack(side="left")
        self.airframe_colorset_var = tk.StringVar(value=self.cfg.theme.ac_colorset)
        colorset_names = list(AIRFRAME_COLORSETS.keys())
        
        colorset_menu = ttk.OptionMenu(colorset_row, self.airframe_colorset_var, 
                                      self.cfg.theme.ac_colorset, *colorset_names,
                                      command=self._on_colorset_change)
        colorset_menu.pack(side="left", padx=(12, 0), fill="x", expand=True)
        
        # Configure column weights
        for frame in [theme_frame, colorset_frame]:
            frame.columnconfigure(1, weight=1)
    
    def _on_theme_change(self, *args):
        """Handle theme selection change - auto-apply the selected theme."""
        try:
            # Get the selected theme name
            theme_name = self.theme_preset_var.get()
            
            # Apply the theme preset
            apply_theme_preset(self.cfg.theme, theme_name)
            
            # Reapply the centralized theme system
            from .ui_theme import apply_theme, create_palette_from_theme_config
            apply_theme(self.root, create_palette_from_theme_config(self.cfg.theme))
            
            # Update theme description and color swatches
            self._update_theme_description()
            self._update_color_swatches()
            
            # Final update
            self.root.update_idletasks()
            self.root.update()
            
        except Exception as e:
            logger.error(f"Error applying theme: {e}")
    
    def _on_colorset_change(self, *args):
        """Handle airframe colorset change."""
        colorset_name = self.airframe_colorset_var.get()
        if colorset_name in AIRFRAME_COLORSETS:
            self.cfg.theme.ac_colorset = colorset_name
            self.cfg.theme.ac_colors = AIRFRAME_COLORSETS[colorset_name]
    
    def _refresh_all_widgets(self):
        """Force refresh of all UI elements to apply new theme."""
        try:
            # Reapply the centralized theme system
            from .ui_theme import apply_theme, create_palette_from_theme_config
            apply_theme(self.root, create_palette_from_theme_config(self.cfg.theme))
            
            # Force a complete redraw
            self.root.update_idletasks()
            self.root.update()
            
        except Exception as e:
            logger.warning(f"Could not refresh all widgets: {e}")
    
    def _refresh_global_stylesheet(self):
        """Force complete refresh of the global stylesheet."""
        try:
            # Get the current style object
            style = ttk.Style()
            
            # Force theme reset and reapplication
            current_theme = style.theme_use()
            style.theme_use('default')  # Reset to default
            self.root.update_idletasks()  # Force update
            style.theme_use(current_theme)  # Reapply current theme
            self.root.update_idletasks()  # Force update again
            
            # Force complete root update
            self.root.update()
            
            # Theme is now handled centrally by ui_theme.py
            # No need to manually configure colors here
            
        except Exception as e:
            logger.warning(f"Could not refresh global stylesheet: {e}")
    
    # These methods are no longer needed - theming is handled centrally by ui_theme.py
    # Keeping them as no-ops for backward compatibility
    def _refresh_notebook_styling(self):
        """No-op - theming is handled centrally by ui_theme.py."""
        pass
    
    def _refresh_root_colors(self, bg, fg):
        """No-op - theming is handled centrally by ui_theme.py."""
        pass
    
    def _refresh_widget_tree(self, widget):
        """No-op - theming is handled centrally by ui_theme.py."""
        pass
    
    def _update_theme_description(self):
        """Update the theme description label."""
        theme_name = self.theme_preset_var.get()
        if theme_name in THEME_PRESETS:
            description = THEME_PRESETS[theme_name].get("description", "No description available.")
            self.theme_description_label.configure(text=description)
    
    def _update_color_swatches(self):
        """Update the color swatches to show current theme colors."""
        theme_name = self.theme_preset_var.get()
        if theme_name in THEME_PRESETS:
            theme = THEME_PRESETS[theme_name]
            for attr in ["accent_primary", "accent_secondary", "success", "warning", "error", "info"]:
                if attr in self.color_swatches and attr in theme:
                    color = theme[attr]
                    swatch = self.color_swatches[attr]
                    label = self.color_swatches.get(f"{attr}_label")
                    
                    # Update swatch color
                    swatch.configure(bg=color)
                    
                    # Update label with hex value
                    if label:
                        label.configure(text=color)

    def build_gameplay_tab(self, tab):
        """Build the enhanced gameplay tab with improved styling."""
        g = ttk.Frame(tab, style="Card.TFrame")
        g.pack(fill="both", expand=True)

        # Gameplay settings
        gameplay_frame = ttk.LabelFrame(g, text="Gameplay Settings", padding=12)
        gameplay_frame.pack(fill="x", pady=(0, 16))
        
        # Period duration
        period_row = ttk.Frame(gameplay_frame)
        period_row.pack(fill="x", pady=(0, 8))
        ttk.Label(period_row, text="Period duration (seconds):", style="Header.TLabel").pack(side="left")
        self.period_seconds_var = tk.DoubleVar(value=self.cfg.period_seconds)
        
        # Create a function to update the entry field when slider changes and ensure 0.1 increments
        def update_period_entry(*args):
            # Get current value and round to nearest 0.1
            current_value = self.period_seconds_var.get()
            rounded_value = round(current_value * 10) / 10  # Round to 1 decimal place
            # Only update if the value actually changed (prevents infinite loops)
            if abs(current_value - rounded_value) > 0.001:
                self.period_seconds_var.set(rounded_value)
        
        period_scale = ttk.Scale(period_row, from_=0.1, to=10.0, 
                                variable=self.period_seconds_var, orient="horizontal", 
                                style="Green.Horizontal.TScale",
                                command=update_period_entry)
        period_scale.pack(side="left", padx=(12, 8), fill="x", expand=True)
        period_entry = ttk.Entry(period_row, textvariable=self.period_seconds_var, width=8)
        period_entry.pack(side="left")
        
        # Target FPS
        fps_row = ttk.Frame(gameplay_frame)
        fps_row.pack(fill="x", pady=(8, 0))
        ttk.Label(fps_row, text="Target FPS:", style="Header.TLabel").pack(side="left")
        self.fps_var = tk.IntVar(value=self.cfg.fps)
        fps_spin = ttk.Spinbox(fps_row, from_=30, to=120, textvariable=self.fps_var, width=12)
        fps_spin.pack(side="left", padx=(12, 0))

        # Debug settings
        debug_frame = ttk.LabelFrame(g, text="Debug Settings", padding=12)
        debug_frame.pack(fill="x", pady=(0, 16))
        
        # Debug mode
        debug_enable_row = ttk.Frame(debug_frame)
        debug_enable_row.pack(fill="x", pady=(0, 8))
        self.debug_mode_var = tk.BooleanVar(value=self.cfg.debug_mode)
        ttk.Checkbutton(debug_enable_row, text="Enable debug mode", 
                       variable=self.debug_mode_var).pack(side="left")
        
        # Random seed
        seed_row = ttk.Frame(debug_frame)
        seed_row.pack(fill="x", pady=(8, 0))
        ttk.Label(seed_row, text="Random seed:", style="Header.TLabel").pack(side="left")
        self.seed_var = tk.IntVar(value=self.cfg.seed)
        seed_spin = ttk.Spinbox(seed_row, from_=1, to=999999, textvariable=self.seed_var, width=12)
        seed_spin.pack(side="left", padx=(12, 0))

        # Launch settings
        launch_frame = ttk.LabelFrame(g, text="Launch Settings", padding=12)
        launch_frame.pack(fill="x")
        
        launch_row = ttk.Frame(launch_frame)
        launch_row.pack(fill="x")
        self.launch_fullscreen_var = tk.BooleanVar(value=self.cfg.launch_fullscreen)
        ttk.Checkbutton(launch_row, text="Launch in fullscreen mode", 
                       variable=self.launch_fullscreen_var).pack(side="left")
        
        # Help section
        help_frame = ttk.Frame(g, style="Card.TFrame")
        help_frame.pack(fill="x", pady=(16, 0))
        
        ttk.Label(help_frame, text="Gameplay Help", style="Header.TLabel").pack(anchor="w", pady=(0, 8))
        ttk.Separator(help_frame).pack(fill="x", pady=(0, 8))
        
        help_text = [
            "• Period Duration: How long each AM/PM period lasts in real time",
            "• Target FPS: Frame rate for smooth animation (30-120 recommended)",
            "• Debug Mode: Shows detailed simulation actions and creates logs",
            "  - Press D to cycle through levels: OFF → BASIC → DETAILED",
            "  - Press F12 as alternative toggle key",
            "  - Basic level shows essential info, Detailed shows comprehensive data",
            "• Random Seed: Ensures reproducible simulation results",
            "• Fullscreen Launch: Start simulation in fullscreen mode"
        ]
        
        for help_line in help_text:
            ttk.Label(help_frame, text=help_line, style="Muted.TLabel").pack(anchor="w", pady=2)

    def build_record_tab(self, tab):
        """Build the enhanced recording tab with improved styling."""
        g = ttk.Frame(tab, style="Card.TFrame")
        g.pack(fill="both", expand=True)

        # Live recording
        live_frame = ttk.LabelFrame(g, text="Live Recording", padding=12)
        live_frame.pack(fill="x", pady=(0, 16))
        
        # Enable live recording
        live_enable_row = ttk.Frame(live_frame)
        live_enable_row.pack(fill="x", pady=(0, 8))
        self.record_live_enabled_var = tk.BooleanVar(value=self.cfg.recording.record_live_enabled)
        ttk.Checkbutton(live_enable_row, text="Enable live recording", 
                       variable=self.record_live_enabled_var).pack(side="left")
        
        # Live recording format
        live_format_row = ttk.Frame(live_frame)
        live_format_row.pack(fill="x", pady=(8, 0))
        ttk.Label(live_format_row, text="Format:", style="Header.TLabel").pack(side="left")
        self.record_live_format_var = tk.StringVar(value=self.cfg.recording.record_live_format)
        live_format_menu = ttk.OptionMenu(live_format_row, self.record_live_format_var, 
                                         self.cfg.recording.record_live_format, "mp4", "png")
        live_format_menu.pack(side="left", padx=(12, 0), fill="x", expand=True)
        
        # Live recording folder
        live_folder_row = ttk.Frame(live_frame)
        live_folder_row.pack(fill="x", pady=(8, 0))
        ttk.Label(live_folder_row, text="Output folder:", style="Header.TLabel").pack(side="left")
        folder_frame = ttk.Frame(live_folder_row)
        folder_frame.pack(side="left", padx=(12, 0), fill="x", expand=True)
        self.record_live_folder_var = tk.StringVar(value=self.cfg.recording.record_live_folder)
        ttk.Entry(folder_frame, textvariable=self.record_live_folder_var, width=35).pack(side="left", fill="x", expand=True)
        ttk.Button(folder_frame, text="Browse", command=lambda: self._browse_folder(self.record_live_folder_var), 
                  style="Secondary.TButton").pack(side="right", padx=(8, 0))

        # Offline recording
        offline_frame = ttk.LabelFrame(g, text="Offline Recording", padding=12)
        offline_frame.pack(fill="x", pady=(0, 16))
        
        # Offline format
        offline_format_row = ttk.Frame(offline_frame)
        offline_format_row.pack(fill="x", pady=(0, 8))
        ttk.Label(offline_format_row, text="Format:", style="Header.TLabel").pack(side="left")
        self.offline_fmt_var = tk.StringVar(value=self.cfg.recording.offline_fmt)
        offline_format_menu = ttk.OptionMenu(offline_format_row, self.offline_fmt_var, 
                                            self.cfg.recording.offline_fmt, "mp4", "png")
        offline_format_menu.pack(side="left", padx=(12, 0), fill="x", expand=True)
        
        # Offline FPS
        offline_fps_row = ttk.Frame(offline_frame)
        offline_fps_row.pack(fill="x", pady=(8, 0))
        ttk.Label(offline_fps_row, text="FPS:", style="Header.TLabel").pack(side="left")
        self.offline_fps_var = tk.IntVar(value=self.cfg.recording.offline_fps)
        offline_fps_spin = ttk.Spinbox(offline_fps_row, from_=1, to=60, textvariable=self.offline_fps_var, width=12)
        offline_fps_spin.pack(side="left", padx=(12, 0))
        
        # Offline output path
        offline_path_row = ttk.Frame(offline_frame)
        offline_path_row.pack(fill="x", pady=(8, 0))
        ttk.Label(offline_path_row, text="Output path:", style="Header.TLabel").pack(side="left")
        path_frame = ttk.Frame(offline_path_row)
        path_frame.pack(side="left", padx=(12, 0), fill="x", expand=True)
        self.offline_output_path_var = tk.StringVar(value=self.cfg.recording.offline_output_path)
        ttk.Entry(path_frame, textvariable=self.offline_output_path_var, width=35).pack(side="left", fill="x", expand=True)
        ttk.Button(path_frame, text="Browse", command=lambda: self._browse_file(self.offline_output_path_var), 
                  style="Secondary.TButton").pack(side="right", padx=(8, 0))

        # Recording options
        options_frame = ttk.LabelFrame(g, text="Recording Options", padding=12)
        options_frame.pack(fill="x")
        
        # Async writer
        async_row = ttk.Frame(options_frame)
        async_row.pack(fill="x", pady=(0, 8))
        self.record_async_writer_var = tk.BooleanVar(value=self.cfg.recording.record_async_writer)
        ttk.Checkbutton(async_row, text="Use async writer", 
                       variable=self.record_async_writer_var).pack(side="left")
        
        # Max queue size
        queue_row = ttk.Frame(options_frame)
        queue_row.pack(fill="x", pady=(8, 0))
        ttk.Label(queue_row, text="Max queue size:", style="Header.TLabel").pack(side="left")
        self.record_max_queue_var = tk.IntVar(value=self.cfg.recording.record_max_queue)
        queue_spin = ttk.Spinbox(queue_row, from_=16, to=256, textvariable=self.record_max_queue_var, width=12)
        queue_spin.pack(side="left", padx=(12, 0))
        
        # Help section
        help_frame = ttk.Frame(g, style="Card.TFrame")
        help_frame.pack(fill="x", pady=(16, 0))
        
        ttk.Label(help_frame, text="Recording Help", style="Header.TLabel").pack(anchor="w", pady=(0, 8))
        ttk.Separator(help_frame).pack(fill="x", pady=(0, 8))
        
        help_text = [
            "• Live Recording: Captures simulation in real-time",
            "• Offline Recording: Generates high-quality output files",
            "• MP4: Video format with compression (smaller files)",
            "• PNG: Image sequence (larger files, better quality)",
            "• Async Writer: Improves performance during recording",
            "• Queue Size: Memory buffer for smooth recording"
        ]
        
        for help_line in help_text:
            ttk.Label(help_frame, text=help_line, style="Muted.TLabel").pack(anchor="w", pady=2)

    def _browse_folder(self, var):
        """Browse for a folder and update the variable."""
        folder = filedialog.askdirectory(initialdir=var.get())
        if folder:
            var.set(folder)

    def _browse_file(self, var):
        """Browse for a file and update the variable."""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".mp4",
            filetypes=[("MP4 files", "*.mp4"), ("PNG files", "*.png"), ("All files", "*.*")]
        )
        if file_path:
            var.set(file_path)

    def build_start_tab(self, tab):
        """Build the enhanced start/save tab with improved styling."""
        frm = ttk.Frame(tab, style="Card.TFrame")
        frm.pack(fill="both", expand=True)

        # Status section
        status_frame = ttk.LabelFrame(frm, text="System Status", padding=12)
        status_frame.pack(fill="x", pady=(0, 16))
        
        self.dep_msg = ttk.Label(status_frame, text="", style="Muted.TLabel")
        self.dep_msg.pack(anchor="w", pady=(0, 8))

        # Action buttons
        btn_frame = ttk.LabelFrame(frm, text="Actions", padding=12)
        btn_frame.pack(fill="x", pady=(0, 16))
        
        btn_row = ttk.Frame(btn_frame)
        btn_row.pack(fill="x", pady=8)

        self.save_btn = ttk.Button(btn_row, text="Save Configuration", command=self.on_save, style="Secondary.TButton")
        self.save_btn.pack(side="left", padx=(0, 12))
        
        self.start_btn = ttk.Button(btn_row, text="Start Simulation", command=self.on_start, style="Primary.TButton")
        self.start_btn.pack(side="right")
        
        # Quick start info
        info_frame = ttk.LabelFrame(frm, text="Quick Start Guide", padding=12)
        info_frame.pack(fill="both", expand=True)
        
        ttk.Label(info_frame, text="Getting Started", style="Header.TLabel").pack(anchor="w", pady=(0, 8))
        ttk.Separator(info_frame).pack(fill="x", pady=(0, 8))
        
        steps = [
            "1. Configure your fleet and initial settings in the Configuration tab",
            "2. Set up scheduling preferences in the Scheduling tab", 
            "3. Customize the visual appearance in the Theme tab",
            "4. Adjust gameplay settings in the Gameplay tab",
            "5. Configure recording options if needed in the Recording tab",
            "6. Save your configuration and start the simulation!"
        ]
        
        for step in steps:
            ttk.Label(info_frame, text=step, style="Muted.TLabel").pack(anchor="w", pady=4)
        
        ttk.Separator(info_frame).pack(fill="x", pady=12)
        
        ttk.Label(info_frame, text="During Simulation", style="Header.TLabel").pack(anchor="w", pady=(0, 8))
        ttk.Label(info_frame, text="• Press ESC to pause and access the menu\n"
                                   "• Press G to return to this Control Panel\n"
                                   "• Use F11 to toggle fullscreen mode\n"
                                   "• Press D to cycle through debug levels (OFF→BASIC→DETAILED)\n"
                                   "• Press F12 as alternative debug toggle\n"
                                   "• Debug mode shows real-time simulation data and logs",
                  style="Muted.TLabel", justify="left").pack(anchor="w")

    def _update_dep_state(self):
        """Update dependency state and disable unavailable features."""
        msg = []
        
        # Check pygame availability without importing
        pygame_available = False
        try:
            import importlib.util
            pygame_spec = importlib.util.find_spec("pygame")
            pygame_available = pygame_spec is not None
        except Exception:
            pygame_available = False
        
        if not pygame_available:
            msg.append("pygame missing — simulation & offline render disabled")
            self.start_btn.state(["disabled"])
            if hasattr(self, "offline_btn"):
                self.offline_btn.state(["disabled"])
        
        if pygame_available:
            self.start_btn.state(["!disabled"])
            if hasattr(self, "offline_btn"):
                self.offline_btn.state(["!disabled"])
        
        mp4_ok, _ = _mp4_available()
        if not mp4_ok:
            msg.append("imageio-ffmpeg missing — MP4 disabled")
        
        self.dep_msg.configure(text=("; ".join(msg) if msg else "All dependencies available."))

    def on_save(self):
        """Save the current configuration."""
        if self._read_back_to_cfg():
            save_config(self.cfg)
            # Configuration saved successfully - no popup needed

    def on_start(self):
        """Start the simulation."""
        if not self._read_back_to_cfg():
            return
        
        # Check pygame availability without importing
        pygame_available = False
        try:
            import importlib.util
            pygame_spec = importlib.util.find_spec("pygame")
            pygame_available = pygame_spec is not None
        except Exception:
            pygame_available = False
            
        if not pygame_available:
            messagebox.showerror("Missing Dependency", "pygame is required to run the simulation.")
            return
            
        save_config(self.cfg)
        self.root.destroy()
        from .main import run_sim
        exit_code, live_out = run_sim(self.cfg, force_windowed=self.force_windowed)
        if live_out:
            tmp = tk.Tk(); tmp.withdraw()
            # Recording saved successfully - no popup needed
            tmp.destroy()
        if exit_code == "GUI":
            from .main import main
            main()

    def _read_back_to_cfg(self) -> bool:
        """Read values from GUI back to config object."""
        try:
            # Configuration tab
            self.cfg.fleet_label = self.fleet_var.get()
            self.cfg.periods = self.periods_var.get()
            self.cfg.cap_c130 = self.c130_cap_var.get()
            self.cfg.cap_c27 = self.c27_cap_var.get()
            self.cfg.rest_c130 = self.c130_rest_var.get()
            self.cfg.rest_c27 = self.c27_rest_var.get()
            
            self.cfg.init_A = self.initA.get()
            self.cfg.init_B = self.initB.get()
            self.cfg.init_C = self.initC.get()
            self.cfg.init_D = self.initD.get()
            self.cfg.unlimited_storage = self.unlimited_var.get()
            
            self.cfg.a_days = self.a_days.get()
            self.cfg.b_days = self.b_days.get()
            self.cfg.c_days = self.c_days.get()
            self.cfg.d_days = self.d_days.get()
            
            # Schedule tab
            try:
                import ast
                self.cfg.pair_order = ast.literal_eval(self.pair_order_var.get())
            except (ValueError, SyntaxError):
                messagebox.showerror("Invalid Input", "Pair order must be valid Python list format")
                return False
            
            self.cfg.advanced_decision_making = self.adv_decision_var.get()
            self.cfg.advanced_decision_interval = self.adv_decision_interval_var.get()
            self.cfg.stats_mode = self.stats_mode_var.get()
            
            # Visual tab
            setattr(self.cfg, "viz_include_side_panels", self.include_side_panels_var.get())
            setattr(self.cfg, "viz_show_stats_overlay", self.show_stats_overlay_var.get())
            self.cfg.orient_aircraft = self.orient_aircraft_var.get()
            self.cfg.show_aircraft_labels = self.show_aircraft_labels_var.get()
            setattr(self.cfg, "viz_show_header", self.show_header_var.get())
            setattr(self.cfg, "right_panel_view", self.right_panel_view_var.get())
            self.cfg.cursor_color = self.cursor_color_var.get()
            
            # Theme tab
            self.cfg.theme.preset = self.theme_preset_var.get()
            self.cfg.theme.ac_colorset = self.airframe_colorset_var.get()
            
            # Gameplay tab
            self.cfg.period_seconds = self.period_seconds_var.get()
            self.cfg.fps = self.fps_var.get()
            self.cfg.debug_mode = self.debug_mode_var.get()
            self.cfg.seed = self.seed_var.get()
            self.cfg.launch_fullscreen = self.launch_fullscreen_var.get()
            
            # Recording tab
            self.cfg.recording.record_live_enabled = self.record_live_enabled_var.get()
            self.cfg.recording.record_live_format = self.record_live_format_var.get()
            self.cfg.recording.record_live_folder = self.record_live_folder_var.get()
            self.cfg.recording.offline_fmt = self.offline_fmt_var.get()
            self.cfg.recording.offline_fps = self.offline_fps_var.get()
            self.cfg.recording.offline_output_path = self.offline_output_path_var.get()
            self.cfg.recording.record_async_writer = self.record_async_writer_var.get()
            self.cfg.recording.record_max_queue = self.record_max_queue_var.get()
            
            return True
            
        except Exception as e:
            messagebox.showerror("Configuration Error", f"Failed to read configuration: {e}")
            return False

    def _apply_specific_widget_theming(self):
        """No-op - theming is handled centrally by ui_theme.py."""
        pass

    def _apply_dropdown_styling(self):
        """No-op - theming is handled centrally by ui_theme.py."""
        pass

    def _setup_global_widget_options(self):
        """No-op - theming is handled centrally by ui_theme.py."""
        pass


if __name__ == "__main__":
    # This allows the file to be run directly for testing
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    from cargosim.config import load_config
    from cargosim.main import main
    
    # Load config and run main
    main()
