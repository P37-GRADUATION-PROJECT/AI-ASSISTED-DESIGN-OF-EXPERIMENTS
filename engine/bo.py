"""Bayesian-optimization campaign on top of BayBE.

`recommend(cfg, history, batch_size)` is stateless: it rebuilds the BayBE
campaign from the config and the measured history on every call. With the
same config, history and round it returns the same batch, so every
recommendation can be reproduced later (report, jury questions).

Objectives (config `[optimizer] objective`):

- ``single``: optimize one response (``optimizer.target``, default the first).
- ``desirability``: geometric mean of all responses, each mapped to 0-1 with
  its ``low``/``high`` from the config (BayBE DesirabilityObjective).

Each recommended run carries the model's prediction for every response,
``pred_<name>_mean`` and ``pred_<name>_std``, so predicted vs measured can be
compared once the lab reports back. The std is the model's uncertainty about
the mean response; a single measurement also has lab noise on top of it.

With no data at all the first batch is a maximin Latin hypercube (spread
over every factor's range). With warm-start data (`[warm_start]` in the
config, e.g. the Çimyapan 2024 thesis runs) the earlier experiments enter as
related tasks (BayBE transfer learning) and the first batch is model-based.

BayBE (and PyTorch) are imported inside the functions, so the rest of the
engine and the web tool work without them installed.
"""

from __future__ import annotations

import math

from engine.config import ExperimentConfig
from engine.interface import Goal, Run
from engine.warmstart import TASK, load_prior, tasks

CLASSICAL_PREFIXES = ("BBD-", "CCD-")


def _targets(cfg: ExperimentConfig):
    from baybe.targets import NumericalTarget

    if cfg.optimizer.objective == "single":
        r = cfg.response(cfg.spec.objective.name)
        return [NumericalTarget(r.name, minimize=r.goal is Goal.MINIMIZE)]
    return [
        NumericalTarget.normalized_ramp(
            r.name, cutoffs=(r.low, r.high), descending=r.goal is Goal.MINIMIZE
        )
        for r in cfg.responses
    ]


def _frame(cfg: ExperimentConfig, runs: list[Run], cols: list[str], label: str):
    import pandas as pd

    rows = []
    for i, run in enumerate(runs):
        missing = [c for c in cols if c not in run or run[c] is None]
        if missing:
            raise ValueError(f"{label} run {run.get('run_id', i)} is missing {missing}")
        values = [run[c] if c == TASK else float(run[c]) for c in cols]
        if not all(math.isfinite(v) for v in values if not isinstance(v, str)):
            raise ValueError(f"{label} run {run.get('run_id', i)} has a non-finite value")
        rows.append(values)
    return pd.DataFrame(rows, columns=cols)


def build_campaign(cfg: ExperimentConfig, history: list[Run], prior: list[Run] | None = None):
    """BayBE Campaign with the config's search space, objective and measurements.

    With warm-start data (`prior`, rows carrying a ``task`` key), the search
    space gets a task parameter: each source task is a related experiment and
    only the target task (the new experiment) is ever recommended. Source rows
    may lie outside the new ranges (e.g. the thesis used up to 48 min); they
    are kept because they still inform the model. The lab's own history must
    stay inside the ranges and is checked strictly.
    """
    from baybe import Campaign
    from baybe.objectives import DesirabilityObjective, SingleTargetObjective
    from baybe.parameters import NumericalContinuousParameter, TaskParameter
    from baybe.searchspace import SearchSpace

    params = [NumericalContinuousParameter(p.name, bounds=p.bounds) for p in cfg.spec.parameters]
    targets = _targets(cfg)
    if cfg.optimizer.objective == "single":
        objective = SingleTargetObjective(targets[0])
    else:
        weights = [r.weight for r in cfg.responses]
        objective = DesirabilityObjective(targets, weights=weights)

    names = [p.name for p in cfg.spec.parameters]
    cols = names + [t.name for t in targets]
    if prior:
        target = _target_task(cfg)
        source_tasks = tasks(prior)
        if target in source_tasks:
            raise ValueError(f"target task {target!r} also appears in the warm-start data")
        params.append(TaskParameter(TASK, values=(*source_tasks, target), active_values=(target,)))
        campaign = Campaign(SearchSpace.from_product(params), objective)
        campaign.add_measurements(
            _frame(cfg, prior, [*cols, TASK], "warm-start"),
            numerical_measurements_must_be_within_tolerance=False,
        )
        if history:
            hist = [{**r, TASK: target} for r in history]
            campaign.add_measurements(_frame(cfg, hist, [*cols, TASK], "history"))
        return campaign

    campaign = Campaign(SearchSpace.from_product(params), objective)
    if history:
        campaign.add_measurements(_frame(cfg, history, cols, "history"))
    return campaign


def _target_task(cfg: ExperimentConfig) -> str:
    return cfg.warm_start.target_task if cfg.warm_start else "target"


def check_history_is_fair(history: list[Run]) -> list[str]:
    """Run IDs from a classical design found in the history.

    E3 rule: the BO campaign must not see the Box-Behnken/CCD results, or the
    comparison is not fair. Callers refuse such history unless told otherwise.
    """
    return [
        str(r.get("run_id"))
        for r in history
        if str(r.get("run_id", "")).startswith(CLASSICAL_PREFIXES)
    ]


def initial_design(cfg: ExperimentConfig, n: int, seed: int):
    """Space-filling first batch when there is no data: maximin Latin hypercube.

    Plain random sampling can put a small batch in one corner (seen in testing:
    4 random runs all at 42-45 g/L biomass). A Latin hypercube puts each run in
    a different slice of every factor's range.
    """
    import numpy as np
    from pyDOE3 import lhs

    unit = lhs(len(cfg.spec.parameters), samples=n, criterion="maximin", seed=seed)
    lo = np.array([p.bounds[0] for p in cfg.spec.parameters])
    hi = np.array([p.bounds[1] for p in cfg.spec.parameters])
    return lo + unit * (hi - lo)


def recommend(
    cfg: ExperimentConfig,
    history: list[Run],
    batch_size: int | None = None,
    round_no: int = 1,
    id_prefix: str = "BO",
    prior: list[Run] | None = None,
) -> list[Run]:
    """Next batch to run, each with predictions for every response.

    Run IDs look like ``BO1-01`` (round 1, run 1). The random seed is
    ``spec.seed + round_no``, so repeating a round reproduces it exactly.

    ``prior``: warm-start rows. ``None`` loads them from the config's
    ``[warm_start]`` section (none if the section is absent); pass ``[]`` to
    switch warm start off, or a list to use other rows (simulations).
    With warm-start data even the first round is model-based.
    """
    import pandas as pd
    from baybe import Settings

    n = batch_size or cfg.optimizer.batch_size
    seed = cfg.spec.seed + round_no
    Settings(random_seed=seed).activate()
    if prior is None:
        prior = load_prior(cfg)
    campaign = build_campaign(cfg, history, prior)
    names = [p.name for p in cfg.spec.parameters]
    has_model = bool(history or prior)
    if has_model:
        batch = campaign.recommend(batch_size=n).reset_index(drop=True)
    else:
        batch = pd.DataFrame(initial_design(cfg, n, seed), columns=names)

    decimals = {f.name: f.decimals for f in cfg.factors}
    # Round to what the lab can actually set, then predict at the rounded point.
    for c in names:
        batch[c] = batch[c].round(decimals.get(c, 6))
    preds = None
    if has_model:
        query = batch[names].copy()
        if prior:
            query[TASK] = _target_task(cfg)
        preds = campaign.posterior_stats(query)

    runs: list[Run] = []
    for i in range(len(batch)):
        run: Run = {
            "run_order": i + 1,
            "std_order": i + 1,
            "run_id": f"{id_prefix}{round_no}-{i + 1:02d}",
            "point_type": ("bo" if history else "bo-warm") if has_model else "bo-initial",
        }
        for c in names:
            run[c] = float(batch[c].iloc[i])
        if preds is not None:
            for t in campaign.targets:
                run[f"pred_{t.name}_mean"] = float(preds[f"{t.name}_mean"].iloc[i])
                run[f"pred_{t.name}_std"] = float(preds[f"{t.name}_std"].iloc[i])
        runs.append(run)
    return runs
