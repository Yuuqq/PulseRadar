---
phase: 02-test-safety-net
plan: 03
subsystem: testing
tags:
  - testing
  - crawler
  - responses-mocking
requirements:
  - TEST-03
  - COV-03
dependency_graph:
  requires:
    - 02-01 (responses dev dep, pytest-cov, pytest-randomly installed)
    - 02-02 (shared fixture library at tests/conftest.py)
  provides:
    - 18 mock-based crawler plugin tests covering all 9 plugins (happy + error mode each)
    - tests/crawler/_helpers.py shared assertion helpers reusable by future crawler tests
    - tests/crawler/ + tests/crawler/plugins/ nested package structure (D-25 scaffolding)
  affects:
    - tests/ directory structure (adds tests/__init__.py to shadow Anaconda site-packages tests pkg)
tech-stack:
  added: []
  patterns:
    - "@responses.activate decorator per test (simpler than the mock_http_response fixture for per-test HTTP stubs)"
    - "Inline Python dict/string fixtures (per D-23; no external yaml/json fixture files)"
    - "from tests.crawler._helpers import ... (cross-file helper import via tests/__init__.py)"
key-files:
  created:
    - tests/__init__.py
    - tests/crawler/__init__.py
    - tests/crawler/_helpers.py
    - tests/crawler/plugins/__init__.py
    - tests/crawler/plugins/test_dailyhot.py
    - tests/crawler/plugins/test_eastmoney.py
    - tests/crawler/plugins/test_gnews.py
    - tests/crawler/plugins/test_mediastack.py
    - tests/crawler/plugins/test_newsapi.py
    - tests/crawler/plugins/test_thenewsapi.py
    - tests/crawler/plugins/test_tonghuashun.py
    - tests/crawler/plugins/test_vvhan.py
    - tests/crawler/plugins/test_wallstreetcn.py
  modified: []
decisions:
  - "Used @responses.activate decorator on every test function (simpler than consuming mock_http_response fixture from conftest for per-test URL stubs)"
  - "Added tests/__init__.py BEYOND the plan's files_modified list as a [Rule 3 - Blocker] fix: a site-packages tests package in Anaconda shadows the project-local tests dir without it, causing 'No module named tests.crawler' at import time"
  - "Locked current behavior for vvhan empty data (CrawlResult.success == False because items is empty AND errors contains '[VvhanPlugin] 全平台聚合返回空数据') — no plugin code change"
  - "Locked current behavior for tonghuashun malformed HTML (CrawlResult.success == False via '解析后无有效条目' error message) — no plugin code change"
  - "Used plugin.close() in every test finally-block to release the requests.Session — prevents ResourceWarning when pytest-randomly randomizes test order"
metrics:
  duration: ~30min
  completed: 2026-04-14
---

# Phase 02 Plan 03: Crawler Plugin Mock Tests Summary

Added 18 mock-based unit tests (2 per plugin × 9 plugins) under `tests/crawler/plugins/` plus shared assertion helpers under `tests/crawler/_helpers.py`. Every test uses the `responses` library via `@responses.activate` for deterministic offline HTTP mocking. All tests verified passing via a lightweight module-loader runner that sidesteps the known slow `trendradar/__init__.py` import chain.

## What Was Built

### Task 1: Scaffolding + shared helpers (commit `718aa280`)

Four files created:

- `tests/__init__.py` — one-line `# coding=utf-8` marker. REQUIRED deviation from the plan's files_modified list (see Deviations below).
- `tests/crawler/__init__.py` — package marker.
- `tests/crawler/plugins/__init__.py` — package marker.
- `tests/crawler/_helpers.py` — three assertion helpers reusable across all crawler plugin tests:
  - `assert_fetched_item_shape(item)` — FetchedItem type and non-empty title check
  - `assert_crawl_result_success(result, min_items=1)` — CrawlResult success + item-count + per-item shape
  - `assert_crawl_result_error(result)` — CrawlResult failure + non-empty errors tuple + empty items tuple

### Task 2: 9 plugin test files (commit `c67d0063`)

Each of the 9 crawler plugins has a dedicated test file with exactly 1 happy-path test and 1 error-mode test. Every test uses `@responses.activate` and imports the shared helpers.

**Per-plugin error mode chosen (per RESEARCH.md §Q1 table):**

| Plugin | Error mode | Plugin line / mechanism |
|--------|-----------|---|
| DailyHotPlugin | HTTP 500 | `raise_for_status` raises → caught in `_get_json` → returns None → `_parse_payload` returns {} → error branch |
| EastMoneyPlugin | Malformed JS wrapper | `_parse_response` catches `json.JSONDecodeError` → returns [] → "解析后无有效条目" error |
| GNewsPlugin | Missing api_key | Early-return at `fetch()` top without any HTTP call — test registers NO URL |
| MediaStackPlugin | HTTP 500 | `raise_for_status` raises → caught → returns error tuple with "HTTP 500: {}" |
| NewsAPIPlugin | status=error (HTTP 200) | `data.get("status") != "ok"` branch |
| TheNewsAPIPlugin | Missing api_key | Early-return at `fetch()` top — test registers NO URL |
| TongHuaShunPlugin | Malformed HTML | `_parse_html` returns [] because no `<div class="article"` block in body |
| VvhanPlugin | Empty data dict | `_fetch_all` returns {} → flatten produces 0 items → "[VvhanPlugin] 全平台聚合返回空数据" error |
| WallStreetCNPlugin | code=40000 (HTTP 200) | `data.get("code") != 20000` branch with "API 返回非预期状态码: 40000" error |

## Task Commits

| Task | Description | Commit |
|------|-------------|--------|
| 1 | Crawler test scaffolding and shared helpers | `718aa280` |
| 2 | 9 per-plugin test files using responses library | `c67d0063` |

## Files Created

All under `tests/`:

- `tests/__init__.py` (new — see deviation)
- `tests/crawler/__init__.py`
- `tests/crawler/_helpers.py`
- `tests/crawler/plugins/__init__.py`
- `tests/crawler/plugins/test_dailyhot.py` (2 tests)
- `tests/crawler/plugins/test_eastmoney.py` (2 tests)
- `tests/crawler/plugins/test_gnews.py` (2 tests)
- `tests/crawler/plugins/test_mediastack.py` (2 tests)
- `tests/crawler/plugins/test_newsapi.py` (2 tests)
- `tests/crawler/plugins/test_thenewsapi.py` (2 tests)
- `tests/crawler/plugins/test_tonghuashun.py` (2 tests)
- `tests/crawler/plugins/test_vvhan.py` (2 tests)
- `tests/crawler/plugins/test_wallstreetcn.py` (2 tests)

Total: **18 new test functions** across 9 plugin files.

## Deviations from Plan

### 1. [Rule 3 - Blocker] Added `tests/__init__.py` beyond the files_modified list

**Found during:** Task 1 verification. The plan's acceptance criterion `python -c "from tests.crawler._helpers import assert_fetched_item_shape"` failed with `ModuleNotFoundError: No module named 'tests.crawler'`.

**Root cause:** The Anaconda base Python environment has a `tests` package installed under `C:\Users\AD\anaconda3\Lib\site-packages\tests` (likely from pytest or stdlib test helpers). When `import tests` resolves via sys.path, it picks up the site-packages one in preference to the project-local `tests/` directory because the latter lacks an `__init__.py` and isn't recognized as a package by the regular import machinery under the current import mode.

**Fix:** Created `tests/__init__.py` with a single `# coding=utf-8` line. With the project root on sys.path (via the existing bootstrap in `tests/conftest.py` lines 8-11), local `tests` now resolves to the project directory because it's a real package.

**Files modified:** `tests/__init__.py` (1 new file, 1 line).

**Commit:** `718aa280` (folded into Task 1).

**Why this is Rule 3 and not Rule 4:** It's a drop-in addition that doesn't change any existing code path, doesn't alter imports in any pre-existing test file (none of them used `from tests.X` imports), and doesn't touch `trendradar/` or `mcp_server/`. It's the minimum fix needed to make the plan's own acceptance criterion executable.

### 2. [Rule 1 - Bug] Vvhan happy-path response shape correction

**Found during:** Task 2 planning. The plan's inline fixture for `test_vvhan_happy_path` specified `"data":[{"name":"PlatformA","data":[...]}]` (a list of platform dicts), but inspection of `trendradar/crawler/plugins/vvhan.py` `_fetch_all` (line 68-86) shows the plugin iterates `data.get("data", {}).items()` — it expects a DICT `{platform: [items]}`, not a list.

**Fix:** Used the correct shape in the fixture: `{"success": True, "data": {"PlatformA": [{"title": "VVH News", "url": "http://vvh.com"}]}}`. Per Pitfall 1 (lock current behavior), the test fixture matches the plugin's actual parsing contract rather than forcing a plugin change.

**Files modified:** `tests/crawler/plugins/test_vvhan.py` only. No plugin code modified.

### 3. Minor: Locked `CrawlResult.success` semantics

**Finding during Task 2:** `trendradar/crawler/base.py` line 28 defines `CrawlResult.success` as `len(self.errors) == 0 and len(self.items) > 0`. Both conditions required. This means the Vvhan empty-data scenario and TongHuaShun malformed-HTML scenario cannot possibly be "success with empty items" — they MUST be either real successes or errors. Both plugins correctly handle empty items by appending an error message, so `assert_crawl_result_error` is the correct assertion for both.

The plan's conditional wording ("assert whichever matches current behavior, either success-empty OR failure") resolved to "failure" for both plugins. Documented here for Plan 06 baseline review.

## Offline Verification of Tests

**Known environment condition (documented in 02-01 and 02-02 SUMMARYs):** Running `pytest tests/crawler/plugins/test_X.py` in this environment hangs during collection due to the slow `trendradar/__init__.py` → `AppContext` → `litellm` → `aiohttp` import chain. Individual `pytest` invocations timed out at both 120s and 300s without producing any output. This is an environment/test-infrastructure condition that is NOT introduced by this plan; the plan's code is correct.

**Mitigation — direct execution via a lightweight module-loader bypass:** All 18 tests were executed by a small Python script that:

1. Pre-registers a bare `trendradar` package stub in `sys.modules` (empty `ModuleType`, `__path__ = ['trendradar']`) so subsequent `from trendradar.crawler.plugins.X import ...` resolves via `__path__` without triggering `trendradar/__init__.py`.
2. Stubs `trendradar.logging.get_logger` → `structlog.get_logger` and `trendradar.logging.setup_logging` → no-op.
3. Loads `trendradar.crawler.base`, `trendradar.crawler.registry`, and each plugin module via `importlib.util.spec_from_file_location` + `exec_module`.
4. For each `test_*.py` file, loads it as `tests.crawler.plugins.<name>` and calls every `test_*` function directly (each decorated with `@responses.activate` so the HTTP mock context is per-function).

**Run result (full output captured during execution):**

```
=== test_dailyhot ===
  test_dailyhot_happy_path: PASSED
  test_dailyhot_http_500: PASSED
=== test_eastmoney ===
  test_eastmoney_happy_path: PASSED
  test_eastmoney_malformed_wrapper: PASSED
=== test_gnews ===
  test_gnews_happy_path: PASSED
  test_gnews_missing_api_key: PASSED
=== test_mediastack ===
  test_mediastack_happy_path: PASSED
  test_mediastack_http_500: PASSED
=== test_newsapi ===
  test_newsapi_happy_path: PASSED
  test_newsapi_status_error: PASSED
=== test_thenewsapi ===
  test_thenewsapi_happy_path: PASSED
  test_thenewsapi_missing_api_key: PASSED
=== test_tonghuashun ===
  test_tonghuashun_happy_path: PASSED
  test_tonghuashun_malformed_html: PASSED
=== test_vvhan ===
  test_vvhan_empty_data: PASSED
  test_vvhan_happy_path: PASSED
=== test_wallstreetcn ===
  test_wallstreetcn_code_40000: PASSED
  test_wallstreetcn_happy_path: PASSED

=== Summary: 18 passed, 0 failed ===
```

**What this verifies:**

- Every happy-path test produces a `CrawlResult` with `success == True` and at least 1 `FetchedItem` whose field values flow through from the mocked HTTP response.
- Every error-mode test produces a `CrawlResult` with `success == False`, `len(errors) >= 1`, and `len(items) == 0`.
- The `responses` library successfully intercepts every `requests.Session.get` call across all 9 plugins.
- The `from tests.crawler._helpers import ...` cross-file import works (confirmed by each test passing its assertion calls).
- No test triggers an actual network call — if any HTTP call escaped `responses`, the test would fail with `ConnectionError`.

**What is NOT verified by this bypass:**

- Running under pytest's test collector directly — blocked by the slow-import env issue documented above.
- Running under `pytest-randomly` seed variation — blocked by same issue. The tests have zero shared state (each plugin constructs a fresh session in `__init__`, `plugin.close()` is called in a `finally` block, `@responses.activate` scopes the mock per-function), so randomization should be safe.

## Coverage Contribution Estimate

**Could not be measured in this plan's window** — `pytest --cov=trendradar.crawler.plugins` requires pytest to collect and run the suite, which hangs in this environment. Deferred to the full-suite verification run (likely during Plan 02-06 — phase baseline).

Expected impact based on direct inspection of the 9 plugin files:

- Each plugin: ~120 lines, ~60-70 covered lines after both tests run (happy-path covers the success branch end-to-end; error-mode covers one error branch).
- Estimated per-plugin coverage: **~55-70%** per plugin (not 100% because the fallback code paths in dailyhot/vvhan and retry-heavy branches aren't exercised by exactly one happy + one error test each — Pitfall 4 anti-coverage-padding is respected).
- Estimated package-level coverage for `trendradar.crawler.plugins.*`: **~60%** aggregate.

This is the minimum viable safety net per D-24; further expansion is v2.

## Plugins Flagged for Plan 06 Baseline Review

The tests lock current behavior exactly. Two behaviors may be worth re-evaluating during Plan 06 baseline commit (not during this plan):

1. **Vvhan empty data** — Currently surfaces empty `data: {}` as a `CrawlResult` with `success=False` and a single error "[VvhanPlugin] 全平台聚合返回空数据". An upstream API change that returns `data: {}` would surface as a crawler error, possibly noisy in logs. This is correct-as-designed — errors are how the pipeline tracks "no data to report".

2. **DailyHotPlugin single-platform HTTP 500 path** — The test uses `platform="toutiao"` which skips the multi-platform fallback. If the plugin's fallback path is ever enabled for a single-platform config, coverage gap exists. This is acceptable per D-24 (one error mode per plugin, not full matrix).

No architectural changes required. Both are explicitly deferred to Phase 3 decomposition via the Pitfall 1 "lock current behavior" mandate.

## Known Stubs

None — every test is a complete, asserting unit test. No TODO/FIXME/placeholder markers were added.

## Threat Flags

None — no new network endpoints, authentication paths, file-system access patterns, or schema changes introduced. `tests/__init__.py` is a one-line marker file. All HTTP calls are mocked.

## Self-Check: PASSED

**Files verified on disk:**

- FOUND: tests/__init__.py (1 line, `# coding=utf-8`)
- FOUND: tests/crawler/__init__.py
- FOUND: tests/crawler/_helpers.py (parses, 3 assertion functions defined)
- FOUND: tests/crawler/plugins/__init__.py
- FOUND: tests/crawler/plugins/test_dailyhot.py (2 test functions)
- FOUND: tests/crawler/plugins/test_eastmoney.py (2 test functions)
- FOUND: tests/crawler/plugins/test_gnews.py (2 test functions)
- FOUND: tests/crawler/plugins/test_mediastack.py (2 test functions)
- FOUND: tests/crawler/plugins/test_newsapi.py (2 test functions)
- FOUND: tests/crawler/plugins/test_thenewsapi.py (2 test functions)
- FOUND: tests/crawler/plugins/test_tonghuashun.py (2 test functions)
- FOUND: tests/crawler/plugins/test_vvhan.py (2 test functions)
- FOUND: tests/crawler/plugins/test_wallstreetcn.py (2 test functions)
- FOUND: .planning/phases/02-test-safety-net/02-03-SUMMARY.md (this file)

**Commits verified in git log:**

- FOUND: 718aa280 test(02-03): add crawler test scaffolding and shared helpers
- FOUND: c67d0063 test(02-03): add mock-based tests for 9 crawler plugins

**Acceptance-criteria grep counts (from Grep tool):**

- `@responses.activate` → 18 total (2 per file × 9 files) ✓
- `from tests.crawler._helpers import` → 9 total (1 per file × 9 files) ✓
- `assert_crawl_result_success OR assert_crawl_result_error` → 36 total (imports + usage × 2 tests × 9 files) ✓
- `^# coding=utf-8` → 10 total (9 test files + tests/crawler/plugins/__init__.py; helpers/__init__ similarly encoded) ✓
- `def test_` function count via AST → 18 total (2 per test file × 9 files) ✓

**Direct-execution verification:**

- 18 of 18 test functions executed to completion without raising — full output captured above under "Run result".
- No `ConnectionError` raised by `responses` library (verified: no URL escaped the mock registry).

All acceptance criteria from the plan that CAN be checked without running the full pytest collector are satisfied. The remaining two criteria (`pytest --collect-only -q` collection count and `pytest -x --no-cov` pass signal) are deferred to Plan 02-06's baseline run due to the pre-existing slow-import env condition shared with 02-01 and 02-02.

---

*Phase: 02-test-safety-net*
*Plan: 03*
*Completed: 2026-04-14*
