# TrendRadar

## What This Is

TrendRadar is a news aggregation and analysis tool that crawls 20+ Chinese and international hot list platforms, 60+ RSS feeds, and extra API sources, then produces HTML reports with AI-powered analysis and delivers notifications via 9 channels. The codebase has been refactored for long-term maintainability: the 835-line NewsAnalyzer god object has been decomposed into focused orchestrators (CrawlCoordinator, AnalysisEngine) behind a thin facade, backed by 235+ tests and automated quality gates.

## Core Value

Reduce technical debt without breaking any existing user-facing behavior — all CLI arguments, config.yaml files, and Docker deployments must continue working identically.

## Current State

**Shipped:** v1.0 Tech Debt (2026-04-16)

- 4 phases, 16 plans, ~21 tasks delivered
- NewsAnalyzer reduced from 615 lines to 81 lines (thin facade)
- 235+ tests with 27% coverage baseline + branch coverage
- Ruff linting + formatting + pre-commit hooks (<2s execution)
- boto3 optional dependency, tenacity range unpinned
- CLI, config.yaml, Docker, MCP server, Web UI all unchanged

## Next Milestone Goals

See `.planning/todos/pending/` for captured ideas. High-priority candidates:
- **AI Agent-friendly news API page** — design structured data endpoint for AI Agent consumption

## Requirements

### Validated

- ✓ Multi-platform hot list crawling (20+ platforms) — existing
- ✓ RSS feed aggregation (60+ configurable feeds) — existing
- ✓ Extra API sources with plugin architecture (9 plugins) — existing
- ✓ AI analysis and translation via LiteLLM (100+ providers) — existing
- ✓ HTML report generation with keyword/platform views — existing
- ✓ 9 notification channels with multi-account support — existing
- ✓ SQLite local storage + S3 remote storage — existing
- ✓ 3 report modes (incremental/current/daily) — existing
- ✓ Flask Web UI for configuration and job management — existing
- ✓ MCP server with FastMCP 2.0 (7 tool modules) — existing
- ✓ GitHub Actions scheduled workflow — existing
- ✓ Docker deployment with cron scheduling — existing
- ✓ Pydantic config models with env var overrides — existing
- ✓ Plugin registry with auto-discovery — existing
- ✓ Circuit breaker and rate limiter middleware — existing
- ✓ Sync requirements.txt with pyproject.toml dependencies — v1.0 Phase 1
- ✓ Unpin tenacity (==8.5.0 → range) — v1.0 Phase 1
- ✓ Make boto3 an optional dependency — v1.0 Phase 1
- ✓ pytest-cov with coverage ratchet (27% baseline, branch coverage) — v1.0 Phase 2
- ✓ Shared conftest.py fixtures (mock_config, mock_app_context, mock_http_response) — v1.0 Phase 2
- ✓ MCP server test suite (66 tests across 10 modules) — v1.0 Phase 2
- ✓ Crawler plugin mock-HTTP tests (9 plugins via responses) — v1.0 Phase 2
- ✓ Pipeline integration tests (all 3 report modes) — v1.0 Phase 2
- ✓ Frozen DTOs at stage boundaries (CrawlOutput, AnalysisOutput, RSSOutput) — v1.0 Phase 3
- ✓ CrawlCoordinator extraction — v1.0 Phase 3
- ✓ AnalysisEngine extraction — v1.0 Phase 3
- ✓ NewsAnalyzer facade collapse (615 → 81 lines) — v1.0 Phase 3
- ✓ Callback parameter elimination (5 core modules) — v1.0 Phase 3
- ✓ CLI / config / Docker / MCP / Web UI compatibility — v1.0 Phase 3
- ✓ Ruff linting (I, F, E, UP, B, SIM, RUF rule sets) — v1.0 Phase 4
- ✓ Ruff formatting across codebase — v1.0 Phase 4
- ✓ Pre-commit hooks (<10s execution) — v1.0 Phase 4

### Active

(None — ready for next milestone)

### Out of Scope

- Security hardening (Web UI auth, CSRF) — deferred to separate milestone
- Inline HTML generation refactor (templating engine) — large scope, separate effort
- Config key case transformation rework — too risky for backwards compat
- 100% coverage target — diminishing returns past 80%

## Context

- Codebase: ~180 tracked files, Python 3.10+, v5.5.3
- Tests: 235+ tests, 27% baseline coverage with ratchet gate
- Quality: Ruff linting + formatting + pre-commit hooks, zero violations
- Architecture: NewsAnalyzer facade → CrawlCoordinator + AnalysisEngine via frozen DTOs
- GitHub Pages: Hub page aggregating historical reports (post-v1.0 enhancement)

## Constraints

- **CLI compatibility**: `python -m trendradar` and all CLI arguments must keep working
- **Config compatibility**: Existing `config/config.yaml` files must work without migration
- **Docker compatibility**: Docker images and docker-compose files must keep working
- **Import compatibility**: Public imports used by MCP server and Web UI must not break

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Extract orchestrator classes from NewsAnalyzer | 835-line god object; prior refactor extracted pure functions, next step was class decomposition | ✓ v1.0 — facade down to 81 lines |
| Target 27% coverage ratchet (not 80%) | Actual coverage 27.93-27.99%; `cov-fail-under` requires total >= threshold | ✓ v1.0 — baseline locked, ratchet-only increases |
| Keep config.yaml key case transformation | Changing lowercase→UPPERCASE mapping risks breaking all existing configs | ✓ Decided (keep) |
| Tests ordered BEFORE decomposition | Research flagged refactoring without safety net as highest-risk mistake | ✓ v1.0 — Phase 2 → Phase 3 sequencing worked |
| Merge TEST + COV requirements into Phase 2 | Coarse granularity matched execution rhythm | ✓ v1.0 — 7-plan phase shipped cleanly |
| Pragmatic Ruff ignores for Chinese codebase | RUF001-003, E501, E722 etc. would produce 2600+ false positives | ✓ v1.0 — zero violations with 16 ignores |
| Frozen DTOs at stage boundaries | Immutable data contracts prevent hidden mutation between stages | ✓ v1.0 — CrawlOutput, AnalysisOutput, RSSOutput shipped |
| Callback-free core modules | `_fn` params obscured data flow and blocked testability | ✓ v1.0 — 5 modules refactored to direct imports |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-16 after v1.0 Tech Debt milestone*
