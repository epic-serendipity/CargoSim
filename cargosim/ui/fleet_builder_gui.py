"""Visual Fleet Composition Builder GUI for CargoSim."""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, List, Optional, Callable, Any
import json
import math
import logging

from cargosim.ui.fleet_builder import (
    AircraftType, FleetComposition, FleetPreset, 
    AircraftConfigManager, FleetBuilder,
    get_aircraft_config_manager, get_fleet_builder
)

from cargosim.rendering.themes.default_fonts import DEFAULT_FONT, DEFAULT_FONT_BOLD

# Set up logging
logger = logging.getLogger(__name__)

# Error recovery configuration
MAX_RETRY_ATTEMPTS = 3
RETRY_DELAY_MS = 1000  # 1 second

def safe_dict_get(data: Dict[str, Any], key: str, default: Any = None) -> Any:
    """Safely get a value from a dictionary with fallback."""
    try:
        if data is None:
            return default
        return data.get(key, default)
    except (KeyError, TypeError, AttributeError):
        logger.warning(f"Failed to access key '{key}' from data: {type(data)}")
        return default

def safe_list_get(data: List[Any], index: int, default: Any = None) -> Any:
    """Safely get an element from a list with bounds checking."""
    try:
        if data is None or not isinstance(data, list):
            return default
        if 0 <= index < len(data):
            return data[index]
        return default
    except (IndexError, TypeError):
        logger.warning(f"Failed to access index {index} from list: {type(data)}")
        return default

def safe_attr_get(obj: Any, attr: str, default: Any = None) -> Any:
    """Safely get an attribute from an object."""
    try:
        if obj is None:
            return default
        return getattr(obj, attr, default)
    except (AttributeError, TypeError):
        logger.warning(f"Failed to access attribute '{attr}' from object: {type(obj)}")
        return default

def validate_aircraft_info(aircraft_info: Dict[str, Any]) -> bool:
    """Validate aircraft info dictionary structure."""
    if not aircraft_info or not isinstance(aircraft_info, dict):
        return False
    
    required_keys = ['name', 'count', 'capacity', 'total_capacity']
    for key in required_keys:
        if key not in aircraft_info:
            logger.error(f"Missing required key '{key}' in aircraft_info")
            return False
    
    return True

def validate_fleet_summary(summary: Dict[str, Any]) -> bool:
    """Validate fleet summary dictionary structure."""
    if not summary or not isinstance(summary, dict):
        return False
    
    required_keys = ['total_aircraft', 'total_capacity', 'aircraft_breakdown']
    for key in required_keys:
        if key not in summary:
            logger.error(f"Missing required key '{key}' in fleet summary")
            return False
    
    return True

def retry_operation(operation_func, max_attempts: int = MAX_RETRY_ATTEMPTS, 
                   delay_ms: int = RETRY_DELAY_MS, operation_name: str = "Operation"):
    """Retry an operation with exponential backoff."""
    last_exception = None
    
    for attempt in range(max_attempts):
        try:
            return operation_func()
        except Exception as e:
            last_exception = e
            logger.warning(f"{operation_name} attempt {attempt + 1} failed: {e}")
            
            if attempt < max_attempts - 1:
                # Exponential backoff
                wait_time = delay_ms * (2 ** attempt)
                logger.info(f"Retrying {operation_name} in {wait_time}ms...")
                try:
                    import time
                    time.sleep(wait_time / 1000.0)
                except Exception:
                    pass  # Ignore sleep errors
    
    logger.error(f"{operation_name} failed after {max_attempts} attempts")
    raise last_exception

def create_error_dialog(parent, title: str, message: str, error_details: str = None, 
                       retry_callback: Callable = None, close_callback: Callable = None):
    """Create a comprehensive error dialog with retry and recovery options."""
    try:
        dialog = tk.Toplevel(parent)
        dialog.title(f"Error - {title}")
        dialog.geometry("500x400")
        dialog.resizable(False, False)
        dialog.transient(parent)
        dialog.grab_set()
        
        # Error icon and title
        header_frame = ttk.Frame(dialog)
        header_frame.pack(fill="x", padx=20, pady=(20, 10))
        
        # Use tk.Label instead of ttk.Label for font support
        from cargosim.rendering.themes.font_manager import font_manager
        tk.Label(header_frame, text="⚠️", font=font_manager.get_font('icon'), foreground="red").pack()
        tk.Label(header_frame, text=title, font=font_manager.get_font('title', 'bold'), foreground="red").pack()
        
        # Error message
        message_frame = ttk.Frame(dialog)
        message_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        ttk.Label(message_frame, text=message, wraplength=450, justify="center").pack()
        
        # Error details (collapsible)
        if error_details:
            details_frame = ttk.Frame(dialog)
            details_frame.pack(fill="x", padx=20, pady=(0, 10))
            
            details_var = tk.BooleanVar(value=False)
            details_check = ttk.Checkbutton(details_frame, text="Show Error Details", 
                                          variable=details_var, 
                                          command=lambda: toggle_details())
            details_check.pack()
            
            details_text = tk.Text(details_frame, height=6, wrap="word", state="disabled")
            details_text.pack(fill="x", pady=(5, 0))
            
            def toggle_details():
                if details_var.get():
                    details_text.config(state="normal")
                    details_text.delete("1.0", tk.END)
                    details_text.insert("1.0", error_details)
                    details_text.config(state="disabled")
                else:
                    details_text.config(state="normal")
                    details_text.delete("1.0", tk.END)
                    details_text.config(state="disabled")
        
        # Action buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill="x", padx=20, pady=(20, 20))
        
        # Retry button
        if retry_callback:
            retry_btn = ttk.Button(button_frame, text="🔄 Retry", 
                                  command=lambda: [retry_callback(), dialog.destroy()])
            retry_btn.pack(side="left", padx=(0, 10))
        
        # Close button
        close_btn = ttk.Button(button_frame, text="Close", 
                              command=lambda: [close_callback() if close_callback else None, dialog.destroy()])
        close_btn.pack(side="right")
        
        # Center the dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_width() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        return dialog
        
    except Exception as e:
        logger.error(f"Error creating error dialog: {e}")
        # Fallback to simple message box
        messagebox.showerror(title, f"{message}\n\nError: {e}")
        return None


class AircraftPalette(ttk.Frame):
    """Aircraft palette showing available aircraft types for drag and drop."""
    
    def __init__(self, parent, config_manager: AircraftConfigManager, **kwargs):
        super().__init__(parent, **kwargs)
        self.config_manager = config_manager
        self.on_aircraft_selected: Optional[Callable[[str], None]] = None
        
        self._build_ui()
        self._refresh_aircraft_list()
    
    def _build_ui(self):
        """Build the aircraft palette UI."""
        # Header
        header_frame = ttk.Frame(self)
        header_frame.pack(fill="x", padx=8, pady=(8, 4))
        
        from cargosim.rendering.themes.font_manager import font_manager
        ttk.Label(header_frame, text="Available Aircraft", style="Header.TLabel", 
                 font=font_manager.get_font('header', 'bold')).pack(side="left")
        
        # Refresh button
        refresh_btn = ttk.Button(header_frame, text="🔄", width=3, 
                               command=self._reload_and_refresh)
        refresh_btn.pack(side="right")
        
        # Add tooltip to refresh button
        self._add_tooltip(refresh_btn, "Reload aircraft configuration and refresh list")
        
        # Aircraft list
        self.aircraft_frame = ttk.Frame(self)
        self.aircraft_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        
        # Scrollable canvas for aircraft
        self.canvas = tk.Canvas(self.aircraft_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.aircraft_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            self._on_scrollable_frame_configure
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Bind mouse wheel scrolling
        def _on_mousewheel(event):
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
        # Bind mouse wheel events for Windows
        self.canvas.bind("<MouseWheel>", _on_mousewheel)
        # Bind mouse wheel events for Linux/Mac
        self.canvas.bind("<Button-4>", self._on_mousewheel_linux_up)
        self.canvas.bind("<Button-5>", self._on_mousewheel_linux_down)
    
    def _on_scrollable_frame_configure(self, event):
        """Handle scrollable frame configuration changes."""
        try:
            # Get the canvas that contains this frame
            canvas = self.master
            # Only configure scrollregion if this is actually a canvas widget
            if hasattr(canvas, 'configure') and hasattr(canvas, 'bbox'):
                try:
                    canvas.configure(scrollregion=canvas.bbox("all"))
                except Exception:
                    # Skip if scrollregion option is not supported
                    pass
        except Exception as e:
            logger.error(f"Error configuring scroll region: {e}")
    
    def _on_mousewheel_linux_up(self, event):
        """Handle Linux mouse wheel up event."""
        try:
            if hasattr(self, 'canvas') and self.canvas:
                self.canvas.yview_scroll(-1, "units")
        except Exception as e:
            logger.error(f"Error in mouse wheel up: {e}")
    
    def _on_mousewheel_linux_down(self, event):
        """Handle Linux mouse wheel down event."""
        try:
            if hasattr(self, 'canvas') and self.canvas:
                self.canvas.yview_scroll(1, "units")
        except Exception as e:
            logger.error(f"Error in mouse wheel down: {e}")
    
    def destroy(self):
        """Clean up resources when destroying the widget."""
        try:
            # Clear callbacks to prevent memory leaks
            self.on_aircraft_selected = None
            
            # Clear canvas to free memory
            if hasattr(self, 'scrollable_frame'):
                try:
                    for widget in self.scrollable_frame.winfo_children():
                        widget.destroy()
                except Exception:
                    pass
            
            # Call parent destroy
            super().destroy()
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            # Ensure parent destroy is called even if cleanup fails
            try:
                super().destroy()
            except Exception:
                pass
    
    def _refresh_aircraft_list(self):
        """Refresh the list of available aircraft."""
        # Clear existing aircraft
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        # Get all aircraft types
        aircraft_types = self.config_manager.get_all_aircraft_types()
        
        for i, aircraft_type in enumerate(aircraft_types):
            self._create_aircraft_widget(aircraft_type, i)
        
        # Update scroll region after content changes
        self._update_scroll_region()
    
    def reload_aircraft_config(self):
        """Reload the aircraft configuration and refresh the display.
        
        This method ensures that any changes to the aircraft config file
        are reflected in the GUI immediately.
        """
        try:
            logger.info("Reloading aircraft configuration")
            
            # Reload the configuration in the config manager
            if hasattr(self.config_manager, '_load_config_with_priority'):
                self.config_manager._load_config_with_priority()
            else:
                # Fallback to original method
                self.config_manager.load_config()
            
            # Refresh the aircraft list to show any new aircraft
            self._refresh_aircraft_list()
            
            logger.info("Aircraft configuration reloaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to reload aircraft configuration: {e}")
            # Show error to user
            self._show_aircraft_list_error("Configuration Reload Failed",
                                         f"Failed to reload aircraft configuration.\n\nError: {str(e)}")
    
    def _reload_and_refresh(self):
        """Reload configuration and refresh the aircraft list.
        
        This method is called when the refresh button is clicked.
        """
        try:
            logger.info("User requested configuration reload")
            self.reload_aircraft_config()
        except Exception as e:
            logger.error(f"Error in reload and refresh: {e}")
    
    def _add_tooltip(self, widget, text):
        """Add a tooltip to a widget."""
        try:
            # Create a local tooltip class to avoid import issues
            class LocalTooltip:
                """Simple tooltip widget for fleet builder."""
                def __init__(self, widget, text: str, theme):
                    self.widget = widget
                    self.text = text
                    self.theme = theme
                    self.tip = None
                    widget.bind("<Enter>", self.show)
                    widget.bind("<Leave>", self.hide)

                def show(self, _=None):
                    if self.tip:
                        return
                    try:
                        x = self.widget.winfo_rootx() + 20
                        y = self.widget.winfo_rooty() + 20
                        self.tip = tk.Toplevel(self.widget)
                        self.tip.wm_overrideredirect(True)
                        self.tip.wm_geometry(f"+{x}+{y}")
                        
                        # Get theme colors safely
                        bg_color = getattr(theme, 'game_bg', '#2d3748')
                        fg_color = getattr(theme, 'game_fg', '#e2e8f0')
                        
                        tk.Label(self.tip, text=self.text, background=bg_color,
                                 foreground=fg_color, relief="solid", borderwidth=1,
                                 padx=4, pady=2).pack()
                    except Exception as e:
                        logger.warning(f"Failed to show tooltip: {e}")

                def hide(self, _=None):
                    if self.tip:
                        try:
                            self.tip.destroy()
                        except:
                            pass
                        self.tip = None
            
            # Create and return the tooltip
            return LocalTooltip(widget, text, self._get_theme())
        except Exception as e:
            logger.warning(f"Could not add tooltip: {e}")
            return None
    
    def _get_theme(self):
        """Get the current theme for tooltips."""
        try:
            # Try to get theme from parent or use a default
            if hasattr(self.master, '_theme_system_applied'):
                return self.master
            else:
                # Return a simple theme object
                class SimpleTheme:
                    game_bg = "#2d3748"
                    game_fg = "#e2e8f0"
                return SimpleTheme()
        except Exception:
            # Return a simple theme object as fallback
            class SimpleTheme:
                game_bg = "#2d3748"
                game_fg = "#e2e8f0"
            return SimpleTheme()
    
    def _update_scroll_region(self):
        """Update the scroll region to match content."""
        try:
            if hasattr(self, 'canvas') and self.canvas:
                # Wait for the frame to be configured
                self.after(10, lambda: self._configure_scroll_region())
        except Exception as e:
            logger.error(f"Error updating scroll region: {e}")
    
    def _configure_scroll_region(self):
        """Configure the scroll region with bounds checking."""
        try:
            if hasattr(self, 'canvas') and self.canvas:
                # Get the current scroll region
                current_region = self.canvas.bbox("all")
                if current_region:
                    # Ensure we don't scroll past bounds
                    canvas_height = self.canvas.winfo_height()
                    content_height = current_region[3] - current_region[1]
                    
                    if content_height <= canvas_height:
                        # Content fits in canvas, no scrolling needed
                        self.canvas.configure(scrollregion=(0, 0, 0, 0))
                    else:
                        # Content is larger than canvas, set proper scroll region
                        self.canvas.configure(scrollregion=current_region)
        except Exception as e:
            logger.error(f"Error configuring scroll region: {e}")
    
    def _safe_scroll(self, delta):
        """Safely scroll the canvas with bounds checking."""
        try:
            if hasattr(self, 'canvas') and self.canvas:
                # Get current scroll position
                current_pos = self.canvas.yview()
                if current_pos:
                    # Calculate new position
                    new_pos = current_pos[0] + (delta * 0.1)  # Scale down the scroll amount
                    
                    # Ensure we don't scroll past bounds
                    if new_pos < 0:
                        new_pos = 0
                    elif new_pos > 1:
                        new_pos = 1
                    
                    # Apply the scroll
                    self.canvas.yview_moveto(new_pos)
        except Exception as e:
            logger.error(f"Error in safe scroll: {e}")
    
    def _create_aircraft_widget(self, aircraft_type: AircraftType, index: int):
        """Create a widget for a single aircraft type."""
        frame = ttk.Frame(self.scrollable_frame, style="Card.TFrame")
        frame.pack(fill="x", padx=4, pady=2)
        
        # Aircraft info
        info_frame = ttk.Frame(frame)
        info_frame.pack(fill="x", padx=8, pady=6)
        
        # Aircraft name and description
        from cargosim.rendering.themes.font_manager import font_manager
        name_label = ttk.Label(info_frame, text=aircraft_type.name, 
                              style="Header.TLabel", font=font_manager.get_font('medium', 'bold'))
        name_label.pack(anchor="w")
        
        desc_label = ttk.Label(info_frame, text=aircraft_type.description, 
                              style="Muted.TLabel", wraplength=200)
        desc_label.pack(anchor="w", pady=(2, 4))
        
        # Aircraft stats
        stats_frame = ttk.Frame(info_frame)
        stats_frame.pack(fill="x", pady=(4, 0))
        
        # Capacity
        cap_frame = ttk.Frame(stats_frame)
        cap_frame.pack(side="left", padx=(0, 16))
        ttk.Label(cap_frame, text="Capacity:", style="Muted.TLabel").pack(side="left")
        ttk.Label(cap_frame, text=f" {aircraft_type.base_capacity}", 
                 style="Header.TLabel").pack(side="left")
        
        # Speed
        speed_frame = ttk.Frame(stats_frame)
        speed_frame.pack(side="left", padx=(0, 16))
        ttk.Label(speed_frame, text="Speed:", style="Muted.TLabel").pack(side="left")
        ttk.Label(speed_frame, text=f" {aircraft_type.cruise_speed_mach:.2f} Mach", 
                 style="Header.TLabel").pack(side="left")
        
        # Add aircraft button
        add_btn = ttk.Button(frame, text="Add to Fleet", 
                            command=self._create_add_aircraft_callback(aircraft_type.id))
        add_btn.pack(side="right", padx=8, pady=(0, 6))
        
        # Make entire frame clickable
        frame.bind("<Button-1>", self._create_add_aircraft_callback(aircraft_type.id))
        name_label.bind("<Button-1>", self._create_add_aircraft_callback(aircraft_type.id))
        desc_label.bind("<Button-1>", self._create_add_aircraft_callback(aircraft_type.id))
    
    def _create_add_aircraft_callback(self, aircraft_id: str):
        """Create a callback for adding aircraft to avoid lambda memory leaks."""
        def callback(event=None):
            if self.on_aircraft_selected:
                self.on_aircraft_selected(aircraft_id)
        return callback
    
    def _add_aircraft(self, aircraft_id: str):
        """Add an aircraft to the fleet."""
        if self.on_aircraft_selected:
            self.on_aircraft_selected(aircraft_id)


class FleetCanvas(ttk.Frame):
    """Canvas area where users can see and modify their fleet composition."""
    
    def __init__(self, parent, fleet_builder: FleetBuilder, **kwargs):
        super().__init__(parent, **kwargs)
        self.fleet_builder = fleet_builder
        self.on_fleet_changed: Optional[Callable[[], None]] = None
        
        self._build_ui()
        self._refresh_fleet_display()
    
    def _build_ui(self):
        """Build the fleet canvas UI."""
        # Header
        header_frame = ttk.Frame(self)
        header_frame.pack(fill="x", padx=8, pady=(8, 4))
        
        ttk.Label(header_frame, text="Current Fleet", style="Header.TLabel").pack(side="left")
        
        # Clear button
        clear_btn = ttk.Button(header_frame, text="Clear Fleet", 
                              command=self._clear_fleet)
        clear_btn.pack(side="right")
        
        # Fleet display area
        self.fleet_display_frame = ttk.Frame(self)
        self.fleet_display_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        
        # Fleet summary
        self.summary_frame = ttk.LabelFrame(self.fleet_display_frame, text="Fleet Summary", padding=8)
        self.summary_frame.pack(fill="x", pady=(0, 8))
        
        # Aircraft list
        self.aircraft_list_frame = ttk.LabelFrame(self.fleet_display_frame, text="Aircraft", padding=8)
        self.aircraft_list_frame.pack(fill="both", expand=True)
        
        # Empty state
        self.empty_label = ttk.Label(self.aircraft_list_frame, 
                                   text="No aircraft in fleet.\nDrag aircraft from the palette to build your fleet.",
                                   style="Muted.TLabel", justify="center")
        self.empty_label.pack(expand=True, pady=20)
    
    def _refresh_fleet_display(self):
        """Refresh the fleet display."""
        # Update summary
        self._update_summary()
        
        # Update aircraft list
        self._update_aircraft_list()
    
    def _update_summary(self):
        """Update the fleet summary display."""
        try:
            # Clear existing summary
            for widget in self.summary_frame.winfo_children():
                widget.destroy()
            
            # Get fleet summary safely with retry logic
            def get_summary_operation():
                return self.fleet_builder.get_fleet_summary()
            
            try:
                summary = retry_operation(get_summary_operation, 
                                        operation_name="Fleet Summary Retrieval")
            except Exception as e:
                logger.error(f"Failed to retrieve fleet summary after retries: {e}")
                self._show_summary_error("Unable to load fleet summary", 
                                       f"Failed to retrieve fleet data from the system.\n\nError: {str(e)}",
                                       self._retry_summary_update)
                return
            
            # Validate summary structure
            if not validate_fleet_summary(summary):
                logger.error("Invalid fleet summary structure")
                self._show_summary_error("Invalid Fleet Data", 
                                       "The fleet data structure is invalid or corrupted.\n\nThis may indicate a configuration issue.",
                                       self._retry_summary_update)
                return
            
            # Safely get values with defaults
            total_aircraft = safe_dict_get(summary, "total_aircraft", 0)
            total_capacity = safe_dict_get(summary, "total_capacity", 0)
            total_cost = safe_dict_get(summary, "total_cost", 0.0)
            efficiency_score = safe_dict_get(summary, "efficiency_score", 0.0)
            operational_cost = safe_dict_get(summary, "operational_cost", 0.0)
            capabilities = safe_dict_get(summary, "capabilities", [])
            
            if total_aircraft == 0:
                ttk.Label(self.summary_frame, text="No aircraft in fleet", 
                         style="Muted.TLabel").pack()
                return
            
            # Summary grid
            summary_grid = ttk.Frame(self.summary_frame)
            summary_grid.pack(fill="x")
            
            # Row 1: Aircraft count and total capacity
            row1 = ttk.Frame(summary_grid)
            row1.pack(fill="x", pady=(0, 4))
            
            ttk.Label(row1, text=f"Aircraft: {total_aircraft}", 
                     style="Header.TLabel").pack(side="left")
            ttk.Label(row1, text=f"Total Capacity: {total_capacity}", 
                     style="Header.TLabel").pack(side="right")
            
            # Row 2: Cost and efficiency
            row2 = ttk.Frame(summary_grid)
            row2.pack(fill="x", pady=(0, 4))
            
            ttk.Label(row2, text=f"Maintenance Cost: {total_cost:.1f}", 
                     style="Muted.TLabel").pack(side="left")
            ttk.Label(row2, text=f"Efficiency: {efficiency_score:.2f}", 
                     style="Muted.TLabel").pack(side="right")
            
            # Row 3: Operational cost
            row3 = ttk.Frame(summary_grid)
            row3.pack(fill="x", pady=(0, 4))
            
            ttk.Label(row3, text=f"Daily Operational Cost: ${operational_cost:,.2f}", 
                     style="Header.TLabel").pack(side="left")
            
            # Row 4: 30-day cost breakdown
            row4 = ttk.Frame(summary_grid)
            row4.pack(fill="x", pady=(4, 0))
            
            total_30_day = operational_cost * 30
            ttk.Label(row4, text=f"30-Day Total Cost: ${total_30_day:,.2f}", 
                     style="Muted.TLabel").pack(side="left")
            
            # Row 5: Capabilities
            if capabilities and isinstance(capabilities, list):
                row5 = ttk.Frame(summary_grid)
                row5.pack(fill="x", pady=(4, 0))
                
                ttk.Label(row5, text="Capabilities:", style="Muted.TLabel").pack(side="left")
                capabilities_text = ", ".join(str(cap) for cap in capabilities if cap)
                ttk.Label(row5, text=capabilities_text, style="Muted.TLabel").pack(side="left", padx=(8, 0))
                
        except Exception as e:
            logger.error(f"Error updating summary: {e}")
            self._show_summary_error("Summary Update Failed", 
                                   f"An unexpected error occurred while updating the fleet summary.\n\nError: {str(e)}",
                                   self._retry_summary_update)
    
    def _show_summary_error(self, title: str, message: str, retry_callback: Callable = None):
        """Show enhanced error state in summary area."""
        try:
            error_frame = ttk.Frame(self.summary_frame)
            error_frame.pack(fill="x", pady=20)
            
            # Error icon and title
            from cargosim.rendering.themes.font_manager import font_manager
            ttk.Label(error_frame, text="⚠️", 
                     style="Header.TLabel", foreground="red", font=font_manager.get_font('icon')).pack()
            ttk.Label(error_frame, text=title, 
                     style="Header.TLabel", foreground="red").pack()
            
            # Error message
            ttk.Label(error_frame, text=message, 
                     style="Muted.TLabel", wraplength=400, justify="center").pack(pady=(8, 0))
            
            # Action buttons
            button_frame = ttk.Frame(error_frame)
            button_frame.pack(pady=(12, 0))
            
            # Retry button
            if retry_callback:
                retry_btn = ttk.Button(button_frame, text="🔄 Retry", 
                                      command=retry_callback)
                retry_btn.pack(side="left", padx=(0, 8))
            
            # Advanced error details button
            details_btn = ttk.Button(button_frame, text="🔍 Error Details", 
                                    command=lambda: self._show_advanced_error_details(title, message))
            details_btn.pack(side="left")
            
        except Exception as e:
            logger.error(f"Error showing summary error: {e}")
            # Fallback to simple error display
            fallback_label = ttk.Label(self.summary_frame, 
                                      text=f"Error: {title}", 
                                      foreground="red")
            fallback_label.pack(pady=20)
    
    def _show_advanced_error_details(self, title: str, message: str):
        """Show advanced error details in a separate dialog."""
        try:
            # Get additional diagnostic information
            diagnostic_info = self._gather_diagnostic_info()
            
            # Create comprehensive error dialog
            create_error_dialog(
                parent=self,
                title=title,
                message=message,
                error_details=diagnostic_info,
                retry_callback=self._retry_summary_update,
                close_callback=None
            )
        except Exception as e:
            logger.error(f"Error showing advanced error details: {e}")
            # Fallback to simple message box
            messagebox.showerror(title, f"{message}\n\nDiagnostic information unavailable.")
    
    def _gather_diagnostic_info(self) -> str:
        """Gather diagnostic information for error reporting."""
        try:
            info_lines = []
            info_lines.append("=== DIAGNOSTIC INFORMATION ===")
            info_lines.append(f"Timestamp: {self._get_current_timestamp()}")
            info_lines.append(f"Fleet Builder Type: {type(self.fleet_builder).__name__}")
            
            # Check fleet builder state
            if hasattr(self.fleet_builder, 'current_fleet'):
                fleet = self.fleet_builder.current_fleet
                info_lines.append(f"Current Fleet: {fleet is not None}")
                if fleet:
                    info_lines.append(f"Fleet Type: {type(fleet).__name__}")
                    if hasattr(fleet, 'aircraft'):
                        info_lines.append(f"Aircraft Count: {len(fleet.aircraft) if fleet.aircraft else 0}")
            
            # Check configuration manager
            if hasattr(self.fleet_builder, 'config_manager'):
                config_mgr = self.fleet_builder.config_manager
                info_lines.append(f"Config Manager: {config_mgr is not None}")
                if config_mgr:
                    info_lines.append(f"Config Manager Type: {type(config_mgr).__name__}")
            
            # Check UI state
            info_lines.append(f"Summary Frame: {self.summary_frame is not None}")
            info_lines.append(f"Summary Frame Children: {len(self.summary_frame.winfo_children()) if self.summary_frame else 0}")
            
            return "\n".join(info_lines)
            
        except Exception as e:
            logger.error(f"Error gathering diagnostic info: {e}")
            return f"Failed to gather diagnostic information: {str(e)}"
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp for diagnostic information."""
        try:
            import datetime
            return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return "Unknown"
    
    def _retry_summary_update(self):
        """Retry updating the summary with enhanced error handling."""
        try:
            logger.info("Retrying summary update...")
            self._update_summary()
        except Exception as e:
            logger.error(f"Error retrying summary update: {e}")
            # Show error again with updated message
            self._show_summary_error("Retry Failed", 
                                   f"The retry attempt also failed.\n\nError: {str(e)}",
                                   self._retry_summary_update)
    
    def _update_aircraft_list(self):
        """Update the aircraft list display."""
        try:
            # Clear existing aircraft list
            for widget in self.aircraft_list_frame.winfo_children():
                if widget != self.empty_label:
                    widget.destroy()
            
            # Get fleet summary safely with retry logic
            def get_summary_operation():
                return self.fleet_builder.get_fleet_summary()
            
            try:
                summary = retry_operation(get_summary_operation, 
                                        operation_name="Aircraft List Summary Retrieval")
            except Exception as e:
                logger.error(f"Failed to retrieve aircraft list summary after retries: {e}")
                self._show_aircraft_list_error("Unable to load aircraft list", 
                                             f"Failed to retrieve aircraft data from the system.\n\nError: {str(e)}",
                                             self._retry_aircraft_list_update)
                return
            
            # Validate summary structure
            if not validate_fleet_summary(summary):
                logger.error("Invalid fleet summary structure in aircraft list update")
                self._show_aircraft_list_error("Invalid Fleet Data", 
                                             "The fleet data structure is invalid or corrupted.\n\nThis may indicate a configuration issue.",
                                             self._retry_aircraft_list_update)
                return
            
            # Safely get total aircraft count
            total_aircraft = safe_dict_get(summary, "total_aircraft", 0)
            
            if total_aircraft == 0:
                self.empty_label.pack(expand=True, pady=20)
                return
            
            # Hide empty state
            self.empty_label.pack_forget()
            
            # Safely get aircraft breakdown
            aircraft_breakdown = safe_dict_get(summary, "aircraft_breakdown", {})
            if not aircraft_breakdown or not isinstance(aircraft_breakdown, dict):
                logger.error("Invalid aircraft breakdown structure")
                self._show_aircraft_list_error("Invalid Aircraft Data", 
                                             "The aircraft breakdown data is invalid or corrupted.\n\nThis may indicate a data structure issue.",
                                             self._retry_aircraft_list_update)
                return
            
            # Create aircraft widgets safely with progress tracking
            successful_widgets = 0
            failed_widgets = 0
            
            for aircraft_id, aircraft_info in aircraft_breakdown.items():
                try:
                    if validate_aircraft_info(aircraft_info):
                        self._create_aircraft_widget(aircraft_id, aircraft_info)
                        successful_widgets += 1
                    else:
                        logger.warning(f"Skipping invalid aircraft info for {aircraft_id}")
                        failed_widgets += 1
                except Exception as e:
                    logger.error(f"Error creating aircraft widget for {aircraft_id}: {e}")
                    failed_widgets += 1
            
            # Log summary of widget creation
            logger.info(f"Aircraft list update completed: {successful_widgets} successful, {failed_widgets} failed")
            
            # Show warning if some widgets failed
            if failed_widgets > 0:
                self._show_aircraft_list_warning(f"Some aircraft could not be displayed ({failed_widgets} failed)")
                    
        except Exception as e:
            logger.error(f"Error updating aircraft list: {e}")
            self._show_aircraft_list_error("Aircraft List Update Failed", 
                                         f"An unexpected error occurred while updating the aircraft list.\n\nError: {str(e)}",
                                         self._retry_aircraft_list_update)
    
    def _show_aircraft_list_error(self, title: str, message: str, retry_callback: Callable = None):
        """Show enhanced error state in aircraft list area."""
        try:
            # Hide empty label
            self.empty_label.pack_forget()
            
            error_frame = ttk.Frame(self.aircraft_list_frame)
            error_frame.pack(expand=True, pady=20)
            
            # Error icon and title
            from cargosim.rendering.themes.font_manager import font_manager
            ttk.Label(error_frame, text="⚠️", 
                     style="Header.TLabel", foreground="red", font=font_manager.get_font('icon')).pack()
            ttk.Label(error_frame, text=title, 
                     style="Header.TLabel", foreground="red").pack()
            
            # Error message
            ttk.Label(error_frame, text=message, 
                     style="Muted.TLabel", wraplength=400, justify="center").pack(pady=(8, 0))
            
            # Action buttons
            button_frame = ttk.Frame(error_frame)
            button_frame.pack(pady=(12, 0))
            
            # Retry button
            if retry_callback:
                retry_btn = ttk.Button(button_frame, text="🔄 Retry", 
                                      command=retry_callback)
                retry_btn.pack(side="left", padx=(0, 8))
            
            # Advanced error details button
            details_btn = ttk.Button(button_frame, text="🔍 Error Details", 
                                    command=lambda: self._show_advanced_aircraft_error_details(title, message))
            details_btn.pack(side="left")
            
        except Exception as e:
            logger.error(f"Error showing aircraft list error: {e}")
            # Fallback to simple error display
            fallback_label = ttk.Label(self.aircraft_list_frame, 
                                      text=f"Error: {title}", 
                                      foreground="red")
            fallback_label.pack(pady=20)
    
    def _show_aircraft_list_warning(self, message: str):
        """Show warning state in aircraft list area."""
        try:
            warning_frame = ttk.Frame(self.aircraft_list_frame)
            warning_frame.pack(fill="x", pady=(8, 0))
            
            # Warning icon and message
            ttk.Label(warning_frame, text="⚠️", 
                     style="Muted.TLabel", foreground="orange").pack(side="left")
            ttk.Label(warning_frame, text=message, 
                     style="Muted.TLabel", foreground="orange").pack(side="left", padx=(4, 0))
            
        except Exception as e:
            logger.error(f"Error showing aircraft list warning: {e}")
    
    def _show_advanced_aircraft_error_details(self, title: str, message: str):
        """Show advanced error details for aircraft list errors."""
        try:
            # Get additional diagnostic information
            diagnostic_info = self._gather_aircraft_diagnostic_info()
            
            # Create comprehensive error dialog
            create_error_dialog(
                parent=self,
                title=title,
                message=message,
                error_details=diagnostic_info,
                retry_callback=self._retry_aircraft_list_update,
                close_callback=None
            )
        except Exception as e:
            logger.error(f"Error showing advanced aircraft error details: {e}")
            # Fallback to simple message box
            messagebox.showerror(title, f"{message}\n\nDiagnostic information unavailable.")
    
    def _gather_aircraft_diagnostic_info(self) -> str:
        """Gather diagnostic information for aircraft list errors."""
        try:
            info_lines = []
            info_lines.append("=== AIRCRAFT LIST DIAGNOSTIC INFORMATION ===")
            info_lines.append(f"Timestamp: {self._get_current_timestamp()}")
            info_lines.append(f"Fleet Builder Type: {type(self.fleet_builder).__name__}")
            
            # Check fleet builder state
            if hasattr(self.fleet_builder, 'current_fleet'):
                fleet = self.fleet_builder.current_fleet
                info_lines.append(f"Current Fleet: {fleet is not None}")
                if fleet:
                    info_lines.append(f"Fleet Type: {type(fleet).__name__}")
                    if hasattr(fleet, 'aircraft'):
                        info_lines.append(f"Aircraft Count: {len(fleet.aircraft) if fleet.aircraft else 0}")
            
            # Check UI state
            info_lines.append(f"Aircraft List Frame: {self.aircraft_list_frame is not None}")
            info_lines.append(f"Empty Label: {self.empty_label is not None}")
            info_lines.append(f"List Frame Children: {len(self.aircraft_list_frame.winfo_children()) if self.aircraft_list_frame else 0}")
            
            # Check summary data
            try:
                summary = self.fleet_builder.get_fleet_summary()
                if summary:
                    info_lines.append(f"Summary Total Aircraft: {safe_dict_get(summary, 'total_aircraft', 'Unknown')}")
                    info_lines.append(f"Summary Aircraft Breakdown: {safe_dict_get(summary, 'aircraft_breakdown', 'Unknown')}")
                    if 'aircraft_breakdown' in summary and isinstance(summary['aircraft_breakdown'], dict):
                        info_lines.append(f"Breakdown Keys: {list(summary['aircraft_breakdown'].keys())}")
                else:
                    info_lines.append("Summary: None")
            except Exception as e:
                info_lines.append(f"Summary Error: {str(e)}")
            
            return "\n".join(info_lines)
            
        except Exception as e:
            logger.error(f"Error gathering aircraft diagnostic info: {e}")
            return f"Failed to gather aircraft diagnostic information: {str(e)}"
    
    def _retry_aircraft_list_update(self):
        """Retry updating the aircraft list with enhanced error handling."""
        try:
            logger.info("Retrying aircraft list update...")
            self._update_aircraft_list()
        except Exception as e:
            logger.error(f"Error retrying aircraft list update: {e}")
            # Show error again with updated message
            self._show_aircraft_list_error("Retry Failed", 
                                         f"The retry attempt also failed.\n\nError: {str(e)}",
                                         self._retry_aircraft_list_update)
    
    def destroy(self):
        """Clean up resources when destroying the widget."""
        try:
            # Clear references to prevent memory leaks
            self.on_fleet_changed = None
            
            # Clear canvas to free memory
            if hasattr(self, 'preview_canvas'):
                try:
                    self.preview_canvas.delete("all")
                except Exception:
                    pass
            
            # Call parent destroy
            super().destroy()
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            # Ensure parent destroy is called even if cleanup fails
            try:
                super().destroy()
            except Exception:
                pass
    
    def _create_aircraft_widget(self, aircraft_id: str, aircraft_info: Dict):
        """Create a widget for a single aircraft in the fleet."""
        try:
            # Validate aircraft info before processing
            if not validate_aircraft_info(aircraft_info):
                logger.error(f"Invalid aircraft info for {aircraft_id}: {aircraft_info}")
                return
            
            frame = ttk.Frame(self.aircraft_list_frame, style="Card.TFrame")
            frame.pack(fill="x", padx=4, pady=2)
            
            # Aircraft info
            info_frame = ttk.Frame(frame)
            info_frame.pack(fill="x", padx=8, pady=6)
            
            # Aircraft name and count - safely get values
            name_frame = ttk.Frame(info_frame)
            name_frame.pack(fill="x")
            
            aircraft_name = safe_dict_get(aircraft_info, "name", "Unknown Aircraft")
            aircraft_count = safe_dict_get(aircraft_info, "count", 0)
            
            from cargosim.rendering.themes.font_manager import font_manager
            ttk.Label(name_frame, text=aircraft_name, 
                     style="Header.TLabel", font=font_manager.get_font('medium', 'bold')).pack(side="left")
            ttk.Label(name_frame, text=f" × {aircraft_count}", 
                     style="Muted.TLabel").pack(side="left", padx=(4, 0))
            
            # Aircraft stats
            stats_frame = ttk.Frame(info_frame)
            stats_frame.pack(fill="x", pady=(4, 0))
            
            # Individual capacity - safely get values
            cap_frame = ttk.Frame(stats_frame)
            cap_frame.pack(side="left", padx=(0, 16))
            ttk.Label(cap_frame, text="Individual:", style="Muted.TLabel").pack(side="left")
            
            individual_capacity = safe_dict_get(aircraft_info, "capacity", 0)
            ttk.Label(cap_frame, text=f" {individual_capacity}", 
                     style="Header.TLabel").pack(side="left")
            
            # Total capacity - safely get values
            total_cap_frame = ttk.Frame(stats_frame)
            total_cap_frame.pack(side="left", padx=(0, 16))
            ttk.Label(total_cap_frame, text="Total:", style="Muted.TLabel").pack(side="left")
            
            total_capacity = safe_dict_get(aircraft_info, "total_capacity", 0)
            ttk.Label(total_cap_frame, text=f" {total_capacity}", 
                     style="Header.TLabel").pack(side="left")
            
            # Controls
            controls_frame = ttk.Frame(frame)
            controls_frame.pack(anchor="e", padx=8, pady=(0, 6))
            
            # Remove one button - safely get count
            remove_one_btn = ttk.Button(controls_frame, text="-1", width=3,
                                       command=self._create_remove_aircraft_callback(aircraft_id, 1))
            remove_one_btn.pack(side="right", padx=(4, 0))
            
            # Remove all button - safely get count
            remove_all_btn = ttk.Button(controls_frame, text="Remove All", 
                                       command=self._create_remove_aircraft_callback(aircraft_id, aircraft_count))
            remove_all_btn.pack(side="right")
            
        except Exception as e:
            logger.error(f"Error creating aircraft widget for {aircraft_id}: {e}")
    
    def _create_remove_aircraft_callback(self, aircraft_id: str, count: int):
        """Create a safe callback for removing aircraft to avoid lambda memory leaks."""
        def callback():
            try:
                self._remove_aircraft(aircraft_id, count)
            except Exception as e:
                logger.error(f"Error in remove aircraft callback: {e}")
                messagebox.showerror("Error", f"Failed to remove aircraft: {e}")
        return callback
    
    def _remove_aircraft(self, aircraft_id: str, count: int):
        """Remove aircraft from the fleet."""
        self.fleet_builder.remove_aircraft(aircraft_id, count)
        self._refresh_fleet_display()
        
        if self.on_fleet_changed:
            self.on_fleet_changed()
    
    def _clear_fleet(self):
        """Clear the current fleet."""
        self.fleet_builder.clear_fleet()
        self._refresh_fleet_display()
        if self.on_fleet_changed:
            self.on_fleet_changed()
    
    def load_fleet_composition(self, fleet_composition: FleetComposition):
        """Load a fleet composition into the canvas."""
        try:
            # Validate fleet composition
            if not fleet_composition:
                logger.warning("Attempted to load None fleet composition")
                return
            
            # Update the fleet builder's current fleet
            self.fleet_builder.current_fleet = fleet_composition
            
            # Safely access and call methods
            if hasattr(self.fleet_builder.current_fleet, 'calculate_metrics'):
                try:
                    self.fleet_builder.current_fleet.calculate_metrics(self.fleet_builder.config_manager.aircraft_types)
                except Exception as e:
                    logger.warning(f"Could not calculate metrics: {e}")
            else:
                logger.warning("Fleet composition missing calculate_metrics method")
            
            # Refresh the display
            self._refresh_fleet_display()
            
            # Notify that fleet has changed
            if self.on_fleet_changed:
                self.on_fleet_changed()
                
        except Exception as e:
            logger.error(f"Error loading fleet composition: {e}")
            # Fall back to current fleet
            try:
                self._refresh_fleet_display()
            except Exception as fallback_error:
                logger.error(f"Error in fallback display refresh: {fallback_error}")
                self._show_fleet_load_error("Failed to load fleet composition")
    
    def _show_fleet_load_error(self, message: str):
        """Show error state when fleet loading fails."""
        try:
            # Clear existing display
            for widget in self.aircraft_list_frame.winfo_children():
                if widget != self.empty_label:
                    widget.destroy()
            
            # Hide empty label
            self.empty_label.pack_forget()
            
            # Show error
            error_frame = ttk.Frame(self.aircraft_list_frame)
            error_frame.pack(expand=True, pady=20)
            
            ttk.Label(error_frame, text="⚠️ Fleet Load Error", 
                     style="Header.TLabel", foreground="red").pack()
            ttk.Label(error_frame, text=message, 
                     style="Muted.TLabel", foreground="red").pack()
            
            # Add retry button
            retry_btn = ttk.Button(error_frame, text="Retry", 
                                  command=self._retry_fleet_load)
            retry_btn.pack(pady=(8, 0))
            
        except Exception as e:
            logger.error(f"Error showing fleet load error: {e}")
    
    def _retry_fleet_load(self):
        """Retry loading the fleet."""
        try:
            # This would need to be implemented based on how to retry the load
            logger.info("Retry fleet load requested")
            self._refresh_fleet_display()
        except Exception as e:
            logger.error(f"Error retrying fleet load: {e}")
    
    def add_aircraft(self, aircraft_id: str):
        """Add an aircraft to the fleet."""
        if self.fleet_builder.add_aircraft(aircraft_id):
            self._refresh_fleet_display()
            if self.on_fleet_changed:
                self.on_fleet_changed()
    
    def remove_aircraft(self, aircraft_id: str):
        """Remove an aircraft from the fleet."""
        if self.fleet_builder.remove_aircraft(aircraft_id):
            self._refresh_fleet_display()
            # Update fleet name automatically
            self._update_fleet_name()
            if self.on_fleet_changed:
                self.on_fleet_changed()


class FleetPresetPanel(ttk.Frame):
    """Panel for managing fleet presets."""
    
    def __init__(self, parent, fleet_builder: FleetBuilder, **kwargs):
        super().__init__(parent, **kwargs)
        self.fleet_builder = fleet_builder
        self.on_preset_selected: Optional[Callable[[str], None]] = None
        
        self._build_ui()
        self._refresh_presets()
    
    def _build_ui(self):
        """Build the preset panel UI."""
        # Header
        header_frame = ttk.Frame(self)
        header_frame.pack(fill="x", padx=8, pady=(8, 4))
        
        ttk.Label(header_frame, text="Fleet Presets", style="Header.TLabel").pack(side="left")
        
        # Preset list
        self.preset_frame = ttk.Frame(self)
        self.preset_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        
        # Scrollable canvas for presets
        self.canvas = tk.Canvas(self.preset_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.preset_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            self._on_scrollable_frame_configure
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Bind mouse wheel scrolling
        def _on_mousewheel(event):
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
        # Bind mouse wheel events for Windows
        self.canvas.bind("<MouseWheel>", _on_mousewheel)
        # Bind mouse wheel events for Linux/Mac
        self.canvas.bind("<Button-4>", self._on_mousewheel_linux_up)
        self.canvas.bind("<Button-5>", self._on_mousewheel_linux_down)
    
    def _on_scrollable_frame_configure(self, event):
        """Handle scrollable frame configuration changes."""
        try:
            # Get the canvas that contains this frame
            canvas = self.master
            # Only configure scrollregion if this is actually a canvas widget
            if hasattr(canvas, 'configure') and hasattr(canvas, 'bbox'):
                try:
                    canvas.configure(scrollregion=canvas.bbox("all"))
                except Exception:
                    # Skip if scrollregion option is not supported
                    pass
        except Exception as e:
            logger.error(f"Error configuring scroll region: {e}")
    
    def _on_mousewheel_linux_up(self, event):
        """Handle Linux mouse wheel up event."""
        try:
            if hasattr(self, 'canvas') and self.canvas:
                self.canvas.yview_scroll(-1, "units")
        except Exception as e:
            logger.error(f"Error in mouse wheel up: {e}")
    
    def _on_mousewheel_linux_down(self, event):
        """Handle Linux mouse wheel down event."""
        try:
            if hasattr(self, 'canvas') and self.canvas:
                self.canvas.yview_scroll(1, "units")
        except Exception as e:
            logger.error(f"Error in mouse wheel down: {e}")
    
    def _refresh_presets(self):
        """Refresh the list of fleet presets."""
        try:
            # Clear existing presets
            for widget in self.scrollable_frame.winfo_children():
                widget.destroy()
            
            # Get all presets safely with retry logic
            def get_presets_operation():
                return self.fleet_builder.config_manager.get_all_fleet_presets()
            
            try:
                presets = retry_operation(get_presets_operation, 
                                        operation_name="Fleet Presets Retrieval")
            except Exception as e:
                logger.error(f"Failed to retrieve fleet presets after retries: {e}")
                self._show_presets_error("Unable to load presets", 
                                       f"Failed to retrieve fleet preset data from the system.\n\nError: {str(e)}",
                                       self._retry_presets_refresh)
                return
            
            if not presets:
                # Show no presets message
                no_presets_label = ttk.Label(self.scrollable_frame, 
                                           text="No fleet presets available",
                                           style="Muted.TLabel")
                no_presets_label.pack(pady=20)
                return
            
            # Create preset widgets safely with progress tracking
            successful_widgets = 0
            failed_widgets = 0
            
            for i, preset in enumerate(presets):
                try:
                    if preset:  # Validate preset is not None
                        self._create_preset_widget(preset, i)
                        successful_widgets += 1
                    else:
                        logger.warning(f"Skipping None preset at index {i}")
                        failed_widgets += 1
                except Exception as e:
                    logger.error(f"Error creating preset widget at index {i}: {e}")
                    failed_widgets += 1
            
            # Log summary of widget creation
            logger.info(f"Preset refresh completed: {successful_widgets} successful, {failed_widgets} failed")
            
            # Show warning if some widgets failed
            if failed_widgets > 0:
                self._show_presets_warning(f"Some presets could not be displayed ({failed_widgets} failed)")
            
            # Update scroll region after content changes
            self._update_scroll_region()
                    
        except Exception as e:
            logger.error(f"Error refreshing presets: {e}")
            self._show_presets_error("Preset Refresh Failed", 
                                   f"An unexpected error occurred while refreshing the preset list.\n\nError: {str(e)}",
                                   self._retry_presets_refresh)
    
    def _update_scroll_region(self):
        """Update the scroll region to match content."""
        try:
            if hasattr(self, 'canvas') and self.canvas:
                # Wait for the frame to be configured
                self.after(10, lambda: self._configure_scroll_region())
        except Exception as e:
            logger.error(f"Error updating scroll region: {e}")
    
    def _configure_scroll_region(self):
        """Configure the scroll region with bounds checking."""
        try:
            if hasattr(self, 'canvas') and self.canvas:
                # Get the current scroll region
                current_region = self.canvas.bbox("all")
                if current_region:
                    # Ensure we don't scroll past bounds
                    canvas_height = self.canvas.winfo_height()
                    content_height = current_region[3] - current_region[1]
                    
                    if content_height <= canvas_height:
                        # Content fits in canvas, no scrolling needed
                        self.canvas.configure(scrollregion=(0, 0, 0, 0))
                    else:
                        # Content is larger than canvas, set proper scroll region
                        self.canvas.configure(scrollregion=current_region)
        except Exception as e:
            logger.error(f"Error configuring scroll region: {e}")
    
    def _show_presets_error(self, title: str, message: str, retry_callback: Callable = None):
        """Show enhanced error state in presets area."""
        try:
            error_frame = ttk.Frame(self.scrollable_frame)
            error_frame.pack(pady=20)
            
            # Error icon and title
            from cargosim.rendering.themes.font_manager import font_manager
            ttk.Label(error_frame, text="⚠️", 
                     style="Header.TLabel", foreground="red", font=font_manager.get_font('icon')).pack()
            ttk.Label(error_frame, text=title, 
                     style="Header.TLabel", foreground="red").pack()
            
            # Error message
            ttk.Label(error_frame, text=message, 
                     style="Muted.TLabel", wraplength=400, justify="center").pack(pady=(8, 0))
            
            # Action buttons
            button_frame = ttk.Frame(error_frame)
            button_frame.pack(pady=(12, 0))
            
            # Retry button
            if retry_callback:
                retry_btn = ttk.Button(button_frame, text="🔄 Retry", 
                                      command=retry_callback)
                retry_btn.pack(side="left", padx=(0, 8))
            
            # Advanced error details button
            details_btn = ttk.Button(button_frame, text="🔍 Error Details", 
                                    command=lambda: self._show_advanced_presets_error_details(title, message))
            details_btn.pack(side="left")
            
        except Exception as e:
            logger.error(f"Error showing presets error: {e}")
            # Fallback to simple error display
            fallback_label = ttk.Label(self.scrollable_frame, 
                                      text=f"Error: {title}", 
                                      foreground="red")
            fallback_label.pack(pady=20)
    
    def _show_presets_warning(self, message: str):
        """Show warning state in presets area."""
        try:
            warning_frame = ttk.Frame(self.scrollable_frame)
            warning_frame.pack(fill="x", pady=(8, 0))
            
            # Warning icon and message
            ttk.Label(warning_frame, text="⚠️", 
                     style="Muted.TLabel", foreground="orange").pack(side="left")
            ttk.Label(warning_frame, text=message, 
                     style="Muted.TLabel", foreground="orange").pack(side="left", padx=(4, 0))
            
        except Exception as e:
            logger.error(f"Error showing presets warning: {e}")
    
    def _show_advanced_presets_error_details(self, title: str, message: str):
        """Show advanced error details for preset errors."""
        try:
            # Get additional diagnostic information
            diagnostic_info = self._gather_presets_diagnostic_info()
            
            # Create comprehensive error dialog
            create_error_dialog(
                parent=self,
                title=title,
                message=message,
                error_details=diagnostic_info,
                retry_callback=self._retry_presets_refresh,
                close_callback=None
            )
        except Exception as e:
            logger.error(f"Error showing advanced presets error details: {e}")
            # Fallback to simple message box
            messagebox.showerror(title, f"{message}\n\nDiagnostic information unavailable.")
    
    def _gather_presets_diagnostic_info(self) -> str:
        """Gather diagnostic information for preset errors."""
        try:
            info_lines = []
            info_lines.append("=== FLEET PRESETS DIAGNOSTIC INFORMATION ===")
            info_lines.append(f"Timestamp: {self._get_current_timestamp()}")
            info_lines.append(f"Fleet Builder Type: {type(self.fleet_builder).__name__}")
            
            # Check configuration manager
            if hasattr(self.fleet_builder, 'config_manager'):
                config_mgr = self.fleet_builder.config_manager
                info_lines.append(f"Config Manager: {config_mgr is not None}")
                if config_mgr:
                    info_lines.append(f"Config Manager Type: {type(config_mgr).__name__}")
                    
                    # Check if get_all_fleet_presets method exists
                    if hasattr(config_mgr, 'get_all_fleet_presets'):
                        info_lines.append("get_all_fleet_presets method: Available")
                    else:
                        info_lines.append("get_all_fleet_presets method: Missing")
            else:
                info_lines.append("Config Manager: Not available")
            
            # Check UI state
            info_lines.append(f"Scrollable Frame: {self.scrollable_frame is not None}")
            info_lines.append(f"Frame Children: {len(self.scrollable_frame.winfo_children()) if self.scrollable_frame else 0}")
            
            # Check preset data
            try:
                if hasattr(self.fleet_builder, 'config_manager'):
                    presets = self.fleet_builder.config_manager.get_all_fleet_presets()
                    if presets:
                        info_lines.append(f"Presets Count: {len(presets)}")
                        info_lines.append(f"Presets Types: {[type(p).__name__ for p in presets[:5]]}")
                        if presets:
                            first_preset = presets[0]
                            info_lines.append(f"First Preset: {type(first_preset).__name__}")
                            if hasattr(first_preset, 'name'):
                                info_lines.append(f"First Preset Name: {first_preset.name}")
                    else:
                        info_lines.append("Presets: Empty list")
                else:
                    info_lines.append("Presets: Cannot retrieve (no config manager)")
            except Exception as e:
                info_lines.append(f"Presets Error: {str(e)}")
            
            return "\n".join(info_lines)
            
        except Exception as e:
            logger.error(f"Error gathering presets diagnostic info: {e}")
            return f"Failed to gather presets diagnostic information: {str(e)}"
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp for diagnostic information."""
        try:
            import datetime
            return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return "Unknown"
    
    def _retry_presets_refresh(self):
        """Retry refreshing presets with enhanced error handling."""
        try:
            logger.info("Retrying presets refresh...")
            self._refresh_presets()
        except Exception as e:
            logger.error(f"Error retrying presets refresh: {e}")
            # Show error again with updated message
            self._show_presets_error("Retry Failed", 
                                   f"The retry attempt also failed.\n\nError: {str(e)}",
                                   self._retry_presets_refresh)
    
    def _create_preset_widget(self, preset: FleetPreset, index: int):
        """Create a widget for a single fleet preset."""
        try:
            # Validate preset
            if not preset or not hasattr(preset, 'name'):
                logger.warning(f"Invalid preset at index {index}")
                return
            
            frame = ttk.Frame(self.scrollable_frame, style="Card.TFrame")
            frame.pack(fill="x", padx=4, pady=2)
            
            # Preset info
            info_frame = ttk.Frame(frame)
            info_frame.pack(fill="x", padx=8, pady=6)
            
            # Preset name - safely get
            from cargosim.rendering.themes.font_manager import font_manager
            preset_name = safe_attr_get(preset, 'name', 'Unknown Preset')
            ttk.Label(info_frame, text=preset_name, 
                     style="Header.TLabel", font=font_manager.get_font('medium', 'bold')).pack(anchor="w")
            
            # Preset description - safely get
            preset_description = safe_attr_get(preset, 'description', '')
            if preset_description:
                ttk.Label(info_frame, text=preset_description, 
                         style="Muted.TLabel", wraplength=200).pack(anchor="w", pady=(2, 4))
            
            # Aircraft summary - safely get
            aircraft_dict = safe_attr_get(preset, 'aircraft', {})
            if aircraft_dict and isinstance(aircraft_dict, dict):
                aircraft_summary = []
                for aircraft_id, count in aircraft_dict.items():
                    if aircraft_id and count:
                        aircraft_type = self.fleet_builder.config_manager.get_aircraft_type(aircraft_id)
                        if aircraft_type and hasattr(aircraft_type, 'name'):
                            aircraft_summary.append(f"{count}× {aircraft_type.name}")
                
                if aircraft_summary:
                    summary_text = ", ".join(aircraft_summary)
                    ttk.Label(info_frame, text=summary_text, 
                             style="Muted.TLabel").pack(anchor="w", pady=(0, 4))
            
            # Load button - safely create callback
            load_btn = ttk.Button(frame, text="Load Preset", 
                                 command=self._create_load_preset_callback(preset_name))
            load_btn.pack(anchor="e", padx=8, pady=(0, 6))
            
            # Visual feedback on hover
            def on_enter(e):
                try:
                    frame.configure(style="CardHover.TFrame")
                except Exception as e:
                    logger.debug(f"Error setting hover style: {e}")
            
            def on_leave(e):
                try:
                    frame.configure(style="Card.TFrame")
                except Exception as e:
                    logger.debug(f"Error setting normal style: {e}")
            
            frame.bind("<Enter>", on_enter)
            frame.bind("<Leave>", on_leave)
            
        except Exception as e:
            logger.error(f"Error creating preset widget for {getattr(preset, 'name', 'Unknown')}: {e}")
    
    def _create_load_preset_callback(self, preset_name: str):
        """Create a safe callback for loading presets to avoid lambda memory leaks."""
        def callback():
            try:
                if self.on_preset_selected:
                    self.on_preset_selected(preset_name)
                else:
                    logger.warning("No preset selection callback registered")
            except Exception as e:
                logger.error(f"Error in load preset callback: {e}")
                messagebox.showerror("Error", f"Failed to load preset: {e}")
        return callback

    def destroy(self):
        """Clean up resources when destroying the widget."""
        try:
            # Clear callbacks to prevent memory leaks
            self.on_preset_selected = None
            
            # Clear canvas to free memory
            if hasattr(self, 'scrollable_frame'):
                try:
                    for widget in self.scrollable_frame.winfo_children():
                        widget.destroy()
                except Exception:
                    pass
            
            # Call parent destroy
            super().destroy()
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            # Ensure parent destroy is called even if cleanup fails
            try:
                super().destroy()
            except Exception:
                pass


# ConfigurationManager class removed - now using core configuration manager
    """Centralized configuration management that doesn't rely on widget hierarchy."""
    
# Method removed - now using core configuration manager
        
# save_spoke_config method removed - now using core configuration manager
    
# _fallback_save method removed - now using core configuration manager


class SpokeConfigurationPanel(ttk.Frame):
    """Panel for configuring spoke distances and counts for time and distance mechanics."""
    
    def __init__(self, parent, config_manager: AircraftConfigManager, configuration_manager=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.config_manager = config_manager
        # Get the core configuration manager if none provided
        if configuration_manager is None:
            try:
                from cargosim.core.configuration_manager import get_configuration_manager
                self.configuration_manager = get_configuration_manager()
            except ImportError:
                self.configuration_manager = None
        else:
            self.configuration_manager = configuration_manager
        self.on_config_changed: Optional[Callable[[], None]] = None
        
        # Initialize instance variables
        self.distance_vars = []
        self.last_valid_distances: List[float] = []  # Tracks last valid values per spoke
        self.last_valid_spoke_count: int = 10        # Tracks last valid spoke count
        self.distance_entries: List[tk.Entry] = []   # Keep references to entry widgets
        # Distance constraints
        self._DIST_MIN = 100.0
        self._DIST_MAX = 1200.0
        self._DIST_DEFAULT = 500.0
        # Always assume variable spoke count is enabled
        self.var_spoke_count = tk.BooleanVar(value=True)
        self.spoke_count_var = tk.IntVar(value=10)
        self._preview_update_id: Optional[str] = None
        # Debounced configuration saving
        self._save_after_id: Optional[str] = None
        self._saving_config: bool = False
        self._save_pending: bool = False
        
        # Track pending operations for cleanup
        self._pending_operations = set()
        
        # Theme integration
        self.theme_colors = self._get_theme_colors()
        
        self._build_ui()
        self._load_current_config()
        
        # Bind destroy event to clean up pending operations
        self.bind('<Destroy>', self._on_destroy)

    def _schedule_config_save(self, delay: int = 150):
        """Debounce configuration save operations to avoid save storms."""
        try:
            if self._save_after_id:
                try:
                    self.after_cancel(self._save_after_id)
                except Exception:
                    pass
                finally:
                    try:
                        self._pending_operations.discard(self._save_after_id)
                    except Exception:
                        pass
                    self._save_after_id = None

            self._save_after_id = self.after(delay, self._perform_config_save)
            self._pending_operations.add(self._save_after_id)
        except Exception as e:
            logger.error(f"Error scheduling configuration save: {e}")

    def _perform_config_save(self):
        """Perform a single consolidated configuration save, coalescing rapid updates."""
        # Clear the scheduled id since we're executing now
        if self._save_after_id:
            try:
                self._pending_operations.discard(self._save_after_id)
            except Exception:
                pass
            self._save_after_id = None

        if self._saving_config:
            # Another save is in progress; mark pending and try again shortly
            self._save_pending = True
            self._schedule_config_save(100)
            return

        self._saving_config = True
        try:
            self._save_config_to_fleet_builder()
        except Exception as e:
            logger.error(f"Error performing configuration save: {e}")
        finally:
            self._saving_config = False
            if self._save_pending:
                self._save_pending = False
                self._schedule_config_save(100)
    
    def _get_theme_colors(self) -> dict:
        """Get current theme colors for the preview."""
        try:
            # Try to get theme colors from the parent GUI
            parent = self.winfo_parent()
            while parent:
                try:
                    if hasattr(parent, 'cfg') and hasattr(parent.cfg, 'theme'):
                        # We're in the main GUI, get theme colors
                        from cargosim.core.config import create_palette_from_theme_config
                        palette = create_palette_from_theme_config(parent.cfg.theme)
                        return {
                            'bg': palette.get('bg', '#ffffff'),
                            'fg': palette.get('fg', '#000000'),
                            'accent': palette.get('accent', '#3b82f6'),
                            'border': palette.get('border', '#c8c8c8'),
                            'muted': palette.get('muted', '#666666'),
                            'card_bg': palette.get('ui_card_bg', palette.get('bg', '#ffffff')),
                            'hover_bg': palette.get('ui_hover_bg', palette.get('bg', '#ffffff'))
                        }
                except Exception:
                    pass
                
                try:
                    parent = parent.winfo_parent()
                except Exception:
                    break
            
            # Fallback to default colors if theme not available
            return {
                'bg': '#ffffff',
                'fg': '#000000',
                'accent': '#3b82f6',
                'border': '#c8c8c8',
                'muted': '#666666',
                'card_bg': '#ffffff',
                'hover_bg': '#f8f9fa'
            }
        except Exception as e:
            logger.error(f"Error getting theme colors: {e}")
            # Return default colors on error
            return {
                'bg': '#ffffff',
                'fg': '#000000',
                'accent': '#3b82f6',
                'border': '#c8c8c8',
                'muted': '#666666',
                'card_bg': '#ffffff',
                'hover_bg': '#f8f9fa'
            }
    
    def _build_ui(self):
        """Build the spoke configuration UI."""
        # Header
        header_frame = ttk.Frame(self)
        header_frame.pack(fill="x", padx=8, pady=(8, 4))
        
        ttk.Label(header_frame, text="Spoke Configuration", style="Header.TLabel").pack(side="left")
        
        # Spoke count configuration
        count_frame = ttk.LabelFrame(self, text="Spoke Count", padding=8)
        count_frame.pack(fill="x", padx=8, pady=(0, 8))
        
        # Spoke count selector (always enabled)
        count_selector_frame = ttk.Frame(count_frame)
        count_selector_frame.pack(fill="x", pady=(0, 4))
        
        ttk.Label(count_selector_frame, text="Number of Spokes:").pack(side="left")
        
        self.spoke_count_spinner = ttk.Spinbox(
            count_selector_frame,
            from_=1,
            to=20,
            textvariable=self.spoke_count_var,
            width=10,
            command=self._on_spoke_count_changed,
        )
        self.spoke_count_spinner.pack(side="left", padx=(8, 0))

        # Ensure changes made by typing are also captured (not just arrow clicks)
        try:
            # Trace variable writes (fires on any value change)
            self.spoke_count_var.trace('w', lambda *args: self._on_spoke_count_changed())
            # Sanitize on Enter key and when focus leaves the widget
            self.spoke_count_spinner.bind('<Return>', self._sanitize_and_apply_spoke_count)
            self.spoke_count_spinner.bind('<FocusOut>', self._sanitize_and_apply_spoke_count)
        except Exception:
            # Be tolerant if running on older Tk versions
            pass
        
        # Ensure spinner is enabled (since variable spoke count is always on)
        operation_id = self.after(100, self._update_spinner_state)
        self._pending_operations.add(operation_id)
        
        # Spoke distances configuration
        distances_frame = ttk.LabelFrame(self, text="Spoke Distances (miles)", padding=8)
        distances_frame.pack(fill="x", padx=8, pady=(0, 8))
        
        # Distance inputs container
        self.distances_container = ttk.Frame(distances_frame)
        self.distances_container.pack(fill="x")
        
        # Create initial distance inputs
        self._create_distance_inputs()
        
        # Force preview update after creating inputs
        operation_id = self.after(200, self._force_preview_update)
        self._pending_operations.add(operation_id)
        
        # Geographic layout preview
        preview_frame = ttk.LabelFrame(self, text="Geographic Layout Preview", padding=8)
        preview_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        
        # Bind panel resize to update preview sizing
        self.bind("<Configure>", self._on_panel_resize)
        
        # Simple visual representation with theme colors
        self.preview_canvas = tk.Canvas(preview_frame, 
                                       bg=self.theme_colors['card_bg'], 
                                       highlightthickness=0)
        self.preview_canvas.pack(fill="both", expand=True, pady=(4, 0))
        
        # Set initial height and bind to frame resize
        self._set_canvas_height()
        preview_frame.bind("<Configure>", self._on_preview_frame_resize)
        
        # Bind resize events to update preview
        self.preview_canvas.bind("<Configure>", self._on_canvas_resize)
        
        # Bind to main window resize events for better height calculation
        self._bind_to_window_resize()
        
        # Initialize preview after UI is fully constructed
        operation_id = self.after(100, self._initialize_preview)
        self._pending_operations.add(operation_id)
    
    def _set_canvas_height(self):
        """Set canvas height based on available space."""
        try:
            if hasattr(self, 'preview_canvas') and self.preview_canvas:
                # Get the parent frame dimensions
                parent = self.preview_canvas.master
                if parent:
                    # Calculate available height (subtract padding and label)
                    available_height = max(150, parent.winfo_height() - 50)  # Minimum 150px
                    
                    # Try to get the panel height to calculate better proportions
                    panel = self.winfo_parent()
                    if panel:
                        try:
                            panel_height = panel.winfo_height()
                            if panel_height > 0:
                                # Use 60% of panel height for preview, with minimum
                                calculated_height = max(150, int(panel_height * 0.6))
                                available_height = max(available_height, calculated_height)
                        except Exception:
                            pass
                    
                    self.preview_canvas.configure(height=available_height)
        except Exception as e:
            logger.error(f"Error setting canvas height: {e}")
    
    def _bind_to_window_resize(self):
        """Bind to window resize events for better height calculation."""
        try:
            # Find the main window by traversing up the widget hierarchy
            widget = self
            while widget:
                try:
                    if hasattr(widget, 'winfo_toplevel'):
                        toplevel = widget.winfo_toplevel()
                        if toplevel and toplevel != self:
                            # Bind to window resize events
                            toplevel.bind("<Configure>", self._on_window_resize)
                            logger.info("Bound to window resize events")
                            break
                except Exception:
                    pass
                
                try:
                    widget = widget.winfo_parent()
                except Exception:
                    break
        except Exception as e:
            logger.error(f"Error binding to window resize: {e}")
    
    def _on_window_resize(self, event):
        """Handle window resize events to update preview sizing."""
        try:
            # Only handle significant size changes
            if hasattr(self, '_last_window_size'):
                last_width, last_height = self._last_window_size
                if abs(event.width - last_width) > 10 or abs(event.height - last_height) > 10:
                    # Significant size change, update canvas height
                    self._set_canvas_height()
                    # Redraw preview with new dimensions
                    operation_id = self.after(200, self._update_preview)
                    self._pending_operations.add(operation_id)
            
            # Store current size for next comparison
            self._last_window_size = (event.width, event.height)
        except Exception as e:
            logger.error(f"Error handling window resize: {e}")
    
    def _on_preview_frame_resize(self, event):
        """Handle preview frame resize to adjust canvas height."""
        try:
            # Update canvas height when frame is resized
            self._set_canvas_height()
            # Redraw preview with new dimensions
            operation_id = self.after(100, self._update_preview)
            self._pending_operations.add(operation_id)
        except Exception as e:
            logger.error(f"Error handling preview frame resize: {e}")
    
    def _on_panel_resize(self, event):
        """Handle panel resize to update preview sizing."""
        try:
            # Update canvas height when panel is resized
            self._set_canvas_height()
            # Redraw preview with new dimensions
            operation_id = self.after(100, self._update_preview)
            self._pending_operations.add(operation_id)
        except Exception as e:
            logger.error(f"Error handling panel resize: {e}")
    
    def _on_canvas_resize(self, event):
        """Handle canvas resize events to update preview."""
        try:
            # Only update if this is a size change (not just a move)
            if hasattr(self, '_last_canvas_size'):
                last_width, last_height = self._last_canvas_size
                if event.width != last_width or event.height != last_height:
                    # Size changed, update preview
                    operation_id = self.after(100, self._update_preview)
                    self._pending_operations.add(operation_id)
            
            # Store current size for next comparison
            self._last_canvas_size = (event.width, event.height)
        except Exception as e:
            logger.error(f"Error handling canvas resize: {e}")
    
    def refresh_theme_colors(self):
        """Refresh theme colors and redraw preview."""
        try:
            self.theme_colors = self._get_theme_colors()
            # Update canvas background
            if hasattr(self, 'preview_canvas') and self.preview_canvas:
                self.preview_canvas.configure(bg=self.theme_colors['card_bg'])
            # Redraw preview with new colors
            self._update_preview()
        except Exception as e:
            logger.error(f"Error refreshing theme colors: {e}")
    
    def _initialize_preview(self):
        """Initialize the preview after UI construction."""
        try:
            # Wait for the canvas to be properly sized
            operation_id = self.after(100, self._wait_for_canvas_size)
            self._pending_operations.add(operation_id)
        except Exception as e:
            logger.error(f"Error initializing preview: {e}")
    
    def _wait_for_canvas_size(self):
        """Wait for canvas to be properly sized before drawing preview."""
        try:
            # Check if the widget is being destroyed
            if not self.winfo_exists():
                return
                
            if hasattr(self, 'preview_canvas') and self.preview_canvas and self.preview_canvas.winfo_exists():
                canvas_width = self.preview_canvas.winfo_width()
                canvas_height = self.preview_canvas.winfo_height()
                
                if canvas_width > 1 and canvas_height > 1:
                    # Canvas is properly sized, draw the preview
                    self._update_preview()
                    # Reset wait count on success
                    if hasattr(self, '_canvas_wait_count'):
                        self._canvas_wait_count = 0
                else:
                    # Canvas not yet sized, wait a bit more
                    # Use exponential backoff to avoid infinite waiting
                    if not hasattr(self, '_canvas_wait_count'):
                        self._canvas_wait_count = 0
                    
                    if self._canvas_wait_count < 20:  # Increased max attempts further
                        self._canvas_wait_count += 1
                        # Use shorter delays for better responsiveness
                        delay = min(30 + (self._canvas_wait_count * 8), 150)
                        operation_id = self.after(delay, self._wait_for_canvas_size)
                        self._pending_operations.add(operation_id)
                    else:
                        # Force update after max attempts
                        logger.debug("Canvas size wait timeout, forcing preview update")
                        self._force_preview_update()
                        # Reset wait count after forcing update
                        self._canvas_wait_count = 0
            else:
                logger.warning("Preview canvas not available for initialization")
        except Exception as e:
            logger.error(f"Error waiting for canvas size: {e}")
            # Reset wait count on error
            if hasattr(self, '_canvas_wait_count'):
                self._canvas_wait_count = 0
    
    def _create_distance_inputs(self):
        """Create distance input fields for each spoke."""
        try:
            logger.debug("Creating distance inputs for spokes")

            # Clear existing inputs
            for widget in self.distances_container.winfo_children():
                widget.destroy()

            # Clear distance variables list
            old_distance_vars = getattr(self, 'distance_vars', [])
            old_last_valid = list(getattr(self, 'last_valid_distances', []))
            self.distance_vars.clear()
            # Clear and recreate entries list
            try:
                self.distance_entries.clear()
            except Exception:
                self.distance_entries = []

            # Get the current spoke count
            # Be tolerant of transient empty input in the spinbox
            try:
                spoke_count = self.spoke_count_var.get()
            except Exception:
                # Fall back to last valid count
                spoke_count = self.last_valid_spoke_count or 10
            logger.debug(f"Creating distance inputs for {spoke_count} spokes")

            # Ensure spoke count is within valid range
            spoke_count = max(1, min(20, spoke_count))

            # Create grid for distance inputs
            for i in range(spoke_count):
                row = i // 5  # 5 columns per row
                col = i % 5
                
                # Spoke label
                label = ttk.Label(self.distances_container, text=f"Spoke {i+1}:")
                label.grid(row=row, column=col*2, padx=(0, 4), pady=2, sticky="e")
                
                # Distance input (use StringVar-friendly DoubleVar; value may be temporarily empty)
                distance_var = tk.DoubleVar(value=500.0)
                distance_entry = ttk.Entry(self.distances_container, 
                                         textvariable=distance_var,
                                         width=8,
                                         validate="key",
                                         validatecommand=(self.register(self._validate_distance), '%P'))
                distance_entry.grid(row=row, column=col*2+1, padx=(0, 8), pady=2, sticky="w")

                # Store reference to variable
                self.distance_vars.append(distance_var)
                # Store entry reference and bind sanitize on commit
                self.distance_entries.append(distance_entry)
                distance_entry.bind('<Return>', lambda e, i=i: self._sanitize_distance_and_apply(i))
                distance_entry.bind('<FocusOut>', lambda e, i=i: self._sanitize_distance_and_apply(i))

                # Bind change event using a proper method reference
                distance_var.trace('w', self._create_distance_change_callback(i))

            # Resize last_valid_distances to match current spoke count, preserving prior values
            new_last_valid: List[float] = []
            for i in range(spoke_count):
                if i < len(old_last_valid):
                    new_last_valid.append(float(old_last_valid[i]))
                else:
                    new_last_valid.append(500.0)
            self.last_valid_distances = new_last_valid

            logger.debug(f"Successfully created {spoke_count} distance input fields")
            
            # Update preview after creating inputs
            operation_id = self.after(100, self._force_preview_update)
            self._pending_operations.add(operation_id)
            
        except Exception as e:
            logger.error(f"Error creating distance inputs: {e}")
            raise
    
    def _refresh_preview_after_config(self):
        """Refresh preview after configuration changes."""
        try:
            # Force preview update after configuration changes
            operation_id = self.after(100, self._force_preview_update)
            self._pending_operations.add(operation_id)
        except Exception as e:
            logger.error(f"Error refreshing preview after config: {e}")
    
    def _force_preview_update(self):
        """Force update the preview with retry logic."""
        try:
            # Check if the widget is being destroyed
            if not self.winfo_exists():
                return
                
            if hasattr(self, 'preview_canvas') and self.preview_canvas and self.preview_canvas.winfo_exists():
                # Check if canvas is ready
                canvas_width = self.preview_canvas.winfo_width()
                canvas_height = self.preview_canvas.winfo_height()
                
                if canvas_width > 1 and canvas_height > 1:
                    self._update_preview()
                    # Reset retry count on success
                    if hasattr(self, '_force_update_count'):
                        self._force_update_count = 0
                else:
                    # Canvas not ready, try again with limited retries
                    if not hasattr(self, '_force_update_count'):
                        self._force_update_count = 0
                    
                    if self._force_update_count < 8:  # Increased max retries
                        self._force_update_count += 1
                        delay = min(100 + (self._force_update_count * 20), 300)
                        operation_id = self.after(delay, self._force_preview_update)
                        self._pending_operations.add(operation_id)
                    else:
                        logger.debug("Force preview update retry limit reached")
                        self._force_update_count = 0
            else:
                logger.warning("Preview canvas not available for force update")
        except Exception as e:
            logger.error(f"Error in force preview update: {e}")
            # Reset retry count on error
            if hasattr(self, '_force_update_count'):
                self._force_update_count = 0
    
    def _create_distance_change_callback(self, index):
        """Create a callback function for distance changes to avoid lambda memory leaks."""
        def callback(*args):
            self._on_distance_changed(index)
        return callback

    def _validate_distance(self, value):
        """Validate distance input while typing.

        Be permissive to allow smooth editing: allow empty string and any
        string that parses as float, plus transitional states like '-', '.', '-.'.
        Range enforcement is done on commit (Enter/FocusOut).
        """
        if value == "":
            return True
        try:
            float(value)
            return True
        except ValueError:
            # Allow some transitional inputs during typing
            return value in {"-", ".", "-."}

    def _safe_get_spoke_count(self, default: Optional[int] = None) -> Optional[int]:
        """Safely get the spoke count from the IntVar/spinbox, tolerating empty input."""
        # Try IntVar first
        try:
            count = self.spoke_count_var.get()
            self.last_valid_spoke_count = int(count)
            return int(count)
        except Exception:
            pass
        # Try reading raw text from the spinbox widget
        try:
            raw = self.spoke_count_spinner.get().strip()
            if raw == "":
                return default
            count = int(raw)
            self.last_valid_spoke_count = int(count)
            return int(count)
        except Exception:
            return default

    def _safe_get_distance(self, index: int) -> Optional[float]:
        """Safely get a distance value; return None if the field is temporarily empty/invalid."""
        try:
            value = float(self.distance_vars[index].get())
            # Clamp to valid range
            value = max(self._DIST_MIN, min(self._DIST_MAX, value))
            # Update last valid cache
            if index < len(self.last_valid_distances):
                self.last_valid_distances[index] = value
            return value
        except Exception:
            # Return None to indicate an in-progress/invalid edit state
            return None

    def _sanitize_distance_and_apply(self, index: int):
        """On commit (Enter/FocusOut), coerce the input to a valid float or default."""
        try:
            entry = self.distance_entries[index]
        except Exception:
            entry = None
        raw = None
        try:
            raw = entry.get().strip() if entry else None
        except Exception:
            raw = None

        # Convert to float; on failure, use default
        try:
            val = float(raw) if raw not in (None, "") else self._DIST_DEFAULT
        except Exception:
            val = self._DIST_DEFAULT

        # Clamp to nearest valid number
        val = max(self._DIST_MIN, min(self._DIST_MAX, float(val)))

        # Apply back to UI and state
        try:
            self.distance_vars[index].set(val)
        except Exception:
            pass
        if index < len(self.last_valid_distances):
            self.last_valid_distances[index] = float(val)

        # Update preview and schedule save
        try:
            self._update_preview()
        except Exception:
            pass
        try:
            self._schedule_config_save(200)
        except Exception:
            pass
        if self.on_config_changed:
            try:
                self.on_config_changed()
            except Exception:
                pass

    def _sanitize_and_apply_spoke_count(self, event=None):
        """On commit, coerce the spoke count to a valid int in range or default."""
        # Read raw text from spinbox
        try:
            raw = self.spoke_count_spinner.get().strip()
        except Exception:
            raw = ""

        # Convert to int; on failure, use last valid or default
        try:
            val = int(raw)
        except Exception:
            val = self.last_valid_spoke_count or 10

        # Clamp to valid range
        val = max(1, min(20, int(val)))

        # Set the variable; var trace will trigger reflow/update
        try:
            self.spoke_count_var.set(val)
        except Exception:
            pass
        self.last_valid_spoke_count = int(val)
    
    def _on_variable_spoke_count_changed(self):
        """Handle variable spoke count toggle change (no longer used but kept for compatibility)."""
        try:
            logger.info(f"Variable spoke count changed to: {self.var_spoke_count.get()}")
            
            # Since variable spoke count is always enabled, just ensure spinner is enabled
            self._update_spinner_state()
            
            # Schedule consolidated save instead of immediate multiple saves
            self._schedule_config_save(150)
            
            # Notify configuration change
            if self.on_config_changed:
                self.on_config_changed()
                
            logger.debug("Variable spoke count change processed successfully")
                
        except Exception as e:
            logger.error(f"Error in variable spoke count change: {e}")
            self._show_spoke_config_error("Spoke Count Error", 
                                        f"Failed to update spoke count configuration.\n\nError: {str(e)}")
    
    def _update_spinner_state(self):
        """Update the spinner state (always enabled since variable spoke count is always on)."""
        try:
            # Always enable the spinner since variable spoke count is always enabled
            self.spoke_count_spinner.config(state="normal")
        except Exception as e:
            logger.error(f"Error updating spinner state: {e}")
    
    def _on_destroy(self, event):
        """Handle widget destruction to clean up pending operations."""
        try:
            # Cancel all pending operations
            for operation_id in self._pending_operations:
                try:
                    self.after_cancel(operation_id)
                except:
                    pass
            self._pending_operations.clear()

            # Also cancel any pending save if tracked separately
            try:
                if getattr(self, '_save_after_id', None):
                    self.after_cancel(self._save_after_id)
                    self._save_after_id = None
            except Exception:
                pass
            
            logger.debug("Cleaned up pending operations on SpokeConfigurationPanel destruction")
        except Exception as e:
            logger.debug(f"Error during SpokeConfigurationPanel cleanup: {e}")
    
    
    def save_configuration_directly(self):
        """Save configuration directly using ConfigurationManager or fallback methods."""
        try:
            config = self.get_config()
            logger.info(f"Saving configuration directly: {len(config.get('spoke_distances', []))} spokes")
            
            # Use ConfigurationManager if available
            if self.configuration_manager:
                try:
                    success = self.configuration_manager.save_spoke_config(config)
                    if success:
                        logger.info("Configuration saved using ConfigurationManager")
                        return True
                    else:
                        logger.warning("ConfigurationManager save failed, trying fallback methods")
                except Exception as e:
                    logger.warning(f"ConfigurationManager error: {e}, trying fallback methods")
            
            # Fallback: Update the main GUI's cfg via toplevel back-reference if available
            try:
                toplevel = self.winfo_toplevel()
                control_gui = getattr(toplevel, '_control_gui', None)
            except Exception:
                control_gui = None

            if control_gui and hasattr(control_gui, 'cfg'):
                try:
                    if 'spoke_distances' in config:
                        control_gui.cfg.spoke_distances = config['spoke_distances']
                        control_gui.cfg.max_spokes = config.get('max_spokes', len(config['spoke_distances']))
                        control_gui.cfg.variable_spoke_count = config.get('variable_spoke_count', True)

                        # Generate pair order matching the current spoke count
                        actual_spoke_count = len(config['spoke_distances'])
                        if actual_spoke_count > 0:
                            pair_order = []
                            for i in range(0, actual_spoke_count - 1, 2):
                                if i + 1 < actual_spoke_count:
                                    pair_order.append((i, i + 1))
                            if actual_spoke_count % 2 == 1:
                                pair_order.append((actual_spoke_count - 1, 0))
                            control_gui.cfg.pair_order = pair_order

                        # Keep embedded spoke_config consistent
                        control_gui.cfg.spoke_config = config

                        # Save to disk using the core configuration manager when possible
                        if self.configuration_manager:
                            try:
                                success = self.configuration_manager.save_spoke_config(config)
                                if success:
                                    logger.info("Configuration saved successfully using core configuration manager")
                                    return True
                                else:
                                    logger.warning("Core configuration manager save failed, trying fallback")
                            except Exception as cm_error:
                                logger.warning(f"Core configuration manager error: {cm_error}, trying fallback")

                        # Fallback: Save directly to disk
                        try:
                            from cargosim.core.config import save_config
                            save_config(control_gui.cfg)
                            logger.info("Configuration saved successfully using fallback method")
                            return True
                        except Exception as fallback_error:
                            logger.error(f"Fallback save failed: {fallback_error}")
                            return False
                except Exception as update_error:
                    logger.error(f"Failed to update main GUI configuration: {update_error}")

            logger.warning("Could not reach main GUI to save configuration")
            return False
            
        except Exception as e:
            logger.error(f"Error saving configuration directly: {e}")
            return False
    def _save_config_to_fleet_builder(self):
        """Save the current configuration to the fleet builder and main configuration."""
        try:
            # Get current configuration from the UI
            config = self.get_config()
            logger.info(f"SAVING CONFIGURATION: {len(config.get('spoke_distances', []))} spokes")
            
            # Use core ConfigurationManager if available (most reliable method)
            if self.configuration_manager:
                try:
                    success = self.configuration_manager.save_spoke_config(config)
                    if success:
                        logger.info("Configuration saved using core ConfigurationManager")
                    else:
                        logger.warning("Core ConfigurationManager save failed, trying alternative methods")
                except Exception as e:
                    logger.warning(f"Core ConfigurationManager error: {e}, trying alternative methods")
            
            # Fallback: Try to save directly to disk once
            success = self.save_configuration_directly()
            if success:
                logger.info("Configuration saved directly to disk")
            else:
                logger.warning("Direct save failed, trying alternative methods")
            
            # Also try to update the fleet builder if available
            parent = self.winfo_parent()
            while parent:
                try:
                    if hasattr(parent, 'fleet_builder') and hasattr(parent.fleet_builder, 'update_spoke_configuration'):
                        # Update fleet builder with new configuration
                        success = parent.fleet_builder.update_spoke_configuration(config)
                        if success:
                            logger.debug("Spoke configuration saved to fleet builder")
                        else:
                            logger.warning("Failed to save spoke configuration to fleet builder")
                        break
                except Exception:
                    pass
                
                try:
                    parent = parent.winfo_parent()
                except Exception:
                    break
            
            # Reload configuration to verify persistence
            try:
                # Use absolute imports - these should work from anywhere
                from cargosim.core.config import load_config, save_config, repair_spoke_configuration
                
                # Reload configuration to ensure it's up to date
                reloaded_cfg = load_config()
                logger.info(f"Configuration reloaded: {len(reloaded_cfg.spoke_distances)} spokes")
                
                # Normalize any inconsistencies before comparison
                reloaded_cfg = repair_spoke_configuration(reloaded_cfg)
                
                # If the reloaded config doesn't match what we intended, force save once
                if len(reloaded_cfg.spoke_distances) != len(config.get('spoke_distances', [])):
                    logger.debug("Configuration mismatch detected during verification; applying corrective save")
                    reloaded_cfg.spoke_distances = config['spoke_distances']
                    reloaded_cfg.max_spokes = config.get('max_spokes', len(config['spoke_distances']))
                    reloaded_cfg.variable_spoke_count = config.get('variable_spoke_count', True)
                    
                    # Generate new pair order
                    actual_spoke_count = len(config['spoke_distances'])
                    if actual_spoke_count > 0:
                        pair_order = []
                        for i in range(0, actual_spoke_count - 1, 2):
                            if i + 1 < actual_spoke_count:
                                pair_order.append((i, i + 1))
                        
                        if actual_spoke_count % 2 == 1:  # Odd number of spokes
                            pair_order.append((actual_spoke_count - 1, 0))
                        
                        reloaded_cfg.pair_order = pair_order
                    
                    # Keep spoke_config in sync with primary fields
                    reloaded_cfg.spoke_config = {
                        **(reloaded_cfg.spoke_config or {}),
                        'spoke_distances': config['spoke_distances'],
                        'max_spokes': reloaded_cfg.max_spokes,
                        'variable_spoke_count': reloaded_cfg.variable_spoke_count,
                    }
                    save_config(reloaded_cfg)
                    logger.info("Configuration corrected and saved after verification mismatch")
                
            except Exception as reload_error:
                logger.warning(f"Could not reload configuration: {reload_error}")
            
            logger.info(f"CONFIGURATION SAVE COMPLETE: {len(config.get('spoke_distances', []))} spokes")
            
        except Exception as e:
            logger.error(f"Error saving spoke configuration: {e}")
            # Try one more time with the direct method
            try:
                self.save_configuration_directly()
            except Exception as final_error:
                logger.error(f"Final save attempt also failed: {final_error}")
    
    def save_configuration(self):
        """Explicitly save the current configuration."""
        try:
            self._schedule_config_save(100)
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
    
    def _on_spoke_count_changed(self):
        """Handle spoke count change."""
        try:
            # Validate the new spoke count (tolerate empty input during edits)
            new_count = self._safe_get_spoke_count(default=self.last_valid_spoke_count)
            if new_count is None:
                # User is mid-edit (e.g., empty); do not force errors
                return
            logger.info(f"Spoke count changed to: {new_count}")

            if new_count < 1 or new_count > 20:
                logger.warning(f"Invalid spoke count: {new_count}, resetting to valid range")
                if new_count < 1:
                    self.spoke_count_var.set(1)
                    logger.info("Spoke count reset to minimum: 1")
                else:
                    self.spoke_count_var.set(20)
                    logger.info("Spoke count reset to maximum: 20")
                return

            logger.debug(f"Spoke count validation passed: {new_count}")

            # IMPORTANT: Update the configuration BEFORE recreating distance inputs
            # This ensures the configuration reflects the new spoke count
            current_config = self.get_config()
            current_config['max_spokes'] = new_count

            # Generate new spoke distances for the new count
            new_distances = []
            for i in range(new_count):
                if i < len(current_config.get('spoke_distances', [])):
                    # Keep existing distances if available
                    new_distances.append(current_config['spoke_distances'][i])
                else:
                    # Generate new distances for additional spokes
                    new_distances.append(100 + (i * 50))

            current_config['spoke_distances'] = new_distances
            current_config['variable_spoke_count'] = True

            # Update the configuration in the UI
            self.spoke_count_var.set(new_count)
            self.last_valid_spoke_count = int(new_count)

            # Recreate distance inputs with new count
            logger.debug(f"Recreating distance inputs for {new_count} spokes")
            self._create_distance_inputs()

            # Update the distance variables with the new configuration
            for i, distance in enumerate(new_distances):
                if i < len(self.distance_vars):
                    self.distance_vars[i].set(distance)
                    if i < len(self.last_valid_distances):
                        self.last_valid_distances[i] = float(distance)

            # Consolidate save
            logger.info(f"Scheduling save for updated configuration with {new_count} spokes")
            self._schedule_config_save(150)
            
            # Ensure preview is updated after spoke count change
            operation_id = self.after(150, self._force_preview_update)
            self._pending_operations.add(operation_id)
            
            # Notify configuration change
            if self.on_config_changed:
                self.on_config_changed()
                
            logger.info(f"Spoke count change completed: {new_count} spokes configured and saved")
                
        except Exception as e:
            logger.error(f"Error in spoke count change: {e}")
            self._show_spoke_config_error("Spoke Count Change Error", 
                                        f"Failed to update spoke count.\n\nError: {str(e)}")
    
    def _on_distance_changed(self, index):
        """Handle distance input change."""
        try:
            # Get the new distance value safely (tolerate empty/invalid input during edits)
            new_distance = self._safe_get_distance(index)
            if new_distance is None:
                # Skip processing until a valid value is present
                return
            logger.debug(f"Distance changed for spoke {index + 1}: {new_distance} miles")
            
            self._update_preview()
            
            # Schedule consolidated configuration save
            self._schedule_config_save(200)
            
            if self.on_config_changed:
                self.on_config_changed()
                
            logger.debug(f"Distance change for spoke {index + 1} processed successfully")
            
        except Exception as e:
            # Be forgiving during typing; avoid noisy dialogs for transient states
            logger.warning(f"Error in distance change for spoke {index + 1}: {e}")
    
    def _update_preview(self):
        """Update the geographic layout preview."""
        try:
            self.preview_canvas.delete("all")
            
            if not self.distance_vars:
                return
            
            # Get current distances safely
            distances = []
            for var in self.distance_vars:
                try:
                    distance = var.get()
                    if distance > 0:
                        distances.append(distance)
                except Exception as e:
                    logger.warning(f"Error getting distance value: {e}")
                    continue
            
            if not distances:
                # Show no distances message
                self.preview_canvas.create_text(
                    self.preview_canvas.winfo_width() // 2,
                    self.preview_canvas.winfo_height() // 2,
                    text="No distances configured",
                    fill=self.theme_colors['muted'],
                    font=DEFAULT_FONT
                )
                return
            
            # Calculate preview dimensions
            canvas_width = self.preview_canvas.winfo_width()
            canvas_height = self.preview_canvas.winfo_height()
            
            # If canvas is not yet sized, use default dimensions or wait
            if canvas_width <= 1 or canvas_height <= 1:
                # Schedule another update attempt
                self._schedule_preview_update(100)
                return
            
            # Draw hub (center)
            hub_x = canvas_width // 2
            hub_y = canvas_height // 2
            hub_radius = 8
            
            self.preview_canvas.create_oval(hub_x - hub_radius, hub_y - hub_radius,
                                           hub_x + hub_radius, hub_y + hub_radius,
                                           fill=self.theme_colors['accent'], 
                                           outline=self.theme_colors['border'])
            self.preview_canvas.create_text(hub_x, hub_y - hub_radius - 15,
                                          text="HUB", 
                                          fill=self.theme_colors['fg'],
                                          font=DEFAULT_FONT_BOLD)
            
            # Draw spokes safely
            try:
                max_distance = max(distances)
                scale_factor = min(canvas_width, canvas_height) * 0.3 / max_distance
                
                for i, distance in enumerate(distances):
                    if distance <= 0:
                        continue
                    
                    # Calculate spoke position (evenly distributed around hub)
                    angle = (2 * 3.14159 * i) / len(distances)
                    spoke_x = hub_x + int(distance * scale_factor * math.cos(angle))
                    spoke_y = hub_y + int(distance * scale_factor * math.sin(angle))
                    
                    # Draw spoke line
                    self.preview_canvas.create_line(hub_x, hub_y, spoke_x, spoke_y,
                                                  fill=self.theme_colors['muted'], width=1, dash=(2, 2))
                    
                    # Draw spoke point
                    spoke_radius = 4
                    self.preview_canvas.create_oval(spoke_x - spoke_radius, spoke_y - spoke_radius,
                                                   spoke_x + spoke_radius, spoke_y + spoke_radius,
                                                   fill=self.theme_colors['fg'], 
                                                   outline=self.theme_colors['border'])
                    
                    # Draw distance label
                    self.preview_canvas.create_text(spoke_x, spoke_y - spoke_radius - 10,
                                                  text=f"{int(distance)}mi", 
                                                  fill=self.theme_colors['fg'],
                                                  font=DEFAULT_FONT)
            except Exception as e:
                logger.error(f"Error drawing spokes: {e}")
                # Show error message on canvas
                self.preview_canvas.create_text(
                    hub_x, hub_y + 30,
                    text="Error drawing preview",
                    fill=self.theme_colors['muted'],
                    font=DEFAULT_FONT
                )
                
        except Exception as e:
            logger.error(f"Error updating preview: {e}")
            # Show error message on canvas
            try:
                self.preview_canvas.delete("all")
                self.preview_canvas.create_text(
                    self.preview_canvas.winfo_width() // 2,
                    self.preview_canvas.winfo_height() // 2,
                    text="Preview Error",
                    fill=self.theme_colors['muted'],
                    font=DEFAULT_FONT
                )
            except Exception:
                pass  # Ignore errors in error handling
    
    def _load_current_config(self):
        """Load current configuration values."""
        try:
            # Try to get configuration from the parent fleet builder tab (walk widget objects)
            parent_widget = self
            while True:
                parent_widget = getattr(parent_widget, 'master', None)
                if not parent_widget:
                    break
                try:
                    if hasattr(parent_widget, 'fleet_builder') and hasattr(parent_widget.fleet_builder, 'get_spoke_configuration'):
                        stored_config = parent_widget.fleet_builder.get_spoke_configuration()
                        if stored_config:
                            self.set_config(stored_config)
                            logger.info("Loaded spoke configuration from fleet builder")
                            return
                except Exception:
                    pass
            
            # Try to get configuration from the main GUI configuration (walk widget objects)
            parent_widget = self
            while True:
                parent_widget = getattr(parent_widget, 'master', None)
                if not parent_widget:
                    break
                try:
                    if hasattr(parent_widget, 'cfg') and hasattr(parent_widget.cfg, 'spoke_config'):
                        main_config = parent_widget.cfg.spoke_config
                        if main_config:
                            self.set_config(main_config)
                            logger.info("Loaded spoke configuration from main GUI config")
                            return
                except Exception:
                    pass
            
            # If no configuration found, use defaults
            logger.info("No saved spoke configuration found, using defaults")
            self.var_spoke_count.set(True)  # Always enable variable spoke count
            self.spoke_count_var.set(10)
            
            # Ensure the spinner is in the correct state
            self._update_spinner_state()
            
            # Ensure preview is updated after config is loaded
            operation_id = self.after(200, self._refresh_preview_after_config)
            self._pending_operations.add(operation_id)
            
        except Exception as e:
            logger.error(f"Error loading current config: {e}")
            # Set defaults on error
            self.var_spoke_count.set(True)  # Always enable variable spoke count
            self.spoke_count_var.set(10)
            self._update_spinner_state()
    
    def _refresh_preview_after_config(self):
        """Refresh preview after configuration is loaded."""
        try:
            if hasattr(self, 'preview_canvas') and self.preview_canvas:
                # Force a preview update
                self._force_preview_update()
        except Exception as e:
            logger.error(f"Error refreshing preview after config: {e}")
    
    def get_config(self) -> dict:
        """Get the current spoke configuration."""
        try:
            if not self.distance_vars:
                return {}

            # Ensure the configuration is consistent
            # Tolerate empty edits by falling back to last valid values
            distances: List[float] = []
            for i in range(len(self.distance_vars)):
                value = self._safe_get_distance(i)
                if value is None:
                    # Fall back to last valid or a sensible default
                    if i < len(self.last_valid_distances):
                        value = float(self.last_valid_distances[i])
                    else:
                        value = 500.0
                distances.append(value)

            max_spokes_val = self._safe_get_spoke_count(default=self.last_valid_spoke_count)
            if max_spokes_val is None:
                max_spokes_val = len(distances) if distances else 10

            config = {
                'variable_spoke_count': True,  # Always True since we removed the checkbox
                'max_spokes': int(max_spokes_val),
                'spoke_distances': distances,
            }

            # Validate spoke distances
            if config['spoke_distances']:
                config['spoke_distances'] = [
                    max(100.0, min(1200.0, distance)) 
                    for distance in config['spoke_distances']
                ]

            return config

        except Exception as e:
            logger.error(f"Error getting config: {e}")
            # Return safe defaults on error
            return {
                'variable_spoke_count': True,  # Always True since we removed the checkbox
                'max_spokes': 10,
                'spoke_distances': [500.0] * 10
            }
    
    def set_config(self, config: dict):
        """Set the spoke configuration from a config dict."""
        try:
            # Always set variable spoke count to True
            self.var_spoke_count.set(True)

            if 'max_spokes' in config:
                self.spoke_count_var.set(config['max_spokes'])
                try:
                    self.last_valid_spoke_count = int(config['max_spokes'])
                except Exception:
                    pass
                # Create distance inputs after setting the spoke count
                self._create_distance_inputs()

            if 'spoke_distances' in config:
                distances = config['spoke_distances']
                if self.distance_vars:
                    for i, var in enumerate(self.distance_vars):
                        if i < len(distances):
                            var.set(distances[i])
                            if i < len(self.last_valid_distances):
                                try:
                                    self.last_valid_distances[i] = float(distances[i])
                                except Exception:
                                    pass

            # Ensure spinner state is correct after loading config
            self._update_spinner_state()
            
            # Update preview after all configuration is set
            operation_id = self.after(100, self._update_preview)
            self._pending_operations.add(operation_id)
            
        except Exception as e:
            logger.error(f"Error setting config: {e}")
            # Set defaults on error
            self.var_spoke_count.set(True)  # Always True
            self.spoke_count_var.set(10)
            self._update_spinner_state()
    
    def destroy(self):
        """Clean up resources when destroying the widget."""
        try:
            # Save configuration before destroying
            self.save_configuration()
            
            # Cancel any pending updates
            if self._preview_update_id:
                try:
                    self.after_cancel(self._preview_update_id)
                except Exception:
                    pass
            
            # Clear references to prevent memory leaks
            self.distance_vars.clear()
            self.on_config_changed = None
            
            # Clear canvas to free memory
            if hasattr(self, 'preview_canvas'):
                try:
                    self.preview_canvas.delete("all")
                except Exception:
                    pass
            
            # Call parent destroy
            super().destroy()
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            # Ensure parent destroy is called even if cleanup fails
            try:
                super().destroy()
            except Exception:
                pass
    
    def _show_spoke_config_error(self, title: str, message: str):
        """Show error state in spoke configuration area."""
        try:
            # Create error dialog
            create_error_dialog(
                parent=self,
                title=title,
                message=message,
                error_details=self._gather_spoke_config_diagnostic_info(),
                retry_callback=None,
                close_callback=None
            )
        except Exception as e:
            logger.error(f"Error showing spoke config error: {e}")
            # Fallback to simple message box
            messagebox.showerror(title, message)
    
    def _gather_spoke_config_diagnostic_info(self) -> str:
        """Gather diagnostic information for spoke configuration errors."""
        try:
            info_lines = []
            info_lines.append("=== SPOKE CONFIGURATION DIAGNOSTIC INFORMATION ===")
            info_lines.append(f"Timestamp: {self._get_current_timestamp()}")
            info_lines.append(f"Panel Type: {type(self).__name__}")
            
            # Check configuration state
            info_lines.append("Variable Spoke Count: Always Enabled (True)")
            info_lines.append(f"Spoke Count: {self.spoke_count_var.get()}")
            info_lines.append(f"Distance Variables Count: {len(self.distance_vars) if self.distance_vars else 0}")
            
            # Check UI state
            info_lines.append(f"Distances Container: {self.distances_container is not None}")
            info_lines.append(f"Preview Canvas: {self.preview_canvas is not None}")
            
            if self.distances_container:
                info_lines.append(f"Container Children: {len(self.distances_container.winfo_children())}")
            
            if self.preview_canvas:
                info_lines.append(f"Canvas Width: {self.preview_canvas.winfo_width()}")
                info_lines.append(f"Canvas Height: {self.preview_canvas.winfo_height()}")
            
            # Check distance values
            if self.distance_vars:
                distance_values = []
                for i, var in enumerate(self.distance_vars):
                    try:
                        value = var.get()
                        distance_values.append(f"Spoke {i+1}: {value}")
                    except Exception as e:
                        distance_values.append(f"Spoke {i+1}: Error - {str(e)}")
                info_lines.append("Distance Values:")
                info_lines.extend(f"  {d}" for d in distance_values)
            
            return "\n".join(info_lines)
            
        except Exception as e:
            logger.error(f"Error gathering spoke config diagnostic info: {e}")
            return f"Failed to gather spoke configuration diagnostic information: {str(e)}"
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp for diagnostic information."""
        try:
            import datetime
            return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return "Unknown"

    # ------------------------------------------------------------------
    # Preview update scheduling helpers
    # ------------------------------------------------------------------

    def _schedule_preview_update(self, delay: int = 100) -> None:
        """Safely (re)schedule a preview update for this panel."""
        if self._preview_update_id:
            try:
                self.after_cancel(self._preview_update_id)
            except Exception:
                pass
        operation_id = self.after(delay, self._update_preview)
        self._preview_update_id = operation_id
        self._pending_operations.add(operation_id)


class FleetBuilderTab(ttk.Frame):
    """Main fleet builder tab with aircraft palette and fleet canvas."""
    
    def __init__(self, parent, configuration_manager=None, **kwargs):
        super().__init__(parent, **kwargs)
        
        # Get managers
        self.config_manager = get_aircraft_config_manager()
        self.fleet_builder = get_fleet_builder()
        self.configuration_manager = configuration_manager  # Store ConfigurationManager reference
        
        # Callbacks
        self.on_fleet_changed: Optional[Callable[[], None]] = None
        
        # Track pending operations
        self._pending_operations = set()
        
        self._build_ui()
        self._load_default_fleet()
        
        # Bind destroy event to clean up pending operations
        self.bind('<Destroy>', self._on_destroy)
    
    def _build_ui(self):
        """Build the fleet builder UI."""
        # Main layout
        main_frame = ttk.Frame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Left panel: Aircraft palette and spoke configuration
        left_panel = ttk.Frame(main_frame)
        left_panel.pack(side="left", fill="y", padx=(0, 10))
        
        # Aircraft palette
        self.aircraft_palette = AircraftPalette(left_panel, self.config_manager)
        self.aircraft_palette.pack(fill="x", pady=(0, 10))
        
        # Spoke configuration panel
        self.spoke_config_panel = SpokeConfigurationPanel(left_panel, self.config_manager, self.configuration_manager)
        self.spoke_config_panel.pack(fill="x", pady=(0, 10))
        self.spoke_config_panel.on_config_changed = self._on_spoke_config_changed
        
        # Right panel: Fleet canvas and controls
        right_panel = ttk.Frame(main_frame)
        right_panel.pack(side="right", fill="both", expand=True)
        
        # Fleet controls
        controls_frame = ttk.Frame(right_panel)
        controls_frame.pack(fill="x", pady=(0, 10))
        
        # Fleet name input
        name_frame = ttk.Frame(controls_frame)
        name_frame.pack(fill="x", pady=(0, 8))
        
        ttk.Label(name_frame, text="Fleet Name:").pack(side="left")
        self.fleet_name_var = tk.StringVar(value="Custom Fleet")
        name_entry = ttk.Entry(name_frame, textvariable=self.fleet_name_var, width=30)
        name_entry.pack(side="left", padx=(8, 0))
        
        # Fleet actions
        actions_frame = ttk.Frame(controls_frame)
        actions_frame.pack(fill="x")
        
        # Load preset button
        load_btn = ttk.Button(actions_frame, text="Load Preset", 
                             command=self._show_load_preset_dialog)
        load_btn.pack(side="left", padx=(0, 8))
        
        # Save preset button
        save_btn = ttk.Button(actions_frame, text="Save Preset", 
                             command=self._save_fleet_preset)
        save_btn.pack(side="left", padx=(0, 8))
        
        # Info button
        info_btn = ttk.Button(actions_frame, text="ℹ️", width=3,
                             command=self._show_info_popup)
        info_btn.pack(side="right")
        
        # Fleet canvas
        self.fleet_canvas = FleetCanvas(right_panel, self.fleet_builder)
        self.fleet_canvas.pack(fill="both", expand=True)
        
        # Bind aircraft selection
        self.aircraft_palette.on_aircraft_selected = self._on_aircraft_selected
        
        # Bind fleet changes to update fleet name
        self.fleet_canvas.on_fleet_changed = self._on_fleet_composition_changed
    
    def _on_fleet_composition_changed(self):
        """Handle fleet composition changes to update fleet name."""
        try:
            # Update fleet name automatically when fleet changes
            self._update_fleet_name()
            
            # Notify parent of fleet changes
            if self.on_fleet_changed:
                self.on_fleet_changed()
        except Exception as e:
            logger.error(f"Error handling fleet composition change: {e}")
    
    def _reset_fleet_name_to_default(self):
        """Reset fleet name to default when fleet is cleared."""
        try:
            if hasattr(self, 'fleet_name_var'):
                self.fleet_name_var.set("Custom Fleet")
                logger.info("Fleet name reset to default")
        except Exception as e:
            logger.error(f"Error resetting fleet name: {e}")
    
    def _set_fleet_name_from_preset(self, preset_name: str):
        """Set fleet name from preset name."""
        try:
            if hasattr(self, 'fleet_name_var'):
                self.fleet_name_var.set(preset_name)
                logger.info(f"Fleet name set from preset: {preset_name}")
        except Exception as e:
            logger.error(f"Error setting fleet name from preset: {e}")
    
    def refresh_fleet_name_display(self):
        """Refresh the fleet name display based on current fleet composition."""
        try:
            # Update fleet name automatically
            self._update_fleet_name()
        except Exception as e:
            logger.error(f"Error refreshing fleet name display: {e}")
    
    def _on_aircraft_selected(self, aircraft_type: str):
        """Handle aircraft selection from palette."""
        try:
            # Add aircraft to fleet with retry logic
            def add_aircraft_operation():
                return self.fleet_builder.add_aircraft(aircraft_type)
            
            try:
                success = retry_operation(add_aircraft_operation, 
                                        operation_name="Aircraft Addition")
            except Exception as e:
                logger.error(f"Failed to add aircraft '{aircraft_type}' after retries: {e}")
                self._show_aircraft_selection_error("Aircraft Addition Failed", 
                                                  f"Failed to add aircraft '{aircraft_type}' to the fleet.\n\nError: {str(e)}",
                                                  lambda: self._on_aircraft_selected(aircraft_type))
                return
            
            if success:
                # Refresh fleet display
                self.fleet_canvas._refresh_fleet_display()
                
                # Update fleet name automatically
                self._update_fleet_name()
                
                # Notify that fleet has changed
                if self.on_fleet_changed:
                    self.on_fleet_changed()
            else:
                self._show_aircraft_selection_error("Aircraft Addition Failed", 
                                                  f"Failed to add aircraft '{aircraft_type}' to the fleet.\n\nThis may indicate a configuration issue.",
                                                  lambda: self._on_aircraft_selected(aircraft_type))
                
        except Exception as e:
            logger.error(f"Error in aircraft selection: {e}")
            self._show_aircraft_selection_error("Aircraft Selection Error", 
                                              f"An unexpected error occurred while processing aircraft selection.\n\nError: {str(e)}",
                                              lambda: self._on_aircraft_selected(aircraft_type))
    
    def _show_aircraft_selection_error(self, title: str, message: str, retry_callback: Callable = None):
        """Show error state for aircraft selection failures."""
        try:
            # Create comprehensive error dialog
            create_error_dialog(
                parent=self,
                title=title,
                message=message,
                error_details=self._gather_aircraft_selection_diagnostic_info(),
                retry_callback=retry_callback,
                close_callback=None
            )
        except Exception as e:
            logger.error(f"Error showing aircraft selection error: {e}")
            # Fallback to simple message box
            messagebox.showerror(title, message)
    
    def _gather_aircraft_selection_diagnostic_info(self) -> str:
        """Gather diagnostic information for aircraft selection errors."""
        try:
            info_lines = []
            info_lines.append("=== AIRCRAFT SELECTION DIAGNOSTIC INFORMATION ===")
            info_lines.append(f"Timestamp: {self._get_current_timestamp()}")
            info_lines.append(f"Tab Type: {type(self).__name__}")
            
            # Check fleet builder state
            info_lines.append(f"Fleet Builder: {self.fleet_builder is not None}")
            if self.fleet_builder:
                info_lines.append(f"Fleet Builder Type: {type(self.fleet_builder).__name__}")
                
                # Check if add_aircraft method exists
                if hasattr(self.fleet_builder, 'add_aircraft'):
                    info_lines.append("add_aircraft method: Available")
                else:
                    info_lines.append("add_aircraft method: Missing")
                
                # Check current fleet
                if hasattr(self.fleet_builder, 'current_fleet'):
                    fleet = self.fleet_builder.current_fleet
                    info_lines.append(f"Current Fleet: {fleet is not None}")
                    if fleet:
                        info_lines.append(f"Fleet Type: {type(fleet).__name__}")
                        if hasattr(fleet, 'aircraft'):
                            info_lines.append(f"Current Aircraft Count: {len(fleet.aircraft) if fleet.aircraft else 0}")
            
            # Check UI state
            info_lines.append(f"Fleet Canvas: {hasattr(self, 'fleet_canvas')}")
            info_lines.append(f"Fleet Name Var: {hasattr(self, 'fleet_name_var')}")
            
            if hasattr(self, 'fleet_canvas'):
                info_lines.append(f"Canvas Type: {type(self.fleet_canvas).__name__}")
            
            if hasattr(self, 'fleet_name_var'):
                try:
                    current_name = self.fleet_name_var.get()
                    info_lines.append(f"Current Fleet Name: {current_name}")
                except Exception as e:
                    info_lines.append(f"Fleet Name Error: {str(e)}")
            
            return "\n".join(info_lines)
            
        except Exception as e:
            logger.error(f"Error gathering aircraft selection diagnostic info: {e}")
            return f"Failed to gather aircraft selection diagnostic information: {str(e)}"
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp for diagnostic information."""
        try:
            import datetime
            return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return "Unknown"
    
    def _on_spoke_config_changed(self):
        """Handle spoke configuration changes."""
        try:
            # Get spoke configuration safely
            if not hasattr(self, 'spoke_config_panel'):
                logger.warning("Spoke config panel not available")
                return
            
            config = self.spoke_config_panel.get_config()
            
            # Update fleet builder with new spoke configuration
            if hasattr(self.fleet_builder, 'update_spoke_configuration'):
                try:
                    self.fleet_builder.update_spoke_configuration(config)
                    logger.info("Spoke configuration updated successfully")
                except Exception as e:
                    logger.error(f"Error updating spoke configuration: {e}")
                    self._show_spoke_config_update_error("Spoke Configuration Update Failed", 
                                                       f"Failed to update spoke configuration in the fleet builder.\n\nError: {str(e)}")
                    return
            else:
                logger.info("Fleet builder does not have update_spoke_configuration method")
            
            # Notify that configuration has changed
            if self.on_fleet_changed:
                self.on_fleet_changed()
                
        except Exception as e:
            logger.error(f"Failed to update spoke configuration: {e}")
            self._show_spoke_config_update_error("Spoke Configuration Error", 
                                               f"An unexpected error occurred while updating spoke configuration.\n\nError: {str(e)}")
    
    def _show_spoke_config_update_error(self, title: str, message: str):
        """Show error state for spoke configuration update failures."""
        try:
            # Create comprehensive error dialog
            create_error_dialog(
                parent=self,
                title=title,
                message=message,
                error_details=self._gather_spoke_config_update_diagnostic_info(),
                retry_callback=self._on_spoke_config_changed,
                close_callback=None
            )
        except Exception as e:
            logger.error(f"Error showing spoke config update error: {e}")
            # Fallback to simple message box
            messagebox.showerror(title, message)
    
    def _gather_spoke_config_update_diagnostic_info(self) -> str:
        """Gather diagnostic information for spoke configuration update errors."""
        try:
            info_lines = []
            info_lines.append("=== SPOKE CONFIGURATION UPDATE DIAGNOSTIC INFORMATION ===")
            info_lines.append(f"Timestamp: {self._get_current_timestamp()}")
            info_lines.append(f"Tab Type: {type(self).__name__}")
            
            # Check spoke config panel
            info_lines.append(f"Spoke Config Panel: {hasattr(self, 'spoke_config_panel')}")
            if hasattr(self, 'spoke_config_panel'):
                panel = self.spoke_config_panel
                info_lines.append(f"Panel Type: {type(panel).__name__}")
                
                # Get current config
                try:
                    config = panel.get_config()
                    info_lines.append(f"Current Config: {config}")
                except Exception as e:
                    info_lines.append(f"Config Retrieval Error: {str(e)}")
            
            # Check fleet builder
            info_lines.append(f"Fleet Builder: {self.fleet_builder is not None}")
            if self.fleet_builder:
                info_lines.append(f"Fleet Builder Type: {type(self.fleet_builder).__name__}")
                
                # Check if update_spoke_configuration method exists
                if hasattr(self.fleet_builder, 'update_spoke_configuration'):
                    info_lines.append("update_spoke_configuration method: Available")
                else:
                    info_lines.append("update_spoke_configuration method: Missing")
            
            # Check callback
            info_lines.append(f"Fleet Changed Callback: {self.on_fleet_changed is not None}")
            
            return "\n".join(info_lines)
            
        except Exception as e:
            logger.error(f"Error gathering spoke config update diagnostic info: {e}")
            return f"Failed to gather spoke configuration update diagnostic information: {str(e)}"
    
    def _load_default_fleet(self):
        """Load the default fleet configuration."""
        try:
            # Try to load the last used fleet first
            if hasattr(self, 'master') and hasattr(self.master, 'master'):
                # Navigate up to find the main GUI instance
                main_gui = self.master.master
                while main_gui and not hasattr(main_gui, 'fleet_persistence'):
                    main_gui = main_gui.master
                
                if main_gui and hasattr(main_gui, 'fleet_persistence'):
                    try:
                        startup_fleet = main_gui.fleet_persistence.load_last_fleet()
                        if startup_fleet and startup_fleet.get("aircraft"):
                            # Load the last used fleet
                            fleet_config = {
                                "name": startup_fleet.get("name", "Last Used Fleet"),
                                "aircraft": startup_fleet.get("aircraft", {})
                            }
                            
                            success = self.fleet_builder.load_fleet_from_config(fleet_config)
                            if success:
                                self.fleet_canvas._refresh_fleet_display()
                                operation_id = self.after(100, self._update_fleet_name)
                                self._pending_operations.add(operation_id)
                                logger.info(f"Loaded last used fleet: {startup_fleet.get('name', 'Unknown')}")
                                
                                # Also try to restore spoke configuration if available
                                self._restore_spoke_configuration()
                                
                                # Try to restore spoke configuration from the saved fleet data
                                if "spoke_config" in startup_fleet and hasattr(self, 'spoke_config_panel'):
                                    try:
                                        self.spoke_config_panel.set_config(startup_fleet["spoke_config"])
                                        logger.info("Restored spoke configuration from saved fleet data")
                                    except Exception as e:
                                        logger.warning(f"Could not restore spoke configuration from fleet data: {e}")
                                
                                return
                            else:
                                logger.warning("Failed to load last used fleet, falling back to default")
                        else:
                            logger.info("No last used fleet found, using default")
                    except Exception as e:
                        logger.warning(f"Could not load last used fleet: {e}")
            
            # Load default fleet if no last used fleet or if loading failed
            if hasattr(self.fleet_builder, 'get_default_fleet'):
                default_fleet = self.fleet_builder.get_default_fleet()
                if default_fleet:
                    self.fleet_builder.load_fleet_from_preset(default_fleet)
                    self.fleet_canvas._refresh_fleet_display()
                    
                    # Update fleet name after loading default fleet
                    operation_id = self.after(100, self._update_fleet_name)
                    self._pending_operations.add(operation_id)
                    
                    logger.info(f"Loaded default fleet: {default_fleet}")
            else:
                logger.info("Fleet builder does not have get_default_fleet method")
        except Exception as e:
            logger.error(f"Error loading default fleet: {e}")
    
    def _on_destroy(self, event):
        """Handle widget destruction to clean up pending operations."""
        try:
            # Cancel all pending operations
            for operation_id in self._pending_operations:
                try:
                    self.after_cancel(operation_id)
                except:
                    pass
            self._pending_operations.clear()
            
            # Reset counters
            if hasattr(self, '_canvas_wait_count'):
                self._canvas_wait_count = 0
            if hasattr(self, '_force_update_count'):
                self._force_update_count = 0
                
            logger.debug("Cleaned up pending operations on widget destruction")
        except Exception as e:
            logger.debug(f"Error during cleanup: {e}")

    def _restore_spoke_configuration(self):
        """Restore spoke configuration from saved config if available."""
        try:
            if hasattr(self, 'master') and hasattr(self.master, 'master'):
                # Navigate up to find the main GUI instance
                main_gui = self.master.master
                while main_gui and not hasattr(main_gui, 'cfg'):
                    main_gui = main_gui.master
                
                if main_gui and hasattr(main_gui, 'cfg') and hasattr(main_gui.cfg, 'spoke_config'):
                    spoke_config = main_gui.cfg.spoke_config
                    if spoke_config and hasattr(self, 'spoke_config_panel'):
                        # Restore to the spoke config panel
                        self.spoke_config_panel.set_config(spoke_config)
                        
                        # Also sync with the main simulation configuration
                        if 'spoke_distances' in spoke_config and hasattr(main_gui.cfg, 'spoke_distances'):
                            main_gui.cfg.spoke_distances = spoke_config['spoke_distances']
                            logger.info(f"Synced spoke distances with main config: {len(main_gui.cfg.spoke_distances)} spokes")
                        
                        logger.info("Restored spoke configuration from saved config")
        except Exception as e:
            logger.warning(f"Could not restore spoke configuration: {e}")
    
    def _show_load_preset_dialog(self):
        """Show dialog to load a fleet preset."""
        try:
            # Get available presets safely
            if not hasattr(self.fleet_builder, 'config_manager'):
                messagebox.showerror("Error", "Fleet builder configuration manager not available")
                return
            
            presets = self.fleet_builder.config_manager.get_all_fleet_presets()
            
            if not presets:
                messagebox.showinfo("No Presets", "No fleet presets available.")
                return
            
            # Create preset selection dialog
            dialog = tk.Toplevel(self)
            dialog.title("Load Fleet Preset")
            dialog.geometry("400x300")
            dialog.resizable(False, False)
            dialog.transient(self)
            dialog.grab_set()
            
            # Preset list
            ttk.Label(dialog, text="Select a fleet preset to load:").pack(pady=(20, 10))
            
            listbox = tk.Listbox(dialog, height=10)
            listbox.pack(fill="both", expand=True, padx=20, pady=(0, 20))
            
            # Populate listbox safely
            for preset in presets:
                if preset and hasattr(preset, 'name'):
                    listbox.insert(tk.END, preset.name)
            
            # Buttons
            button_frame = ttk.Frame(dialog)
            button_frame.pack(fill="x", padx=20, pady=(0, 20))
            
            def load_selected():
                try:
                    selection = listbox.curselection()
                    if selection:
                        preset_name = listbox.get(selection[0])
                        # Set fleet name from preset before loading
                        self._set_fleet_name_from_preset(preset_name)
                        
                        # Load the preset using the fleet builder's method
                        preset = self.fleet_builder.config_manager.get_fleet_preset(preset_name)
                        if preset:
                            self.fleet_builder.create_fleet_from_preset(preset_name)
                            self.fleet_canvas._refresh_fleet_display()
                            # Update fleet name after loading preset
                            operation_id = self.after(100, self._update_fleet_name)
                            self._pending_operations.add(operation_id)
                        else:
                            messagebox.showerror("Error", f"Preset '{preset_name}' not found")
                            return
                        
                        dialog.destroy()
                    else:
                        messagebox.showwarning("No Selection", "Please select a preset to load.")
                except Exception as e:
                    logger.error(f"Error loading selected preset: {e}")
                    messagebox.showerror("Error", f"Failed to load preset: {e}")
            
            ttk.Button(button_frame, text="Load", command=load_selected).pack(side="left", padx=(0, 10))
            ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side="left")
            
        except Exception as e:
            logger.error(f"Failed to show preset dialog: {e}")
            messagebox.showerror("Error", f"Failed to show preset dialog: {e}")
    
    def _update_fleet_name(self):
        """Update fleet name based on current composition."""
        try:
            # Get fleet summary safely with retry logic
            def get_summary_operation():
                return self.fleet_builder.get_fleet_summary()
            
            try:
                summary = retry_operation(get_summary_operation, 
                                        operation_name="Fleet Name Summary Retrieval")
            except Exception as e:
                logger.error(f"Failed to retrieve fleet summary for name update after retries: {e}")
                # Don't show error dialog for name updates, just log and keep current name
                return
            
            if not summary or not validate_fleet_summary(summary):
                logger.warning("Invalid fleet summary for name update")
                return
            
            # Safely get aircraft breakdown
            aircraft_breakdown = safe_dict_get(summary, "aircraft_breakdown", {})
            if not aircraft_breakdown:
                # Fleet is empty, reset to default name
                self._reset_fleet_name_to_default()
                return
            
            # Generate descriptive name based on aircraft composition
            aircraft_counts = {}
            for aircraft_id, aircraft_info in aircraft_breakdown.items():
                if validate_aircraft_info(aircraft_info):
                    aircraft_type = safe_dict_get(aircraft_info, "name", "Unknown")
                    count = safe_dict_get(aircraft_info, "count", 0)
                    if aircraft_type in aircraft_counts:
                        aircraft_counts[aircraft_type] += count
                    else:
                        aircraft_counts[aircraft_type] = count
            
            if aircraft_counts:
                # Create descriptive name
                name_parts = []
                for aircraft_type, count in sorted(aircraft_counts.items()):
                    if count == 1:
                        name_parts.append(aircraft_type)
                    else:
                        name_parts.append(f"{count}x {aircraft_type}")
                
                new_name = " + ".join(name_parts)
                
                # Update fleet name safely
                try:
                    current_name = self.fleet_name_var.get()
                    if current_name != new_name:
                        self.fleet_name_var.set(new_name)
                        logger.info(f"Fleet name updated to: {new_name}")
                except Exception as e:
                    logger.error(f"Error updating fleet name variable: {e}")
            
        except Exception as e:
            logger.error(f"Error updating fleet name: {e}")
            # Don't show error dialog for name updates, just log and keep current name
    
    def _save_fleet_preset(self):
        """Save current fleet as a preset."""
        try:
            # Get current fleet name safely
            fleet_name = self.fleet_name_var.get()
            if not fleet_name or fleet_name.strip() == "":
                fleet_name = "Custom Fleet"
            
            # Get fleet composition safely
            if not hasattr(self.fleet_builder, 'get_fleet_composition'):
                logger.error("Fleet builder does not have get_fleet_composition method")
                self._show_fleet_save_error("Save Method Missing", 
                                          "The fleet builder does not support saving fleet compositions.\n\nThis may indicate a configuration issue.")
                return
            
            def get_composition_operation():
                return self.fleet_builder.get_fleet_composition()
            
            try:
                fleet_composition = retry_operation(get_composition_operation, 
                                                  operation_name="Fleet Composition Retrieval")
            except Exception as e:
                logger.error(f"Failed to retrieve fleet composition after retries: {e}")
                self._show_fleet_save_error("Unable to Save Fleet", 
                                          f"Failed to retrieve current fleet composition.\n\nError: {str(e)}",
                                          lambda: self._save_fleet_preset())
                return
            
            if not fleet_composition:
                logger.warning("No fleet composition to save")
                self._show_fleet_save_error("No Fleet to Save", 
                                          "There is no fleet composition to save.\n\nPlease add some aircraft to the fleet first.")
                return
            
            # Save fleet preset with retry logic
            def save_preset_operation():
                return self.fleet_builder.config_manager.save_fleet_preset(fleet_name, fleet_composition)
            
            try:
                success = retry_operation(save_preset_operation, 
                                        operation_name="Fleet Preset Save")
            except Exception as e:
                logger.error(f"Failed to save fleet preset after retries: {e}")
                self._show_fleet_save_error("Save Operation Failed", 
                                          f"Failed to save fleet preset '{fleet_name}'.\n\nError: {str(e)}",
                                          lambda: self._save_fleet_preset())
                return
            
            if success:
                # Refresh presets list
                if hasattr(self, 'preset_panel'):
                    self.preset_panel._refresh_presets()
                
                # Show success message
                messagebox.showinfo("Success", f"Fleet preset '{fleet_name}' saved successfully!")
                logger.info(f"Fleet preset '{fleet_name}' saved successfully")
            else:
                self._show_fleet_save_error("Save Failed", 
                                          f"Failed to save fleet preset '{fleet_name}'.\n\nThis may indicate a configuration or permission issue.",
                                          lambda: self._save_fleet_preset())
                
        except Exception as e:
            logger.error(f"Error saving fleet preset: {e}")
            self._show_fleet_save_error("Fleet Save Error", 
                                      f"An unexpected error occurred while saving the fleet preset.\n\nError: {str(e)}",
                                      lambda: self._save_fleet_preset())
    
    def _show_fleet_save_error(self, title: str, message: str, retry_callback: Callable = None):
        """Show error state for fleet save failures."""
        try:
            # Create comprehensive error dialog
            create_error_dialog(
                parent=self,
                title=title,
                message=message,
                error_details=self._gather_fleet_save_diagnostic_info(),
                retry_callback=retry_callback,
                close_callback=None
            )
        except Exception as e:
            logger.error(f"Error showing fleet save error: {e}")
            # Fallback to simple message box
            messagebox.showerror(title, message)
    
    def _gather_fleet_save_diagnostic_info(self) -> str:
        """Gather diagnostic information for fleet save errors."""
        try:
            info_lines = []
            info_lines.append("=== FLEET SAVE DIAGNOSTIC INFORMATION ===")
            info_lines.append(f"Timestamp: {self._get_current_timestamp()}")
            info_lines.append(f"Tab Type: {type(self).__name__}")
            
            # Check fleet builder
            info_lines.append(f"Fleet Builder: {self.fleet_builder is not None}")
            if self.fleet_builder:
                info_lines.append(f"Fleet Builder Type: {type(self.fleet_builder).__name__}")
                
                # Check required methods
                required_methods = ['get_fleet_composition']
                for method in required_methods:
                    if hasattr(self.fleet_builder, method):
                        info_lines.append(f"{method} method: Available")
                    else:
                        info_lines.append(f"{method} method: Missing")
            
            # Check configuration manager
            if hasattr(self.fleet_builder, 'config_manager'):
                config_mgr = self.fleet_builder.config_manager
                info_lines.append(f"Config Manager: {config_mgr is not None}")
                if config_mgr:
                    info_lines.append(f"Config Manager Type: {type(config_mgr).__name__}")
                    
                    # Check if save_fleet_preset method exists
                    if hasattr(config_mgr, 'save_fleet_preset'):
                        info_lines.append("save_fleet_preset method: Available")
                    else:
                        info_lines.append("save_fleet_preset method: Missing")
            else:
                info_lines.append("Config Manager: Not available")
            
            # Check UI state
            info_lines.append(f"Fleet Name Var: {hasattr(self, 'fleet_name_var')}")
            info_lines.append(f"Preset Panel: {hasattr(self, 'preset_panel')}")
            
            if hasattr(self, 'fleet_name_var'):
                try:
                    current_name = self.fleet_name_var.get()
                    info_lines.append(f"Current Fleet Name: {current_name}")
                except Exception as e:
                    info_lines.append(f"Fleet Name Error: {str(e)}")
            
            return "\n".join(info_lines)
            
        except Exception as e:
            logger.error(f"Error gathering fleet save diagnostic info: {e}")
            return f"Failed to gather fleet save diagnostic information: {str(e)}"
    
    def load_fleet_from_config(self, fleet_config):
        """Load fleet from configuration data or fleet label."""
        try:
            if not fleet_config:
                logger.warning("Attempted to load fleet from None config")
                self._show_fleet_load_error("Invalid Configuration", 
                                          "No fleet configuration provided.\n\nThis may indicate a configuration issue.")
                return
            
            # Handle fleet label strings by converting them to fleet configurations
            if isinstance(fleet_config, str):
                logger.info(f"Converting fleet label to configuration: {fleet_config}")
                # Try to create fleet from legacy label first
                fleet_composition = self.fleet_builder.create_fleet_from_legacy_label(fleet_config)
                if fleet_composition:
                    fleet_config = {
                        "name": fleet_composition.name,
                        "aircraft": fleet_composition.aircraft
                    }
                else:
                    # Fleet preset system removed - use current Fleet Builder pallet
                    logger.info("Fleet preset system removed - using current Fleet Builder pallet")
                    return
            
            # Load fleet with retry logic
            def load_fleet_operation():
                return self.fleet_builder.load_fleet_from_config(fleet_config)
            
            try:
                success = retry_operation(load_fleet_operation, 
                                        operation_name="Fleet Configuration Load")
            except Exception as e:
                logger.error(f"Failed to load fleet from config after retries: {e}")
                self._show_fleet_load_error("Fleet Load Failed", 
                                          f"Failed to load fleet from configuration.\n\nError: {str(e)}",
                                          lambda: self.load_fleet_from_config(fleet_config))
                return
            
            if success:
                # Refresh fleet display
                if hasattr(self, 'fleet_canvas'):
                    self.fleet_canvas._refresh_fleet_display()
                
                # Update fleet name
                self._update_fleet_name()
                
                # Notify that fleet has changed
                if self.on_fleet_changed:
                    self.on_fleet_changed()
                
                logger.info("Fleet loaded successfully from configuration")
            else:
                self._show_fleet_load_error("Fleet Load Failed", 
                                          "Failed to load fleet from configuration.\n\nThis may indicate a configuration or data issue.",
                                          lambda: self.load_fleet_from_config(fleet_config))
                
        except Exception as e:
            logger.error(f"Error loading fleet from config: {e}")
            self._show_fleet_load_error("Fleet Load Error", 
                                      f"An unexpected error occurred while loading the fleet.\n\nError: {str(e)}",
                                      lambda: self.load_fleet_from_config(fleet_config))
    
    def _show_fleet_load_error(self, title: str, message: str, retry_callback: Callable = None):
        """Show error state for fleet load failures."""
        try:
            # Create comprehensive error dialog
            create_error_dialog(
                parent=self,
                title=title,
                message=message,
                error_details=self._gather_fleet_load_diagnostic_info(),
                retry_callback=retry_callback,
                close_callback=None
            )
        except Exception as e:
            logger.error(f"Error showing fleet load error: {e}")
            # Fallback to simple message box
            messagebox.showerror(title, message)
    
    def _gather_fleet_load_diagnostic_info(self) -> str:
        """Gather diagnostic information for fleet load errors."""
        try:
            info_lines = []
            info_lines.append("=== FLEET LOAD DIAGNOSTIC INFORMATION ===")
            info_lines.append(f"Timestamp: {self._get_current_timestamp()}")
            info_lines.append(f"Tab Type: {type(self).__name__}")
            
            # Check fleet builder
            info_lines.append(f"Fleet Builder: {self.fleet_builder is not None}")
            if self.fleet_builder:
                info_lines.append(f"Fleet Builder Type: {type(self.fleet_builder).__name__}")
                
                # Check if load_fleet_from_config method exists
                if hasattr(self.fleet_builder, 'load_fleet_from_config'):
                    info_lines.append("load_fleet_from_config method: Available")
                else:
                    info_lines.append("load_fleet_from_config method: Missing")
            
            # Check UI state
            info_lines.append(f"Fleet Canvas: {hasattr(self, 'fleet_canvas')}")
            info_lines.append(f"Fleet Name Var: {hasattr(self, 'fleet_name_var')}")
            
            if hasattr(self, 'fleet_canvas'):
                info_lines.append(f"Canvas Type: {type(self.fleet_canvas).__name__}")
            
            if hasattr(self, 'fleet_name_var'):
                try:
                    current_name = self.fleet_name_var.get()
                    info_lines.append(f"Current Fleet Name: {current_name}")
                except Exception as e:
                    info_lines.append(f"Fleet Name Error: {str(e)}")
            
            # Check callback
            info_lines.append(f"Fleet Changed Callback: {self.on_fleet_changed is not None}")
            
            return "\n".join(info_lines)
            
        except Exception as e:
            logger.error(f"Error gathering fleet load diagnostic info: {e}")
            return f"Failed to gather fleet load diagnostic information: {str(e)}"
    
    def _show_info_popup(self):
        """Show information about the fleet builder."""
        try:
            info_text = """Fleet Builder Information

This tool allows you to:
• Configure spoke distances and count (1-20 spokes)
• View and adjust aircraft performance parameters
• Build custom fleet compositions
• Save fleet configurations as presets
• Visualize geographic layout of your network

The spoke configuration affects:
• Flight times between locations
• Fuel consumption calculations
• Cost analysis for operations
• Route optimization decisions

Aircraft performance settings include:
• Cruise speed (Mach to MPH conversion)
• Turnover time for cargo operations
• Operational range and fuel efficiency
• Cost per flight hour analysis"""
            
            info_window = tk.Toplevel(self)
            info_window.title("Fleet Builder Information")
            info_window.geometry("500x400")
            info_window.resizable(False, False)
            
            # Center the window
            info_window.transient(self)
            info_window.grab_set()
            
            # Create text widget
            text_widget = tk.Text(info_window, wrap="word", padx=20, pady=20)
            text_widget.pack(fill="both", expand=True)
            
            # Insert text
            text_widget.insert("1.0", info_text)
            text_widget.config(state="disabled")
            
            # Close button
            close_btn = ttk.Button(info_window, text="Close", 
                                  command=info_window.destroy)
            close_btn.pack(pady=(0, 20))
            
        except Exception as e:
            logger.error(f"Error showing info popup: {e}")
            messagebox.showerror("Error", f"Failed to show information: {e}")
    
    def destroy(self):
        """Clean up resources when destroying the widget."""
        try:
            # Clear callbacks to prevent memory leaks
            self.on_fleet_changed = None
            
            # Clean up sub-panels
            if hasattr(self, 'aircraft_palette'):
                try:
                    self.aircraft_palette.destroy()
                except Exception:
                    pass
            
            if hasattr(self, 'spoke_config_panel'):
                try:
                    self.spoke_config_panel.destroy()
                except Exception:
                    pass
            
            if hasattr(self, 'fleet_canvas'):
                try:
                    self.fleet_canvas.destroy()
                except Exception:
                    pass
            
            # Call parent destroy
            super().destroy()
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            # Ensure parent destroy is called even if cleanup fails
            try:
                super().destroy()
            except Exception:
                pass

    def get_current_fleet_label(self) -> str:
        """Return the fleet label in legacy format (e.g. "2xC130_1xC27").

        The back-end simulation code still relies on the legacy string label
        format.  We therefore adapt the FleetBuilder's current fleet
        composition into that format by delegating to
        FleetBuilder.export_fleet_to_legacy_format().  This keeps *all* logic
        for building the text inside the core FleetBuilder class and prevents
        accidental drift between GUI and simulation rules.
        """
        try:
            return self.fleet_builder.export_fleet_to_legacy_format()
        except Exception as e:
            logger.error(f"Failed to build fleet label: {e}")
            # Fall back to the text entry shown in the GUI so that the user's
            # intent is still preserved even if something went wrong.
            return self.fleet_name_var.get() or "2xC130"

    # ------------------------------------------------------------------
    # Tk-safe clean-up helpers
    # ------------------------------------------------------------------
    def destroy(self):
        """Ensure any scheduled callbacks are cancelled before widget teardown."""
        if hasattr(self, "_preview_update_id") and self._preview_update_id:
            try:
                self.after_cancel(self._preview_update_id)
            except Exception:
                pass
        super().destroy()
