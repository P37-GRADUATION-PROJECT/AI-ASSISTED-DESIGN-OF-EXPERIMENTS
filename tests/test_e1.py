"""E1 benchmark harness: test problems, scoring and strategies."""

import numpy as np
import pytest

from experiments.e1 import benchmark
from experiments.e1.problems import H3_FOPT, PROBLEMS


def test_hartmann3_known_optimum():
    p = PROBLEMS["hartmann3"]
    assert p.true(p.x_opt)[0] == pytest.approx(H3_FOPT, abs=1e-4)
    u = np.random.default_rng(1).uniform(size=(50_000, 3))
    assert p.true(u).max() <= H3_FOPT + 1e-9


@pytest.mark.parametrize("name", ["peak3", "peak3_narrow", "peak4"])
def test_peak_optimum_is_the_centre(name):
    p = PROBLEMS[name]
    assert p.true(p.x_opt)[0] == pytest.approx(1.0)
    u = np.random.default_rng(2).uniform(size=(50_000, p.dim))
    assert p.true(u).max() < 1.0


@pytest.mark.parametrize("name", list(PROBLEMS))
def test_score_scale(name):
    p = PROBLEMS[name]
    assert p.score(p.f_opt) == pytest.approx(1.0)
    assert p.score(p.f_median) == pytest.approx(0.0)
    assert p.noise_sd(0.1) == pytest.approx(0.1 * (p.f_opt - p.f_median))


def test_classical_on_its_home_ground_finds_the_optimum_without_noise():
    # Broad smooth peak, no noise: the quadratic model's optimum must be near the true one.
    res = benchmark.run_classical(PROBLEMS["peak3"], 0.0, seed=0, method="bbd")
    runs, score = res["bbd"]
    assert runs == 15 + 1  # 3-factor Box-Behnken with 3 centre points, plus a confirmation run
    assert score > 0.95
    assert res["bbd_best_run"][0] == 15


def test_classical_counts_runs_for_four_factors():
    res = benchmark.run_classical(PROBLEMS["peak4"], 0.1, seed=0, method="bbd")
    assert res["bbd"][0] == 27 + 1


def test_random_is_reproducible_and_scores_true_values():
    p = PROBLEMS["peak3"]
    a = benchmark.run_random(p, 0.1, seed=3)
    assert a == benchmark.run_random(p, 0.1, seed=3)
    assert len(a) == benchmark.BUDGET[3]
    assert all(s <= 1.0 + 1e-9 for s in a)


def test_noise_streams_differ_by_strategy_but_not_by_call():
    r1 = benchmark._rng("peak3", 0.1, 0, "bo").normal()
    r2 = benchmark._rng("peak3", 0.1, 0, "bo").normal()
    r3 = benchmark._rng("peak3", 0.1, 0, "random").normal()
    assert r1 == r2 and r1 != r3


def test_bo_curves_have_one_value_per_batch_and_per_run(monkeypatch):
    pytest.importorskip("baybe")
    monkeypatch.setitem(benchmark.BUDGET, 3, 8)
    incumbent, best_run = benchmark.run_bo(PROBLEMS["peak3"], 0.1, seed=0)
    assert len(incumbent) == 8 // benchmark.BATCH
    assert len(best_run) == 8
    assert all(-1.0 < s <= 1.0 + 1e-9 for s in incumbent + best_run)
