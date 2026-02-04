# Repository Guidelines

## Project Structure

- `trendradar/`: Core Python package (crawler, analysis, report generation, notifications, storage).
- `mcp_server/`: MCP server implementation and tools.
- `config/`: Default configuration files and AI prompt templates (e.g. `config/config.yaml`).
- `docker/`: Container build and compose files (`docker/Dockerfile`, `docker/docker-compose.yml`).
- `docs/`: Documentation and guides.
- `output/`: Generated artifacts (SQLite/TXT/HTML reports). Avoid committing new output unless intentionally updating fixtures/sample data.

## Build, Test, and Development Commands

- Install (runtime): `python -m pip install -r requirements.txt`
- Install (editable, recommended for dev): `python -m pip install -e .`
- Run TrendRadar: `python -m trendradar` or `trendradar`
- Run MCP server: `trendradar-mcp`
- Docker (example): `docker compose -f docker/docker-compose.yml up --build`

## Coding Style & Naming

- Python: follow PEP 8, 4-space indentation, type hints where practical.
- Prefer small, testable functions; avoid adding new global state.
- Keep configuration-driven behavior in `config/config.yaml` + environment overrides (e.g. `AI_API_KEY`, `AI_API_BASE`, `CRAWLER_API_URL`).

## Testing Guidelines

- Tests use `pytest`. Install dev deps with `python -m pip install -r requirements-dev.txt`.
- Run tests: `python -m pytest -q`
- Add focused regression tests for parsers/formatters (AI response parsing, batching, config loading).

## Commit & Pull Request Guidelines

- Commit messages follow a conventional style: `feat: ...`, `fix: ...`, `docs: ...`, `refactor: ...`, `chore: ...`.
- PRs should include: a short problem statement, the config keys impacted (if any), and screenshots/outputs for UI/report changes (e.g. HTML report diffs).
- Never commit secrets (API keys, webhook URLs). Use env vars or private CI secrets instead.
