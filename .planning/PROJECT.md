# TrendRadar — Tech Debt Milestone

## What This Is

TrendRadar is a news aggregation and analysis tool that crawls 20+ Chinese and international hot list platforms, 60+ RSS feeds, and extra API sources, then produces HTML reports with AI-powered analysis and delivers notifications via 9 channels. This milestone focuses on reducing accumulated technical debt: extracting the god object, building comprehensive test coverage, and cleaning up dependency management.

## Core Value

Reduce technical debt without breaking any existing user-facing behavior — all CLI arguments, config.yaml files, and Docker deployments must continue working identically.

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
- ✓ GitHub Actions scheduled workflow with check-in cycle — existing
- ✓ Docker deployment with cron scheduling — existing
- ✓ Pydantic config models with env var overrides — existing
- ✓ Plugin registry with auto-discovery — existing
- ✓ Circuit breaker and rate limiter middleware — existing

### Active

- [ ] Break NewsAnalyzer god object into focused orchestrator classes
- [ ] Add MCP server test suite
- [ ] Add pipeline integration tests (crawl→store→analyze→report→notify)
- [ ] Add pytest-cov and achieve 80%+ coverage
- [ ] Add mock HTTP fixtures for crawler tests
- [ ] Sync requirements.txt with pyproject.toml dependencies
- [ ] Unpin tenacity (==8.5.0 → range)
- [ ] Make boto3 an optional dependency

### Out of Scope

- Security hardening (Web UI auth, CSRF) — deferred to separate milestone, not blocking
- Inline HTML generation refactor (templating engine) — large scope, separate effort
- New feature development — this milestone is strictly debt reduction
- Config key case transformation rework — too risky for backwards compat

## Context

- Codebase: ~180 tracked files, Python 3.10+, v5.5.3
- Recent refactor: "comprehensive 6-phase architecture overhaul" (commit 63936e15) already extracted pipeline.py and mode_strategy.py from NewsAnalyzer
- Existing tests: 16 test files in tests/ covering core subsystems, but no coverage measurement
- MCP server: fully functional but zero test coverage
- requirements.txt is missing structlog and pydantic vs pyproject.toml
- tenacity is the only exact-pinned dependency

## Constraints

- **CLI compatibility**: `python -m trendradar` and all CLI arguments must keep working
- **Config compatibility**: Existing `config/config.yaml` files must work without migration
- **Docker compatibility**: Docker images and docker-compose files must keep working
- **Import compatibility**: Public imports used by MCP server and Web UI must not break

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Extract orchestrator classes from NewsAnalyzer | 835-line god object with too many responsibilities; prior refactor already extracted pure functions, next step is class decomposition | — Pending |
| Target 80%+ test coverage | Comprehensive suite requested; current coverage unknown but gaps identified in MCP, crawlers, E2E | — Pending |
| Keep config.yaml key case transformation | Changing lowercase→UPPERCASE mapping risks breaking all existing configs and downstream code | — Decided (keep) |

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
*Last updated: 2026-04-13 after initialization*
