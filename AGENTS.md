# Agent Notes

## Adding a theme preset
- Define `menu_theme`, `game_bg`, `game_fg`, `game_muted`, `hub_color`,
  `good_spoke`, `bad_spoke`, `bar_A`, `bar_B`, `bar_C`, `bar_D`.
- Optionally include `default_airframe_colorset`; never set `ac_colors` directly.
- Ensure `game_fg` vs `game_bg` contrast ≥ 4.5:1.
- Bar colors A–D must be visually distinct.
- Do not override a user's chosen airframe color map when applying presets.
