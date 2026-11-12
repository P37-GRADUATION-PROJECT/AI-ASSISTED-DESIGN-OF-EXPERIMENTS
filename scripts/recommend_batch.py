"""Recommend the next Bayesian-optimization batch and write its run sheet.

Usage:
    # first round, no data yet (space-filling Latin hypercube batch)
    python scripts/recommend_batch.py CONFIG --round 1 -o bo_round1.xlsx

    # later rounds: give every filled-in BO sheet so far
    python scripts/recommend_batch.py CONFIG --round 2 \
        --history bo_round1.xlsx -o bo_round2.xlsx

Writes two files:
  - the run sheet for the lab (no predictions on it, so the lab is not biased)
  - predictions log, CSV, one row per recommended run (default: next to the
    sheet, named <sheet>_predictions.csv); needed later for predicted vs actual

Fair comparison (E3): history that contains Box-Behnken/CCD runs is refused,
because the BO campaign must not see the classical design's results. Use
--allow-classical-history only for simulations, never for the E3 campaign.
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine.bo import check_history_is_fair, recommend  # noqa: E402
from engine.config import load_config  # noqa: E402
from engine.runsheet import read_results, write_run_sheet  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("config")
    ap.add_argument("--round", type=int, required=True, dest="round_no")
    ap.add_argument("--history", nargs="*", default=[], help="filled-in run sheets so far")
    ap.add_argument("--batch", type=int, help="override optimizer.batch_size")
    ap.add_argument("-o", "--output", required=True, help="run sheet to write (.xlsx)")
    ap.add_argument("--log", help="predictions CSV (default: <output>_predictions.csv)")
    ap.add_argument("--allow-classical-history", action="store_true")
    args = ap.parse_args(argv)

    cfg = load_config(args.config)
    history = []
    for sheet in args.history:
        res = read_results(cfg, sheet)
        for p in res.problems:
            print(f"CHECK ({sheet}): {p}")
        if res.pending:
            print(f"note ({sheet}): not measured yet, ignored: {', '.join(res.pending)}")
        history += res.measured

    unfair = check_history_is_fair(history)
    if unfair and not args.allow_classical_history:
        print(
            "refused: history contains classical-design runs "
            f"({', '.join(unfair[:5])}{'...' if len(unfair) > 5 else ''}). "
            "The E3 campaign must not see them.",
            file=sys.stderr,
        )
        return 2
    ids = [r["run_id"] for r in history]
    if len(ids) != len(set(ids)):
        print("refused: the same run_id appears twice in the history", file=sys.stderr)
        return 2

    runs = recommend(cfg, history, args.batch, round_no=args.round_no)
    out = write_run_sheet(cfg, runs, args.output, f"Bayesian optimization, round {args.round_no}")

    log = Path(args.log) if args.log else out.with_name(out.stem + "_predictions.csv")
    names = [f.name for f in cfg.factors]
    pred_cols = sorted({k for r in runs for k in r if k.startswith("pred_")})
    stamp = datetime.now().isoformat(timespec="seconds")
    with log.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            ["run_id", *names, *pred_cols, "round", "n_history", "seed", "objective", "created_at"]
        )
        for r in runs:
            w.writerow(
                [
                    r["run_id"],
                    *[r[n] for n in names],
                    *[r.get(c, "") for c in pred_cols],
                    args.round_no,
                    len(history),
                    cfg.spec.seed + args.round_no,
                    cfg.optimizer.objective,
                    stamp,
                ]
            )

    print(f"{cfg.name}\nround {args.round_no}: {len(runs)} runs from {len(history)} measured\n")
    for r in runs:
        cond = ", ".join(f"{n} = {r[n]:g}" for n in names)
        pred = ""
        if pred_cols:
            t = cfg.spec.objective.name
            if f"pred_{t}_mean" in r:
                pred = f"   predicted {t}: {r[f'pred_{t}_mean']:.3f} ± {r[f'pred_{t}_std']:.3f}"
        print(f"  {r['run_id']}: {cond}{pred}")
    print(f"\nwrote {out}\nwrote {log}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
