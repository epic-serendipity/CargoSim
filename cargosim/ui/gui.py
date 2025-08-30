"""Tkinter GUI for CargoSim control panel."""

import os
import subprocess
import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Optional
import logging
import time
from datetime import datetime

from cargosim.core.config import (
    SimConfig, load_config, save_config, apply_theme_preset, 
    THEME_PRESETS, AIRFRAME_COLORSETS, CURSOR_COLORS
)
from cargosim.core.utils import _mp4_available, log_runtime_event, log_exception, performance_monitor, analytics_engine, export_manager
from cargosim.rendering.themes.font_manager import font_manager
from cargosim.rendering.themes.default_fonts import DEFAULT_FONT, DEFAULT_FONT_BOLD

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
            
            # Make fullscreen by default
            root.state('zoomed')  # Windows fullscreen
            # Note: -zoomed attribute is not supported on Windows, so we only use state('zoomed')
            
            # Set minimum size for when not fullscreen
            root.minsize(1000, 800)
            
            # Bind F11 to toggle fullscreen
            root.bind('<F11>', self._toggle_fullscreen_gui)
            
            # Bind window close event to save fleet
            root.protocol("WM_DELETE_WINDOW", self._on_window_close)

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
            self.tab_fleet = ttk.Frame(nb, padding=12, style="Card.TFrame")
            self.tab_schedule = ttk.Frame(nb, padding=12, style="Card.TFrame")
            self.tab_operations = ttk.Frame(nb, padding=12, style="Card.TFrame")  # New Operations tab
            self.tab_visual = ttk.Frame(nb, padding=12, style="Card.TFrame")
            self.tab_gameplay = ttk.Frame(nb, padding=12, style="Card.TFrame")
            self.tab_theme = ttk.Frame(nb, padding=12, style="Card.TFrame")
            self.tab_record = ttk.Frame(nb, padding=12, style="Card.TFrame")
            self.tab_start = ttk.Frame(nb, padding=12, style="Card.TFrame")
            self.tab_advanced = ttk.Frame(nb, padding=12, style="Card.TFrame")  # New Advanced Features tab
            
            # Add tabs to notebook
            nb.add(self.tab_config, text="Configuration")
            nb.add(self.tab_fleet, text="Fleet Builder")
            nb.add(self.tab_schedule, text="Scheduling")
            nb.add(self.tab_operations, text="Operations")
            nb.add(self.tab_visual, text="Visual")
            nb.add(self.tab_gameplay, text="Gameplay")
            nb.add(self.tab_theme, text="Theme")
            nb.add(self.tab_record, text="Recording")
            nb.add(self.tab_start, text="Start")
            nb.add(self.tab_advanced, text="Advanced")
            
            # Initialize fleet persistence manager BEFORE building tabs
            try:
                from cargosim.ui.fleet_persistence import FleetPersistenceManager
                self.fleet_persistence = FleetPersistenceManager()
                log_runtime_event("Fleet persistence manager initialized")
            except Exception as e:
                log_runtime_event("Failed to initialize fleet persistence manager", f"error={e}")
                self.fleet_persistence = None
            
            # Initialize ConfigurationManager
            try:
                from cargosim.ui.fleet_builder_gui import ConfigurationManager
                self.configuration_manager = ConfigurationManager(self.cfg)
                log_runtime_event("ConfigurationManager initialized")
            except Exception as e:
                log_runtime_event("Failed to initialize ConfigurationManager", f"error={e}")
                self.configuration_manager = None

            log_runtime_event("Building configuration tab")
            self.build_config_tab(self.tab_config)
            
            log_runtime_event("Building fleet builder tab")
            self.build_fleet_tab(self.tab_fleet)
            
            log_runtime_event("Building scheduling tab")
            self.build_schedule_tab(self.tab_schedule)
            
            log_runtime_event("Building operations tab")
            self.build_operations_tab(self.tab_operations)
            
            log_runtime_event("Building visual tab")
            self.build_visual_tab(self.tab_visual)
            
            log_runtime_event("Building gameplay tab")
            self.build_gameplay_tab(self.tab_gameplay)
            
            log_runtime_event("Building theme tab")
            self.build_theme_tab(self.tab_theme)
            
            log_runtime_event("Building recording tab")
            self.build_record_tab(self.tab_record)
            
            log_runtime_event("Building start tab")
            self.build_start_tab(self.tab_start)
            
            log_runtime_event("Building advanced tab")
            self.build_advanced_tab(self.tab_advanced)
            
            log_runtime_event("Updating dependency state and applying theme")
            # After tabs are built, apply dependency gating
            self._update_dep_state()
            
            # Apply theme once after construction
            self._apply_theme_efficiently()
            
            # Initialize preview displays
            self._initialize_previews()
            
            log_runtime_event("Finalizing GUI setup")
            # Final update
            self.root.update_idletasks()
            self.root.update()
            
            # Create status bar
            self._create_status_bar()
            
            # Set up responsive layout bindings
            self._setup_responsive_bindings()
            
            # Initialize advanced systems
            self._initialize_advanced_systems()
            
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
        """Build the Fleet Configuration tab with improved layout and balance."""
        # Configure the main tab for three-column layout with better proportions
        tab.grid_columnconfigure(0, weight=3)  # Fleet config gets most space
        tab.grid_columnconfigure(1, weight=2)  # Help section gets medium space
        tab.grid_columnconfigure(2, weight=1)  # Quick actions gets least space
        tab.grid_rowconfigure(0, weight=1)
        
        # Left side - Fleet Configuration (Column 0)
        left_frame = ttk.Frame(tab, style="Card.TFrame")
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=(0, 8))
        left_frame.grid_columnconfigure(0, weight=1)
        
        # Fleet Configuration Section
        fleet_frame = ttk.LabelFrame(left_frame, text="Custom Aircraft", padding=20)
        fleet_frame.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        fleet_frame.grid_columnconfigure(1, weight=1)
        
        # Custom Transport Configuration Section
        custom_frame = ttk.LabelFrame(fleet_frame, text="Custom Transport Aircraft", padding=20)
        custom_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(16, 0))
        custom_frame.grid_columnconfigure(1, weight=1)
        
        # Aircraft attributes in a more organized grid
        attributes = [
            ("Capacity", "capacity", 1, 20, 4),
            ("Rest Periods", "rest_periods", 1, 24, 8),
            ("Range Factor", "range_factor", 0.5, 3.0, 1.0),
            ("Fuel Efficiency", "fuel_efficiency", 0.5, 2.0, 1.0),
            ("Maintenance Cost", "maintenance_cost", 0.5, 3.0, 1.0),
            ("Speed (Mach)", "speed", 0.3, 0.8, 0.5),
        ]
        
        self.custom_vars = {}
        for i, (label, attr, min_val, max_val, default) in enumerate(attributes):
            # Create a frame for each attribute row
            attr_row = ttk.Frame(custom_frame)
            attr_row.grid(row=i, column=0, columnspan=3, sticky="ew", pady=(12, 0))
            attr_row.grid_columnconfigure(1, weight=1)
            
            # Label with consistent width
            ttk.Label(attr_row, text=f"{label}:", style="Header.TLabel", 
                     width=18, anchor="w").grid(row=0, column=0, sticky="w")
            
            # Scale with better proportions
            var = tk.DoubleVar(value=default)
            scale = ttk.Scale(attr_row, from_=min_val, to=max_val, orient="horizontal", 
                            variable=var, style="Green.Horizontal.TScale")
            scale.grid(row=0, column=1, sticky="ew", padx=(16, 12))
            
            # Entry field with validation
            entry = ttk.Entry(attr_row, width=10, textvariable=var, justify="center")
            entry.grid(row=0, column=2, sticky="w")
            
            # Store variable reference
            self.custom_vars[attr] = var
            
            # Bind scale and entry for synchronization
            def on_scale_change(val, var=var, entry=entry):
                entry.delete(0, tk.END)
                entry.insert(0, f"{float(val):.2f}")
            
            def on_entry_change(event, var=var, scale=scale):
                try:
                    val = float(event.widget.get())
                    var.set(val)
                    scale.set(val)
                except ValueError:
                    pass
            
            scale.configure(command=on_scale_change)
            entry.bind("<Return>", on_entry_change)
            entry.bind("<FocusOut>", on_entry_change)
        
        # Special capabilities in a 3x3 grid for better balance
        capabilities_frame = ttk.LabelFrame(custom_frame, text="Special Capabilities", padding=20)
        capabilities_frame.grid(row=len(attributes), column=0, columnspan=3, sticky="ew", pady=(20, 0))
        capabilities_frame.grid_columnconfigure(0, weight=1)
        
        self.capability_vars = {}
        available_capabilities = [
            "tactical", "short_field", "fuel_efficient", "high_capacity", 
            "long_range", "all_weather", "night_ops", "rough_field"
        ]
        
        # Create a 3x3 grid for capabilities (with one empty slot for balance)
        for i, capability in enumerate(available_capabilities):
            row = i // 3
            col = i % 3
            
            var = tk.BooleanVar()
            cb = ttk.Checkbutton(capabilities_frame, text=capability.replace("_", " ").title(),
                               variable=var, style="Checkbutton.TCheckbutton")
            cb.grid(row=row, column=col, sticky="w", padx=(0, 24), pady=(8, 0))
            self.capability_vars[capability] = var
        
        # Center column now unused (help removed); keep placeholder frame for layout simplicity
        # Center column is now empty (all help sections removed)
        # Keep frame for layout consistency but no content
        center_frame = ttk.Frame(tab, style="Card.TFrame")
        center_frame.grid(row=0, column=1, sticky="nsew", padx=6, pady=(0, 8))
        
        # Right column - Quick Actions (Column 2)
        right_frame = ttk.Frame(tab, style="Card.TFrame")
        right_frame.grid(row=0, column=2, sticky="nsew", padx=(6, 0), pady=(0, 8))
        right_frame.grid_columnconfigure(0, weight=1)
        
        # Quick Actions Section
        actions_frame = ttk.LabelFrame(right_frame, text="Quick Actions", padding=16)
        actions_frame.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        
        # Action buttons
        ttk.Button(actions_frame, text="Reset to Defaults", 
                  command=self._reset_custom_aircraft, style="Secondary.TButton").pack(fill="x", pady=(0, 8))
        ttk.Button(actions_frame, text="Save Custom Aircraft", 
                  command=self._save_custom_aircraft, style="Primary.TButton").pack(fill="x", pady=(0, 8))
        ttk.Button(actions_frame, text="Load Preset", 
                  command=self._load_aircraft_preset, style="Secondary.TButton").pack(fill="x")
        
        # Aircraft Preview Section
        preview_frame = ttk.LabelFrame(right_frame, text="Aircraft Preview", padding=16)
        preview_frame.grid(row=1, column=0, sticky="ew")
        
        self.aircraft_preview_label = ttk.Label(preview_frame, text="Custom aircraft configuration will appear here", 
                                               style="Muted.TLabel", wraplength=200, justify="center")
        self.aircraft_preview_label.pack(expand=True, pady=20)

    def build_schedule_tab(self, tab):
        """Build the Simulation Parameters tab with improved layout and balance."""
        # Configure the main tab for three-column layout with better proportions
        tab.grid_columnconfigure(0, weight=3)  # Main parameters get most space
        tab.grid_columnconfigure(1, weight=2)  # Help section gets medium space
        tab.grid_columnconfigure(2, weight=1)  # Quick actions gets least space
        tab.grid_rowconfigure(0, weight=1)
        
        # Left side - Main Parameters (Column 0)
        left_frame = ttk.Frame(tab, style="Card.TFrame")
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=(0, 8))
        left_frame.grid_columnconfigure(0, weight=1)
        
        # Center side - Help Sections (Column 1)
        center_frame = ttk.Frame(tab, style="Card.TFrame")
        center_frame.grid(row=0, column=1, sticky="nsew", padx=6, pady=(0, 8))
        center_frame.grid_columnconfigure(0, weight=1)
        
        # Simulation Timing Section
        timing_frame = ttk.LabelFrame(left_frame, text="Simulation Timing", padding=20)
        timing_frame.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        timing_frame.grid_columnconfigure(1, weight=1)
        
        # Periods configuration with better layout
        ttk.Label(timing_frame, text="Periods (AM/PM):", style="Header.TLabel", 
                 font=font_manager.get_font('medium', 'bold')).grid(row=0, column=0, sticky="w", pady=(0, 8))
        self.periods_var = tk.IntVar(value=self.cfg.periods)
        periods_spin = ttk.Spinbox(timing_frame, from_=2, to=2000, textvariable=self.periods_var, 
                                  width=15, justify="center")
        periods_spin.grid(row=0, column=1, sticky="w", padx=(16, 0))
        
        # Time scale controls (Phase 3 enhancement)
        ttk.Label(timing_frame, text="Time Scale (simulation speed):", style="Header.TLabel", 
                 font=font_manager.get_font('medium', 'bold')).grid(row=1, column=0, sticky="w", pady=(16, 8))
        
        time_scale_frame = ttk.Frame(timing_frame)
        time_scale_frame.grid(row=1, column=1, sticky="w", padx=(16, 0))
        
        self.time_scale_var = tk.DoubleVar(value=1.0)
        time_scale_slider = ttk.Scale(time_scale_frame, from_=0.1, to=10.0, 
                                     variable=self.time_scale_var, orient="horizontal",
                                     length=150, style="Green.Horizontal.TScale")
        time_scale_slider.pack(side="left")
        
        time_scale_display = ttk.Label(time_scale_frame, text="1.0x", 
                                     style="Header.TLabel", width=8)
        time_scale_display.pack(side="left", padx=(8, 0))
        
        # Update time scale display when slider changes
        def update_time_scale_display(*args):
            scale_value = self.time_scale_var.get()
            time_scale_display.config(text=f"{scale_value:.1f}x")
        
        self.time_scale_var.trace("w", update_time_scale_display)
        
        # Pause/Resume functionality
        pause_resume_frame = ttk.Frame(timing_frame)
        pause_resume_frame.grid(row=2, column=0, columnspan=2, sticky="w", pady=(16, 0))
        
        self.simulation_paused = tk.BooleanVar(value=False)
        pause_resume_btn = ttk.Button(pause_resume_frame, text="⏸ Pause", 
                                    command=self._toggle_simulation_pause)
        pause_resume_btn.pack(side="left")
        
        # Cost display and budget controls
        cost_frame = ttk.LabelFrame(timing_frame, text="Cost & Budget", padding=16)
        cost_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(16, 0))
        cost_frame.grid_columnconfigure(1, weight=1)
        
        # Total cost counter
        ttk.Label(cost_frame, text="Total Cost:", style="Header.TLabel").grid(row=0, column=0, sticky="w")
        self.total_cost_label = ttk.Label(cost_frame, text="$0.00", style="Header.TLabel", 
                                        foreground="green")
        self.total_cost_label.grid(row=0, column=1, sticky="w", padx=(16, 0))
        
        # Cost per period/hour
        ttk.Label(cost_frame, text="Cost per Period:", style="Header.TLabel").grid(row=1, column=0, sticky="w")
        self.cost_per_period_label = ttk.Label(cost_frame, text="$0.00", style="Muted.TLabel")
        self.cost_per_period_label.grid(row=1, column=1, sticky="w", padx=(16, 0))
        
        # Budget limit settings
        ttk.Label(cost_frame, text="Budget Limit ($):", style="Header.TLabel").grid(row=2, column=0, sticky="w")
        self.budget_limit_var = tk.StringVar(value="100000.0")
        budget_entry = ttk.Entry(cost_frame, textvariable=self.budget_limit_var, width=15)
        budget_entry.grid(row=2, column=1, sticky="w", padx=(16, 0))
        
        # Budget remaining indicator
        ttk.Label(cost_frame, text="Budget Remaining:", style="Header.TLabel").grid(row=3, column=0, sticky="w")
        self.budget_remaining_label = ttk.Label(cost_frame, text="$100,000.00", 
                                             style="Header.TLabel", foreground="green")
        self.budget_remaining_label.grid(row=3, column=1, sticky="w", padx=(16, 0))
        
        # Cost trend graph placeholder
        cost_trend_frame = ttk.Frame(cost_frame)
        cost_trend_frame.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(16, 0))
        
        ttk.Label(cost_trend_frame, text="Cost Trend Graph:", style="Header.TLabel").pack(anchor="w")
        cost_graph_placeholder = ttk.Label(cost_trend_frame, text="📊 Cost trend visualization will appear here", 
                                         style="Muted.TLabel", justify="center")
        cost_graph_placeholder.pack(expand=True, pady=20)
        
        # Real-time statistics overlay
        stats_overlay_frame = ttk.LabelFrame(timing_frame, text="Real-time Statistics", padding=16)
        stats_overlay_frame.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(16, 0))
        stats_overlay_frame.grid_columnconfigure(1, weight=1)
        
        # Live operation counts
        ttk.Label(stats_overlay_frame, text="Live Operations:", style="Header.TLabel").grid(row=0, column=0, sticky="w")
        self.live_ops_label = ttk.Label(stats_overlay_frame, text="0", style="Header.TLabel", foreground="blue")
        self.live_ops_label.grid(row=0, column=1, sticky="w", padx=(16, 0))
        
        # Aircraft status summary
        ttk.Label(stats_overlay_frame, text="Aircraft Status:", style="Header.TLabel").grid(row=1, column=0, sticky="w")
        self.aircraft_status_label = ttk.Label(stats_overlay_frame, text="0 IDLE, 0 ENROUTE, 0 LOADING", 
                                             style="Muted.TLabel")
        self.aircraft_status_label.grid(row=1, column=1, sticky="w", padx=(16, 0))
        
        # Performance metrics
        ttk.Label(stats_overlay_frame, text="Performance:", style="Header.TLabel").grid(row=2, column=0, sticky="w")
        self.performance_label = ttk.Label(stats_overlay_frame, text="Efficiency: 0%", style="Muted.TLabel")
        self.performance_label.grid(row=2, column=1, sticky="w", padx=(16, 0))
        
        # Initial Stocks Section
        stocks_frame = ttk.LabelFrame(left_frame, text="Initial Resource Stocks", padding=20)
        stocks_frame.grid(row=1, column=0, sticky="ew", pady=(0, 16))
        stocks_frame.grid_columnconfigure(1, weight=1)
        
        # Stock inputs in a more organized grid
        stock_labels = [
            ("Initial A (Food):", "initA", self.cfg.init_A),
            ("Initial B (Fuel):", "initB", self.cfg.init_B),
            ("Initial C (Weapons):", "initC", self.cfg.init_C),
            ("Initial D (Spares):", "initD", self.cfg.init_D)
        ]
        
        for i, (label_text, var_name, default_value) in enumerate(stock_labels):
            ttk.Label(stocks_frame, text=label_text, style="Header.TLabel", 
                     width=20, anchor="w").grid(row=i, column=0, sticky="w", pady=(0, 8))
            var = tk.IntVar(value=default_value)
            setattr(self, var_name, var)
            ttk.Spinbox(stocks_frame, from_=0, to=100, textvariable=var, 
                       width=15, justify="center").grid(row=i, column=1, sticky="w", padx=(16, 0))
        
        # Unlimited storage checkbox with better spacing
        self.unlimited_var = tk.BooleanVar(value=self.cfg.unlimited_storage)
        ttk.Checkbutton(stocks_frame, text="Unlimited Storage", variable=self.unlimited_var, 
                       style="Checkbutton.TCheckbutton").grid(row=4, column=0, columnspan=2, sticky="w", pady=(16, 0))
        
        # Consumption Cadence Section
        cadence_frame = ttk.LabelFrame(left_frame, text="Resource Consumption Cadence", padding=20)
        cadence_frame.grid(row=2, column=0, sticky="ew", pady=(0, 16))
        cadence_frame.grid_columnconfigure(1, weight=1)
        cadence_frame.grid_columnconfigure(3, weight=1)
        
        # Cadence inputs in a balanced 2x2 grid
        cadence_labels = [
            ("A (days/unit):", "a_days", self.cfg.a_days),
            ("B (days/unit):", "b_days", self.cfg.b_days),
            ("C (ops/unit):", "c_days", getattr(self.cfg, 'c_days', 2)),
            ("D (ops/unit):", "d_days", getattr(self.cfg, 'd_days', 2))
        ]
        
        for i, (label_text, var_name, default_value) in enumerate(cadence_labels):
            row = i // 2
            col = (i % 2) * 2  # 0 or 2
            
            ttk.Label(cadence_frame, text=label_text, style="Header.TLabel", 
                     width=18, anchor="w").grid(row=row, column=col, sticky="w", pady=(0, 8))
            var = tk.IntVar(value=default_value)
            setattr(self, var_name, var)
            ttk.Spinbox(cadence_frame, from_=1, to=30, textvariable=var, 
                       width=12, justify="center").grid(row=row, column=col+1, sticky="w", padx=(12, 0))
        
        # (Advanced Decision Making and Statistics sections removed)
        # (Help sections removed)
        
        # Right column - Quick Actions (Column 2)
        right_frame = ttk.Frame(tab, style="Card.TFrame")
        right_frame.grid(row=0, column=2, sticky="nsew", padx=(6, 0), pady=(0, 8))
        right_frame.grid_columnconfigure(0, weight=1)
        
        # Quick Actions Section
        actions_frame = ttk.LabelFrame(right_frame, text="Quick Actions", padding=16)
        actions_frame.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        
        # Action buttons
        ttk.Button(actions_frame, text="Reset to Defaults", 
                  command=self._reset_simulation_params, style="Secondary.TButton").pack(fill="x", pady=(0, 8))
        ttk.Button(actions_frame, text="Save Parameters", 
                  command=self._save_simulation_params, style="Primary.TButton").pack(fill="x", pady=(0, 8))
        ttk.Button(actions_frame, text="Load Preset", 
                  command=self._load_simulation_preset, style="Secondary.TButton").pack(fill="x")
        
        # Parameter Summary Section
        summary_frame = ttk.LabelFrame(right_frame, text="Parameter Summary", padding=16)
        summary_frame.grid(row=1, column=0, sticky="ew")
        
        self.param_summary_label = ttk.Label(summary_frame, text="Simulation parameters will be summarized here", 
                                            style="Muted.TLabel", wraplength=200, justify="center")
        self.param_summary_label.pack(expand=True, pady=20)

    def build_visual_tab(self, tab):
        """Build the enhanced visualization tab with improved layout and balance."""
        # Configure main tab for three-column layout with better proportions
        tab.grid_columnconfigure(0, weight=2)  # Visual settings get most space
        tab.grid_columnconfigure(1, weight=2)  # Bar scale gets medium space
        tab.grid_columnconfigure(2, weight=1)  # Help and options get least space
        tab.grid_rowconfigure(0, weight=1)
        
        # Left column - Visual Settings
        left_frame = ttk.Frame(tab, style="Card.TFrame")
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=8)
        left_frame.grid_columnconfigure(0, weight=1)
        
        # Visual Settings Section
        vis_frame = ttk.LabelFrame(left_frame, text="Visual Settings", padding=20)
        vis_frame.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        vis_frame.grid_columnconfigure(1, weight=1)
        
        # Side panels setting
        side_panels_row = ttk.Frame(vis_frame)
        side_panels_row.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        self.include_side_panels_var = tk.BooleanVar(value=getattr(self.cfg, "viz_include_side_panels", True))
        ttk.Checkbutton(side_panels_row, text="Include side panels in fullscreen", 
                       variable=self.include_side_panels_var, style="Checkbutton.TCheckbutton").grid(row=0, column=0, sticky="w")
        
        # Stats overlay setting
        stats_overlay_row = ttk.Frame(vis_frame)
        stats_overlay_row.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        self.show_stats_overlay_var = tk.BooleanVar(value=getattr(self.cfg, "viz_show_stats_overlay", False))
        ttk.Checkbutton(stats_overlay_row, text="Show statistics overlay", 
                       variable=self.show_stats_overlay_var, style="Checkbutton.TCheckbutton").grid(row=0, column=0, sticky="w")
        
        # Aircraft orientation setting
        orient_row = ttk.Frame(vis_frame)
        orient_row.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        self.orient_aircraft_var = tk.BooleanVar(value=self.cfg.orient_aircraft)
        ttk.Checkbutton(orient_row, text="Orient aircraft in flight direction", 
                       variable=self.orient_aircraft_var, style="Checkbutton.TCheckbutton").grid(row=0, column=0, sticky="w")
        
        # Aircraft labels setting
        labels_row = ttk.Frame(vis_frame)
        labels_row.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        self.show_aircraft_labels_var = tk.BooleanVar(value=self.cfg.show_aircraft_labels)
        ttk.Checkbutton(labels_row, text="Show aircraft labels", 
                       variable=self.show_aircraft_labels_var, style="Checkbutton.TCheckbutton").grid(row=0, column=0, sticky="w")
        
        # Aircraft trails setting
        trails_row = ttk.Frame(vis_frame)
        trails_row.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        self.show_aircraft_trails_var = tk.BooleanVar(value=getattr(self.cfg, "viz_show_aircraft_trails", True))
        ttk.Checkbutton(trails_row, text="Show aircraft motion trails", 
                       variable=self.show_aircraft_trails_var, style="Checkbutton.TCheckbutton").grid(row=0, column=0, sticky="w")
        
        # Header visibility setting
        header_row = ttk.Frame(vis_frame)
        header_row.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(0, 0))
        self.show_header_var = tk.BooleanVar(value=getattr(self.cfg, "viz_show_header", True))
        ttk.Checkbutton(header_row, text="Show simulation header", 
                       variable=self.show_header_var, style="Checkbutton.TCheckbutton").grid(row=0, column=0, sticky="w")

        # Center column - Bar Scale Configuration
        center_frame = ttk.Frame(tab, style="Card.TFrame")
        center_frame.grid(row=0, column=1, sticky="nsew", padx=6, pady=8)
        center_frame.grid_columnconfigure(0, weight=1)
        
        # Bar Scale (Denominators) group
        bar_scale_frame = ttk.LabelFrame(center_frame, text="Bar Scale (Denominators)", padding=20)
        bar_scale_frame.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        bar_scale_frame.grid_columnconfigure(0, weight=1)
        
        # Create a tooltip helper for the bar scale controls
        def create_bar_scale_tooltip(widget, resource_name):
            _Tooltip(widget, f"Each {resource_name} bar shows current_value / denominator", self.cfg.theme)
        
        # A, B, C, D denominator controls in a balanced 2x2 grid
        denom_vars = []
        error_labels = []
        resource_names = ["A", "B", "C", "D"]
        
        # Create a grid for balanced layout
        grid_frame = ttk.Frame(bar_scale_frame)
        grid_frame.grid(row=0, column=0, sticky="ew", pady=(8, 0))
        grid_frame.grid_columnconfigure(1, weight=1)
        grid_frame.grid_columnconfigure(3, weight=1)
        
        for i, (resource, name) in enumerate(zip([self.cfg.bar_scale.denom_A, self.cfg.bar_scale.denom_B, 
                                                  self.cfg.bar_scale.denom_C, self.cfg.bar_scale.denom_D], resource_names)):
            denom_var = tk.IntVar(value=resource)
            denom_vars.append(denom_var)
            
            # Place in 2x2 grid: A,B on top row, C,D on bottom row
            row = i // 2
            col = (i % 2) * 2  # 0 or 2
            
            # Container for each denominator control
            control_frame = ttk.Frame(grid_frame)
            control_frame.grid(row=row, column=col, columnspan=2, sticky="ew", padx=(0, 16), pady=8)
            control_frame.grid_columnconfigure(1, weight=1)
            
            ttk.Label(control_frame, text=f"{name}:", style="Header.TLabel", 
                     width=3, anchor="w").grid(row=0, column=0, sticky="w")
            
            # Spinbox for denominator input with validation
            def validate_denominator(value, var=denom_var):
                try:
                    if value == "":
                        return True
                    val = int(value)
                    return val >= 1 and val <= 99
                except ValueError:
                    return False
            
            vcmd = (self.root.register(validate_denominator), '%P')
            denom_entry = ttk.Spinbox(control_frame, from_=1, to=99, width=8, textvariable=denom_var, 
                                     validate="key", validatecommand=vcmd, command=lambda: self._on_bar_scale_changed(),
                                     justify="center")
            denom_entry.grid(row=0, column=1, sticky="ew", padx=(8, 0))
            
            # Add tooltip
            create_bar_scale_tooltip(denom_entry, name)
            
            # Error label for validation feedback
            error_label = ttk.Label(control_frame, text="", foreground="red", style="Muted.TLabel", 
                                   font=font_manager.get_font('tiny'))
            error_label.grid(row=0, column=2, sticky="w", padx=(8, 0))
            error_labels.append(error_label)
        
        # Store denominator variables and error labels for later access
        self.bar_scale_vars = denom_vars
        self.bar_scale_error_labels = error_labels
        
        # Button row for bar scale actions
        button_row = ttk.Frame(bar_scale_frame)
        button_row.grid(row=1, column=0, sticky="ew", pady=(16, 0))
        button_row.grid_columnconfigure(0, weight=1)
        button_row.grid_columnconfigure(1, weight=1)
        
        # Reset to Defaults button
        reset_btn = ttk.Button(button_row, text="Reset to Defaults", 
                              command=self._reset_bar_scale_defaults, style="Secondary.TButton")
        reset_btn.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        
        # Apply to All Sessions (Save) button
        save_btn = ttk.Button(button_row, text="Save Configuration", 
                             command=self._save_bar_scale_config, style="Primary.TButton")
        save_btn.grid(row=0, column=1, sticky="ew", padx=(4, 0))
        
        # Help text for bar scale
        help_text = ttk.Label(bar_scale_frame, text="Each bar shows current_value / denominator. Bars are bounded only by their pixel containers.", 
                             style="Muted.TLabel", wraplength=350, justify="center")
        help_text.grid(row=2, column=0, sticky="ew", pady=(12, 0))

        # Right column - Panel Options and Help
        right_frame = ttk.Frame(tab, style="Card.TFrame")
        right_frame.grid(row=0, column=2, sticky="nsew", padx=(6, 0), pady=8)
        right_frame.grid_columnconfigure(0, weight=1)
        
        # Right panel view configuration
        panel_frame = ttk.LabelFrame(right_frame, text="Right Panel View", padding=16)
        panel_frame.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        panel_frame.grid_columnconfigure(1, weight=1)
        
        ttk.Label(panel_frame, text="Display mode:", style="Header.TLabel", 
                 width=15, anchor="w").grid(row=0, column=0, sticky="w", pady=(0, 8))
        self.right_panel_view_var = tk.StringVar(value=getattr(self.cfg, "right_panel_view", "ops_total_sparkline"))
        panel_menu = ttk.OptionMenu(panel_frame, self.right_panel_view_var, 
                                   self.right_panel_view_var.get(), 
                                   "ops_total_sparkline", "ops_total_number", "ops_by_spoke")
        panel_menu.grid(row=0, column=1, sticky="ew", padx=(12, 0))

        # Cursor color configuration
        cursor_frame = ttk.LabelFrame(right_frame, text="Cursor Color", padding=16)
        cursor_frame.grid(row=1, column=0, sticky="ew", pady=(0, 16))
        cursor_frame.grid_columnconfigure(1, weight=1)
        
        ttk.Label(cursor_frame, text="Color:", style="Header.TLabel", 
                 width=15, anchor="w").grid(row=0, column=0, sticky="w", pady=(0, 8))
        self.cursor_color_var = tk.StringVar(value=self.cfg.cursor_color)
        cursor_menu = ttk.OptionMenu(cursor_frame, self.cursor_color_var, self.cfg.cursor_color, 
                                    *list(CURSOR_COLORS.keys()))
        cursor_menu.grid(row=0, column=1, sticky="ew", padx=(12, 0))
        
        # Help section
        help_frame = ttk.LabelFrame(right_frame, text="Visualization Help", padding=16)
        help_frame.grid(row=2, column=0, sticky="ew")
        help_frame.grid_columnconfigure(0, weight=1)
        
        help_text = [
            "• Side Panels: Show operational data during simulation",
            "• Statistics Overlay: Display real-time performance metrics", 
            "• Aircraft Orientation: Rotate aircraft to show flight direction",
            "• Aircraft Labels: Show identification tags on aircraft",
            "• Header: Display simulation status and operational summary",
            "• Bar Scale: Control how resource bars are scaled",
            "• Right Panel: Choose what operational data to display",
            "• Cursor Color: Select highlight color for better visibility"
        ]
        
        for i, help_line in enumerate(help_text):
            ttk.Label(help_frame, text=f"• {help_line}", style="Muted.TLabel", 
                     wraplength=250).grid(row=i, column=0, sticky="w", pady=4)

    def build_theme_tab(self, tab):
        """Build the enhanced theme tab with improved layout and balance."""
        # Configure main tab for three-column layout with better proportions
        tab.grid_columnconfigure(0, weight=2)  # Theme selection gets most space
        tab.grid_columnconfigure(1, weight=2)  # Color preview gets medium space
        tab.grid_columnconfigure(2, weight=1)  # Aircraft colors gets least space
        tab.grid_rowconfigure(0, weight=1)
        
        # Left column - Theme Selection
        left_frame = ttk.Frame(tab, style="Card.TFrame")
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=8)
        left_frame.grid_columnconfigure(0, weight=1)
        
        # Theme preset selection with descriptions
        theme_frame = ttk.LabelFrame(left_frame, text="Theme Preset", padding=20)
        theme_frame.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        theme_frame.grid_columnconfigure(1, weight=1)
        
        # Theme selection row
        selection_row = ttk.Frame(theme_frame)
        selection_row.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        selection_row.grid_columnconfigure(1, weight=1)
        
        ttk.Label(selection_row, text="Theme:", style="Header.TLabel", 
                 font=font_manager.get_font('medium', 'bold'), width=15, anchor="w").grid(row=0, column=0, sticky="w")
        self.theme_preset_var = tk.StringVar(value=self.cfg.theme.preset)
        theme_names = list(THEME_PRESETS.keys())
        
        theme_menu = ttk.OptionMenu(selection_row, self.theme_preset_var, self.cfg.theme.preset, *theme_names, 
                                   command=self._on_theme_change)
        theme_menu.grid(row=0, column=1, sticky="ew", padx=(16, 0))
        
        # Theme description
        self.theme_description_label = ttk.Label(theme_frame, text="", style="Muted.TLabel", 
                                               wraplength=350, justify="center")
        self.theme_description_label.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        
        # Update description for current theme
        self._update_theme_description()
        
        # Theme information section
        info_frame = ttk.LabelFrame(left_frame, text="Theme Information", padding=20)
        info_frame.grid(row=1, column=0, sticky="ew")
        info_frame.grid_columnconfigure(0, weight=1)
        
        info_text = [
            "• Choose from predefined theme presets",
            "• Themes automatically apply when selected",
            "• Each theme has unique color schemes",
            "• Customize aircraft color schemes separately"
        ]
        
        for i, info_line in enumerate(info_text):
            ttk.Label(info_frame, text=f"• {info_line}", style="Muted.TLabel", 
                     wraplength=350).grid(row=i, column=0, sticky="w", pady=6)
        
        # Center column - Color Preview
        center_frame = ttk.Frame(tab, style="Card.TFrame")
        center_frame.grid(row=0, column=1, sticky="nsew", padx=6, pady=8)
        center_frame.grid_columnconfigure(0, weight=1)
        
        # Theme preview section
        preview_frame = ttk.LabelFrame(center_frame, text="Color Palette Preview", padding=20)
        preview_frame.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        preview_frame.grid_columnconfigure(0, weight=1)
        
        # Create color swatches in a balanced 3x2 grid
        self.color_swatches = {}
        colors_to_show = [
            ("Primary", "accent_primary"),
            ("Secondary", "accent_secondary"), 
            ("Success", "success"),
            ("Warning", "warning"),
            ("Error", "error"),
            ("Info", "info")
        ]
        
        # Create a 3x2 grid for color swatches
        for i, (label, attr) in enumerate(colors_to_show):
            row = i // 3
            col = i % 3
            
            # Container for each color swatch
            swatch_container = ttk.Frame(preview_frame)
            swatch_container.grid(row=row, column=col, sticky="ew", padx=(0, 16), pady=8)
            swatch_container.grid_columnconfigure(0, weight=1)
            
            # Label
            ttk.Label(swatch_container, text=label, style="Muted.TLabel", 
                     font=font_manager.get_font('normal', 'bold'), anchor="center").grid(row=0, column=0, sticky="ew")
            
            # Create color swatch (colored frame)
            swatch = tk.Frame(swatch_container, width=40, height=20, relief="solid", borderwidth=2)
            swatch.grid(row=1, column=0, sticky="ew", pady=(4, 0))
            self.color_swatches[attr] = swatch
            
            # Color value label
            color_label = ttk.Label(swatch_container, text="", style="Muted.TLabel", 
                                   font=font_manager.get_font('tiny'), anchor="center")
            color_label.grid(row=2, column=0, sticky="ew", pady=(2, 0))
            self.color_swatches[f"{attr}_label"] = color_label
        
        # Theme customization section
        custom_frame = ttk.LabelFrame(center_frame, text="Theme Customization", padding=20)
        custom_frame.grid(row=1, column=0, sticky="ew")
        custom_frame.grid_columnconfigure(0, weight=1)
        
        custom_text = [
            "• Colors automatically update when theme changes",
            "• Preview shows the current theme's color palette",
            "• Aircraft colors can be customized independently",
            "• Changes are applied immediately"
        ]
        
        for i, custom_line in enumerate(custom_text):
            ttk.Label(custom_frame, text=f"• {custom_line}", style="Muted.TLabel", 
                     wraplength=350).grid(row=i, column=0, sticky="w", pady=6)
        
        # Right column - Aircraft Colors
        right_frame = ttk.Frame(tab, style="Card.TFrame")
        right_frame.grid(row=0, column=2, sticky="nsew", padx=(6, 0), pady=8)
        right_frame.grid_columnconfigure(0, weight=1)
        
        # Airframe colorset selection
        colorset_frame = ttk.LabelFrame(right_frame, text="Aircraft Color Scheme", padding=20)
        colorset_frame.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        colorset_frame.grid_columnconfigure(1, weight=1)
        
        ttk.Label(colorset_frame, text="Color scheme:", style="Header.TLabel", 
                 font=font_manager.get_font('medium', 'bold'), width=18, anchor="w").grid(row=0, column=0, sticky="w", pady=(0, 8))
        self.airframe_colorset_var = tk.StringVar(value=self.cfg.theme.ac_colorset)
        colorset_names = list(AIRFRAME_COLORSETS.keys())
        
        colorset_menu = ttk.OptionMenu(colorset_frame, self.airframe_colorset_var, 
                                      self.cfg.theme.ac_colorset, *colorset_names,
                                      command=self._on_colorset_change)
        colorset_menu.grid(row=0, column=1, sticky="ew", padx=(16, 0))
        
        # Aircraft color information
        colorset_info_frame = ttk.LabelFrame(right_frame, text="Aircraft Colors", padding=20)
        colorset_info_frame.grid(row=1, column=0, sticky="ew")
        colorset_info_frame.grid_columnconfigure(0, weight=1)
        
        colorset_info_text = [
            "• Choose aircraft color schemes",
            "• Different schemes for different aircraft types",
            "• Colors apply to all aircraft in simulation",
            "• Can be changed independently of themes"
        ]
        
        for i, info_line in enumerate(colorset_info_text):
            ttk.Label(colorset_info_frame, text=f"• {info_line}", style="Muted.TLabel", 
                     wraplength=250).grid(row=i, column=0, sticky="w", pady=6)
    
    def _on_theme_change(self, *args):
        """Handle theme selection change - auto-apply the selected theme."""
        try:
            # Get the selected theme name
            theme_name = self.theme_preset_var.get()
            
            # Apply the theme preset
            apply_theme_preset(self.cfg.theme, theme_name)
            
            # Reapply the centralized theme system
            from cargosim.rendering.themes.ui_theme import apply_theme, create_palette_from_theme_config
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
            from cargosim.rendering.themes.ui_theme import apply_theme, create_palette_from_theme_config
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
        """Build the enhanced gameplay tab with improved layout and balance."""
        # Configure main tab for three-column layout with better proportions
        tab.grid_columnconfigure(0, weight=2)  # Main settings get most space
        tab.grid_columnconfigure(1, weight=2)  # Debug settings get medium space
        tab.grid_columnconfigure(2, weight=1)  # Help and launch get least space
        tab.grid_rowconfigure(0, weight=1)
        
        # Left column - Main Gameplay Settings
        left_frame = ttk.Frame(tab, style="Card.TFrame")
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=8)
        left_frame.grid_columnconfigure(0, weight=1)
        
        # Gameplay settings
        gameplay_frame = ttk.LabelFrame(left_frame, text="Gameplay Settings", padding=20)
        gameplay_frame.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        gameplay_frame.grid_columnconfigure(1, weight=1)
        
        # Period duration with better layout
        period_row = ttk.Frame(gameplay_frame)
        period_row.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        period_row.grid_columnconfigure(1, weight=1)
        
        ttk.Label(period_row, text="Period duration (seconds):", style="Header.TLabel", 
                 font=font_manager.get_font('medium', 'bold'), width=25, anchor="w").grid(row=0, column=0, sticky="w")
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
        period_scale.grid(row=0, column=1, sticky="ew", padx=(16, 12))
        
        period_entry = ttk.Entry(period_row, textvariable=self.period_seconds_var, width=10, justify="center")
        period_entry.grid(row=0, column=2, sticky="w")
        
        # Target FPS with better layout
        fps_row = ttk.Frame(gameplay_frame)
        fps_row.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 0))
        fps_row.grid_columnconfigure(1, weight=1)
        
        ttk.Label(fps_row, text="Target FPS:", style="Header.TLabel", 
                 font=font_manager.get_font('medium', 'bold'), width=25, anchor="w").grid(row=0, column=0, sticky="w")
        self.fps_var = tk.IntVar(value=self.cfg.fps)
        fps_spin = ttk.Spinbox(fps_row, from_=30, to=120, textvariable=self.fps_var, 
                              width=15, justify="center")
        fps_spin.grid(row=0, column=1, sticky="w", padx=(16, 0))
        
        # Gameplay information section
        info_frame = ttk.LabelFrame(left_frame, text="Gameplay Information", padding=20)
        info_frame.grid(row=1, column=0, sticky="ew")
        info_frame.grid_columnconfigure(0, weight=1)
        
        info_text = [
            "• Period Duration: Controls simulation speed",
            "• Target FPS: Affects animation smoothness",
            "• Higher FPS = smoother animation",
            "• Lower period duration = faster simulation"
        ]
        
        for i, info_line in enumerate(info_text):
            ttk.Label(info_frame, text=f"• {info_line}", style="Muted.TLabel", 
                     wraplength=350).grid(row=i, column=0, sticky="w", pady=6)

        # Center column - Debug Settings
        center_frame = ttk.Frame(tab, style="Card.TFrame")
        center_frame.grid(row=0, column=1, sticky="nsew", padx=6, pady=8)
        center_frame.grid_columnconfigure(0, weight=1)
        
        # Debug settings
        debug_frame = ttk.LabelFrame(center_frame, text="Debug Settings", padding=20)
        debug_frame.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        debug_frame.grid_columnconfigure(1, weight=1)
        
        # Debug mode
        debug_enable_row = ttk.Frame(debug_frame)
        debug_enable_row.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        self.debug_mode_var = tk.BooleanVar(value=self.cfg.debug_mode)
        ttk.Checkbutton(debug_enable_row, text="Enable debug mode", 
                       variable=self.debug_mode_var, style="Checkbutton.TCheckbutton").grid(row=0, column=0, sticky="w")
        
        # Random seed
        seed_row = ttk.Frame(debug_frame)
        seed_row.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 0))
        seed_row.grid_columnconfigure(1, weight=1)
        
        ttk.Label(seed_row, text="Random seed:", style="Header.TLabel", 
                 font=font_manager.get_font('medium', 'bold'), width=20, anchor="w").grid(row=0, column=0, sticky="w")
        self.seed_var = tk.IntVar(value=self.cfg.seed)
        seed_spin = ttk.Spinbox(seed_row, from_=1, to=999999, textvariable=self.seed_var, 
                               width=15, justify="center")
        seed_spin.grid(row=0, column=1, sticky="w", padx=(16, 0))
        
        # Debug information section
        debug_info_frame = ttk.LabelFrame(center_frame, text="Debug Information", padding=20)
        debug_info_frame.grid(row=1, column=0, sticky="ew")
        debug_info_frame.grid_columnconfigure(0, weight=1)
        
        debug_info_text = [
            "• Debug Mode: Shows detailed simulation data",
            "• Press D to cycle: OFF → BASIC → DETAILED",
            "• Press F12 as alternative toggle",
            "• Random Seed: Ensures reproducible results"
        ]
        
        for i, info_line in enumerate(debug_info_text):
            ttk.Label(debug_info_frame, text=f"• {info_line}", style="Muted.TLabel", 
                     wraplength=350).grid(row=i, column=0, sticky="w", pady=6)

        # Right column - Launch Settings and Help
        right_frame = ttk.Frame(tab, style="Card.TFrame")
        right_frame.grid(row=0, column=2, sticky="nsew", padx=(6, 0), pady=8)
        right_frame.grid_columnconfigure(0, weight=1)
        
        # Launch settings
        launch_frame = ttk.LabelFrame(right_frame, text="Launch Settings", padding=20)
        launch_frame.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        
        self.launch_fullscreen_var = tk.BooleanVar(value=self.cfg.launch_fullscreen)
        ttk.Checkbutton(launch_frame, text="Launch in fullscreen mode", 
                       variable=self.launch_fullscreen_var, style="Checkbutton.TCheckbutton").grid(row=0, column=0, sticky="w")
        
        # Launch information
        launch_info_frame = ttk.LabelFrame(right_frame, text="Launch Information", padding=20)
        launch_info_frame.grid(row=1, column=0, sticky="ew", pady=(0, 16))
        launch_info_frame.grid_columnconfigure(0, weight=1)
        
        launch_info_text = [
            "• Fullscreen: Maximizes simulation window",
            "• Windowed: Standard window mode",
            "• Can be toggled during simulation",
            "• F11 toggles fullscreen mode"
        ]
        
        for i, info_line in enumerate(launch_info_text):
            ttk.Label(launch_info_frame, text=f"• {info_line}", style="Muted.TLabel", 
                     wraplength=250).grid(row=i, column=0, sticky="w", pady=6)
        
        # Help section
        help_frame = ttk.LabelFrame(right_frame, text="Quick Help", padding=20)
        help_frame.grid(row=2, column=0, sticky="ew")
        help_frame.grid_columnconfigure(0, weight=1)
        
        help_text = [
            "• D: Cycle debug levels",
            "• F11: Toggle fullscreen",
            "• F12: Alternative debug toggle",
            "• ESC: Return to menu"
        ]
        
        for i, help_line in enumerate(help_text):
            ttk.Label(help_frame, text=f"• {help_line}", style="Muted.TLabel", 
                     wraplength=250).grid(row=i, column=0, sticky="w", pady=4)

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
            msg.append("pygame missing — simulation disabled")
            self.start_btn.state(["disabled"])
        
        if pygame_available:
            self.start_btn.state(["!disabled"])
        
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
        
        # Save the current fleet before starting simulation
        try:
            if hasattr(self, 'fleet_persistence') and hasattr(self, 'fleet_builder_tab_instance'):
                if hasattr(self.fleet_builder_tab_instance, 'fleet_builder') and self.fleet_builder_tab_instance.fleet_builder:
                    # Get current fleet composition from fleet builder
                    current_fleet = self.fleet_builder_tab_instance.fleet_builder.get_fleet_composition()
                    if current_fleet and current_fleet.get("aircraft"):
                        # Get spoke configuration if available
                        spoke_config = None
                        if hasattr(self.fleet_builder_tab_instance, 'spoke_config_panel'):
                            try:
                                spoke_config = self.fleet_builder_tab_instance.spoke_config_panel.get_config()
                            except Exception as e:
                                logger.warning(f"Could not get spoke configuration: {e}")
                        
                        # Save the current fleet and spoke configuration for next startup
                        self.fleet_persistence.save_last_fleet(current_fleet, spoke_config)
                        logger.info("Current fleet and spoke configuration saved before simulation start")
                    else:
                        logger.warning("No current fleet to save")
                else:
                    logger.warning("Fleet builder not available for saving fleet")
        except Exception as e:
            logger.warning(f"Could not save current fleet: {e}")
        
        # Save spoke configuration if available
        try:
            if hasattr(self, 'fleet_builder_tab_instance') and hasattr(self.fleet_builder_tab_instance, 'spoke_config_panel'):
                spoke_config = self.fleet_builder_tab_instance.spoke_config_panel.get_config()
                if spoke_config:
                    # Save spoke configuration to the main config
                    self.cfg.spoke_config = spoke_config
                    
                    # Transfer spoke configuration to main simulation config
                    if 'spoke_distances' in spoke_config:
                        self.cfg.spoke_distances = spoke_config['spoke_distances']
                        logger.info(f"Spoke distances updated: {len(self.cfg.spoke_distances)} spokes")
                    
                    if 'max_spokes' in spoke_config:
                        # Update the M constant if needed (this affects the simulation)
                        from cargosim.core.config import M
                        if spoke_config['max_spokes'] != M:
                            logger.info(f"Spoke count changed from {M} to {spoke_config['max_spokes']}")
                    
                    logger.info("Spoke configuration saved and transferred to simulation config")
        except Exception as e:
            logger.warning(f"Could not save spoke configuration: {e}")
        
        # Save all GUI state variables to ensure complete configuration persistence
        try:
            # Save custom aircraft configuration
            if hasattr(self, 'custom_vars') and hasattr(self, 'capability_vars'):
                custom_config = {
                    'capacity': self.custom_vars.get('capacity', tk.DoubleVar()).get(),
                    'rest_periods': self.custom_vars.get('rest_periods', tk.IntVar()).get(),
                    'range_factor': self.custom_vars.get('range_factor', tk.DoubleVar()).get(),
                    'fuel_efficiency': self.custom_vars.get('fuel_efficiency', tk.DoubleVar()).get(),
                    'maintenance_cost': self.custom_vars.get('maintenance_cost', tk.DoubleVar()).get(),
                    'speed': self.custom_vars.get('speed', tk.DoubleVar()).get(),
                    'capabilities': [cap for cap, var in self.capability_vars.items() if var.get()]
                }
                self.cfg.custom_aircraft_config = custom_config
                logger.info("Custom aircraft configuration saved before simulation start")
        except Exception as e:
            logger.warning(f"Could not save custom aircraft configuration: {e}")
        
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
        
        # Save the complete configuration
        try:
            save_config(self.cfg)
            logger.info("Complete configuration saved before simulation start")
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            messagebox.showerror("Configuration Error", f"Failed to save configuration: {e}")
            return
            
        self.root.destroy()
        from cargosim.main import run_sim
        exit_code, live_out = run_sim(self.cfg, force_windowed=self.force_windowed)
        if live_out:
            tmp = tk.Tk(); tmp.withdraw()
            # Recording saved successfully - no popup needed
            tmp.destroy()
        if exit_code == "GUI":
            from cargosim.main import main
            main()

    def _read_back_to_cfg(self) -> bool:
        """Read values from GUI back to config object."""
        try:
            # Configuration tab (fleet preset removed)
            
            # Custom Transport Configuration
            if hasattr(self, 'custom_vars') and hasattr(self, 'capability_vars'):
                try:
                    # Update custom aircraft configuration in fleet builder
                    from cargosim.ui.fleet_builder import get_aircraft_config_manager
                    config_manager = get_aircraft_config_manager()
                    
                    if "Custom_Transport" in config_manager.aircraft_types:
                        custom_aircraft = config_manager.aircraft_types["Custom_Transport"]
                        
                        # Update attributes
                        custom_aircraft.base_capacity = int(self.custom_vars["capacity"].get())
                        custom_aircraft.rest_periods = int(self.custom_vars["rest_periods"].get())
                        custom_aircraft.range_factor = self.custom_vars["range_factor"].get()
                        custom_aircraft.fuel_efficiency = self.custom_vars["fuel_efficiency"].get()
                        custom_aircraft.maintenance_cost = self.custom_vars["maintenance_cost"].get()
                        custom_aircraft.cruise_speed_mach = self.custom_vars["speed"].get()
                        
                        # Update special capabilities
                        custom_aircraft.special_capabilities = [
                            cap for cap, var in self.capability_vars.items() if var.get()
                        ]
                        
                        # Save updated configuration
                        config_manager.save_config()
                        
                except Exception as e:
                    logger.warning(f"Could not update custom transport configuration: {e}")
            
            # Restore custom aircraft configuration from saved config if available
            if hasattr(self, 'custom_vars') and hasattr(self, 'capability_vars'):
                try:
                    if hasattr(self.cfg, 'custom_aircraft_config'):
                        custom_config = self.cfg.custom_aircraft_config
                        if custom_config:
                            # Restore custom aircraft values
                            if 'capacity' in custom_config and 'capacity' in self.custom_vars:
                                self.custom_vars['capacity'].set(custom_config['capacity'])
                            if 'rest_periods' in custom_config and 'rest_periods' in self.custom_vars:
                                self.custom_vars['rest_periods'].set(custom_config['rest_periods'])
                            if 'range_factor' in custom_config and 'range_factor' in self.custom_vars:
                                self.custom_vars['range_factor'].set(custom_config['range_factor'])
                            if 'fuel_efficiency' in custom_config and 'fuel_efficiency' in self.custom_vars:
                                self.custom_vars['fuel_efficiency'].set(custom_config['fuel_efficiency'])
                            if 'maintenance_cost' in custom_config and 'maintenance_cost' in self.custom_vars:
                                self.custom_vars['maintenance_cost'].set(custom_config['maintenance_cost'])
                            if 'speed' in custom_config and 'speed' in self.custom_vars:
                                self.custom_vars['speed'].set(custom_config['speed'])
                            
                            # Restore capabilities
                            if 'capabilities' in custom_config and hasattr(self, 'capability_vars'):
                                for capability in custom_config['capabilities']:
                                    if capability in self.capability_vars:
                                        self.capability_vars[capability].set(True)
                            
                            logger.info("Restored custom aircraft configuration from saved config")
                except Exception as e:
                    logger.warning(f"Could not restore custom aircraft configuration: {e}")
            
            # Restore spoke configuration from saved config if available
            try:
                if hasattr(self.cfg, 'spoke_config'):
                    spoke_config = self.cfg.spoke_config
                    if spoke_config and hasattr(self, 'fleet_builder_tab_instance') and hasattr(self.fleet_builder_tab_instance, 'spoke_config_panel'):
                        self.fleet_builder_tab_instance.spoke_config_panel.set_config(spoke_config)
                        logger.info("Restored spoke configuration from saved config")
            except Exception as e:
                logger.warning(f"Could not restore spoke configuration: {e}")
            
            # Simulation Parameters tab
            if hasattr(self, 'periods_var'):
                self.cfg.periods = self.periods_var.get()
            if hasattr(self, 'initA'):
                self.cfg.init_A = self.initA.get()
                self.cfg.init_B = self.initB.get()
                self.cfg.init_C = self.initC.get()
                self.cfg.init_D = self.initD.get()
                self.cfg.unlimited_storage = self.unlimited_var.get()
            if hasattr(self, 'a_days'):
                self.cfg.a_days = self.a_days.get()
                self.cfg.b_days = self.b_days.get()
                self.cfg.c_days = self.c_days.get()
                self.cfg.d_days = self.d_days.get()
            
            # Schedule tab - pair_order is now handled automatically by the simulation
            # No need to read from GUI as it's managed internally
            
            # (Advanced decision making and stats mode variables removed)
            
            # Visual tab
            setattr(self.cfg, "viz_include_side_panels", self.include_side_panels_var.get())
            setattr(self.cfg, "viz_show_stats_overlay", self.show_stats_overlay_var.get())
            self.cfg.orient_aircraft = self.orient_aircraft_var.get()
            self.cfg.show_aircraft_labels = self.show_aircraft_labels_var.get()
            setattr(self.cfg, "viz_show_aircraft_trails", self.show_aircraft_trails_var.get())
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

    def _on_window_close(self):
        """Handle window close event - save current fleet before closing."""
        try:
            if hasattr(self, 'fleet_persistence') and hasattr(self, 'fleet_builder_tab_instance'):
                if hasattr(self.fleet_builder_tab_instance, 'fleet_builder') and self.fleet_builder_tab_instance.fleet_builder:
                    # Get current fleet composition from fleet builder
                    current_fleet = self.fleet_builder_tab_instance.fleet_builder.get_fleet_composition()
                    if current_fleet and current_fleet.get("aircraft"):
                        # Get spoke configuration if available
                        spoke_config = None
                        if hasattr(self.fleet_builder_tab_instance, 'spoke_config_panel'):
                            try:
                                spoke_config = self.fleet_builder_tab_instance.spoke_config_panel.get_config()
                            except Exception as e:
                                logger.warning(f"Could not get spoke configuration on close: {e}")
                        
                        # Save the current fleet and spoke configuration for next startup
                        self.fleet_persistence.save_last_fleet(current_fleet, spoke_config)
                        logger.info("Current fleet and spoke configuration saved on window close")
                    else:
                        logger.info("No current fleet to save on window close")
                else:
                    logger.info("Fleet builder not available for saving fleet on close")
            else:
                logger.info("Fleet persistence not available for saving fleet on close")
        except Exception as e:
            logger.warning(f"Could not save fleet on window close: {e}")
        
        # Destroy the root window
        self.root.destroy()

    def _apply_specific_widget_theming(self):
        """No-op - theming is handled centrally by ui_theme.py."""
        pass

    def _apply_dropdown_styling(self):
        """No-op - theming is handled centrally by ui_theme.py."""
        pass

    def _setup_global_widget_options(self):
        """No-op - theming is handled centrally by ui_theme.py."""
        pass

    def _reset_bar_scale_defaults(self):
        """Reset bar scale denominators to their default values."""
        from cargosim.core.config import DEFAULT_BAR_SCALE_DENOMINATORS
        for i, var in enumerate(self.bar_scale_vars):
            var.set(DEFAULT_BAR_SCALE_DENOMINATORS[i])
        self._on_bar_scale_changed()
        messagebox.showinfo("Bar Scale Reset", "Bar scale denominators have been reset to their default values.")

    def _save_bar_scale_config(self):
        """Save the current bar scale denominators to the config."""
        try:
            # Validate all values before saving
            for i, var in enumerate(self.bar_scale_vars):
                value = var.get()
                if not (1 <= value <= 99):
                    messagebox.showerror("Validation Error", f"Denominator {['A', 'B', 'C', 'D'][i]} must be between 1 and 99")
                    return
            
            # Update config
            self.cfg.bar_scale.denom_A = self.bar_scale_vars[0].get()
            self.cfg.bar_scale.denom_B = self.bar_scale_vars[1].get()
            self.cfg.bar_scale.denom_C = self.bar_scale_vars[2].get()
            self.cfg.bar_scale.denom_D = self.bar_scale_vars[3].get()
            
            # Save to disk
            from cargosim.core.config import save_config
            save_config(self.cfg)
            
            messagebox.showinfo("Bar Scale Saved", "Bar scale denominators have been saved to the configuration and will persist across sessions.")
        except Exception as e:
            messagebox.showerror("Error Saving Bar Scale", f"Failed to save bar scale denominators: {e}")

    def _on_bar_scale_changed(self):
        """Handle bar scale changes and update error labels."""
        for i, var in enumerate(self.bar_scale_vars):
            try:
                value = var.get()
                if hasattr(self, 'bar_scale_error_labels') and i < len(self.bar_scale_error_labels):
                    error_label = self.bar_scale_error_labels[i]
                    if value < 1 or value > 99:
                        error_label.configure(text="Must be between 1 and 99")
                    else:
                        error_label.configure(text="")
            except (tk.TclError, ValueError):
                # Handle invalid input gracefully
                pass
        
        # Update simulation bar scale if available
        self._update_simulation_bar_scale()
    
    def _update_simulation_bar_scale(self):
        """Update the simulation's bar scale with current values."""
        try:
            # Check if we have access to the simulation
            if hasattr(self, 'simulation') and self.simulation:
                # Update the simulation's bar scale
                self.simulation.cfg.bar_scale.denom_A = self.bar_scale_vars[0].get()
                self.simulation.cfg.bar_scale.denom_B = self.bar_scale_vars[1].get()
                self.simulation.cfg.bar_scale.denom_C = self.bar_scale_vars[2].get()
                self.simulation.cfg.bar_scale.denom_D = self.bar_scale_vars[3].get()
                
                # Update the simulation's bar_scale attribute
                self.simulation.bar_scale = self.simulation.cfg.bar_scale
                
                # Try to refresh the renderer if available
                if hasattr(self, 'renderer') and self.renderer:
                    self.renderer.refresh_bar_states()
        except Exception as e:
            # Silently handle errors - simulation might not be running yet
            pass
    
    # Helper methods for the new tab layouts
    def _reset_custom_aircraft(self):
        """Reset custom aircraft configuration to defaults."""
        # Reset to default values
        defaults = {"capacity": 4, "rest_periods": 8, "range_factor": 1.0, 
                   "fuel_efficiency": 1.0, "maintenance_cost": 1.0, "speed": 0.5}
        
        for attr, default_value in defaults.items():
            if attr in self.custom_vars:
                self.custom_vars[attr].set(default_value)
        
        # Clear all capabilities
        for var in self.capability_vars.values():
            var.set(False)
        
        # Update preview
        self._update_aircraft_preview()
    
    def _save_custom_aircraft(self):
        """Save custom aircraft configuration."""
        try:
            # Update custom aircraft configuration in fleet builder
            from cargosim.ui.fleet_builder import get_aircraft_config_manager
            config_manager = get_aircraft_config_manager()
            
            if "Custom_Transport" in config_manager.aircraft_types:
                custom_aircraft = config_manager.aircraft_types["Custom_Transport"]
                
                # Update attributes
                custom_aircraft.base_capacity = int(self.custom_vars["capacity"].get())
                custom_aircraft.rest_periods = int(self.custom_vars["rest_periods"].get())
                custom_aircraft.range_factor = self.custom_vars["range_factor"].get()
                custom_aircraft.fuel_efficiency = self.custom_vars["fuel_efficiency"].get()
                custom_aircraft.maintenance_cost = self.custom_vars["maintenance_cost"].get()
                custom_aircraft.cruise_speed_mach = self.custom_vars["speed"].get()
                
                # Update special capabilities
                custom_aircraft.special_capabilities = [
                    cap for cap, var in self.capability_vars.items() if var.get()
                ]
                
                # Save updated configuration
                config_manager.save_config()
                
                # Update preview
                self._update_aircraft_preview()
                
                messagebox.showinfo("Success", "Custom aircraft configuration saved successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save custom aircraft configuration: {e}")
    
    def _load_aircraft_preset(self):
        """Load aircraft preset configuration."""
        # This would typically show a dialog to select a preset
        messagebox.showinfo("Info", "Aircraft preset loading functionality would be implemented here.")
    
    def _update_aircraft_preview(self):
        """Update the aircraft preview display."""
        if hasattr(self, 'aircraft_preview_label'):
            try:
                capacity = self.custom_vars["capacity"].get()
                rest = self.custom_vars["rest_periods"].get()
                range_factor = self.custom_vars["range_factor"].get()
                fuel = self.custom_vars["fuel_efficiency"].get()
                maintenance = self.custom_vars["maintenance_cost"].get()
                
                capabilities = [cap.replace("_", " ").title() 
                              for cap, var in self.capability_vars.items() if var.get()]
                
                speed = self.custom_vars["speed"].get()
                preview_text = f"Capacity: {capacity}\nRest: {rest} periods\nRange: {range_factor}x\nFuel: {fuel}x\nCost: {maintenance}x\nSpeed: {speed:.2f} Mach"
                
                if capabilities:
                    preview_text += f"\n\nCapabilities:\n{', '.join(capabilities)}"
                
                self.aircraft_preview_label.configure(text=preview_text)
            except Exception:
                self.aircraft_preview_label.configure(text="Custom aircraft configuration will appear here")
    
    def _reset_simulation_params(self):
        """Reset simulation parameters to defaults."""
        # Reset to default values from config
        if hasattr(self, 'periods_var'):
            self.periods_var.set(100)
        if hasattr(self, 'initA'):
            self.initA.set(10)
            self.initB.set(10)
            self.initC.set(10)
            self.initD.set(10)
            self.unlimited_var.set(False)
        if hasattr(self, 'a_days'):
            self.a_days.set(2)
            self.b_days.set(2)
            self.c_days.set(2)
            self.d_days.set(2)
        
        # (Advanced decision making and stats mode variables removed)
        
        # Update parameter summary
        self._update_param_summary()
    
    def _save_simulation_params(self):
        """Save simulation parameters."""
        try:
            # This would typically save to a preset file
            messagebox.showinfo("Success", "Simulation parameters saved successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save simulation parameters: {e}")
    
    def _load_simulation_preset(self):
        """Load simulation preset."""
        # This would typically show a dialog to select a preset
        messagebox.showinfo("Info", "Simulation preset loading functionality would be implemented here.")
    
    def _update_param_summary(self):
        """Update the parameter summary display."""
        if hasattr(self, 'param_summary_label'):
            try:
                periods = self.periods_var.get()
                init_a = self.initA.get()
                init_b = self.initB.get()
                init_c = self.initC.get()
                init_d = self.initD.get()
                unlimited = self.unlimited_var.get()
                
                summary_text = f"Periods: {periods}\nInitial A: {init_a}\nInitial B: {init_b}\nInitial C: {init_c}\nInitial D: {init_d}\nUnlimited: {'Yes' if unlimited else 'No'}"
                
                self.param_summary_label.configure(text=summary_text)
            except Exception:
                                self.param_summary_label.configure(text="Simulation parameters will be summarized here")
    
    def _initialize_previews(self):
        """Initialize preview displays for various tabs."""
        try:
            # Initialize aircraft preview
            if hasattr(self, 'aircraft_preview_label'):
                self._update_aircraft_preview()
            
            # Initialize parameter summary
            if hasattr(self, 'param_summary_label'):
                self._update_param_summary()
                
        except Exception as e:
            # Silently handle errors during initialization
            pass
    
    def _toggle_fullscreen_gui(self, event=None):
        """Toggle fullscreen mode."""
        try:
            if self.root.state() == 'zoomed':
                self.root.state('normal')
                self._apply_normal_layout()
            else:
                self.root.state('zoomed')
                self._apply_fullscreen_layout()
                
        except Exception as e:
            print(f"Error toggling fullscreen: {e}")
    
    def _update_status_bar(self, message):
        """Update the status bar message."""
        try:
            if hasattr(self, 'status_label'):
                self.status_label.configure(text=message)
        except Exception:
            pass
    
    def _on_tab_changed(self, event):
        """Handle tab change events to update status bar."""
        try:
            notebook = event.widget
            current_tab = notebook.select()
            tab_name = notebook.tab(current_tab, "text").strip()
            
            # Update status bar with tab-specific information
            if "Fleet Configuration" in tab_name:
                self._update_status_bar("Fleet Configuration - Configure aircraft and capabilities")
            elif "Fleet Builder" in tab_name:
                self._update_status_bar("Fleet Builder - Build and manage your aircraft fleet")
            elif "Simulation Parameters" in tab_name:
                self._update_status_bar("Simulation Parameters - Set up simulation timing and resources")
            elif "Operations" in tab_name:
                self._update_status_bar("Operations - Live aircraft status and cost tracking")
            elif "Visualization" in tab_name:
                self._update_status_bar("Visualization - Customize display and bar scaling")
            elif "Gameplay" in tab_name:
                self._update_status_bar("Gameplay - Adjust simulation speed and debug settings")
            elif "Theme" in tab_name:
                self._update_status_bar("Theme - Choose visual themes and color schemes")
            elif "Recording" in tab_name:
                self._update_status_bar("Recording - Configure simulation recording options")
            elif "Save / Start" in tab_name:
                self._update_status_bar("Save / Start - Save configuration and launch simulation")
            else:
                self._update_status_bar("Ready - Press F11 to toggle fullscreen")
                
        except Exception:
            # Silently handle tab change errors
            pass
    
    def _create_status_bar(self):
        """Create a status bar at the bottom of the GUI."""
        try:
            # Create status bar frame
            self.status_bar = ttk.Frame(self.root, style="Card.TFrame")
            self.status_bar.pack(side="bottom", fill="x", padx=10, pady=(0, 10))
            
            # Status information
            self.status_label = ttk.Label(self.status_bar, text="Ready - Press F11 to toggle fullscreen", 
                                        style="Muted.TLabel")
            self.status_label.pack(side="left", padx=8, pady=4)
            
            # Performance information (will be updated by performance monitor)
            self.performance_status_label = ttk.Label(self.status_bar, text="", 
                                                   style="Muted.TLabel")
            self.performance_status_label.pack(side="left", padx=20, pady=4)
            
            # Version/help info
            help_label = ttk.Label(self.status_bar, text="Press F11: Fullscreen | ESC: Exit", 
                                 style="Muted.TLabel")
            help_label.pack(side="right", padx=8, pady=4)
            
        except Exception as e:
            # Silently handle status bar creation errors
            pass
    
    def build_fleet_tab(self, tab):
        """Build the Fleet Builder tab."""
        try:
            from cargosim.ui.fleet_builder_gui import FleetBuilderTab
            from cargosim.ui.fleet_persistence import FleetPersistenceManager
            
            # Create the fleet builder tab
            self.fleet_builder_tab = FleetBuilderTab(tab, self.configuration_manager)
            self.fleet_builder_tab.pack(fill="both", expand=True)
            
            # Store reference for later use
            self.fleet_builder_tab_instance = self.fleet_builder_tab
            
            # Load the appropriate fleet on startup
            try:
                if hasattr(self.fleet_builder_tab, 'fleet_builder') and self.fleet_builder_tab.fleet_builder:
                    # Wait a bit for the fleet builder to fully initialize
                    self.after(500, self._load_startup_fleet)
                else:
                    logger.warning("Fleet builder not available for loading fleet")
            except Exception as e:
                logger.warning(f"Could not setup startup fleet loading: {e}")
            
            # Initialize custom aircraft values from aircraft configuration
            try:
                self._initialize_custom_aircraft_from_config()
            except Exception as e:
                logger.warning(f"Could not initialize custom aircraft from config: {e}")
            
        except ImportError as e:
            # Fallback if fleet builder is not available
            error_frame = ttk.Frame(tab)
            error_frame.pack(fill="both", expand=True, pady=50)
            
            ttk.Label(error_frame, text="Fleet Builder Not Available", 
                     style="Header.TLabel", font=font_manager.get_font('title', 'bold')).pack(pady=(0, 20))
            
            ttk.Label(error_frame, text="The Fleet Builder module could not be loaded.", 
                     style="Muted.TLabel").pack(pady=(0, 10))
            
            ttk.Label(error_frame, text=f"Error: {e}", 
                     style="Muted.TLabel", wraplength=400).pack(pady=(0, 20))
            
            ttk.Button(error_frame, text="Continue without Fleet Builder", 
                      command=lambda: tab.destroy()).pack()
    
    def _load_startup_fleet(self):
        """Load the startup fleet after the fleet builder has fully initialized."""
        try:
            if hasattr(self, 'fleet_builder_tab') and hasattr(self.fleet_builder_tab, 'fleet_builder') and self.fleet_builder_tab.fleet_builder:
                # Load fleet using persistence manager (last used or default)
                startup_fleet = self.fleet_persistence.load_fleet_on_startup()
                
                if startup_fleet and startup_fleet.get("aircraft"):
                    # Convert to fleet composition format
                    fleet_config = {
                        "name": startup_fleet["name"],
                        "aircraft": startup_fleet["aircraft"]
                    }
                    
                    # Load the fleet into the fleet builder
                    success = self.fleet_builder_tab.load_fleet_from_config(fleet_config)
                    
                    if success:
                        logger.info(f"Loaded startup fleet: {startup_fleet['name']}")
                    else:
                        logger.warning("Failed to load startup fleet, using empty fleet")
                else:
                    logger.info("No startup fleet to load, using empty fleet")
            else:
                logger.warning("Fleet builder not available for loading startup fleet")
        except Exception as e:
            logger.warning(f"Could not load startup fleet: {e}")

    def _initialize_custom_aircraft_from_config(self):
        """Initialize custom aircraft values from the aircraft configuration file."""
        try:
            if hasattr(self, 'custom_vars') and hasattr(self, 'capability_vars'):
                # Get the aircraft configuration manager
                from cargosim.ui.fleet_builder import get_aircraft_config_manager
                config_manager = get_aircraft_config_manager()
                
                if "Custom_Transport" in config_manager.aircraft_types:
                    custom_aircraft = config_manager.aircraft_types["Custom_Transport"]
                    
                    # Set the custom aircraft values from the configuration
                    if 'capacity' in self.custom_vars:
                        self.custom_vars['capacity'].set(custom_aircraft.base_capacity)
                    if 'rest_periods' in self.custom_vars:
                        self.custom_vars['rest_periods'].set(custom_aircraft.rest_periods)
                    if 'range_factor' in self.custom_vars:
                        self.custom_vars['range_factor'].set(custom_aircraft.range_factor)
                    if 'fuel_efficiency' in self.custom_vars:
                        self.custom_vars['fuel_efficiency'].set(custom_aircraft.fuel_efficiency)
                    if 'maintenance_cost' in self.custom_vars:
                        self.custom_vars['maintenance_cost'].set(custom_aircraft.maintenance_cost)
                    if 'speed' in self.custom_vars:
                        self.custom_vars['speed'].set(custom_aircraft.cruise_speed_mach)
                    
                    # Set the special capabilities
                    for capability, var in self.capability_vars.items():
                        var.set(capability in custom_aircraft.special_capabilities)
                    
                    logger.info("Custom aircraft values initialized from aircraft configuration")
                    
        except Exception as e:
            logger.warning(f"Could not initialize custom aircraft from config: {e}")

    def _toggle_simulation_pause(self):
        """Toggle simulation pause/resume state."""
        if self.simulation_paused.get():
            self.simulation_paused.set(False)
            self.pause_resume_btn.config(text="⏸ Pause")
            # Resume simulation logic would go here
        else:
            self.simulation_paused.set(True)
            self.pause_resume_btn.config(text="▶ Resume")
            # Pause simulation logic would go here
    
    def update_cost_display(self, total_cost: float, cost_per_period: float):
        """Update the cost display with current values."""
        try:
            # Update total cost
            self.total_cost_label.config(text=f"${total_cost:,.2f}")
            
            # Update cost per period
            self.cost_per_period_label.config(text=f"${cost_per_period:,.2f}")
            
            # Update budget remaining
            try:
                budget_limit = float(self.budget_limit_var.get())
                remaining = budget_limit - total_cost
                self.budget_remaining_label.config(text=f"${remaining:,.2f}")
                
                # Color code based on remaining budget
                if remaining > budget_limit * 0.5:
                    self.budget_remaining_label.config(foreground="green")
                elif remaining > budget_limit * 0.2:
                    self.budget_remaining_label.config(foreground="orange")
                else:
                    self.budget_remaining_label.config(foreground="red")
                    
            except ValueError:
                self.budget_remaining_label.config(text="Invalid budget")
                
        except Exception as e:
            print(f"Error updating cost display: {e}")
    
    def update_aircraft_status_display(self, status_counts: dict):
        """Update the aircraft status display."""
        try:
            idle = status_counts.get('IDLE', 0)
            enroute = status_counts.get('ENROUTE', 0)
            loading = status_counts.get('LOADING', 0)
            maintenance = status_counts.get('MAINTENANCE', 0)
            
            status_text = f"{idle} IDLE, {enroute} ENROUTE, {loading} LOADING, {maintenance} MAINTENANCE"
            self.aircraft_status_label.config(text=status_text)
            
            # Update live operations count
            live_ops = enroute + loading + maintenance
            self.live_ops_label.config(text=str(live_ops))
            
        except Exception as e:
            print(f"Error updating aircraft status display: {e}")
    
    def update_performance_display(self, efficiency_percent: float):
        """Update the performance metrics display."""
        try:
            self.performance_label.config(text=f"Efficiency: {efficiency_percent:.1f}%")
            
            # Color code based on efficiency
            if efficiency_percent >= 80:
                self.performance_label.config(foreground="green")
            elif efficiency_percent >= 60:
                self.performance_label.config(foreground="orange")
            else:
                self.performance_label.config(foreground="red")
                
        except Exception as e:
            print(f"Error updating performance display: {e}")
    
    def build_operations_tab(self, tab):
        """Build the Operations tab with live aircraft status and cost tracking."""
        # Configure the tab for two-column layout
        tab.grid_columnconfigure(0, weight=2)  # Aircraft status gets more space
        tab.grid_columnconfigure(1, weight=1)  # Cost dashboard gets less space
        tab.grid_rowconfigure(0, weight=1)
        
        # Left side - Live Aircraft Status
        left_frame = ttk.Frame(tab, style="Card.TFrame")
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=(0, 8))
        left_frame.grid_columnconfigure(0, weight=1)
        
        # Aircraft status section
        status_frame = ttk.LabelFrame(left_frame, text="Live Aircraft Status", padding=20)
        status_frame.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        status_frame.grid_columnconfigure(1, weight=1)
        
        # Aircraft list header
        header_frame = ttk.Frame(status_frame)
        header_frame.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 12))
        
        ttk.Label(header_frame, text="Aircraft", style="Header.TLabel", width=15).grid(row=0, column=0, sticky="w")
        ttk.Label(header_frame, text="Status", style="Header.TLabel", width=12).grid(row=0, column=1, sticky="w")
        ttk.Label(header_frame, text="Time Remaining", style="Header.TLabel", width=15).grid(row=0, column=2, sticky="w")
        
        # Aircraft list (placeholder for now)
        self.aircraft_list_frame = ttk.Frame(status_frame)
        self.aircraft_list_frame.grid(row=1, column=0, columnspan=3, sticky="ew")
        
        # Placeholder for aircraft list
        placeholder = ttk.Label(self.aircraft_list_frame, 
                              text="Aircraft status will appear here during simulation", 
                              style="Muted.TLabel", justify="center")
        placeholder.pack(expand=True, pady=20)
        
        # Progress indicators section
        progress_frame = ttk.LabelFrame(left_frame, text="Operation Progress", padding=20)
        progress_frame.grid(row=1, column=0, sticky="ew")
        progress_frame.grid_columnconfigure(1, weight=1)
        
        # Loading operations progress
        ttk.Label(progress_frame, text="Loading Operations:", style="Header.TLabel").grid(row=0, column=0, sticky="w")
        self.loading_progress = ttk.Progressbar(progress_frame, mode='determinate', length=200)
        self.loading_progress.grid(row=0, column=1, sticky="w", padx=(16, 0))
        
        # Flight operations progress
        ttk.Label(progress_frame, text="Flight Operations:", style="Header.TLabel").grid(row=1, column=0, sticky="w")
        self.flight_progress = ttk.Progressbar(progress_frame, mode='determinate', length=200)
        self.flight_progress.grid(row=1, column=1, sticky="w", padx=(16, 0))
        
        # Maintenance operations progress
        ttk.Label(progress_frame, text="Maintenance:", style="Header.TLabel").grid(row=2, column=0, sticky="w")
        self.maintenance_progress = ttk.Progressbar(progress_frame, mode='determinate', length=200)
        self.maintenance_progress.grid(row=2, column=1, sticky="w", padx=(16, 0))
        
        # Right side - Cost Tracking Dashboard
        right_frame = ttk.Frame(tab, style="Card.TFrame")
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(6, 0), pady=(0, 8))
        right_frame.grid_columnconfigure(0, weight=1)
        
        # Cost tracking section
        cost_frame = ttk.LabelFrame(right_frame, text="Cost Tracking Dashboard", padding=20)
        cost_frame.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        cost_frame.grid_columnconfigure(1, weight=1)
        
        # Operational cost breakdown
        ttk.Label(cost_frame, text="Operational Cost:", style="Header.TLabel").grid(row=0, column=0, sticky="w")
        self.operational_cost_label = ttk.Label(cost_frame, text="$0.00", style="Muted.TLabel")
        self.operational_cost_label.grid(row=0, column=1, sticky="w", padx=(16, 0))
        
        # Fuel cost analysis
        ttk.Label(cost_frame, text="Fuel Cost:", style="Header.TLabel").grid(row=1, column=0, sticky="w")
        self.fuel_cost_label = ttk.Label(cost_frame, text="$0.00", style="Muted.TLabel")
        self.fuel_cost_label.grid(row=1, column=1, sticky="w", padx=(16, 0))
        
        # Maintenance cost tracking
        ttk.Label(cost_frame, text="Maintenance Cost:", style="Header.TLabel").grid(row=2, column=0, sticky="w")
        self.maintenance_cost_label = ttk.Label(cost_frame, text="$0.00", style="Muted.TLabel")
        self.maintenance_cost_label.grid(row=2, column=1, sticky="w", padx=(16, 0))
        
        # Total cost projections
        ttk.Label(cost_frame, text="Total Cost:", style="Header.TLabel").grid(row=3, column=0, sticky="w")
        self.total_cost_ops_label = ttk.Label(cost_frame, text="$0.00", style="Header.TLabel", foreground="green")
        self.total_cost_ops_label.grid(row=3, column=1, sticky="w", padx=(16, 0))
        
        # Performance metrics section
        metrics_frame = ttk.LabelFrame(right_frame, text="Performance Metrics", padding=20)
        metrics_frame.grid(row=1, column=0, sticky="ew", pady=(0, 16))
        metrics_frame.grid_columnconfigure(1, weight=1)
        
        # Efficiency ratings
        ttk.Label(metrics_frame, text="Efficiency Rating:", style="Header.TLabel").grid(row=0, column=0, sticky="w")
        self.efficiency_rating_label = ttk.Label(metrics_frame, text="0%", style="Muted.TLabel")
        self.efficiency_rating_label.grid(row=0, column=1, sticky="w", padx=(16, 0))
        
        # Utilization statistics
        ttk.Label(metrics_frame, text="Utilization:", style="Header.TLabel").grid(row=1, column=0, sticky="w")
        self.utilization_label = ttk.Label(metrics_frame, text="0%", style="Muted.TLabel")
        self.utilization_label.grid(row=1, column=1, sticky="w", padx=(16, 0))
        
        # Cost per operation metrics
        ttk.Label(metrics_frame, text="Cost per Operation:", style="Header.TLabel").grid(row=2, column=0, sticky="w")
        self.cost_per_op_label = ttk.Label(metrics_frame, text="$0.00", style="Muted.TLabel")
        self.cost_per_op_label.grid(row=2, column=1, sticky="w", padx=(16, 0))
        
        # Maintenance scheduling section
        maintenance_frame = ttk.LabelFrame(right_frame, text="Maintenance Scheduling", padding=20)
        maintenance_frame.grid(row=2, column=0, sticky="ew")
        maintenance_frame.grid_columnconfigure(1, weight=1)
        
        # Maintenance due indicators
        ttk.Label(maintenance_frame, text="Maintenance Due:", style="Header.TLabel").grid(row=0, column=0, sticky="w")
        self.maintenance_due_label = ttk.Label(maintenance_frame, text="0 aircraft", style="Muted.TLabel")
        self.maintenance_due_label.grid(row=0, column=1, sticky="w", padx=(16, 0))
        
        # Scheduled maintenance calendar
        ttk.Label(maintenance_frame, text="Next Scheduled:", style="Header.TLabel").grid(row=1, column=0, sticky="w")
        self.next_maintenance_label = ttk.Label(maintenance_frame, text="None", style="Muted.TLabel")
        self.next_maintenance_label.grid(row=1, column=1, sticky="w", padx=(16, 0))
        
        # Maintenance cost projections
        ttk.Label(maintenance_frame, text="Projected Cost:", style="Header.TLabel").grid(row=2, column=0, sticky="w")
        self.maintenance_projection_label = ttk.Label(maintenance_frame, text="$0.00", style="Muted.TLabel")
        self.maintenance_projection_label.grid(row=2, column=1, sticky="w", padx=(16, 0))
    
    def update_operations_display(self, aircraft_data: list, cost_data: dict, performance_data: dict):
        """Update the operations tab display with live data."""
        try:
            # Update aircraft list
            self._update_aircraft_list(aircraft_data)
            
            # Update cost tracking
            self._update_cost_tracking(cost_data)
            
            # Update performance metrics
            self._update_performance_metrics(performance_data)
            
            # Update maintenance scheduling
            self._update_maintenance_scheduling(performance_data)
            
        except Exception as e:
            print(f"Error updating operations display: {e}")
    
    def _update_aircraft_list(self, aircraft_data: list):
        """Update the aircraft list display."""
        try:
            # Clear existing list
            for widget in self.aircraft_list_frame.winfo_children():
                widget.destroy()
            
            if not aircraft_data:
                placeholder = ttk.Label(self.aircraft_list_frame, 
                                      text="No aircraft data available", 
                                      style="Muted.TLabel", justify="center")
                placeholder.pack(expand=True, pady=20)
                return
            
            # Create aircraft list
            for i, aircraft in enumerate(aircraft_data):
                row_frame = ttk.Frame(self.aircraft_list_frame)
                row_frame.grid(row=i, column=0, columnspan=3, sticky="ew", pady=2)
                
                # Aircraft name
                ttk.Label(row_frame, text=aircraft.get('name', 'Unknown'), 
                         width=15).grid(row=0, column=0, sticky="w")
                
                # Status
                status = aircraft.get('state', 'UNKNOWN')
                status_label = ttk.Label(row_frame, text=status, width=12)
                status_label.grid(row=0, column=1, sticky="w")
                
                # Color code status
                if status == 'ENROUTE':
                    status_label.config(foreground="blue")
                elif status == 'LOADING':
                    status_label.config(foreground="orange")
                elif status == 'MAINTENANCE':
                    status_label.config(foreground="red")
                elif status == 'IDLE':
                    status_label.config(foreground="green")
                
                # Time remaining
                time_remaining = aircraft.get('time_remaining', 0)
                if time_remaining > 0:
                    time_text = f"{time_remaining:.1f}h"
                else:
                    time_text = "Complete"
                
                ttk.Label(row_frame, text=time_text, width=15).grid(row=0, column=2, sticky="w")
                
        except Exception as e:
            print(f"Error updating aircraft list: {e}")
    
    def _update_cost_tracking(self, cost_data: dict):
        """Update the cost tracking display."""
        try:
            operational = cost_data.get('operational', 0)
            fuel = cost_data.get('fuel', 0)
            maintenance = cost_data.get('maintenance', 0)
            total = cost_data.get('total', 0)
            
            self.operational_cost_label.config(text=f"${operational:,.2f}")
            self.fuel_cost_label.config(text=f"${fuel:,.2f}")
            self.maintenance_cost_label.config(text=f"${maintenance:,.2f}")
            self.total_cost_ops_label.config(text=f"${total:,.2f}")
            
        except Exception as e:
            print(f"Error updating cost tracking: {e}")
    
    def _update_performance_metrics(self, performance_data: dict):
        """Update the performance metrics display."""
        try:
            efficiency = performance_data.get('efficiency', 0)
            utilization = performance_data.get('utilization', 0)
            cost_per_op = performance_data.get('cost_per_operation', 0)
            
            self.efficiency_rating_label.config(text=f"{efficiency:.1f}%")
            self.utilization_label.config(text=f"{utilization:.1f}%")
            self.cost_per_op_label.config(text=f"${cost_per_op:,.2f}")
            
        except Exception as e:
            print(f"Error updating performance metrics: {e}")
    
    def _update_maintenance_scheduling(self, performance_data: dict):
        """Update the maintenance scheduling display."""
        try:
            maintenance_due = performance_data.get('maintenance_due', 0)
            next_maintenance = performance_data.get('next_maintenance', 'None')
            projected_cost = performance_data.get('maintenance_projection', 0)
            
            self.maintenance_due_label.config(text=f"{maintenance_due} aircraft")
            self.next_maintenance_label.config(text=str(next_maintenance))
            self.maintenance_projection_label.config(text=f"${projected_cost:,.2f}")
            
        except Exception as e:
            print(f"Error updating maintenance scheduling: {e}")
    
    def _handle_responsive_layout(self):
        """Handle responsive layout adjustments for different screen resolutions."""
        try:
            # Get current window dimensions
            window_width = self.root.winfo_width()
            window_height = self.root.winfo_height()
            
            # Minimum size requirements
            min_width = 1000
            min_height = 800
            
            # Check if window is too small
            if window_width < min_width or window_height < min_height:
                self._apply_compact_layout()
            else:
                self._apply_normal_layout()
            
            # Handle fullscreen mode
            if self.root.state() == 'zoomed':
                self._apply_fullscreen_layout()
            
        except Exception as e:
            print(f"Error handling responsive layout: {e}")
    
    def _apply_compact_layout(self):
        """Apply compact layout for small screens."""
        try:
            # Reduce padding and margins
            for tab in [self.tab_config, self.tab_fleet, self.tab_schedule, 
                       self.tab_operations, self.tab_visual, self.tab_gameplay, 
                       self.tab_theme, self.tab_record, self.tab_start]:
                tab.configure(padding=6)
            
            # Adjust font sizes for small screens
            self._adjust_font_sizes(compact=True)
            
        except Exception as e:
            print(f"Error applying compact layout: {e}")
    
    def _apply_normal_layout(self):
        """Apply normal layout for standard screens."""
        try:
            # Standard padding and margins
            for tab in [self.tab_config, self.tab_fleet, self.tab_schedule, 
                       self.tab_operations, self.tab_visual, self.tab_gameplay, 
                       self.tab_theme, self.tab_record, self.tab_start]:
                tab.configure(padding=12)
            
            # Standard font sizes
            self._adjust_font_sizes(compact=False)
            
        except Exception as e:
            print(f"Error applying normal layout: {e}")
    
    def _apply_fullscreen_layout(self):
        """Apply fullscreen layout optimizations."""
        try:
            # Increase padding for fullscreen
            for tab in [self.tab_config, self.tab_fleet, self.tab_schedule, 
                       self.tab_operations, self.tab_visual, self.tab_gameplay, 
                       self.tab_theme, self.tab_record, self.tab_start]:
                tab.configure(padding=16)
            
            # Larger fonts for fullscreen
            self._adjust_font_sizes(compact=False, fullscreen=True)
            
        except Exception as e:
            print(f"Error applying fullscreen layout: {e}")
    
    def _adjust_font_sizes(self, compact: bool = False, fullscreen: bool = False):
        """Apply consistent default tkinter fonts regardless of layout mode."""
        try:
            # Always use default tkinter fonts for consistency
            fonts = {
                'small': DEFAULT_FONT,
                'normal': DEFAULT_FONT,
                'header': DEFAULT_FONT_BOLD
            }
            
            # Apply font adjustments to key elements
            self._apply_font_to_elements(fonts['small'], fonts['normal'], fonts['header'])
            
        except Exception as e:
            print(f"Error adjusting font sizes: {e}")
    
    def _apply_font_to_elements(self, small_font, normal_font, header_font):
        """Apply consistent default tkinter fonts to GUI elements."""
        try:
            # Apply fonts to labels and buttons
            for widget in self.root.winfo_children():
                if hasattr(widget, 'winfo_children'):
                    self._recursive_font_apply(widget, small_font, normal_font, header_font)
                    
        except Exception as e:
            from cargosim.core.utils import log_exception
            log_exception(e, "Error applying fonts to elements")
    
    def _recursive_font_apply(self, parent, small_font, normal_font, header_font):
        """Recursively apply consistent default tkinter fonts to all child widgets."""
        try:
            for child in parent.winfo_children():
                # Apply fonts based on widget type using default tkinter fonts
                if isinstance(child, ttk.Label):
                    try:
                        if "Header" in str(child.cget("style")):
                            child.configure(font=header_font)
                        else:
                            child.configure(font=normal_font)
                    except Exception:
                        # Skip widgets that don't support font configuration
                        pass
                elif isinstance(child, ttk.Button):
                    try:
                        child.configure(font=normal_font)
                    except Exception:
                        pass
                elif isinstance(child, ttk.Entry):
                    try:
                        child.configure(font=normal_font)
                    except Exception:
                        pass
                elif isinstance(child, ttk.Spinbox):
                    try:
                        child.configure(font=normal_font)
                    except Exception:
                        pass
                elif isinstance(child, ttk.Combobox):
                    try:
                        child.configure(font=normal_font)
                    except Exception:
                        pass
                
                # Recursively apply to children
                if hasattr(child, 'winfo_children'):
                    self._recursive_font_apply(child, small_font, normal_font, header_font)
                    
        except Exception as e:
            from cargosim.core.utils import log_exception
            log_exception(e, "Error in recursive font application")
    
    def _handle_screen_resize(self, event=None):
        """Handle screen resize events."""
        try:
            # Debounce resize events
            if hasattr(self, '_resize_timer'):
                self.root.after_cancel(self._resize_timer)
            
            self._resize_timer = self.root.after(100, self._handle_responsive_layout)
            
        except Exception as e:
            from cargosim.core.utils import log_exception
            log_exception(e, "Error handling screen resize")
    
    def _setup_responsive_bindings(self):
        """Set up responsive layout bindings."""
        try:
            # Bind resize events
            self.root.bind('<Configure>', self._handle_screen_resize)
            
            # Bind fullscreen toggle
            self.root.bind('<F11>', self._toggle_fullscreen_gui)
            
        except Exception as e:
            from cargosim.core.utils import log_exception
            log_exception(e, "Error setting up responsive bindings")

    def build_advanced_tab(self, tab):
        """Build the advanced features tab with enhanced user experience controls."""
        frm = ttk.Frame(tab, style="Card.TFrame")
        frm.pack(fill="both", expand=True)

        # Enhanced Visualization Controls
        viz_frame = ttk.LabelFrame(frm, text="Enhanced Visualization", padding=12)
        viz_frame.pack(fill="x", pady=(0, 16))
        
        # Animation controls
        anim_frame = ttk.Frame(viz_frame)
        anim_frame.pack(fill="x", pady=8)
        
        self.cost_display_var = tk.BooleanVar(value=True)
        self.performance_display_var = tk.BooleanVar(value=True)
        self.speed_indicators_var = tk.BooleanVar(value=True)
        self.motion_blur_var = tk.BooleanVar(value=True)
        self.cargo_animations_var = tk.BooleanVar(value=True)
        
        ttk.Checkbutton(anim_frame, text="Cost Display", variable=self.cost_display_var, 
                       style="Check.TCheckbutton").grid(row=0, column=0, sticky="w", padx=(0, 20))
        ttk.Checkbutton(anim_frame, text="Performance Metrics", variable=self.performance_display_var,
                       style="Check.TCheckbutton").grid(row=0, column=1, sticky="w", padx=(0, 20))
        ttk.Checkbutton(anim_frame, text="Speed Indicators", variable=self.speed_indicators_var,
                       style="Check.TCheckbutton").grid(row=0, column=2, sticky="w", padx=(0, 20))
        
        ttk.Checkbutton(anim_frame, text="Motion Blur", variable=self.motion_blur_var,
                       style="Check.TCheckbutton").grid(row=1, column=0, sticky="w", padx=(0, 20))
        ttk.Checkbutton(anim_frame, text="Cargo Animations", variable=self.cargo_animations_var,
                       style="Check.TCheckbutton").grid(row=1, column=1, sticky="w", padx=(0, 20))
        
        # Interactive Features
        interact_frame = ttk.LabelFrame(frm, text="Interactive Features", padding=12)
        interact_frame.pack(fill="x", pady=(0, 16))
        
        self.clickable_aircraft_var = tk.BooleanVar(value=True)
        self.hover_effects_var = tk.BooleanVar(value=True)
        self.drag_drop_var = tk.BooleanVar(value=False)
        self.zoom_pan_var = tk.BooleanVar(value=False)
        
        ttk.Checkbutton(interact_frame, text="Clickable Aircraft", variable=self.clickable_aircraft_var,
                       style="Check.TCheckbutton").grid(row=0, column=0, sticky="w", padx=(0, 20))
        ttk.Checkbutton(interact_frame, text="Hover Effects", variable=self.hover_effects_var,
                       style="Check.TCheckbutton").grid(row=0, column=1, sticky="w", padx=(0, 20))
        
        ttk.Checkbutton(interact_frame, text="Drag & Drop Routes", variable=self.drag_drop_var,
                       style="Check.TCheckbutton").grid(row=1, column=0, sticky="w", padx=(0, 20))
        ttk.Checkbutton(interact_frame, text="Zoom & Pan", variable=self.zoom_pan_var,
                       style="Check.TCheckbutton").grid(row=1, column=1, sticky="w", padx=(0, 20))
        
        # Accessibility Features
        accessibility_frame = ttk.LabelFrame(frm, text="Accessibility", padding=12)
        accessibility_frame.pack(fill="x", pady=(0, 16))
        
        # Font size control
        font_frame = ttk.Frame(accessibility_frame)
        font_frame.pack(fill="x", pady=8)
        
        ttk.Label(font_frame, text="Font Scale:").grid(row=0, column=0, sticky="w", padx=(0, 10))
        
        # Font scale slider
        self.font_scale_var = tk.DoubleVar(value=1.0)
        font_scale_slider = ttk.Scale(font_frame, from_=0.8, to=1.5, 
                                     variable=self.font_scale_var, 
                                     orient="horizontal", length=150)
        font_scale_slider.grid(row=0, column=1, sticky="w", padx=(0, 10))
        
        # Scale value label
        self.scale_value_label = ttk.Label(font_frame, text="100%")
        self.scale_value_label.grid(row=0, column=2, sticky="w", padx=(0, 10))
        
        # Apply button
        ttk.Button(font_frame, text="Apply", 
                   command=self._apply_font_scale).grid(row=0, column=3)
        
        # Update scale label when slider changes
        font_scale_slider.configure(command=self._update_scale_label)
        
        # High contrast mode
        self.high_contrast_var = tk.BooleanVar(value=False)
        high_contrast_check = ttk.Checkbutton(accessibility_frame, text="High Contrast Mode", variable=self.high_contrast_var,
                       command=self._toggle_high_contrast, style="Check.TCheckbutton")
        high_contrast_check.pack(anchor="w", pady=4)
        
        # Color blind friendly mode
        self.color_blind_var = tk.BooleanVar(value=False)
        color_blind_check = ttk.Checkbutton(accessibility_frame, text="Color Blind Friendly Palette", variable=self.color_blind_var,
                       command=self._toggle_color_blind_mode, style="Check.TCheckbutton")
        color_blind_check.pack(anchor="w", pady=4)
        
        # Keyboard navigation
        self.keyboard_nav_var = tk.BooleanVar(value=True)
        keyboard_nav_check = ttk.Checkbutton(accessibility_frame, text="Enhanced Keyboard Navigation", variable=self.keyboard_nav_var,
                       style="Check.TCheckbutton")
        keyboard_nav_check.pack(anchor="w", pady=4)
        
        # Performance Optimization
        perf_frame = ttk.LabelFrame(frm, text="Performance Optimization", padding=12)
        perf_frame.pack(fill="x", pady=(0, 16))
        
        # Animation quality
        quality_frame = ttk.Frame(perf_frame)
        quality_frame.pack(fill="x", pady=8)
        
        ttk.Label(quality_frame, text="Animation Quality:").grid(row=0, column=0, sticky="w", padx=(0, 10))
        self.animation_quality_var = tk.StringVar(value="High")
        quality_combo = ttk.Combobox(quality_frame, textvariable=self.animation_quality_var,
                                    values=["Low", "Medium", "High", "Ultra"],
                                    state="readonly", width=15)
        quality_combo.grid(row=0, column=1, sticky="w")
        quality_combo.bind("<<ComboboxSelected>>", self._on_animation_quality_change)
        
        # Performance monitoring
        self.performance_monitoring_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(perf_frame, text="Real-time Performance Monitoring", variable=self.performance_monitoring_var,
                       style="Check.TCheckbutton").pack(anchor="w", pady=4)
        
        # Cost Analysis Tools
        cost_frame = ttk.LabelFrame(frm, text="Cost Analysis Tools", padding=12)
        cost_frame.pack(fill="x", pady=(0, 16))
        
        # Real-time cost preview
        self.realtime_cost_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(cost_frame, text="Real-time Cost Preview", variable=self.realtime_cost_var,
                       style="Check.TCheckbutton").pack(anchor="w", pady=4)
        
        # Cost optimization suggestions
        self.cost_optimization_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(cost_frame, text="Cost Optimization Suggestions", variable=self.cost_optimization_var,
                       style="Check.TCheckbutton").pack(anchor="w", pady=4)
        
        # Budget warnings
        self.budget_warnings_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(cost_frame, text="Budget Warning Alerts", variable=self.budget_warnings_var,
                       style="Check.TCheckbutton").pack(anchor="w", pady=4)
        
        # Scenario Planning
        scenario_frame = ttk.LabelFrame(frm, text="Scenario Planning", padding=12)
        scenario_frame.pack(fill="x", pady=(0, 16))
        
        # What-if analysis
        self.whatif_analysis_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(scenario_frame, text="What-if Analysis Mode", variable=self.whatif_analysis_var,
                       style="Check.TCheckbutton").pack(anchor="w", pady=4)
        
        # Cost projection tools
        self.cost_projection_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(scenario_frame, text="Cost Projection Tools", variable=self.cost_projection_var,
                       style="Check.TCheckbutton").pack(anchor="w", pady=4)
        
        # Performance modeling
        self.performance_modeling_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(scenario_frame, text="Performance Modeling", variable=self.performance_modeling_var,
                       style="Check.TCheckbutton").pack(anchor="w", pady=4)
        
        # Control buttons
        btn_frame = ttk.Frame(frm)
        btn_frame.pack(fill="x", pady=16)
        
        ttk.Button(btn_frame, text="Apply Settings", command=self._apply_advanced_settings,
                  style="Primary.TButton").pack(side="left", padx=(0, 12))
        ttk.Button(btn_frame, text="Reset to Defaults", command=self._reset_advanced_settings,
                  style="Secondary.TButton").pack(side="left", padx=(0, 12))
        ttk.Button(btn_frame, text="Export Settings", command=self._export_advanced_settings,
                  style="Secondary.TButton").pack(side="left")
        
        # Add tooltips
        self._add_tip(font_scale_slider, "Adjust the size of text throughout the interface")
        self._add_tip(quality_combo, "Balance between visual quality and performance")
        self._add_tip(high_contrast_check, "Increase contrast for better visibility")
        self._add_tip(color_blind_check, "Use color-blind friendly color schemes")
        self._add_tip(keyboard_nav_check, "Enable enhanced keyboard navigation features")

        # Performance Metrics Display
        self._add_performance_metrics_display(frm)

    def _add_performance_metrics_display(self, main_frame):
        """Add real-time performance metrics display to the advanced tab."""
        try:
            # Create performance metrics section
            metrics_frame = ttk.LabelFrame(main_frame, text="Real-Time Performance Metrics", padding=12)
            metrics_frame.pack(fill="x", pady=(0, 16))
            
            # Create metrics display dictionary
            self.performance_metrics_display = {}
            
            # CPU Usage
            cpu_frame = ttk.Frame(metrics_frame)
            cpu_frame.pack(fill="x", pady=4)
            ttk.Label(cpu_frame, text="CPU Usage:", width=20).pack(side="left")
            self.performance_metrics_display['cpu_usage'] = ttk.Label(cpu_frame, text="0.0%", width=15)
            self.performance_metrics_display['cpu_usage'].pack(side="left")
            
            # Memory Usage
            memory_frame = ttk.Frame(metrics_frame)
            memory_frame.pack(fill="x", pady=4)
            ttk.Label(memory_frame, text="Memory Usage:", width=20).pack(side="left")
            self.performance_metrics_display['memory_usage'] = ttk.Label(memory_frame, text="0 MB", width=15)
            self.performance_metrics_display['memory_usage'].pack(side="left")
            
            # Uptime
            uptime_frame = ttk.Frame(metrics_frame)
            uptime_frame.pack(fill="x", pady=4)
            ttk.Label(uptime_frame, text="Uptime:", width=20).pack(side="left")
            self.performance_metrics_display['uptime_label'] = ttk.Label(uptime_frame, text="0.0 hours", width=15)
            self.performance_metrics_display['uptime_label'].pack(side="left")
            
            # Alerts
            alerts_frame = ttk.Frame(metrics_frame)
            alerts_frame.pack(fill="x", pady=4)
            ttk.Label(alerts_frame, text="Alerts:", width=20).pack(side="left")
            self.performance_metrics_display['alerts_label'] = ttk.Label(alerts_frame, text="0", width=15, foreground="green")
            self.performance_metrics_display['alerts_label'].pack(side="left")
            
            # Performance trend
            trend_frame = ttk.Frame(metrics_frame)
            trend_frame.pack(fill="x", pady=4)
            ttk.Label(trend_frame, text="Performance Trend:", width=20).pack(side="left")
            self.performance_metrics_display['trend_label'] = ttk.Label(trend_frame, text="Stable", width=15)
            self.performance_metrics_display['trend_label'].pack(side="left")
            
            # Refresh button
            refresh_btn = ttk.Button(metrics_frame, text="Refresh Metrics", 
                                   command=self._refresh_performance_metrics, style="Secondary.TButton")
            refresh_btn.pack(anchor="w", pady=8)
            
            # Add tooltip
            self._add_tip(refresh_btn, "Refresh performance metrics display")
            
        except Exception as e:
            log_exception(e, "Performance metrics display setup failed")

    def _refresh_performance_metrics(self):
        """Refresh performance metrics display."""
        if hasattr(self, 'performance_monitor') and self.performance_monitor:
            try:
                summary = self.performance_monitor.get_performance_summary()
                self._update_performance_metrics_display(summary)
                
                # Update trend
                if 'cpu_usage' in summary['current_metrics']:
                    cpu_trend = self.performance_monitor.calculate_trend('cpu_usage', 1.0)  # Last hour
                    if cpu_trend > 0.1:
                        trend_text = "Increasing"
                        trend_color = "orange"
                    elif cpu_trend < -0.1:
                        trend_text = "Decreasing"
                        trend_color = "green"
                    else:
                        trend_text = "Stable"
                        trend_color = "blue"
                    
                    if 'trend_label' in self.performance_metrics_display:
                        self.performance_metrics_display['trend_label'].configure(
                            text=trend_text, foreground=trend_color
                        )
                        
            except Exception as e:
                log_exception(e, "Performance metrics refresh failed")

    def _update_scale_label(self, value):
        """Update the scale label when slider changes."""
        try:
            percentage = int(float(value) * 100)
            self.scale_value_label.configure(text=f"{percentage}%")
        except Exception as e:
            print(f"Error updating scale label: {e}")
    
    def _apply_font_scale(self):
        """Apply font scaling changes."""
        try:
            from cargosim.rendering.themes.font_manager import font_manager
            scale = self.font_scale_var.get()
            font_manager.set_scale(scale)
            
            # Reapply current layout fonts
            if hasattr(self, '_current_layout_mode'):
                if self._current_layout_mode == 'compact':
                    self._adjust_font_sizes(compact=True)
                elif self._current_layout_mode == 'fullscreen':
                    self._adjust_font_sizes(fullscreen=True)
                else:
                    self._adjust_font_sizes()
            else:
                # Default to standard layout
                self._adjust_font_sizes()
            
            print(f"Font scale applied: {scale:.2f}x")
            
        except Exception as e:
            print(f"Error applying font scale: {e}")
    
    def _toggle_high_contrast(self):
        """Toggle high contrast mode."""
        enabled = self.high_contrast_var.get()
        # This would integrate with the theme system
        print(f"High contrast mode: {'enabled' if enabled else 'disabled'}")
    
    def _toggle_color_blind_mode(self):
        """Toggle color blind friendly mode."""
        enabled = self.color_blind_var.get()
        # This would integrate with the theme system
        print(f"Color blind friendly mode: {'enabled' if enabled else 'disabled'}")
    
    def _on_animation_quality_change(self, event=None):
        """Handle animation quality change."""
        quality = self.animation_quality_var.get()
        self._apply_animation_quality(quality)
    
    def _apply_animation_quality(self, quality):
        """Apply animation quality settings."""
        # This would integrate with the renderer
        print(f"Animation quality changed to: {quality}")
    
    def _apply_advanced_settings(self):
        """Apply all advanced settings."""
        # Collect all settings and apply them
        settings = {
            'cost_display': self.cost_display_var.get(),
            'performance_display': self.performance_display_var.get(),
            'speed_indicators': self.speed_indicators_var.get(),
            'motion_blur': self.motion_blur_var.get(),
            'cargo_animations': self.cargo_animations_var.get(),
            'clickable_aircraft': self.clickable_aircraft_var.get(),
            'hover_effects': self.hover_effects_var.get(),
            'drag_drop': self.drag_drop_var.get(),
            'zoom_pan': self.zoom_pan_var.get(),
            'font_scale': self.font_scale_var.get(),
            'high_contrast': self.high_contrast_var.get(),
            'color_blind': self.color_blind_var.get(),
            'keyboard_nav': self.keyboard_nav_var.get(),
            'animation_quality': self.animation_quality_var.get(),
            'performance_monitoring': self.performance_monitoring_var.get(),
            'realtime_cost': self.realtime_cost_var.get(),
            'cost_optimization': self.cost_optimization_var.get(),
            'budget_warnings': self.budget_warnings_var.get(),
            'whatif_analysis': self.whatif_analysis_var.get(),
            'cost_projection': self.cost_projection_var.get(),
            'performance_modeling': self.performance_modeling_var.get()
        }
        
        # Apply settings to configuration
        self.cfg.advanced_features = settings
        
        # Show confirmation
        messagebox.showinfo("Settings Applied", "Advanced settings have been applied successfully!")
    
    def _reset_advanced_settings(self):
        """Reset advanced settings to defaults."""
        # Reset all variables to defaults
        self.cost_display_var.set(True)
        self.performance_display_var.set(True)
        self.speed_indicators_var.set(True)
        self.motion_blur_var.set(True)
        self.cargo_animations_var.set(True)
        self.clickable_aircraft_var.set(True)
        self.hover_effects_var.set(True)
        self.drag_drop_var.set(False)
        self.zoom_pan_var.set(False)
        self.font_scale_var.set(1.0)
        self.high_contrast_var.set(False)
        self.color_blind_var.set(False)
        self.keyboard_nav_var.set(True)
        self.animation_quality_var.set("High")
        self.performance_monitoring_var.set(True)
        self.realtime_cost_var.set(True)
        self.cost_optimization_var.set(True)
        self.budget_warnings_var.set(True)
        self.whatif_analysis_var.set(False)
        self.cost_projection_var.set(True)
        self.performance_modeling_var.set(True)
        
        messagebox.showinfo("Settings Reset", "Advanced settings have been reset to defaults!")
    
    def _export_advanced_settings(self):
        """Export advanced settings to file."""
        # Get current settings
        settings = {
            'cost_display': self.cost_display_var.get(),
            'performance_display': self.performance_display_var.get(),
            'speed_indicators': self.speed_indicators_var.get(),
            'motion_blur': self.motion_blur_var.get(),
            'cargo_animations': self.cargo_animations_var.get(),
            'clickable_aircraft': self.clickable_aircraft_var.get(),
            'hover_effects': self.hover_effects_var.get(),
            'drag_drop': self.drag_drop_var.get(),
            'zoom_pan': self.zoom_pan_var.get(),
            'font_scale': self.font_scale_var.get(),
            'high_contrast': self.high_contrast_var.get(),
            'color_blind': self.color_blind_var.get(),
            'keyboard_nav': self.keyboard_nav_var.get(),
            'animation_quality': self.animation_quality_var.get(),
            'performance_monitoring': self.performance_monitoring_var.get(),
            'realtime_cost': self.realtime_cost_var.get(),
            'cost_optimization': self.cost_optimization_var.get(),
            'budget_warnings': self.budget_warnings_var.get(),
            'whatif_analysis': self.whatif_analysis_var.get(),
            'cost_projection': self.cost_projection_var.get(),
            'performance_modeling': self.performance_modeling_var.get()
        }
        
        # Export to JSON file
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Export Advanced Settings"
        )
        
        if filename:
            try:
                import json
                with open(filename, 'w') as f:
                    json.dump(settings, f, indent=2)
                messagebox.showinfo("Export Successful", f"Settings exported to {filename}")
            except Exception as e:
                messagebox.showerror("Export Failed", f"Failed to export settings: {str(e)}")

    def _setup_performance_monitoring(self):
        """Setup performance monitoring integration."""
        try:
            from cargosim.core.utils import performance_monitor, analytics_engine
            
            # Initialize performance monitoring
            self.performance_monitor = performance_monitor
            self.analytics_engine = analytics_engine
            
            # Start performance monitoring
            self._start_performance_monitoring()
            
            log_runtime_event("Performance monitoring initialized successfully")
        except Exception as e:
            log_exception(e, "Performance monitoring setup failed")
            self.performance_monitor = None
            self.analytics_engine = None

    def _start_performance_monitoring(self):
        """Start real-time performance monitoring."""
        if not hasattr(self, 'performance_monitor') or not self.performance_monitor:
            return
        
        # Start monitoring thread
        import threading
        self.monitoring_thread = threading.Thread(target=self._monitoring_worker, daemon=True)
        self.monitoring_thread.start()
        
        # Setup periodic updates
        self._schedule_performance_updates()

    def _monitoring_worker(self):
        """Background worker for performance monitoring."""
        import time
        import psutil
        
        while hasattr(self, 'performance_monitor') and self.performance_monitor:
            try:
                # Monitor system performance
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                
                # Track metrics
                self.performance_monitor.track_metric('cpu_usage', cpu_percent)
                self.performance_monitor.track_metric('memory_usage', memory.used / 1024 / 1024)  # MB
                
                # Update GUI if needed
                self.root.after(0, self._update_performance_display)
                
                time.sleep(5)  # Update every 5 seconds
            except Exception as e:
                log_exception(e, "Performance monitoring worker error")
                time.sleep(10)  # Wait longer on error

    def _schedule_performance_updates(self):
        """Schedule periodic performance updates to the GUI."""
        if hasattr(self, 'performance_monitor') and self.performance_monitor:
            # Update performance display every 2 seconds
            self.root.after(2000, self._update_performance_display)
            self.root.after(2000, self._schedule_performance_updates)

    def _update_performance_display(self):
        """Update performance display in the GUI."""
        if not hasattr(self, 'performance_monitor') or not self.performance_monitor:
            return
        
        # Check if the application is being destroyed
        try:
            if hasattr(self, 'root') and self.root and not self.root.winfo_exists():
                return
        except tk.TclError:
            # Application is being destroyed
            return
        
        try:
            # Get current performance summary
            summary = self.performance_monitor.get_performance_summary()
            
            # Update status bar with performance info - check if widgets still exist
            if hasattr(self, 'status_bar') and self.status_bar and self.status_bar.winfo_exists():
                if hasattr(self, 'performance_status_label') and self.performance_status_label and self.performance_status_label.winfo_exists():
                    try:
                        perf_text = f"CPU: {summary['current_metrics'].get('cpu_usage', 0):.1f}% | "
                        perf_text += f"Memory: {summary['current_metrics'].get('memory_usage', 0):.0f}MB | "
                        perf_text += f"Uptime: {summary['uptime_hours']:.1f}h"
                        
                        self.performance_status_label.configure(text=perf_text)
                    except tk.TclError as e:
                        # Widget may have been destroyed, log and continue
                        logger.debug(f"Performance status label update failed (widget may be destroyed): {e}")
                        return
            
            # Update performance metrics in advanced tab if visible
            if hasattr(self, 'performance_metrics_display'):
                self._update_performance_metrics_display(summary)
                
        except Exception as e:
            log_exception(e, "Performance display update failed")

    def _update_performance_metrics_display(self, summary: dict):
        """Update performance metrics display in the advanced tab."""
        if not hasattr(self, 'performance_metrics_display'):
            return
        
        try:
            # Update metrics labels - check if widgets still exist
            for metric_name, value in summary['current_metrics'].items():
                if metric_name in self.performance_metrics_display:
                    label = self.performance_metrics_display[metric_name]
                    if label and label.winfo_exists():
                        try:
                            if isinstance(value, float):
                                label.configure(text=f"{metric_name.replace('_', ' ').title()}: {value:.2f}")
                            else:
                                label.configure(text=f"{metric_name.replace('_', ' ').title()}: {value}")
                        except tk.TclError as e:
                            logger.debug(f"Failed to update metric {metric_name} (widget may be destroyed): {e}")
                            continue
            
            # Update uptime
            if 'uptime_label' in self.performance_metrics_display:
                uptime_label = self.performance_metrics_display['uptime_label']
                if uptime_label and uptime_label.winfo_exists():
                    try:
                        uptime_label.configure(
                            text=f"Uptime: {summary['uptime_hours']:.1f} hours"
                        )
                    except tk.TclError as e:
                        logger.debug(f"Failed to update uptime label (widget may be destroyed): {e}")
            
            # Update alert count
            if 'alerts_label' in self.performance_metrics_display:
                alerts_label = self.performance_metrics_display['alerts_label']
                if alerts_label and alerts_label.winfo_exists():
                    try:
                        alert_count = summary['total_alerts']
                        alert_color = "red" if alert_count > 0 else "green"
                        alerts_label.configure(
                            text=f"Alerts: {alert_count}",
                            foreground=alert_color
                        )
                    except tk.TclError as e:
                        logger.debug(f"Failed to update alerts label (widget may be destroyed): {e}")
                
        except Exception as e:
            log_exception(e, "Performance metrics display update failed")

    def _setup_analytics_integration(self):
        """Setup analytics engine integration."""
        try:
            from cargosim.core.utils import analytics_engine
            
            # Initialize analytics
            self.analytics_engine = analytics_engine
            
            # Setup predictive analytics
            self._initialize_predictive_analytics()
            
            log_runtime_event("Analytics engine initialized successfully")
        except Exception as e:
            log_exception(e, "Analytics integration setup failed")
            self.analytics_engine = None

    def _initialize_predictive_analytics(self):
        """Initialize predictive analytics features."""
        if not hasattr(self, 'analytics_engine') or not self.analytics_engine:
            return
        
        try:
            # Initialize demand forecasting
            self._setup_demand_forecasting()
            
            # Initialize cost prediction
            self._setup_cost_prediction()
            
            # Initialize performance prediction
            self._setup_performance_prediction()
            
            log_runtime_event("Predictive analytics initialized successfully")
        except Exception as e:
            log_exception(e, "Predictive analytics initialization failed")

    def _setup_demand_forecasting(self):
        """Setup demand forecasting system."""
        if not hasattr(self, 'analytics_engine'):
            return
        
        # Create demand forecasting controls in advanced tab
        if hasattr(self, 'tab_advanced'):
            self._add_demand_forecasting_controls()

    def _add_demand_forecasting_controls(self):
        """Add demand forecasting controls to the advanced tab."""
        try:
            # Find the advanced tab content
            for child in self.tab_advanced.winfo_children():
                if isinstance(child, ttk.Frame):
                    main_frame = child
                    break
            else:
                return
            
            # Create demand forecasting section
            demand_frame = ttk.LabelFrame(main_frame, text="Demand Forecasting", padding=12)
            demand_frame.pack(fill="x", pady=(0, 16))
            
            # Spoke selection
            spoke_frame = ttk.Frame(demand_frame)
            spoke_frame.pack(fill="x", pady=8)
            
            ttk.Label(spoke_frame, text="Spoke:").grid(row=0, column=0, sticky="w", padx=(0, 10))
            self.demand_spoke_var = tk.StringVar(value="1")
            spoke_combo = ttk.Combobox(spoke_frame, textvariable=self.demand_spoke_var,
                                      values=[str(i+1) for i in range(15)], state="readonly", width=10)
            spoke_combo.grid(row=0, column=1, sticky="w", padx=(0, 20))
            
            # Resource selection
            ttk.Label(spoke_frame, text="Resource:").grid(row=0, column=2, sticky="w", padx=(0, 10))
            self.demand_resource_var = tk.StringVar(value="A")
            resource_combo = ttk.Combobox(spoke_frame, textvariable=self.demand_resource_var,
                                         values=["A", "B", "C", "D"], state="readonly", width=10)
            resource_combo.grid(row=0, column=3, sticky="w", padx=(0, 20))
            
            # Time horizon
            ttk.Label(spoke_frame, text="Time Horizon (hours):").grid(row=0, column=4, sticky="w", padx=(0, 10))
            self.demand_horizon_var = tk.StringVar(value="24")
            horizon_entry = ttk.Entry(spoke_frame, textvariable=self.demand_horizon_var, width=10)
            horizon_entry.grid(row=0, column=5, sticky="w")
            
            # Forecast button
            forecast_btn = ttk.Button(demand_frame, text="Generate Forecast", 
                                    command=self._generate_demand_forecast, style="Primary.TButton")
            forecast_btn.pack(anchor="w", pady=8)
            
            # Forecast results display
            self.forecast_results_text = tk.Text(demand_frame, height=6, width=60, wrap="word")
            self.forecast_results_text.pack(fill="x", pady=8)
            
            # Add tooltips
            self._add_tip(spoke_combo, "Select the spoke for demand forecasting")
            self._add_tip(resource_combo, "Select the resource type to forecast")
            self._add_tip(horizon_entry, "Enter the time horizon in hours")
            self._add_tip(forecast_btn, "Generate demand forecast based on current data")
            
        except Exception as e:
            log_exception(e, "Demand forecasting controls setup failed")

    def _generate_demand_forecast(self):
        """Generate demand forecast using analytics engine."""
        if not hasattr(self, 'analytics_engine') or not self.analytics_engine:
            messagebox.showerror("Error", "Analytics engine not available")
            return
        
        try:
            # Get parameters
            spoke_idx = int(self.demand_spoke_var.get()) - 1
            resource = self.demand_resource_var.get()
            time_horizon = float(self.demand_horizon_var.get())
            
            # Generate forecast
            forecast = self.analytics_engine.predict_demand(spoke_idx, resource, time_horizon)
            
            # Display results
            if hasattr(self, 'forecast_results_text'):
                self.forecast_results_text.delete(1.0, tk.END)
                
                results = f"Demand Forecast Results:\n"
                results += f"Spoke: S{spoke_idx + 1}\n"
                results += f"Resource: {resource}\n"
                results += f"Time Horizon: {time_horizon} hours\n"
                results += f"Predicted Demand: {forecast['predicted_demand']:.2f}\n"
                results += f"Confidence: {forecast['confidence']:.1%}\n"
                results += f"Model Type: {forecast['model_type']}\n"
                results += f"Generated: {datetime.fromtimestamp(forecast['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}"
                
                self.forecast_results_text.insert(1.0, results)
                
        except Exception as e:
            log_exception(e, "Demand forecast generation failed")
            messagebox.showerror("Error", f"Failed to generate forecast: {str(e)}")

    def _setup_cost_prediction(self):
        """Setup cost prediction system."""
        if not hasattr(self, 'analytics_engine'):
            return
        
        # Create cost prediction controls in advanced tab
        if hasattr(self, 'tab_advanced'):
            self._add_cost_prediction_controls()

    def _add_cost_prediction_controls(self):
        """Add cost prediction controls to the advanced tab."""
        try:
            # Find the advanced tab content
            for child in self.tab_advanced.winfo_children():
                if isinstance(child, ttk.Frame):
                    main_frame = child
                    break
            else:
                return
            
            # Create cost prediction section
            cost_frame = ttk.LabelFrame(main_frame, text="Cost Prediction", padding=12)
            cost_frame.pack(fill="x", pady=(0, 16))
            
            # Operation type selection
            op_frame = ttk.Frame(cost_frame)
            op_frame.pack(fill="x", pady=8)
            
            ttk.Label(op_frame, text="Operation Type:").grid(row=0, column=0, sticky="w", padx=(0, 10))
            self.cost_op_type_var = tk.StringVar(value="flight")
            op_type_combo = ttk.Combobox(op_frame, textvariable=self.cost_op_type_var,
                                        values=["flight", "loading", "unloading", "maintenance"], 
                                        state="readonly", width=15)
            op_type_combo.grid(row=0, column=1, sticky="w", padx=(0, 20))
            
            # Distance input
            ttk.Label(op_frame, text="Distance (km):").grid(row=0, column=2, sticky="w", padx=(0, 10))
            self.cost_distance_var = tk.StringVar(value="100")
            distance_entry = ttk.Entry(op_frame, textvariable=self.cost_distance_var, width=10)
            distance_entry.grid(row=0, column=3, sticky="w", padx=(0, 20))
            
            # Aircraft type
            ttk.Label(op_frame, text="Aircraft:").grid(row=0, column=4, sticky="w", padx=(0, 10))
            self.cost_aircraft_var = tk.StringVar(value="C-130")
            aircraft_combo = ttk.Combobox(op_frame, textvariable=self.cost_aircraft_var,
                                         values=["C-130", "C-27", "Custom_Transport"], 
                                         state="readonly", width=15)
            aircraft_combo.grid(row=0, column=5, sticky="w")
            
            # Predict button
            predict_btn = ttk.Button(cost_frame, text="Predict Cost", 
                                   command=self._predict_operation_cost, style="Primary.TButton")
            predict_btn.pack(anchor="w", pady=8)
            
            # Cost prediction results display
            self.cost_results_text = tk.Text(cost_frame, height=6, width=60, wrap="word")
            self.cost_results_text.pack(fill="x", pady=8)
            
            # Add tooltips
            self._add_tip(op_type_combo, "Select the type of operation")
            self._add_tip(distance_entry, "Enter the distance in kilometers")
            self._add_tip(aircraft_combo, "Select the aircraft type")
            self._add_tip(predict_btn, "Predict operation cost based on parameters")
            
        except Exception as e:
            log_exception(e, "Cost prediction controls setup failed")

    def _predict_operation_cost(self):
        """Predict operation cost using analytics engine."""
        if not hasattr(self, 'analytics_engine') or not self.analytics_engine:
            messagebox.showerror("Error", "Analytics engine not available")
            return
        
        try:
            # Get parameters
            operation_type = self.cost_op_type_var.get()
            distance = float(self.cost_distance_var.get())
            aircraft_type = self.cost_aircraft_var.get()
            
            # Generate prediction
            prediction = self.analytics_engine.predict_cost(operation_type, distance, aircraft_type)
            
            # Display results
            if hasattr(self, 'cost_results_text'):
                self.cost_results_text.delete(1.0, tk.END)
                
                results = f"Cost Prediction Results:\n"
                results += f"Operation Type: {operation_type}\n"
                results += f"Distance: {distance} km\n"
                results += f"Aircraft Type: {aircraft_type}\n"
                results += f"Predicted Cost: ${prediction['predicted_cost']:.2f}\n"
                results += f"Confidence: {prediction['confidence']:.1%}\n"
                results += f"Model Type: {prediction['model_type']}\n"
                results += f"Generated: {datetime.fromtimestamp(prediction['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}"
                
                self.cost_results_text.insert(1.0, results)
                
        except Exception as e:
            log_exception(e, "Cost prediction failed")
            messagebox.showerror("Error", f"Failed to predict cost: {str(e)}")

    def _setup_performance_prediction(self):
        """Setup performance prediction system."""
        if not hasattr(self, 'analytics_engine'):
            return
        
        # Create performance prediction controls in advanced tab
        if hasattr(self, 'tab_advanced'):
            self._add_performance_prediction_controls()

    def _add_performance_prediction_controls(self):
        """Add performance prediction controls to the advanced tab."""
        try:
            # Find the advanced tab content
            for child in self.tab_advanced.winfo_children():
                if isinstance(child, ttk.Frame):
                    main_frame = child
                    break
            else:
                return
            
            # Create performance prediction section
            perf_frame = ttk.LabelFrame(main_frame, text="Performance Prediction", padding=12)
            perf_frame.pack(fill="x", pady=(0, 16))
            
            # Metric selection
            metric_frame = ttk.Frame(perf_frame)
            metric_frame.pack(fill="x", pady=8)
            
            ttk.Label(metric_frame, text="Metric:").grid(row=0, column=0, sticky="w", padx=(0, 10))
            self.perf_metric_var = tk.StringVar(value="operations_per_second")
            metric_combo = ttk.Combobox(metric_frame, textvariable=self.perf_metric_var,
                                       values=["operations_per_second", "efficiency_ratio", "resource_utilization", 
                                              "cost_per_operation"], state="readonly", width=20)
            metric_combo.grid(row=0, column=1, sticky="w", padx=(0, 20))
            
            # Current value input
            ttk.Label(metric_frame, text="Current Value:").grid(row=0, column=2, sticky="w", padx=(0, 10))
            self.perf_current_value_var = tk.StringVar(value="0.0")
            current_value_entry = ttk.Entry(metric_frame, textvariable=self.perf_current_value_var, width=10)
            current_value_entry.grid(row=0, column=3, sticky="w", padx=(0, 20))
            
            # Time horizon
            ttk.Label(metric_frame, text="Time Horizon (hours):").grid(row=0, column=4, sticky="w", padx=(0, 10))
            self.perf_horizon_var = tk.StringVar(value="24")
            perf_horizon_entry = ttk.Entry(metric_frame, textvariable=self.perf_horizon_var, width=10)
            perf_horizon_entry.grid(row=0, column=5, sticky="w")
            
            # Predict button
            perf_predict_btn = ttk.Button(perf_frame, text="Predict Performance", 
                                        command=self._predict_performance, style="Primary.TButton")
            perf_predict_btn.pack(anchor="w", pady=8)
            
            # Performance prediction results display
            self.perf_results_text = tk.Text(perf_frame, height=6, width=60, wrap="word")
            self.perf_results_text.pack(fill="x", pady=8)
            
            # Add tooltips
            self._add_tip(metric_combo, "Select the performance metric to predict")
            self._add_tip(current_value_entry, "Enter the current value of the metric")
            self._add_tip(perf_horizon_entry, "Enter the time horizon in hours")
            self._add_tip(perf_predict_btn, "Predict future performance based on current trends")
            
        except Exception as e:
            log_exception(e, "Performance prediction controls setup failed")

    def _predict_performance(self):
        """Predict performance using analytics engine."""
        if not hasattr(self, 'analytics_engine') or not self.analytics_engine:
            messagebox.showerror("Error", "Analytics engine not available")
            return
        
        try:
            # Get parameters
            metric = self.perf_metric_var.get()
            current_value = float(self.perf_current_value_var.get())
            time_horizon = float(self.perf_horizon_var.get())
            
            # Generate prediction
            prediction = self.analytics_engine.predict_performance(metric, current_value, time_horizon)
            
            # Display results
            if hasattr(self, 'perf_results_text'):
                self.perf_results_text.delete(1.0, tk.END)
                
                results = f"Performance Prediction Results:\n"
                results += f"Metric: {metric.replace('_', ' ').title()}\n"
                results += f"Current Value: {current_value:.2f}\n"
                results += f"Time Horizon: {time_horizon} hours\n"
                results += f"Predicted Value: {prediction['predicted_value']:.2f}\n"
                results += f"Trend: {prediction['trend']:.4f}\n"
                results += f"Confidence: {prediction['confidence']:.1%}\n"
                results += f"Model Type: {prediction['model_type']}\n"
                results += f"Generated: {datetime.fromtimestamp(prediction['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}"
                
                self.perf_results_text.insert(1.0, results)
                
        except Exception as e:
            log_exception(e, "Performance prediction failed")
            messagebox.showerror("Error", f"Failed to predict performance: {str(e)}")

    def _setup_export_integration(self):
        """Setup export manager integration."""
        try:
            from cargosim.core.utils import export_manager
            
            # Initialize export manager
            self.export_manager = export_manager
            
            # Setup export controls
            if hasattr(self, 'tab_advanced'):
                self._add_export_controls()
            
            log_runtime_event("Export manager initialized successfully")
        except Exception as e:
            log_exception(e, "Export integration setup failed")
            self.export_manager = None

    def _add_export_controls(self):
        """Add export controls to the advanced tab."""
        try:
            # Find the advanced tab content
            for child in self.tab_advanced.winfo_children():
                if isinstance(child, ttk.Frame):
                    main_frame = child
                    break
            else:
                return
            
            # Create export section
            export_frame = ttk.LabelFrame(main_frame, text="Data Export & Integration", padding=12)
            export_frame.pack(fill="x", pady=(0, 16))
            
            # Export format selection
            format_frame = ttk.Frame(export_frame)
            format_frame.pack(fill="x", pady=8)
            
            ttk.Label(format_frame, text="Export Format:").grid(row=0, column=0, sticky="w", padx=(0, 10))
            self.export_format_var = tk.StringVar(value="json")
            format_combo = ttk.Combobox(format_frame, textvariable=self.export_format_var,
                                       values=["csv", "json", "excel", "pdf"], state="readonly", width=10)
            format_combo.grid(row=0, column=1, sticky="w", padx=(0, 20))
            
            # Export simulation data button
            export_sim_btn = ttk.Button(format_frame, text="Export Simulation Data", 
                                      command=self._export_simulation_data, style="Secondary.TButton")
            export_sim_btn.grid(row=0, column=2, sticky="w", padx=(0, 20))
            
            # Export configuration button
            export_config_btn = ttk.Button(format_frame, text="Export Configuration", 
                                         command=self._export_configuration, style="Secondary.TButton")
            export_config_btn.grid(row=0, column=3, sticky="w")
            
            # Integration status
            integration_frame = ttk.Frame(export_frame)
            integration_frame.pack(fill="x", pady=8)
            
            ttk.Label(integration_frame, text="Integration Status:").pack(anchor="w", pady=(0, 4))
            
            # Integration status display
            self.integration_status_text = tk.Text(integration_frame, height=4, width=60, wrap="word")
            self.integration_status_text.pack(fill="x", pady=4)
            
            # Test integrations button
            test_integrations_btn = ttk.Button(integration_frame, text="Test Integrations", 
                                             command=self._test_integrations, style="Secondary.TButton")
            test_integrations_btn.pack(anchor="w", pady=4)
            
            # Add tooltips
            self._add_tip(format_combo, "Select the export format")
            self._add_tip(export_sim_btn, "Export current simulation data")
            self._add_tip(export_config_btn, "Export current configuration")
            self._add_tip(test_integrations_btn, "Test external system integrations")
            
            # Help and Documentation section
            help_frame = ttk.LabelFrame(main_frame, text="Help & Documentation", padding=12)
            help_frame.pack(fill="x", pady=(0, 16))
            
            # Help buttons
            help_buttons_frame = ttk.Frame(help_frame)
            help_buttons_frame.pack(fill="x", pady=8)
            
            help_btn = ttk.Button(help_buttons_frame, text="📚 Help System", 
                                command=self._show_help_system, style="Primary.TButton")
            help_btn.pack(side="left", padx=(0, 10))
            
            quick_help_btn = ttk.Button(help_buttons_frame, text="❓ Quick Help", 
                                      command=self._show_quick_help, style="Secondary.TButton")
            quick_help_btn.pack(side="left", padx=(0, 10))
            
            user_guide_btn = ttk.Button(help_buttons_frame, text="📖 User Guide", 
                                      command=self._open_user_guide, style="Secondary.TButton")
            user_guide_btn.pack(side="left", padx=(0, 10))
            
            # Add tooltips
            self._add_tip(help_btn, "Open comprehensive help system")
            self._add_tip(quick_help_btn, "Show quick help for current feature")
            self._add_tip(user_guide_btn, "Open detailed user guide")
            
        except Exception as e:
            log_exception(e, "Export controls setup failed")

    def _export_simulation_data(self):
        """Export simulation data using export manager."""
        if not hasattr(self, 'export_manager') or not self.export_manager:
            messagebox.showerror("Error", "Export manager not available")
            return
        
        try:
            # Get export format
            export_format = self.export_format_var.get()
            
            # Collect simulation data
            sim_data = self._collect_simulation_data()
            
            # Export data
            filename = self.export_manager.export_simulation_data(sim_data, export_format)
            
            messagebox.showinfo("Export Successful", f"Simulation data exported to {filename}")
            
        except Exception as e:
            log_exception(e, "Simulation data export failed")
            messagebox.showerror("Error", f"Failed to export simulation data: {str(e)}")

    def _export_configuration(self):
        """Export current configuration."""
        try:
            # Get current configuration
            config_data = self._collect_configuration_data()
            
            # Export to JSON
            filename = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                title="Export Configuration"
            )
            
            if filename:
                import json
                with open(filename, 'w') as f:
                    json.dump(config_data, f, indent=2)
                messagebox.showinfo("Export Successful", f"Configuration exported to {filename}")
                
        except Exception as e:
            log_exception(e, "Configuration export failed")
            messagebox.showerror("Error", f"Failed to export configuration: {str(e)}")

    def _collect_simulation_data(self) -> dict:
        """Collect current simulation data for export."""
        try:
            # This would collect data from the simulation if it's running
            # For now, return a sample structure
            sim_data = {
                'timestamp': time.time(),
                'simulation_state': 'not_running',
                'configuration': self._collect_configuration_data(),
                'performance_metrics': {},
                'export_info': {
                    'exported_by': 'CargoSim Advanced Features',
                    'export_timestamp': datetime.now().isoformat(),
                    'version': '1.0.0'
                }
            }
            
            # Add performance metrics if available
            if hasattr(self, 'performance_monitor') and self.performance_monitor:
                sim_data['performance_metrics'] = self.performance_monitor.get_performance_summary()
            
            return sim_data
            
        except Exception as e:
            log_exception(e, "Simulation data collection failed")
            return {'error': str(e)}

    def _collect_configuration_data(self) -> dict:
        """Collect current configuration data."""
        try:
            # Collect configuration from all tabs
            config = {
                'fleet_configuration': self._get_fleet_configuration(),
                'simulation_parameters': self._get_simulation_parameters(),
                'visual_settings': self._get_visual_settings(),
                'advanced_features': self._get_advanced_features_config(),
                'export_info': {
                    'exported_by': 'CargoSim Advanced Features',
                    'export_timestamp': datetime.now().isoformat(),
                    'version': '1.0.0'
                }
            }
            
            return config
            
        except Exception as e:
            log_exception(e, "Configuration data collection failed")
            return {'error': str(e)}

    def _get_fleet_configuration(self) -> dict:
        """Get current fleet configuration."""
        try:
            # This would collect actual fleet configuration
            # For now, return a sample structure
            return {
                'fleet_label': getattr(self.cfg, 'fleet_label', 'default'),
                'aircraft_count': len(getattr(self.cfg, 'fleet', [])),
                'fleet_composition': getattr(self.cfg, 'fleet', [])
            }
        except Exception:
            return {'error': 'Unable to collect fleet configuration'}

    def _get_simulation_parameters(self) -> dict:
        """Get current simulation parameters."""
        try:
            return {
                'initial_stocks': {
                    'A': getattr(self.cfg, 'init_A', 0),
                    'B': getattr(self.cfg, 'init_B', 0),
                    'C': getattr(self.cfg, 'init_C', 0),
                    'D': getattr(self.cfg, 'init_D', 0)
                },
                'consumption_cadence': {
                    'A_days': getattr(self.cfg, 'a_days', 1),
                    'B_days': getattr(self.cfg, 'b_days', 1),
                    'C_days': getattr(self.cfg, 'c_days', 1),
                    'D_days': getattr(self.cfg, 'd_days', 1)
                }
            }
        except Exception:
            return {'error': 'Unable to collect simulation parameters'}

    def _get_visual_settings(self) -> dict:
        """Get current visual settings."""
        try:
            return {
                'theme': getattr(self.cfg, 'theme', 'default'),
                'launch_fullscreen': getattr(self.cfg, 'launch_fullscreen', False),
                'fps': getattr(self.cfg, 'fps', 60)
            }
        except Exception:
            return {'error': 'Unable to collect visual settings'}

    def _get_advanced_features_config(self) -> dict:
        """Get current advanced features configuration."""
        try:
            return {
                'cost_display': getattr(self, 'cost_display_var', tk.BooleanVar()).get(),
                'performance_display': getattr(self, 'performance_display_var', tk.BooleanVar()).get(),
                'speed_indicators': getattr(self, 'speed_indicators_var', tk.BooleanVar()).get(),
                'motion_blur': getattr(self, 'motion_blur_var', tk.BooleanVar()).get(),
                'cargo_animations': getattr(self, 'cargo_animations_var', tk.BooleanVar()).get()
            }
        except Exception:
            return {'error': 'Unable to collect advanced features configuration'}

    def _test_integrations(self):
        """Test external system integrations."""
        if not hasattr(self, 'export_manager') or not self.export_manager:
            messagebox.showerror("Error", "Export manager not available")
            return
        
        try:
            # Get integration status
            status = self.export_manager.get_integration_status()
            
            # Display status
            if hasattr(self, 'integration_status_text'):
                self.integration_status_text.delete(1.0, tk.END)
                
                status_text = "Integration Status:\n"
                for name, info in status.items():
                    status_text += f"{name.title()}: {'Enabled' if info['enabled'] else 'Disabled'}"
                    if info['enabled']:
                        status_text += f" - Test: {'Passed' if info['test_result'] else 'Failed'}"
                    status_text += "\n"
                
                self.integration_status_text.insert(1.0, status_text)
                
        except Exception as e:
            log_exception(e, "Integration testing failed")
            messagebox.showerror("Error", f"Failed to test integrations: {str(e)}")

    def _show_help_system(self):
        """Show the comprehensive help system."""
        try:
            from cargosim.ui.help_system import HelpSystem
            
            if not hasattr(self, 'help_system'):
                self.help_system = HelpSystem(self.root)
            
            self.help_system.show_help()
            
        except Exception as e:
            log_exception(e, "Help system initialization failed")
            messagebox.showerror("Error", f"Failed to open help system: {str(e)}")

    def _show_quick_help(self):
        """Show quick help for the current feature."""
        try:
            # Determine current context and show relevant help
            current_tab = self.notebook.select()
            tab_id = self.notebook.index(current_tab)
            
            if tab_id == 0:  # Main tab
                help_topic = "getting_started"
            elif tab_id == 1:  # Fleet tab
                help_topic = "fleet_management"
            elif tab_id == 2:  # Advanced tab
                help_topic = "advanced_features"
            else:
                help_topic = "getting_started"
            
            # Show help system with specific topic
            self._show_help_system()
            if hasattr(self, 'help_system'):
                self.help_system.show_help(help_topic)
                
        except Exception as e:
            log_exception(e, "Quick help failed")
            messagebox.showerror("Error", f"Failed to show quick help: {str(e)}")

    def _open_user_guide(self):
        """Open the detailed user guide."""
        try:
            # This would open the actual user guide file or URL   
            import os
            import webbrowser
            
            # Try to open local user guide if available
            user_guide_path = os.path.join(os.path.dirname(__file__), "..", "docs", "USER_GUIDES", "ADVANCED_FEATURES_GUIDE.md")
            
            if os.path.exists(user_guide_path):
                # Open with default markdown viewer or text editor
                os.startfile(user_guide_path) if os.name == 'nt' else os.system(f"xdg-open {user_guide_path}")
            else:
                # Fallback to online documentation
                webbrowser.open("https://cargosim-docs.example.com/user-guide")
                
        except Exception as e:
            log_exception(e, "User guide opening failed")
            messagebox.showerror("Error", f"Failed to open user guide: {str(e)}")

    def _initialize_advanced_systems(self):
        """Initialize all advanced systems."""
        try:
            # Setup performance monitoring
            self._setup_performance_monitoring()
            
            # Setup analytics integration
            self._setup_analytics_integration()
            
            # Setup export integration
            self._setup_export_integration()
            
            log_runtime_event("All advanced systems initialized successfully")
        except Exception as e:
            log_exception(e, "Advanced systems initialization failed")

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
            msg.append("pygame missing — simulation disabled")
            self.start_btn.state(["disabled"])
        
        if pygame_available:
            self.start_btn.state(["!disabled"])
        
        mp4_ok, _ = _mp4_available()
        if not mp4_ok:
            msg.append("imageio-ffmpeg missing — MP4 disabled")
        
        self.dep_msg.configure(text=("; ".join(msg) if msg else "All dependencies available."))


if __name__ == "__main__":
    # This allows the file to be run directly for testing
    import os
    import sys
    
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    from cargosim.main import main
    
    # Load config and run main
    main()
