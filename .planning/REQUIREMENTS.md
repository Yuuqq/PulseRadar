# Requirements — TrendRadar Tech Debt Milestone

**Version:** v1
**Created:** 2026-04-13
**Status:** Ready for roadmap

## v1 Requirements

### Dependency Management

- [ ] **DEPS-01**: requirements.txt contains exactly the runtime packages declared in pyproject.toml (no drift, no missing packages)
- [ ] **DEPS-02**: tenacity version specifier is a range (`>=9.0,<10`) instead of exact pin
- [ ] **DEPS-03**: boto3 is an optional extra (`pip install trendradar[s3]`), with clear error if S3 is used without installation

### Test Infrastructure

- [ ] **TEST-01**: pytest-cov is configured in pyproject.toml with `--cov-fail-under=80` and branch coverage enabled
- [ ] **TEST-02**: Coverage baseline is measured and recorded before any refactor changes
- [ ] **TEST-03**: `responses` library is added as a dev dependency and usable for mocking HTTP in crawler tests
- [ ] **TEST-04**: Shared `conftest.py` fixture library provides `mock_config`, `mock_app_context`, and `mock_http_response` fixtures

### Test Coverage Expansion

- [ ] **COV-01**: MCP server has unit tests for all 7 tool modules (data_query, analytics, search, config_mgmt, system, storage_sync, article_reader)
- [ ] **COV-02**: MCP server has unit tests for all 3 service modules (cache_service, data_service, parser_service)
- [ ] **COV-03**: Crawler plugins have mock-based tests using `responses` library for all 9 plugins
- [ ] **COV-04**: Pipeline integration test covers crawl→store→analyze→report→notify for all 3 report modes (incremental/current/daily)
- [ ] **COV-05**: Overall test coverage reaches 80%+ with branch coverage enabled

### God Object Decomposition

- [ ] **REFACTOR-01**: Frozen dataclass DTOs `CrawlOutput`, `AnalysisOutput`, `RSSOutput` exist and are used at stage boundaries
- [ ] **REFACTOR-02**: `CrawlCoordinator` class exists and owns crawl + merge + store logic, returning `CrawlOutput`
- [ ] **REFACTOR-03**: `AnalysisEngine` class exists and owns mode strategy + analysis pipeline + AI analysis, returning `AnalysisOutput`
- [ ] **REFACTOR-04**: `NewsAnalyzer` in `__main__.py` is reduced to a thin facade (under 150 lines)
- [ ] **REFACTOR-05**: `_fn` callback parameters are removed from `core/pipeline.py`, `core/mode_strategy.py`, `core/notification_service.py`, and `core/ai_service.py`
- [ ] **REFACTOR-06**: CLI (`python -m trendradar` + all flags), config.yaml loading, and Docker deployment continue to work unchanged

### Quality Tooling

- [ ] **QUAL-01**: ruff is configured (pyproject.toml) with rule sets I, F, E, UP, B, SIM, RUF and passes on the full codebase
- [ ] **QUAL-02**: ruff format has been run and the codebase is consistently formatted
- [ ] **QUAL-03**: pre-commit hooks run ruff check and ruff format on every commit, execution under 10 seconds

## v2 Requirements (Deferred)

- mypy type checking on core/ and models/ modules
- pip-audit vulnerability scanning in CI
- pytest-freezer for deterministic time-dependent tests
- Storage manager dependency injection (replace module-level singleton)
- AppContext secondary god object decomposition
- Coverage trend tracking in CI with PR blocking

## Out of Scope

- **Jinja2 HTML templating** — large scope change, separate milestone
- **Security hardening** (Web UI auth, CSRF, input validation) — distinct domain, separate milestone
- **Config key case transformation rework** — too risky for backwards compat, deeply embedded
- **100% coverage target** — diminishing returns past 80%
- **Async/await migration** — full rewrite, not debt reduction
- **Strategy pattern for report modes** — modes share 80% logic, would create duplication
- **Event-driven pipeline** — YAGNI for single-consumer linear pipeline
- **DI container framework** — AppContext is enough, manual injection works
- **pytest-xdist parallelism** — test suite too small to justify
- **VCR.py / cassette-based HTTP recording** — cassettes stale for changing platforms
- **SQLite replacement** — sufficient for single-process access

## Traceability

| Requirement | Phase |
|-------------|-------|
| DEPS-01 to DEPS-03 | TBD by roadmap |
| TEST-01 to TEST-04 | TBD by roadmap |
| COV-01 to COV-05 | TBD by roadmap |
| REFACTOR-01 to REFACTOR-06 | TBD by roadmap |
| QUAL-01 to QUAL-03 | TBD by roadmap |

---
*Generated from research (.planning/research/FEATURES.md)*
