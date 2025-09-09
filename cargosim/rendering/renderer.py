import os
import time
import math
import warnings
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

warnings.filterwarnings(
    "ignore",
    message="pkg_resources is deprecated as an API",
    category=UserWarning,
    module=r"pygame\.pkgdata"
)

try:
    import pygame
except ImportError:
    pygame = None

from cargosim.core.utils import clamp, log_exception, _mp4_available
from cargosim.core.config import (
    SAFE_PAD_PCT, SAFE_PAD_MIN_PX, LEFT_RAIL_PCT, LEFT_RAIL_MIN_PX,
    RIGHT_RAIL_PCT, RIGHT_RAIL_MIN_PX, hex2rgb, blend
)
from cargosim.core.simulation import LogisticsSim
from cargosim.rendering.recorder import Recorder, NullRecorder

# ---------------------------------------------------------------------------
# Layout and drawing constants
# ---------------------------------------------------------------------------
DEFAULT_WINDOW_WIDTH = 1200
DEFAULT_WINDOW_HEIGHT = 850
HEADER_HEIGHT_MIN = 28
HEADER_HEIGHT_PCT = 0.04
INNER_PADDING_FACTOR = 0.8

AIRCRAFT_SIZE_DEFAULT = 12
AIRCRAFT_LABEL_OFFSET = 16

# Spoke labels + micro bars
SPOKE_LABEL_GAP = 6
MICRO_BAR_WIDTH = 6
MICRO_BAR_HEIGHT = 12
MICRO_BAR_GAP = 2
MIN_VISIBLE_BAR_HEIGHT = 2
SPOKE_BAR_MAX_HEIGHT = 28

# Debug overlay
DEBUG_OVERLAY_WIDTH_PCT = 0.45
DEBUG_OVERLAY_HEIGHT_PCT = 0.35
DEBUG_OVERLAY_ALPHA = 160
DEBUG_OVERLAY_X_OFFSET = 20
DEBUG_OVERLAY_Y_OFFSET = 60
DEBUG_OVERLAY_PADDING = 8
DEBUG_OVERLAY_LINE_HEIGHT = 18
DEBUG_MAX_LINES = 18

@dataclass
class Layout:
    w: int
    h: int
    pad: int
    left: "pygame.Rect"
    right: "pygame.Rect"
    map: "pygame.Rect"
    left_inner: "pygame.Rect"
    right_inner: "pygame.Rect"
    header_rect: "pygame.Rect"
    header_visible: bool = True

@dataclass
class AircraftSegment:
    p0: Tuple[int, int]
    p1: Tuple[int, int]
    start_time_hours: float
    end_time_hours: float

@dataclass
class SpokeBarState:
    current_heights: List[float]
    last_update: float
    display_caps: List[float]

class Renderer:
    """Cohesive renderer with accurate motion timing and modular UI features."""

    def __init__(self, sim: LogisticsSim, *, force_windowed: bool = False):
        super().__init__()
        self.sim = sim

        # Display
        self.fullscreen = sim.cfg.launch_fullscreen and not force_windowed
        self.flags = 0
        self._pygame_initialized = False
        self._display_initialized = False
        self._gfx_pipeline_initialized = False
        self.screen = None
        self.surface = None
        self.clock = None

        # Theme
        self.tt = None
        self.bar_cols: List[Tuple[int, int, int]] = []

        # Layout
        self.layout: Optional[Layout] = None
        self.width = 0
        self.height = 0
        self.cx = 0
        self.cy = 0
        self.radius = 0
        self.spoke_pos: List[Tuple[int, int]] = []

        # Fonts
        self.font_big = None
        self.font_small = None

        # Timing
        self.ticks_per_second = int(getattr(self.sim.cfg, 'ticks_per_second', 120))
        if self.ticks_per_second < 10:
            self.ticks_per_second = 10
        elif self.ticks_per_second > 500:
            self.ticks_per_second = 500
        self.period_seconds = 1.0 / float(self.ticks_per_second)
        self.frames_per_period = getattr(self.sim.cfg, 'frames_per_period', 10)
        self.last_step_time_wall = time.time()
        # Accumulate elapsed real time to support multiple sim ticks per frame
        # when ticks_per_second exceeds the render FPS.
        self._tick_accumulator = 0.0

        # State expected by tests
        self.aircraft_stagger_delays: Dict[str, int] = {}
        self._hud_cache: Dict[str, Any] = {}
        self._last_heading_by_ac: Dict[str, float] = {}
        self.mouse_pos: Tuple[int, int] = (0, 0)
        self.hovered_aircraft = None
        self.hover_info_surface = None
        self.include_side_panels = getattr(sim.cfg, 'viz_include_side_panels', True)
        self._previous_actions: List[Dict[str, Any]] = []

        # Aircraft state
        self.aircraft_positions: Dict[str, Tuple[int, int]] = {}
        self.aircraft_headings: Dict[str, float] = {}
        self.aircraft_segments: Dict[str, AircraftSegment] = {}

        # Operation launch visual effects (mini jets)
        self.op_animations: List[Dict[str, Any]] = []

        # Bars state
        self.spoke_bar_states: List[SpokeBarState] = []

        # UI/flow
        self.paused = False
        self.simulation_completed = False
        self.menu_open = False
        self.exit_code = None

        # Toggles/overlays
        self.header_visible = True
        self.show_safe_area = False
        self.show_debug = bool(getattr(sim.cfg, 'debug_mode', False))
        self.debug_level = 1 if self.show_debug else 0
        self.debug_lines: List[str] = []
        self.debug_timestamp = time.time()

        # Feature toggles
        self.speed_indicators_enabled = True
        self.motion_blur_enabled = True
        self.cargo_animations_enabled = True

        # Recorder
        self.recorder = NullRecorder()

        self._ensure_gfx_pipeline_initialized()

    # Init helpers -------------------------------------------------------
    def _ensure_pygame_initialized(self):
        if self._pygame_initialized:
            return
        if pygame is None:
            raise RuntimeError("pygame is required to run the simulator.")
        if not pygame.get_init():
            pygame.init()
        self.flags = pygame.RESIZABLE
        self._pygame_initialized = True

    def _ensure_display_initialized(self):
        if self._display_initialized:
            return
        self._ensure_pygame_initialized()
        pygame.display.set_caption("CargoSim — Hub–Spoke Logistics")
        if self.fullscreen:
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN | pygame.DOUBLEBUF)
        else:
            self.screen = pygame.display.set_mode((DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT), self.flags)
        self.surface = self.screen
        self.clock = pygame.time.Clock()
        self._display_initialized = True

    def _apply_theme(self):
        t = self.sim.cfg.theme
        bg = hex2rgb(t.game_bg)
        text = hex2rgb(t.game_fg)
        muted = hex2rgb(t.game_muted)
        hub = hex2rgb(t.hub_color)
        good = hex2rgb(t.good_spoke)
        bad = hex2rgb(t.bad_spoke)
        self.tt = type("ThemeTokens", (), {})()
        self.tt.text = text
        self.tt.muted = muted
        self.tt.bg = bg
        self.tt.hub = hub
        self.tt.good_spoke = good
        self.tt.bad_spoke = bad
        self.tt.bar_A = hex2rgb(t.bar_A)
        self.tt.bar_B = hex2rgb(t.bar_B)
        self.tt.bar_C = hex2rgb(t.bar_C)
        self.tt.bar_D = hex2rgb(t.bar_D)
        self.tt.panel_bg = blend(bg, text, 0.1)
        self.bar_cols = [self.tt.bar_A, self.tt.bar_B, self.tt.bar_C, self.tt.bar_D]
        # Airframe-specific colors if provided by theme
        self.ac_colors: Dict[str, Tuple[int, int, int]] = {}
        try:
            if hasattr(t, 'ac_colors') and isinstance(t.ac_colors, dict):
                self.ac_colors = {k: hex2rgb(v) for k, v in t.ac_colors.items()}
        except Exception:
            self.ac_colors = {}

    def _build_fonts(self, h: int):
        self._ensure_pygame_initialized()
        pygame.font.init()
        big = clamp(int(h * 0.028), 16, 36)
        small = clamp(int(h * 0.018), 12, 20)
        self.font_big = pygame.font.SysFont(None, big)
        self.font_small = pygame.font.SysFont(None, small)

    def _compute_layout(self, w: int, h: int, header_visible: bool = True) -> Layout:
        pad = max(SAFE_PAD_MIN_PX, int(min(w, h) * SAFE_PAD_PCT))
        lw = max(LEFT_RAIL_MIN_PX, int(w * LEFT_RAIL_PCT))
        rw = max(RIGHT_RAIL_MIN_PX, int(w * RIGHT_RAIL_PCT))
        r_left = pygame.Rect(pad, pad, lw, h - 2 * pad)
        r_right = pygame.Rect(w - rw - pad, pad, rw, h - 2 * pad)
        map_left = r_left.right + pad
        map_width = r_right.left - map_left - pad
        r_map = pygame.Rect(map_left, pad, map_width, h - 2 * pad)
        li = r_left.inflate(-int(pad * INNER_PADDING_FACTOR), -int(pad * INNER_PADDING_FACTOR))
        ri = r_right.inflate(-int(pad * INNER_PADDING_FACTOR), -int(pad * INNER_PADDING_FACTOR))
        if header_visible:
            header_h = max(int(h * HEADER_HEIGHT_PCT), HEADER_HEIGHT_MIN)
            header = pygame.Rect(r_map.left, r_map.top, r_map.width, header_h)
            r_map.y += header_h
            r_map.height -= header_h
        else:
            header = pygame.Rect(r_map.left, r_map.top, r_map.width, 0)
        return Layout(w, h, pad, r_left, r_right, r_map, li, ri, header, header_visible)

    def _init_gfx_pipeline(self, w: int, h: int):
        self._apply_theme()
        self.layout = self._compute_layout(w, h, header_visible=self.header_visible)
        self.width, self.height = w, h
        self.cx = int(self.layout.map.centerx)
        self.cy = int(self.layout.map.centery)
        self.radius = int(min(self.layout.map.width, self.layout.map.height) // 2 - self.layout.pad)
        self._build_fonts(self.layout.h)
        self.spoke_pos = self._compute_realistic_spoke_positions(self.radius, self.cx, self.cy, self.sim.M)
        # initialize aircraft visuals
        for ac in self.sim.fleet:
            if ac.location == "HUB":
                self.aircraft_positions[ac.name] = (self.cx, self.cy)
                self.aircraft_headings[ac.name] = -math.pi / 2
            elif ac.location.startswith("S"):
                idx = int(ac.location[1:]) - 1
                pos = self.spoke_pos[idx] if 0 <= idx < len(self.spoke_pos) else (self.cx, self.cy)
                self.aircraft_positions[ac.name] = pos
                self.aircraft_headings[ac.name] = self._heading_from(self.cx, self.cy, *pos)
            else:
                self.aircraft_positions[ac.name] = (self.cx, self.cy)
                self.aircraft_headings[ac.name] = -math.pi / 2
        self._init_spoke_bar_states()

    def _ensure_gfx_pipeline_initialized(self):
        if self._gfx_pipeline_initialized:
            return
        self._ensure_display_initialized()
        w, h = pygame.display.get_surface().get_size()
        self._init_gfx_pipeline(w, h)
        self._gfx_pipeline_initialized = True

    # Geometry -----------------------------------------------------------
    def _compute_spoke_positions(self, radius: int, cx: int, cy: int, count: int) -> List[Tuple[int, int]]:
        pts: List[Tuple[int, int]] = []
        if count <= 0:
            return pts
        for i in range(count):
            theta = 2 * math.pi * i / count
            x = cx + int((radius - 20) * math.cos(theta))
            y = cy + int((radius - 20) * math.sin(theta))
            pts.append((x, y))
        return pts

    def _compute_realistic_spoke_positions(self, radius: int, cx: int, cy: int, count: int) -> List[Tuple[int, int]]:
        """Place spokes on a circle with per-spoke radius scaled by real miles.

        This preserves angles but maps spoke radial distance to its configured miles,
        so on-screen path length correlates to actual distance.
        """
        pts: List[Tuple[int, int]] = []
        if count <= 0:
            return pts
        distances = getattr(self.sim.cfg, 'spoke_distances', []) or []
        use_scaled = isinstance(distances, list) and len(distances) >= count and max(distances) > 0
        max_dist = max(distances) if use_scaled else 1.0
        for i in range(count):
            theta = 2 * math.pi * i / count
            if use_scaled:
                d = float(distances[i])
                r_i = max(20, int((radius - 20) * (d / max_dist)))
            else:
                r_i = radius - 20
            x = cx + int(r_i * math.cos(theta))
            y = cy + int(r_i * math.sin(theta))
            pts.append((x, y))
        return pts

    def _heading_from(self, x0: int, y0: int, x1: int, y1: int) -> float:
        return math.atan2((y1 - y0), (x1 - x0))

    # Bars ---------------------------------------------------------------
    def _init_spoke_bar_states(self):
        self.spoke_bar_states = []
        if not hasattr(self.sim, 'stock') or not self.sim.stock:
            return
        bar_scale = getattr(self.sim.cfg, 'bar_scale', None)
        if bar_scale is not None:
            caps = [bar_scale.denom_A, bar_scale.denom_B, bar_scale.denom_C, bar_scale.denom_D]
        else:
            caps = [1.0, 1.0, 1.0, 1.0]
        for _ in range(len(self.sim.stock)):
            self.spoke_bar_states.append(
                SpokeBarState(current_heights=[0.0, 0.0, 0.0, 0.0], last_update=time.time(), display_caps=caps[:])
            )

    def _update_spoke_bar_heights(self, now: float):
        if not self.spoke_bar_states or not hasattr(self.sim, 'stock'):
            return
        for i, bar_state in enumerate(self.spoke_bar_states):
            if i >= len(self.sim.stock):
                continue
            for j in range(4):
                cap = max(1.0, float(bar_state.display_caps[j]))
                value = float(self.sim.stock[i][j])
                ratio = value / cap
                scaled = ratio
                height = max(MIN_VISIBLE_BAR_HEIGHT, min(SPOKE_BAR_MAX_HEIGHT, scaled * SPOKE_BAR_MAX_HEIGHT))
                bar_state.current_heights[j] = height
            bar_state.last_update = now

    # Motion timing ------------------------------------------------------
    def _movement_positions_for(self, ac) -> Tuple[Tuple[int, int], Tuple[int, int]]:
        if ac.location == "HUB":
            start_pos = (self.cx, self.cy)
        elif ac.location.startswith("S"):
            idx = int(ac.location[1:]) - 1
            start_pos = self.spoke_pos[idx] if 0 <= idx < len(self.spoke_pos) else (self.cx, self.cy)
        else:
            start_pos = (self.cx, self.cy)

        end_pos = start_pos
        if ac.state == "LEG1_ENROUTE" and ac.plan:
            i = ac.plan[0]
            if i is not None and 0 <= i < len(self.spoke_pos):
                end_pos = self.spoke_pos[i]
        elif ac.state == "AT_SPOKEB_ENROUTE" and ac.plan and len(ac.plan) > 1:
            j = ac.plan[1]
            if j is not None and 0 <= j < len(self.spoke_pos):
                end_pos = self.spoke_pos[j]
        elif ac.state == "RETURN_ENROUTE":
            end_pos = (self.cx, self.cy)
        return start_pos, end_pos

    def _ensure_segment_for_enroute(self, ac) -> None:
        if ac.name in self.aircraft_segments:
            return
        base_start, end_pos = self._movement_positions_for(ac)
        dynamic_start = self.aircraft_positions.get(ac.name, base_start)
        if dynamic_start == end_pos:
            return
        start_hours = float(self.sim.current_time_hours)
        end_hours = start_hours + max(0.0, float(getattr(ac, 'time_remaining', 0.0)))
        self.aircraft_segments[ac.name] = AircraftSegment(
            p0=dynamic_start,
            p1=end_pos,
            start_time_hours=start_hours,
            end_time_hours=end_hours,
        )

    def _update_aircraft_animation(self, _now_wall: float):
        for ac in self.sim.fleet:
            if ac.state in ("LEG1_ENROUTE", "AT_SPOKEB_ENROUTE", "RETURN_ENROUTE"):
                self._ensure_segment_for_enroute(ac)
            else:
                self.aircraft_segments.pop(ac.name, None)

        now_h = float(self.sim.current_time_hours)
        for ac in self.sim.fleet:
            seg = self.aircraft_segments.get(ac.name)
            if seg is None:
                # stationary
                if ac.location == "HUB":
                    self.aircraft_positions[ac.name] = (self.cx, self.cy)
                    self.aircraft_headings[ac.name] = -math.pi / 2
                elif ac.location.startswith("S"):
                    idx = int(ac.location[1:]) - 1
                    pos = self.spoke_pos[idx] if 0 <= idx < len(self.spoke_pos) else (self.cx, self.cy)
                    self.aircraft_positions[ac.name] = pos
                    self.aircraft_headings[ac.name] = self._heading_from(self.cx, self.cy, *pos)
                else:
                    self.aircraft_positions[ac.name] = (self.cx, self.cy)
                    self.aircraft_headings[ac.name] = -math.pi / 2
                continue

            dur = max(1e-6, seg.end_time_hours - seg.start_time_hours)
            progress = (now_h - seg.start_time_hours) / dur
            progress = max(0.0, min(1.0, progress))
            eased = 3 * progress * progress - 2 * progress * progress * progress
            x = int(seg.p0[0] + (seg.p1[0] - seg.p0[0]) * eased)
            y = int(seg.p0[1] + (seg.p1[1] - seg.p0[1]) * eased)
            self.aircraft_positions[ac.name] = (x, y)
            self.aircraft_headings[ac.name] = self._heading_from(seg.p0[0], seg.p0[1], seg.p1[0], seg.p1[1])

    # Drawing ------------------------------------------------------------
    def _draw_header(self):
        if not self.layout or not self.layout.header_visible:
            return
        fleet_label = self.sim.cfg.fleet_label
        hhmm = getattr(self.sim, 'get_clock_hhmm', lambda: '00:00')()
        day = getattr(self.sim, 'day', 0)
        header_text = f"{fleet_label} | {hhmm} (Day {day})"
        surf = self.font_big.render(header_text, True, self.tt.text)
        pygame.draw.rect(self.surface, self.tt.panel_bg, self.layout.header_rect)
        pygame.draw.rect(self.surface, self.tt.text, self.layout.header_rect, 1)
        rect = surf.get_rect(center=self.layout.header_rect.center)
        self.surface.blit(surf, rect)

    def _draw_map(self):
        pygame.draw.circle(self.surface, self.tt.hub, (self.cx, self.cy), 20)
        for i, pos in enumerate(self.spoke_pos):
            color = self.tt.good_spoke if (i < len(self.sim.op) and self.sim.op[i]) else self.tt.bad_spoke
            pygame.draw.circle(self.surface, color, pos, 8)
        # Draw spoke micro-bars and labels once to avoid duplicate labels
        self._draw_enhanced_spoke_bars()

    def _draw_enhanced_spoke_bars(self):
        if not self.spoke_bar_states:
            return
        for i, (pos, bar_state) in enumerate(zip(self.spoke_pos, self.spoke_bar_states)):
            if i >= len(self.sim.stock):
                continue
            # Label placed once here (map no longer draws labels elsewhere)
            label_surf = self.font_small.render(f"S{i+1}", True, self.tt.text)
            label_rect = label_surf.get_rect()
            label_rect.centerx = pos[0]
            label_rect.top = pos[1] + 8 + 4
            self.surface.blit(label_surf, label_rect)
            # Micro bar origin
            micro_x = label_rect.right + SPOKE_LABEL_GAP
            micro_y = label_rect.centery
            total_w = 4 * MICRO_BAR_WIDTH + 3 * MICRO_BAR_GAP
            if micro_x + total_w > self.layout.map.right:
                micro_x = self.layout.map.right - total_w - 5
            for j, (col, h) in enumerate(zip(self.bar_cols, bar_state.current_heights)):
                bx = int(micro_x + j * (MICRO_BAR_WIDTH + MICRO_BAR_GAP))
                by = int(micro_y - MICRO_BAR_HEIGHT // 2)
                bh = int(h)
                if bh < MIN_VISIBLE_BAR_HEIGHT and self.sim.stock[i][j] > 0:
                    bh = MIN_VISIBLE_BAR_HEIGHT
                rect = pygame.Rect(bx, by + MICRO_BAR_HEIGHT - bh, MICRO_BAR_WIDTH, bh)
                pygame.draw.rect(self.surface, col, rect)
                pygame.draw.rect(self.surface, self.tt.text, rect, 1)

    def _draw_left_panel(self):
        if not self.layout:
            return
        pygame.draw.rect(self.surface, self.tt.panel_bg, self.layout.left)
        # Ops count
        try:
            total_spokes = len(self.sim.op)
            ops_capable = sum(1 for i in range(total_spokes) if self.sim.op[i])
        except Exception:
            ops_capable = 0
        ops_text = self.font_big.render(f"Operational: {ops_capable}", True, self.tt.text)
        self.surface.blit(ops_text, (self.layout.left_inner.x + 10, self.layout.left_inner.y + 10))
        # Aggregate A-D bars
        bar_start_y = self.layout.left_inner.y + 60
        bar_width = 20
        bar_spacing = 30
        for idx, (ch, color) in enumerate(zip(["A", "B", "C", "D"], self.bar_cols)):
            try:
                total = sum(self.sim.stock[s][idx] if s < len(self.sim.stock) else 0 for s in range(len(self.sim.op)))
            except Exception:
                total = 0.0
            x = self.layout.left_inner.x + 10 + idx * bar_spacing
            letter = self.font_small.render(ch, True, self.tt.text)
            lr = letter.get_rect()
            lr.centerx = x + bar_width // 2
            lr.bottom = bar_start_y - 5
            self.surface.blit(letter, lr)
            max_h = 100
            h = min(int(total * 3), max_h)
            rect = pygame.Rect(x, bar_start_y + max_h - h, bar_width, h)
            pygame.draw.rect(self.surface, color, rect)
            pygame.draw.rect(self.surface, self.tt.text, rect, 1)
            val = self.font_small.render(f"{total:.1f}", True, self.tt.text)
            self.surface.blit(val, (x - 4, bar_start_y + max_h + 5))

    def _draw_right_panel(self):
        if not self.layout:
            return
        pygame.draw.rect(self.surface, self.tt.panel_bg, self.layout.right)
        # Simple sparkline for ops_total_history
        inner = self.layout.right_inner
        spark_w = int(inner.width * 0.8)
        sx = inner.x + (inner.width - spark_w) // 2
        sy = inner.y + 20
        rect = pygame.Rect(sx, sy, spark_w, 80)
        pygame.draw.rect(self.surface, self.tt.text, rect, 1)
        if len(self.sim.ops_total_history) > 1:
            max_ops = max(self.sim.ops_total_history)
            pts = []
            for i, ops in enumerate(self.sim.ops_total_history):
                if i >= 1 and i < len(self.sim.ops_total_history):
                    x = sx + (i * spark_w) // max(1, len(self.sim.ops_total_history) - 1)
                    y = sy + 80 - (ops * 80) // max(1, max_ops)
                    pts.append((int(x), int(y)))
            if len(pts) > 1:
                pygame.draw.lines(self.surface, self.tt.bar_A, False, pts, 2)
        total_ops = sum(self.sim.ops_by_spoke) if hasattr(self.sim, 'ops_by_spoke') else 0
        hhmm = getattr(self.sim, 'get_clock_hhmm', lambda: '00:00')()
        day = getattr(self.sim, 'day', 0)
        title = self.font_small.render(f"Total Ops: {total_ops} ({hhmm}, day {day})", True, self.tt.text)
        self.surface.blit(title, (inner.x + 10, sy + 80 + 20))

    def _draw_aircraft(self):
        for ac in self.sim.fleet:
            pos = self.aircraft_positions.get(ac.name, (self.cx, self.cy))
            angle = self.aircraft_headings.get(ac.name, -math.pi / 2)
            color = self.ac_colors.get(getattr(ac, 'typ', ''), self.tt.text) if hasattr(self, 'ac_colors') else self.tt.text
            # Speed lines for motion perception
            self._draw_speed_indicators(ac, pos, angle, color)
            self._draw_aircraft_icon(pos, angle, color, ac.name)

    def _draw_speed_indicators(self, ac, pos: Tuple[int, int], angle: float, color: Tuple[int, int, int]):
        if not self.speed_indicators_enabled:
            return
        # Only when moving between nodes
        if getattr(ac, 'state', '') not in ("LEG1_ENROUTE", "AT_SPOKEB_ENROUTE", "RETURN_ENROUTE"):
            return
        speed_mach = float(getattr(ac, 'speed_mach', 0.45))
        # Map Mach to indicator count/length
        count = max(2, min(8, int(speed_mach * 10)))
        length = 10 + int(20 * min(1.0, speed_mach))
        normal_angle = angle + math.pi  # trail behind
        for i in range(count):
            offset = (i - count // 2) * 2
            nx = pos[0] + int(math.cos(angle + math.pi / 2) * offset)
            ny = pos[1] + int(math.sin(angle + math.pi / 2) * offset)
            ex = nx + int(math.cos(normal_angle) * length)
            ey = ny + int(math.sin(normal_angle) * length)
            pygame.draw.line(self.surface, color, (nx, ny), (ex, ey), 1)

    def _draw_aircraft_icon(self, pos: Tuple[int, int], angle: float, color: Tuple[int, int, int], name: str):
        x, y = int(pos[0]), int(pos[1])
        size = AIRCRAFT_SIZE_DEFAULT
        base = [(0, -size), (-size // 2, size // 2), (size // 2, size // 2)]
        c = math.cos(angle + math.pi / 2)
        s = math.sin(angle + math.pi / 2)
        pts = [(int(x + px * c - py * s), int(y + px * s + py * c)) for px, py in base]
        pygame.draw.polygon(self.surface, color, pts)
        # motion blur shadows (simple trailing ghosts)
        if self.motion_blur_enabled:
            for i in range(1, 4):
                alpha = max(0, 60 - i * 15)
                if alpha <= 0:
                    break
                offset = i * 2
                tx = x - int(math.cos(angle) * offset)
                ty = y - int(math.sin(angle) * offset)
                ghost_col = (min(255, color[0]), min(255, color[1]), min(255, color[2]))
                pygame.draw.polygon(self.surface, ghost_col, [(px + (tx - x), py + (ty - y)) for px, py in pts], 1)
        t = self.font_small.render(name, True, self.tt.text)
        self.surface.blit(t, (x - t.get_width() // 2, y - size - AIRCRAFT_LABEL_OFFSET))

    # Overlays -----------------------------------------------------------
    def _add_debug_message(self, message: str):
        timestamp = time.time() - self.debug_timestamp
        msg = f"[{timestamp:.1f}s] {message}"
        self.debug_lines.append(msg)
        if len(self.debug_lines) > DEBUG_MAX_LINES:
            self.debug_lines = self.debug_lines[-DEBUG_MAX_LINES:]

    def draw_debug_overlay(self):
        if not self.show_debug:
            return
        ow = int(self.layout.w * DEBUG_OVERLAY_WIDTH_PCT)
        oh = int(self.layout.h * DEBUG_OVERLAY_HEIGHT_PCT)
        surf = pygame.Surface((ow, oh), pygame.SRCALPHA)
        surf.fill((0, 0, 0, DEBUG_OVERLAY_ALPHA))
        x0, y0 = DEBUG_OVERLAY_X_OFFSET, DEBUG_OVERLAY_Y_OFFSET
        # Title
        title = self.font_small.render("DEBUG OVERLAY", True, (255, 255, 255))
        surf.blit(title, (DEBUG_OVERLAY_PADDING, DEBUG_OVERLAY_PADDING))
        y = DEBUG_OVERLAY_PADDING + 24
        # Basic info
        info = [
            f"Ticks/sec: {self.ticks_per_second}",
            f"Fleet Size: {len(self.sim.fleet)}", 
            f"Sim Clock: {getattr(self.sim, 'get_clock_hhmm', lambda: '00:00')()}"
        ]
        for line in info:
            text = self.font_small.render(line, True, (220, 220, 220))
            surf.blit(text, (DEBUG_OVERLAY_PADDING, y))
            y += DEBUG_OVERLAY_LINE_HEIGHT
        # Recent messages
        if self.debug_lines:
            y += 8
            for line in self.debug_lines[-8:]:
                text = self.font_small.render(line, True, (180, 255, 180))
                surf.blit(text, (DEBUG_OVERLAY_PADDING, y))
                y += DEBUG_OVERLAY_LINE_HEIGHT
        self.surface.blit(surf, (x0, y0))

    def draw_recording_overlays(self):
        if not self.recorder.live:
            return
        watermark = self.font_small.render("REC", True, (255, 0, 0))
        self.surface.blit(watermark, (10, 16))
        info_text = f"{self.recorder.fmt.upper()} • {self.recorder.fps}fps"
        info_surf = self.font_small.render(info_text, True, self.tt.muted)
        self.surface.blit(info_surf, (10, 16 + 4))

    def _draw_safe_area(self):
        if not self.layout:
            return
        safe_rect = pygame.Rect(self.layout.pad, self.layout.pad, self.width - 2 * self.layout.pad, self.height - 2 * self.layout.pad)
        pygame.draw.rect(self.surface, (255, 255, 0), safe_rect, 2)

    # Public API ---------------------------------------------------------
    def _set_tick_rate(self, ticks_per_second: int) -> None:
        """Update tick cadence and persist to cfg (10..500)."""
        try:
            tps = int(ticks_per_second)
        except Exception:
            tps = self.ticks_per_second
        tps = max(10, min(500, tps))
        if tps == self.ticks_per_second:
            return
        self.ticks_per_second = tps
        self.period_seconds = 1.0 / float(self.ticks_per_second)
        try:
            self.sim.cfg.ticks_per_second = int(self.ticks_per_second)
            self.sim.cfg.period_seconds = 1.0 / max(1, int(self.ticks_per_second))
        except Exception:
            pass
        self._add_debug_message(f"Ticks/sec set to {self.ticks_per_second}")

    def _bump_tick_rate(self, delta: int) -> None:
        self._set_tick_rate(self.ticks_per_second + int(delta))

    def render_frame(self, actions: List[Dict[str, Any]], alpha: float = 1.0, with_overlays: bool = True) -> None:
        self._ensure_gfx_pipeline_initialized()
        # Update effects from latest actions and advance animations
        self._process_actions_for_effects(actions)
        self._update_op_effects(time.time())
        self.surface.fill(self.tt.bg)
        if self.include_side_panels:
            self._draw_left_panel()
            self._draw_right_panel()
        self._draw_header()
        self._draw_map()
        self._draw_op_effects()
        self._draw_aircraft()
        if with_overlays:
            if self.show_debug:
                self.draw_debug_overlay()
            if self.recorder.live:
                self.draw_recording_overlays()
            if self.show_safe_area:
                self._draw_safe_area()

    # Operation launch effects -------------------------------------------
    def _process_actions_for_effects(self, actions: List[Dict[str, Any]]) -> None:
        if not actions:
            return
        try:
            for who, action in actions:
                if isinstance(who, str) and who.startswith("SPOKE") and ("OP" in action):
                    # Parse spoke index from label like "SPOKE3"
                    idx = int(who.replace("SPOKE", "")) - 1
                    if 0 <= idx < len(self.spoke_pos):
                        self._spawn_op_effect(idx)
        except Exception:
            pass

    def _spawn_op_effect(self, spoke_index: int) -> None:
        try:
            sx, sy = self.spoke_pos[spoke_index]
            vx = sx - self.cx
            vy = sy - self.cy
            mag = max(1.0, (vx*vx + vy*vy) ** 0.5)
            ux, uy = vx / mag, vy / mag
            length = 80  # pixels to travel outward
            ex = sx + int(ux * length)
            ey = sy + int(uy * length)
            self.op_animations.append({
                'start_time': time.time(),
                'duration': 1.2,
                'p0': (sx, sy),
                'p1': (ex, ey),
            })
        except Exception:
            pass

    def _update_op_effects(self, now: float) -> None:
        if not self.op_animations:
            return
        # Remove expired animations
        keep: List[Dict[str, Any]] = []
        for anim in self.op_animations:
            start = float(anim.get('start_time', 0.0))
            dur = max(0.1, float(anim.get('duration', 1.0)))
            if now - start <= dur:
                anim['progress'] = (now - start) / dur
                keep.append(anim)
        self.op_animations = keep

    def _draw_op_effects(self) -> None:
        for anim in self.op_animations:
            p0 = anim['p0']
            p1 = anim['p1']
            t = max(0.0, min(1.0, float(anim.get('progress', 0.0))))
            # ease-in-out for smoother motion
            eased = 3 * t * t - 2 * t * t * t
            x = int(p0[0] + (p1[0] - p0[0]) * eased)
            y = int(p0[1] + (p1[1] - p0[1]) * eased)
            angle = self._heading_from(p0[0], p0[1], p1[0], p1[1])
            self._draw_mini_jet((x, y), angle, self.tt.bar_C)

    def _draw_mini_jet(self, pos: Tuple[int, int], angle: float, color: Tuple[int, int, int]) -> None:
        x, y = int(pos[0]), int(pos[1])
        size = max(6, AIRCRAFT_SIZE_DEFAULT - 4)
        base = [(0, -size), (-size // 2, size // 2), (size // 2, size // 2)]
        c = math.cos(angle + math.pi / 2)
        s = math.sin(angle + math.pi / 2)
        pts = [(int(x + px * c - py * s), int(y + px * s + py * c)) for px, py in base]
        pygame.draw.polygon(self.surface, color, pts)

    def _toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN | pygame.DOUBLEBUF)
        else:
            self.screen = pygame.display.set_mode((DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT), self.flags)
        self.surface = self.screen
        w, h = self.surface.get_size()
        self._init_gfx_pipeline(w, h)

    def toggle_header(self):
        self.header_visible = not self.header_visible
        self.layout.header_visible = self.header_visible
        w, h = pygame.display.get_surface().get_size()
        self._init_gfx_pipeline(w, h)

    def run(self) -> Optional[str]:
        try:
            rcfg = self.sim.cfg.recording
            ok, _ = _mp4_available()
            fmt = "mp4" if (rcfg.record_live_format.lower() == "mp4" and ok) else "png"
            if rcfg.record_live_enabled:
                self.recorder = Recorder.for_live(
                    folder=rcfg.record_live_folder,
                    fps=rcfg.fps,
                    fmt=fmt,
                    async_writer=rcfg.record_async_writer,
                    max_queue=rcfg.record_max_queue,
                    drop_on_backpressure=rcfg.record_skip_on_backpressure,
                )
            else:
                self.recorder = NullRecorder()

            running = True
            while running:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False
                        self.exit_code = "QUIT"
                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            self.exit_code = "GUI"
                            running = False
                        elif event.key == pygame.K_F11:
                            self._toggle_fullscreen()
                        elif event.key == pygame.K_d or event.key == pygame.K_F12:
                            self.show_debug = not self.show_debug
                            self._add_debug_message(f"Debug: {'ON' if self.show_debug else 'OFF'}")
                        elif event.key == pygame.K_h:
                            self.toggle_header()
                            self._add_debug_message(f"Header: {'ON' if self.header_visible else 'OFF'}")
                        elif event.key == pygame.K_s:
                            self.show_safe_area = not self.show_safe_area
                        elif event.key == pygame.K_SPACE:
                            self.paused = not self.paused
                        else:
                            # Runtime tick speed control: + / - (and keypad/brackets)
                            increase_keys = set()
                            dec_increase = getattr(pygame, 'K_PLUS', None)
                            if dec_increase is not None:
                                increase_keys.add(dec_increase)
                            k_eq = getattr(pygame, 'K_EQUALS', None)
                            if k_eq is not None:
                                increase_keys.add(k_eq)
                            kp_plus = getattr(pygame, 'K_KP_PLUS', None)
                            if kp_plus is not None:
                                increase_keys.add(kp_plus)
                            rb = getattr(pygame, 'K_RIGHTBRACKET', None)
                            if rb is not None:
                                increase_keys.add(rb)

                            decrease_keys = set()
                            k_minus = getattr(pygame, 'K_MINUS', None)
                            if k_minus is not None:
                                decrease_keys.add(k_minus)
                            kp_minus = getattr(pygame, 'K_KP_MINUS', None)
                            if kp_minus is not None:
                                decrease_keys.add(kp_minus)
                            lb = getattr(pygame, 'K_LEFTBRACKET', None)
                            if lb is not None:
                                decrease_keys.add(lb)

                            if event.key in increase_keys:
                                self._bump_tick_rate(10)
                            elif event.key in decrease_keys:
                                self._bump_tick_rate(-10)
                    elif event.type == pygame.VIDEORESIZE and not self.fullscreen:
                        self.screen = pygame.display.set_mode((event.w, event.h), self.flags)
                        self.surface = self.screen
                        self._init_gfx_pipeline(event.w, event.h)

                now = time.time()
                # Measure frame delta and advance wall-clock marker every frame
                frame_dt = (now - self.last_step_time_wall)
                self.last_step_time_wall = now
                if not self.paused and not self.simulation_completed:
                    # Accumulate elapsed time only when running, and step as many
                    # ticks as needed (capped) to honor ticks_per_second regardless of FPS.
                    self._tick_accumulator += frame_dt
                    max_steps_per_frame = 100  # sane upper bound to prevent spiral of death
                    steps_done = 0
                    last_actions = self._previous_actions
                    while self._tick_accumulator >= self.period_seconds and steps_done < max_steps_per_frame and not self.simulation_completed:
                        step_fn = getattr(self.sim, 'step_time', None)
                        if callable(step_fn):
                            actions = step_fn(1)
                        else:
                            actions = self.sim.step_period()
                        self._tick_accumulator -= self.period_seconds
                        steps_done += 1
                        last_actions = actions if actions is not None else []
                        if actions is None:
                            self.exit_code = "COMPLETE"
                            self.simulation_completed = True
                            last_actions = []
                            break
                    self._previous_actions = last_actions

                self._update_spoke_bar_heights(now)
                self._update_aircraft_animation(now)
                self.render_frame(self._previous_actions, 1.0)
                pygame.display.flip()
                self.clock.tick(60)

            if self.exit_code == "GUI":
                self._cleanup_simulation()
            return None
        except Exception as e:
            log_exception(e, "Renderer.run() main loop")
            try:
                pygame.quit()
            except Exception:
                pass
            raise

    # Cleanup ------------------------------------------------------------
    def _cleanup_simulation(self):
        try:
            if hasattr(self, 'recorder') and self.recorder and hasattr(self.recorder, 'close'):
                self.recorder.close()
            self._hud_cache.clear()
            self.aircraft_segments.clear()
            self.aircraft_positions.clear()
            self.aircraft_headings.clear()
        except Exception:
            pass
