"""Contract between the web tool (app/) and the optimization engine (engine/).

This is a draft; see docs/engine-interface.md. The web tool depends only on the
names defined here, so the engine internals (BayBE, pyDOE3) can change freely.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol


class ParameterKind(StrEnum):
    CONTINUOUS = "continuous"
    DISCRETE = "discrete"
    CATEGORICAL = "categorical"


@dataclass(frozen=True)
class Parameter:
    name: str
    kind: ParameterKind
    bounds: tuple[float, float] | None = None
    values: tuple[float | str, ...] | None = None

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Parameter name must not be empty")
        if self.kind is ParameterKind.CONTINUOUS:
            if self.bounds is None or self.bounds[0] >= self.bounds[1]:
                raise ValueError(f"{self.name}: continuous parameter needs bounds (low < high)")
        elif not self.values:
            raise ValueError(f"{self.name}: {self.kind.value} parameter needs values")


class Goal(StrEnum):
    MAXIMIZE = "max"
    MINIMIZE = "min"


@dataclass(frozen=True)
class Objective:
    name: str
    goal: Goal = Goal.MAXIMIZE


@dataclass(frozen=True)
class ExperimentSpec:
    parameters: tuple[Parameter, ...]
    objective: Objective
    seed: int = 0

    def __post_init__(self) -> None:
        names = [p.name for p in self.parameters]
        if not names:
            raise ValueError("At least one parameter is required")
        if len(names) != len(set(names)):
            raise ValueError("Parameter names must be unique")


# One run: parameter values plus, once measured, the objective value.
Run = dict[str, float | str]


@dataclass
class History:
    runs: list[Run] = field(default_factory=list)


class Engine(Protocol):
    """What the engine must provide to the web tool."""

    def classical_design(self, spec: ExperimentSpec, method: str) -> list[Run]:
        """Return a classical design (e.g. full factorial, LHS) for the spec."""
        ...

    def recommend(self, spec: ExperimentSpec, history: History, batch_size: int) -> list[Run]:
        """Return the next batch of runs to perform, given measured history."""
        ...
