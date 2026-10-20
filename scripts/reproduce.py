"""Single entry point for regenerating reported results.

Usage: python scripts/reproduce.py <experiment>
"""

import argparse
import sys

EXPERIMENTS: dict[str, str] = {}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("experiment", nargs="?", help="experiment id, e.g. e1")
    args = parser.parse_args(argv)
    if not args.experiment:
        print("Available experiments:", ", ".join(EXPERIMENTS) or "none yet")
        return 0
    if args.experiment not in EXPERIMENTS:
        print(f"Unknown experiment: {args.experiment}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
