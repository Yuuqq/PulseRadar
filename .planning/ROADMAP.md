# Roadmap: TrendRadar Tech Debt Milestone

## Overview

This milestone reduces three categories of accumulated technical debt in TrendRadar — a broken install path, an 835-line god object, and zero coverage measurement — without changing any user-facing behavior. The journey moves from "users cannot install correctly" to "install works cleanly", then establishes a test safety net, then uses that safety net to decompose `NewsAnalyzer` into focused orchestrator classes, and finally locks in long-term maintainability with ruff and pre-commit hooks. Every phase preserves CLI (`python -m trendradar`), config.yaml loading, Docker deployment, and public imports used by the MCP server and Web UI.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Dependency Hygiene** - Fix the broken install path: sync requirements.txt, unpin tenacity, make boto3 optional
- [ ] **Phase 2: Test Safety Net** - Establish coverage measurement, HTTP mocking, and comprehensive tests for MCP server, crawlers, and the full pipeline
- [ ] **Phase 3: God Object Decomposition** - Extract CrawlCoordinator and AnalysisEngine from NewsAnalyzer behind a thin facade, using frozen DTOs at stage boundaries
- [ ] **Phase 4: Quality Gates** - Lock in long-term maintainability with ruff linting, ruff format, and pre-commit hooks

## Phase Details

### Phase 1: Dependency Hygiene
**Goal**: A fresh clone can be installed correctly from requirements.txt, and the dependency manifest honestly reflects what the project needs
**Depends on**: Nothing (first phase)
**Requirements**: DEPS-01, DEPS-02, DEPS-03
**Success Criteria** (what must be TRUE):
  1. A user running `pip install -r requirements.txt` in a clean venv gets every package the runtime actually imports (no `ModuleNotFoundError` for structlog or pydantic at startup)
  2. `pip install trendradar` succeeds without pulling boto3, and using S3 storage without the `[s3]` extra produces a clear, actionable error message pointing the user to `pip install trendradar[s3]`
  3. `pip install trendradar` picks up tenacity 9.x via the new range specifier, and the existing retry/circuit-breaker code continues to work unchanged
  4. `python -m trendradar` and all existing CLI flags still work identically after the dependency changes
**Plans:** 2 plans
Plans:
- [x] 01-01-PLAN.md — Update pyproject.toml (tenacity range, boto3 optional), regenerate requirements.txt, add fail-fast boto3 check with unit test
- [x] 01-02-PLAN.md — Update Dockerfiles for boto3, add CHANGELOG entry and README install notes

### Phase 2: Test Safety Net
**Goal**: A developer can run one command, see measured coverage, and trust that the MCP server, every crawler plugin, and the full pipeline are verified against current behavior — so structural refactors in Phase 3 are safe
**Depends on**: Phase 1
**Requirements**: TEST-01, TEST-02, TEST-03, TEST-04, COV-01, COV-02, COV-03, COV-04, COV-05
**Success Criteria** (what must be TRUE):
  1. Running `pytest` reports coverage with branch coverage enabled and fails the run if coverage drops below 80%
  2. A baseline coverage number exists on record (committed artifact or documented in Phase 2 summary) taken before any refactor touches `NewsAnalyzer`
  3. Every MCP server tool module and service module has unit tests that exercise its public surface; running them does not require a live MCP client
  4. Every crawler plugin has tests that use the `responses` library to mock HTTP, so the full test suite runs offline and deterministically
  5. A pipeline integration test exercises crawl → store → analyze → report → notify for all three report modes (incremental, current, daily) and passes against the current (still-monolithic) `NewsAnalyzer`
  6. A shared `conftest.py` exposes `mock_config`, `mock_app_context`, and `mock_http_response` fixtures that new tests can reuse without duplication
**Plans:** 6 plans
Plans:
- [ ] 02-01-PLAN.md — Coverage infrastructure (pytest-cov, responses, pytest-randomly in pyproject.toml + requirements-dev.txt)
- [ ] 02-02-PLAN.md — Shared conftest.py fixtures (mock_config, mock_app_context, mock_http_response, autouse singleton reset)
- [ ] 02-03-PLAN.md — Crawler plugin tests (9 plugins x happy+error using responses)
- [ ] 02-04-PLAN.md — MCP server tests (7 tool modules + 3 service modules + FastMCP smoke test)
- [ ] 02-05-PLAN.md — Pipeline integration tests (5-case mode strategy + extra-API merge + dead code lock)
- [ ] 02-06-PLAN.md — Coverage baseline capture (coverage.xml commit + .gitignore update)

### Phase 3: God Object Decomposition
**Goal**: `NewsAnalyzer` is a thin facade over two focused orchestrators (`CrawlCoordinator`, `AnalysisEngine`) that communicate via frozen DTOs, and every external caller (CLI, MCP server, Web UI, Docker) keeps working exactly as before
**Depends on**: Phase 2
**Requirements**: REFACTOR-01, REFACTOR-02, REFACTOR-03, REFACTOR-04, REFACTOR-05, REFACTOR-06
**Success Criteria** (what must be TRUE):
  1. `CrawlOutput`, `AnalysisOutput`, and `RSSOutput` exist as frozen dataclasses and are the only data shapes crossing stage boundaries between crawl, analyze, report, and notify
  2. `CrawlCoordinator` owns crawl + merge + store and returns `CrawlOutput`; `AnalysisEngine` owns mode strategy + analysis pipeline + AI analysis and returns `AnalysisOutput`
  3. `NewsAnalyzer` in `trendradar/__main__.py` is under 150 lines and contains no business logic beyond wiring the orchestrators together
  4. No module in `core/` accepts a `_fn` callback parameter (pipeline, mode_strategy, notification_service, ai_service are all callback-free)
  5. Running `python -m trendradar` with every existing CLI flag produces identical HTML reports and identical notification payloads to the pre-refactor baseline, and the Phase 2 pipeline integration test still passes unchanged
  6. The MCP server and Flask Web UI start and serve requests without any import errors, using the same public import paths they used before the refactor
**Plans**: TBD

### Phase 4: Quality Gates
**Goal**: New commits are automatically checked for style, lint, and import issues in under 10 seconds, so the newly-clean codebase cannot silently regress
**Depends on**: Phase 3
**Requirements**: QUAL-01, QUAL-02, QUAL-03
**Success Criteria** (what must be TRUE):
  1. Running `ruff check .` on the full codebase exits clean with rule sets I, F, E, UP, B, SIM, and RUF enabled in `pyproject.toml`
  2. Running `ruff format --check .` on the full codebase exits clean (the whole codebase is already formatted)
  3. A `git commit` from a fresh clone (after `pre-commit install`) automatically runs ruff check and ruff format on staged files and completes in under 10 seconds on a typical laptop
  4. `python -m trendradar`, config.yaml loading, and Docker deployment still work identically after formatting and lint fixes
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Dependency Hygiene | 0/2 | Planned | - |
| 2. Test Safety Net | 0/6 | Planned | - |
| 3. God Object Decomposition | 0/TBD | Not started | - |
| 4. Quality Gates | 0/TBD | Not started | - |
