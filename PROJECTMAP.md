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

Both the interactive `Renderer` and offline `Headless` renderer compute and use
these values so offline frames match the on‑screen simulation.

Presets supply core tokens and may specify a `default_airframe_colorset` for
first‑run defaults. Switching presets does not modify the user's chosen
airframe colors.

## Visualization

- Right-side fullscreen panel modes:
  - `ops_total_number` (default) shows a large running total of OFFLOAD ops.
  - `ops_total_sparkline` plots a sparkline of recent totals.
  - `per_spoke` shows legacy per-spoke bars.
- Aircraft glyphs can optionally rotate toward their current destination when
  `orient_aircraft` is enabled. Both interactive and headless renderers share
  this behavior.

## Recording paths and offline render

- Live recording is disabled until the user selects an existing output folder.
- Offline rendering requires an explicit file path; the render button spawns a
  background process and shows progress with Cancel/Reveal buttons.
- All saved paths are normalized to absolute form in the config file.
