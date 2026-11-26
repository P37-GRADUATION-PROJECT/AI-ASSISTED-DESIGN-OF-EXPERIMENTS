"""E1 test problems: noisy functions on [0, 1]^d whose true optimum is known.

Every problem is maximized. The "lab" returns ``f(x) + noise``; the score
always uses the noise-free ``f``. Noise is set relative to how much there is
to gain: ``sd = noise * (f_opt - f_median)``, where ``f_median`` is the value
of a typical random run. With ``noise = 0.1`` a single measurement scatters by
a tenth of the gap between a random run and the optimum.

Problems:

- ``hartmann3``: the standard 3-factor Hartmann function (four bumps, one
  global optimum near a corner of the box). A quadratic model cannot follow
  it, so it is hard for the classical response-surface approach.
- ``peak3`` / ``peak4``: a single broad, smooth optimum off the centre of the
  box with interacting factors (a rotated Gaussian bump). Over the box it is
  close to a quadratic, the shape a response-surface study expects: this is the
  classical design's home ground (without noise its predicted optimum scores
  about 0.98).
- ``peak3_narrow``: the same bump, 1.8 times narrower. The optimum region is
  small compared with the ranges, as when the ranges were chosen too wide, and
  a quadratic over the whole box no longer fits well.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

_H3_ALPHA = np.array([1.0, 1.2, 3.0, 3.2])
_H3_A = np.array([[3.0, 10, 30], [0.1, 10, 35], [3.0, 10, 30], [0.1, 10, 35]])
_H3_P = 1e-4 * np.array(
    [[3689, 1170, 2673], [4699, 4387, 7470], [1091, 8732, 5547], [381, 5743, 8828]]
)
# Known global optimum (e.g. Surjanovic & Bingham, Virtual Library of Simulation Experiments).
H3_XOPT = np.array([0.114614, 0.555649, 0.852547])
H3_FOPT = 3.86278


def hartmann3(x: np.ndarray) -> np.ndarray:
    x = np.atleast_2d(x)
    inner = ((x[:, None, :] - _H3_P[None]) ** 2 * _H3_A[None]).sum(axis=2)
    return (_H3_ALPHA * np.exp(-inner)).sum(axis=1)


def _peak(centre, sd, corr):
    centre = np.asarray(centre, dtype=float)
    d = np.diag(sd)
    prec = np.linalg.inv(d @ np.asarray(corr, dtype=float) @ d)

    def f(x: np.ndarray) -> np.ndarray:
        z = np.atleast_2d(x) - centre
        return np.exp(-0.5 * np.einsum("ni,ij,nj->n", z, prec, z))

    return f


PEAK3_C = (0.72, 0.35, 0.62)
_PEAK3_SD = np.array([0.25, 0.40, 0.30])
_PEAK3_CORR = [[1, 0.5, 0], [0.5, 1, -0.3], [0, -0.3, 1]]
peak3 = _peak(PEAK3_C, 1.8 * _PEAK3_SD, _PEAK3_CORR)
peak3_narrow = _peak(PEAK3_C, _PEAK3_SD, _PEAK3_CORR)
PEAK4_C = (0.65, 0.30, 0.70, 0.45)
peak4 = _peak(
    PEAK4_C,
    1.8 * np.array([0.30, 0.35, 0.25, 0.40]),
    [[1, 0.4, 0, 0], [0.4, 1, 0, -0.3], [0, 0, 1, 0.3], [0, -0.3, 0.3, 1]],
)


@dataclass
class Problem:
    name: str
    dim: int
    f: object
    x_opt: np.ndarray
    f_opt: float
    f_median: float = field(init=False)

    def __post_init__(self) -> None:
        # Median of a typical random run: the score's zero (same convention as E2).
        u = np.random.default_rng(0).uniform(size=(20000, self.dim))
        self.f_median = float(np.median(self.f(u)))

    def true(self, x: np.ndarray) -> np.ndarray:
        return self.f(np.clip(np.atleast_2d(x), 0.0, 1.0))

    def noise_sd(self, noise: float) -> float:
        return noise * (self.f_opt - self.f_median)

    def measure(self, x: np.ndarray, noise: float, rng: np.random.Generator) -> np.ndarray:
        x = np.atleast_2d(x)
        return self.true(x) + rng.normal(0.0, self.noise_sd(noise), len(x))

    def score(self, true_value: float) -> float:
        """0 = median random run, 1 = the optimum."""
        return (true_value - self.f_median) / (self.f_opt - self.f_median)


PROBLEMS = {
    "hartmann3": Problem("hartmann3", 3, hartmann3, H3_XOPT, H3_FOPT),
    "peak3": Problem("peak3", 3, peak3, np.array(PEAK3_C), 1.0),
    "peak3_narrow": Problem("peak3_narrow", 3, peak3_narrow, np.array(PEAK3_C), 1.0),
    "peak4": Problem("peak4", 4, peak4, np.array(PEAK4_C), 1.0),
}
