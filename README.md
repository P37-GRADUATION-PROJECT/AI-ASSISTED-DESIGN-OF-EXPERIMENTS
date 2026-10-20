# AI-Assisted Design of Experiments (P37)

A web-based Design of Experiments (DoE) assistant built on Bayesian optimization
([BayBE](https://github.com/emdgroup/baybe)). The goal is to help lab scientists
reach good process conditions with fewer wet-lab runs than a classical design.

CSE 495/496 Graduation Project, Fall 2026. Advisor: Dr. Salih Sarp.

## Team

| Member | Area |
| --- | --- |
| Emre Kaan Şahin | Optimization engine and benchmarks (`engine/`) |
| Ömer Faruk Gedikli | Web tool, LLM assistant, repository, live demo (`app/`, `frontend/`) |
| Burak Altıparmak | Institute liaison, case study, data documentation (`data/`, `docs/`) |

## Repository layout

```
app/          FastAPI backend (web tool). Talks to the engine only through engine/interface.py
engine/       Optimization engine (BayBE, classical designs via pyDOE3)
frontend/     User interface (framework decision pending, see docs/decisions.md)
docs/         Design notes, decisions, engine interface contract
data/         Dataset descriptions (raw institute data is never committed)
experiments/  Benchmark configs and results (E1, E2, E3)
scripts/      Reproducibility entry points
tests/        pytest suite
```

## Quick start

Requires Python 3.12 or 3.13.

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
pytest                             # run the tests
ruff check .                       # lint
uvicorn app.main:app --reload      # start the API at http://127.0.0.1:8000
```

The same commands are available through `make install`, `make test`, `make lint`
and `make run`.

The engine dependencies (BayBE and PyTorch) are large, so they are kept in a
separate file:

```bash
pip install -r requirements-engine.txt
```

## Reproducibility

- All dependencies are pinned to exact versions.
- Every experiment uses fixed random seeds, recorded next to its results.
- Each reported result can be regenerated with one command
  (`python scripts/reproduce.py <experiment>`, filled in as experiments land).

## Data policy

Raw data from the partner institute is not committed to this repository. The LLM
assistant is off by default, and no institute data is sent to external APIs
without explicit permission.

## License

Apache License 2.0, see [LICENSE](LICENSE).
