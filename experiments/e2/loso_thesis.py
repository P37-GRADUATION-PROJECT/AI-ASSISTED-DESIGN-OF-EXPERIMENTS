"""E2 (preliminary): does warm start from the other species help? Leave-one-species-out.

For each species in the Çimyapan (2024) data, in turn:

- The "lab" is a quadratic response surface fitted to that species' own runs
  (inside its own tested box), plus Gaussian noise with the SD of its
  replicated centre runs. This simulated lab is only as good as the fit:
  S. limacinum's quadratic fit predicts poorly (LOO Q2 about 0.07), so its
  results are the least reliable.
- Cold BO: no prior data; round 1 is a Latin hypercube.
- Warm BO: the other two species' runs are given as related tasks (BayBE
  transfer learning); round 1 is already model-based.
- Both run 3 rounds of 4 runs (12 runs) over the same seeds, for two
  objectives: soluble protein (g/L) and yield (mg protein / g biomass).

Metric (same convention as E1): the TRUE value of the best OBSERVED run,
scored 0 = median random run, 1 = optimum of the simulated lab.

This is a small, preliminary check (2 factors, 3 species, simulated lab), not
the E2 result. Usage:

    python experiments/e2/loso_thesis.py --seeds 10 --out experiments/e2/results
"""

from __future__ import annotations

import argparse
import csv
import statistics
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from engine.bo import recommend  # noqa: E402
from engine.config import parse_config  # noqa: E402
from engine.rsm import fit_quadratic  # noqa: E402

DATA = ROOT / "data" / "public" / "cimyapan2024" / "extraction_runs.csv"
SPECIES = ["S_platensis", "A_protothecoides", "S_limacinum"]
BOXES = {  # the factorial box each species was tested in (thesis)
    "S_platensis": {"biomass": (10.0, 50.0), "time": (5.0, 20.0)},
    "A_protothecoides": {"biomass": (10.0, 50.0), "time": (15.0, 40.0)},
    "S_limacinum": {"biomass": (10.0, 50.0), "time": (15.0, 40.0)},
}
OBJECTIVES = {"protein_g_L": "soluble_protein", "yield_mg_g": "yield_mg_per_g"}
ROUNDS, BATCH = 3, 4


def load_rows() -> list[dict]:
    with DATA.open(encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r["use_in_model"] == "1"]
    out = []
    for r in rows:
        b, t, y = float(r["biomass_g_L"]), float(r["time_min"]), float(r["soluble_protein_g_L"])
        out.append(
            {
                "task": r["species"],
                "biomass": b,
                "time": t,
                "soluble_protein": y,
                "yield_mg_per_g": 1000 * y / b,
                "point_type": r["point_type"],
            }
        )
    return out


class SimulatedLab:
    """Quadratic fit to one species' runs + measurement noise from its centre replicates."""

    def __init__(self, rows: list[dict], species: str):
        sub = [r for r in rows if r["task"] == species]
        box = BOXES[species]
        self.bounds = [box["biomass"], box["time"]]
        x = np.array([[r["biomass"], r["time"]] for r in sub])
        y = np.array([r["soluble_protein"] for r in sub])
        self.model = fit_quadratic(x, y, ["biomass", "time"], self.bounds)
        centre = [r["soluble_protein"] for r in sub if r["point_type"] == "centre"]
        self.noise_sd = statistics.stdev(centre)
        # dense grid for optimum and random reference of each objective
        g = np.stack(
            np.meshgrid(np.linspace(*self.bounds[0], 201), np.linspace(*self.bounds[1], 201)), -1
        ).reshape(-1, 2)
        self.grid = g
        self.ref = {}
        rng = np.random.default_rng(0)
        u = np.column_stack([rng.uniform(lo, hi, 20000) for lo, hi in self.bounds])
        for name in OBJECTIVES.values():
            self.ref[name] = (
                float(self.true(g, name).max()),
                float(np.median(self.true(u, name))),
            )

    def true(self, x: np.ndarray, objective: str) -> np.ndarray:
        x = np.atleast_2d(x)
        protein = np.maximum(self.model.predict(x), 0.0)  # a concentration cannot be negative
        return protein if objective == "soluble_protein" else 1000 * protein / x[:, 0]

    def measure(self, x: np.ndarray, rng: np.random.Generator) -> np.ndarray:
        """Noisy protein measurement (g/L); yield is derived from it like in the lab."""
        return np.maximum(self.true(x, "soluble_protein") + rng.normal(0, self.noise_sd, len(x)), 0)

    def score(self, value: float, objective: str) -> float:
        best, med = self.ref[objective]
        return (value - med) / (best - med)


def make_cfg(species: str, objective: str, seed: int, warm: bool):
    box = BOXES[species]
    data = {
        "name": f"loso-{species}",
        "seed": seed,
        "factors": [
            {"name": "biomass", "low": box["biomass"][0], "high": box["biomass"][1], "decimals": 1},
            {"name": "time", "low": box["time"][0], "high": box["time"][1], "decimals": 1},
        ],
        "responses": [
            {"name": "soluble_protein", "unit": "g/L"},
            {
                "name": "yield_mg_per_g",
                "ratio_of": ["soluble_protein", "biomass"],
                "scale": 1000,
                "unit": "mg/g",
            },
        ],
        "optimizer": {"objective": "single", "target": objective, "batch_size": BATCH},
    }
    if warm:
        data["warm_start"] = {
            "source": str(DATA),
            "task_column": "species",
            "target_task": "target",
            "filters": {"use_in_model": "1"},
            "factors": {"biomass": "biomass_g_L", "time": "time_min"},
            "responses": {"soluble_protein": "soluble_protein_g_L"},
        }
    return parse_config(data)


def run_one(rows, lab, species, objective, seed, warm) -> list[float]:
    cfg = make_cfg(species, objective, seed, warm)
    prior = [r for r in rows if r["task"] != species] if warm else []
    rng = np.random.default_rng(10_000 + seed)
    history, scores = [], []
    for k in range(1, ROUNDS + 1):
        batch = recommend(cfg, history, round_no=k, prior=prior)
        x = np.array([[r["biomass"], r["time"]] for r in batch])
        protein = lab.measure(x, rng)
        for r, p in zip(batch, protein, strict=True):
            r["soluble_protein"] = float(p)
            r["yield_mg_per_g"] = 1000 * float(p) / r["biomass"]
            history.append(r)
            # best observed so far (by the noisy measurement), scored by its true value
            best = max(history, key=lambda h: h[objective])
            true_val = lab.true(np.array([[best["biomass"], best["time"]]]), objective)[0]
            scores.append(lab.score(float(true_val), objective))
    return scores


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--out", default=str(ROOT / "experiments" / "e2" / "results"))
    ap.add_argument("--species", nargs="*", default=SPECIES)
    args = ap.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    rows = load_rows()
    path = out / "loso_thesis_runs.csv"
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["species", "objective", "mode", "seed", "n_runs", "score"])
        for sp in args.species:
            lab = SimulatedLab(rows, sp)
            print(
                f"{sp}: lab fit R2 {lab.model.r2:.3f}, Q2 {lab.model.q2:.3f}, "
                f"noise SD {lab.noise_sd:.3f} g/L",
                flush=True,
            )
            for obj_label, obj in OBJECTIVES.items():
                for mode in ("cold", "warm"):
                    t0 = time.time()
                    for s in range(args.seeds):
                        for n, sc in enumerate(run_one(rows, lab, sp, obj, s, mode == "warm"), 1):
                            w.writerow([sp, obj_label, mode, s, n, f"{sc:.5f}"])
                    f.flush()
                    print(f"  {obj_label:<12}{mode:<5} done in {time.time() - t0:.0f}s", flush=True)
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
