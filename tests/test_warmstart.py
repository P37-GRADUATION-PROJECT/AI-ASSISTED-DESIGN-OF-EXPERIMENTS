"""Warm start: config validation and loading need no BayBE; the BO tests do."""

import tomllib
from pathlib import Path

import pytest

from engine.config import load_config, parse_config
from engine.warmstart import load_prior, tasks

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "experiments" / "e3" / "case_study.example.toml"


def _data(**ws_overrides) -> dict:
    with EXAMPLE.open("rb") as f:
        d = tomllib.load(f)
    d["warm_start"]["enabled"] = True
    d["warm_start"].update(ws_overrides)
    return d


def test_example_ships_with_warm_start_off():
    # The thesis pH is unknown, so the example must not use a guessed value by default.
    assert load_config(EXAMPLE).warm_start is None


def test_prior_rows_use_config_names_and_skip_flagged_run():
    cfg = parse_config(_data())
    prior = load_prior(cfg)
    assert len(prior) == 38  # 39 thesis runs minus the suspect S. limacinum centre run
    assert tasks(prior) == ["S_platensis", "A_protothecoides", "S_limacinum"]
    first = prior[0]
    assert first["biomass"] == 30.0 and first["time"] == 12.3
    assert first["soluble_protein"] == 1.21
    assert first["ph"] == 7.0  # from [warm_start.fixed]
    assert first["yield_mg_per_g"] == pytest.approx(1000 * 1.21 / 30.0)  # derived like the lab data


def test_missing_factor_value_is_an_error_not_a_guess():
    d = _data()
    del d["warm_start"]["fixed"]
    with pytest.raises(ValueError, match="ph"):
        parse_config(d)


def test_unknown_or_double_mapped_factor_rejected():
    with pytest.raises(ValueError):
        parse_config(_data(fixed={"ph": 7.0, "temperature": 30.0}))
    with pytest.raises(ValueError):
        parse_config(_data(fixed={"ph": 7.0, "biomass": 20.0}))


def test_responses_must_map_every_measured_response():
    with pytest.raises(ValueError):
        parse_config(_data(responses={}))


def test_target_task_name_must_not_clash_with_a_source_task():
    cfg = parse_config(_data(target_task="S_platensis"))
    with pytest.raises(ValueError):
        load_prior(cfg)


def test_bad_source_column_reported():
    cfg = parse_config(_data(task_column="organism"))
    with pytest.raises(ValueError, match="organism"):
        load_prior(cfg)


# ---------------------------------------------------------------- with BayBE
def test_warm_first_round_is_model_based_with_predictions():
    pytest.importorskip("baybe")
    from engine.bo import recommend

    cfg = parse_config(_data())
    runs = recommend(cfg, [], round_no=1)
    assert len(runs) == 4
    assert all(r["point_type"] == "bo-warm" for r in runs)
    for r in runs:
        for p in cfg.spec.parameters:
            assert p.bounds[0] <= r[p.name] <= p.bounds[1]  # only the new ranges are proposed
        assert r["pred_soluble_protein_std"] > 0
        assert "task" not in r
    assert runs == recommend(cfg, [], round_no=1)


def test_warm_start_can_be_switched_off_per_call():
    pytest.importorskip("baybe")
    from engine.bo import recommend

    cfg = parse_config(_data())
    runs = recommend(cfg, [], round_no=1, prior=[])
    assert all(r["point_type"] == "bo-initial" for r in runs)


def test_lab_history_outside_ranges_is_still_rejected():
    pytest.importorskip("baybe")
    from engine.bo import recommend

    cfg = parse_config(_data())
    bad = {"run_id": "BO1-01", "biomass": 70.0, "time": 10.0, "ph": 8.0, "soluble_protein": 1.0}
    bad["yield_mg_per_g"] = 1000 / 70
    with pytest.raises(ValueError):
        recommend(cfg, [bad], round_no=2)
