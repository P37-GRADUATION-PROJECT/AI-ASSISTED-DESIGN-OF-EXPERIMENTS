"""Checks for the transcribed Çimyapan (2024) dataset (standard library only)."""

import csv
import hashlib
import json
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data" / "public" / "cimyapan2024"


def _rows() -> list[dict[str, str]]:
    with (DATA / "extraction_runs.csv").open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_shape_and_species():
    rows = _rows()
    assert len(rows) == 39
    for sp in ("S_platensis", "A_protothecoides", "S_limacinum"):
        runs = sorted(int(r["run"]) for r in rows if r["species"] == sp)
        assert runs == list(range(1, 14))


def test_yield_is_recomputable():
    for r in _rows():
        expected = 1000 * float(r["soluble_protein_g_L"]) / float(r["biomass_g_L"])
        assert abs(float(r["yield_mg_per_g"]) - expected) < 0.01


def test_design_structure_is_ccd():
    for sp in ("S_platensis", "A_protothecoides", "S_limacinum"):
        types = [r["point_type"] for r in _rows() if r["species"] == sp]
        assert types.count("centre") == 5
        assert types.count("axial") + types.count("factorial") == 8


def test_suspect_run_excluded_and_documented():
    rows = _rows()
    excluded = [(r["species"], r["run"]) for r in rows if r["use_in_model"] == "0"]
    assert excluded == [("S_limacinum", "13")]
    meta = json.loads((DATA / "extraction_runs.json").read_text(encoding="utf-8"))
    for r in rows:
        for flag in filter(None, r["flags"].split(";")):
            assert flag in meta["flags"]


def test_checksum_matches_csv():
    meta = json.loads((DATA / "extraction_runs.json").read_text(encoding="utf-8"))
    digest = hashlib.sha256((DATA / "extraction_runs.csv").read_bytes()).hexdigest()
    assert meta["csv_sha256"] == digest
