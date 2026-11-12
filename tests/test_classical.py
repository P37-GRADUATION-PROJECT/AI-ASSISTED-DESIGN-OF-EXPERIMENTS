import itertools
from pathlib import Path

import numpy as np
import pytest
from openpyxl import load_workbook

from engine.classical import classical_design, coded_design, to_coded
from engine.config import load_config, parse_config
from engine.interface import ExperimentSpec, Goal, Objective, Parameter, ParameterKind
from engine.rsm import fit_quadratic, model_matrix
from engine.runsheet import read_results, write_run_sheet

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "experiments" / "e3" / "case_study.example.toml"
BOUNDS = [(10.0, 50.0), (5.0, 20.0), (7.0, 11.0)]
NAMES = ["biomass", "time", "ph"]


def _spec(seed: int = 1) -> ExperimentSpec:
    params = tuple(
        Parameter(n, ParameterKind.CONTINUOUS, bounds=b) for n, b in zip(NAMES, BOUNDS, strict=True)
    )
    return ExperimentSpec(parameters=params, objective=Objective("y"), seed=seed)


# ---------------------------------------------------------------- designs
def test_bbd_three_factors_is_the_textbook_design():
    d = coded_design("bbd", 3, center_points=3)
    assert d.shape == (15, 3)
    edges = {
        tuple(row)
        for i, j in itertools.combinations(range(3), 2)
        for a, b in itertools.product([-1.0, 1.0], repeat=2)
        for row in [np.where(np.arange(3) == i, a, np.where(np.arange(3) == j, b, 0.0))]
    }
    got = [tuple(r) for r in d]
    assert set(got) - {(0.0, 0.0, 0.0)} == edges
    assert got.count((0.0, 0.0, 0.0)) == 3
    assert not any(np.all(np.abs(r) == 1) for r in d)  # Box-Behnken has no corner runs


def test_bbd_four_factors_has_27_runs():
    assert coded_design("bbd", 4, center_points=3).shape == (27, 4)


def test_bbd_needs_three_factors():
    with pytest.raises(ValueError):
        coded_design("bbd", 2, center_points=3)


@pytest.mark.parametrize("method,n", [("ccd_face", 17), ("ccd_inscribed", 17)])
def test_ccd_sizes_and_all_points_inside_ranges(method, n):
    d = coded_design(method, 3, center_points=3)
    assert d.shape == (n, 3)
    assert np.all(np.abs(d) <= 1 + 1e-9)


def test_unknown_or_circumscribed_method_rejected():
    with pytest.raises(ValueError):
        coded_design("ccd_circumscribed", 3, center_points=3)


def test_actual_values_within_bounds_and_order_reproducible():
    runs = classical_design(_spec(seed=7), "bbd", center_points=3)
    for r in runs:
        for n, (lo, hi) in zip(NAMES, BOUNDS, strict=True):
            assert lo <= r[n] <= hi
    assert [r["run_order"] for r in runs] == list(range(1, 16))
    assert sorted(r["std_order"] for r in runs) == list(range(1, 16))
    again = classical_design(_spec(seed=7), "bbd", center_points=3)
    other = classical_design(_spec(seed=8), "bbd", center_points=3)
    assert runs == again
    assert [r["std_order"] for r in runs] != [r["std_order"] for r in other]


def test_unrandomized_order_is_standard_order():
    runs = classical_design(_spec(), "bbd", center_points=3, randomize=False)
    assert [r["std_order"] for r in runs] == list(range(1, 16))
    assert runs[0]["biomass"] == 10.0 and runs[0]["time"] == 5.0 and runs[0]["ph"] == 9.0


# ---------------------------------------------------------------- quadratic model
TRUE = np.array([2.0, 0.5, -0.3, 0.2, 0.1, 0.0, -0.05, -0.4, -0.6, -0.2])


def _truth(actual: np.ndarray) -> np.ndarray:
    return model_matrix(to_coded(actual, BOUNDS)) @ TRUE


def test_quadratic_recovers_known_coefficients_on_bbd():
    runs = classical_design(_spec(), "bbd", center_points=3)
    x = np.array([[r[n] for n in NAMES] for r in runs])
    m = fit_quadratic(x, _truth(x), NAMES, BOUNDS)
    assert np.allclose(m.coef, TRUE, atol=1e-9)
    assert m.r2 == pytest.approx(1.0)


def test_predicted_optimum_matches_analytic_stationary_point():
    runs = classical_design(_spec(), "ccd_face", center_points=3)
    x = np.array([[r[n] for n in NAMES] for r in runs])
    m = fit_quadratic(x, _truth(x), NAMES, BOUNDS)
    b = TRUE[1:4]
    bmat = np.array(
        [
            [2 * TRUE[7], TRUE[4], TRUE[5]],
            [TRUE[4], 2 * TRUE[8], TRUE[6]],
            [TRUE[5], TRUE[6], 2 * TRUE[9]],
        ]
    )
    z_star = np.linalg.solve(bmat, -b)  # stationary point (a maximum: bmat is negative definite)
    assert np.all(np.abs(z_star) < 1)
    opt = m.optimum(Goal.MAXIMIZE)
    assert np.allclose(list(opt["coded"].values()), z_star, atol=1e-4)
    assert opt["on_limit"] == []


def test_optimum_on_limit_is_reported():
    coef = np.zeros(10)
    coef[1] = 1.0  # response rises linearly with biomass -> optimum at the upper limit
    runs = classical_design(_spec(), "bbd", center_points=3)
    x = np.array([[r[n] for n in NAMES] for r in runs])
    y = model_matrix(to_coded(x, BOUNDS)) @ coef
    opt = fit_quadratic(x, y + 1e-6 * np.arange(len(y)), NAMES, BOUNDS).optimum()
    assert "biomass" in opt["on_limit"]
    assert opt["factors"]["biomass"] == pytest.approx(50.0)


def test_too_few_runs_rejected():
    x = np.random.default_rng(0).uniform(0, 1, (8, 3))
    with pytest.raises(ValueError):
        fit_quadratic(x, np.ones(8), NAMES, [(0, 1)] * 3)


# ---------------------------------------------------------------- config + run sheet
def test_example_config_loads():
    cfg = load_config(EXAMPLE)
    assert [f.name for f in cfg.factors] == NAMES
    assert cfg.design.method == "bbd"
    assert cfg.spec.objective.name == "soluble_protein"


def test_config_rejects_reserved_and_duplicate_names():
    base = {"name": "t", "responses": [{"name": "y"}]}
    with pytest.raises(ValueError):
        parse_config({**base, "factors": [{"name": "notes", "low": 0, "high": 1}]})
    with pytest.raises(ValueError):
        parse_config({**base, "factors": [{"name": "y", "low": 0, "high": 1}]})


def test_run_sheet_roundtrip(tmp_path):
    cfg = load_config(EXAMPLE)
    runs = classical_design(cfg.spec, "bbd", 3, decimals={f.name: f.decimals for f in cfg.factors})
    path = write_run_sheet(cfg, runs, tmp_path / "sheet.xlsx", "bbd")

    wb = load_workbook(path)
    ws = wb["Run sheet"]
    keys = [c.value for c in ws[2]]
    resp, ph_applied, notes = (
        keys.index(k) + 1 for k in ("soluble_protein", "ph__applied", "notes")
    )
    ws.cell(row=3, column=resp, value=1.25)
    ws.cell(row=4, column=resp, value="0,98")  # decimal comma as typed in Turkish Excel
    ws.cell(row=4, column=ph_applied, value=9.4)
    ws.cell(row=4, column=notes, value="pH drifted")
    ws.cell(row=5, column=resp, value="n/a")
    wb.save(path)

    res = read_results(cfg, path)
    assert [r["run_id"] for r in res.measured] == ["BBD-01", "BBD-02"]
    assert res.measured[0]["soluble_protein"] == 1.25
    assert res.measured[1]["soluble_protein"] == pytest.approx(0.98)
    assert res.measured[1]["ph"] == 9.4  # applied value replaces the planned one
    assert res.measured[1]["notes"] == "pH drifted"
    assert res.measured[0]["ph"] == runs[0]["ph"]
    assert "BBD-03" in res.pending and len(res.pending) == 13
    assert any("BBD-03" in p for p in res.problems)
