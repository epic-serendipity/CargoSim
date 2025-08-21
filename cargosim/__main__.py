"""Command-line entry point for CargoSim."""

import argparse
import sys
from .main import main as gui_main, load_config, LogisticsSim


def run_headless(periods: int, seed: int) -> int:
    """Run the simulation in headless mode."""
    print(f"Starting headless simulation: periods={periods}, seed={seed}")
    cfg = load_config()
    cfg.periods = periods
    cfg.seed = seed
    print(f"Config loaded: periods={cfg.periods}, seed={cfg.seed}")
    
    sim = LogisticsSim(cfg)
    print(f"Simulation created: initial period={sim.t}, target periods={sim.cfg.periods}")
    
    step_count = 0
    while sim.t < sim.cfg.periods:
        print(f"Step {step_count}: period={sim.t}, target={sim.cfg.periods}")
        actions = sim.step_period()
        print(f"  Actions: {len(actions)}")
        step_count += 1
        if step_count > 100:  # Safety break
            print("ERROR: Too many steps, breaking to prevent infinite loop")
            break
    
    print(f"Simulation completed: final period={sim.t}, steps taken={step_count}")
    return 0


def headless(argv=None) -> int:
    """Headless mode entry point."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--periods", type=int, default=4)
    parser.add_argument("--seed", type=int, default=1)
    args = parser.parse_args(argv)
    return run_headless(args.periods, args.seed)


def main(argv=None) -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--periods", type=int, default=4)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--windowed", action="store_true")
    args = parser.parse_args(argv)
    if args.headless:
        return run_headless(args.periods, args.seed)
    gui_main(force_windowed=args.windowed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
