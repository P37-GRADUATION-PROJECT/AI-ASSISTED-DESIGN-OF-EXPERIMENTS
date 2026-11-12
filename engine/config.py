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
    """A response. Measured in the lab, or derived as scale * numerator / denominator.

    `low`/`high` are only needed for the desirability objective: they map the
    response onto 0-1 (worst to best expected value).
    """

    name: str
    unit: str
    goal: Goal
    ratio_of: tuple[str, str] | None = None  # (numerator, denominator) column names
    scale: float = 1.0
    low: float | None = None
    high: float | None = None
    weight: float = 1.0

    @property
    def derived(self) -> bool:
        return self.ratio_of is not None


OBJECTIVES = ("single", "desirability")


@dataclass(frozen=True)
class OptimizerSettings:
    objective: str = "single"  # single | desirability
    target: str | None = None  # response optimized in "single" mode (default: first)
    batch_size: int = 4

    def __post_init__(self) -> None:
        if self.objective not in OBJECTIVES:
            raise ValueError(f"optimizer.objective must be one of {OBJECTIVES}")
        if self.batch_size < 1:
            raise ValueError("optimizer.batch_size must be at least 1")


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
    optimizer: OptimizerSettings = field(default_factory=OptimizerSettings)

    @property
    def measured_responses(self) -> tuple[ResponseInfo, ...]:
        """Responses the lab writes on the run sheet (not derived ones)."""
        return tuple(r for r in self.responses if not r.derived)

    def response(self, name: str) -> ResponseInfo:
        for r in self.responses:
            if r.name == name:
                return r
        raise KeyError(name)

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
    responses = []
    for i, r in enumerate(raw_resp):
        where = f"responses[{i}]"
        ratio = r.get("ratio_of")
        if ratio is not None and (len(ratio) != 2 or not all(isinstance(x, str) for x in ratio)):
            raise ValueError(f"{where}: ratio_of must be [numerator, denominator]")
        responses.append(
            ResponseInfo(
                name=str(_require(r, "name", where)),
                unit=str(r.get("unit", "")),
                goal=Goal(str(r.get("goal", "max"))),
                ratio_of=tuple(ratio) if ratio is not None else None,
                scale=float(r.get("scale", 1.0)),
                low=float(r["low"]) if "low" in r else None,
                high=float(r["high"]) if "high" in r else None,
                weight=float(r.get("weight", 1.0)),
            )
        )
    responses = tuple(responses)

    names = [p.name for p in params] + [r.name for r in responses]
    if len(names) != len(set(names)):
        raise ValueError("config: factor and response names must all be different")
    measured = {p.name for p in params} | {r.name for r in responses if not r.derived}
    for r in responses:
        if r.derived and not set(r.ratio_of) <= measured:
            raise ValueError(
                f"response {r.name!r}: ratio_of must name factors or measured responses, "
                f"got {list(r.ratio_of)}"
            )
    if not any(not r.derived for r in responses):
        raise ValueError("config: at least one response must be measured (not derived)")

    o = data.get("optimizer", {})
    optimizer = OptimizerSettings(
        objective=str(o.get("objective", "single")),
        target=str(o["target"]) if "target" in o else None,
        batch_size=int(o.get("batch_size", 4)),
    )
    if optimizer.target is not None and optimizer.target not in {r.name for r in responses}:
        raise ValueError(f"optimizer.target {optimizer.target!r} is not a response")
    if optimizer.objective == "desirability":
        for r in responses:
            if r.low is None or r.high is None or r.low >= r.high:
                raise ValueError(
                    f"response {r.name!r}: desirability needs low < high (expected range)"
                )
    primary = next(r for r in responses if r.name == (optimizer.target or responses[0].name))

    record = tuple(str(c) for c in data.get("run_sheet", {}).get("record", []))
    clash = set(record) & (set(names) | RESERVED_COLUMNS)
    if clash:
        raise ValueError(f"run_sheet.record: column names already used: {sorted(clash)}")

    d = data.get("design", {})
    design = DesignSettings(
        method=str(d.get("method", "bbd")), center_points=int(d.get("center_points", 3))
    )

    # The primary objective is optimizer.target (default: the first response).
    spec = ExperimentSpec(
        parameters=tuple(params),
        objective=Objective(primary.name, primary.goal),
        seed=seed,
    )
    return ExperimentConfig(name, spec, tuple(infos), responses, design, record, optimizer)


def load_config(path: str | Path) -> ExperimentConfig:
    with Path(path).open("rb") as f:
        return parse_config(tomllib.load(f))
