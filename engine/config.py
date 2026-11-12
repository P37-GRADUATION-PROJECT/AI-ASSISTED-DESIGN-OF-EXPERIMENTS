"""Load an experiment definition from a TOML file.

The case-study factors are not final yet, so everything the lab may change
(factors, ranges, units, rounding, responses, design settings) lives in a
config file, not in code. See `experiments/e3/case_study.example.toml`.

Format::

    name = "..."
    seed = 2026

    [design]
    method = "bbd"            # bbd | ccd_face | ccd_inscribed
    center_points = 3

    [[factors]]
    name = "biomass"          # column name used everywhere
    label = "Biomass concentration"
    unit = "g/L"
    low = 10
    high = 50
    decimals = 1              # rounding of the values written to the run sheet

    [[responses]]
    name = "soluble_protein"
    unit = "g/L"
    goal = "max"              # max | min

    [run_sheet]
    record = ["bath_temp_start_C", "bath_temp_end_C"]   # extra columns to fill in

Standard library only (tomllib).
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from engine.interface import ExperimentSpec, Goal, Objective, Parameter, ParameterKind

DESIGN_METHODS = ("bbd", "ccd_face", "ccd_inscribed")
RESERVED_COLUMNS = frozenset({"run_order", "std_order", "run_id", "point_type", "notes"})


@dataclass(frozen=True)
class FactorInfo:
    name: str
    label: str
    unit: str
    decimals: int


@dataclass(frozen=True)
class ResponseInfo:
    name: str
    unit: str
    goal: Goal


@dataclass(frozen=True)
class DesignSettings:
    method: str = "bbd"
    center_points: int = 3

    def __post_init__(self) -> None:
        if self.method not in DESIGN_METHODS:
            raise ValueError(f"design.method must be one of {DESIGN_METHODS}, got {self.method!r}")
        if self.center_points < 1:
            raise ValueError("design.center_points must be at least 1 (needed to estimate noise)")


@dataclass(frozen=True)
class ExperimentConfig:
    name: str
    spec: ExperimentSpec
    factors: tuple[FactorInfo, ...]
    responses: tuple[ResponseInfo, ...]
    design: DesignSettings
    record_columns: tuple[str, ...] = field(default_factory=tuple)

    def factor(self, name: str) -> FactorInfo:
        for f in self.factors:
            if f.name == name:
                return f
        raise KeyError(name)


def _require(table: dict, key: str, where: str):
    if key not in table:
        raise ValueError(f"{where}: missing required key {key!r}")
    return table[key]


def parse_config(data: dict) -> ExperimentConfig:
    """Build an ExperimentConfig from an already parsed TOML dict."""
    name = str(_require(data, "name", "config"))
    seed = int(data.get("seed", 0))

    raw_factors = _require(data, "factors", "config")
    if not raw_factors:
        raise ValueError("config: at least one factor is required")
    params: list[Parameter] = []
    infos: list[FactorInfo] = []
    for i, f in enumerate(raw_factors):
        where = f"factors[{i}]"
        fname = str(_require(f, "name", where))
        if fname in RESERVED_COLUMNS:
            raise ValueError(f"{where}: {fname!r} is a reserved column name")
        low, high = float(_require(f, "low", where)), float(_require(f, "high", where))
        params.append(Parameter(fname, ParameterKind.CONTINUOUS, bounds=(low, high)))
        infos.append(
            FactorInfo(
                name=fname,
                label=str(f.get("label", fname)),
                unit=str(f.get("unit", "")),
                decimals=int(f.get("decimals", 2)),
            )
        )

    raw_resp = _require(data, "responses", "config")
    if not raw_resp:
        raise ValueError("config: at least one response is required")
    responses = tuple(
        ResponseInfo(
            name=str(_require(r, "name", f"responses[{i}]")),
            unit=str(r.get("unit", "")),
            goal=Goal(str(r.get("goal", "max"))),
        )
        for i, r in enumerate(raw_resp)
    )

    names = [p.name for p in params] + [r.name for r in responses]
    if len(names) != len(set(names)):
        raise ValueError("config: factor and response names must all be different")

    record = tuple(str(c) for c in data.get("run_sheet", {}).get("record", []))
    clash = set(record) & (set(names) | RESERVED_COLUMNS)
    if clash:
        raise ValueError(f"run_sheet.record: column names already used: {sorted(clash)}")

    d = data.get("design", {})
    design = DesignSettings(
        method=str(d.get("method", "bbd")), center_points=int(d.get("center_points", 3))
    )

    # The first response is the primary objective; the others are recorded and
    # can be optimized jointly later (multi-objective BO).
    spec = ExperimentSpec(
        parameters=tuple(params),
        objective=Objective(responses[0].name, responses[0].goal),
        seed=seed,
    )
    return ExperimentConfig(name, spec, tuple(infos), responses, design, record)


def load_config(path: str | Path) -> ExperimentConfig:
    with Path(path).open("rb") as f:
        return parse_config(tomllib.load(f))
