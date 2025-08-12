
CargoSim — Control GUI + Visualizer (Themed, Recording, Offline Render)
======================================================================

Run:
    python cargo_sim_with_gui.py

Themes
------
The **Theme** tab lets you choose from ten presets (Classic Light/Dark, Cyber,
GitHub Light/Dark, Night Ops, Solarized Light/Dark, Desert, Ocean). Presets
apply consistently to the Tk control panel, the Pygame simulation, pause menu
and fullscreen overlays. Selecting a preset restyles the control panel
immediately; the next simulation you launch will use the same palette. Aircraft
colors are controlled separately via the *Airframe Color Map* menu and are not
overwritten when switching presets.

New controls:
- Sliders now have digital readouts (Entry fields) — type values directly or drag the slider.
- Theme tab: pick a light/dark menu theme, set game colors (BG, text, hub, spoke good/bad), aircraft colors per type, and supply bar colors.
- Recording tab: 
  * Record Live Session (frames to a folder; if imageio is available and you choose MP4, a session.mp4 is assembled after exit).
  * Offline render: creates a video WITHOUT running the interactive sim, using frames_per_period × periods at your chosen FPS.
- Visualization tab: Stats Mode = total or average for the fullscreen left panel bars.

Visualizer keys:
- SPACE pause/play
- LEFT / RIGHT step backward/forward
- + / − speed up / slow down
- D toggle debug overlay
- F11 or Alt+Enter fullscreen
- M minimize
- G return to Control Panel
- R reset

Notes:
- The ops counter is uncapped now.
- HOME/END jumps removed.
- In fullscreen, the left panel shows operational spokes and supply totals/averages; the right panel shows per‑spoke ops counts (number of OFFLOADs serviced at each spoke).
- If MP4 assembly isn't available (no imageio), you'll still get PNG frames you can stitch with another tool.
