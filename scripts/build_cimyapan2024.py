"""Build the clean dataset of the Çimyapan (2024) extraction experiments.

Source: Ş. Çimyapan, MSc thesis, Gebze Technical University, 2024 (advisor:
Assoc. Prof. Dr. Müge İşleten Hoşoğlu). Tables 3.1-3.3, thesis pages 29, 31
and 33: ultrasound-assisted extraction of soluble protein from three
microalgal biomasses, 13 runs each, two factors (biomass concentration, time).

The values below are transcribed exactly as printed (decimal commas converted
to points). Nothing is corrected in place. Problems found in the tables are
recorded in the `flags` column and in the provenance JSON, so every later
decision (e.g. leaving a run out of a model) is explicit and reversible.

Outputs (written next to each other):
    data/public/cimyapan2024/extraction_runs.csv
    data/public/cimyapan2024/extraction_runs.json   (provenance + summary)

Usage: python scripts/build_cimyapan2024.py
Standard library only, so it also runs in CI.
"""

from __future__ import annotations

import csv
import hashlib
import json
import statistics
import sys
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parents[1] / "data" / "public" / "cimyapan2024"

SOURCE = {
    "citation": (
        "Çimyapan, Ş. (2024). MSc thesis, Institute of Biotechnology, Gebze Technical "
        "University. Advisor: Assoc. Prof. Dr. Müge İşleten Hoşoğlu."
    ),
    "tables": "Table 3.1 (p. 29), Table 3.2 (p. 31), Table 3.3 (p. 33)",
    "received": "2026-10-21, from the GTU Institute of Biotechnology (via B. Altıparmak)",
    "transcribed_by": "Emre Kaan Şahin, 2026-11-12; checked against the rendered PDF pages",
}

METHOD = {
    "extraction": (
        "Probe-type ultrasonic homogenizer (Bandelin HD 2070), 9 x 10% cycle, 45-55% power; "
        "biomass dispersed in deionized water; centrifuged 10,000 rpm, 40 min"
    ),
    "response": "Total soluble protein in the supernatant (g/L), Lowry method, BSA standard",
    "design_stated_in_thesis": "Box-Behnken, 13 runs per species, Design-Expert 13.0.0",
    "design_actual": (
        "Two-factor central composite design (4 factorial + 4 axial + 5 centre runs). "
        "Box-Behnken needs at least 3 factors, so the label in the thesis is not correct."
    ),
    "not_reported": "pH and temperature during extraction; protein content of the biomasses",
}

# species key -> (full name, table id, centre time in min)
SPECIES = {
    "S_platensis": ("Spirulina (Arthrospira) platensis", "3.1"),
    "A_protothecoides": ("Auxenochlorella protothecoides", "3.2"),
    "S_limacinum": ("Schizochytrium limacinum", "3.3"),
}

# (run, biomass g/L, biomass coded as printed, time min, time coded as printed, protein g/L)
TABLES: dict[str, list[tuple[int, float, int, float, int, float]]] = {
    "S_platensis": [
        (1, 30.0, 0, 12.30, 0, 1.210),
        (2, 30.0, 0, 12.30, 0, 0.923),
        (3, 1.72, -1, 12.30, 0, 0.101),
        (4, 30.0, 0, 12.30, 0, 0.976),
        (5, 30.0, 0, 12.30, 0, 0.944),
        (6, 30.0, 0, 12.30, 0, 0.955),
        (7, 58.28, 1, 12.30, 0, 1.773),
        (8, 50.0, 1, 20.00, 1, 2.050),
        (9, 30.0, 0, 23.11, 1, 1.422),
        (10, 50.0, 1, 5.00, -1, 1.493),
        (11, 10.0, -1, 20.00, 1, 0.700),
        (12, 30.0, 0, 2.29, -1, 0.838),
        (13, 10.0, -1, 2.00, -1, 0.374),
    ],
    "A_protothecoides": [
        (1, 30.0, 0, 27.50, 0, 0.613),
        (2, 30.0, 0, 27.50, 0, 0.666),
        (3, 1.72, -1, 27.50, 0, 0.0001),
        (4, 30.0, 0, 10.22, -1, 0.647),
        (5, 50.0, 1, 40.00, 1, 1.008),
        (6, 30.0, 0, 27.50, 0, 0.663),
        (7, 30.0, 0, 27.50, 0, 0.723),
        (8, 58.28, 1, 27.50, 0, 1.116),
        (9, 50.0, 1, 15.00, -1, 0.978),
        (10, 30.0, 0, 48.18, 1, 0.640),
        (11, 10.0, -1, 40.00, 1, 0.185),
        (12, 10.0, -1, 15.00, -1, 0.168),
        (13, 30.0, 0, 27.50, 0, 0.564),
    ],
    "S_limacinum": [
        (1, 30.0, 0, 27.50, 0, 1.099),
        (2, 30.0, 0, 27.50, 0, 1.114),
        (3, 1.72, -1, 27.50, 0, 0.033),
        (4, 30.0, 0, 10.22, -1, 1.008),
        (5, 50.0, 1, 40.00, 1, 1.610),
        (6, 30.0, 0, 27.50, 0, 1.133),
        (7, 30.0, 0, 27.50, 0, 1.119),
        (8, 58.28, 1, 27.50, 0, 1.752),
        (9, 50.0, 1, 15.00, -1, 0.523),
        (10, 30.0, 0, 48.18, 1, 1.246),
        (11, 10.0, -1, 40.00, 1, 0.485),
        (12, 10.0, -1, 15.00, -1, 0.447),
        (13, 30.0, 0, 27.50, 0, 0.108),
    ],
}

# Factorial levels used to compute consistent coded values (+-1 = factorial,
# +-1.414 = axial). For S. platensis the time levels are ambiguous (both 2 and
# 5 min are printed as -1); 5-20 min is used because the axial value 23.11 min
# equals 12.5 + 1.414 * 7.5 exactly.
FACTORIAL = {
    "S_platensis": {"biomass": (10.0, 50.0), "time": (5.0, 20.0)},
    "A_protothecoides": {"biomass": (10.0, 50.0), "time": (15.0, 40.0)},
    "S_limacinum": {"biomass": (10.0, 50.0), "time": (15.0, 40.0)},
}

# Run-level flags (species, run) -> list of flag codes. Codes are explained in FLAG_TEXT.
RUN_FLAGS: dict[tuple[str, int], list[str]] = {
    ("S_limacinum", 13): ["suspect_value"],
    ("A_protothecoides", 3): ["near_zero"],
    ("S_platensis", 12): ["time_level_mismatch"],
    ("S_platensis", 13): ["time_level_mismatch"],
}
for _run in (1, 2, 3, 4, 5, 6, 7):
    RUN_FLAGS.setdefault(("S_platensis", _run), []).append("centre_time_typo")
for _sp in ("A_protothecoides", "S_limacinum"):
    for _run in (4, 10):
        RUN_FLAGS.setdefault((_sp, _run), []).append("axial_time_asymmetric")

FLAG_TEXT = {
    "suspect_value": (
        "Centre run reads 0.108 g/L while the other four centre runs read 1.099-1.133 g/L. "
        "Probably a transcription error (e.g. 1.108). Excluded from models by default "
        "(use_in_model = 0) until the raw file confirms the value."
    ),
    "near_zero": (
        "0.0001 g/L at 1.72 g/L biomass; likely below the Lowry quantification limit. "
        "Kept, but treat as 'about zero', not as an exact value."
    ),
    "time_level_mismatch": (
        "Low time level printed as 5 min for run 10 but 2 min for run 13 (both coded -1); "
        "the axial point 2.29 min does not match 12.5 - 1.414 * 7.5 = 1.89 min. "
        "Actual values are used as printed."
    ),
    "centre_time_typo": (
        "Centre time printed as 12.30 min; the midpoint of 5-20 min is 12.50 min. "
        "Value kept as printed (difference is negligible for modelling)."
    ),
    "axial_time_asymmetric": (
        "Axial times 10.22 and 48.18 min are not symmetric around 27.5 min "
        "(a rotatable CCD would give 9.82 and 45.18 min). Values kept as printed."
    ),
    "coded_labels": (
        "All tables print axial points as -1/+1; in a CCD they are -1.414/+1.414. "
        "The columns *_coded are recomputed from the actual values."
    ),
}

COLUMNS = [
    "species",
    "species_name",
    "source_table",
    "run",
    "biomass_g_L",
    "time_min",
    "soluble_protein_g_L",
    "yield_mg_per_g",
    "biomass_coded",
    "time_coded",
    "biomass_coded_printed",
    "time_coded_printed",
    "point_type",
    "use_in_model",
    "flags",
]


def _coded(x: float, levels: tuple[float, float]) -> float:
    lo, hi = levels
    return round((x - (lo + hi) / 2) / ((hi - lo) / 2), 3)


def _point_type(bc: float, tc: float) -> str:
    if abs(bc) < 0.2 and abs(tc) < 0.2:
        return "centre"
    if abs(abs(bc) - 1) < 0.05 and abs(abs(tc) - 1) < 0.05:
        return "factorial"
    return "axial"


def build_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for sp, (name, table) in SPECIES.items():
        lv = FACTORIAL[sp]
        for run, b, b_pr, t, t_pr, y in TABLES[sp]:
            bc, tc = _coded(b, lv["biomass"]), _coded(t, lv["time"])
            flags = RUN_FLAGS.get((sp, run), [])
            rows.append(
                {
                    "species": sp,
                    "species_name": name,
                    "source_table": table,
                    "run": run,
                    "biomass_g_L": b,
                    "time_min": t,
                    "soluble_protein_g_L": y,
                    # g/L protein divided by g/L biomass = g/g; x1000 = mg protein per g biomass
                    "yield_mg_per_g": round(1000 * y / b, 2),
                    "biomass_coded": bc,
                    "time_coded": tc,
                    "biomass_coded_printed": b_pr,
                    "time_coded_printed": t_pr,
                    "point_type": _point_type(bc, tc),
                    "use_in_model": 0 if "suspect_value" in flags else 1,
                    "flags": ";".join(flags),
                }
            )
    return rows


def summarize(rows: list[dict[str, object]]) -> dict[str, object]:
    out: dict[str, object] = {}
    for sp in SPECIES:
        sub = [r for r in rows if r["species"] == sp]
        centre = [
            float(r["soluble_protein_g_L"])
            for r in sub
            if r["point_type"] == "centre" and r["use_in_model"] == 1
        ]
        best_conc = max(sub, key=lambda r: float(r["soluble_protein_g_L"]))
        best_yield = max(
            (r for r in sub if r["use_in_model"] == 1), key=lambda r: float(r["yield_mg_per_g"])
        )
        mean = statistics.mean(centre)
        sd = statistics.stdev(centre)
        out[sp] = {
            "n_runs": len(sub),
            "n_used": sum(int(r["use_in_model"]) for r in sub),
            "centre_replicates_used": len(centre),
            "centre_mean_g_L": round(mean, 4),
            "centre_sd_g_L": round(sd, 4),
            "centre_cv_pct": round(100 * sd / mean, 1),
            "best_concentration": {
                k: best_conc[k]
                for k in ("run", "biomass_g_L", "time_min", "soluble_protein_g_L", "yield_mg_per_g")
            },
            "best_yield": {
                k: best_yield[k]
                for k in ("run", "biomass_g_L", "time_min", "soluble_protein_g_L", "yield_mg_per_g")
            },
        }
    return out


def main() -> int:
    rows = build_rows()
    if len(rows) != 39:
        print(f"expected 39 runs, got {len(rows)}", file=sys.stderr)
        return 1
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = OUT_DIR / "extraction_runs.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)

    meta = {
        "source": SOURCE,
        "method": METHOD,
        "columns": {
            "yield_mg_per_g": "1000 * soluble_protein_g_L / biomass_g_L (derived, not in thesis)",
            "biomass_coded/time_coded": (
                "recomputed from actual values; +-1 factorial, +-1.414 axial"
            ),
            "use_in_model": "0 = excluded by default (see flags); 1 = used",
        },
        "factorial_levels": FACTORIAL,
        "flags": FLAG_TEXT,
        "summary": summarize(rows),
        "csv_sha256": hashlib.sha256(csv_path.read_bytes()).hexdigest(),
    }
    json_path = OUT_DIR / "extraction_runs.json"
    json_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {csv_path} ({len(rows)} rows) and {json_path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
