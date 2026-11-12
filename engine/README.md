# engine

Owner: Emre Kaan Şahin.

Bayesian optimization (BayBE) and classical designs (pyDOE3), plus the
benchmark code for E1 and E2. The web tool uses this package only through
`engine/interface.py`; anything else in here is internal.

Install the engine dependencies with `pip install -r requirements-engine.txt`.

## Modules

| Module | What it does | Needs BayBE |
| --- | --- | --- |
| `interface.py` | Contract with the web tool (types, `Engine` protocol) | no |
| `config.py` | Reads an experiment definition from TOML (factors, ranges, responses, design) | no |
| `classical.py` | Box–Behnken and central composite designs inside the factor ranges, shuffled run order | no |
| `rsm.py` | Quadratic response-surface model: fit, R², adjusted R², Q² (LOO), predicted optimum | no |
| `runsheet.py` | Excel run sheet for the lab and reading measured results back | no |
| `bo.py` | Bayesian-optimization batches (single or desirability objective) with predictions | yes |
| `warmstart.py` | Loads earlier experiments (e.g. the thesis runs) as warm-start data | no |

## Classical design workflow (E3 baseline)

```bash
# 1. make the run sheet (factors and ranges come from the config)
python scripts/make_design.py experiments/e3/case_study.example.toml -o runsheet.xlsx

# 2. the lab fills in the measured responses (and "applied" values if a run deviated)

# 3. fit the quadratic model and get the predicted optimum
python scripts/analyze_design.py experiments/e3/case_study.example.toml runsheet.xlsx
```

Design choices:

- Only designs whose points stay inside the ranges are offered (`bbd`,
  `ccd_face`, `ccd_inscribed`). The circumscribed CCD puts axial points outside
  the ranges, which in the lab can be unsafe or impossible.
- The run order is shuffled with the config's `seed`, so the same config always
  gives the same sheet.
- When reading results, an "applied" value replaces the planned one, so the
  model sees the condition that was actually used. Decimal commas are accepted.

## Bayesian optimization workflow (E3 campaign)

```bash
# round 1: no data yet -> space-filling Latin hypercube batch
python scripts/recommend_batch.py experiments/e3/case_study.example.toml --round 1 -o bo_round1.xlsx

# round 2+: pass every filled-in BO sheet so far
python scripts/recommend_batch.py experiments/e3/case_study.example.toml --round 2 \
    --history bo_round1.xlsx -o bo_round2.xlsx
```

- Needs `pip install -r requirements-engine.txt` (BayBE, PyTorch). The tests in
  `tests/test_bo.py` are skipped when BayBE is missing, so CI does not run them;
  run `pytest` locally with the engine environment before merging BO changes.
- Each round also writes `<sheet>_predictions.csv`: the model's mean and std for
  every run, recorded *before* the lab measures it (predicted vs actual). The
  lab's run sheet does not show predictions.
- The same config, history and round always give the same batch (seed =
  `seed + round`), and values are rounded to the lab's precision before predicting.
- The E3 campaign must not see the classical design: history with `BBD-`/`CCD-`
  runs is refused (`--allow-classical-history` exists for simulations only).
- A response can be derived instead of typed in, e.g. yield =
  `1000 * soluble_protein / biomass` (`ratio_of`, `scale` in the config).

## Warm start (transfer learning)

An enabled `[warm_start]` section in the config gives earlier experiments to
the optimizer as related tasks (BayBE `TaskParameter`): each source task (here
each species of the Çimyapan 2024 thesis) informs the model, and only the
target task (the new experiment) is ever recommended. With warm start the
first round is already model-based.

- Every factor must be mapped to a source column or given a value in
  `[warm_start.fixed]`. A missing value is an error; the code never guesses.
  The example ships with warm start **off** because the thesis does not report
  the pH it used.
- Source rows outside the new ranges are kept (they still inform the model);
  the lab's own runs are checked strictly against the ranges.
- `--no-warm-start` on `scripts/recommend_batch.py` switches it off per call.
- `experiments/e2/loso_thesis.py` checks whether it helps, holding out one species
  at a time (see `experiments/e2/README.md`).
