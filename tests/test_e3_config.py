"""The E3 cowpea config loads and produces the lab sheet we expect."""

from pathlib import Path

from openpyxl import load_workbook

from engine.classical import classical_design
from engine.config import load_config
from engine.runsheet import write_run_sheet

CFG = Path(__file__).resolve().parents[1] / "experiments" / "e3" / "cowpea_v1.toml"


def test_cowpea_config_and_sheet(tmp_path):
    cfg = load_config(CFG)
    assert cfg.optimizer.target == "yield_mg_per_g"
    assert cfg.warm_start is None
    runs = classical_design(cfg.spec, "bbd", 3)
    assert len(runs) == 15
    path = write_run_sheet(cfg, runs, tmp_path / "bbd.xlsx", "bbd")
    keys = {c.value for c in load_workbook(path)["Run sheet"][2]}
    for k in (
        "soluble_protein__abs1",
        "soluble_protein__abs2",
        "soluble_protein__dilution",
        "bath_position",
        "ph_measured",
        "bath_temp_10min_C",
        "flour_g__applied",
    ):
        assert k in keys, k
