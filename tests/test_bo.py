"""Tests for the BO campaign. Skipped when BayBE is not installed (CI installs only
requirements-dev.txt); run them locally after `pip install -r requirements-engine.txt`."""

from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("baybe")

from engine.bo import check_history_is_fair, recommend  # noqa: E402
from engine.config import load_config, parse_config  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "experiments" / "e3" / "case_study.example.toml"


def _lab(run: dict) -> float:
    """Hidden 'true' protein response (g/L) for the tests; optimum inside the box."""
    b, t, ph = run["biomass"], run["time"], run["ph"]
    return 0.03 * b + 0.08 * t - 0.003 * t**2 + 0.2 * ph - 0.012 * ph**2


def _measure(cfg, runs):
    out = []
    for r in runs:
        m = dict(r)
        m["soluble_protein"] = _lab(r)
        m["yield_mg_per_g"] = 1000 * m["soluble_protein"] / r["biomass"]
        out.append(m)
    return out


def test_first_round_without_history_is_inside_bounds_and_reproducible():
    cfg = load_config(EXAMPLE)
    a = recommend(cfg, [], round_no=1)
    b = recommend(cfg, [], round_no=1)
    assert len(a) == cfg.optimizer.batch_size == 4
    assert a == b
    for r in a:
        for p in cfg.spec.parameters:
            assert p.bounds[0] <= r[p.name] <= p.bounds[1]
        assert r["run_id"].startswith("BO1-")
        assert not any(k.startswith("pred_") for k in r)  # no model yet, no prediction


def test_values_are_rounded_to_lab_precision():
    cfg = load_config(EXAMPLE)
    for r in recommend(cfg, [], round_no=1):
        for f in cfg.factors:
            assert r[f.name] == round(r[f.name], f.decimals)


def test_later_round_has_predictions_and_is_reproducible():
    cfg = load_config(EXAMPLE)
    hist = _measure(cfg, recommend(cfg, [], round_no=1))
    hist += _measure(cfg, recommend(cfg, hist, round_no=2))
    a = recommend(cfg, hist, round_no=3)
    assert a == recommend(cfg, hist, round_no=3)
    assert a != recommend(cfg, hist, round_no=4)  # different round -> different seed
    for r in a:
        assert np.isfinite(r["pred_soluble_protein_mean"])
        assert r["pred_soluble_protein_std"] > 0


def test_closed_loop_improves_on_the_random_start():
    cfg = load_config(EXAMPLE)
    hist = _measure(cfg, recommend(cfg, [], round_no=1))
    start_best = max(r["soluble_protein"] for r in hist)
    for k in range(2, 5):
        hist += _measure(cfg, recommend(cfg, hist, round_no=k))
    assert max(r["soluble_protein"] for r in hist) > start_best


def test_desirability_objective_predicts_both_responses():
    cfg = load_config(EXAMPLE)
    data = {
        "name": "t",
        "seed": 5,
        "factors": [
            {"name": f.name, "low": p.bounds[0], "high": p.bounds[1], "decimals": f.decimals}
            for f, p in zip(cfg.factors, cfg.spec.parameters, strict=True)
        ],
        "responses": [
            {"name": "soluble_protein", "low": 0, "high": 2.5},
            {
                "name": "yield_mg_per_g",
                "ratio_of": ["soluble_protein", "biomass"],
                "scale": 1000,
                "low": 0,
                "high": 80,
            },
        ],
        "optimizer": {"objective": "desirability", "batch_size": 3},
    }
    dcfg = parse_config(data)
    hist = _measure(dcfg, recommend(dcfg, [], round_no=1))
    runs = recommend(dcfg, hist, round_no=2)
    assert len(runs) == 3
    for r in runs:
        assert "pred_soluble_protein_mean" in r and "pred_yield_mg_per_g_mean" in r


def test_desirability_requires_expected_ranges():
    with pytest.raises(ValueError):
        parse_config(
            {
                "name": "t",
                "factors": [{"name": "x", "low": 0, "high": 1}],
                "responses": [{"name": "y"}],
                "optimizer": {"objective": "desirability"},
            }
        )


def test_classical_runs_in_history_are_detected():
    hist = [{"run_id": "BBD-03"}, {"run_id": "BO1-01"}, {"run_id": "CCD-10"}]
    assert check_history_is_fair(hist) == ["BBD-03", "CCD-10"]
    assert check_history_is_fair([{"run_id": "BO2-01"}]) == []


def test_initial_batch_is_a_latin_hypercube():
    from engine.bo import initial_design

    cfg = load_config(EXAMPLE)
    x = initial_design(cfg, 4, seed=11)
    for j, p in enumerate(cfg.spec.parameters):
        lo, hi = p.bounds
        strata = np.floor((x[:, j] - lo) / (hi - lo) * 4).astype(int)
        assert sorted(strata) == [0, 1, 2, 3]  # one run in each quarter of every range


def test_script_writes_unique_log_columns_and_refuses_classical_history(tmp_path):
    import csv
    import sys

    sys.path.insert(0, str(ROOT))
    from openpyxl import load_workbook

    from scripts import make_design, recommend_batch

    sheet = tmp_path / "bo1.xlsx"
    assert recommend_batch.main([str(EXAMPLE), "--round", "1", "-o", str(sheet)]) == 0
    with (tmp_path / "bo1_predictions.csv").open() as f:
        header = next(csv.reader(f))
    assert len(header) == len(set(header))

    bbd = tmp_path / "bbd.xlsx"
    make_design.main([str(EXAMPLE), "-o", str(bbd)])
    wb = load_workbook(bbd)
    ws = wb["Run sheet"]
    col = [c.value for c in ws[2]].index("soluble_protein") + 1
    for i in range(3, ws.max_row + 1):
        ws.cell(row=i, column=col, value=1.0)
    wb.save(bbd)
    args = [str(EXAMPLE), "--round", "2", "--history", str(bbd), "-o", str(tmp_path / "x.xlsx")]
    assert recommend_batch.main(args) == 2


def test_applied_value_slightly_outside_range_is_kept():
    # The lab ran one condition at 21 min (range 5-20): a real deviation, not an error.
    cfg = load_config(EXAMPLE)
    hist = _measure(cfg, recommend(cfg, [], round_no=1))
    hist[0]["time"] = 21.0
    hist[0]["soluble_protein"] = _lab(hist[0])
    runs = recommend(cfg, hist, round_no=2)
    assert len(runs) == cfg.optimizer.batch_size
    for r in runs:  # recommendations themselves stay inside the ranges
        for p in cfg.spec.parameters:
            assert p.bounds[0] <= r[p.name] <= p.bounds[1]


def test_value_far_outside_range_is_refused_with_run_id():
    cfg = load_config(EXAMPLE)
    hist = _measure(cfg, recommend(cfg, [], round_no=1))
    hist[2]["biomass"] = 70.0  # typo for 7.0 or 40.0; range is 10-50
    with pytest.raises(ValueError, match=r"BO1-03: biomass = 70"):
        recommend(cfg, hist, round_no=2)


def test_script_refuses_far_out_applied_value_without_traceback(tmp_path, capsys):
    import sys

    sys.path.insert(0, str(ROOT))
    from openpyxl import load_workbook

    from scripts import recommend_batch

    sheet = tmp_path / "bo1.xlsx"
    assert recommend_batch.main([str(EXAMPLE), "--round", "1", "-o", str(sheet)]) == 0
    wb = load_workbook(sheet)
    ws = wb["Run sheet"]
    keys = [c.value for c in ws[2]]
    for i in range(3, ws.max_row + 1):
        ws.cell(row=i, column=keys.index("soluble_protein") + 1, value=1.0)
    ws.cell(row=3, column=keys.index("time__applied") + 1, value=21.0)  # kept
    args = [str(EXAMPLE), "--round", "2", "--history", str(sheet), "-o", str(tmp_path / "b2.xlsx")]
    wb.save(sheet)
    assert recommend_batch.main(args) == 0

    ws.cell(row=4, column=keys.index("biomass__applied") + 1, value=70.0)  # refused
    wb.save(sheet)
    assert recommend_batch.main(args) == 2
    assert "biomass = 70 is too far outside" in capsys.readouterr().err
