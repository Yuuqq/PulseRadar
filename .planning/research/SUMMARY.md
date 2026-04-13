# Research Summary: TrendRadar Tech Debt Milestone

**Domain:** Python tech debt reduction (testing, dependency management, class decomposition)
**Researched:** 2026-04-13
**Overall confidence:** HIGH

## Executive Summary

TrendRadar is a Python 3.10+ news aggregation tool with ~180 tracked files, 20+ platform crawlers, 60+ RSS feeds, AI analysis via LiteLLM, and 9 notification channels. The codebase has accumulated three categories of technical debt: an 835-line god object (`NewsAnalyzer`), zero test coverage measurement despite 16 existing test files, and a drifting dependency manifest (requirements.txt missing 2 packages vs pyproject.toml).

The prior refactor (commit `63936e15`) already extracted pure functions from `NewsAnalyzer` into five service modules, but left circular coupling through callback parameters (`_fn` injection pattern). The class can be safely decomposed further because it has NO external consumers -- only `main()` in the same file constructs it. MCP server and Web UI import from subpackages, never from `__main__`.

The recommended tooling stack adds five dev dependencies to the existing pytest: `pytest-cov` (7.1.0) for coverage measurement, `responses` (0.26.0) for HTTP mocking of the `requests`-based crawlers, `ruff` (0.15.10) for linting/formatting, `mypy` (1.20.1) for type safety during refactoring, and `pytest-freezer` (0.4.9) for deterministic time tests. The project should adopt `uv` (0.11.6) for dependency management, which supports PEP 735 dependency-groups natively and is 10-100x faster than pip.

The key architectural decision is to decompose `NewsAnalyzer` using the Extract Class pattern into `CrawlCoordinator` and `AnalysisEngine`, with `NewsAnalyzer` preserved as a thin facade. Frozen dataclasses (`CrawlOutput`, `AnalysisOutput`) replace the current 10-15 individual parameter passing between stages.

## Key Findings

**Stack:** pytest 9.x + pytest-cov 7.x + responses 0.26 + ruff 0.15 + mypy 1.20 + uv 0.11 (see STACK.md for full rationale)
**Architecture:** Extract Class decomposition: CrawlCoordinator + AnalysisEngine + thin NewsAnalyzer facade (see ARCHITECTURE.md)
**Critical pitfall:** Refactoring before integration tests exist is the highest-risk mistake -- tests must prove current behavior before structural changes

## Implications for Roadmap

Based on research, suggested phase structure:

1. **Dependency Hygiene** - Fix the broken install path immediately
   - Addresses: requirements.txt drift, tenacity exact pin, optional boto3
   - Avoids: Scope creep (no new features, just fixing what is broken)

2. **Test Infrastructure Setup** - Establish measurement and tooling
   - Addresses: Zero coverage measurement, no HTTP mocking framework, no linter
   - Avoids: Refactoring without a safety net

3. **Test Coverage Expansion** - Fill the gaps identified by coverage
   - Addresses: MCP server (0 tests), crawler mocking, pipeline integration
   - Avoids: Coverage-padding anti-pattern (test behavior, not implementation)

4. **God Object Decomposition** - Extract classes with test safety net
   - Addresses: 835-line NewsAnalyzer, callback coupling, parameter explosion
   - Avoids: Breaking CLI/config/Docker/import compatibility
   - Sub-steps: DTOs first, CrawlCoordinator second, AnalysisEngine third, facade collapse last

5. **Quality Gates** - Establish long-term maintainability
   - Addresses: mypy on new code, pre-commit hooks, pip-audit in CI
   - Avoids: Applying strict typing to all 180 files at once

**Phase ordering rationale:**
- Dependency hygiene first because requirements.txt is actively broken (users cannot install correctly)
- Test infrastructure before test expansion because you need the tools (responses, pytest-cov) before writing the tests
- Test expansion before decomposition because integration tests are the safety net for structural changes
- Decomposition before quality gates because quality gates validate the new structure
- Each phase is independently valuable and independently deployable

**Research flags for phases:**
- Phase 3 (MCP server tests): FastMCP 2.0 test client utilities may be underdocumented; may need to test at function level instead
- Phase 4 (Decomposition): The `run_ai_analysis_fn` callback in notification_service.py re-triggers AI analysis; this must be resolved during AnalysisEngine extraction
- Phase 4 (Decomposition): `TrendAnalyzer.compare_periods()` result is computed but never used downstream; clarify if dead code before extracting

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All versions verified against PyPI on 2026-04-13. No reliance on training data. |
| Features | HIGH | Derived directly from PROJECT.md requirements and CONCERNS.md analysis. |
| Architecture | HIGH | Based on direct code analysis of __main__.py, context.py, and all core/ modules. |
| Pitfalls | HIGH | Derived from actual code patterns (callback coupling, singleton, requirements drift). |
| Phase ordering | HIGH | Determined by data flow and dependency analysis, not convention. |
| FastMCP test utilities | LOW | Could not verify test client API from docs; may need investigation during Phase 3. |

## Gaps to Address

- **FastMCP test patterns:** The MCP server tests will need a testing approach for FastMCP 2.0. Current docs focus on production usage, not testing. May need to test at the function/handler level rather than the MCP protocol level.
- **tenacity 8-to-9 changelog:** The upgrade from 8.5.0 to 9.x needs changelog review before executing. The recommendation is high-confidence but the specific migration path needs verification.
- **TrendAnalyzer dead code:** `TrendAnalyzer.compare_periods()` is called in `run()` but its output (`trend_report`) is never used downstream. Need to determine if this is dead code or a feature-in-progress before decomposition.
- **AppContext secondary god object:** At 485 lines mixing config access, storage, report generation, and notification dispatch, AppContext is itself a god object. Not in scope for this milestone but should be flagged for future work.
- **Coverage baseline:** The actual current coverage is unknown. The first action in Phase 2 should be running pytest-cov to establish a baseline before any changes.
