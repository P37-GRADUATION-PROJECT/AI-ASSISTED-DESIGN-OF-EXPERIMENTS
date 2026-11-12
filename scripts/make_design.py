"""Generate a classical design from a config file and write the lab run sheet.

Usage:
    python scripts/make_design.py experiments/e3/case_study.example.toml -o runsheet.xlsx

Prints the design to the terminal as well. The method and the number of
centre points come from the config; --method / --center-points override them.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine.classical import classical_design  # noqa: E402
from engine.config import load_config  # noqa: E402
from engine.runsheet import write_run_sheet  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("config")
    ap.add_argument("-o", "--output", required=True, help="path of the .xlsx run sheet")
    ap.add_argument("--method", help="override design.method")
    ap.add_argument("--center-points", type=int, help="override design.center_points")
    args = ap.parse_args(argv)

    cfg = load_config(args.config)
    method = args.method or cfg.design.method
    cp = args.center_points or cfg.design.center_points
    runs = classical_design(
        cfg.spec,
        method=method,
        center_points=cp,
        decimals={f.name: f.decimals for f in cfg.factors},
    )
    path = write_run_sheet(cfg, runs, args.output, method)

    names = [f.name for f in cfg.factors]
    print(f"{cfg.name}\n{method}, {len(runs)} runs, seed {cfg.spec.seed}\n")
    print("  ".join(f"{h:>10}" for h in ["run_id", "std", "type", *names]))
    for r in runs:
        vals = [r["run_id"], r["std_order"], r["point_type"], *[r[n] for n in names]]
        print("  ".join(f"{v!s:>10}" for v in vals))
    print(f"\nwrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
