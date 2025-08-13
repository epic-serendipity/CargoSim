# Project Map

## Theme system
Core theme tokens are stored in `ThemeConfig`:
- `menu_theme`
- `game_bg`, `game_fg`, `game_muted`
- `hub_color`, `good_spoke`, `bad_spoke`
- `bar_A`, `bar_B`, `bar_C`, `bar_D`
- `ac_colors` populated from the selected airframe color map

At runtime the renderer derives:
- `panel_bg`, `panel_btn`, `panel_btn_fg`
- `overlay_backdrop_rgba`
from core tokens using a shared `hex2rgb` and `blend(a,b,t)` helper so all
surfaces stay on theme.

Both the interactive `Renderer` and offline `Headless` renderer compute and use
these values so offline frames match the on‑screen simulation.

Presets supply core tokens and may specify a `default_airframe_colorset` for
first‑run defaults. Switching presets does not modify the user's chosen
airframe colors.

Cursor highlight color is stored by name in `SimConfig.cursor_color` and mapped
internally via `CURSOR_COLORS` to fixed hex values. UI elements show only the
names (Cobalt, Signal Orange, Cyber Lime, Cerulean, Royal Magenta).

## Visualization

- Right-side fullscreen panel modes:
- `ops_total_number` (default) shows a large running total of OFFLOAD ops.
  - `ops_total_sparkline` plots a sparkline of recent totals (up to 120 points).
  - `per_spoke` shows legacy per-spoke bars.
- Aircraft glyphs can optionally rotate toward their current destination when
  `orient_aircraft` is enabled. On departure from the hub the heading smoothly
  interpolates from north to the leg heading over the first ~15 % of the
  segment. When parked at the hub, glyphs are forced to face north.

## Recording paths and offline render

- Live recording is disabled until the user selects an existing output folder.
- The recording subsystem uses a producer/consumer queue with an optional
  asynchronous writer thread. When the queue fills, frames may be dropped rather
  than blocking the GUI. The HUD shows dropped counts.
- Offline rendering requires an explicit file path; the render button spawns a
  background process and shows progress with Cancel/Reveal buttons. Polling
  cadence is configurable.
- All saved paths are normalized to absolute form in the config file.
- Headless offline rendering creates a hidden 1×1 display using the SDL "dummy"
  driver so that surface conversions like `convert_alpha()` succeed without a
  visible window.
The overlay pipeline is: HUD/overlays are drawn onto the Pygame surface → the
resulting frame is scaled if requested → the writer thread/process encodes the
frame to MP4 or PNG.

Static text surfaces and hub/spoke geometry are cached to avoid per-frame
recreation. `ops_total_history` is bounded to the most recent 2000 points to
prevent unbounded growth.

## Advanced Decision Making & Gameplay

- `SimConfig.adm` holds fairness cooldowns, target days-of-supply for A/B,
  an emergency preemption toggle and a deterministic seed.
- `SimConfig.gameplay` contains realism toggles, leg time radius ranges and
  fleet optimization weights grouped under the *Gameplay* tab.
