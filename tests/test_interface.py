import pytest

from engine.interface import ExperimentSpec, Objective, Parameter, ParameterKind


def test_valid_spec():
    spec = ExperimentSpec(
        parameters=(
            Parameter("temperature", ParameterKind.CONTINUOUS, bounds=(25.0, 40.0)),
            Parameter("medium", ParameterKind.CATEGORICAL, values=("A", "B")),
        ),
        objective=Objective("yield"),
        seed=42,
    )
    assert spec.seed == 42


def test_continuous_needs_valid_bounds():
    with pytest.raises(ValueError):
        Parameter("ph", ParameterKind.CONTINUOUS, bounds=(8.0, 6.0))


def test_categorical_needs_values():
    with pytest.raises(ValueError):
        Parameter("medium", ParameterKind.CATEGORICAL)


def test_duplicate_parameter_names_rejected():
    p = Parameter("ph", ParameterKind.CONTINUOUS, bounds=(6.0, 8.0))
    with pytest.raises(ValueError):
        ExperimentSpec(parameters=(p, p), objective=Objective("yield"))
