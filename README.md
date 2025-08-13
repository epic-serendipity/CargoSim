# CargoSim

CargoSim models a hub-and-spoke airlift network with daily AM/PM cadence. Aircraft ferry supplies to spokes and operations consume resources.

## Quickstart (60 seconds)
1. Install: `pipx install .` or `pip install -e .[video]`
2. Run the GUI: `cargosim`
3. Headless help: `cargosim-headless --help`

## Core Concepts
- Periods alternate AM/PM; arrivals apply at the next period.
- **Ops gate:** A+B+C+D must all be >0 for an op to run.
- Only ops consume C and D. PM consumption requires A>0 and B>0 and reduces only A and B.
- A spoke is operational (green) only if it has A, B, C, and D on hand now (arrivals become usable next period).
- Each op consumes one unit of C and D at that spoke; A and B gate PM consumption and ops eligibility but are not consumed by the op itself.

## Features
- Five themes: GitHub Dark, Classic Light, Solarized Light, Night Ops, Cyber (green/black).
- Five cursor colors and overlay presets.
- Async recording with dropped-frame HUD.
- Pause menu and right-panel views (Total Ops number, sparkline, per-spoke).

## Controls
Key highlights: `SPACE` pause, `←/→` step, `+/-` speed, `R` reset, `D` debug, `ESC` menu.

## Recording
Live recording writes MP4 or PNG when a folder is set. Offline rendering requires a file path and runs atomically with progress and cancel options.

## Gameplay Tab
- Realism: distance affects leg times.
- Fleet Optimization: configurable weights.

## Advanced Decision Making
Fairness cooldown, A/B target DoS, emergency A preempt, deterministic RNG seed.

## Determinism & Invariants
Seed options enable reproducibility. Invariants log or assert non‑negative stocks and correct C/D usage on ops.

## Scenarios & Batch
Use `--scenario` and `--runs` to batch simulations; results emit CSV/JSON.

## Theming
Presets affect UI and renderer. Cyber theme is strictly green on black with pulsing warnings.

## Troubleshooting
Missing deps? install `pygame` or `imageio-ffmpeg`. Check codecs, file permissions, and fullscreen/windowing quirks.

## License
MIT

## Contributing & Code of Conduct
PRs welcome. By participating you agree to the [Contributor Covenant](CODE_OF_CONDUCT.md) code of conduct.
