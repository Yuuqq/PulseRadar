# Feature Landscape

**Domain:** Python tech debt reduction for a news aggregation tool (TrendRadar)
**Researched:** 2026-04-13
**Confidence:** HIGH (based on project files + verified tooling ecosystem)

## Table Stakes

Features that must be present or the debt stays. Missing any of these means the reduction effort is incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **pytest-cov integration with fail-under threshold** | Cannot claim "reduced debt" without knowing coverage. The project has 16 test files but zero coverage measurement. | Low | pytest-cov 7.1.0; configure in pyproject.toml with `--cov-fail-under=80`. Branch coverage (`branch = true`) is essential for conditional-heavy crawling logic. |
| **MCP server test suite** | 18 Python files in mcp_server/ with zero tests. This is the largest untested surface. Every tool module, service, and utility needs unit tests. | High | 7 tool modules + 3 services + 3 utilities. Use `responses` library to mock HTTP calls the MCP tools make. |
| **Mock HTTP fixtures for crawler tests** | Crawlers hit 20+ external APIs. Tests without mocks either require network or silently skip. Tests that depend on live endpoints are not tests. | Medium | Use `responses` (0.26.0) for requests-based mocking. Create a `tests/fixtures/` directory with recorded JSON payloads for each platform. |
| **Pipeline integration tests** | No test covers crawl-to-store-to-analyze-to-report-to-notify flow. Individual unit tests pass while the pipeline can break silently at boundaries. | Medium | Mock external I/O at boundaries (HTTP, filesystem, notification channels). Must cover all 3 modes (incremental/current/daily) including the daily fallback-to-current-data path. |
| **Dependency manifest sync** | requirements.txt has 11 packages, pyproject.toml has 13. `structlog` and `pydantic` are missing from requirements.txt. Users installing via requirements.txt get broken installs. | Low | Recommended: delete requirements.txt, use pyproject.toml as single source. Or generate via `uv pip compile`. |
| **tenacity version range** | Exact pin `tenacity==8.5.0` while every other dep uses ranges. This causes unnecessary resolution conflicts and blocks security patches. Latest is 9.1.4. | Low | Change to `tenacity>=9.0,<10`. |
| **God object decomposition (NewsAnalyzer)** | 835-line class with too many responsibilities. Prior refactor extracted functions but left callback coupling (`_fn` params). Blocks testability and comprehension. | High | Extract into CrawlCoordinator + AnalysisEngine with frozen dataclass DTOs (CrawlOutput, AnalysisOutput, RSSOutput). NewsAnalyzer becomes a thin facade. Six steps: (1) define DTOs, (2) extract CrawlCoordinator, (3) extract AnalysisEngine, (4) simplify notification, (5) collapse facade, (6) remove callback params. See ARCHITECTURE.md for component boundaries, data flow, and refactoring order. |
| **Optional boto3 dependency** | boto3 is a 100+ MB transitive dependency tree (botocore) pulled in even when S3 is unused. Most users run local-only. | Low | Use extras: `pip install trendradar[s3]`. Guard S3 imports behind try/except with clear error message. |

## Differentiators

Features that elevate the codebase from "debt reduced" to "maintainable long-term." Not strictly required but provide outsized value.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **ruff linting + formatting** | Replaces flake8/isort/black with a single tool that's 10-100x faster. Catches style drift, unused imports, and code smells. | Low | ruff 0.15.10. Configure in pyproject.toml. Enable I, F, E, UP, B, SIM, RUF rule sets. |
| **mypy type checking** | Catches type mismatches at boundaries between god object and extracted modules. Essential safety net for refactoring. | Medium | mypy 1.20.1. Start with `--ignore-missing-imports`. Focus on core/ and models/ first since Pydantic models already define types. |
| **pip-audit in CI** | Automated vulnerability scanning for all dependencies. Catches known CVEs before they reach production. | Low | pip-audit 2.10.0. Add to CI pipeline. |
| **Coverage report in CI with trend tracking** | CI can track coverage trend over time, block PRs that drop coverage below threshold. | Low | Use `--cov-report=xml` for CI integration and `--cov-report=html` for local review. |
| **conftest.py fixture library** | Current tests use inline setup with MagicMock. Shared fixtures reduce test boilerplate and improve consistency. | Medium | Build `mock_config`, `mock_app_context`, `mock_http_response` fixtures incrementally. |
| **Pre-commit hooks** | Automated quality gates on every commit: ruff check, ruff format, mypy. | Low | pre-commit 4.5.1. Keep hook execution under 10 seconds. |
| **Storage manager testability** | Module-level singleton `_storage_manager` is untestable in isolation. Dependency injection makes storage testable. | Medium | Replace singleton with constructor injection on AppContext. |
| **pytest-freezer for time-dependent tests** | Rate limiter, circuit breaker, and push window tests currently patch `time.monotonic` manually (verbose, fragile). pytest-freezer provides a `freezer` fixture. | Low | pytest-freezer 0.4.9. Drop-in improvement for existing time-patching tests. |
| **Frozen dataclass DTOs for pipeline boundaries** | Replace 10-15 individual function params with CrawlOutput, AnalysisOutput, RSSOutput. Eliminates param confusion, enables IDE support, prevents mutation bugs. | Low | `@dataclass(frozen=True)` from stdlib. Consistent with existing project patterns (FetchedItem, CrawlResult, NewsData). |

## Anti-Features

Features to explicitly NOT build during this debt reduction effort.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Jinja2 templating for HTML reports** | Large scope change that risks breaking all report output. Explicitly out of scope per PROJECT.md. | Separate milestone. Test existing HTML generation for now. |
| **Security hardening (Web UI auth, CSRF)** | Distinct domain requiring threat modeling, not a tech debt item. | Separate milestone. Document risks in PITFALLS.md. |
| **Config key case transformation rework** | Deeply embedded lowercase-to-UPPERCASE mapping. Changing it risks breaking every existing config.yaml. PROJECT.md marks this as decided: keep. | Document the mapping for new contributors. |
| **100% test coverage target** | Diminishing returns past 80%. Chasing 100% leads to testing implementation details. | Target 80% with branch coverage. Focus on untested MCP, crawlers, pipeline. |
| **Migrate to async/await** | Converting entire codebase to async is a rewrite, not debt reduction. | Document as future enhancement. |
| **Strategy pattern for report modes** | The three modes share 80% logic. Separate strategy classes would create massive code duplication. Current mode-branching with a mode string is simpler and correct. | Keep mode branching in AnalysisEngine. MODE_STRATEGIES dict parameterizes differences. |
| **Event-driven pipeline architecture** | Linear pipeline, single consumer per stage. Events add indirection and ordering ambiguity for zero benefit. | Keep explicit sequential call chain in run(). |
| **Abstract base classes for new components** | Only one implementation of CrawlCoordinator and AnalysisEngine. ABCs add indirection without polymorphism benefit. YAGNI. | Concrete classes. Extract interface later if needed. |
| **DI container framework** | Only ~5 services. AppContext already acts as service locator. A DI framework adds magic and learning curve for trivial wiring. | Manual constructor injection. |
| **pytest-xdist parallel execution** | Test suite is small (~200 tests expected). Parallelism adds isolation complexity. | Revisit if suite exceeds 500 tests. |
| **pytest-mock migration** | Codebase already uses `unittest.mock` consistently across 16 files. Switching creates inconsistency for no functional gain. | Keep `unittest.mock`. |
| **VCR.py / pytest-recording** | Cassette-based HTTP recording would be immediately stale for 20+ constantly-changing platforms. | Use `responses` library for transport-layer mocking instead. |
| **hypothesis property-based testing** | Not justified for this milestone's scope (debt reduction, not edge case discovery). | Revisit for a testing-focused milestone. |
| **Replacing SQLite** | Fine for single-process access. Multi-process concern is theoretical. | Leave as-is. Address if actual contention measured. |

## Feature Dependencies

```
pytest-cov integration
    |
    v
Coverage baseline measurement -----> Coverage trend tracking (differentiator)
    |
    v
Mock HTTP fixtures (responses library)
    |
    +---> Crawler unit tests with mocks
    |         |
    |         v
    +---> MCP server test suite (uses same fixture patterns)
    |         |
    |         v
    +---> Pipeline integration tests (compose mocked stages)
              |
              v
         Define DTOs (CrawlOutput, AnalysisOutput, RSSOutput)
              |
              v
         Extract CrawlCoordinator (crawl + merge + store)
              |
              v
         Extract AnalysisEngine (mode strategy + analysis pipeline + AI)
              |
              v
         Simplify Notification Service + Collapse Facade
              |
              v
         Remove _fn callback params from core modules

Dependency sync (independent, do first)
    |
    +---> Optional boto3 (requires extras in pyproject.toml)
    +---> tenacity unpin (trivial, no dependencies)

ruff + pre-commit (independent, do early for immediate quality gates)
    |
    v
mypy type checking (benefits from ruff-cleaned code)
```

## MVP Recommendation

The minimum viable debt reduction, in dependency order:

1. **Dependency manifest sync** -- Fix the broken requirements.txt immediately. Users cannot install the project correctly today.

2. **pytest-cov integration with 80% fail-under** -- Establish the measurement baseline before changing anything else.

3. **ruff linter/formatter** -- Catch code quality issues immediately. Fast to set up, immediate value.

4. **Mock HTTP fixtures + responses library** -- Foundation for all subsequent test work.

5. **MCP server test suite** -- Largest untested surface. Highest coverage-per-effort ratio.

6. **Pipeline integration tests** -- Validate boundary contracts between stages. Must test all 3 modes.

7. **God object decomposition** -- Extract NewsAnalyzer into CrawlCoordinator + AnalysisEngine with frozen DTOs. Tests from steps 4-6 serve as regression safety net. Doing this WITHOUT tests first is the number one cause of refactoring failures.

Defer to differentiator phase: mypy, pip-audit, pre-commit hooks, storage DI, pytest-freezer.

Defer to separate milestones: HTML templating, security hardening, async migration, config case rework.

## Sources

- Project files: `.planning/PROJECT.md`, `.planning/codebase/STACK.md`, `.planning/codebase/CONCERNS.md`
- Direct codebase analysis: `trendradar/__main__.py`, `trendradar/context.py`, `trendradar/core/*.py`
- Import dependency analysis confirming no external consumers of NewsAnalyzer
- pytest-cov 7.1.0: https://pypi.org/project/pytest-cov/ (verified 2026-04-13)
- responses 0.26.0: https://pypi.org/project/responses/ (verified 2026-04-13)
- ruff 0.15.10: https://pypi.org/project/ruff/ (verified 2026-04-13)
- mypy 1.20.1: https://pypi.org/project/mypy/ (verified 2026-04-13)
- pip-audit 2.10.0: https://pypi.org/project/pip-audit/ (verified 2026-04-13)
- pytest-freezer 0.4.9: https://pypi.org/project/pytest-freezer/ (verified 2026-04-13)
