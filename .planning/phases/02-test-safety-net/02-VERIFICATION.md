---
phase: 02-test-safety-net
verified: 2026-04-15T09:30:00Z
status: gaps_found
score: 5/6 must-haves verified
overrides_applied: 0
gaps:
  - truth: "Running `pytest` reports coverage with branch coverage enabled and fails the run if coverage drops below 80%"
    status: partial
    reason: "Coverage infrastructure is fully wired (branch=true, --cov-fail-under=80 in pyproject.toml addopts, dual-package source). However, actual coverage is ~28%, so `pytest` exits non-zero on every run due to the 80% gate. The gate is technically working as designed (it DOES fail below 80%), but the COV-05 requirement ('Overall test coverage reaches 80%+ with branch coverage enabled') is not met. The codebase has 13,171 statements; covering 80% would require ~10,500 exercised lines, far beyond what the safety-net scope produced."
    artifacts:
      - path: "pyproject.toml"
        issue: "Coverage gate configured correctly at 80%, but actual coverage is only ~28%"
    missing:
      - "COV-05: Overall coverage must reach 80%+ -- current level is ~28% with 235 tests across both packages"
      - "Decision needed: lower the gate to ~30% as a ratchet (preventing regression), keep at 80% as aspirational, or remove fail-under entirely and rely on baseline comparison"
---

# Phase 2: Test Safety Net Verification Report

**Phase Goal:** A developer can run one command, see measured coverage, and trust that the MCP server, every crawler plugin, and the full pipeline are verified against current behavior -- so structural refactors in Phase 3 are safe
**Verified:** 2026-04-15T09:30:00Z
**Status:** gaps_found
**Re-verification:** No -- initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Running `pytest` reports coverage with branch coverage enabled and fails the run if coverage drops below 80% | PARTIAL | `pyproject.toml` addopts = `--cov=trendradar --cov=mcp_server --cov-fail-under=80`, branch = true. Configuration is correct. But actual coverage is ~28%, so `pytest` always exits non-zero. COV-05 (80%+) is not met. |
| 2 | A baseline coverage number exists on record (committed artifact or documented in Phase 2 summary) taken before any refactor touches `NewsAnalyzer` | VERIFIED | coverage.xml committed at `e0945a2c`, retrievable via `git show e0945a2c:coverage.xml`. Per-module table documented in 02-06-SUMMARY.md. Baseline: 26.69% (13,171 stmts). |
| 3 | Every MCP server tool module and service module has unit tests that exercise its public surface; running them does not require a live MCP client | VERIFIED | 7 tool test files (test_analytics.py, test_article_reader.py, test_config_mgmt.py, test_data_query.py, test_search_tools.py, test_storage_sync.py, test_system.py) + 3 service test files (test_cache_service.py, test_data_service.py, test_parser_service.py) + 1 smoke test = 66 tests, all passing in 11.98s. FastMCP smoke test passes in-process (no live client). |
| 4 | Every crawler plugin has tests that use the `responses` library to mock HTTP, so the full test suite runs offline and deterministically | VERIFIED | 9 plugin test files (one per plugin), each with `@responses.activate` on every test function. 18 tests total (2 per plugin: happy + error). All pass in ~10s. All 9 files import from `tests.crawler._helpers`. |
| 5 | A pipeline integration test exercises crawl to store to analyze to report to notify for all three report modes (incremental, current, daily) and passes against the current (still-monolithic) `NewsAnalyzer` | VERIFIED | `tests/pipeline/test_mode_strategy.py` has 5 named test functions covering all 5 branches: incremental+data, current+history, current-no-history->RuntimeError, daily+history, daily-no-history->fallback. Additionally: `test_extra_api_merge.py` (2 tests), `test_analyze_trends_dead_code.py` (1 test). All 8 pipeline tests pass. |
| 6 | A shared `conftest.py` exposes `mock_config`, `mock_app_context`, and `mock_http_response` fixtures that new tests can reuse without duplication | VERIFIED | `tests/conftest.py` (109 lines) contains all three named fixtures plus autouse `_reset_storage_singleton`. `mock_config` returns 22-key UPPERCASE dict with tmp_path-backed storage. `mock_app_context` instantiates REAL AppContext. `mock_http_response` wraps `responses.RequestsMock`. |

**Score:** 5/6 truths verified (1 partial)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `pyproject.toml` | Coverage + dev deps config | VERIFIED | addopts, branch=true, source=["trendradar","mcp_server"], fail-under=80, coverage.xml output, dev group with pytest-cov/responses/pytest-randomly |
| `requirements-dev.txt` | Regenerated dev deps mirror | VERIFIED | 381 lines, auto-generated header, contains pytest==8.4.2, pytest-cov==7.1.0, responses==0.26.0, pytest-randomly==4.0.1, coverage==7.13.5 |
| `.gitignore` | coverage.xml exclusion | VERIFIED | Contains `coverage.xml` and `.coverage` entries; all original entries preserved |
| `tests/conftest.py` | Shared fixture library | VERIFIED | 109 lines, 3 named fixtures + autouse singleton reset, sys.path bootstrap preserved |
| `tests/crawler/_helpers.py` | Shared assertion helpers | VERIFIED | 31 lines, 3 helpers: assert_fetched_item_shape, assert_crawl_result_success, assert_crawl_result_error |
| `tests/crawler/plugins/test_*.py` | 9 plugin test files | VERIFIED | All 9 exist, each with @responses.activate, import shared helpers, have happy+error tests |
| `tests/mcp/test_smoke.py` | FastMCP in-process smoke test | VERIFIED | 61 lines, 2 test functions, asyncio.run() pattern, passes directly |
| `tests/mcp/conftest.py` | MCP singleton reset | VERIFIED | 21 lines, autouse _reset_mcp_tools_instances fixture |
| `tests/mcp/tools/test_*.py` | 7 tool test files | VERIFIED | All 7 exist, each imports from mcp_server.tools.*, has concrete assertions |
| `tests/mcp/services/test_*.py` | 3 service test files | VERIFIED | All 3 exist, each imports from mcp_server.services.*, has concrete assertions |
| `tests/pipeline/conftest.py` | Pipeline-specific fixtures | VERIFIED | 148 lines, pipeline_config, pipeline_ctx, sample_results, html_report_factory, mock_callbacks |
| `tests/pipeline/test_mode_strategy.py` | 5-case mode strategy test | VERIFIED | 356 lines, 5 test functions covering all 3 report modes, HTML content checks, notification kwargs assertions |
| `tests/pipeline/test_extra_api_merge.py` | Extra-API merge shape lock | VERIFIED | 114 lines, 2 tests (basic merge + duplicate title rank append) |
| `tests/pipeline/test_analyze_trends_dead_code.py` | Dead code lock (Pitfall 8) | VERIFIED | 53 lines, static inspection verifying _analyze_trends result not passed to _execute_mode_strategy |
| `coverage.xml` | Committed baseline | VERIFIED | Committed at e0945a2c (674KB), retrievable via `git show e0945a2c:coverage.xml` |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| pyproject.toml addopts | coverage.run source | pytest-cov reads both sections | WIRED | `--cov=trendradar --cov=mcp_server` in addopts matches `source = ["trendradar", "mcp_server"]` in coverage.run |
| pyproject.toml dev group | requirements-dev.txt | uv pip compile | WIRED | All 4 dev deps present in lockfile with pinned versions |
| tests/conftest.py mock_app_context | trendradar.context.AppContext | Real instantiation | WIRED | `from trendradar.context import AppContext; return AppContext(mock_config)` |
| tests/conftest.py autouse reset | trendradar.storage.manager._storage_manager | Module attribute set to None | WIRED | `import trendradar.storage.manager as _sm; _sm._storage_manager = None` before/after yield |
| tests/crawler/plugins/test_*.py | responses library | @responses.activate decorator | WIRED | All 9 files use decorator, 18 total @responses.activate occurrences |
| tests/crawler/plugins/test_*.py | tests/crawler/_helpers.py | from tests.crawler._helpers import | WIRED | All 9 files import shared helpers |
| tests/mcp/tools/test_*.py | mcp_server/tools/*.py | Direct tool class import | WIRED | Each test file imports its corresponding tool class |
| tests/mcp/services/test_*.py | mcp_server/services/*.py | Direct service class import | WIRED | Each test file imports its corresponding service class |
| tests/mcp/test_smoke.py | mcp_server/server.py | fastmcp.Client(mcp) in-process | WIRED | `from mcp_server.server import mcp; async with Client(mcp) as client` |
| tests/pipeline/test_mode_strategy.py | trendradar/core/mode_strategy.py | direct import + call | WIRED | `from trendradar.core.mode_strategy import execute_mode_strategy` |
| .gitignore | coverage.xml | git ignores post-baseline | WIRED | `coverage.xml` line present in .gitignore |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All dev deps importable | `python -c "import pytest_cov; import responses; import pytest_randomly"` | All importable | PASS |
| pyproject.toml valid TOML with all keys | tomllib parse + 6 assertions | All assertions passed | PASS |
| Crawler + pipeline tests pass | `pytest tests/crawler/plugins/ tests/pipeline/ -x --no-cov -p no:randomly` | 26 passed in 10.19s | PASS |
| MCP tests pass | `pytest tests/mcp/ -x --no-cov -p no:randomly` | 66 passed in 11.98s | PASS |
| Full suite (no cov gate) | `pytest tests/ --no-cov -p no:randomly` | 234 passed, 1 failed (pre-existing) in 21.74s | PASS |
| Coverage baseline in git | `git show e0945a2c:coverage.xml` | Valid XML, coverage 7.13.5 | PASS |
| Test collection count | `pytest tests/ --collect-only -q -p no:randomly` | 235 tests collected | PASS |
| Actual coverage level | `pytest tests/ --override-ini="addopts=" --cov=trendradar --cov=mcp_server` | TOTAL: 28% | INFO (below 80% gate) |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| TEST-01 | 02-01 | pytest-cov configured with --cov-fail-under=80 and branch coverage | SATISFIED | pyproject.toml verified: addopts, branch=true, source, fail-under=80 |
| TEST-02 | 02-06 | Coverage baseline measured and recorded before refactor | SATISFIED | coverage.xml at e0945a2c; per-module table in 02-06-SUMMARY.md; 26.69% baseline |
| TEST-03 | 02-01, 02-03 | responses library added as dev dep and usable for mocking HTTP | SATISFIED | In dev group + 18 crawler tests + ArticleReader tests use @responses.activate |
| TEST-04 | 02-02 | Shared conftest.py exposes mock_config, mock_app_context, mock_http_response | SATISFIED | tests/conftest.py has all three fixtures + autouse singleton reset |
| COV-01 | 02-04 | MCP server unit tests for all 7 tool modules | SATISFIED | 7 test files, 31 tool tests + 2 smoke tests, all passing |
| COV-02 | 02-04 | MCP server unit tests for all 3 service modules | SATISFIED | 3 test files, 33 service tests, all passing |
| COV-03 | 02-03 | Crawler plugins have mock-based tests for all 9 plugins | SATISFIED | 9 test files, 18 tests (2 per plugin), all @responses.activate |
| COV-04 | 02-05 | Pipeline integration test covers all 3 report modes | SATISFIED | 5 mode-strategy tests + 2 merge tests + 1 dead code test = 8 tests |
| COV-05 | 02-01, 02-06 | Overall test coverage reaches 80%+ with branch coverage enabled | BLOCKED | Actual coverage is ~28% (13,171 stmts). 80% gate configured but not achievable with current test count. |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| tests/mcp/test_smoke.py | 39 | pytest.skip for FastMCP fallback | Info | By design (D-11 fallback pattern). Test actually passes; skip is only a safety net. |
| tests/test_crawler_registry.py | 88 | Pre-existing test failure (singleton contamination) | Warning | Not introduced by Phase 2. CrawlerRegistry.discover() returns 0 plugins when run after other tests. Passes in isolation. |

### Human Verification Required

### 1. Full Test Suite Under pytest-randomly

**Test:** Run `pytest tests/ --no-cov` multiple times (without `-p no:randomly`) to verify no cross-test coupling under random ordering.
**Expected:** All tests pass regardless of order (except the pre-existing test_discover_finds_all_builtin_plugins failure).
**Why human:** The environment has a known `thinc` library seed overflow issue with pytest-randomly that blocks automated verification.

### 2. Coverage Gate Behavior on Fresh Clone

**Test:** On a fresh clone, run `pip install -e ".[dev]" && pytest` to verify the 80% gate triggers.
**Expected:** pytest exits non-zero with "FAIL Required test coverage of 80% not reached" message.
**Why human:** Verifier ran tests with --no-cov to separate coverage gate behavior from test pass/fail. Need human to confirm the integrated experience.

### 3. Docker Test Suite Compatibility

**Test:** Build the Docker image and verify `pytest tests/ --no-cov` passes inside the container.
**Expected:** All tests pass (dev deps must be available in the container).
**Why human:** Docker environment differs from local Anaconda; cannot verify programmatically from the verifier environment.

### Gaps Summary

**One gap blocks full phase completion:**

**COV-05 (80% coverage gate):** The coverage infrastructure is fully wired and working correctly -- `pytest` DOES report coverage with branch coverage enabled, and it DOES fail when coverage is below 80%. The problem is that actual coverage is only ~28% (13,171 statements across both packages), far below the 80% threshold. This means `pytest` exits non-zero on every run, which breaks the phase goal of "a developer can run one command" for a clean pass.

The 80% gate was configured as per TEST-01 requirements, but achieving 80% coverage would require ~10,500 exercised lines (vs. the ~4,133 currently covered). The Phase 2 safety-net tests added ~92 new tests across MCP, crawler, and pipeline subsystems, but the codebase volume (notification channels, storage backends, report generation, webui, utils) dwarfs what targeted safety-net tests can cover.

**Root cause:** The COV-05 requirement ("Overall test coverage reaches 80%+ with branch coverage enabled") was aspirational for the Phase 2 scope. The 02-06-SUMMARY documents this honestly: "The 80% gate was aspirational for Phase 2; achieving it requires substantial additional test investment beyond the safety-net scope."

**Decision needed from developer:**
1. **Lower the gate** to current level + margin (e.g., `--cov-fail-under=30`) as a ratchet preventing regression during Phase 3
2. **Keep at 80%** as aspirational but accept pytest exits non-zero (developers use `--no-cov` or `--override-ini` to skip)
3. **Remove fail-under** and rely on the committed baseline comparison for Phase 3 regression detection

**Note:** The coverage gate configuration (TEST-01) is distinct from the coverage level (COV-05). TEST-01 IS satisfied -- the gate is configured. COV-05 is NOT satisfied -- the level does not reach 80%.

---

_Verified: 2026-04-15T09:30:00Z_
_Verifier: Claude (gsd-verifier)_
