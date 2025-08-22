"""Pygame rendering and visualization for CargoSim."""

import os
import math
import time
from typing import List, Tuple, Optional, Dict, Any
from types import SimpleNamespace
from dataclasses import dataclass
from functools import lru_cache

# Import pygame at module level to ensure it's available throughout
try:
    import pygame
except ImportError:
    pygame = None

from .config import (
    SAFE_PAD_PCT, SAFE_PAD_MIN_PX, LEFT_RAIL_PCT, LEFT_RAIL_MIN_PX,
    RIGHT_RAIL_PCT, RIGHT_RAIL_MIN_PX, VIS_CAPS_DFLT, M,
    CURSOR_COLORS, hex2rgb, blend
)
from .simulation import LogisticsSim, is_ops_capable, _row_to_spoke
from .recorder import Recorder, NullRecorder
from .utils import clamp, _mp4_available, log_runtime_event, log_exception

# Animation constants
ANIMATION_MIDPOINT = 0.5
ANIMATION_ROTATION_START = 0.15
AIRCRAFT_SIZE_C130 = 14
AIRCRAFT_SIZE_C27 = 10
AIRCRAFT_LABEL_OFFSET = 16
CURSOR_HOVER_RADIUS = 18
CURSOR_HIGHLIGHT_RADIUS = 12
SPOKE_BAR_WIDTH = 8
SPOKE_BAR_GAP = 4
SPOKE_CIRCLE_RADIUS = 9
SPOKE_ARC_RADIUS = 14
SPOKE_ARC_SEGMENTS = 12
SPOKE_ARC_PULSE_SPEED = 1.8
SPOKE_LABEL_LIFT = 4
SPOKE_LABEL_GAP = 6
SPOKE_BAR_MAX_HEIGHT = 28
SPOKE_BAR_MAX_RATIO = 2.0

# Enhanced animation constants for the new state machine
AIRCRAFT_STATES = {
    'IDLE_AT_HUB': 'IDLE_AT_HUB',
    'LOADING': 'LOADING',
    'DEPARTING': 'DEPARTING',
    'ENROUTE': 'ENROUTE',
    'ARRIVING': 'ARRIVING',
    'UNLOADING': 'UNLOADING',
    'RESTING': 'RESTING',
    'BROKEN_AT_HUB': 'BROKEN_AT_HUB',
    'BROKEN_AT_SPOKE': 'BROKEN_AT_SPOKE'
}

# Animation timing constants
MIN_VISIBLE_BAR_HEIGHT = 2  # Minimum height for non-zero values
BAR_ANIMATION_DURATION = 0.25  # Seconds for bar height transitions
BAR_GEOMETRIC_GAMMA = 0.6  # Default gamma for geometric scaling
BAR_LINEAR_MODE = 'linear'
BAR_GEOMETRIC_MODE = 'geometric'

# Enhanced spoke bar constants
SPOKE_BAR_DISPLAY_CAPS = [4, 4, 4, 4]  # Default display caps for A, B, C, D
SPOKE_BAR_ROLLING_PERCENTILE = 0.75  # P75 for rolling cap calculation

# Layout constants
HEADER_HEIGHT_PCT = 0.04
HEADER_HEIGHT_MIN = 28
INNER_PADDING_FACTOR = 0.8
DEFAULT_WINDOW_WIDTH = 1200
DEFAULT_WINDOW_HEIGHT = 850

# New layout constants for the specification
HEADER_TOGGLE_ENABLED = True  # Control panel toggle for header visibility
MICRO_BAR_WIDTH = 6
MICRO_BAR_HEIGHT = 12
MICRO_BAR_GAP = 2
SPARKLINE_HEIGHT = 80
SPARKLINE_WIDTH_PCT = 0.8

# Menu constants
PAUSE_MENU_WIDTH = 420
PAUSE_MENU_HEIGHT = 280
PAUSE_MENU_BUTTON_WIDTH = 40
PAUSE_MENU_BUTTON_HEIGHT = 44
PAUSE_MENU_BUTTON_SPACING = 56
PAUSE_MENU_START_Y = 72
PAUSE_MENU_BORDER_RADIUS = 12
PAUSE_MENU_BUTTON_RADIUS = 8

# Debug overlay constants
DEBUG_OVERLAY_WIDTH_PCT = 0.45
DEBUG_OVERLAY_HEIGHT_PCT = 0.35
DEBUG_OVERLAY_ALPHA = 160
DEBUG_OVERLAY_X_OFFSET = 20
DEBUG_OVERLAY_Y_OFFSET = 60
DEBUG_OVERLAY_PADDING = 8
DEBUG_OVERLAY_LINE_HEIGHT = 18
DEBUG_MAX_LINES = 18

# Recording overlay constants
RECORDING_WATERMARK_COLOR = (255, 0, 0)
RECORDING_OVERLAY_START_Y = 16
RECORDING_OVERLAY_SPACING = 4

# Side panel constants
SIDE_PANEL_BAR_HEIGHT_PCT = 0.25
SIDE_PANEL_BAR_WIDTH = 24
SIDE_PANEL_BAR_GAP = 18
SIDE_PANEL_ROW_HEIGHT = 24
SIDE_PANEL_BAR_RADIUS = 6
SIDE_PANEL_LABEL_LIFT_FACTOR = 0.6


@lru_cache(maxsize=128)
def compute_spoke_positions(radius: int, center_x: int, center_y: int, spoke_count: int = M) -> List[Tuple[int, int]]:
    """Cache spoke position calculations for better performance."""
    positions = []
    for idx in range(spoke_count):
        theta = 2 * math.pi * idx / spoke_count
        x = center_x + (radius - 20) * math.cos(theta)
        y = center_y + (radius - 20) * math.sin(theta)
        # Ensure coordinates snap to integers to prevent jitter
        positions.append((int(x), int(y)))
    return positions


@lru_cache(maxsize=64)
def create_aircraft_triangle(size: int) -> List[Tuple[int, int]]:
    """Cache aircraft triangle vertices."""
    return [(0, -size), (-size//2, size//2), (size//2, size//2)]


@dataclass
class Layout:
    """Layout rectangles for the renderer."""
    w: int
    h: int
    pad: int
    left: "pygame.Rect"
    right: "pygame.Rect"
    map: "pygame.Rect"
    left_inner: "pygame.Rect"
    right_inner: "pygame.Rect"
    header_rect: "pygame.Rect"
    header_visible: bool = True  # New field for header toggle


@dataclass
class AircraftSegment:
    """Represents a movement segment for aircraft animation."""
    p0: Tuple[int, int]  # Start position (pixel coordinates)
    p1: Tuple[int, int]  # End position (pixel coordinates)
    d: float  # Euclidean distance
    t_move: int  # Visual duration in frames
    start_frame: int  # Start frame for this segment
    end_frame: int  # End frame for this segment
    start_time: float  # Start time for this segment
    end_time: float  # End time for this segment


@dataclass
class SpokeBarState:
    """Represents the current state of spoke resource bars."""
    current_heights: List[float]  # Current animated heights
    target_heights: List[float]  # Target heights to animate toward
    last_update: float  # Last time the heights were updated
    display_caps: List[float]  # Current display caps for normalization
    scaling_mode: str  # 'linear' or 'geometric'
    gamma: float  # Gamma value for geometric scaling


def compute_layout(w: int, h: int, header_visible: bool = True) -> Layout:
    """Compute the layout rectangles for the UI."""
    # Ensure all coordinates snap to integers to prevent jitter
    pad = max(SAFE_PAD_MIN_PX, int(min(w, h) * SAFE_PAD_PCT))
    lw = max(LEFT_RAIL_MIN_PX, int(w * LEFT_RAIL_PCT))
    rw = max(RIGHT_RAIL_MIN_PX, int(w * RIGHT_RAIL_PCT))
    
    # Left rail (metrics panel)
    r_left = pygame.Rect(pad, pad, lw, h - 2 * pad)
    
    # Right rail (trend panel)
    r_right = pygame.Rect(w - rw - pad, pad, rw, h - 2 * pad)
    
    # Central map (hub + spokes + aircraft)
    map_left = r_left.right + pad
    map_width = r_right.left - map_left - pad
    r_map = pygame.Rect(map_left, pad, map_width, h - 2 * pad)
    
    # Inner padding for rails
    li = r_left.inflate(-int(pad * INNER_PADDING_FACTOR), -int(pad * INNER_PADDING_FACTOR))
    ri = r_right.inflate(-int(pad * INNER_PADDING_FACTOR), -int(pad * INNER_PADDING_FACTOR))
    
    # Header at top of central map (only if visible)
    if header_visible:
        header_h = max(int(h * HEADER_HEIGHT_PCT), HEADER_HEIGHT_MIN)
        header = pygame.Rect(r_map.left, r_map.top, r_map.width, header_h)
        # Adjust map to account for header
        r_map.y += header_h
        r_map.height -= header_h
    else:
        # No header - use full map area
        header = pygame.Rect(r_map.left, r_map.top, r_map.width, 0)
    
    return Layout(w, h, pad, r_left, r_right, r_map, li, ri, header, header_visible)


@dataclass
class ThemeTokens:
    """Theme color tokens for the renderer."""
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
    ac_colors: Dict[str, Tuple[int, int, int]]
    panel_bg: Tuple[int, int, int]
    panel_btn: Tuple[int, int, int]
    panel_btn_fg: Tuple[int, int, int]
    overlay_backdrop_rgba: Tuple[int, int, int, int]
    # Semantic color tokens
    primary: Tuple[int, int, int]
    secondary: Tuple[int, int, int]
    success: Tuple[int, int, int]
    warning: Tuple[int, int, int]
    error: Tuple[int, int, int]
    info: Tuple[int, int, int]


class VizState:
    """Base class for visualization state."""
    layout: Optional[Layout] = None
    width: int = 0
    height: int = 0
    cx: int = 0
    cy: int = 0
    radius: int = 0
    spoke_pos: List[Tuple[int, int]] = None
    hub_text: Optional["pygame.Surface"] = None
    spoke_text: List["pygame.Surface"] = None
    bar_letter_surfs: List["pygame.Surface"] = None
    font_big: Optional["pygame.font.Font"] = None
    font_small: Optional["pygame.font.Font"] = None


class Renderer(VizState):
    """Main pygame renderer for CargoSim."""
    
    def __init__(self, sim: LogisticsSim, *, force_windowed: bool = False):
        """Initialize the renderer."""
        try:
            log_runtime_event("Starting Renderer initialization", f"force_windowed={force_windowed}")
            
            # Input validation
            log_runtime_event("Validating Renderer inputs")
            if not hasattr(sim, 'cfg'):
                raise ValueError("sim must have a cfg attribute")
            if not hasattr(sim.cfg, 'launch_fullscreen'):
                raise ValueError("sim.cfg must have launch_fullscreen attribute")
            if not hasattr(sim.cfg, 'debug_mode'):
                raise ValueError("sim.cfg must have debug_mode attribute")
            log_runtime_event("Renderer input validation passed")
            
            # Store configuration for lazy initialization
            log_runtime_event("Setting up Renderer configuration")
            self.sim = sim
            self.force_windowed = force_windowed
            self._pygame_initialized = False
            self._display_initialized = False
            
            # Initialize basic attributes
            log_runtime_event("Initializing Renderer basic attributes")
            self.flags = 0  # Will be set when pygame is initialized
            self.fullscreen = sim.cfg.launch_fullscreen and not force_windowed
            self.screen = None
            self.surface = None
            self.clock = None

            self._hud_cache: Dict[str, Tuple[str, "pygame.Surface"]] = {}
            self._pm_rects: Dict[str, Any] = {}
            self._last_heading_by_ac: Dict[str, float] = {}
            
            # Enhanced debug mode management
            self.show_debug = bool(self.sim.cfg.debug_mode)
            self.debug_level = 1  # 0=off, 1=basic, 2=detailed
            self.debug_lines: List[str] = []
            self.debug_timestamp = time.time()
            self.debug_message_count = 0
            
            # Debug mode persistence
            self.debug_mode_persistent = bool(self.sim.cfg.debug_mode)
            
            # Simulation completion tracking
            self.simulation_completed = False
            self.completion_time = None
            
            # Simulation timing
            self.period_seconds = 1.0
            self.last_step_time = 0.0
            
            # Visualization settings
            self.include_side_panels = True
            self.bar_cols = []  # Will be set after theme is applied
            self.ac_colors = {}  # Will be set after theme is applied
            
            # Header visibility toggle
            self.header_visible = getattr(sim.cfg, "viz_show_header", True)
            
            # Enhanced aircraft animation system
            self.aircraft_segments: Dict[str, AircraftSegment] = {}  # Aircraft name -> current segment
            self.aircraft_states: Dict[str, str] = {}  # Aircraft name -> current visual state
            self.aircraft_positions: Dict[str, Tuple[int, int]] = {}  # Aircraft name -> current position
            self.aircraft_headings: Dict[str, float] = {}  # Aircraft name -> current heading
            self.aircraft_stagger_delays: Dict[str, int] = {}  # Aircraft name -> frame delay for staggering
            self.current_frame = 0
            self.frames_per_period = 10  # Default, will be updated from config
            
            # Enhanced spoke bar system
            self.spoke_bar_states: List[SpokeBarState] = []  # One per spoke
            self.bar_scaling_mode = BAR_LINEAR_MODE
            self.bar_gamma = BAR_GEOMETRIC_GAMMA
            self.bar_animation_enabled = True
            
            # Simulation state
            self.paused = False
            self.show_safe_area = False
            self.exit_code = None
            self.menu_open = False

            log_runtime_event("Setting up Renderer display options", f"fullscreen={self.fullscreen}")
            
            # Apply theme and initialize graphics pipeline (will be done lazily)
            log_runtime_event("Setting up Renderer lazy initialization flags")
            self._theme_applied = False
            self._gfx_pipeline_initialized = False
            
            log_runtime_event("Renderer initialization completed successfully")
            
        except Exception as e:
            log_exception(e, "Renderer initialization")
            raise

    def __del__(self):
        """Destructor to ensure proper cleanup."""
        try:
            self._cleanup_simulation()
        except:
            pass  # Don't raise exceptions in destructor
    
    def _ensure_pygame_initialized(self):
        """Ensure pygame is initialized when needed."""
        if not self._pygame_initialized:
            try:
                log_runtime_event("Starting pygame initialization")
                
                # Check pygame availability
                if pygame is None:
                    log_runtime_event("pygame is None - not available", level="ERROR")
                    raise RuntimeError("pygame is required to run the simulator.")
                
                log_runtime_event("pygame module is available")
                
                if not pygame.get_init():
                    log_runtime_event("Calling pygame.init()")
                    pygame.init()
                    log_runtime_event("pygame.init() completed")
                else:
                    log_runtime_event("pygame already initialized")
                
                # Set flags now that pygame is available
                log_runtime_event("Setting pygame flags")
                self.flags = pygame.RESIZABLE
                
                self._pygame_initialized = True
                log_runtime_event("pygame initialization completed successfully")
                
            except Exception as e:
                log_exception(e, "_ensure_pygame_initialized")
                raise

    def _map_aircraft_state(self, ac_state: str, ac_location: str) -> str:
        """Map simulation aircraft state to visual state machine state."""
        if ac_state == "IDLE":
            if ac_location == "HUB":
                return AIRCRAFT_STATES['IDLE_AT_HUB']
            else:
                return AIRCRAFT_STATES['RESTING']
        elif ac_state == "LEG1_ENROUTE":
            return AIRCRAFT_STATES['ENROUTE']
        elif ac_state == "AT_SPOKEA":
            return AIRCRAFT_STATES['UNLOADING']
        elif ac_state == "AT_SPOKEB_ENROUTE":
            return AIRCRAFT_STATES['ENROUTE']
        elif ac_state == "AT_SPOKEB":
            return AIRCRAFT_STATES['UNLOADING']
        elif ac_state == "RETURN_ENROUTE":
            return AIRCRAFT_STATES['ENROUTE']
        else:
            return AIRCRAFT_STATES['IDLE_AT_HUB']

    def _create_aircraft_segment(self, ac_name: str, start_pos: Tuple[int, int], 
                                end_pos: Tuple[int, int], start_frame: int) -> AircraftSegment:
        """Create a movement segment for aircraft animation."""
        dx = end_pos[0] - start_pos[0]
        dy = end_pos[1] - start_pos[1]
        distance = math.sqrt(dx*dx + dy*dy)
        
        # Reference distance is hub to spoke distance
        ref_distance = math.sqrt((self.spoke_pos[0][0] - self.cx)**2 + (self.spoke_pos[0][1] - self.cy)**2)
        
        # Calculate movement duration based on distance
        t_move = max(1, int(self.frames_per_period * min(1.0, distance / ref_distance)))
        
        # Add stagger delay to prevent overlapping departures
        stagger_delay = self.aircraft_stagger_delays.get(ac_name, 0)
        start_frame += stagger_delay
        
        return AircraftSegment(
            p0=start_pos,
            p1=end_pos,
            d=distance,
            t_move=t_move,
            start_frame=start_frame,
            end_frame=start_frame + t_move,
            start_time=time.time(),
            end_time=time.time() + (t_move / self.frames_per_period) * self.period_seconds
        )

    def _update_aircraft_animation(self, current_time: float):
        """Update aircraft animation state and positions."""
        for ac in self.sim.fleet:
            ac_name = ac.name
            
            # Update visual state based on simulation state
            new_visual_state = self._map_aircraft_state(ac.state, ac.location)
            if ac_name not in self.aircraft_states or self.aircraft_states[ac_name] != new_visual_state:
                self.aircraft_states[ac_name] = new_visual_state
                self._initialize_aircraft_state(ac_name, ac, new_visual_state)
            
            # Special handling for RETURN_ENROUTE: ensure movement segment exists
            if ac.state == "RETURN_ENROUTE" and ac_name not in self.aircraft_segments:
                # Force creation of return movement segment
                start_pos, end_pos = self._get_aircraft_movement_positions(ac)
                if start_pos and end_pos and start_pos != end_pos:
                    segment = self._create_aircraft_segment(ac_name, start_pos, end_pos, self.current_frame)
                    self.aircraft_segments[ac_name] = segment
            
            # Update position and heading based on current segment
            if ac_name in self.aircraft_segments:
                segment = self.aircraft_segments[ac_name]
                self._update_aircraft_position(ac_name, segment, current_time)
            else:
                # Aircraft is stationary, update position based on location
                self._update_stationary_aircraft(ac_name, ac)

    def _initialize_aircraft_state(self, ac_name: str, ac, visual_state: str):
        """Initialize aircraft state when it changes."""
        if visual_state in [AIRCRAFT_STATES['DEPARTING'], AIRCRAFT_STATES['ENROUTE']]:
            # Aircraft is moving, create movement segment
            start_pos, end_pos = self._get_aircraft_movement_positions(ac)
            if start_pos and end_pos and start_pos != end_pos:
                # Add random stagger delay (0-3 frames) for departures, not returns
                if ac_name not in self.aircraft_stagger_delays:
                    import random
                    # No delay for return flights to ensure smooth animation
                    if ac.state == "RETURN_ENROUTE":
                        self.aircraft_stagger_delays[ac_name] = 0
                    else:
                        self.aircraft_stagger_delays[ac_name] = random.randint(0, 3)
                
                segment = self._create_aircraft_segment(ac_name, start_pos, end_pos, self.current_frame)
                self.aircraft_segments[ac_name] = segment
        else:
            # Aircraft is stationary, clear any existing segment
            if ac_name in self.aircraft_segments:
                del self.aircraft_segments[ac_name]

    def _get_aircraft_movement_positions(self, ac) -> Tuple[Optional[Tuple[int, int]], Optional[Tuple[int, int]]]:
        """Get start and end positions for aircraft movement."""
        if ac.location == "HUB":
            start_pos = (self.cx, self.cy)
        elif ac.location.startswith("S"):
            spoke_idx = int(ac.location[1:]) - 1
            if 0 <= spoke_idx < len(self.spoke_pos):
                start_pos = self.spoke_pos[spoke_idx]
            else:
                start_pos = (self.cx, self.cy)
        else:
            start_pos = (self.cx, self.cy)
        
        # Determine destination based on plan and state
        if ac.state == "LEG1_ENROUTE" and ac.plan:
            # Moving from HUB to first spoke
            first_spoke = ac.plan[0]
            if 0 <= first_spoke < len(self.spoke_pos):
                end_pos = self.spoke_pos[first_spoke]
            else:
                end_pos = start_pos
        elif ac.state == "AT_SPOKEB_ENROUTE" and ac.plan:
            # Moving between spokes
            second_spoke = ac.plan[1]
            if second_spoke is not None and 0 <= second_spoke < len(self.spoke_pos):
                end_pos = self.spoke_pos[second_spoke]
            else:
                end_pos = start_pos
        elif ac.state == "RETURN_ENROUTE":
            # Moving from current spoke back to HUB
            end_pos = (self.cx, self.cy)
        else:
            # No movement - aircraft is stationary
            end_pos = start_pos
        
        return start_pos, end_pos

    def _update_aircraft_position(self, ac_name: str, segment: AircraftSegment, current_time: float):
        """Update aircraft position based on current movement segment."""
        if current_time < segment.start_time:
            # Segment hasn't started yet
            pos = segment.p0
            angle = -math.pi/2  # North orientation
        elif current_time >= segment.end_time:
            # Segment completed
            pos = segment.p1
            # Calculate final heading
            dx = segment.p1[0] - segment.p0[0]
            dy = segment.p1[1] - segment.p0[1]
            angle = math.atan2(dy, dx)
            # Clear completed segment
            del self.aircraft_segments[ac_name]
        else:
            # Segment in progress
            progress = (current_time - segment.start_time) / (segment.end_time - segment.start_time)
            progress = max(0.0, min(1.0, progress))
            
            # Apply ease-in/ease-out
            eased_progress = 3 * progress * progress - 2 * progress * progress * progress
            
            # Linear interpolation
            x = segment.p0[0] + (segment.p1[0] - segment.p0[0]) * eased_progress
            y = segment.p0[1] + (segment.p1[1] - segment.p0[1]) * eased_progress
            pos = (int(x), int(y))
            
            # Calculate heading toward destination
            dx = segment.p1[0] - segment.p0[0]
            dy = segment.p1[1] - segment.p0[1]
            angle = math.atan2(dy, dx)
        
        self.aircraft_positions[ac_name] = pos
        self.aircraft_headings[ac_name] = angle

    def _update_stationary_aircraft(self, ac_name: str, ac):
        """Update position for stationary aircraft."""
        if ac.location == "HUB":
            pos = (self.cx, self.cy)
            angle = -math.pi/2  # North orientation
        elif ac.location.startswith("S"):
            spoke_idx = int(ac.location[1:]) - 1
            if 0 <= spoke_idx < len(self.spoke_pos):
                pos = self.spoke_pos[spoke_idx]
                # Keep last heading or point outward from hub
                if ac_name in self.aircraft_headings:
                    angle = self.aircraft_headings[ac_name]
                else:
                    # Point outward from hub
                    dx = pos[0] - self.cx
                    dy = pos[1] - self.cy
                    angle = math.atan2(dy, dx)
            else:
                pos = (self.cx, self.cy)
                angle = -math.pi/2
        else:
            pos = (self.cx, self.cy)
            angle = -math.pi/2
        
        self.aircraft_positions[ac_name] = pos
        self.aircraft_headings[ac_name] = angle

    def _initialize_spoke_bar_states(self):
        """Initialize spoke bar states for all spokes."""
        if not self.spoke_bar_states:
            for i in range(len(self.sim.stock)):
                bar_state = SpokeBarState(
                    current_heights=[0.0] * 4,
                    target_heights=[0.0] * 4,
                    last_update=time.time(),
                    display_caps=SPOKE_BAR_DISPLAY_CAPS.copy(),
                    scaling_mode=self.bar_scaling_mode,
                    gamma=self.bar_gamma
                )
                self.spoke_bar_states.append(bar_state)

    def _update_spoke_bar_caps(self):
        """Update display caps for spoke bars based on current stock values."""
        if not self.spoke_bar_states:
            return
        
        # Calculate rolling caps based on current stock values
        for resource_idx in range(4):  # A, B, C, D
            values = [self.sim.stock[s][resource_idx] if s < len(self.sim.stock) else 0 
                     for s in range(len(self.sim.stock))]
            
            if values:
                # Use P75 as rolling cap
                sorted_values = sorted(values)
                p75_idx = int(len(sorted_values) * SPOKE_BAR_ROLLING_PERCENTILE)
                rolling_cap = sorted_values[p75_idx] if p75_idx < len(sorted_values) else max(values)
                
                # Update caps for all spokes
                for bar_state in self.spoke_bar_states:
                    bar_state.display_caps[resource_idx] = max(1.0, rolling_cap)

    def _calculate_bar_height(self, value: float, cap: float, mode: str, gamma: float) -> float:
        """Calculate bar height based on scaling mode."""
        if value <= 0:
            return MIN_VISIBLE_BAR_HEIGHT
        
        normalized = min(1.0, value / cap)
        
        if mode == BAR_GEOMETRIC_MODE:
            # Apply geometric scaling
            scaled = normalized ** gamma
        else:
            # Linear scaling
            scaled = normalized
        
        # Apply minimum height and maximum height constraints
        height = max(MIN_VISIBLE_BAR_HEIGHT, 
                    min(SPOKE_BAR_MAX_HEIGHT, scaled * SPOKE_BAR_MAX_HEIGHT))
        
        return height

    def _update_spoke_bar_heights(self, current_time: float):
        """Update spoke bar heights with smooth animation."""
        if not self.spoke_bar_states:
            return
        
        # Update display caps periodically
        if current_time - getattr(self, '_last_cap_update', 0) > 1.0:  # Update caps every second
            self._update_spoke_bar_caps()
            self._last_cap_update = current_time
        
        for i, bar_state in enumerate(self.spoke_bar_states):
            if i >= len(self.sim.stock):
                continue
            
            stock = self.sim.stock[i]
            
            for resource_idx in range(4):
                current_height = bar_state.current_heights[resource_idx]
                target_height = self._calculate_bar_height(
                    stock[resource_idx], 
                    bar_state.display_caps[resource_idx],
                    bar_state.scaling_mode,
                    bar_state.gamma
                )
                
                if self.bar_animation_enabled:
                    # Smooth animation toward target height
                    if abs(current_height - target_height) > 0.1:
                        time_diff = current_time - bar_state.last_update
                        animation_speed = 1.0 / BAR_ANIMATION_DURATION
                        delta = (target_height - current_height) * animation_speed * time_diff
                        
                        new_height = current_height + delta
                        # Ensure we don't overshoot
                        if (target_height > current_height and new_height > target_height) or \
                           (target_height < current_height and new_height < target_height):
                            new_height = target_height
                        
                        bar_state.current_heights[resource_idx] = new_height
                    else:
                        bar_state.current_heights[resource_idx] = target_height
                else:
                    # No animation - snap directly to target
                    bar_state.current_heights[resource_idx] = target_height
            
            bar_state.last_update = current_time

    def _draw_enhanced_spoke_bars(self):
        """Draw enhanced spoke bars with proper scaling and animation."""
        if not self.spoke_bar_states:
            return
        
        for i, (pos, bar_state) in enumerate(zip(self.spoke_pos, self.spoke_bar_states)):
            if i >= len(self.sim.stock):
                continue
            
            # Draw spoke label "S#" below the spoke
            spoke_label = f"S{i+1}"
            label_surf = self.font_small.render(spoke_label, True, self.tt.text)
            label_rect = label_surf.get_rect()
            label_rect.centerx = pos[0]
            label_rect.top = pos[1] + SPOKE_CIRCLE_RADIUS + SPOKE_LABEL_LIFT
            
            # Ensure coordinates snap to integers
            label_rect.x = int(label_rect.x)
            label_rect.y = int(label_rect.y)
            
            # Clamp label to remain inside the map
            if label_rect.left < self.layout.map.left:
                label_rect.left = self.layout.map.left + 5
            elif label_rect.right > self.layout.map.right:
                label_rect.right = self.layout.map.right - 5
            
            self.surface.blit(label_surf, label_rect)
            
            # Draw micro resource bars to the right of the label
            micro_bars_x = label_rect.right + SPOKE_LABEL_GAP
            micro_bars_y = label_rect.centery
            
            # Ensure bars fit within map bounds
            total_bar_width = 4 * MICRO_BAR_WIDTH + 3 * MICRO_BAR_GAP
            if micro_bars_x + total_bar_width > self.layout.map.right:
                # Adjust position to fit
                micro_bars_x = self.layout.map.right - total_bar_width - 5
            
            # Draw micro-bars for A/B/C/D
            for j, (color, current_height) in enumerate(zip(self.bar_cols, bar_state.current_heights)):
                bar_x = int(micro_bars_x + j * (MICRO_BAR_WIDTH + MICRO_BAR_GAP))
                bar_y = int(micro_bars_y - MICRO_BAR_HEIGHT // 2)
                bar_height = int(current_height)
                
                # Ensure minimum visibility for non-zero values
                if bar_height < MIN_VISIBLE_BAR_HEIGHT and self.sim.stock[i][j] > 0:
                    bar_height = MIN_VISIBLE_BAR_HEIGHT
                
                # Draw micro-bar
                bar_rect = pygame.Rect(bar_x, bar_y + MICRO_BAR_HEIGHT - bar_height,
                                     MICRO_BAR_WIDTH, bar_height)
                pygame.draw.rect(self.surface, color, bar_rect)
                pygame.draw.rect(self.surface, self.tt.text, bar_rect, 1)
                
                # Draw over-cap indicator if value exceeds cap
                if self.sim.stock[i][j] > bar_state.display_caps[j]:
                    over_cap_tick_y = bar_y
                    over_cap_tick_rect = pygame.Rect(bar_x, over_cap_tick_y, MICRO_BAR_WIDTH, 2)
                    pygame.draw.rect(self.surface, self.tt.warning, over_cap_tick_rect)

    def _draw_aircraft_state_indicator(self, pos: Tuple[int, int], state: str):
        """Draw visual indicator for aircraft state (loading/unloading)."""
        if state in [AIRCRAFT_STATES['LOADING'], AIRCRAFT_STATES['UNLOADING']]:
            # Draw a small pulsing ring around the aircraft
            current_time = time.time()
            pulse_scale = 1.0 + 0.3 * math.sin(current_time * 4.0)  # 4 Hz pulse
            
            indicator_radius = int(8 * pulse_scale)
            indicator_color = self.tt.info
            
            # Draw pulsing ring
            pygame.draw.circle(self.surface, indicator_color, pos, indicator_radius, 2)
            
            # Draw state text above aircraft
            state_text = "LOAD" if state == AIRCRAFT_STATES['LOADING'] else "UNLOAD"
            text_surf = self.font_small.render(state_text, True, indicator_color)
            text_rect = text_surf.get_rect()
            text_rect.centerx = pos[0]
            text_rect.bottom = pos[1] - 20
            
            self.surface.blit(text_surf, text_rect)

    def _ensure_display_initialized(self):
        """Ensure pygame display is initialized when needed."""
        if not self._display_initialized:
            try:
                log_runtime_event("Starting display initialization", f"fullscreen={self.fullscreen}")
                
                self._ensure_pygame_initialized()
                log_runtime_event("pygame initialization ensured")
                
                log_runtime_event("Setting display caption")
                pygame.display.set_caption("CargoSim — Hub–Spoke Logistics")
                
                if self.fullscreen:
                    log_runtime_event("Creating fullscreen display")
                    self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN | pygame.DOUBLEBUF)
                    log_runtime_event("Fullscreen display created", f"size={self.screen.get_size()}")
                else:
                    log_runtime_event("Creating windowed display", f"size=({DEFAULT_WINDOW_WIDTH}, {DEFAULT_WINDOW_HEIGHT})")
                    self.screen = pygame.display.set_mode((DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT), self.flags)
                    log_runtime_event("Windowed display created", f"size={self.screen.get_size()}")
                
                log_runtime_event("Setting up surface and clock")
                self.surface = self.screen
                self.clock = pygame.time.Clock()
                
                self._display_initialized = True
                log_runtime_event("Display initialization completed successfully")
                
            except Exception as e:
                log_exception(e, "_ensure_display_initialized")
                raise

    def _ensure_theme_applied(self):
        """Ensure theme is applied when needed."""
        if not self._theme_applied:
            self._apply_theme()
            self._theme_applied = True

    def _ensure_gfx_pipeline_initialized(self):
        """Ensure graphics pipeline is initialized when needed."""
        if not self._gfx_pipeline_initialized:
            self._ensure_display_initialized()
            self._ensure_theme_applied()
            
            w, h = pygame.display.get_surface().get_size()
            self._init_gfx_pipeline(w, h)
            self._gfx_pipeline_initialized = True

    def _apply_theme(self, theme_name: Optional[str] = None):
        """Apply a theme to the renderer."""
        if theme_name:
            from .config import apply_theme_preset
            apply_theme_preset(self.sim.cfg.theme, theme_name)
        t = self.sim.cfg.theme
        bg = hex2rgb(t.game_bg)
        text = hex2rgb(t.game_fg)
        muted = hex2rgb(t.game_muted)
        hub = hex2rgb(t.hub_color)
        good = hex2rgb(t.good_spoke)
        bad = hex2rgb(t.bad_spoke)
        self.tt = ThemeTokens(
            text=text,
            muted=muted,
            bg=bg,
            hub=hub,
            good_spoke=good,
            bad_spoke=bad,
            bar_A=hex2rgb(t.bar_A),
            bar_B=hex2rgb(t.bar_B),
            bar_C=hex2rgb(t.bar_C),
            bar_D=hex2rgb(t.bar_D),
            ac_colors={k: hex2rgb(v) for k, v in t.ac_colors.items()},
            panel_bg=blend(bg, text, 0.1),
            panel_btn=blend(bg, text, 0.2),
            panel_btn_fg=text,
            overlay_backdrop_rgba=(*bg, 160),
            # Semantic color tokens
            primary=hex2rgb(t.accent_primary),
            secondary=hex2rgb(t.accent_secondary),
            success=hex2rgb(t.success),
            warning=hex2rgb(t.warning),
            error=hex2rgb(t.error),
            info=hex2rgb(t.info),
        )
        
        # Set derived color attributes
        self.bar_cols = [self.tt.bar_A, self.tt.bar_B, self.tt.bar_C, self.tt.bar_D]
        self.ac_colors = {k: hex2rgb(v) for k, v in t.ac_colors.items()}

    def _text(self, text: str, font, color: Tuple[int, int, int]):
        """Render text to a surface."""
        if font is None:
            raise RuntimeError("Fonts not built yet; call _build_fonts before rendering text.")
        
        # Ensure pygame is available
        self._ensure_pygame_initialized()
        
        surf = font.render(text, True, color)
        disp = pygame.display.get_surface()
        if disp is not None:
            try:
                return surf.convert_alpha()
            except pygame.error:
                return surf
        return surf

    def _build_fonts(self, h: int):
        """Build font objects for the renderer."""
        # Ensure pygame is available
        self._ensure_pygame_initialized()
        
        big = clamp(int(h * 0.028), 16, 36)
        small = clamp(int(h * 0.018), 12, 20)
        pygame.font.init()
        self.font_big = pygame.font.SysFont(None, big)
        self.font_small = pygame.font.SysFont(None, small)

    def _init_gfx_pipeline(self, width: int, height: int) -> None:
        """Initialize the graphics pipeline."""
        assert getattr(self, "tt", None) is not None, "_apply_theme must run before init pipeline."
        self.layout = compute_layout(width, height, self.header_visible)
        
        # Update header visibility from config
        if hasattr(self.sim.cfg, "viz_show_header"):
            self.header_visible = self.sim.cfg.viz_show_header
            self.layout.header_visible = self.header_visible
        
        self.width, self.height = width, height
        # Ensure center coordinates snap to integers
        self.cx = int(self.layout.map.centerx)
        self.cy = int(self.layout.map.centery)
        self.radius = int(min(self.layout.map.width, self.layout.map.height) // 2 - self.layout.pad)
        self.spoke_pos = compute_spoke_positions(self.radius, self.cx, self.cy, M)
        for r in (self.layout.left, self.layout.right, self.layout.map):
            if r.width <= 0 or r.height <= 0:
                raise ValueError("layout rectangle collapsed")
        self._build_fonts(self.layout.h)
        self._compose_static()
        self._hud_cache = {}

        # Initialize spoke positions
        self.spoke_pos = compute_spoke_positions(self.radius, self.cx, self.cy, M)
        
        # Initialize enhanced systems
        self._initialize_spoke_bar_states()
        
        # Initialize aircraft positions and states
        for ac in self.sim.fleet:
            ac_name = ac.name
            if ac.location == "HUB":
                self.aircraft_positions[ac_name] = (self.cx, self.cy)
                self.aircraft_headings[ac_name] = -math.pi/2  # North orientation
            else:
                spoke_idx = int(ac.location[1:]) - 1
                if 0 <= spoke_idx < len(self.spoke_pos):
                    self.aircraft_positions[ac_name] = self.spoke_pos[spoke_idx]
                    # Point outward from hub
                    dx = self.spoke_pos[spoke_idx][0] - self.cx
                    dy = self.spoke_pos[spoke_idx][1] - self.cy
                    self.aircraft_headings[ac_name] = math.atan2(dy, dx)
                else:
                    self.aircraft_positions[ac_name] = (self.cx, self.cy)
                    self.aircraft_headings[ac_name] = -math.pi/2
            
            # Initialize visual state
            self.aircraft_states[ac_name] = self._map_aircraft_state(ac.state, ac.location)

    def _compose_static(self):
        """Compose static UI elements."""
        assert hasattr(self, "font_big")
        assert hasattr(self, "tt")
        self.hub_text = self._text("HUB", self.font_big, self.tt.text)
        self.spoke_text = [self._text(f"S{i+1}", self.font_small, self.tt.text) for i in range(M)]
        self.bar_letter_surfs = [self._text(ch, self.font_small, self.tt.muted) for ch in ["A", "B", "C", "D"]]

    def _init_display_headless_safe(self):
        """Initialize display in a headless-safe way."""
        self._ensure_pygame_initialized()
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        if not pygame.display.get_init():
            pygame.display.init()
        pygame.font.init()
        pygame.display.set_mode((1, 1), flags=pygame.HIDDEN)

    def change_theme(self, theme_name: str) -> None:
        """Change the current theme."""
        self._theme_applied = False
        self._apply_theme(theme_name)
        self._theme_applied = True
        if self._gfx_pipeline_initialized:
            w, h = pygame.display.get_surface().get_size()
            self._init_gfx_pipeline(w, h)

    def toggle_header(self):
        """Toggle header visibility."""
        self.header_visible = not self.header_visible
        # Save to configuration
        if hasattr(self.sim.cfg, "viz_show_header"):
            self.sim.cfg.viz_show_header = self.header_visible
        # Recompute layout to adjust map area
        if self.layout:
            w, h = pygame.display.get_surface().get_size()
            self._init_gfx_pipeline(w, h)

    def _toggle_fullscreen(self):
        """Toggle between fullscreen and windowed mode."""
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN | pygame.DOUBLEBUF)
        else:
            self.screen = pygame.display.set_mode((DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT), self.flags)
        self.surface = self.screen
        w, h = self.surface.get_size()
        if self.fullscreen:
            self.sim.cfg.recording.last_fullscreen_size = (w, h)
        self.sim.cfg.launch_fullscreen = self.fullscreen

    def draw_triangle(self, pos, typ, name, color, angle: float):
        """Draw an aircraft as a triangle."""
        x, y = int(pos[0]), int(pos[1])
        size = AIRCRAFT_SIZE_C130 if typ == "C-130" else AIRCRAFT_SIZE_C27
        base = create_aircraft_triangle(size)
        if self.sim.cfg.orient_aircraft:
            rot = angle + math.pi/2
        else:
            rot = 0.0
        c = math.cos(rot); s = math.sin(rot)
        pts = [(int(x + px*c - py*s), int(y + px*s + py*c)) for px, py in base]
        pygame.draw.polygon(self.surface, color, pts)
        show_lbl = self.sim.cfg.show_aircraft_labels or (self.recorder.live and self.sim.cfg.recording.include_labels)
        if show_lbl:
            t = self.font_small.render(name, True, self.tt.text)
            label_x = int(x - t.get_width()//2)
            label_y = int(y - size - AIRCRAFT_LABEL_OFFSET)
            self.surface.blit(t, (label_x, label_y))

    def _add_debug_message(self, message: str):
        """Add a debug message with timestamp."""
        timestamp = time.time() - self.debug_timestamp
        formatted_message = f"[{timestamp:.1f}s] {message}"
        self.debug_lines.append(formatted_message)
        self.debug_message_count += 1
        
        # Keep only the last DEBUG_MAX_LINES messages
        if len(self.debug_lines) > DEBUG_MAX_LINES:
            self.debug_lines = self.debug_lines[-DEBUG_MAX_LINES:]
    
    def draw_debug_overlay(self):
        """Draw the debug overlay with enhanced information."""
        if not self.show_debug:
            return
        
        # Calculate overlay dimensions
        overlay_width = int(self.layout.w * DEBUG_OVERLAY_WIDTH_PCT)
        overlay_height = int(self.layout.h * DEBUG_OVERLAY_HEIGHT_PCT)
        
        # Create overlay surface
        surf = pygame.Surface((overlay_width, overlay_height), pygame.SRCALPHA)
        surf.fill((0, 0, 0, DEBUG_OVERLAY_ALPHA))
        
        # Position overlay
        x0, y0 = DEBUG_OVERLAY_X_OFFSET, DEBUG_OVERLAY_Y_OFFSET
        
        # Draw title
        title_font = pygame.font.Font(None, 24)
        title_text = title_font.render("DEBUG OVERLAY", True, (255, 255, 255))
        title_rect = title_text.get_rect()
        title_rect.topleft = (x0 + DEBUG_OVERLAY_PADDING, y0 + DEBUG_OVERLAY_PADDING)
        surf.blit(title_text, title_rect)
        
        # Draw debug information based on level
        y = y0 + DEBUG_OVERLAY_PADDING + 30
        
        # Basic info (always shown when debug is on)
        basic_info = [
            f"Debug Level: {self.debug_level}",
            f"Messages: {self.debug_message_count}",
            f"Simulation Time: {self.sim.t} periods",
            f"Current Period: {self.sim.half}",
            f"Period Duration: {self.period_seconds:.1f}s",
            f"Fleet Size: {len(self.sim.fleet)} aircraft"
        ]
        
        for info in basic_info:
            text = self.font_small.render(info, True, (255, 255, 255))
            surf.blit(text, (x0 + DEBUG_OVERLAY_PADDING, y))
            y += DEBUG_OVERLAY_LINE_HEIGHT
        
        # Detailed info (level 2)
        if self.debug_level >= 2:
            y += 10  # Add spacing
            detailed_info = [
                f"Stock A: {sum(row[0] for row in self.sim.stock):.1f}",
                f"Stock B: {sum(row[1] for row in self.sim.stock):.1f}",
                f"Stock C: {sum(row[2] for row in self.sim.stock):.1f}",
                f"Stock D: {sum(row[3] for row in self.sim.stock):.1f}",
                f"Operations: {sum(self.sim.ops_by_spoke)}",
                f"Actions Log: {len(self.sim.actions_log)} entries"
            ]
            
            for info in detailed_info:
                text = self.font_small.render(info, True, (200, 200, 200))
                surf.blit(text, (x0 + DEBUG_OVERLAY_PADDING, y))
                y += DEBUG_OVERLAY_LINE_HEIGHT
            
            # Aircraft information
            y += 10  # Add spacing
            try:
                aircraft_info = self.get_aircraft_debug_info()
                for i, line in enumerate(aircraft_info[:6]):  # Limit to 6 lines to avoid overflow
                    text = self.font_small.render(line, True, (200, 200, 200))
                    surf.blit(text, (x0 + DEBUG_OVERLAY_PADDING, y))
                    y += DEBUG_OVERLAY_LINE_HEIGHT
            except Exception as e:
                error_text = self.font_small.render(f"Error getting aircraft info: {e}", True, (255, 150, 150))
                surf.blit(error_text, (x0 + DEBUG_OVERLAY_PADDING, y))
                y += DEBUG_OVERLAY_LINE_HEIGHT
            
            # Bar scaling mode
            bar_mode_text = f"Bar scaling: {self.bar_scaling_mode}"
            if self.bar_scaling_mode == BAR_GEOMETRIC_MODE:
                bar_mode_text += f" (γ={self.bar_gamma:.1f})"
            bar_mode_text += f" | Animation: {'ON' if self.bar_animation_enabled else 'OFF'}"
            
            mode_text = self.font_small.render(bar_mode_text, True, (200, 200, 200))
            surf.blit(mode_text, (x0 + DEBUG_OVERLAY_PADDING, y))
            y += DEBUG_OVERLAY_LINE_HEIGHT
        
        # Draw recent debug messages
        if self.debug_lines:
            y += 10  # Add spacing
            recent_messages = self.debug_lines[-8:]  # Show last 8 messages
            
            for message in recent_messages:
                text = self.font_small.render(message, True, (150, 255, 150))
                surf.blit(text, (x0 + DEBUG_OVERLAY_PADDING, y))
                y += DEBUG_OVERLAY_LINE_HEIGHT
        
        # Draw the overlay onto the main surface
        self.surface.blit(surf, (x0, y0))

    def draw_recording_overlays(self):
        """Draw recording-specific overlays."""
        if not self.recorder.live:
            return
        
        # Recording watermark
        watermark = self.font_small.render("REC", True, RECORDING_WATERMARK_COLOR)
        self.surface.blit(watermark, (10, RECORDING_OVERLAY_START_Y))
        
        # Recording info
        info_text = f"{self.recorder.fmt.upper()} • {self.recorder.fps}fps"
        info_surf = self.font_small.render(info_text, True, self.tt.muted)
        self.surface.blit(info_surf, (10, RECORDING_OVERLAY_START_Y + RECORDING_OVERLAY_SPACING))

    def draw_completion_overlay(self):
        """Draw completion overlay when simulation is finished."""
        # No overlay or text when simulation ends - just let it stop cleanly
        pass

    def run(self) -> Optional[str]:
        """Run the main simulation loop."""
        try:
            log_runtime_event("Starting renderer.run() main loop")
            
            # Ensure graphics pipeline is initialized before starting the event loop
            self._ensure_gfx_pipeline_initialized()
            log_runtime_event("Graphics pipeline initialized successfully")
            
            # Setup recording
            rcfg = self.sim.cfg.recording
            ok, _ = _mp4_available()
            fmt = "mp4" if (rcfg.record_live_format.lower() == "mp4" and ok) else "png"
            if rcfg.record_live_format.lower() == "mp4" and not ok:
                self.debug_lines.append("MP4 requires imageio-ffmpeg; recording PNG frames instead.")
            if rcfg.record_live_enabled:
                log_runtime_event("Setting up live recording", f"format={fmt}, fps={rcfg.fps}")
                self.recorder = Recorder.for_live(
                    folder=rcfg.record_live_folder,
                    fps=rcfg.fps,
                    fmt=fmt,
                    async_writer=rcfg.record_async_writer,
                    max_queue=rcfg.record_max_queue,
                    drop_on_backpressure=rcfg.record_skip_on_backpressure,
                )
                log_runtime_event("Live recording setup completed")
            else:
                log_runtime_event("Recording disabled, using NullRecorder")
                self.recorder = NullRecorder()

            # Setup simulation parameters
            log_runtime_event("Setting up simulation parameters")
            self.period_seconds = float(self.sim.cfg.period_seconds)
            self.frames_per_period = getattr(self.sim.cfg, 'frames_per_period', 10)
            
            log_runtime_event("Simulation parameters configured", f"period_seconds={self.period_seconds}, frames_per_period={self.frames_per_period}")
            
            # Main game loop
            log_runtime_event("Starting main game loop")
            running = True
            
            while running:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False
                        self.exit_code = "QUIT"
                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            if self.menu_open:
                                self.menu_open = False
                            else:
                                self.exit_code = "GUI"
                                running = False
                        elif event.key == pygame.K_F11:
                            self._toggle_fullscreen()
                        elif event.key == pygame.K_d:
                            # Enhanced debug toggle with multiple levels
                            if self.debug_mode_persistent:
                                # Cycle through debug levels: off -> basic -> detailed -> off
                                if self.show_debug:
                                    if self.debug_level == 1:
                                        self.debug_level = 2
                                        self.show_debug = True
                                        debug_status = "DETAILED"
                                    else:
                                        self.debug_level = 0
                                        self.show_debug = False
                                        debug_status = "OFF"
                                else:
                                    self.debug_level = 1
                                    self.show_debug = True
                                    debug_status = "BASIC"
                            else:
                                # Simple toggle if debug mode is not persistent
                                self.show_debug = not self.show_debug
                                debug_status = "ON" if self.show_debug else "OFF"
                            
                            log_runtime_event(f"Debug mode toggled: {debug_status} (level={self.debug_level})")
                            
                            # Add debug message to show current status
                            if self.show_debug:
                                self._add_debug_message(f"Debug Mode: {debug_status}")
                            else:
                                self._add_debug_message("Debug Mode: OFF")
                        elif event.key == pygame.K_F12:
                            # Alternative debug toggle key
                            self.show_debug = not self.show_debug
                            debug_status = "ON" if self.show_debug else "OFF"
                            log_runtime_event(f"Debug mode toggled via F12: {debug_status}")
                            if self.show_debug:
                                self._add_debug_message(f"Debug Mode: {debug_status}")
                            else:
                                self._add_debug_message("Debug Mode: OFF")
                        elif event.key == pygame.K_h:
                            # Header visibility toggle
                            self.toggle_header()
                            header_status = "ON" if self.header_visible else "OFF"
                            log_runtime_event(f"Header visibility toggled: {header_status}")
                            self._add_debug_message(f"Header: {header_status}")
                        elif event.key == pygame.K_s:
                            self.show_safe_area = not self.show_safe_area
                        elif event.key == pygame.K_SPACE:
                            self.paused = not self.paused
                        elif event.key == pygame.K_r:
                            # Restart simulation
                            self._restart_simulation()
                        elif event.key == pygame.K_b:
                            # Toggle bar scaling mode
                            if self.bar_scaling_mode == BAR_LINEAR_MODE:
                                self.set_bar_scaling_mode(BAR_GEOMETRIC_MODE)
                                self._add_debug_message("Bar scaling: Geometric")
                            else:
                                self.set_bar_scaling_mode(BAR_LINEAR_MODE)
                                self._add_debug_message("Bar scaling: Linear")
                        elif event.key == pygame.K_a:
                            # Toggle bar animation
                            self.toggle_bar_animation()
                            anim_status = "ON" if self.bar_animation_enabled else "OFF"
                            self._add_debug_message(f"Bar animation: {anim_status}")
                        elif event.key == pygame.K_g:
                            # Adjust gamma for geometric scaling
                            if self.bar_scaling_mode == BAR_GEOMETRIC_MODE:
                                # Cycle through gamma values
                                gamma_values = [0.3, 0.5, 0.6, 0.7, 0.8]
                                current_idx = gamma_values.index(self.bar_gamma) if self.bar_gamma in gamma_values else 2
                                next_idx = (current_idx + 1) % len(gamma_values)
                                new_gamma = gamma_values[next_idx]
                                self.set_bar_scaling_mode(BAR_GEOMETRIC_MODE, new_gamma)
                                self._add_debug_message(f"Gamma: {new_gamma}")
                    elif event.type == pygame.VIDEORESIZE and not self.fullscreen:
                        self.screen = pygame.display.set_mode((event.w, event.h), self.flags)
                        self._init_gfx_pipeline(event.w, event.h)

                # Check if it's time to step the simulation based on period_seconds
                current_time = time.time()
                should_step = (not self.paused and 
                             not self.simulation_completed and 
                             (current_time - self.last_step_time) >= self.period_seconds)
                
                # Store actions from previous step for rendering
                if not hasattr(self, '_previous_actions'):
                    self._previous_actions = []
                
                # Update spoke bar heights with smooth animation
                self._update_spoke_bar_heights(current_time)
                
                # Always render frame using previous simulation state
                # This ensures the renderer sees aircraft in RETURN_ENROUTE before they teleport to HUB
                self.render_frame(self._previous_actions, 1.0)
                
                if should_step:
                    # Update simulation AFTER rendering (only if not completed)
                    actions = self.sim.step_period()
                    self.last_step_time = current_time  # Update last step time
                    self.current_frame += self.frames_per_period
                    
                    # Store actions for next frame's rendering
                    self._previous_actions = actions if actions is not None else []
                    
                    # Clear completed aircraft segments at period boundaries
                    completed_segments = [name for name, segment in self.aircraft_segments.items() 
                                        if current_time >= segment.end_time]
                    for name in completed_segments:
                        del self.aircraft_segments[name]
                    
                    if actions is None:  # Simulation complete (reached max periods)
                        self.exit_code = "COMPLETE"
                        # Don't exit - show completion state and keep window open
                        self.simulation_completed = True
                        self.completion_time = time.time()
                        # Continue to render the final state
                        self._previous_actions = []  # Use empty actions for final render
                
                # If paused, draw pause menu overlay
                if self.paused:
                    self._draw_pause_menu()
                
                # Update display
                pygame.display.flip()
                
                # Cap frame rate
                if self.paused:
                    self.clock.tick(30)
                else:
                    self.clock.tick(60)

            log_runtime_event("Main game loop completed", f"exit_code={self.exit_code}")
            
            # Clean up simulation objects when returning to GUI
            if self.exit_code == "GUI":
                log_runtime_event("Cleaning up simulation objects for GUI return")
                self._cleanup_simulation()
            
            # Don't quit pygame - let the main function handle it
            log_runtime_event("Game loop completed, returning control to main function")
            
            return None
            
        except Exception as e:
            log_runtime_event("Exception in renderer.run()", f"error={e}")
            log_exception(e, "Renderer.run() main loop")
            # Ensure pygame is properly cleaned up even if there's an error
            try:
                pygame.quit()
                log_runtime_event("pygame.quit() called after exception")
            except:
                pass
            raise

    def render_frame(self, actions: List[Dict[str, Any]], alpha: float = 1.0, with_overlays: bool = True) -> None:
        """Render a single frame."""
        self._ensure_gfx_pipeline_initialized()
        # Clear screen
        self.surface.fill(self.tt.bg)
        
        # Draw layout elements
        if self.layout:
            # Draw side panels
            if self.include_side_panels:
                self._draw_left_panel()
                self._draw_right_panel()
            
            # Draw header at top of central map
            self._draw_header()
            
            # Draw main map area
            self._draw_map_area()
            
            # Draw aircraft
            self._draw_aircraft(actions, alpha)
            
            # Draw overlays
            if with_overlays:
                if self.show_debug:
                    self.draw_debug_overlay()
                if self.recorder.live:
                    self.draw_recording_overlays()
                if self.show_safe_area:
                    self._draw_safe_area()
                if self.simulation_completed:
                    self.draw_completion_overlay()

    def _draw_header(self):
        """Draw the header at the top of the central map."""
        if not self.layout or not self.layout.header_visible:
            return
        
        # Header content: Fleet label | Period X/Y (AM/PM, Day Z) | Ops a/b • Gate: A+B+C+D
        fleet_label = self.sim.cfg.fleet_label
        period = self.sim.t
        half = "AM" if period % 2 == 0 else "PM"
        day = period // 2
        
        # Count operational spokes
        ops_capable = sum(1 for i in range(M) if i < len(self.sim.op) and self.sim.op[i])
        total_spokes = M
        
        # Build header text
        header_text = f"{fleet_label} | Period {period} ({half}, Day {day}) | Ops {ops_capable}/{total_spokes}"
        
        # Simple text truncation if it would overflow the header area
        max_chars = int(self.layout.header_rect.width / 8)  # Approximate character width
        if len(header_text) > max_chars:
            header_text = header_text[:max_chars-3] + "..."
        
        # Render header text
        header_surf = self.font_big.render(header_text, True, self.tt.text)
        header_rect = header_surf.get_rect()
        header_rect.center = self.layout.header_rect.center
        
        # Ensure coordinates snap to integers
        header_rect.x = int(header_rect.x)
        header_rect.y = int(header_rect.y)
        
        # Draw header background
        pygame.draw.rect(self.surface, self.tt.panel_bg, self.layout.header_rect)
        pygame.draw.rect(self.surface, self.tt.text, self.layout.header_rect, 1)
        
        # Draw header text
        self.surface.blit(header_surf, header_rect)

    def _draw_map_area(self):
        """Draw the main map area (operational picture)."""
        if not self.layout:
            return
        
        # 4.1 Hub - centered in the map region
        pygame.draw.circle(self.surface, self.tt.hub, (self.cx, self.cy), 20)
        self.surface.blit(self.hub_text, 
                         (self.cx - self.hub_text.get_width()//2, 
                          self.cy - self.hub_text.get_height()//2))
        
        # 4.2 & 4.3 Spokes with labels and micro-bars
        for i, pos in enumerate(self.spoke_pos):
            # Status dot indicating ops-capable (on) vs not (off)
            color = self.tt.good_spoke if self.sim.op[i] else self.tt.bad_spoke
            pygame.draw.circle(self.surface, color, pos, SPOKE_CIRCLE_RADIUS)
            
            # Spoke label "S#" below the spoke, horizontally centered
            spoke_label = f"S{i+1}"
            label_surf = self.font_small.render(spoke_label, True, self.tt.text)
            label_rect = label_surf.get_rect()
            label_rect.centerx = pos[0]
            label_rect.top = pos[1] + SPOKE_CIRCLE_RADIUS + SPOKE_LABEL_LIFT
            
            # Ensure coordinates snap to integers
            label_rect.x = int(label_rect.x)
            label_rect.y = int(label_rect.y)
            
            # Clamp label to remain inside the map (never clipped at edges)
            if label_rect.left < self.layout.map.left:
                label_rect.left = self.layout.map.left + 5
            elif label_rect.right > self.layout.map.right:
                label_rect.right = self.layout.map.right - 5
            
            self.surface.blit(label_surf, label_rect)
            
            # Micro resource bars to the right of the label, on the same baseline
            if i < len(self.sim.stock):
                stock = self.sim.stock[i]
                micro_bars_x = label_rect.right + SPOKE_LABEL_GAP
                micro_bars_y = label_rect.centery
                
                # Draw micro-bars for A/B/C/D
                for j, (value, color) in enumerate(zip(stock, self.bar_cols)):
                    bar_x = micro_bars_x + j * (MICRO_BAR_WIDTH + MICRO_BAR_GAP)
                    bar_y = micro_bars_y - MICRO_BAR_HEIGHT // 2
                    
                    # Scale bar height based on value (increased by factor of 10)
                    bar_height = min(int(value * 20), MICRO_BAR_HEIGHT)
                    
                    # Ensure coordinates snap to integers
                    bar_x = int(bar_x)
                    bar_y = int(bar_y)
                    bar_height = int(bar_height)
                    
                    # Clamp micro-bars to remain inside the map
                    if bar_x + MICRO_BAR_WIDTH > self.layout.map.right:
                        break  # Stop drawing bars if they would overflow
                    
                    # Draw micro-bar
                    bar_rect = pygame.Rect(bar_x, bar_y + MICRO_BAR_HEIGHT - bar_height, 
                                         MICRO_BAR_WIDTH, bar_height)
                    pygame.draw.rect(self.surface, color, bar_rect)
                    pygame.draw.rect(self.surface, self.tt.text, bar_rect, 1)

        # Draw enhanced spoke bars with proper scaling and animation
        self._draw_enhanced_spoke_bars()

    def _draw_left_panel(self):
        """Draw the left side panel (metrics panel)."""
        if not self.layout:
            return
        
        # Panel background
        pygame.draw.rect(self.surface, self.tt.panel_bg, self.layout.left)
        
        # 3.1 "Operational" counter - Top-left, inside the left rail
        ops_capable = sum(1 for i in range(M) if i < len(self.sim.op) and self.sim.op[i])
        ops_text = self.font_big.render(f"Operational: {ops_capable}", True, self.tt.text)
        ops_rect = ops_text.get_rect()
        ops_rect.topleft = (self.layout.left_inner.x + 10, self.layout.left_inner.y + 10)
        self.surface.blit(ops_text, ops_rect)
        
        # 3.2 Inventory bar group (A, B, C, D) - Four vertical bars
        bar_start_y = ops_rect.bottom + 30
        bar_width = 20
        bar_spacing = 30
        
        # Resource letters above bars, horizontally centered
        for i, (ch, color) in enumerate(zip(["A", "B", "C", "D"], self.bar_cols)):
            # Calculate aggregate stocks across all spokes for this resource
            total_stock = sum(self.sim.stock[s][i] if s < len(self.sim.stock) else 0 for s in range(M))
            
            # Position for this bar
            bar_x = self.layout.left_inner.x + 10 + i * bar_spacing
            
            # Draw resource letter above bar
            letter_surf = self.font_small.render(ch, True, self.tt.text)
            letter_rect = letter_surf.get_rect()
            letter_rect.centerx = bar_x + bar_width // 2
            letter_rect.bottom = bar_start_y - 5
            self.surface.blit(letter_surf, letter_rect)
            
            # Draw vertical bar
            max_height = 100  # Maximum bar height
            bar_height = min(int(total_stock * 3), max_height)  # Scale factor for visibility
            bar_rect = pygame.Rect(bar_x, bar_start_y + max_height - bar_height, bar_width, bar_height)
            pygame.draw.rect(self.surface, color, bar_rect)
            pygame.draw.rect(self.surface, self.tt.text, bar_rect, 1)
            
            # Numeric tick/amount label near bar bottom
            value_text = self.font_small.render(f"{total_stock:.1f}", True, self.tt.text)
            value_rect = value_text.get_rect()
            value_rect.centerx = bar_x + bar_width // 2
            value_rect.top = bar_start_y + max_height + 5
            self.surface.blit(value_text, value_rect)

    def _draw_right_panel(self):
        """Draw the right side panel (trend panel)."""
        if not self.layout:
            return
        
        # Panel background
        pygame.draw.rect(self.surface, self.tt.panel_bg, self.layout.right)
        
        # Sparkline in upper portion of right rail
        sparkline_width = int(self.layout.right_inner.width * SPARKLINE_WIDTH_PCT)
        sparkline_x = self.layout.right_inner.x + (self.layout.right_inner.width - sparkline_width) // 2
        sparkline_y = self.layout.right_inner.y + 20
        
        # Draw sparkline background
        sparkline_rect = pygame.Rect(sparkline_x, sparkline_y, sparkline_width, SPARKLINE_HEIGHT)
        pygame.draw.rect(self.surface, self.tt.panel_btn, sparkline_rect, 1)
        
        # Draw sparkline data (simplified - just total ops over time)
        if len(self.sim.ops_total_history) > 1:
            points = []
            for i, ops in enumerate(self.sim.ops_total_history):
                if i < len(self.sim.ops_total_history) - 1:
                    x = sparkline_x + (i * sparkline_width) // (len(self.sim.ops_total_history) - 1)
                    # Scale y based on max ops (with some padding)
                    max_ops = max(self.sim.ops_total_history) if self.sim.ops_total_history else 1
                    y = sparkline_y + SPARKLINE_HEIGHT - (ops * SPARKLINE_HEIGHT) // max(1, max_ops)
                    points.append((int(x), int(y)))
            
            # Draw sparkline
            if len(points) > 1:
                pygame.draw.lines(self.surface, self.tt.primary, False, points, 2)
        
        # "Total Ops: N (AM/PM, day d)" title/counter below sparkline
        total_ops = sum(self.sim.ops_by_spoke)
        period = self.sim.t
        half = "AM" if period % 2 == 0 else "PM"
        day = period // 2
        
        ops_title = f"Total Ops: {total_ops} ({half}, day {day})"
        # Simple text truncation if it would overflow the rail
        if len(ops_title) > 25:  # Approximate character limit
            ops_title = ops_title[:22] + "..."
        
        title_text = self.font_small.render(ops_title, True, self.tt.text)
        title_rect = title_text.get_rect()
        title_rect.topleft = (self.layout.right_inner.x + 10, sparkline_y + SPARKLINE_HEIGHT + 20)
        self.surface.blit(title_text, title_rect)

    def _draw_safe_area(self):
        """Draw safe area boundaries."""
        if not self.layout:
            return
        
        # Draw safe area rectangle
        safe_rect = pygame.Rect(self.layout.pad, self.layout.pad, 
                               self.width - 2*self.layout.pad, 
                               self.height - 2*self.layout.pad)
        pygame.draw.rect(self.surface, (255, 255, 0, 128), safe_rect, 2)

    def _draw_pause_menu(self):
        """Draw the pause menu."""
        if not self.layout:
            return
        
        # Semi-transparent overlay
        overlay = pygame.Surface((PAUSE_MENU_WIDTH, PAUSE_MENU_HEIGHT), pygame.SRCALPHA)
        overlay.fill((*self.tt.bg, 200))
        
        # Menu background
        menu_rect = pygame.Rect((self.width - PAUSE_MENU_WIDTH) // 2, 
                               (self.height - PAUSE_MENU_HEIGHT) // 2,
                               PAUSE_MENU_WIDTH, PAUSE_MENU_HEIGHT)
        pygame.draw.rect(self.surface, self.tt.panel_bg, menu_rect, 
                        border_radius=PAUSE_MENU_BORDER_RADIUS)
        
        # Menu text
        title = self.font_big.render("PAUSED", True, self.tt.text)
        self.surface.blit(title, 
                         (menu_rect.centerx - title.get_width()//2, 
                          menu_rect.y + 20))
        
        # Instructions
        instructions = [
            "ESC: Exit to menu",
            "F11: Toggle fullscreen",
            "D/F12: Toggle debug",
            "H: Toggle header",
            "S: Toggle safe area",
            "SPACE: Pause/Resume",
            "R: Restart simulation",
            "B: Toggle bar scaling (Linear/Geometric)",
            "A: Toggle bar animation",
            "G: Adjust gamma (Geometric mode only)"
        ]
        
        for i, instruction in enumerate(instructions):
            text = self.font_small.render(instruction, True, self.tt.muted)
            self.surface.blit(text, 
                             (menu_rect.centerx - text.get_width()//2, 
                              menu_rect.y + 60 + i * 25))

    def _draw_aircraft(self, actions: List[Dict[str, Any]], alpha: float):
        """Draw aircraft based on enhanced state machine with smooth animation."""
        current_time = time.time()
        
        # Update aircraft animation state
        self._update_aircraft_animation(current_time)
        
        for ac in self.sim.fleet:
            ac_name = ac.name
            
            # Get current position and heading from the enhanced system
            if ac_name in self.aircraft_positions:
                pos = self.aircraft_positions[ac_name]
                angle = self.aircraft_headings[ac_name]
            else:
                # Fallback to default position
                pos = (self.cx, self.cy)
                angle = -math.pi/2
            
            # Determine aircraft color
            col = self.ac_colors.get(ac.typ, self.tt.text)
            
            # Draw aircraft with current position and heading
            self.draw_triangle(pos, ac.typ, ac.name, col, angle)
            
            # Draw state indicator if in loading/unloading state
            if ac_name in self.aircraft_states:
                visual_state = self.aircraft_states[ac_name]
                if visual_state in [AIRCRAFT_STATES['LOADING'], AIRCRAFT_STATES['UNLOADING']]:
                    self._draw_aircraft_state_indicator(pos, visual_state)

    def _get_aircraft_position_and_angle(self, ac, alpha: float):
        """Calculate interpolated position and angle for aircraft transit animation."""
        # Get start and end positions based on aircraft state
        start_pos, end_pos, progress = self._get_transit_positions(ac)
        
        # Interpolate position based on progress through the period
        if start_pos and end_pos and start_pos != end_pos:
            # Use alpha (progress through period) to interpolate position
            interp_alpha = min(1.0, max(0.0, alpha))
            x = start_pos[0] + (end_pos[0] - start_pos[0]) * interp_alpha
            y = start_pos[1] + (end_pos[1] - start_pos[1]) * interp_alpha
            pos = (x, y)
            
            # Calculate angle pointing toward destination
            dx = end_pos[0] - start_pos[0]
            dy = end_pos[1] - start_pos[1]
            angle = math.atan2(dy, dx)
        else:
            # Aircraft is stationary
            pos = start_pos if start_pos else (self.cx, self.cy)
            angle = -math.pi/2  # Default north orientation
        
        return pos, angle

    def _get_transit_positions(self, ac):
        """Get start and end positions for aircraft transit."""
        if ac.location == "HUB":
            # Aircraft is at hub
            return (self.cx, self.cy), (self.cx, self.cy), 0.0
        
        # Aircraft is at a spoke or in transit
        if ac.location.startswith("S"):
            spoke_idx = int(ac.location[1:]) - 1
            if 0 <= spoke_idx < len(self.spoke_pos):
                spoke_pos = self.spoke_pos[spoke_idx]
                
                # Check if aircraft is in transit
                if ac.state == "LEG1_ENROUTE" and ac.plan:
                    # Moving from HUB to first spoke
                    return (self.cx, self.cy), spoke_pos, 1.0
                elif ac.state == "AT_SPOKEB_ENROUTE" and ac.plan and len(ac.plan) > 1 and ac.plan[1] is not None:
                    # Moving between spokes
                    first_spoke = ac.plan[0]
                    second_spoke = ac.plan[1]
                    if 0 <= first_spoke < len(self.spoke_pos) and 0 <= second_spoke < len(self.spoke_pos):
                        return self.spoke_pos[first_spoke], self.spoke_pos[second_spoke], 1.0
                    else:
                        return spoke_pos, spoke_pos, 0.0
                elif ac.state in ["AT_SPOKEA", "AT_SPOKEB"] and ac.plan:
                    # Aircraft is at spoke, check if it will return to hub
                    if len(ac.plan) > 1 and ac.plan[1] is not None:
                        # Will go to second spoke
                        second_spoke = ac.plan[1]
                        if 0 <= second_spoke < len(self.spoke_pos):
                            return spoke_pos, self.spoke_pos[second_spoke], 1.0
                    else:
                        # Will return to hub
                        return spoke_pos, (self.cx, self.cy), 1.0
                
                # Aircraft is stationary at spoke
                return spoke_pos, spoke_pos, 0.0
        
        # Fallback to hub
        return (self.cx, self.cy), (self.cx, self.cy), 0.0

    def _restart_simulation(self):
        """Restart the simulation from the beginning."""
        try:
            log_runtime_event("Restarting simulation")
            
            # Reset simulation state
            self.sim.reset_world()
            
            # Reset renderer state
            self.simulation_completed = False
            self.completion_time = None
            self.paused = False
            self.last_step_time = time.time()
            self.current_frame = 0
            
            # Clear aircraft animation state
            self.aircraft_segments.clear()
            self.aircraft_states.clear()
            self.aircraft_positions.clear()
            self.aircraft_headings.clear()
            self.aircraft_stagger_delays.clear()
            
            # Clear debug messages
            if hasattr(self, 'debug_lines'):
                self.debug_lines.clear()
            if hasattr(self, 'debug_message_count'):
                self.debug_message_count = 0
            
            # Reinitialize graphics pipeline to ensure clean state
            if hasattr(self, 'width') and hasattr(self, 'height'):
                self._init_gfx_pipeline(self.width, self.height)
            
            log_runtime_event("Simulation restarted successfully")
            self._add_debug_message("Simulation restarted")
            
        except Exception as e:
            log_runtime_event("Error restarting simulation", f"error={e}")
            self._add_debug_message(f"Restart failed: {e}")

    def _cleanup_simulation(self):
        """Clean up simulation objects when returning to main menu."""
        try:
            log_runtime_event("Starting simulation cleanup")
            
            # Close recorder if it exists
            if hasattr(self, 'recorder') and self.recorder:
                try:
                    if hasattr(self.recorder, 'close'):
                        self.recorder.close()
                        log_runtime_event("Recorder closed successfully")
                except Exception as e:
                    log_runtime_event("Error closing recorder", f"error={e}")
            
            # Clear simulation state
            if hasattr(self, 'sim') and self.sim:
                try:
                    # Clear any large data structures
                    if hasattr(self.sim, 'actions_log'):
                        self.sim.actions_log.clear()
                    if hasattr(self.sim, 'history'):
                        self.sim.history.clear()
                    if hasattr(self.sim, 'stock'):
                        self.sim.stock.clear()
                    if hasattr(self.sim, 'fleet'):
                        self.sim.fleet.clear()
                    log_runtime_event("Simulation state cleared")
                except Exception as e:
                    log_runtime_event("Error clearing simulation state", f"error={e}")
            
            # Clear debug lines
            if hasattr(self, 'debug_lines'):
                self.debug_lines.clear()
            
            # Clear any cached surfaces or graphics
            if hasattr(self, '_cached_surfaces'):
                for surface in self._cached_surfaces.values():
                    try:
                        surface.fill((0, 0, 0, 0))
                    except:
                        pass
                self._cached_surfaces.clear()
            
            # Clear pygame surfaces
            if hasattr(self, 'screen'):
                self.screen = None
            if hasattr(self, 'surface'):
                self.surface = None
            
            log_runtime_event("Simulation cleanup completed")
            
        except Exception as e:
            log_runtime_event("Error during simulation cleanup", f"error={e}")
            # Don't raise - cleanup errors shouldn't prevent returning to menu

    def quit_pygame(self):
        """Properly quit pygame when returning to main menu."""
        try:
            log_runtime_event("Quitting pygame display")
            
            # Quit pygame display
            pygame.display.quit()
            log_runtime_event("pygame display quit successfully")
            
            # Clear any remaining surfaces
            if hasattr(self, 'screen'):
                self.screen = None
            if hasattr(self, 'surface'):
                self.surface = None
            
            # Note: Don't call pygame.quit() here as it might affect other parts of the system
            # The main function will handle the final pygame cleanup
            
            log_runtime_event("pygame quit completed")
            
        except Exception as e:
            log_runtime_event("Error during pygame quit", f"error={e}")
            # Don't raise - cleanup errors shouldn't prevent returning to menu

    def set_bar_scaling_mode(self, mode: str, gamma: float = None):
        """Set the scaling mode for spoke bars and update all bar states."""
        if mode not in [BAR_LINEAR_MODE, BAR_GEOMETRIC_MODE]:
            raise ValueError(f"Invalid scaling mode: {mode}. Must be '{BAR_LINEAR_MODE}' or '{BAR_GEOMETRIC_MODE}'")
        
        self.bar_scaling_mode = mode
        if gamma is not None:
            self.bar_gamma = max(0.1, min(1.0, gamma))  # Clamp gamma between 0.1 and 1.0
        
        # Update all existing bar states
        for bar_state in self.spoke_bar_states:
            bar_state.scaling_mode = mode
            bar_state.gamma = self.bar_gamma
        
        log_runtime_event(f"Bar scaling mode updated", f"mode={mode}, gamma={self.bar_gamma}")

    def toggle_bar_animation(self, enabled: bool = None):
        """Toggle bar height animation on/off."""
        if enabled is None:
            self.bar_animation_enabled = not self.bar_animation_enabled
        else:
            self.bar_animation_enabled = bool(enabled)
        
        log_runtime_event(f"Bar animation toggled", f"enabled={self.bar_animation_enabled}")

    def get_aircraft_debug_info(self) -> List[str]:
        """Get debug information about aircraft states and positions."""
        info = []
        info.append(f"Aircraft count: {len(self.sim.fleet)}")
        
        for ac in self.sim.fleet:
            ac_name = ac.name
            visual_state = self.aircraft_states.get(ac_name, "UNKNOWN")
            sim_state = ac.state
            location = ac.location
            
            if ac_name in self.aircraft_positions:
                pos = self.aircraft_positions[ac_name]
                pos_str = f"({pos[0]}, {pos[1]})"
            else:
                pos_str = "UNKNOWN"
            
            if ac_name in self.aircraft_headings:
                heading_deg = math.degrees(self.aircraft_headings[ac_name])
                heading_str = f"{heading_deg:.1f}°"
            else:
                heading_str = "UNKNOWN"
            
            if ac_name in self.aircraft_segments:
                segment = self.aircraft_segments[ac_name]
                segment_info = f"Segment: {segment.p0}→{segment.p1} ({segment.t_move}f)"
            else:
                segment_info = "No active segment"
            
            info.append(f"{ac_name}: {visual_state} ({sim_state}) @ {location}")
            info.append(f"  Pos: {pos_str}, Heading: {heading_str}")
            info.append(f"  {segment_info}")
        
        return info