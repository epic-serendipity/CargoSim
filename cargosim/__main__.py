import argparse
import sys
from cargo_sim import main as gui_main, load_config, LogisticsSim


def run_headless(periods: int, seed: int) -> int:
    cfg = load_config()
    cfg.periods = periods
    cfg.seed = seed
    sim = LogisticsSim(cfg)
    while sim.t < sim.cfg.periods:
        sim.step_period()
    return 0


def headless(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--periods", type=int, default=4)
    parser.add_argument("--seed", type=int, default=1)
    args = parser.parse_args(argv)
    return run_headless(args.periods, args.seed)


def main(argv=None) -> int:
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
