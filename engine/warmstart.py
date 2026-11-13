"""Load earlier experiments as warm-start (transfer-learning) data.

The rows come back in the config's own names (factors and responses), with a
``task`` key naming the source task (e.g. the species). Derived responses
(e.g. yield per gram) are computed the same way as for run sheets.

Standard library only; BayBE is not needed to load or inspect the data.
"""

from __future__ import annotations

import csv
import math
from pathlib import Path

from engine.config import ExperimentConfig
from engine.interface import Run

REPO_ROOT = Path(__file__).resolve().parents[1]
TASK = "task"


def load_prior(cfg: ExperimentConfig, root: Path = REPO_ROOT) -> list[Run]:
    ws = cfg.warm_start
    if ws is None:
        return []
    path = Path(ws.source)
    if not path.is_absolute():
        path = root / path
    with path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError(f"warm-start source {path} is empty")
    needed = {ws.task_column, *ws.factors.values(), *ws.responses.values(), *ws.filters}
    missing = needed - set(rows[0])
    if missing:
        raise ValueError(f"warm-start source {path} has no columns {sorted(missing)}")

    out: list[Run] = []
    for i, row in enumerate(rows):
        if any(row[c] != v for c, v in ws.filters.items()):
            continue
        task = row[ws.task_column]
        if task == ws.target_task:
            raise ValueError(f"source row {i} uses the target task name {task!r}")
        run: Run = {TASK: task, "run_id": f"prior-{task}-{i + 1}"}
        for name, col in {**ws.factors, **ws.responses}.items():
            v = float(row[col])
            if not math.isfinite(v):
                raise ValueError(f"source row {i}: {col} is not a finite number")
            run[name] = v
        run.update(ws.fixed)
        for r in cfg.responses:
            if r.derived:
                num, den = (float(run[k]) for k in r.ratio_of)
                if den == 0:
                    raise ValueError(
                        f"source row {i}: cannot derive {r.name} ({r.ratio_of[1]} = 0)"
                    )
                run[r.name] = r.scale * num / den
        out.append(run)
    if not out:
        raise ValueError("warm-start filters removed every source row")
    return out


def tasks(prior: list[Run]) -> list[str]:
    """Source task names, in first-seen order."""
    seen: dict[str, None] = {}
    for r in prior:
        seen.setdefault(str(r[TASK]), None)
    return list(seen)
