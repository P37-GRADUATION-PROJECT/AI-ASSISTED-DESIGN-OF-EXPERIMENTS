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
