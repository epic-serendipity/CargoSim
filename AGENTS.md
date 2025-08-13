# Agent Notes

## Adding a theme preset
- Provide all core tokens: `menu_theme`, `game_bg`, `game_fg`, `game_muted`,
  `hub_color`, `good_spoke`, `bad_spoke`, `bar_A`, `bar_B`, `bar_C`, `bar_D`.
- Ensure contrast between `game_fg` and `game_bg` is ≥ 4.5:1 for HUD text.
- Bars A/B/C/D must be perceptually distinct.
- Never override a user's selected airframe color map (`ac_colors`).
- Renderer derives `panel_bg`, `panel_btn`, `panel_btn_fg` and
  `overlay_backdrop_rgba` from `game_bg` + `hub_color`; avoid hardcoded greys.
- Cyber theme must use only green on black; bad spokes pulse with a dashed ring.
- New presets must not introduce hardcoded colors elsewhere; always reuse theme
  tokens.

## Cursor color menu
- UI shows only color names; hex codes live in `CURSOR_COLORS`.
- Exactly five options are supported; no greys or neutrals.

## Overlay stats
- When adding recording overlay stats, draw them in both interactive and
  headless renderers.

## Coding
- Follow existing snake_case style and keep functions compact.
- Persist new `SimConfig` fields via `to_json` / `from_json` and bump
  `CONFIG_VERSION` when changing schema.
- Prefer non-blocking design for recording; respect queue limits and dropping
  behaviour controlled by config.

## Tests
- `python -m py_compile cargo_sim_with_gui.py`
- `python cargo_sim_with_gui.py --offline-render` (may fail if pygame missing).
