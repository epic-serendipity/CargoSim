# CargoSim (WIP)
*All features subject to change or deprication.*

CargoSim models a hub-and-spoke airlift network with daily AM/PM cadence. Aircraft ferry supplies to spokes and operations consume resources.

## Quickstart (60 seconds)
1. Install: `pipx install .` or `pip install -e .[video]`
2. Run the GUI: `cargosim`
3. Headless help: `cargosim-headless --help`

## Core Concepts
- Periods alternate AM/PM; arrivals apply at the next period.
- Ops can run only when a spoke has A, B, C, and D on hand now (arrivals are usable next period). Each op consumes one unit of C and D; A and B gate ops/PM but are not consumed by the op.

## Features
- Five themes: GitHub Dark, Classic Light, Solarized Light, Night Ops, Cyber (green/black).
- Five cursor colors and overlay presets.
- Async recording with dropped-frame HUD.
- Pause menu and right-panel views (Total Ops number, sparkline, per-spoke).

## Controls
Key highlights: `SPACE` pause, `←/→` step, `+/-` speed, `R` reset, `D` debug, `ESC` menu.

## Recording
Live recording writes MP4 or PNG when a folder is set. Offline rendering requires a file path and runs atomically with progress and cancel options.
By default, recordings capture the fullscreen resolution with all HUD and side panels visible.
## Advanced Decision Making
Fairness cooldown, A/B target DoS, emergency A preempt, deterministic RNG seed.

## Scenarios & Batch
Use `--scenario` and `--runs` to batch simulations; results emit CSV/JSON.

## Troubleshooting
Missing deps? install `pygame` or `imageio-ffmpeg`. Check codecs, file permissions, and fullscreen/windowing quirks.
## Contributing & Code of Conduct
PRs welcome. By participating you agree to the [Contributor Covenant](CODE_OF_CONDUCT.md) code of conduct.
