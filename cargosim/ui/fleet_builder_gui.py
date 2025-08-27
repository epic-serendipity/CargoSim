"""Visual Fleet Composition Builder GUI for CargoSim."""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, List, Optional, Callable, Any
import json
import math
import logging

from .fleet_builder import (
    AircraftType, FleetComposition, FleetPreset, 
    AircraftConfigManager, FleetBuilder,
    get_aircraft_config_manager, get_fleet_builder
)

from ..rendering.themes.default_fonts import DEFAULT_FONT, DEFAULT_FONT_BOLD

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
        from ..rendering.themes.font_manager import font_manager
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
        
        from ..rendering.themes.font_manager import font_manager
        ttk.Label(header_frame, text="Available Aircraft", style="Header.TLabel", 
                 font=font_manager.get_font('header', 'bold')).pack(side="left")
        
        # Refresh button
        refresh_btn = ttk.Button(header_frame, text="🔄", width=3, 
                               command=self._refresh_aircraft_list)
        refresh_btn.pack(side="right")
        
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
        from ..rendering.themes.font_manager import font_manager
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
            from ..rendering.themes.font_manager import font_manager
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
            from ..rendering.themes.font_manager import font_manager
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
            
            from ..rendering.themes.font_manager import font_manager
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
            from ..rendering.themes.font_manager import font_manager
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
            from ..rendering.themes.font_manager import font_manager
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


class SpokeConfigurationPanel(ttk.Frame):
    """Panel for configuring spoke distances and counts for time and distance mechanics."""
    
    def __init__(self, parent, config_manager: AircraftConfigManager, **kwargs):
        super().__init__(parent, **kwargs)
        self.config_manager = config_manager
        self.on_config_changed: Optional[Callable[[], None]] = None
        
        # Initialize instance variables
        self.distance_vars = []
        self.var_spoke_count = tk.BooleanVar()
        self.spoke_count_var = tk.IntVar(value=10)
        self._preview_update_id: Optional[str] = None
        
        # Theme integration
        self.theme_colors = self._get_theme_colors()
        
        self._build_ui()
        self._load_current_config()
    
    def _get_theme_colors(self) -> dict:
        """Get current theme colors for the preview."""
        try:
            # Try to get theme colors from the parent GUI
            parent = self.winfo_parent()
            while parent:
                try:
                    if hasattr(parent, 'cfg') and hasattr(parent.cfg, 'theme'):
                        # We're in the main GUI, get theme colors
                        from ...core.config import create_palette_from_theme_config
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
        
        # Variable spoke count toggle
        var_check = ttk.Checkbutton(count_frame, text="Enable Variable Spoke Count", 
                                   variable=self.var_spoke_count, 
                                   command=self._on_variable_spoke_count_changed)
        var_check.pack(anchor="w", pady=(0, 4))
        
        # Spoke count selector
        count_selector_frame = ttk.Frame(count_frame)
        count_selector_frame.pack(fill="x", pady=(0, 4))
        
        ttk.Label(count_selector_frame, text="Number of Spokes:").pack(side="left")
        
        self.spoke_count_spinner = ttk.Spinbox(count_selector_frame, 
                                              from_=1, to=20, 
                                              textvariable=self.spoke_count_var,
                                              width=10,
                                              command=self._on_spoke_count_changed)
        self.spoke_count_spinner.pack(side="left", padx=(8, 0))
        
        # Spoke distances configuration
        distances_frame = ttk.LabelFrame(self, text="Spoke Distances (miles)", padding=8)
        distances_frame.pack(fill="x", padx=8, pady=(0, 8))
        
        # Distance inputs container
        self.distances_container = ttk.Frame(distances_frame)
        self.distances_container.pack(fill="x")
        
        # Create initial distance inputs
        self._create_distance_inputs()
        
        # Force preview update after creating inputs
        self.after(200, self._force_preview_update)
        
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
        self.after(100, self._initialize_preview)
    
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
                    self.after(200, self._update_preview)
            
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
            self.after(100, self._update_preview)
        except Exception as e:
            logger.error(f"Error handling preview frame resize: {e}")
    
    def _on_panel_resize(self, event):
        """Handle panel resize to update preview sizing."""
        try:
            # Update canvas height when panel is resized
            self._set_canvas_height()
            # Redraw preview with new dimensions
            self.after(100, self._update_preview)
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
                    self.after(100, self._update_preview)
            
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
            self.after(50, self._wait_for_canvas_size)
        except Exception as e:
            logger.error(f"Error initializing preview: {e}")
    
    def _wait_for_canvas_size(self):
        """Wait for canvas to be properly sized before drawing preview."""
        try:
            if hasattr(self, 'preview_canvas') and self.preview_canvas:
                canvas_width = self.preview_canvas.winfo_width()
                canvas_height = self.preview_canvas.winfo_height()
                
                if canvas_width > 1 and canvas_height > 1:
                    # Canvas is properly sized, draw the preview
                    self._update_preview()
                else:
                    # Canvas not yet sized, wait a bit more
                    # Use exponential backoff to avoid infinite waiting
                    if not hasattr(self, '_canvas_wait_count'):
                        self._canvas_wait_count = 0
                    
                    if self._canvas_wait_count < 10:  # Max 10 attempts
                        self._canvas_wait_count += 1
                        self.after(100, self._wait_for_canvas_size)
                    else:
                        # Force update after max attempts
                        logger.warning("Canvas size wait timeout, forcing preview update")
                        self._force_preview_update()
            else:
                logger.warning("Preview canvas not available for initialization")
        except Exception as e:
            logger.error(f"Error waiting for canvas size: {e}")
    
    def _create_distance_inputs(self):
        """Create distance input fields for each spoke."""
        # Clear existing inputs
        for widget in self.distances_container.winfo_children():
            widget.destroy()
        
        # Clear distance variables list
        self.distance_vars.clear()
        
        # Create grid for distance inputs
        for i in range(self.spoke_count_var.get()):
            row = i // 5  # 5 columns per row
            col = i % 5
            
            # Spoke label
            label = ttk.Label(self.distances_container, text=f"Spoke {i+1}:")
            label.grid(row=row, column=col*2, padx=(0, 4), pady=2, sticky="e")
            
            # Distance input
            distance_var = tk.DoubleVar(value=500.0)
            distance_entry = ttk.Entry(self.distances_container, 
                                     textvariable=distance_var,
                                     width=8,
                                     validate="key",
                                     validatecommand=(self.register(self._validate_distance), '%P'))
            distance_entry.grid(row=row, column=col*2+1, padx=(0, 8), pady=2, sticky="w")
            
            # Store reference to variable
            self.distance_vars.append(distance_var)
            
            # Bind change event using a proper method reference
            distance_var.trace('w', self._create_distance_change_callback(i))
        
        # Update preview after creating inputs
        self.after(100, self._force_preview_update)
    
    def _refresh_preview_after_config(self):
        """Refresh preview after configuration changes."""
        try:
            # Force preview update after configuration changes
            self.after(100, self._force_preview_update)
        except Exception as e:
            logger.error(f"Error refreshing preview after config: {e}")
    
    def _force_preview_update(self):
        """Force update the preview with retry logic."""
        try:
            if hasattr(self, 'preview_canvas') and self.preview_canvas:
                # Check if canvas is ready
                canvas_width = self.preview_canvas.winfo_width()
                canvas_height = self.preview_canvas.winfo_height()
                
                if canvas_width > 1 and canvas_height > 1:
                    self._update_preview()
                else:
                    # Canvas not ready, try again
                    self.after(100, self._force_preview_update)
            else:
                logger.warning("Preview canvas not available for force update")
        except Exception as e:
            logger.error(f"Error in force preview update: {e}")
    
    def _create_distance_change_callback(self, index):
        """Create a callback function for distance changes to avoid lambda memory leaks."""
        def callback(*args):
            self._on_distance_changed(index)
        return callback
    
    def _validate_distance(self, value):
        """Validate distance input (100-1200 miles)."""
        if value == "":
            return True
        try:
            distance = float(value)
            return 100.0 <= distance <= 1200.0
        except ValueError:
            return False
    
    def _on_variable_spoke_count_changed(self):
        """Handle variable spoke count toggle change."""
        try:
            if self.var_spoke_count.get():
                self.spoke_count_spinner.config(state="normal")
            else:
                self.spoke_count_spinner.config(state="disabled")
            
            if self.on_config_changed:
                self.on_config_changed()
        except Exception as e:
            logger.error(f"Error in variable spoke count change: {e}")
            self._show_spoke_config_error("Spoke Count Error", 
                                        f"Failed to update spoke count configuration.\n\nError: {str(e)}")
    
    def _on_spoke_count_changed(self):
        """Handle spoke count change."""
        try:
            self._create_distance_inputs()
            
            # Ensure preview is updated after spoke count change
            self.after(150, self._force_preview_update)
            
            if self.on_config_changed:
                self.on_config_changed()
        except Exception as e:
            logger.error(f"Error in spoke count change: {e}")
            self._show_spoke_config_error("Spoke Count Change Error", 
                                        f"Failed to update spoke count.\n\nError: {str(e)}")
    
    def _on_distance_changed(self, index):
        """Handle distance input change."""
        try:
            self._update_preview()
            if self.on_config_changed:
                self.on_config_changed()
        except Exception as e:
            logger.error(f"Error in distance change: {e}")
            self._show_spoke_config_error("Distance Change Error", 
                                        f"Failed to update distance configuration.\n\nError: {str(e)}")
    
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
            # This would be populated from the actual simulation config
            # For now, use defaults
            self.var_spoke_count.set(False)
            self.spoke_count_var.set(10)
            
            # Ensure preview is updated after config is loaded
            self.after(200, self._refresh_preview_after_config)
        except Exception as e:
            logger.error(f"Error loading current config: {e}")
    
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
            
            return {
                'variable_spoke_count': self.var_spoke_count.get(),
                'max_spokes': self.spoke_count_var.get(),
                'spoke_distances': [var.get() for var in self.distance_vars]
            }
        except Exception as e:
            print(f"Error getting config: {e}")
            return {}
    
    def set_config(self, config: dict):
        """Set the spoke configuration from a config dict."""
        try:
            if 'variable_spoke_count' in config:
                self.var_spoke_count.set(config['variable_spoke_count'])
            
            if 'max_spokes' in config:
                self.spoke_count_var.set(config['max_spokes'])
                self._create_distance_inputs()
            
            if 'spoke_distances' in config:
                distances = config['spoke_distances']
                if self.distance_vars:
                    for i, var in enumerate(self.distance_vars):
                        if i < len(distances):
                            var.set(distances[i])
            
            self._update_preview()
        except Exception as e:
            logger.error(f"Error setting config: {e}")
    
    def destroy(self):
        """Clean up resources when destroying the widget."""
        try:
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
            info_lines.append(f"Variable Spoke Count: {self.var_spoke_count.get()}")
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
        self._preview_update_id = self.after(delay, self._update_preview)


class FleetBuilderTab(ttk.Frame):
    """Main fleet builder tab with aircraft palette and fleet canvas."""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        
        # Get managers
        self.config_manager = get_aircraft_config_manager()
        self.fleet_builder = get_fleet_builder()
        
        # Callbacks
        self.on_fleet_changed: Optional[Callable[[], None]] = None
        
        self._build_ui()
        self._load_default_fleet()
    
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
        self.spoke_config_panel = SpokeConfigurationPanel(left_panel, self.config_manager)
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
            # Load default fleet if available
            if hasattr(self.fleet_builder, 'get_default_fleet'):
                default_fleet = self.fleet_builder.get_default_fleet()
                if default_fleet:
                    self.fleet_builder.load_fleet_from_preset(default_fleet)
                    self.fleet_canvas._refresh_fleet_display()
                    
                    # Update fleet name after loading default fleet
                    self.after(100, self._update_fleet_name)
                    
                    logger.info(f"Loaded default fleet: {default_fleet}")
            else:
                logger.info("Fleet builder does not have get_default_fleet method")
        except Exception as e:
            logger.error(f"Error loading default fleet: {e}")
    
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
                        self.load_fleet_from_config(preset_name)
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
