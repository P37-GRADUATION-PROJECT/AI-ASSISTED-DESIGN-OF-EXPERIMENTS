"""Smoke test for the engine dependencies (BayBE, BoTorch, PyTorch, pyDOE3).

Usage: python scripts/check_engine.py
"""

import time

import numpy as np
import pandas as pd
from baybe import Campaign, Settings
from baybe.objectives import SingleTargetObjective
from baybe.parameters import NumericalContinuousParameter
from baybe.searchspace import SearchSpace
from baybe.targets import NumericalTarget
from pyDOE3 import lhs

SEED = 42


def toy_yield(df: pd.DataFrame) -> np.ndarray:
    # Known optimum at temperature=32, ph=6.8
    return 100 - (df["temperature"] - 32) ** 2 - 20 * (df["ph"] - 6.8) ** 2


def main() -> None:
    Settings(random_seed=SEED).activate()
    parameters = [
        NumericalContinuousParameter("temperature", bounds=(25, 40)),
        NumericalContinuousParameter("ph", bounds=(6, 8)),
    ]
    campaign = Campaign(
        searchspace=SearchSpace.from_product(parameters),
        objective=SingleTargetObjective(NumericalTarget("yield")),
    )

    # Start from a small classical design (Latin hypercube via pyDOE3)
    unit = lhs(2, samples=4, seed=SEED)
    start = pd.DataFrame({"temperature": 25 + 15 * unit[:, 0], "ph": 6 + 2 * unit[:, 1]})
    start["yield"] = toy_yield(start)
    campaign.add_measurements(start)

    t0 = time.perf_counter()
    for i in range(1, 4):
        batch = campaign.recommend(batch_size=2)
        batch["yield"] = toy_yield(batch)
        campaign.add_measurements(batch)
        print(f"round {i}: best yield so far = {campaign.measurements['yield'].max():.2f}")
    print(f"OK: engine stack works ({time.perf_counter() - t0:.1f}s for 3 BO rounds)")


if __name__ == "__main__":
    main()
