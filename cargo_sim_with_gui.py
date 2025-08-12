import os
import sys
import json
import math
import copy
import time
import subprocess
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict

# --- Tk first (always available on Win/macOS, may require apt on Linux) ---
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# --- Dependency probing (do not hard-crash on import) ---
_HAS_PYGAME = True
try:
    import pygame
except Exception:
    _HAS_PYGAME = False

_HAS_IMAGEIO = True
try:
    import imageio.v2 as imageio  # optional
    try:
        # imageio-ffmpeg is optional but recommended for local MP4
        import imageio_ffmpeg  # noqa: F401
        _HAS_IMAGEIO = True
    except Exception:
        # we still let imageio exist (will still write PNGs); MP4 assembly may fail
        pass
except Exception:
    _HAS_IMAGEIO = False
    imageio = None  # type: ignore

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cargo_sim_config.json")
DEBUG_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cargo_sim_debug.log")

# ------------------------- Defaults & Model Parameters -------------------------

M = 10  # number of spokes
PAIR_ORDER_DEFAULT = [(0,1),(2,3),(4,5),(6,7),(8,9)]  # zero-based spoke indices

# Default consumption cadences (PM only; day = t//2)
A_PERIOD_DAYS_DFLT = 2  # A: 1 every 2 days
B_PERIOD_DAYS_DFLT = 2  # B: 1 every 2 days
C_PERIOD_DAYS_DFLT = 3  # C: 1 every 3 days
D_PERIOD_DAYS_DFLT = 4  # D: 1 every 4 days

# Visual scaling for spoke bars (purely aesthetic; no caps)
VIS_CAPS_DFLT = (6, 2, 4, 4)  # used for relative bar heights

# ------------------------- Theme Presets & Color Maps -------------------------

def _hex(h):  # helper to clamp/normalize hex
    h = h.strip().lstrip("#")
    if len(h) == 3:
        h = "".join([c*2 for c in h])
    return "#" + h.lower()

THEME_PRESETS = {
    # name: dict fields for ThemeConfig
    "Classic Light": {
        "menu_mode": "light",
        "game_bg": _hex("f8fafc"),
        "game_fg": _hex("0f172a"),
        "game_muted": _hex("475569"),
        "hub_color": _hex("e5e7eb"),
        "good_spoke": _hex("16a34a"),
        "bad_spoke": _hex("dc2626"),
        "bar_A": _hex("2563eb"),
        "bar_B": _hex("ea580c"),
        "bar_C": _hex("10b981"),
        "bar_D": _hex("ef4444"),
    },
    "Classic Dark": {
        "menu_mode": "dark",
        "game_bg": _hex("0f172a"),
        "game_fg": _hex("e5e7eb"),
        "game_muted": _hex("9ca3af"),
        "hub_color": _hex("1f2937"),
        "good_spoke": _hex("3fb950"),
        "bad_spoke": _hex("f85149"),
        "bar_A": _hex("60a5fa"),
        "bar_B": _hex("f59e0b"),
        "bar_C": _hex("34d399"),
        "bar_D": _hex("f87171"),
    },
    "Cyber": {
        "menu_mode": "dark",
        "game_bg": _hex("0b1020"),
        "game_fg": _hex("e0f2fe"),
        "game_muted": _hex("7dd3fc"),
        "hub_color": _hex("0e7490"),
        "good_spoke": _hex("22d3ee"),
        "bad_spoke": _hex("f43f5e"),
        "bar_A": _hex("22d3ee"),
        "bar_B": _hex("f59e0b"),
        "bar_C": _hex("22c55e"),
        "bar_D": _hex("f97316"),
    },
    "GitHub Light": {
        "menu_mode": "light",
        "game_bg": _hex("f6f8fa"),
        "game_fg": _hex("24292f"),
        "game_muted": _hex("57606a"),
        "hub_color": _hex("d0d7de"),
        "good_spoke": _hex("2da44e"),
        "bad_spoke": _hex("cf222e"),
        "bar_A": _hex("0969da"),
        "bar_B": _hex("bf8700"),
        "bar_C": _hex("1a7f37"),
        "bar_D": _hex("cf222e"),
    },
    "GitHub Dark": {
        "menu_mode": "dark",
        "game_bg": _hex("0d1117"),
        "game_fg": _hex("c9d1d9"),
        "game_muted": _hex("8b949e"),
        "hub_color": _hex("161b22"),
        "good_spoke": _hex("3fb950"),
        "bad_spoke": _hex("f85149"),
        "bar_A": _hex("58a6ff"),
        "bar_B": _hex("d29922"),
        "bar_C": _hex("3fb950"),
        "bar_D": _hex("f85149"),
    },
    "Night Ops": {
        "menu_mode": "dark",
        "game_bg": _hex("0b0f14"),
        "game_fg": _hex("d1d5db"),
        "game_muted": _hex("9ca3af"),
        "hub_color": _hex("111827"),
        "good_spoke": _hex("22c55e"),
        "bad_spoke": _hex("ef4444"),
        "bar_A": _hex("60a5fa"),
        "bar_B": _hex("fbbf24"),
        "bar_C": _hex("22c55e"),
        "bar_D": _hex("f87171"),
    },
    "Solarized Light": {
        "menu_mode": "light",
        "game_bg": _hex("fdf6e3"),
        "game_fg": _hex("073642"),
        "game_muted": _hex("586e75"),
        "hub_color": _hex("eee8d5"),
        "good_spoke": _hex("859900"),
        "bad_spoke": _hex("dc322f"),
        "bar_A": _hex("268bd2"),
        "bar_B": _hex("b58900"),
        "bar_C": _hex("2aa198"),
        "bar_D": _hex("cb4b16"),
    },
    "Solarized Dark": {
        "menu_mode": "dark",
        "game_bg": _hex("002b36"),
        "game_fg": _hex("eee8d5"),
        "game_muted": _hex("93a1a1"),
        "hub_color": _hex("073642"),
        "good_spoke": _hex("859900"),
        "bad_spoke": _hex("dc322f"),
        "bar_A": _hex("268bd2"),
        "bar_B": _hex("b58900"),
        "bar_C": _hex("2aa198"),
        "bar_D": _hex("cb4b16"),
    },
    "Desert": {
        "menu_mode": "light",
        "game_bg": _hex("f5f0e6"),
        "game_fg": _hex("3f3a2e"),
        "game_muted": _hex("7a6e5a"),
        "hub_color": _hex("e5dcc9"),
        "good_spoke": _hex("a3be8c"),
        "bad_spoke": _hex("bf616a"),
        "bar_A": _hex("d4a373"),
        "bar_B": _hex("b08968"),
        "bar_C": _hex("a7c957"),
        "bar_D": _hex("e76f51"),
    },
    "Ocean": {
        "menu_mode": "light",
        "game_bg": _hex("e6f1f8"),
        "game_fg": _hex("0a2540"),
        "game_muted": _hex("55738a"),
        "hub_color": _hex("c7d9e8"),
        "good_spoke": _hex("2ea44f"),
        "bad_spoke": _hex("d73a49"),
        "bar_A": _hex("1e88e5"),
        "bar_B": _hex("00acc1"),
        "bar_C": _hex("26a69a"),
        "bar_D": _hex("ef5350"),
    },
}

AIRFRAME_COLORSETS = {
    "Neutral Grays": {"C-130": "#dcdcdc", "C-27": "#a6a6a6"},
    "Blue / Orange": {"C-130": "#3b82f6", "C-27": "#f59e0b"},
    "Green / Yellow": {"C-130": "#10b981", "C-27": "#fbbf24"},
    "Red / Gray": {"C-130": "#ef4444", "C-27": "#9ca3af"},
    "Camo (olive / tan)": {"C-130": "#6b8e23", "C-27": "#c2b280"},
    "High Contrast": {"C-130": "#06b6d4", "C-27": "#a855f7"},
    "Coast Guard": {"C-130": "#ffffff", "C-27": "#ea580c"},
    "Desert (sand / brown)": {"C-130": "#c2b280", "C-27": "#8b5e34"},
    "Navy (navy / gold)": {"C-130": "#1e3a8a", "C-27": "#f59e0b"},
    "Mono Invert": {"C-130": "#f5f5f5", "C-27": "#262626"},
}

# ------------------------- Config -------------------------
@dataclass
class ThemeConfig:
    preset: str = "Classic Dark"
    menu_theme: str = "dark"     # applied to Tk controls
    game_bg: str = "#121418"
    game_fg: str = "#e0e0e0"
    game_muted: str = "#8a8a8a"
    hub_color: str = "#1e1e1e"
    good_spoke: str = "#3ccc78"
    bad_spoke: str = "#dc3c3c"
    ac_colors: Dict[str, str] = field(default_factory=lambda: {"C-130": "#dcdcdc", "C-27": "#b5b5b5"})
    bar_A: str = "#4682c8"
    bar_B: str = "#eba23c"
    bar_C: str = "#50b45a"
    bar_D: str = "#d25050"

    def to_json(self) -> dict:
        return {
            "preset": self.preset,
            "menu_theme": self.menu_theme,
            "game_bg": self.game_bg,
            "game_fg": self.game_fg,
            "game_muted": self.game_muted,
            "hub_color": self.hub_color,
            "good_spoke": self.good_spoke,
            "bad_spoke": self.bad_spoke,
            "ac_colors": self.ac_colors,
            "bar_A": self.bar_A,
            "bar_B": self.bar_B,
            "bar_C": self.bar_C,
            "bar_D": self.bar_D,
        }

    @staticmethod
    def from_json(d: dict) -> "ThemeConfig":
        t = ThemeConfig()
        t.preset = d.get("preset", t.preset)
        t.menu_theme = d.get("menu_theme", t.menu_theme)
        t.game_bg = d.get("game_bg", t.game_bg)
        t.game_fg = d.get("game_fg", t.game_fg)
        t.game_muted = d.get("game_muted", t.game_muted)
        t.hub_color = d.get("hub_color", t.hub_color)
        t.good_spoke = d.get("good_spoke", t.good_spoke)
        t.bad_spoke = d.get("bad_spoke", t.bad_spoke)
        t.ac_colors = d.get("ac_colors", t.ac_colors)
        t.bar_A = d.get("bar_A", t.bar_A)
        t.bar_B = d.get("bar_B", t.bar_B)
        t.bar_C = d.get("bar_C", t.bar_C)
        t.bar_D = d.get("bar_D", t.bar_D)
        return t

@dataclass
class RecordingConfig:
    record_live: bool = False
    record_format: str = "PNG frames"  # "PNG frames" | "MP4"
    live_out_dir: str = "captures"
    offline_out_file: str = "render.mp4"
    fps: int = 30
    frames_per_period: int = 10

    def to_json(self) -> dict:
        return {
            "record_live": self.record_live,
            "record_format": self.record_format,
            "live_out_dir": self.live_out_dir,
            "offline_out_file": self.offline_out_file,
            "fps": self.fps,
            "frames_per_period": self.frames_per_period,
        }

    @staticmethod
    def from_json(d: dict) -> "RecordingConfig":
        r = RecordingConfig()
        r.record_live = bool(d.get("record_live", r.record_live))
        r.record_format = d.get("record_format", r.record_format)
        r.live_out_dir = d.get("live_out_dir", r.live_out_dir)
        r.offline_out_file = d.get("offline_out_file", r.offline_out_file)
        r.fps = int(d.get("fps", r.fps))
        r.frames_per_period = int(d.get("frames_per_period", r.frames_per_period))
        return r

@dataclass
class SimConfig:
    fleet_label: str = "2xC130"       # "2xC130", "4xC130", "2xC130_2xC27"
    periods: int = 60                 # 30 days (AM/PM)
    init_A: int = 4
    init_B: int = 4
    init_C: int = 0
    init_D: int = 0
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
    theme: ThemeConfig = field(default_factory=ThemeConfig)
    recording: RecordingConfig = field(default_factory=RecordingConfig)

    def to_json(self) -> dict:
        return {
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
            "theme": self.theme.to_json(),
            "recording": self.recording.to_json(),
        }

    @staticmethod
    def from_json(d: dict) -> "SimConfig":
        cfg = SimConfig()
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
        cfg.theme = ThemeConfig.from_json(d.get("theme", {}))
        cfg.recording = RecordingConfig.from_json(d.get("recording", {}))
        return cfg

def load_config() -> SimConfig:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return SimConfig.from_json(data)
        except Exception:
            pass
    return SimConfig()

def save_config(cfg: SimConfig):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg.to_json(), f, indent=2)
    except Exception as e:
        print("Warning: failed to save config:", e)

def append_debug(lines: List[str]):
    try:
        with open(DEBUG_LOG, "a", encoding="utf-8") as f:
            for ln in lines:
                f.write(ln + "\n")
    except Exception:
        pass

# ------------------------- Dependency Manager -------------------------

def _pip_install(pkgs: List[str]) -> bool:
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade"] + pkgs)
        return True
    except Exception as e:
        messagebox.showerror("Install Failed", f"Failed to install: {' '.join(pkgs)}\n{e}")
        return False

def check_and_offer_installs(startup_root: tk.Tk):
    """Ask user to install missing deps. Greys out features later."""
    global _HAS_PYGAME, _HAS_IMAGEIO, imageio

    # Required: pygame
    if not _HAS_PYGAME:
        startup_root.deiconify()
        if messagebox.askyesno("Dependency Required",
                               "Required dependency 'pygame' is not installed.\nInstall it now?"):
            ok = _pip_install(["pygame"])
            if ok:
                try:
                    import importlib
                    import pygame as _pg  # noqa
                    importlib.reload(sys.modules.get("pygame", _pg))
                    _HAS_PYGAME = True
                except Exception:
                    _HAS_PYGAME = True  # best effort
                if messagebox.askyesno("Restart Needed", "Pygame installed. Restart the app now?"):
                    os.execl(sys.executable, sys.executable, *sys.argv)
        else:
            messagebox.showwarning("Simulation Disabled", "Without pygame, the simulation and offline render are disabled.")

    # Optional: imageio & imageio-ffmpeg
    if not _HAS_IMAGEIO:
        if messagebox.askyesno("Optional Feature: MP4",
                               "Optional dependency 'imageio' (and imageio-ffmpeg) not installed.\n"
                               "Install to enable MP4 assembly for recordings?\n"
                               "You can still export PNG frames without it."):
            ok = _pip_install(["imageio", "imageio-ffmpeg"])
            if ok:
                try:
                    import importlib
                    import imageio.v2 as _io
                    import imageio_ffmpeg as _iof  # noqa
                    imageio = _io
                    _HAS_IMAGEIO = True
                except Exception:
                    pass

# ------------------------- Logistics Model -------------------------

@dataclass
class Aircraft:
    typ: str           # "C-130" or "C-27"
    cap: int           # capacity
    name: str
    location: str = "HUB"  # "HUB" or "S{1..10}"
    state: str = "IDLE"    # IDLE, LEG1_ENROUTE, AT_SPOKEA, AT_SPOKEB_ENROUTE, AT_SPOKEB
    plan: Optional[Tuple[int, Optional[int]]] = None  # (i, j|None)
    payload_A: List[int] = field(default_factory=lambda: [0,0,0,0])
    payload_B: List[int] = field(default_factory=lambda: [0,0,0,0])
    active_periods: int = 0
    rest_cooldown: int = 0

    def max_active_before_rest(self, cfg: SimConfig) -> int:
        return cfg.rest_c130 if self.typ == "C-130" else cfg.rest_c27

    def at_hub(self) -> bool:
        return self.location == "HUB"

class LogisticsSim:
    def __init__(self, cfg: SimConfig):
        self.cfg = cfg
        self.M = M
        self.PAIR_ORDER = list(cfg.pair_order)
        self.A_PERIOD_DAYS = cfg.a_days
        self.B_PERIOD_DAYS = cfg.b_days
        self.C_PERIOD_DAYS = cfg.c_days
        self.D_PERIOD_DAYS = cfg.d_days
        self.VIS_CAPS = VIS_CAPS_DFLT

        self.reset_world()

    def reset_world(self):
        self.t = 0  # current period
        self.day = 0
        self.half = "AM"  # AM for even t, PM for odd t
        self.stock = [[self.cfg.init_A, self.cfg.init_B, self.cfg.init_C, self.cfg.init_D] for _ in range(self.M)]
        self.op = [False]*self.M  # operational flags (A&B only)
        self.arrivals_next = [[] for _ in range(self.M)]
        self.pair_cursor = 0
        self.fleet = self.build_fleet(self.cfg.fleet_label)
        self.actions_log: List[List[Tuple[str,str]]] = []

        # Stats
        self.ops_by_spoke = [0]*self.M  # counts of OFFLOAD occurrences per spoke

        # History for rewind
        self.history: List[dict] = []
        self.push_snapshot()  # store initial state (period 0 before any action)

    def build_fleet(self, label: str) -> List[Aircraft]:
        if label == "2xC130":
            return [Aircraft("C-130", self.cfg.cap_c130, "C-130 #1"),
                    Aircraft("C-130", self.cfg.cap_c130, "C-130 #2")]
        if label == "4xC130":
            return [Aircraft("C-130", self.cfg.cap_c130, "C-130 #1"),
                    Aircraft("C-130", self.cfg.cap_c130, "C-130 #2"),
                    Aircraft("C-130", self.cfg.cap_c130, "C-130 #3"),
                    Aircraft("C-130", self.cfg.cap_c130, "C-130 #4")]
        if label == "2xC130_2xC27":
            return [Aircraft("C-130", self.cfg.cap_c130, "C-130 #1"),
                    Aircraft("C-130", self.cfg.cap_c130, "C-130 #2"),
                    Aircraft("C-27", self.cfg.cap_c27, "C-27 #1"),
                    Aircraft("C-27", self.cfg.cap_c27, "C-27 #2")]
        raise ValueError("Unknown fleet label")

    def detect_stage(self) -> str:
        if any(self.stock[i][0] == 0 for i in range(self.M)):
            return "A"
        if any(self.stock[i][1] == 0 for i in range(self.M)):
            return "B"
        return "OPS"

    def plan_for_pair_stage(self, i: int, j: int, cap_left: int, stage: str):
        p_i = [0,0,0,0]; p_j = [0,0,0,0]; rem = cap_left
        def give(target_idx: int, k: int, need: int):
            nonlocal rem
            if rem <= 0 or need <= 0: return
            x = min(rem, need)
            if target_idx == i: p_i[k] += x
            else: p_j[k] += x
            rem -= x

        needA_i = max(0, 1 - self.stock[i][0]); needB_i = max(0, 1 - self.stock[i][1])
        needA_j = max(0, 1 - self.stock[j][0]); needB_j = max(0,  1 - self.stock[j][1])
        needC_i = max(0, 1 - self.stock[i][2]); needD_i = max(0,  1 - self.stock[i][3])
        needC_j = max(0,  1 - self.stock[j][2]); needD_j = max(0,  1 - self.stock[j][3])

        if stage == "A":
            give(i,0,needA_i); give(j,0,needA_j)
            give(i,1,needB_i); give(j,1,needB_j)
            give(i,0, max(0, 2 - (self.stock[i][0] + p_i[0])))
            give(j,0, max(0, 2 - (self.stock[j][0] + p_j[0])))
        elif stage == "B":
            give(i,1,needB_i); give(j,1,needB_j)
            give(i,0, max(0, 2 - self.stock[i][0]))
            give(j,0, max(0, 2 - self.stock[j][0]))
        else:  # "OPS"
            give(i,2,needC_i); give(j,2,needC_j)
            give(i,3,needD_i); give(j,3,needD_j)
            give(i,2, max(0, 2 - (self.stock[i][2] + p_i[2])))
            give(j,2, max(0, 2 - (self.stock[j][2] + p_j[2])))
            give(i,3, max(0, 2 - (self.stock[i][3] + p_i[3])))
            give(j,3, max(0, 2 - (self.stock[j][3] + p_j[3])))

        return p_i, p_j

    def snapshot(self) -> dict:
        return {
            "t": self.t,
            "day": self.day,
            "half": self.half,
            "stock": copy.deepcopy(self.stock),
            "op": self.op.copy(),
            "arrivals_next": copy.deepcopy(self.arrivals_next),
            "pair_cursor": self.pair_cursor,
            "fleet": copy.deepcopy(self.fleet),
            "actions_log": copy.deepcopy(self.actions_log),
            "ops_by_spoke": self.ops_by_spoke[:],
        }

    def restore(self, snap: dict):
        self.t = snap["t"]
        self.day = snap["day"]
        self.half = snap["half"]
        self.stock = copy.deepcopy(snap["stock"])
        self.op = snap["op"].copy()
        self.arrivals_next = copy.deepcopy(snap["arrivals_next"])
        self.pair_cursor = snap["pair_cursor"]
        self.fleet = copy.deepcopy(snap["fleet"])
        self.actions_log = copy.deepcopy(snap["actions_log"])
        self.ops_by_spoke = snap.get("ops_by_spoke", [0]*self.M)[:]

    def push_snapshot(self):
        self.history.append(self.snapshot())

    def step_period(self):
        if self.t >= self.cfg.periods:
            return []

        # 1) Apply arrivals
        for s in range(self.M):
            if self.arrivals_next[s]:
                add = [0,0,0,0]
                for vec in self.arrivals_next[s]:
                    for k in range(4): add[k] += vec[k]
                self.arrivals_next[s].clear()
                for k in range(4): self.stock[s][k] += add[k]

        # 2) Operational if and only if A>0 and B>0
        for s in range(self.M):
            self.op[s] = (self.stock[s][0] > 0 and self.stock[s][1] > 0)

        stage = self.detect_stage()
        actions_this_period: List[Tuple[str,str]] = []
        pairs_used = set()  # ensure unique pair per period across all aircraft

        # 3) Aircraft actions
        for ac in sorted(self.fleet, key=lambda a: (-a.cap, a.name)):
            if ac.rest_cooldown > 0:
                actions_this_period.append((ac.name, "REST at HUB"))
                ac.rest_cooldown -= 1
                continue

            events = 0
            def consume_event():
                nonlocal events, ac
                events += 1
                if events == 1:
                    ac.active_periods += 1

            # rest if due
            if ac.at_hub() and ac.active_periods >= ac.max_active_before_rest(self.cfg) and ac.state in ("IDLE","REST"):
                actions_this_period.append((ac.name, "INITIATE REST at HUB"))
                ac.active_periods = 0
                ac.rest_cooldown = 1
                continue

            # progress in-flight states
            if ac.state == "LEG1_ENROUTE":
                ac.state = "AT_SPOKEA"
            if ac.state == "AT_SPOKEA":
                i = ac.plan[0]
                self.arrivals_next[i].append(ac.payload_A[:])
                self.ops_by_spoke[i] += 1
                actions_this_period.append((ac.name, f"OFFLOAD@S{i+1}"))
                ac.payload_A = [0,0,0,0]
                consume_event()
                if events < 2:
                    if ac.plan[1] is not None:
                        j = ac.plan[1]
                        ac.location = f"S{j+1}"
                        ac.state = "AT_SPOKEB_ENROUTE"
                        actions_this_period.append((ac.name, f"MOVE S{i+1}→S{j+1}"))
                        consume_event()
                    else:
                        ac.location = "HUB"
                        ac.state = "IDLE"
                        actions_this_period.append((ac.name, f"MOVE S{i+1}→HUB"))
                        consume_event()
                continue
            if ac.state == "AT_SPOKEB_ENROUTE":
                ac.state = "AT_SPOKEB"
            if ac.state == "AT_SPOKEB":
                j = ac.plan[1]
                self.arrivals_next[j].append(ac.payload_B[:])
                self.ops_by_spoke[j] += 1
                actions_this_period.append((ac.name, f"OFFLOAD@S{j+1}"))
                ac.payload_B = [0,0,0,0]
                consume_event()
                if events < 2:
                    ac.location = "HUB"
                    ac.state = "IDLE"
                    actions_this_period.append((ac.name, f"MOVE S{j+1}→HUB"))
                    consume_event()
                continue

            # new sortie
            if ac.at_hub() and ac.state == "IDLE":
                if ac.active_periods >= ac.max_active_before_rest(self.cfg):
                    actions_this_period.append((ac.name, "INITIATE REST at HUB"))
                    ac.active_periods = 0
                    ac.rest_cooldown = 1
                    continue

                tried = 0
                cursor = self.pair_cursor
                chosen_pair = None
                while tried < len(self.PAIR_ORDER):
                    i, j = self.PAIR_ORDER[cursor]
                    p_i, p_j = self.plan_for_pair_stage(i, j, ac.cap, stage)
                    key = (i, j if p_j and sum(p_j)>0 else -1)
                    if (sum(p_i) + sum(p_j)) > 0 and key not in pairs_used:
                        chosen_pair = (i, j)
                        break
                    cursor = (cursor + 1) % len(self.PAIR_ORDER)
                    tried += 1

                if chosen_pair is None:
                    continue

                i, j = chosen_pair
                p_i, p_j = self.plan_for_pair_stage(i, j, ac.cap, stage)
                if sum(p_i) == 0 and sum(p_j) == 0:
                    continue
                leg2_none = False
                if sum(p_j) == 0:
                    chosen_pair = (i, None)
                    leg2_none = True

                key = (i, (j if not leg2_none else -1))
                pairs_used.add(key)
                self.pair_cursor = (cursor + 1) % len(self.PAIR_ORDER)

                ac.plan = chosen_pair
                ac.payload_A = p_i[:]
                ac.payload_B = p_j[:] if not leg2_none else [0,0,0,0]
                actions_this_period.append((ac.name, f"ONLOAD@HUB→S{i+1}"))
                ac.location = f"S{i+1}"
                ac.state = "LEG1_ENROUTE"
                actions_this_period.append((ac.name, f"MOVE HUB→S{i+1}"))
                consume_event(); consume_event()

        # 4) PM consumption
        if self.t % 2 == 1:
            self.day = self.t // 2
            # A
            if (self.day % self.A_PERIOD_DAYS) == (self.A_PERIOD_DAYS - 1):
                for s in range(self.M):
                    self.stock[s][0] = max(0, self.stock[s][0] - 1)
            # B
            if (self.day % self.B_PERIOD_DAYS) == (self.B_PERIOD_DAYS - 1):
                for s in range(self.M):
                    self.stock[s][1] = max(0, self.stock[s][1] - 1)
            # C & D only if op and A,B available
            mask = [(self.stock[s][0] > 0 and self.stock[s][1] > 0) for s in range(self.M)]
            if (self.day % self.C_PERIOD_DAYS) == (self.C_PERIOD_DAYS - 1):
                for s in range(self.M):
                    if mask[s]:
                        self.stock[s][2] = max(0, self.stock[s][2] - 1)
            if (self.day % self.D_PERIOD_DAYS) == (self.D_PERIOD_DAYS - 1):
                for s in range(self.M):
                    if mask[s]:
                        self.stock[s][3] = max(0, self.stock[s][3] - 1)

        self.actions_log.append(actions_this_period)
        self.t += 1
        self.half = "AM" if self.t % 2 == 0 else "PM"

        self.push_snapshot()

        if self.cfg.debug_mode:
            lines = [f"[t={self.t} {self.half} day={self.t//2}] ops={self.ops_count()}"]
            lines += [f"  {nm}: {act}" for (nm, act) in actions_this_period]
            append_debug(lines)

        return actions_this_period

    def ops_count(self) -> int:
        return sum(1 for x in self.op if x)

# ------------------------- Recording Helpers -------------------------

class Recorder:
    def __init__(self, live: bool, out_dir: str, fps: int, fmt: str):
        self.live = live
        self.out_dir = out_dir
        self.fps = fps
        self.fmt = fmt
        self.frame_idx = 0
        if live:
            os.makedirs(out_dir, exist_ok=True)

    def capture(self, surface):
        if not self.live:
            return
        path = os.path.join(self.out_dir, f"frame_{self.frame_idx:06d}.png")
        pygame.image.save(surface, path)
        self.frame_idx += 1

    def finalize(self):
        if not self.live:
            return None
        if self.fmt == "MP4" and _HAS_IMAGEIO and self.frame_idx > 0:
            mp4_path = os.path.join(self.out_dir, "session.mp4")
            writer = imageio.get_writer(mp4_path, fps=self.fps, codec="libx264", quality=8)  # type: ignore
            for i in range(self.frame_idx):
                frame_path = os.path.join(self.out_dir, f"frame_{i:06d}.png")
                try:
                    img = imageio.imread(frame_path)  # type: ignore
                    writer.append_data(img)
                except Exception:
                    pass
            writer.close()
            return mp4_path
        return None

# ------------------------- Pygame Renderer -------------------------

class Renderer:
    def __init__(self, sim: LogisticsSim):
        if not _HAS_PYGAME:
            raise RuntimeError("pygame is required to run the simulator.")
        pygame.init()
        self.flags = pygame.RESIZABLE
        self.fullscreen = False
        pygame.display.set_caption("CargoSim — Hub–Spoke Logistics")
        self.width, self.height = 1200, 850
        self.screen = pygame.display.set_mode((self.width, self.height), self.flags)
        self.clock = pygame.time.Clock()
        self.sim = sim

        self._compute_layout()

        # Theme colors
        t = self.sim.cfg.theme
        def hex2rgb(h):
            h = h.lstrip("#")
            return tuple(int(h[i:i+2], 16) for i in (0,2,4))
        self.bg = hex2rgb(t.game_bg)
        self.white = hex2rgb(t.game_fg)
        self.grey = hex2rgb(t.game_muted)
        self.hub_color = hex2rgb(t.hub_color)
        self.good_spoke_col = hex2rgb(t.good_spoke)
        self.bad_spoke_col = hex2rgb(t.bad_spoke)
        self.ac_colors = {k: hex2rgb(v) for k,v in t.ac_colors.items()}
        self.bar_cols = [hex2rgb(t.bar_A), hex2rgb(t.bar_B), hex2rgb(t.bar_C), hex2rgb(t.bar_D)]

        self.font = pygame.font.SysFont("consolas", 18)
        self.bigfont = pygame.font.SysFont("consolas", 22, bold=True)

        self.period_seconds = float(self.sim.cfg.period_seconds)
        self.paused = False
        self.debug_overlay = bool(self.sim.cfg.debug_mode)
        self.exit_code = None  # "GUI" to return to control panel
        self.menu_open = False

        self.debug_lines: List[str] = []

        rcfg = self.sim.cfg.recording
        self.recorder = Recorder(live=rcfg.record_live,
                                 out_dir=rcfg.live_out_dir,
                                 fps=rcfg.fps,
                                 fmt=("MP4" if (rcfg.record_format == "MP4" and _HAS_IMAGEIO) else "PNG frames"))

        # Pause menu button rects
        self._pm_rects = {}

    def _compute_layout(self):
        self.cx = self.width // 2
        self.cy = self.height // 2
        side_pad = 180 if self.fullscreen else 40
        self.radius = int(min(self.cx - side_pad, self.cy - 120))
        self.spoke_pos = []
        for idx in range(M):
            theta = 2*math.pi*idx / M
            x = self.cx + (self.radius - 20) * math.cos(theta)
            y = self.cy + (self.radius - 20) * math.sin(theta)
            self.spoke_pos.append((x, y))

    def _toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            self.screen = pygame.display.set_mode((0,0), pygame.FULLSCREEN)
            self.width, self.height = self.screen.get_size()
        else:
            self.screen = pygame.display.set_mode((1200, 850), self.flags)
            self.width, self.height = 1200, 850
        self._compute_layout()

    def draw_spokes(self):
        pygame.draw.circle(self.screen, self.hub_color, (self.cx, self.cy), 10)
        hub_text = self.bigfont.render("HUB", True, self.white)
        self.screen.blit(hub_text, (self.cx - hub_text.get_width()//2, self.cy - 30))

        # Spokes: green if A>0 and B>0
        for i, (x, y) in enumerate(self.spoke_pos):
            has_A = self.sim.stock[i][0] > 0
            has_B = self.sim.stock[i][1] > 0
            color = self.good_spoke_col if (has_A and has_B) else self.bad_spoke_col
            pygame.draw.circle(self.screen, color, (int(x), int(y)), 9)
            label = self.font.render(f"S{i+1}", True, self.white)
            self.screen.blit(label, (int(x) - label.get_width()//2, int(y) - 26))

    def draw_bars(self):
        bar_w = 8
        gap = 4
        labels = ["A","B","C","D"]
        for i, (x, y) in enumerate(self.spoke_pos):
            base_x = int(x) + 14
            base_y = int(y) + 16
            for k in range(4):
                denom = VIS_CAPS_DFLT[k] if VIS_CAPS_DFLT[k] else 1
                ratio = self.sim.stock[i][k] / denom
                h = int(28 * min(2.0, ratio))
                rect = pygame.Rect(base_x + k*(bar_w+gap), base_y - h, bar_w, h)
                pygame.draw.rect(self.screen, self.bar_cols[k], rect)
                t = self.font.render(labels[k], True, self.grey)
                self.screen.blit(t, (rect.x + rect.w//2 - t.get_width()//2, rect.y + h + 2))

    def draw_hud(self):
        title = f"{self.sim.cfg.fleet_label} | Period {self.sim.t}/{self.sim.cfg.periods} ({self.sim.half}, Day {self.sim.t//2}) | Ops: {self.sim.ops_count()}"
        t = self.bigfont.render(title, True, self.white)
        self.screen.blit(t, (20, 16))

        help1 = self.font.render("SPACE pause | ←/→ step | +/− speed | D debug | F11 fullscreen | M minimize | G menu | R reset | ESC", True, self.grey)
        self.screen.blit(help1, (20, self.height - 30))

    def draw_aircraft(self, actions_this_period: List[Tuple[str,str]], alpha: float):
        moves_by_ac: Dict[str, List[Tuple[str,str]]] = {}
        for (nm, act) in actions_this_period:
            if act.startswith("MOVE"):
                body = act.split("MOVE")[1].strip()
                src, dst = body.split("→")
                moves_by_ac.setdefault(nm, []).append((src, dst))

        def node_xy(token: str):
            if token == "HUB": return (self.cx, self.cy)
            if token.startswith("S"):
                idx = int(token[1:]) - 1
                return self.spoke_pos[idx]
            return (self.cx, self.cy)

        for ac in self.sim.fleet:
            segs = moves_by_ac.get(ac.name, [])
            col = self.ac_colors.get(ac.typ, self.white)
            if not segs:
                pos = (self.cx, self.cy) if ac.location == "HUB" else self.spoke_pos[int(ac.location[1:])-1]
                self.draw_triangle(pos, ac.typ, ac.name, col)
            else:
                if alpha <= 0.5 and len(segs) >= 1:
                    s = segs[0]
                    a = (alpha / 0.5)
                    p0 = node_xy(s[0]); p1 = node_xy(s[1])
                    pos = (p0[0] + (p1[0]-p0[0])*a, p0[1] + (p1[1]-p0[1])*a)
                    self.draw_triangle(pos, ac.typ, ac.name, col)
                elif alpha > 0.5 and len(segs) >= 2:
                    s = segs[1]
                    a = (alpha - 0.5) / 0.5
                    p0 = node_xy(s[0]); p1 = node_xy(s[1])
                    pos = (p0[0] + (p1[0]-p0[0])*a, p0[1] + (p1[1]-p0[1])*a)
                    self.draw_triangle(pos, ac.typ, ac.name, col)
                else:
                    last = segs[-1]
                    pos = node_xy(last[1])
                    self.draw_triangle(pos, ac.typ, ac.name, col)

    def draw_triangle(self, pos, typ, name, color):
        x, y = int(pos[0]), int(pos[1])
        size = 14 if typ == "C-130" else 10
        pts = [(x, y - size), (x - size//2, y + size//2), (x + size//2, y + size//2)]
        pygame.draw.polygon(self.screen, color, pts)
        if self.sim.cfg.show_aircraft_labels:
            t = self.font.render(name, True, self.white)
            self.screen.blit(t, (x - t.get_width()//2, y - size - 16))

    def draw_debug_overlay(self):
        if not self.debug_overlay:
            return
        surf = pygame.Surface((int(self.width*0.45), int(self.height*0.35)), pygame.SRCALPHA)
        surf.fill((0, 0, 0, 128))
        x0, y0 = 20, 60
        self.screen.blit(surf, (x0, y0))

        lines = self.debug_lines[-18:]
        y = y0 + 8
        for ln in lines:
            t = self.font.render(ln, True, self.white)
            self.screen.blit(t, (x0 + 10, y))
            y += 18

    def draw_fullscreen_side_panels(self):
        if not self.fullscreen:
            return
        pad = 18
        panel_w = 160
        left_rect = pygame.Rect(0, 0, panel_w, self.height)
        right_rect = pygame.Rect(self.width - panel_w, 0, panel_w, self.height)
        pygame.draw.rect(self.screen, (20,20,24), left_rect)
        pygame.draw.rect(self.screen, (20,20,24), right_rect)

        # Left: operational spokes
        ops = self.sim.ops_count()
        max_ops = self.sim.M
        bar_h = int(self.height*0.25)
        bar_x = 24
        bar_y = 60
        pygame.draw.rect(self.screen, (50,50,60), (bar_x, bar_y, 24, bar_h), border_radius=6)
        fill_h = int(bar_h * (ops / max_ops if max_ops else 1))
        pygame.draw.rect(self.screen, (100,180,120), (bar_x, bar_y + (bar_h - fill_h), 24, fill_h), border_radius=6)
        label = self.font.render(f"Operational: {ops}", True, self.white)
        self.screen.blit(label, (bar_x - 4, bar_y - 24))

        totals = [sum(s[k] for s in self.sim.stock) for k in range(4)]
        if self.sim.cfg.stats_mode == "average":
            totals = [x / self.sim.M for x in totals]
        max_val = max(1.0, max(totals))
        bars_area_y = bar_y + bar_h + 40
        barw = 24
        gap = 18
        for k, val in enumerate(totals):
            h = int((self.height*0.25) * (val / max_val if max_val else 1))
            x = bar_x + k*(barw+gap)
            y = bars_area_y + (self.height*0.25 - h)
            pygame.draw.rect(self.screen, (60,60,70), (x, bars_area_y, barw, int(self.height*0.25)), border_radius=6)
            pygame.draw.rect(self.screen, self.bar_cols[k], (x, y, barw, h), border_radius=6)
            lbl = self.font.render(["A","B","C","D"][k], True, self.white)
            self.screen.blit(lbl, (x+4 - lbl.get_width()//2 + 6, bars_area_y - 22))
            val_str = f"{val:.1f}" if isinstance(val, float) else str(val)
            vtxt = self.font.render(val_str, True, self.grey)
            self.screen.blit(vtxt, (x - vtxt.get_width()//2 + 12, y - 18))

        # Right: per-spoke ops bars
        ops_counts = self.sim.ops_by_spoke
        max_ops_spoke = max(1, max(ops_counts) if ops_counts else 1)
        base_y = 60
        row_h = 24
        for i in range(self.sim.M):
            y = base_y + i*row_h
            pygame.draw.rect(self.screen, (60,60,70), (self.width - panel_w + 18, y, panel_w - 36, 12), border_radius=6)
            w = int((panel_w - 36) * (ops_counts[i] / max_ops_spoke))
            pygame.draw.rect(self.screen, (140,180,220), (self.width - panel_w + 18, y, w, 12), border_radius=6)
            lbl = self.font.render(f"S{i+1}", True, self.white)
            self.screen.blit(lbl, (self.width - panel_w + 18, y - 18))

    # --- Pause Menu ---
    def draw_pause_menu(self):
        # backdrop
        s = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        s.fill((0,0,0,160))
        self.screen.blit(s, (0,0))
        # box
        box_w, box_h = 420, 280
        bx = (self.width - box_w)//2
        by = (self.height - box_h)//2
        pygame.draw.rect(self.screen, (24,26,32), (bx,by,box_w,box_h), border_radius=12)
        title = self.bigfont.render("Paused", True, self.white)
        self.screen.blit(title, (bx + (box_w - title.get_width())//2, by + 16))

        # buttons
        labels = [("Resume", "resume"),
                  ("Record Offline", "offline"),
                  ("Main Menu", "menu"),
                  ("Exit", "exit")]
        self._pm_rects.clear()
        yy = by + 72
        for text, key in labels:
            rect = pygame.Rect(bx+40, yy, box_w-80, 44)
            pygame.draw.rect(self.screen, (44,46,56), rect, border_radius=8)
            t = self.font.render(text, True, self.white)
            self.screen.blit(t, (rect.x + (rect.w - t.get_width())//2, rect.y + (rect.h - t.get_height())//2))
            self._pm_rects[key] = rect
            yy += 56

    def handle_pause_click(self, pos):
        for key, rect in self._pm_rects.items():
            if rect.collidepoint(pos):
                if key == "resume":
                    self.menu_open = False
                    self.paused = False
                elif key == "offline":
                    # spawn a separate process to render offline video from saved config
                    try:
                        cfg_path = CONFIG_FILE
                        # ensure latest config saved
                        save_config(self.sim.cfg)
                        subprocess.Popen([sys.executable, os.path.abspath(__file__), "--offline-render"],
                                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        # brief on-screen confirmation
                        self.debug_lines.append("Started offline render in background.")
                    except Exception as e:
                        self.debug_lines.append(f"Offline render failed: {e}")
                elif key == "menu":
                    self.exit_code = "GUI"
                    pygame.event.post(pygame.event.Event(pygame.QUIT))
                elif key == "exit":
                    pygame.event.post(pygame.event.Event(pygame.QUIT))

    def run(self):
        running = True
        accum = 0.0
        actions = self.sim.actions_log[-1] if self.sim.actions_log else []

        if os.path.exists(DEBUG_LOG) and self.sim.cfg.debug_mode:
            try:
                os.remove(DEBUG_LOG)
            except Exception:
                pass

        while running:
            dt = self.clock.tick(60) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.VIDEORESIZE:
                    self.width, self.height = event.w, event.h
                    self.screen = pygame.display.set_mode((self.width, self.height), self.flags)
                    self._compute_layout()
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.paused = True
                        self.menu_open = True
                    elif event.key in (pygame.K_q,) and not self.menu_open:
                        running = False
                    elif event.key == pygame.K_SPACE and not self.menu_open:
                        self.paused = not self.paused
                    elif event.key == pygame.K_RIGHT and not self.menu_open:
                        self.step_forward()
                        actions = self.sim.actions_log[-1] if self.sim.actions_log else []
                        self._collect_debug_lines(actions)
                        accum = 0.0
                    elif event.key == pygame.K_LEFT and not self.menu_open:
                        self.step_back()
                        actions = self.sim.actions_log[-1] if self.sim.actions_log else []
                        self._collect_debug_lines(actions)
                        accum = 0.0
                    elif event.key in (pygame.K_PLUS, pygame.K_EQUALS) and not self.menu_open:
                        self.period_seconds = max(0.3, self.period_seconds * 0.85)
                    elif event.key in (pygame.K_MINUS, pygame.K_UNDERSCORE) and not self.menu_open:
                        self.period_seconds = min(5.0, self.period_seconds * 1.15)
                    elif event.key == pygame.K_r and not self.menu_open:
                        self.sim.reset_world()
                        actions = self.sim.actions_log[-1] if self.sim.actions_log else []
                        self._collect_debug_lines(actions)
                        accum = 0.0
                    elif event.key == pygame.K_d and not self.menu_open:
                        self.debug_overlay = not self.debug_overlay
                    elif event.key == pygame.K_g and not self.menu_open:
                        self.exit_code = "GUI"
                        running = False
                    elif (event.key == pygame.K_F11 or (event.key == pygame.K_RETURN and (pygame.key.get_mods() & pygame.KMOD_ALT))) and not self.menu_open:
                        self._toggle_fullscreen()
                    elif event.key == pygame.K_m and not self.menu_open:
                        try: pygame.display.iconify()
                        except Exception: pass
                elif event.type == pygame.MOUSEBUTTONDOWN and self.menu_open:
                    self.handle_pause_click(event.pos)

            if not self.paused and not self.menu_open and self.sim.t < self.sim.cfg.periods:
                accum += dt
                if accum >= self.period_seconds:
                    self.step_forward()
                    actions = self.sim.actions_log[-1] if self.sim.actions_log else []
                    self._collect_debug_lines(actions)
                    accum = 0.0

            # Render
            self.screen.fill(self.bg)
            self.draw_spokes()
            self.draw_bars()
            self.draw_hud()
            alpha = (accum / self.period_seconds) if self.period_seconds > 1e-3 else 0.0
            actions_current = self.sim.actions_log[-1] if self.sim.actions_log else []
            self.draw_aircraft(actions_current, alpha)
            self.draw_fullscreen_side_panels()
            self.draw_debug_overlay()
            if self.menu_open:
                self.draw_pause_menu()

            pygame.display.flip()

        out = self.recorder.finalize()
        pygame.quit()
        return out

    def _collect_debug_lines(self, actions):
        if not actions: return
        lines = [f"t={self.sim.t} {self.sim.half} ops={self.sim.ops_count()}"]
        lines += [f"  {nm}: {act}" for (nm,act) in actions]
        self.debug_lines.extend(lines)
        if self.sim.cfg.debug_mode:
            append_debug(lines)

    def step_forward(self):
        if self.sim.t < self.sim.cfg.periods:
            if len(self.sim.history) > 0 and (len(self.sim.history)-1) > self.sim.t:
                next_idx = self.sim.t + 1
                snap = self.sim.history[next_idx]
                self.sim.restore(snap)
            else:
                self.sim.step_period()

    def step_back(self):
        if len(self.sim.history) >= 2:
            target_idx = len(self.sim.history) - 2
            snap = self.sim.history[target_idx]
            self.sim.restore(snap)
            self.sim.history = self.sim.history[:target_idx+1]
            self.sim.actions_log = self.sim.actions_log[:target_idx]

# ------------------------- Offline Render (separate process) -------------------------

def render_offline(cfg: SimConfig):
    """
    Render a video directly from current config without interactive playback.
    Writes MP4 if imageio is available and path endswith .mp4, otherwise PNG frames folder.
    This function runs as a separate process from the ESC menu to avoid display conflicts.
    """
    if not _HAS_PYGAME:
        raise RuntimeError("pygame is required for offline rendering.")

    # headless surface rendering
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    import pygame as pg
    pg.init()
    w, h = 1200, 850
    screen = pg.Surface((w,h))

    # Build sim and a faux renderer that draws onto our surface without display
    class Headless(Renderer):
        def __init__(self, sim):
            # do not call display.set_mode (bypass parent __init__)
            self.sim = sim
            self.width, self.height = w, h
            self.screen = screen
            self.clock = None

            # ensure attributes used by _compute_layout / draw paths exist
            self.fullscreen = False
            self.flags = 0

            self._compute_layout()

            # theme
            t = self.sim.cfg.theme
            def hex2rgb(h):
                h = h.lstrip("#")
                return tuple(int(h[i:i+2], 16) for i in (0,2,4))
            self.bg = hex2rgb(t.game_bg)
            self.white = hex2rgb(t.game_fg)
            self.grey = hex2rgb(t.game_muted)
            self.hub_color = hex2rgb(t.hub_color)
            self.good_spoke_col = hex2rgb(t.good_spoke)
            self.bad_spoke_col = hex2rgb(t.bad_spoke)
            self.ac_colors = {k: hex2rgb(v) for k,v in t.ac_colors.items()}
            self.bar_cols = [hex2rgb(t.bar_A), hex2rgb(t.bar_B), hex2rgb(t.bar_C), hex2rgb(t.bar_D)]

            pygame.font.init()
            self.font = pygame.font.SysFont("consolas", 18)
            self.bigfont = pygame.font.SysFont("consolas", 22, bold=True)

            self.period_seconds = float(self.sim.cfg.period_seconds)
            self.debug_overlay = False
            self.paused = False

            # derive panel colors from theme so pause/menu visuals stay on-brand
            def blend(a, b, t):
                return tuple(int(a[i]*(1-t) + b[i]*t) for i in range(3))
            self.panel_bg = blend(self.bg, self.hub_color, 0.25)
            self.panel_btn = blend(self.bg, self.hub_color, 0.45)
            self.panel_btn_fg = self.white


        def run(self): pass  # not used

    sim = LogisticsSim(cfg)
    rnd = Headless(sim)

    rc = cfg.recording
    frames_per_period = max(1, rc.frames_per_period)
    total_frames = cfg.periods * frames_per_period

    # writer
    write_mp4 = (_HAS_IMAGEIO and rc.offline_out_file.lower().endswith(".mp4"))
    if write_mp4:
        writer = imageio.get_writer(rc.offline_out_file, fps=rc.fps, codec="libx264", quality=8)  # type: ignore
    else:
        out_dir = os.path.splitext(rc.offline_out_file)[0] + "_frames"
        os.makedirs(out_dir, exist_ok=True)

    frame_idx = 0
    for period in range(cfg.periods):
        actions = sim.actions_log[-1] if sim.actions_log else []
        for f in range(frames_per_period):
            alpha = (f + 1) / frames_per_period
            screen.fill(rnd.bg)
            rnd.draw_spokes()
            rnd.draw_bars()
            rnd.draw_hud()
            rnd.draw_aircraft(actions, alpha)
            if write_mp4:
                arr = pg.surfarray.array3d(screen).swapaxes(0,1)
                writer.append_data(arr)  # type: ignore
            else:
                frame_file = os.path.join(out_dir, f"frame_{frame_idx:06d}.png")
                pg.image.save(screen, frame_file)
            frame_idx += 1
        sim.step_period()

    if write_mp4:
        writer.close()
    pg.quit()
    return rc.offline_out_file if write_mp4 else out_dir

# ------------------------- Tkinter Control GUI -------------------------

class ControlGUI:
    def __init__(self, root: tk.Tk, cfg: SimConfig):
        self.root = root
        self.cfg = cfg
        root.title("CargoSim — Control Panel")
        root.geometry("860x760")
        root.minsize(760, 640)

        self._setup_style(initial_mode=self.cfg.theme.menu_theme)

        nb = ttk.Notebook(root, style="Tabs.TNotebook")
        nb.pack(fill="both", expand=True, padx=10, pady=10)

        self.tab_fleet = ttk.Frame(nb, padding=12, style="Card.TFrame")
        self.tab_init = ttk.Frame(nb, padding=12, style="Card.TFrame")
        self.tab_consumption = ttk.Frame(nb, padding=12, style="Card.TFrame")
        self.tab_schedule = ttk.Frame(nb, padding=12, style="Card.TFrame")
        self.tab_visual = ttk.Frame(nb, padding=12, style="Card.TFrame")
        self.tab_theme = ttk.Frame(nb, padding=12, style="Card.TFrame")
        self.tab_record = ttk.Frame(nb, padding=12, style="Card.TFrame")
        self.tab_start = ttk.Frame(nb, padding=12, style="Card.TFrame")

        nb.add(self.tab_fleet, text=" Fleet & Timing ")
        nb.add(self.tab_init, text=" Initial Stocks ")
        nb.add(self.tab_consumption, text=" Consumption ")
        nb.add(self.tab_schedule, text=" Scheduling ")
        nb.add(self.tab_visual, text=" Visualization ")
        nb.add(self.tab_theme, text=" Theme ")
        nb.add(self.tab_record, text=" Recording ")
        nb.add(self.tab_start, text=" Save / Start ")

        self.build_fleet_tab(self.tab_fleet)
        self.build_init_tab(self.tab_init)
        self.build_consumption_tab(self.tab_consumption)
        self.build_schedule_tab(self.tab_schedule)
        self.build_visual_tab(self.tab_visual)
        self.build_theme_tab(self.tab_theme)
        self.build_record_tab(self.tab_record)
        self.build_start_tab(self.tab_start)

        # After tabs are built, apply dependency gating
        self._apply_dependency_states()

    # ---- Style & Theme ----
    def _setup_style(self, initial_mode="dark"):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        self._apply_menu_theme(style, initial_mode)

    def _apply_menu_theme(self, style: ttk.Style, mode: str):
        if mode == "light":
            bg = "#f3f4f6"; card_bg = "#ffffff"; fg = "#111827"; subfg = "#4b5563"
            accent = "#2563eb"; accent_hover = "#1d4ed8"
            field_bg = "#f9fafb"
        else:
            bg = "#0f172a"; card_bg = "#111827"; fg = "#e5e7eb"; subfg = "#9ca3af"
            accent = "#2563eb"; accent_hover = "#1d4ed8"
            field_bg = "#0b1220"

        self.root.configure(bg=bg)
        style.configure(".", background=bg, foreground=fg, fieldbackground=field_bg)
        style.configure("Card.TFrame", background=card_bg, relief="flat")
        style.configure("TLabel", background=card_bg, foreground=fg, padding=2)
        style.configure("TCheckbutton", background=card_bg, foreground=fg)
        style.configure("TEntry", fieldbackground=field_bg, foreground=fg, insertcolor=fg, padding=4, relief="flat")
        style.configure("TSpinbox", fieldbackground=field_bg, foreground=fg, arrowsize=14)
        style.configure("TSeparator", background="#1f2937")

        style.configure("Accent.TButton", background=accent, foreground="white", padding=8, relief="flat", focusthickness=3)
        style.map("Accent.TButton", background=[("active", "#1d4ed8")], relief=[("pressed","groove")])

        style.configure("TButton", padding=6, relief="flat")
        style.map("TButton", background=[("active", "#374151")], relief=[("pressed","groove")])

        style.configure("Tabs.TNotebook", background=bg, borderwidth=0)
        style.configure("Tabs.TNotebook.Tab", padding=(16,8), background=field_bg, foreground=fg, borderwidth=0)
        style.map("Tabs.TNotebook.Tab", background=[("selected", card_bg), ("active", field_bg)], foreground=[("selected", fg)])
        style.configure("Horizontal.TScale", background=card_bg, troughcolor=field_bg)

    # ---- Helpers for "Scale + Entry" controls ----
    def _scale_with_entry(self, parent, label_text, from_, to_, var_type="int", init=0):
        frame = ttk.Frame(parent, style="Card.TFrame")
        frame.grid_columnconfigure(1, weight=1)

        ttk.Label(frame, text=label_text).grid(row=0, column=0, sticky="w")
        if var_type == "int":
            var = tk.IntVar(value=int(init))
            scale = ttk.Scale(frame, from_=from_, to=to_, orient="horizontal", variable=var)
            entry = ttk.Entry(frame, width=8)
            entry.insert(0, str(int(init)))
            def on_scale(_):
                entry.delete(0, tk.END); entry.insert(0, str(int(var.get())))
            def on_entry(_=None):
                try: v = int(entry.get())
                except Exception: v = int(init)
                v = max(int(from_), min(int(to_), v))
                var.set(v)
                entry.delete(0, tk.END); entry.insert(0, str(v))
            scale.bind("<B1-Motion>", on_scale); scale.bind("<ButtonRelease-1>", on_scale)
            entry.bind("<Return>", on_entry); entry.bind("<FocusOut>", on_entry)
        else:
            var = tk.DoubleVar(value=float(init))
            scale = ttk.Scale(frame, from_=from_, to=to_, orient="horizontal", variable=var)
            entry = ttk.Entry(frame, width=8)
            entry.insert(0, f"{float(init):.2f}")
            def on_scale(_):
                entry.delete(0, tk.END); entry.insert(0, f"{float(var.get()):.2f}")
            def on_entry(_=None):
                try: v = float(entry.get())
                except Exception: v = float(init)
                v = max(float(from_), min(float(to_), v))
                var.set(v)
                entry.delete(0, tk.END); entry.insert(0, f"{v:.2f}")
            scale.bind("<B1-Motion>", on_scale); scale.bind("<ButtonRelease-1>", on_scale)
            entry.bind("<Return>", on_entry); entry.bind("<FocusOut>", on_entry)

        scale.grid(row=0, column=1, sticky="we", padx=(8,6))
        entry.grid(row=0, column=2, sticky="w")
        return var, scale, entry, frame

    # ---- Tabs ----
    def build_fleet_tab(self, tab):
        g = ttk.Frame(tab, style="Card.TFrame")
        g.pack(fill="both", expand=True)

        left = ttk.Frame(g, style="Card.TFrame")
        left.pack(side="left", fill="both", expand=True, padx=(0,8))

        ttk.Label(left, text="Fleet").grid(row=0, column=0, sticky="w")
        self.fleet_var = tk.StringVar(value=self.cfg.fleet_label)
        ttk.OptionMenu(left, self.fleet_var, self.cfg.fleet_label, "2xC130","4xC130","2xC130_2xC27").grid(row=0, column=1, sticky="we")

        ttk.Label(left, text="Periods (AM/PM)").grid(row=1, column=0, sticky="w", pady=(6,0))
        self.periods_var = tk.IntVar(value=self.cfg.periods)
        ttk.Spinbox(left, from_=2, to=2000, textvariable=self.periods_var, width=10).grid(row=1, column=1, sticky="w")

        self.c130_cap_var, _, _, row2 = self._scale_with_entry(left, "C-130 Capacity", 1, 20, "int", self.cfg.cap_c130)
        row2.grid(row=2, column=0, columnspan=2, sticky="we", pady=(6,0))
        self.c27_cap_var, _, _, row3 = self._scale_with_entry(left, "C-27 Capacity", 1, 20, "int", self.cfg.cap_c27)
        row3.grid(row=3, column=0, columnspan=2, sticky="we", pady=(6,0))
        self.c130_rest_var, _, _, row4 = self._scale_with_entry(left, "C-130 Rest After (periods)", 2, 30, "int", self.cfg.rest_c130)
        row4.grid(row=4, column=0, columnspan=2, sticky="we", pady=(6,0))
        self.c27_rest_var, _, _, row5 = self._scale_with_entry(left, "C-27 Rest After (periods)", 2, 36, "int", self.cfg.rest_c27)
        row5.grid(row=5, column=0, columnspan=2, sticky="we", pady=(6,0))

        for r in range(6): left.rowconfigure(r, pad=4)
        left.columnconfigure(1, weight=1)

        right = ttk.Frame(g, style="Card.TFrame")
        right.pack(side="left", fill="both", expand=True, padx=(8,0))
        ttk.Label(right, text="Notes", foreground="#9ca3af").pack(anchor="w")
        ttk.Separator(right).pack(fill="x", pady=4)
        ttk.Label(right, text="• ESC opens pause menu: Resume / Record Offline / Main Menu / Exit.\n"
                              "• Press G anytime to return to this Control Panel.\n"
                              "• Debug Mode overlays actions and writes a log file.",
                  foreground="#9ca3af", justify="left").pack(anchor="w")

    def build_init_tab(self, tab):
        frm = ttk.Frame(tab, style="Card.TFrame")
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="Initial A (food)").grid(row=0, column=0, sticky="w")
        self.initA = tk.IntVar(value=self.cfg.init_A)
        ttk.Spinbox(frm, from_=0, to=100, textvariable=self.initA, width=10).grid(row=0, column=1, sticky="w")

        ttk.Label(frm, text="Initial B (fuel)").grid(row=1, column=0, sticky="w")
        self.initB = tk.IntVar(value=self.cfg.init_B)
        ttk.Spinbox(frm, from_=0, to=100, textvariable=self.initB, width=10).grid(row=1, column=1, sticky="w")

        ttk.Label(frm, text="Initial C (weapons)").grid(row=2, column=0, sticky="w")
        self.initC = tk.IntVar(value=self.cfg.init_C)
        ttk.Spinbox(frm, from_=0, to=100, textvariable=self.initC, width=10).grid(row=2, column=1, sticky="w")

        ttk.Label(frm, text="Initial D (spares)").grid(row=3, column=0, sticky="w")
        self.initD = tk.IntVar(value=self.cfg.init_D)
        ttk.Spinbox(frm, from_=0, to=100, textvariable=self.initD, width=10).grid(row=3, column=1, sticky="w")

        ttk.Label(frm, text="Unlimited Storage").grid(row=4, column=0, sticky="w", pady=(6,0))
        self.unlimited_var = tk.BooleanVar(value=self.cfg.unlimited_storage)
        ttk.Checkbutton(frm, variable=self.unlimited_var).grid(row=4, column=1, sticky="w")

        for r in range(5): frm.rowconfigure(r, pad=6)

    def build_consumption_tab(self, tab):
        frm = ttk.Frame(tab, style="Card.TFrame")
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="A cadence (days/unit)").grid(row=0, column=0, sticky="w")
        self.a_days = tk.IntVar(value=self.cfg.a_days)
        ttk.Spinbox(frm, from_=1, to=30, textvariable=self.a_days, width=10).grid(row=0, column=1, sticky="w")

        ttk.Label(frm, text="B cadence (days/unit)").grid(row=1, column=0, sticky="w")
        self.b_days = tk.IntVar(value=self.cfg.b_days)
        ttk.Spinbox(frm, from_=1, to=30, textvariable=self.b_days, width=10).grid(row=1, column=1, sticky="w")

        ttk.Label(frm, text="C cadence (days/unit)").grid(row=2, column=0, sticky="w")
        self.c_days = tk.IntVar(value=self.cfg.c_days)
        ttk.Spinbox(frm, from_=1, to=30, textvariable=self.c_days, width=10).grid(row=2, column=1, sticky="w")

        ttk.Label(frm, text="D cadence (days/unit)").grid(row=3, column=0, sticky="w")
        self.d_days = tk.IntVar(value=self.cfg.d_days)
        ttk.Spinbox(frm, from_=1, to=30, textvariable=self.d_days, width=10).grid(row=3, column=1, sticky="w")

        for r in range(4): frm.rowconfigure(r, pad=6)

    def build_schedule_tab(self, tab):
        frm = ttk.Frame(tab, style="Card.TFrame")
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="Milk‑run Pair Order (1‑based pairs, e.g. 1-2,3-4,5-6,7-8,9-10)").grid(row=0, column=0, sticky="w", columnspan=2)
        default_text = ",".join([f"{i+1}-{j+1}" for (i,j) in self.cfg.pair_order])
        self.pairs_entry = ttk.Entry(frm, width=42)
        self.pairs_entry.insert(0, default_text)
        self.pairs_entry.grid(row=1, column=0, columnspan=2, sticky="we", pady=(4,8))

        ttk.Label(frm, text="Planner priority", foreground="#9ca3af").grid(row=2, column=0, sticky="w")
        ttk.Label(frm, text="A-first, then B, else C/D (fixed)", foreground="#9ca3af").grid(row=2, column=1, sticky="w")

        frm.columnconfigure(0, weight=1)
        frm.columnconfigure(1, weight=1)

    def build_visual_tab(self, tab):
        frm = ttk.Frame(tab, style="Card.TFrame")
        frm.pack(fill="both", expand=True)

        self.per_sec_var, _, _, row0 = self._scale_with_entry(frm, "Seconds per Period", 0.3, 5.0, "float", self.cfg.period_seconds)
        row0.grid(row=0, column=0, columnspan=2, sticky="we")

        ttk.Label(frm, text="Show Aircraft Labels").grid(row=1, column=0, sticky="w", pady=(6,0))
        self.show_aircraft_labels = tk.BooleanVar(value=self.cfg.show_aircraft_labels)
        ttk.Checkbutton(frm, variable=self.show_aircraft_labels).grid(row=1, column=1, sticky="w")

        ttk.Label(frm, text="Debug Mode (overlay + log)").grid(row=2, column=0, sticky="w", pady=(6,0))
        self.debug_mode = tk.BooleanVar(value=self.cfg.debug_mode)
        ttk.Checkbutton(frm, variable=self.debug_mode).grid(row=2, column=1, sticky="w")

        ttk.Label(frm, text="Stats Mode").grid(row=3, column=0, sticky="w", pady=(6,0))
        self.stats_mode = tk.StringVar(value=self.cfg.stats_mode)
        ttk.OptionMenu(frm, self.stats_mode, self.cfg.stats_mode, "total", "average").grid(row=3, column=1, sticky="w")

        frm.columnconfigure(0, weight=1)
        frm.columnconfigure(1, weight=1)

    def build_theme_tab(self, tab):
        frm = ttk.Frame(tab, style="Card.TFrame")
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="Theme Preset").grid(row=0, column=0, sticky="w")
        self.theme_preset = tk.StringVar(value=self.cfg.theme.preset)
        presets = list(THEME_PRESETS.keys())
        def on_theme_change(choice):
            # apply preset immediately
            p = THEME_PRESETS.get(self.theme_preset.get(), THEME_PRESETS["Classic Dark"])
            self.cfg.theme.preset = self.theme_preset.get()
            self.cfg.theme.menu_theme = p["menu_mode"]
            self.cfg.theme.game_bg = p["game_bg"]
            self.cfg.theme.game_fg = p["game_fg"]
            self.cfg.theme.game_muted = p["game_muted"]
            self.cfg.theme.hub_color = p["hub_color"]
            self.cfg.theme.good_spoke = p["good_spoke"]
            self.cfg.theme.bad_spoke = p["bad_spoke"]
            self.cfg.theme.bar_A = p["bar_A"]
            self.cfg.theme.bar_B = p["bar_B"]
            self.cfg.theme.bar_C = p["bar_C"]
            self.cfg.theme.bar_D = p["bar_D"]
            # reflect immediately on GUI theme
            self._apply_menu_theme(ttk.Style(), self.cfg.theme.menu_theme)
        ttk.OptionMenu(frm, self.theme_preset, self.cfg.theme.preset, *presets, command=lambda _: on_theme_change(None)).grid(row=0, column=1, sticky="w")

        ttk.Separator(frm).grid(row=1, column=0, columnspan=2, sticky="we", pady=8)

        ttk.Label(frm, text="Airframe Color Map").grid(row=2, column=0, sticky="w")
        self.color_map = tk.StringVar(value="Neutral Grays")
        def on_colorset_change(*_):
            cmap = AIRFRAME_COLORSETS.get(self.color_map.get(), AIRFRAME_COLORSETS["Neutral Grays"])
            self.cfg.theme.ac_colors = cmap
        ttk.OptionMenu(frm, self.color_map, "Neutral Grays", *AIRFRAME_COLORSETS.keys(), command=on_colorset_change).grid(row=2, column=1, sticky="w")

        frm.columnconfigure(1, weight=1)

    def build_record_tab(self, tab):
        frm = ttk.Frame(tab, style="Card.TFrame")
        frm.pack(fill="both", expand=True)

        self.record_live = tk.BooleanVar(value=self.cfg.recording.record_live)
        ttk.Checkbutton(frm, text="Record Live Session", variable=self.record_live).grid(row=0, column=0, sticky="w")

        ttk.Label(frm, text="Record Format").grid(row=1, column=0, sticky="w", pady=(6,0))
        # MP4 only enabled if imageio available
        opts = ["PNG frames"] + (["MP4"] if _HAS_IMAGEIO else [])
        self.record_format = tk.StringVar(value=(self.cfg.recording.record_format if self.cfg.recording.record_format in opts else "PNG frames"))
        self.record_format_menu = ttk.OptionMenu(frm, self.record_format, self.record_format.get(), *opts)
        self.record_format_menu.grid(row=1, column=1, sticky="w")

        ttk.Label(frm, text="Live Output Folder").grid(row=2, column=0, sticky="w", pady=(6,0))
        self.live_out_dir = ttk.Entry(frm, width=28)
        self.live_out_dir.insert(0, self.cfg.recording.live_out_dir)
        self.live_out_dir.grid(row=2, column=1, sticky="w")
        def pick_live_dir():
            d = filedialog.askdirectory(title="Select Output Folder", initialdir=os.path.abspath(self.live_out_dir.get() or "."))
            if d:
                self.live_out_dir.delete(0, tk.END); self.live_out_dir.insert(0, d)
        ttk.Button(frm, text="Browse…", command=pick_live_dir).grid(row=2, column=2, sticky="w", padx=6)

        self.fps_var, _, _, row3 = self._scale_with_entry(frm, "FPS", 10, 60, "int", self.cfg.recording.fps)
        row3.grid(row=3, column=0, columnspan=3, sticky="we", pady=(6,0))

        self.fpp_var, _, _, row4 = self._scale_with_entry(frm, "Frames per Period (offline)", 1, 60, "int", self.cfg.recording.frames_per_period)
        row4.grid(row=4, column=0, columnspan=3, sticky="we", pady=(6,0))

        ttk.Label(frm, text="Offline Output").grid(row=5, column=0, sticky="w", pady=(6,0))
        self.offline_out = ttk.Entry(frm, width=28)
        self.offline_out.insert(0, self.cfg.recording.offline_out_file)
        self.offline_out.grid(row=5, column=1, sticky="w")
        def pick_offline_out():
            # choose file path; default .mp4 but can be any
            path = filedialog.asksaveasfilename(title="Select Offline Output File",
                                                defaultextension=".mp4",
                                                initialfile=os.path.basename(self.offline_out.get() or "render.mp4"),
                                                filetypes=[("MP4 Video","*.mp4"),("All Files","*.*")])
            if path:
                self.offline_out.delete(0, tk.END); self.offline_out.insert(0, path)
        ttk.Button(frm, text="Browse…", command=pick_offline_out).grid(row=5, column=2, sticky="w", padx=6)

        def do_offline_render():
            if not self._read_back_to_cfg():
                return
            if not _HAS_PYGAME:
                messagebox.showerror("Missing Dependency", "pygame is required for offline rendering.")
                return
            save_config(self.cfg)
            out = render_offline(self.cfg)
            messagebox.showinfo("Offline Render Complete", f"Output written to:\n{out}")
        self.offline_btn = ttk.Button(frm, text="Render Offline Video Now", style="Accent.TButton", command=do_offline_render)
        self.offline_btn.grid(row=6, column=0, columnspan=3, sticky="we", pady=(12,0))

        # Info label if MP4 disabled
        if not _HAS_IMAGEIO:
            ttk.Label(frm, text="Tip: install 'imageio' + 'imageio-ffmpeg' to enable MP4 output.", foreground="#9ca3af").grid(row=7, column=0, columnspan=3, sticky="w", pady=(6,0))

        frm.columnconfigure(0, weight=1)
        frm.columnconfigure(1, weight=1)

    def build_start_tab(self, tab):
        frm = ttk.Frame(tab, style="Card.TFrame")
        frm.pack(fill="both", expand=True)

        self.dep_msg = ttk.Label(frm, text="", foreground="#9ca3af")
        self.dep_msg.pack(anchor="w", pady=(0,8))

        btn_row = ttk.Frame(frm, style="Card.TFrame")
        btn_row.pack(fill="x", pady=10)

        self.save_btn = ttk.Button(btn_row, text="Save Config", command=self.on_save, style="TButton")
        self.save_btn.pack(side="left", padx=6)
        self.start_btn = ttk.Button(btn_row, text="Start Simulation", command=self.on_start, style="Accent.TButton")
        self.start_btn.pack(side="right", padx=6)

    # ---- Parsing helpers ----
    def _parse_pairs(self, text: str) -> Optional[List[Tuple[int,int]]]:
        try:
            pairs = []
            parts = [p.strip() for p in text.split(",") if p.strip()]
            for part in parts:
                a,b = part.split("-")
                i = int(a) - 1
                j = int(b) - 1
                if i<0 or j<0 or i>=M or j>=M: return None
                pairs.append((i,j))
            return pairs
        except Exception:
            return None

    def _read_back_to_cfg(self) -> bool:
        self.cfg.fleet_label = self.fleet_var.get()
        self.cfg.periods = int(self.periods_var.get())

        self.cfg.cap_c130 = int(self.c130_cap_var.get())
        self.cfg.cap_c27 = int(self.c27_cap_var.get())
        self.cfg.rest_c130 = int(self.c130_rest_var.get())
        self.cfg.rest_c27 = int(self.c27_rest_var.get())

        self.cfg.init_A = int(self.initA.get())
        self.cfg.init_B = int(self.initB.get())
        self.cfg.init_C = int(self.initC.get())
        self.cfg.init_D = int(self.initD.get())
        self.cfg.unlimited_storage = bool(self.unlimited_var.get())

        self.cfg.a_days = int(self.a_days.get())
        self.cfg.b_days = int(self.b_days.get())
        self.cfg.c_days = int(self.c_days.get())
        self.cfg.d_days = int(self.d_days.get())

        pairs = self._parse_pairs(self.pairs_entry.get().strip())
        if not pairs:
            messagebox.showerror("Invalid Pair Order", "Use format: 1-2,3-4,5-6,7-8,9-10")
            return False
        self.cfg.pair_order = pairs

        self.cfg.period_seconds = float(self.per_sec_var.get())
        self.cfg.show_aircraft_labels = bool(self.show_aircraft_labels.get())
        self.cfg.debug_mode = bool(self.debug_mode.get())
        self.cfg.stats_mode = self.stats_mode.get()

        # Theme preset already applied on change; persist
        self.cfg.theme.preset = self.theme_preset.get()
        # Airframe set already applied; persist
        self.cfg.theme.ac_colors = AIRFRAME_COLORSETS.get(self.color_map.get(), AIRFRAME_COLORSETS["Neutral Grays"])

        # Recording
        self.cfg.recording.record_live = bool(self.record_live.get())
        self.cfg.recording.record_format = self.record_format.get()
        self.cfg.recording.live_out_dir = self.live_out_dir.get().strip() or "captures"
        self.cfg.recording.fps = int(self.fps_var.get())
        self.cfg.recording.frames_per_period = int(self.fpp_var.get())
        self.cfg.recording.offline_out_file = self.offline_out.get().strip() or "render.mp4"

        return True

    def _apply_dependency_states(self):
        # Grey out / message for missing deps
        msg = []
        if not _HAS_PYGAME:
            msg.append("pygame missing — simulation & offline render disabled")
            self.start_btn.configure(state="disabled")
        if not _HAS_IMAGEIO:
            msg.append("imageio/imageio-ffmpeg missing — MP4 assembly disabled")
            # Adjust dropdown value & state
            self.record_format.set("PNG frames")
            self.record_format_menu.configure(state="disabled")
        self.dep_msg.configure(text=("; ".join(msg) if msg else "All dependencies available."))

    def on_save(self):
        if self._read_back_to_cfg():
            save_config(self.cfg)
            messagebox.showinfo("Saved", "Configuration saved.")

    def on_start(self):
        if not self._read_back_to_cfg():
            return
        if not _HAS_PYGAME:
            messagebox.showerror("Missing Dependency", "pygame is required to run the simulation.")
            return
        save_config(self.cfg)
        self.root.destroy()
        exit_code, live_out = run_sim(self.cfg)
        if exit_code == "GUI":
            main()

# ------------------------- Entrypoints & CLI -------------------------

def run_sim(cfg: SimConfig):
    sim = LogisticsSim(cfg)
    renderer = Renderer(sim)
    live_out = renderer.run()
    return renderer.exit_code, live_out

def main():
    # dependencies prompt on startup
    tmp = tk.Tk(); tmp.withdraw()
    check_and_offer_installs(tmp)
    tmp.destroy()

    cfg = load_config()
    # ensure theme preset fields are coherent (apply if not yet applied)
    preset = THEME_PRESETS.get(cfg.theme.preset, THEME_PRESETS["Classic Dark"])
    cfg.theme.menu_theme = preset["menu_mode"]
    cfg.theme.game_bg = preset["game_bg"]
    cfg.theme.game_fg = preset["game_fg"]
    cfg.theme.game_muted = preset["game_muted"]
    cfg.theme.hub_color = preset["hub_color"]
    cfg.theme.good_spoke = preset["good_spoke"]
    cfg.theme.bad_spoke = preset["bad_spoke"]
    cfg.theme.bar_A = preset["bar_A"]
    cfg.theme.bar_B = preset["bar_B"]
    cfg.theme.bar_C = preset["bar_C"]
    cfg.theme.bar_D = preset["bar_D"]

    root = tk.Tk()
    ControlGUI(root, cfg)
    root.mainloop()

if __name__ == "__main__":
    if "--offline-render" in sys.argv:
        cfg = load_config()
        out = render_offline(cfg)
        print(out)
    else:
        main()