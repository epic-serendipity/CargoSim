# Agent Notes

## Adding a theme preset
- Provide all core tokens: `menu_theme`, `game_bg`, `game_fg`, `game_muted`,
  `hub_color`, `good_spoke`, `bad_spoke`, `bar_A`, `bar_B`, `bar_C`, `bar_D`.
- Ensure contrast between `game_fg` and `game_bg` is ≥ 4.5:1 for HUD text.
- Bars A/B/C/D must be perceptually distinct.
- Never override a user's selected airframe color map (`ac_colors`).
- Renderer derives `panel_bg`, `panel_btn`, `panel_btn_fg` and
  `overlay_backdrop_rgba` from `game_bg` + `hub_color`; avoid hardcoded greys.
