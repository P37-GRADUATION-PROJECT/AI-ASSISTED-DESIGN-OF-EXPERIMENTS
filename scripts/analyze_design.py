"""Fit the quadratic response-surface model to a filled-in run sheet.

Usage:
    python scripts/analyze_design.py experiments/e3/case_study.example.toml runsheet.xlsx
    python scripts/analyze_design.py CONFIG SHEET --response soluble_protein

Reports pending runs and data problems first, then the coefficients (coded
scale), R^2, adjusted R^2, Q^2 (leave-one-out), RMSE, the noise estimate from
the replicated centre runs, and the predicted optimum inside the ranges.
"""

from __future__ import annotations

import argparse
import statistics
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine.config import load_config  # noqa: E402
from engine.rsm import fit_quadratic  # noqa: E402
from engine.runsheet import read_results  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("config")
    ap.add_argument("sheet")
    ap.add_argument("--response", help="response to model (default: the first in the config)")
    args = ap.parse_args(argv)

    cfg = load_config(args.config)
    resp = next(
        (r for r in cfg.responses if r.name == (args.response or cfg.responses[0].name)), None
    )
    if resp is None:
        print(f"unknown response {args.response!r}", file=sys.stderr)
        return 1

    res = read_results(cfg, args.sheet)
    for p in res.problems:
        print(f"CHECK: {p}")
    if res.pending:
        print(f"pending (not measured yet): {', '.join(res.pending)}")
    print(f"measured runs: {len(res.measured)}\n")

    names = [f.name for f in cfg.factors]
    bounds = [p.bounds for p in cfg.spec.parameters]
    x = np.array([[r[n] for n in names] for r in res.measured], dtype=float)
    y = np.array([r[resp.name] for r in res.measured], dtype=float)
    try:
        model = fit_quadratic(x, y, names, bounds)
    except ValueError as e:
        print(f"cannot fit the quadratic model yet: {e}")
        return 1

    print(f"Quadratic model for {resp.name} ({resp.unit}), coded factors")
    for term, b in model.coefficients.items():
        print(f"  {term:<24}{b:>12.5f}")
    print(f"\n  R2 {model.r2:.3f}   adj R2 {model.adj_r2:.3f}   Q2 (LOO) {model.q2:.3f}")
    print(f"  RMSE {model.rmse:.4f} {resp.unit}  (n = {model.n_obs})")

    centre = [r[resp.name] for r in res.measured if r["point_type"] == "centre"]
    if len(centre) >= 2:
        sd = statistics.stdev(centre)
        print(f"  centre replicates: n = {len(centre)}, SD {sd:.4f} {resp.unit} (lab noise)")

    opt = model.optimum(resp.goal, seed=cfg.spec.seed)
    where = ", ".join(f"{n} = {v:.3g}" for n, v in opt["factors"].items())
    print(f"\nPredicted {resp.goal.value} {resp.name}: {opt['predicted']:.4f} at {where}")
    if opt["on_limit"]:
        print(f"  on a range limit: {', '.join(opt['on_limit'])} (the model extrapolates a trend)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
