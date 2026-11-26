"""E1: simulated benchmark, classical response-surface DoE vs Bayesian optimization.

For every problem, noise level and seed:

- ``random``: uniform random runs (sanity baseline).
- ``bo``: the engine's BO campaign (``engine.bo.recommend``), batches of 4;
  round 1 is a maximin Latin hypercube, later rounds are model-based.
- ``bbd`` / ``ccd_face``: the engine's classical design (3 centre points),
  measured once, then the quadratic model (``engine.rsm``) and its predicted
  optimum. The lab would run that optimum once to confirm it, so the classical
  result counts design runs + 1.

What is scored (always the TRUE, noise-free value; 0 = median random run,
1 = optimum):

- ``bo``: after each batch, the run the model believes is best (highest
  posterior mean among the runs done so far). Like the classical model, this
  averages out the noise of a single measurement. Scored at batch ends only
  (4, 8, ... runs), because the lab acts on whole batches.
- ``bo_best_run`` and ``random``: after each run, the run with the highest
  *measured* value. A lucky noisy measurement can pick a worse point.
- classical: the quadratic model's predicted optimum (``<method>``), and for
  reference the best measured run of the design (``<method>_best_run``).

Usage (about 30 min per noise level on 2 CPU cores):

    python experiments/e1/benchmark.py --seeds 20 --noise 0.1 0.3 --out experiments/e1/results
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from engine.classical import classical_design  # noqa: E402
from engine.config import parse_config  # noqa: E402
from engine.rsm import fit_quadratic  # noqa: E402
from experiments.e1.problems import PROBLEMS  # noqa: E402

BATCH = 4
BUDGET = {3: 32, 4: 40}  # sequential runs for random and BO, per number of factors
CENTRE_POINTS = 3
METHODS = ("bbd", "ccd_face")
FIELDS = ["problem", "noise", "strategy", "seed", "n_runs", "score"]


def make_cfg(dim: int, seed: int):
    return parse_config(
        {
            "name": f"e1-{dim}d",
            "seed": seed,
            "factors": [
                {"name": f"x{i}", "low": 0.0, "high": 1.0, "decimals": 3} for i in range(1, dim + 1)
            ],
            "responses": [{"name": "y"}],
            "optimizer": {"objective": "single", "target": "y", "batch_size": BATCH},
        }
    )


def _rng(problem: str, noise: float, seed: int, strategy: str) -> np.random.Generator:
    # Separate, reproducible noise stream per (problem, noise, seed, strategy).
    key = [sum(map(ord, problem)), int(round(noise * 1000)), seed, sum(map(ord, strategy))]
    return np.random.default_rng(key)


def _curve(problem, xs: np.ndarray, ys: np.ndarray) -> list[float]:
    """Score of the best-measured run after each run."""
    out, best = [], 0
    for i in range(len(ys)):
        if ys[i] > ys[best]:
            best = i
        out.append(problem.score(float(problem.true(xs[best])[0])))
    return out


def run_random(problem, noise: float, seed: int) -> list[float]:
    n = BUDGET[problem.dim]
    rng = _rng(problem.name, noise, seed, "random")
    xs = rng.uniform(size=(n, problem.dim))
    ys = problem.measure(xs, noise, rng)
    return _curve(problem, xs, ys)


def run_bo(problem, noise: float, seed: int) -> tuple[list[float], list[float]]:
    """(score of the model's best run after each batch, best-measured curve per run)."""
    import pandas as pd

    from engine.bo import build_campaign, recommend

    cfg = make_cfg(problem.dim, seed)
    names = [p.name for p in cfg.spec.parameters]
    rng = _rng(problem.name, noise, seed, "bo")
    history, incumbent = [], []
    for k in range(1, BUDGET[problem.dim] // BATCH + 1):
        batch = recommend(cfg, history, round_no=k, prior=[])
        x = np.array([[r[c] for c in names] for r in batch])
        for r, y in zip(batch, problem.measure(x, noise, rng), strict=True):
            r["y"] = float(y)
            history.append(r)
        xs = np.array([[r[c] for c in names] for r in history])
        stats = build_campaign(cfg, history, prior=[]).posterior_stats(
            pd.DataFrame(xs, columns=names)
        )
        best = int(np.argmax(stats["y_mean"].to_numpy()))
        incumbent.append(problem.score(float(problem.true(xs[best])[0])))
    ys = np.array([r["y"] for r in history])
    return incumbent, _curve(problem, xs, ys)


def run_classical(problem, noise: float, seed: int, method: str) -> dict[str, tuple[int, float]]:
    """{strategy: (runs used, score)} for the model's optimum and the best design run."""
    cfg = make_cfg(problem.dim, seed)
    names = [p.name for p in cfg.spec.parameters]
    bounds = [p.bounds for p in cfg.spec.parameters]
    runs = classical_design(cfg.spec, method, center_points=CENTRE_POINTS, randomize=False)
    x = np.array([[r[c] for c in names] for r in runs])
    y = problem.measure(x, noise, _rng(problem.name, noise, seed, method))
    model = fit_quadratic(x, y, names, bounds)
    opt = model.optimum()
    x_opt = np.array([opt["factors"][c] for c in names])
    best_run = x[int(np.argmax(y))]
    return {
        method: (len(x) + 1, problem.score(float(problem.true(x_opt)[0]))),
        f"{method}_best_run": (len(x), problem.score(float(problem.true(best_run)[0]))),
    }


def task(args: tuple[str, float, int]) -> list[list]:
    """All strategies for one (problem, noise, seed): CSV rows."""
    name, noise, seed = args
    problem = PROBLEMS[name]
    rows = []
    for n, s in enumerate(run_random(problem, noise, seed), start=1):
        rows.append([name, noise, "random", seed, n, round(s, 5)])
    incumbent, best_run = run_bo(problem, noise, seed)
    for k, s in enumerate(incumbent, start=1):
        rows.append([name, noise, "bo", seed, k * BATCH, round(s, 5)])
    for n, s in enumerate(best_run, start=1):
        rows.append([name, noise, "bo_best_run", seed, n, round(s, 5)])
    for method in METHODS:
        for strategy, (n, s) in run_classical(problem, noise, seed, method).items():
            rows.append([name, noise, strategy, seed, n, round(s, 5)])
    return rows


def _init_worker() -> None:
    # Two processes on two cores: keep each to one thread so they do not fight.
    import torch

    torch.set_num_threads(1)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=20)
    ap.add_argument("--noise", type=float, nargs="+", default=[0.1])
    ap.add_argument("--problems", nargs="+", default=list(PROBLEMS))
    ap.add_argument("--workers", type=int, default=min(2, os.cpu_count() or 1))
    ap.add_argument("--out", default=str(ROOT / "experiments" / "e1" / "results"))
    args = ap.parse_args(argv)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    path = out / "e1_runs.csv"
    done = set()
    if path.exists():  # resume: skip (problem, noise, seed) already written
        with path.open() as f:
            done = {(r["problem"], float(r["noise"]), int(r["seed"])) for r in csv.DictReader(f)}
    todo = [
        (p, nz, s)
        for nz in args.noise
        for p in args.problems
        for s in range(args.seeds)
        if (p, nz, s) not in done
    ]
    print(f"{len(todo)} tasks ({len(done)} already done)", flush=True)
    new = not path.exists()
    t0 = time.time()
    with path.open("a", newline="") as f, Pool(args.workers, initializer=_init_worker) as pool:
        w = csv.writer(f)
        if new:
            w.writerow(FIELDS)
        for i, rows in enumerate(pool.imap_unordered(task, todo), start=1):
            w.writerows(rows)
            f.flush()
            p, nz, s = rows[0][:2] + [rows[0][3]]
            print(f"[{i}/{len(todo)}] {p} noise={nz} seed={s}  {time.time() - t0:.0f}s", flush=True)
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
