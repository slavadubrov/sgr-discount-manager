# Repository Guidelines

## Project Structure & Module Organization

- `agent.py` drives the pricing workflow: router call, feature fetch via tools, and schema-enforced response generation.
- `tools.py` holds `HybridFeatureStore`, which merges cold metrics from `offline_store.duckdb` with live cart data in `online_store.db`.
- `schemas.py` defines the Pydantic contracts (`RouterSchema`, `PricingLogic`) that govern every model reply; keep modifications backward compatible.
- Utility files include `setup_data.py` for reseeding databases, the minimal `main.py`, and the UV project metadata (`pyproject.toml`, `uv.lock`).

## Build, Test, and Development Commands

- `uv sync` installs the Python 3.13 toolchain locally; rerun whenever dependencies change.
- `uv run python setup_data.py` recreates DuckDB/SQLite tables with demo users (`user_100`–`user_109`); execute before exercising the agent.
- `uv run python agent.py` runs the negotiation demo; ensure a vLLM server exposes `http://localhost:8000/v1` with `--guided-decoding-backend xgrammar`.
- `uv run python -m main` is a smoke check proving the interpreter and package metadata are wired correctly.

## Coding Style & Naming Conventions

- Use 4-space indentation, snake_case identifiers, and descriptive function names; mirror existing patterns like `cart_profit_margin` and `margin_math`.
- Keep logic segmented: orchestration in `agent.py`, data access in `tools.py`, schemas in `schemas.py`; avoid circular imports.
- Format with `ruff format` or `black` plus `ruff check` before raising a PR (add them as dev dependencies if needed).

## Testing Guidelines

- Place automated tests under `tests/`, mirroring module names (for example, `tests/test_tools.py` for database integration checks).
- Prefer `pytest` and create fixtures that spin up disposable DuckDB/SQLite files seeded with the SQL used in `setup_data.py`.
- Cover routing behavior (respond vs. fetch), DB error handling, and schema validation edge cases; target ≥80 % statement coverage via `pytest --cov`.

## Commit & Pull Request Guidelines

- Follow Conventional Commits (`feat: add churn gate`, `fix: handle empty inventory`) so release notes can be auto-generated.
- Summarize scenario, include reproduction commands (e.g., `uv run python agent.py "I want a discount" user_105`), and link issues in every PR.
- Attach logs or screenshots that illustrate the `margin_math` or `max_discount_percent` reasoning whenever behavior changes.

## Security & Configuration Tips

- Store API keys and model endpoints in env vars; even though `agent.py` points to localhost, production keys must never hit the repo.
- Treat the DB artifacts as throwaway fixtures—regenerate them locally and exclude any customer-derived data from commits.
