
CargoSim — Control GUI + Visualizer (Themed, Recording, Offline Render)
======================================================================

Run:
    python cargo_sim_with_gui.py

Highlights
---------
- **Themes:** ten distinct presets with derived tokens; Cyber is pure green on
  jet black.
- **Recording Overlays:** presets plus optional statistics for live and offline
  captures.
- **Seconds/Period:** slider now ranges from 2.00 s down to 0.05 s with a live
  numeric readout.

Themes and Recording
--------------------
The **Theme** tab offers ten presets (Classic Light/Dark, Cyber, GitHub
Light/Dark, Night Ops, Solarized Light/Dark, Desert, Ocean). Presets restyle
the Tk control panel, Pygame scene, pause menu and fullscreen side panels using
named tokens rather than hardcoded colors. Aircraft colors are chosen
independently via the *Airframe Color Map* menu and are never overridden by a
theme.

Recording requires explicit destinations. The **Recording** tab lets you select
a folder for live captures and a file path for offline renders; recording will
refuse to start until these paths are set. Live sessions write `session_*.mp4`
or PNG frames using an asynchronous producer/consumer queue. If the queue
fills, frames are dropped rather than blocking the UI and the HUD shows
"REC n (dropped=x)". Offline renders run in a background process with progress
and a *Cancel* button.

Advanced Decision Making & Gameplay
-----------------------------------
The **Scheduling** tab now includes an *Advanced Decision Making* group for
tuning routing behavior (fairness cooldowns, target days-of-supply and a
deterministic seed). A new **Gameplay** tab exposes toggles for *Realism* and
*Fleet Optimization* features with adjustable weights.

Right Panel Views
-----------------
The fullscreen right panel defaults to a large **Total Ops** number. Switch
between the number, a rolling sparkline or legacy per-spoke bars via the
*Right Panel View* menu on the **Visualization** tab.

Aircraft Heading
----------------
Enable *Orient Aircraft Toward Destination* on the **Visualization** tab to
rotate aircraft icons toward their current destination. Disable it to keep all
triangles upright. While parked at the hub, aircraft always face due north.

Below this are *Recording Overlays* controls for what appears in live
recordings: HUD, debug overlay, fullscreen panels, REC watermark, timestamps,
frame indices, scale percentage and aircraft labels.

Other controls:
- Sliders now have digital readouts (Entry fields) — type values directly or drag the slider.
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
- In fullscreen, the left panel shows operational spokes and supply totals/averages. The right panel can show a running Total Ops number, a Total Ops sparkline, or per‑spoke ops counts.
- If MP4 assembly isn't available (no imageio), you'll still get PNG frames you can stitch with another tool.
