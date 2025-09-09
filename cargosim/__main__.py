"""Command-line entry point for CargoSim.

Minimizes import-time overhead by importing heavy GUI paths only
when needed. Headless mode imports core modules directly.
"""

import argparse
import sys
from cargosim.core.config import load_config
from cargosim.core.simulation import LogisticsSim


def run_headless(duration_minutes: int, seed: int) -> int:
    """Run the simulation in headless mode (minute-based)."""
    print(f"Starting headless simulation: duration_minutes={duration_minutes}, seed={seed}")
    cfg = load_config()
    cfg.duration_minutes = duration_minutes
    cfg.seed = seed
    print(f"Config loaded: duration_minutes={cfg.duration_minutes}, seed={cfg.seed}")
    
    sim = LogisticsSim(cfg)
    print(f"Simulation created: clock={getattr(sim,'get_clock_hhmm',lambda:'00:00')()}, target minutes={sim.cfg.duration_minutes}")
    
    steps = 0
    while not getattr(sim, 'is_complete', lambda: True)():
        actions = getattr(sim, 'step_time', lambda *_: None)(1)
        print(f"Step {steps}: time={getattr(sim,'get_clock_hhmm',lambda:'00:00')()} actions={len(actions) if actions is not None else 0}")
        steps += 1
        if steps > cfg.duration_minutes + 10:  # Safety break
            print("ERROR: Too many steps, breaking to prevent infinite loop")
            break
    
    print(f"Simulation completed: final time={getattr(sim,'get_clock_hhmm',lambda:'00:00')()}, steps taken={steps}")
    return 0


def headless(argv=None) -> int:
    """Headless mode entry point."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration-minutes", type=int, default=4*12*60)
    parser.add_argument("--seed", type=int, default=1)
    args = parser.parse_args(argv)
    return run_headless(args.duration_minutes, args.seed)


def main(argv=None) -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--duration-minutes", type=int, default=4*12*60)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--windowed", action="store_true")
    args = parser.parse_args(argv)
    if args.headless:
        return run_headless(args.duration_minutes, args.seed)
    # Defer GUI import to avoid loading tkinter/pygame unless needed
    from cargosim.main import main as gui_main
    gui_main(force_windowed=args.windowed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
