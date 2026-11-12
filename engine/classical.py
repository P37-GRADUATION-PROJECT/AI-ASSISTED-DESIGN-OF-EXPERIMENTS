"""Classical response-surface designs (the baseline the lab normally uses).

Supported methods (all points stay inside the configured factor ranges):

- ``bbd``: Box-Behnken. Needs at least 3 factors. Points sit on the edge
  midpoints and the centre, never on the corners. 3 factors with 3 centre
  points = 15 runs; 4 factors = 27 runs.
- ``ccd_face``: face-centred central composite design (alpha = 1).
  2^k corners + 2k face centres + centre points. 3 factors -> 17 runs.
- ``ccd_inscribed``: rotatable CCD shrunk so the axial points sit on the
  range limits; corners move inside (e.g. +-0.595 for 3 factors).

The circumscribed CCD is deliberately not offered: its axial points fall
outside the ranges, which in the lab can mean an unsafe or impossible setting
(for example a temperature above the agreed limit).

Coded value -1 maps to the factor's ``low``, +1 to ``high``.
"""

from __future__ import annotations

import numpy as np
from pyDOE3 import bbdesign, ccdesign

from engine.interface import ExperimentSpec, ParameterKind, Run

METHODS = ("bbd", "ccd_face", "ccd_inscribed")


def coded_design(method: str, n_factors: int, center_points: int) -> np.ndarray:
    """Design matrix in coded units, standard order, shape (runs, n_factors)."""
    if center_points < 1:
        raise ValueError("center_points must be at least 1")
    if method == "bbd":
        if n_factors < 3:
            raise ValueError("Box-Behnken needs at least 3 factors; use a CCD for 2 factors")
        return np.asarray(bbdesign(n_factors, center=center_points), dtype=float)
    if method in ("ccd_face", "ccd_inscribed"):
        if n_factors < 2:
            raise ValueError("a central composite design needs at least 2 factors")
        face = "ccf" if method == "ccd_face" else "cci"
        # center=(points in factorial block, points in axial block); all go in one block here
        m = ccdesign(n_factors, center=(0, center_points), alpha="rotatable", face=face)
        return np.asarray(m, dtype=float)
    raise ValueError(f"unknown method {method!r}; choose one of {METHODS}")


def point_types(coded: np.ndarray) -> list[str]:
    """Label each row as 'centre', 'factorial' (all factors at +-level) or 'axial'/'edge'."""
    out = []
    for row in coded:
        nz = np.abs(row) > 1e-9
        if not nz.any():
            out.append("centre")
        elif nz.all():
            out.append("factorial")
        elif nz.sum() == 1:
            out.append("axial")
        else:
            out.append("edge")
    return out


def to_actual(coded: np.ndarray, bounds: list[tuple[float, float]]) -> np.ndarray:
    lo = np.array([b[0] for b in bounds], dtype=float)
    hi = np.array([b[1] for b in bounds], dtype=float)
    return (lo + hi) / 2 + coded * (hi - lo) / 2


def to_coded(actual: np.ndarray, bounds: list[tuple[float, float]]) -> np.ndarray:
    lo = np.array([b[0] for b in bounds], dtype=float)
    hi = np.array([b[1] for b in bounds], dtype=float)
    return (np.asarray(actual, dtype=float) - (lo + hi) / 2) / ((hi - lo) / 2)


def classical_design(
    spec: ExperimentSpec,
    method: str = "bbd",
    center_points: int = 3,
    randomize: bool = True,
    decimals: dict[str, int] | None = None,
    id_prefix: str | None = None,
) -> list[Run]:
    """Return the design as runs in the order the lab should perform them.

    Each run holds the factor values in actual units plus ``run_order``
    (1..n, the order to perform), ``std_order`` (row in the textbook design),
    ``run_id`` and ``point_type``. The run order is shuffled with
    ``spec.seed`` so time trends in the lab do not line up with a factor;
    the same seed always gives the same order.
    """
    for p in spec.parameters:
        if p.kind is not ParameterKind.CONTINUOUS:
            raise ValueError(f"{p.name}: classical designs here support continuous factors only")
    names = [p.name for p in spec.parameters]
    bounds = [p.bounds for p in spec.parameters]
    coded = coded_design(method, len(names), center_points)
    actual = to_actual(coded, bounds)
    types = point_types(coded)

    order = np.arange(len(coded))
    if randomize:
        order = np.random.default_rng(spec.seed).permutation(len(coded))

    prefix = id_prefix or method.upper().split("_")[0]
    decimals = decimals or {}
    runs: list[Run] = []
    for run_order, std_idx in enumerate(order, start=1):
        run: Run = {
            "run_order": run_order,
            "std_order": int(std_idx) + 1,
            "run_id": f"{prefix}-{run_order:02d}",
            "point_type": types[std_idx],
        }
        for j, name in enumerate(names):
            run[name] = round(float(actual[std_idx, j]), decimals.get(name, 6))
        runs.append(run)
    return runs
