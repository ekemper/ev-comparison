# AGENTS.md

## Cursor Cloud specific instructions

This is a Python 3.11+ CLI/batch project managed with `uv` (see `SETUP.md` for the
canonical human setup). There is no web server or frontend. The update script runs
`uv sync`, so dependencies are already installed when a session starts.

### Services / entry points

- **XGBoost price model** (`scripts/train_xgboost.py`) — fully self-contained. Trains
  on the committed dataset `data/nissan_leaf_raw.json`, writes `models/nissan_leaf_xgb.json`
  and PNGs to `plots/`. No DB or API keys required. Run:
  `uv run python scripts/train_xgboost.py`.
  Note: running it overwrites the committed model/plot files — `git checkout -- models/ plots/`
  afterward if you don't intend to commit regenerated binaries.
- **Vehicle listing aggregator** (`uv run python -m src.main`, entry point `ev-search`) —
  requires BOTH MongoDB and at least one third-party API key. `src/main.py` exits with
  `ERROR: No API keys configured` if no key is set, so it cannot run end-to-end without
  credentials (`MARKETCHECK_API_KEY`, `AUTODEV_API_KEY`, `DRIVLY_API_KEY`, `CARAPIS_API_KEY` —
  see `SETUP.md`). MongoDB (`docker compose up -d`, port 27017) is only needed for the
  aggregated search; `--skip-db` skips the DB write but still requires an API key.

### Tests / lint

- No test framework, linter, or CI is configured. `scripts/test_*.py` are ad-hoc API
  exploration scripts, not a test suite. The closest smoke test is `python -m src.main`.
