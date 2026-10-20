# Engine interface (draft)

Status: draft, to be agreed between Ömer (web tool) and Emre (engine). Decision D-009.

The code version of this contract is `engine/interface.py`.

## Rules

1. The web tool imports only from `engine.interface`.
2. Inputs and outputs are plain Python types (dataclasses, dicts, lists), so the
   API layer can serialize them without knowing about BayBE or pandas.
3. Every call that involves randomness takes its seed from `ExperimentSpec.seed`.

## Types

- `Parameter`: name, kind (continuous, discrete, categorical), bounds or values.
- `Objective`: name and goal (max or min).
- `ExperimentSpec`: parameters, objective, seed.
- `Run`: a dict of parameter name to value, plus the objective value once measured.
- `History`: the list of runs measured so far.

## Engine operations

- `classical_design(spec, method) -> list[Run]`: a classical design for the
  baseline (full factorial, fractional factorial, LHS, ...).
- `recommend(spec, history, batch_size) -> list[Run]`: next runs from BO.

## Open questions

- Multiple objectives and constraints: in scope for v1?
- How warm-start data (E2) is passed in: as part of `History` or separately?
- Should `recommend` be stateless (as drafted) or keep a campaign object?
