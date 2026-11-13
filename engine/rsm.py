"""Second-order response-surface model: the analysis that follows a classical design.

y = b0 + sum b_i x_i + sum_{i<j} b_ij x_i x_j + sum b_ii x_i^2

Fitted by least squares on coded factors (-1 = low, +1 = high), the same way
Design-Expert reports a quadratic model. The fit gives the "predicted
optimum" that a lab would carry forward after a Box-Behnken or CCD; E1 and E3
count the runs needed to reach it.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

import numpy as np
from scipy.optimize import minimize

from engine.classical import to_actual, to_coded
from engine.interface import Goal


def term_names(factors: list[str]) -> list[str]:
    k = len(factors)
    names = ["intercept"] + list(factors)
    names += [f"{factors[i]}*{factors[j]}" for i, j in combinations(range(k), 2)]
    names += [f"{f}^2" for f in factors]
    return names


def model_matrix(coded: np.ndarray) -> np.ndarray:
    x = np.atleast_2d(np.asarray(coded, dtype=float))
    n, k = x.shape
    cols = [np.ones(n)] + [x[:, i] for i in range(k)]
    cols += [x[:, i] * x[:, j] for i, j in combinations(range(k), 2)]
    cols += [x[:, i] ** 2 for i in range(k)]
    return np.column_stack(cols)


@dataclass
class QuadraticModel:
    factors: list[str]
    bounds: list[tuple[float, float]]
    coef: np.ndarray
    n_obs: int
    r2: float
    adj_r2: float
    rmse: float
    q2: float  # leave-one-out predictive R^2 (from PRESS); nan if not computable

    @property
    def coefficients(self) -> dict[str, float]:
        """Coefficients on the coded scale, keyed by term name."""
        return dict(zip(term_names(self.factors), self.coef.tolist(), strict=True))

    def predict(self, actual: np.ndarray) -> np.ndarray:
        coded = to_coded(np.atleast_2d(actual), self.bounds)
        return model_matrix(coded) @ self.coef

    def optimum(self, goal: Goal = Goal.MAXIMIZE, n_starts: int = 32, seed: int = 0) -> dict:
        """Best predicted point inside the factor ranges (coded box [-1, 1]^k).

        Multi-start L-BFGS-B from the centre, every corner (up to 6 factors)
        and random points. A predicted optimum on a range limit is reported
        in ``on_limit``: the model is then extrapolating the trend and the
        real optimum may lie outside the tested region.
        """
        k = len(self.factors)
        sign = -1.0 if goal is Goal.MAXIMIZE else 1.0

        def f(z: np.ndarray) -> float:
            return float(sign * (model_matrix(z[None, :]) @ self.coef)[0])

        starts = [np.zeros(k)]
        if k <= 6:
            grid = np.array(np.meshgrid(*[[-1.0, 1.0]] * k)).reshape(k, -1).T
            starts += list(grid)
        rng = np.random.default_rng(seed)
        starts += list(rng.uniform(-1, 1, (n_starts, k)))
        best = None
        for s in starts:
            res = minimize(f, s, method="L-BFGS-B", bounds=[(-1.0, 1.0)] * k)
            if best is None or res.fun < best.fun:
                best = res
        z = np.clip(best.x, -1.0, 1.0)
        x = to_actual(z[None, :], self.bounds)[0]
        return {
            "factors": {n: float(v) for n, v in zip(self.factors, x, strict=True)},
            "coded": {n: float(v) for n, v in zip(self.factors, z, strict=True)},
            "predicted": float(sign * best.fun),
            "on_limit": [n for n, v in zip(self.factors, z, strict=True) if abs(abs(v) - 1) < 1e-4],
        }


def fit_quadratic(
    actual: np.ndarray, y: np.ndarray, factors: list[str], bounds: list[tuple[float, float]]
) -> QuadraticModel:
    """Least-squares fit of the full quadratic model.

    Raises ValueError if there are not more observations than model terms
    (no residual degrees of freedom), because R^2 would then be meaningless.
    """
    x = np.atleast_2d(np.asarray(actual, dtype=float))
    y = np.asarray(y, dtype=float).ravel()
    if x.shape[0] != y.size:
        raise ValueError("actual and y must have the same number of rows")
    if not np.all(np.isfinite(y)):
        raise ValueError("y contains missing or non-numeric values")
    xm = model_matrix(to_coded(x, bounds))
    n, p = xm.shape
    if n <= p:
        raise ValueError(f"need more runs ({n}) than model terms ({p}) to fit a quadratic model")
    if np.linalg.matrix_rank(xm) < p:
        raise ValueError("design cannot estimate all quadratic terms (rank deficient)")

    coef, *_ = np.linalg.lstsq(xm, y, rcond=None)
    resid = y - xm @ coef
    ss_res = float(resid @ resid)
    ss_tot = float(((y - y.mean()) ** 2).sum())
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    adj = 1 - (1 - r2) * (n - 1) / (n - p) if ss_tot > 0 else float("nan")
    rmse = float(np.sqrt(ss_res / (n - p)))

    # PRESS via the hat matrix: leave-one-out residual = e_i / (1 - h_ii)
    hat = xm @ np.linalg.pinv(xm.T @ xm) @ xm.T
    h = np.clip(np.diag(hat), 0, 1)
    if np.any(h > 1 - 1e-10) or ss_tot <= 0:
        q2 = float("nan")
    else:
        press = float(((resid / (1 - h)) ** 2).sum())
        q2 = 1 - press / ss_tot
    return QuadraticModel(list(factors), list(bounds), coef, n, r2, adj, rmse, q2)
