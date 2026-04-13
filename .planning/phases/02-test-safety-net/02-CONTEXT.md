# Phase 2: Test Safety Net - Context

**Gathered:** 2026-04-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Establish a measurable, reliable test safety net so that Phase 3 can decompose `NewsAnalyzer` without behavior regressions. Three pillars:

1. **Coverage infrastructure** — `pytest-cov` wired into `pyproject.toml` with branch coverage and an 80% local gate (TEST-01, TEST-02, COV-05).
2. **Offline HTTP mocking** — `responses` library as a dev dep + reusable fixture so every crawler test runs deterministically without network (TEST-03).
3. **Targeted coverage expansion** — new tests for all MCP tool and service modules (COV-01, COV-02), all 9 crawler plugins (COV-03), and a characterization-style pipeline integration test covering all 3 report modes (COV-04), backed by a shared `conftest.py` fixture library (TEST-04).

Phase preserves the existing `NewsAnalyzer` monolith — this phase adds tests AROUND it, never changes it. All CLI, `config.yaml`, Docker, and public MCP/Web UI imports continue to work unchanged.

</domain>

<decisions>
## Implementation Decisions

### Coverage scope & configuration
- **D-01:** Coverage source = `["trendradar", "mcp_server"]`. Both packages measured against a single global 80% gate. Pitfall 15 explicitly warns against `--cov=trendradar` alone.
- **D-02:** Gate enforced locally via `pyproject.toml` `[tool.pytest.ini_options] addopts = "--cov --cov-fail-under=80"` so a bare `pytest` invocation runs coverage and fails below 80%. No separate command or Makefile target required.
- **D-03:** Branch coverage enabled via `[tool.coverage.run] branch = true` in `pyproject.toml`.
- **D-04:** Coverage exclusions kept tight: `tests/**`, `trendradar/webui/templates/**`, `trendradar/webui/static/**`, `if __name__ == "__main__":` guards, and `if TYPE_CHECKING:` blocks. Everything else — including `trendradar/__main__.py:main()` and the unused `trend_report` path (Pitfall 8) — stays IN scope so discrepancies surface.

### Baseline artifact for TEST-02
- **D-05:** At phase end, commit `coverage.xml` ONCE as the locked baseline alongside a per-module coverage table in the Phase 2 `02-SUMMARY.md`. Add `coverage.xml` to `.gitignore` afterward so subsequent runs don't churn the file. Phase 3 can diff against the committed baseline.

### Dev dependency additions
- **D-06:** Add `pytest-cov`, `responses`, and `pytest-randomly` to `pyproject.toml` `[dependency-groups] dev`. These are test infrastructure, not ad-hoc tools — they must exist in the canonical dep manifest (different from Phase 1 D-07's treatment of `pip-tools`/`uv`).
- **D-07:** `pytest-randomly` is included specifically to surface Pitfall 12 (StorageManager singleton state leaks) and any other cross-test coupling before Phase 3 refactors rely on isolation.
- **D-08:** Regenerate `requirements-dev.txt` via the same `uv pip compile` / `pip-compile` path Phase 1 established for `requirements.txt` (D-05/D-06 in Phase 1). Generated-file header mirrors Phase 1 style. No new dev dep for the regen tool — still ad-hoc (consistent with Phase 1 D-07).

### CI / pre-commit integration
- **D-09:** Phase 2 ships the coverage gate LOCALLY only. No GitHub Actions workflow edits, no pre-commit hook. CI enforcement + pre-commit hooks are Phase 4 deliverables (QUAL-03) — keeps phase boundaries clean and avoids duplicate work.

### MCP testing strategy (COV-01, COV-02)
- **D-10:** **Handler-level testing** for all 7 tool modules (`data_query`, `analytics`, `search_tools`, `config_mgmt`, `system`, `storage_sync`, `article_reader`) and all 3 service modules (`cache_service`, `data_service`, `parser_service`). Tests import the tool/service Python functions directly and call them with mocked dependencies, bypassing FastMCP's registration layer.
- **D-11:** Add exactly ONE end-to-end smoke test that spins up FastMCP in-process and invokes one representative tool through the MCP protocol surface. Purpose: verify `@mcp.tool` registration wiring is intact. If the FastMCP 2.0 test client API blocks this smoke test, planner is authorized to fall back to a pure import-side assertion (tool registration list is non-empty) rather than spending research budget on the underdocumented API. STATE.md flagged this gap — do NOT let it block the phase.
- **D-12:** All MCP tool tests consume `mock_app_context` (from TEST-04) as the dependency-injection entry point. Storage is a tmp_path SQLite. AI client is patched. HTTP calls (from `article_reader`, `search_tools`) go through the shared `mock_http_response` / `responses` fixture.
- **D-13:** **Claude's discretion — async handling:** FastMCP tool handlers may be sync or async depending on decorator. The phase researcher (`gsd-phase-researcher`) must inspect actual tool signatures in `mcp_server/tools/*.py` and recommend `pytest-asyncio` or `anyio` in RESEARCH.md. If `pytest-asyncio` is required, add it to dev deps at that point — not upfront.

### Pipeline integration test (COV-04)
- **D-14:** Mock boundaries: **HTTP (via `responses`), AI client (via `unittest.mock.patch` on `trendradar/ai/client.py`), and notification channels (via patched dispatcher)**. SQLite storage is REAL, living in `tmp_path`. Rationale: storage bugs matter for Phase 3 DTO extraction; external I/O does not.
- **D-15:** **Five test cases** covering Pitfall 7's mode-strategy branches exhaustively:
  1. `incremental` with data
  2. `current` with history
  3. `current` without history → must raise `RuntimeError` (assertion required)
  4. `daily` with history
  5. `daily` without history → must fall back to current data
  Each case is a named test function sharing a parametrized fixture set. No monolithic single test.
- **D-16:** Assertions per case: (a) report HTML file content checks — assert key substrings / section presence in the generated HTML, NOT full golden-file diff; (b) notification dispatcher receive calls — recorded via mock, assert recipient count, payload field shape, and ordering per mode; (c) extra-API merge verification — assert `results` dict contains both hotlist and extra-API `source_ids` and `id_to_name` contains both, locking in Pitfall 3's current mutation-based merge shape; (d) storage state verification — row counts / content via the real SQLite file after run.
- **D-17:** **Pitfall 8 handling (dead `trend_report`):** Test asserts that `_analyze_trends` is invoked (method is called) but does NOT assert the result is used downstream — locking current behavior exactly. Phase 3 decides whether to remove the dead call or wire `trend_report` into the pipeline. Captured in Deferred Ideas below.

### Fixture & conftest design (TEST-04)
- **D-18:** **`mock_config` fixture** — returns a minimal-valid config `Dict` built from `trendradar/models/config.py` Pydantic model defaults. Overridable via kwargs so individual tests can tweak fields. Function-scoped.
- **D-19:** **`mock_app_context` fixture** — constructs a REAL `AppContext` using `mock_config` + a `tmp_path`-backed SQLite storage + patched AI client. Real code paths exercised; only external I/O is faked. Function-scoped.
- **D-20:** **`mock_http_response` fixture** — wraps `responses.RequestsMock` as a context manager, yielding the mock object. Function-scoped. Crawler / MCP HTTP-using tests consume this to register URL stubs.
- **D-21:** **Autouse singleton reset** — add an autouse fixture in top-level `tests/conftest.py` that sets `trendradar.storage.manager._storage_manager = None` before each test. Combined with `pytest-randomly`, this catches Pitfall 12 state leaks deterministically. This is a test-only change; production code is untouched.

### Crawler plugin tests (COV-03)
- **D-22:** **One test file per plugin** under a new `tests/crawler/plugins/` directory — `test_dailyhot.py`, `test_eastmoney.py`, etc. for all 9 plugins.
- **D-23:** Shared assertion helpers live in `tests/crawler/_helpers.py` (e.g., `assert_fetched_item_shape`). HTTP response fixtures live INLINE as Python dicts/strings at the top of each test file — no external YAML or JSON fixture files. Readability over DRY.
- **D-24:** Coverage depth per plugin: at least ONE happy-path test + at least ONE error mode (timeout OR HTTP 5xx OR malformed response). Planner picks which error mode per plugin based on what the plugin actually handles. Full error-matrix coverage is NOT required — Pitfall 4 warns against coverage-padding.

### Test directory structure
- **D-25:** **Nested by subsystem for NEW files**: `tests/crawler/plugins/`, `tests/mcp/tools/`, `tests/mcp/services/`, `tests/pipeline/`. Each subsystem folder may have its own `conftest.py` for scoped fixtures.
- **D-26:** **Existing 16 test files stay at `tests/` root** — do NOT move or restructure them. No behavior change, lower churn, zero risk of import breakage. Phase 2 is additive only.

### Claude's Discretion
- Exact `[tool.coverage.report]` exclude_lines patterns beyond the categories in D-04 (standard `pragma: no cover`, abstract methods, etc.).
- Exact file naming convention within `tests/mcp/tools/` vs `tests/mcp/services/`.
- Exact assertion helper names in `tests/crawler/_helpers.py`.
- Whether the one FastMCP smoke test (D-11) lives in `tests/mcp/` root or `tests/mcp/tools/`.
- Whether `mock_app_context` exposes individual mocked components as attributes (`.storage`, `.ai_client`) or only via `AppContext` accessor methods — planner decides based on actual AppContext API.
- Exact HTML substring assertions in the pipeline integration test — planner picks 3-5 stable markers per mode.
- Order of test commits during execution (coverage config first vs fixtures first vs test content first).
- Whether to add `pytest-asyncio` or `anyio` for MCP async handlers — D-13 delegates this to the researcher.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Research artifacts (project-local)
- `.planning/research/PITFALLS.md` §"Pitfall 1: Refactoring Without Integration Tests First" — the guiding rationale for why Phase 2 exists at all. Downstream agents must treat this as the phase's reason-for-being.
- `.planning/research/PITFALLS.md` §"Pitfall 4: Coverage Threshold Without Meaningful Tests" — mandates behavior-over-implementation assertions; planner must not allow coverage-padding tests.
- `.planning/research/PITFALLS.md` §"Pitfall 7: Mode Strategy Branching Subtleties" — explicit list of 5 mode × data-state combinations that MUST be covered by the pipeline integration test (D-15).
- `.planning/research/PITFALLS.md` §"Pitfall 8: trend_report Computed But Never Used" — locks D-17's "test current behavior, defer resolution" stance.
- `.planning/research/PITFALLS.md` §"Pitfall 12: StorageManager Singleton Blocking Test Isolation" — justifies D-21 autouse reset fixture and D-07 `pytest-randomly` inclusion.
- `.planning/research/PITFALLS.md` §"Pitfall 15: Coverage Configuration Omitting mcp_server" — justifies D-01 dual-package source.
- `.planning/research/PITFALLS.md` §"Phase-Specific Warnings" table rows for "Coverage setup", "Mock fixtures", "MCP server tests" — mitigation summaries for this phase.
- `.planning/research/FEATURES.md` — full test infrastructure features matrix.

### Project contract docs
- `.planning/REQUIREMENTS.md` §"Test Infrastructure" (TEST-01, TEST-02, TEST-03, TEST-04) and §"Test Coverage Expansion" (COV-01 through COV-05) — the nine requirements this phase must satisfy.
- `.planning/ROADMAP.md` §"Phase 2: Test Safety Net" — the six Success Criteria that define "done".
- `.planning/PROJECT.md` §"Constraints" — CLI / config.yaml / Docker / public-import compatibility constraints; no code changes in Phase 2 should break any of these.
- `.planning/STATE.md` §"Blockers/Concerns" — records the FastMCP 2.0 test client research gap that D-10/D-11 route around.

### Prior phase artifacts (for pattern consistency)
- `.planning/phases/01-dependency-hygiene/01-CONTEXT.md` §"requirements.txt strategy" (D-05, D-06, D-07) — the `uv pip compile` regeneration pattern that D-08 extends to `requirements-dev.txt`.
- `.planning/phases/01-dependency-hygiene/01-CONTEXT.md` §"Docker image handling" — reminder that Docker is a constraint, not a target for this phase.

### Codebase map docs
- `.planning/codebase/TESTING.md` — baseline of current 16-test suite, gaps list, and pytest config. Phase 2 additions must remain compatible with `testpaths = ["tests"]` and the existing `tests/conftest.py` sys.path bootstrap.
- `.planning/codebase/CONCERNS.md` §"Testing Gaps" — confirms "No MCP Server Tests", "No E2E Pipeline Tests", "Minimal Mocking" as the concrete holes COV-01 through COV-04 fill.
- `.planning/codebase/ARCHITECTURE.md` §"Crawler Layer", §"Analysis Layer", §"Notification Layer" — module-to-test mapping reference.

### Code files the planner/researcher will touch or reference
- `pyproject.toml` — add `[tool.pytest.ini_options] addopts`, `[tool.coverage.run]`, `[tool.coverage.report]`, and `[dependency-groups] dev` entries (D-02, D-03, D-04, D-06).
- `requirements-dev.txt` — regenerate from `[dependency-groups] dev` via `uv pip compile` (D-08).
- `tests/conftest.py` — extend existing sys.path bootstrap with `mock_config`, `mock_app_context`, `mock_http_response` fixtures + autouse singleton reset (D-18, D-19, D-20, D-21).
- `trendradar/models/config.py` — reference for `mock_config` default construction (D-18).
- `trendradar/context.py` (`AppContext`) — reference for `mock_app_context` wiring (D-19).
- `trendradar/storage/manager.py` — location of `_storage_manager` module-level singleton that D-21 resets.
- `trendradar/__main__.py` `NewsAnalyzer.run()` — the method the pipeline integration test exercises; 3 report modes branch through `core/mode_strategy.py:execute_mode_strategy()`. Do NOT modify.
- `trendradar/core/mode_strategy.py` — the 5 branches D-15 covers (lines around 420–438 for the daily fallback, per Pitfall 7).
- `trendradar/__main__.py` lines 624–641 — the extra-API merge site whose current shape D-16 must assert.
- `trendradar/crawler/plugins/*.py` — 9 files: `dailyhot`, `eastmoney`, `gnews`, `mediastack`, `newsapi`, `thenewsapi`, `tonghuashun`, `vvhan`, `wallstreetcn`. One test file each under `tests/crawler/plugins/` (D-22).
- `mcp_server/tools/*.py` — 7 files: `analytics`, `article_reader`, `config_mgmt`, `data_query`, `search_tools`, `storage_sync`, `system`. Test files under `tests/mcp/tools/` (D-10).
- `mcp_server/services/*.py` — 3 files: `cache_service`, `data_service`, `parser_service`. Test files under `tests/mcp/services/` (D-10).
- `mcp_server/server.py` — reference for the one FastMCP in-process smoke test (D-11).
- `trendradar/ai/client.py` — the patch target for AI mocking in the pipeline integration test (D-14).
- `trendradar/notification/dispatcher.py` — the patch target for notification assertions (D-14, D-16).

### External references (only if planner needs to verify)
- `responses` library docs: https://pypi.org/project/responses/ — reference for `RequestsMock` context manager used in `mock_http_response` (D-20).
- `pytest-cov` docs: https://pytest-cov.readthedocs.io/ — reference for `--cov-fail-under`, `--cov-branch`, and `pyproject.toml` configuration syntax.
- `pytest-randomly` docs: https://pypi.org/project/pytest-randomly/ — reference for cross-test isolation detection (D-07).
- `coverage.py` docs: https://coverage.readthedocs.io/ — reference for `[tool.coverage.run]` branch + source config (D-01, D-03, D-04).
- FastMCP 2.0 docs (to be located by researcher): reference for in-process test client (D-11); known to be underdocumented per STATE.md.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`tests/conftest.py`** — already does sys.path bootstrap. Extend it (don't replace it) with the three TEST-04 fixtures and the autouse singleton reset.
- **Pydantic config models** at `trendradar/models/config.py` — provide a ready-to-use source for `mock_config` default construction; no need to hand-write test config dicts.
- **`AppContext`** at `trendradar/context.py` — central DI container; `mock_app_context` builds a real one rather than faking one, so tests exercise the real wiring.
- **Existing 16 test files** — establish the style (`# coding=utf-8`, `from __future__ import annotations`, direct assertions, minimal mocks). New tests follow the same style for consistency.
- **`trendradar/storage/remote.py` `HAS_BOTO3` guard** — Phase 1 artifact; MCP storage_sync tool tests must respect this guard when the test environment lacks boto3 (handler-level tests per D-10 skip the guarded path cleanly).
- **`tests/test_storage_boto3_guard.py`** — Phase 1's boto3-guard test; follow its pattern for any new tests that need to toggle optional dependencies.

### Established Patterns
- **`testpaths = ["tests"]`** in `pyproject.toml` — new nested test directories must live under `tests/` so pytest discovers them without config changes.
- **Chinese + English mixed docstrings** — preserve the existing style in new test files. English is fine for test function names and assertion messages.
- **Storage singleton via module-level `_storage_manager`** — Pitfall 12 — test isolation requires explicit reset; D-21 addresses this.
- **`# coding=utf-8` header** — preserve on all new test files.
- **No existing mocking library beyond `unittest.mock`** — `responses` is a NEW addition in Phase 2 (TEST-03). Document its usage pattern in the first crawler test file so later tests have a reference.
- **Connection pool / circuit breaker middleware** — `trendradar/crawler/middleware/` — crawler plugin tests should exercise the middleware in at least one plugin test to catch Pitfall-7-style regressions in middleware wiring.

### Integration Points
- **`trendradar/__main__.py main()` CLI entry** — the pipeline integration test must invoke `NewsAnalyzer.run()` through the same path `main()` uses, or pipe-equivalent, so that decomposition tests validate the user-facing path.
- **`mcp_server/server.py run_server()`** — MCP entry point; the one smoke test (D-11) exercises this via in-process FastMCP client.
- **`trendradar/webui/app.py`** — Web UI is OUT of scope for new tests in Phase 2. Existing `test_webui_app_jobs.py` and `test_webui_job_manager.py` stay untouched. Web UI coverage counts toward the 80% gate but is not a Phase 2 expansion target.
- **GitHub Actions workflow** (`.github/workflows/`) — NOT touched in Phase 2 per D-09. Phase 4 wires CI gating.
- **Docker images** — NOT touched in Phase 2. Compatibility comes for free since the test infrastructure is local-only.

</code_context>

<specifics>
## Specific Ideas

- "Characterization tests are mandatory before any structural change" — Pitfall 1 phrasing. Phase 2 tests must lock in CURRENT behavior, not prescribe ideal behavior. Where current behavior includes dead code (Pitfall 8) or in-place mutation (Pitfall 3), the test locks that shape as-is.
- The pipeline integration test is literally the thing Phase 3 engineers will run after every commit to prove they haven't broken anything. Treat its clarity and failure-message quality as a first-class requirement.
- `pyproject.toml` is the canonical dependency manifest (Phase 1 precedent). `requirements-dev.txt` is generated mirror, not source-of-truth.
- No coverage-padding. If a tool or service module is genuinely untestable without FastMCP client or without decomposition, document that in the phase SUMMARY and accept a lower-than-100% module number; the 80% gate applies globally, not per-module.
- Autouse fixtures are cheap — use them for cross-cutting concerns (singleton reset) but NOT for substantive setup (that belongs in explicit fixtures tests opt into).
- Keep the one FastMCP smoke test robust: if the test client API is unstable, its failure must be clearly distinguishable from a real tool registration regression. Use explicit skip markers with reason text, not silent pass.

</specifics>

<deferred>
## Deferred Ideas

- **CI `--cov-fail-under` gate in GitHub Actions** — Phase 4 Quality Gates (QUAL-03) wires this into CI alongside ruff and pre-commit hooks.
- **Pre-commit hook running coverage** — Phase 4 (QUAL-03). Adding it now duplicates Phase 4 infrastructure work.
- **Resolution of Pitfall 8 `trend_report`** — Phase 2 locks current behavior (compute + discard). Phase 3 `AnalysisEngine` extraction is the natural point to decide: remove the dead call OR wire `trend_report` through to reports/notifications. Planner for Phase 3 must raise this explicitly.
- **Resolution of Pitfall 3 extra-API in-place mutation** — Phase 2 locks the current merge shape via assertions. Phase 3 `CrawlCoordinator` must internalize the merge so `CrawlOutput` can be frozen; the Phase 2 test will catch any mistake in that refactor.
- **Full error matrix per crawler plugin** — Phase 2 requires one happy + one error mode per plugin (D-24). Exhaustive error testing (timeout × 5xx × malformed × circuit-breaker-tripped) can land as a v2 requirement if gaps surface during Phase 3.
- **Strict golden-file HTML diffing** — rejected for pipeline integration test (D-14, D-16). Too brittle for Phase 3's refactor work where incidental string changes are expected. Can be added in v2 with an intentional "lock the rendered HTML" requirement.
- **Pydantic-model-validated test fixtures** — `mock_config` returns a dict, not a Pydantic instance. Full model validation in fixtures could catch test-side config errors but is out of scope; revisit if test suite config errors become common.
- **Splitting pipeline integration test by subsystem** — the 5-case integration test intentionally covers the full pipeline per mode. Pitfall 1 warns against splitting it into per-subsystem unit tests that miss boundary bugs.
- **FastMCP 2.0 protocol-level test fleet** — D-11 caps FastMCP protocol testing at ONE smoke test. If FastMCP client proves robust, expanding protocol-level coverage is a v2 effort.
- **Mock boundary at SQLite level (in-memory DB)** — rejected (D-14). Real SQLite in `tmp_path` catches schema and WAL interaction bugs that in-memory mode hides.
- **pytest-xdist parallelism** — already listed as rejected in REQUIREMENTS.md v2. Not revisited.
- **pytest-freezer for deterministic time-dependent tests** — listed as v2 in REQUIREMENTS.md. If Phase 2 test work surfaces flaky time-based tests, flag for v2, don't add now.
- **Coverage trend tracking in CI** — v2 per REQUIREMENTS.md.
- **Test for `AppContext` secondary god object concerns** — `AppContext` decomposition is listed as v2. Phase 2 tests use the current `AppContext` as-is.

</deferred>

---

*Phase: 02-test-safety-net*
*Context gathered: 2026-04-13*
