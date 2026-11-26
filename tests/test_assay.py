"""Lowry assay: absorbances -> protein, quality flags, config and run-sheet integration."""

import pytest
from openpyxl import load_workbook

from engine.assay import AssaySettings, lowry, parse_assay
from engine.classical import classical_design
from engine.config import parse_config
from engine.runsheet import read_results, write_run_sheet

# Calibration line of the institute's Lowry instruction (LBF3, BSA standards 0-0.20 mg/mL).
CAL = AssaySettings(method="lowry", slope=4.6113, intercept=0.0583, dilution=10)


def _lab_excel(a1: float, a2: float, dilution: float) -> float:
    # The formula in the lab's own sheet: ((AVERAGE(B:C) - 0.0583) / 4.6113) * E
    return ((a1 + a2) / 2 - 0.0583) / 4.6113 * dilution


def test_matches_the_lab_spreadsheet_formula():
    for a1, a2 in [(0.50, 0.52), (0.30, 0.31), (0.85, 0.80)]:
        res = lowry([a1, a2], 10, CAL)
        assert res.value == pytest.approx(_lab_excel(a1, a2, 10), rel=1e-12)
        assert res.mean_absorbance == pytest.approx((a1 + a2) / 2)
        assert res.flags == ()


def test_dilution_scales_the_result():
    assert lowry([0.4], 20, CAL).value == pytest.approx(2 * lowry([0.4], 10, CAL).value)


def test_flags():
    low = lowry([0.08, 0.09], 10, CAL)
    assert any("below" in f for f in low.flags)
    high = lowry([1.10, 1.12], 10, CAL)
    assert any("above" in f for f in high.flags)
    spread = lowry([0.30, 0.40], 10, CAL)  # 29 % of the mean
    assert any("differ" in f for f in spread.flags)
    neg = lowry([0.02, 0.03], 10, CAL)
    assert any("negative" in f for f in neg.flags)


def test_bad_input_rejected():
    with pytest.raises(ValueError):
        lowry([], 10, CAL)
    with pytest.raises(ValueError):
        lowry([0.4], 0.5, CAL)


def test_parse_assay_validation():
    ok = parse_assay("p", {"method": "lowry", "slope": 4.6, "intercept": 0.05})
    assert ok.dilution == 1.0 and ok.replicates == 2
    with pytest.raises(ValueError, match="slope"):
        parse_assay("p", {"method": "lowry", "intercept": 0.05})
    with pytest.raises(ValueError, match="unknown"):
        parse_assay("p", {"method": "lowry", "slope": 4.6, "intercept": 0.05, "slop": 1})
    with pytest.raises(ValueError):
        parse_assay("p", {"method": "bradford", "slope": 4.6, "intercept": 0.05})
    with pytest.raises(ValueError):
        parse_assay("p", {"method": "lowry", "slope": -1, "intercept": 0.05})


def _cfg(**assay) -> dict:
    return {
        "name": "assay test",
        "seed": 3,
        "factors": [
            {"name": "flour_g", "low": 0.1, "high": 0.5, "decimals": 3},
            {"name": "time", "low": 10, "high": 60, "decimals": 0},
            {"name": "ph", "low": 7, "high": 10, "decimals": 1},
        ],
        "responses": [
            {"name": "soluble_protein", "unit": "g/L"},
            # mg protein per g flour, 10 mL extraction volume: 1000 * protein * 0.010 / flour_g
            {"name": "yield_mg_per_g", "ratio_of": ["soluble_protein", "flour_g"], "scale": 10},
        ],
        "assay": {
            "soluble_protein": {
                "method": "lowry",
                "slope": 4.6113,
                "intercept": 0.0583,
                "dilution": 10,
                **assay,
            }
        },
    }


def test_config_assay_only_on_measured_responses():
    cfg = parse_config(_cfg())
    assert cfg.assays["soluble_protein"].slope == 4.6113
    bad = _cfg()
    bad["assay"]["yield_mg_per_g"] = bad["assay"]["soluble_protein"]
    with pytest.raises(ValueError, match="measured"):
        parse_config(bad)


def test_run_sheet_with_absorbances(tmp_path):
    cfg = parse_config(_cfg())
    runs = classical_design(cfg.spec, "bbd", 3)
    path = write_run_sheet(cfg, runs, tmp_path / "sheet.xlsx", "bbd")

    wb = load_workbook(path)
    ws = wb["Run sheet"]
    keys = [c.value for c in ws[2]]
    assert "soluble_protein" not in keys  # the lab types readings, not g/L
    a1, a2, dil = (
        keys.index(k) + 1
        for k in (
            "soluble_protein__abs1",
            "soluble_protein__abs2",
            "soluble_protein__dilution",
        )
    )
    assert ws.cell(row=3, column=dil).value == 10  # default dilution pre-filled
    ws.cell(row=3, column=a1, value=0.61)
    ws.cell(row=3, column=a2, value="0,63")  # decimal comma
    ws.cell(row=4, column=a1, value=0.30)
    ws.cell(row=4, column=a2, value=0.31)
    ws.cell(row=4, column=dil, value=5)  # less diluted for a weak sample
    ws.cell(row=5, column=a1, value=0.12)  # second reading missing -> still pending
    ws.cell(row=6, column=a1, value=0.07)
    ws.cell(row=6, column=a2, value=0.08)  # below the calibration range -> flagged
    ws.cell(row=7, column=a1, value=0.50)
    ws.cell(row=7, column=a2, value=0.50)
    ws.cell(row=7, column=dil).value = None  # emptied -> default, flagged
    wb.save(path)

    res = read_results(cfg, path)
    by_id = {r["run_id"]: r for r in res.measured}
    assert sorted(by_id) == ["BBD-01", "BBD-02", "BBD-04", "BBD-05"]
    assert by_id["BBD-01"]["soluble_protein"] == pytest.approx(_lab_excel(0.61, 0.63, 10))
    assert by_id["BBD-02"]["soluble_protein"] == pytest.approx(_lab_excel(0.30, 0.31, 5))
    first = by_id["BBD-01"]
    assert first["yield_mg_per_g"] == pytest.approx(
        10 * first["soluble_protein"] / first["flour_g"]
    )
    assert "BBD-03" in res.pending
    assert any(p.startswith("BBD-04") and "below" in p for p in res.problems)
    assert any(p.startswith("BBD-05") and "default" in p for p in res.problems)
    assert not any(p.startswith("BBD-01") for p in res.problems)


def test_without_assay_the_sheet_is_unchanged(tmp_path):
    d = _cfg()
    del d["assay"]
    cfg = parse_config(d)
    path = write_run_sheet(cfg, classical_design(cfg.spec, "bbd", 3), tmp_path / "s.xlsx", "bbd")
    keys = [c.value for c in load_workbook(path)["Run sheet"][2]]
    assert "soluble_protein" in keys
    assert not any("__abs" in str(k) for k in keys)
