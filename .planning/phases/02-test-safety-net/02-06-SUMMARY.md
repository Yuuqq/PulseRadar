---
phase: 02-test-safety-net
plan: 06
subsystem: testing
tags:
  - testing
  - coverage
  - baseline
  - pytest-cov

# Dependency graph
requires:
  - phase: 02-01
    provides: pytest-cov configured in pyproject.toml with --cov-fail-under=80 and branch coverage
  - phase: 02-02
    provides: shared fixture library with mock_config, mock_app_context, singleton reset
  - phase: 02-03
    provides: 18 crawler plugin tests contributing to coverage
  - phase: 02-04
    provides: 66 MCP server tests contributing to coverage
  - phase: 02-05
    provides: pipeline integration tests (executing in parallel, may not be in baseline)
provides:
  - coverage.xml baseline artifact committed at e0945a2c (retrievable via git show e0945a2c:coverage.xml)
  - Per-module coverage table with branch coverage metrics
  - .gitignore updated to exclude coverage.xml and .coverage from future commits
affects:
  - Phase 3 (decomposition compares post-refactor coverage against this baseline)
  - Phase 4 (CI enforcement of coverage gate)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "D-05 two-commit baseline workflow: commit coverage.xml first, then gitignore + untrack"
    - "Coverage baseline retrievable via git show <sha>:coverage.xml for regression comparison"

key-files:
  created: []
  modified:
    - .gitignore

key-decisions:
  - "Coverage baseline is 26.69% (not 80%) -- this is the honest pre-refactor measurement with branch coverage enabled"
  - "80% gate NOT lowered -- documented as gap requiring future test additions"
  - "Also gitignored .coverage binary cache (pytest-cov runtime artifact) alongside coverage.xml"
  - "Plan 02-05 executing in parallel -- baseline may be slightly lower than final Phase 2 number"

patterns-established:
  - "Pattern: D-05 coverage baseline workflow -- commit XML once as locked artifact, then gitignore to prevent churn"

requirements-completed: [TEST-02]

# Metrics
duration: 8min
completed: 2026-04-14
---

# Phase 02 Plan 06: Coverage Baseline Summary

**Coverage baseline captured at 26.69% (13171 stmts, 4892 branches) with branch coverage enabled -- committed as locked artifact at e0945a2c for Phase 3 regression comparison**

## Performance

- **Duration:** 8 min
- **Started:** 2026-04-14T11:57:03Z
- **Completed:** 2026-04-14T12:05:33Z
- **Tasks:** 2
- **Files modified:** 2 (.gitignore, coverage.xml)

## Accomplishments

- Full test suite executed: 227 tests collected, 226 passed, 1 pre-existing failure (singleton isolation in test_discover_finds_all_builtin_plugins)
- Coverage.xml baseline committed at e0945a2c with 674KB of line-level and branch-level coverage data
- .gitignore updated to exclude both coverage.xml and .coverage from future commits
- Per-module coverage table captured below for human-readable reference

## Task Commits

Each task was committed atomically:

1. **Task 1+2a: Commit coverage baseline artifact** - `e0945a2c` (docs)
2. **Task 2b: Gitignore coverage.xml and .coverage** - `abbdd07a` (chore)

## Overall Coverage Summary

| Metric | Value |
|--------|-------|
| **Overall Coverage** | **26.69%** |
| Total Statements | 13,171 |
| Statements Missed | 9,038 |
| Total Branches | 4,892 |
| Branch Partial | 318 |
| Tests Collected | 227 |
| Tests Passed | 226 |
| Tests Failed | 1 (pre-existing) |
| Coverage Engine | coverage.py 7.13.5 |

## Per-Module Coverage Table (THE Baseline - TEST-02)

### trendradar package

| Module | Stmts | Miss | Branch | BrPart | Cover |
|--------|-------|------|--------|--------|-------|
| trendradar/\_\_init\_\_.py | 12 | 0 | 0 | 0 | 100% |
| trendradar/\_\_main\_\_.py | 476 | 358 | 178 | 15 | 20% |
| trendradar/ai/\_\_init\_\_.py | 5 | 0 | 0 | 0 | 100% |
| trendradar/ai/analyzer.py | 176 | 161 | 78 | 1 | 5% |
| trendradar/ai/client.py | 56 | 30 | 18 | 2 | 41% |
| trendradar/ai/formatter.py | 72 | 31 | 30 | 7 | 55% |
| trendradar/ai/translator.py | 73 | 55 | 20 | 1 | 20% |
| trendradar/context.py | 103 | 34 | 42 | 7 | 63% |
| trendradar/core/\_\_init\_\_.py | 5 | 0 | 0 | 0 | 100% |
| trendradar/core/analyzer.py | 65 | 37 | 30 | 2 | 36% |
| trendradar/core/config.py | 128 | 97 | 42 | 2 | 19% |
| trendradar/core/frequency.py | 98 | 27 | 34 | 5 | 71% |
| trendradar/core/mode_strategy.py | 121 | 80 | 32 | 7 | 26% |
| trendradar/core/pipeline.py | 113 | 45 | 38 | 9 | 55% |
| trendradar/core/trend.py | 119 | 5 | 52 | 6 | 93% |
| trendradar/crawler/\_\_init\_\_.py | 2 | 0 | 0 | 0 | 100% |
| trendradar/crawler/base.py | 54 | 3 | 12 | 2 | 93% |
| trendradar/crawler/extra_apis.py | 100 | 77 | 36 | 1 | 20% |
| trendradar/crawler/fetcher.py | 187 | 139 | 66 | 1 | 21% |
| trendradar/crawler/middleware/\_\_init\_\_.py | 2 | 0 | 0 | 0 | 100% |
| trendradar/crawler/middleware/circuit_breaker.py | 37 | 21 | 14 | 1 | 39% |
| trendradar/crawler/middleware/rate_limiter.py | 20 | 9 | 2 | 0 | 50% |
| trendradar/crawler/plugins/\_\_init\_\_.py | 2 | 0 | 0 | 0 | 100% |
| trendradar/crawler/plugins/dailyhot.py | 62 | 7 | 20 | 6 | 81% |
| trendradar/crawler/plugins/eastmoney.py | 59 | 7 | 16 | 3 | 82% |
| trendradar/crawler/plugins/gnews.py | 45 | 6 | 14 | 3 | 80% |
| trendradar/crawler/plugins/mediastack.py | 47 | 7 | 14 | 2 | 80% |
| trendradar/crawler/plugins/newsapi.py | 46 | 7 | 12 | 2 | 79% |
| trendradar/crawler/plugins/thenewsapi.py | 50 | 5 | 16 | 4 | 84% |
| trendradar/crawler/plugins/tonghuashun.py | 64 | 14 | 22 | 4 | 73% |
| trendradar/crawler/plugins/vvhan.py | 58 | 14 | 22 | 3 | 72% |
| trendradar/crawler/plugins/wallstreetcn.py | 53 | 7 | 14 | 4 | 80% |
| trendradar/crawler/pool.py | 92 | 71 | 30 | 1 | 18% |
| trendradar/crawler/registry.py | 66 | 38 | 26 | 3 | 38% |
| trendradar/crawler/rss/\_\_init\_\_.py | 2 | 0 | 0 | 0 | 100% |
| trendradar/crawler/rss/feed_parser.py | 47 | 34 | 12 | 1 | 22% |
| trendradar/crawler/rss/rss_fetcher.py | 204 | 159 | 76 | 1 | 17% |
| trendradar/logging/\_\_init\_\_.py | 2 | 0 | 0 | 0 | 100% |
| trendradar/logging/setup.py | 56 | 14 | 10 | 3 | 72% |
| trendradar/models/\_\_init\_\_.py | 1 | 0 | 0 | 0 | 100% |
| trendradar/models/config.py | 227 | 80 | 42 | 10 | 62% |
| trendradar/notification/\_\_init\_\_.py | 6 | 0 | 0 | 0 | 100% |
| trendradar/notification/batch.py | 143 | 112 | 48 | 0 | 11% |
| trendradar/notification/channels/\_\_init\_\_.py | 2 | 0 | 0 | 0 | 100% |
| trendradar/notification/channels/bark.py | 47 | 37 | 12 | 0 | 14% |
| trendradar/notification/channels/custom_webhook.py | 97 | 87 | 32 | 0 | 6% |
| trendradar/notification/channels/dingtalk.py | 45 | 35 | 12 | 0 | 15% |
| trendradar/notification/channels/email.py | 87 | 73 | 20 | 0 | 12% |
| trendradar/notification/channels/feishu.py | 44 | 34 | 12 | 0 | 15% |
| trendradar/notification/channels/pushplus.py | 29 | 20 | 4 | 0 | 22% |
| trendradar/notification/channels/serverchan.py | 30 | 21 | 4 | 0 | 21% |
| trendradar/notification/channels/slack.py | 52 | 42 | 14 | 0 | 12% |
| trendradar/notification/channels/telegram.py | 50 | 39 | 14 | 0 | 14% |
| trendradar/notification/dispatcher.py | 96 | 51 | 32 | 7 | 41% |
| trendradar/notification/push_manager.py | 141 | 108 | 54 | 3 | 20% |
| trendradar/notification/renderer.py | 107 | 67 | 52 | 9 | 44% |
| trendradar/notification/splitter.py | 65 | 34 | 20 | 3 | 42% |
| trendradar/report/\_\_init\_\_.py | 5 | 0 | 0 | 0 | 100% |
| trendradar/report/formatter.py | 136 | 116 | 100 | 7 | 11% |
| trendradar/report/generator.py | 75 | 69 | 34 | 0 | 6% |
| trendradar/report/helpers.py | 57 | 31 | 30 | 8 | 39% |
| trendradar/report/html.py | 133 | 125 | 72 | 0 | 4% |
| trendradar/report/html_scripts.py | 1 | 0 | 0 | 0 | 100% |
| trendradar/report/html_sections.py | 216 | 207 | 102 | 0 | 3% |
| trendradar/report/html_styles.py | 1 | 0 | 0 | 0 | 100% |
| trendradar/report/rss_html.py | 48 | 48 | 20 | 0 | 0% |
| trendradar/storage/\_\_init\_\_.py | 11 | 3 | 0 | 0 | 73% |
| trendradar/storage/base.py | 141 | 79 | 38 | 0 | 35% |
| trendradar/storage/local.py | 262 | 206 | 88 | 1 | 16% |
| trendradar/storage/manager.py | 156 | 84 | 44 | 6 | 40% |
| trendradar/storage/remote.py | 404 | 341 | 116 | 0 | 12% |
| trendradar/storage/sqlite_mixin.py | 510 | 479 | 162 | 0 | 5% |
| trendradar/utils/\_\_init\_\_.py | 3 | 0 | 0 | 0 | 100% |
| trendradar/utils/time.py | 179 | 159 | 66 | 0 | 8% |
| trendradar/utils/url.py | 30 | 24 | 12 | 0 | 14% |
| trendradar/webui/\_\_init\_\_.py | 2 | 0 | 0 | 0 | 100% |
| trendradar/webui/\_\_main\_\_.py | 11 | 11 | 0 | 0 | 0% |
| trendradar/webui/app.py | 37 | 3 | 0 | 0 | 92% |
| trendradar/webui/helpers.py | 204 | 28 | 62 | 15 | 83% |
| trendradar/webui/job_manager.py | 482 | 154 | 144 | 33 | 63% |
| trendradar/webui/routes_config.py | 75 | 51 | 24 | 0 | 24% |
| trendradar/webui/routes_jobs.py | 139 | 17 | 34 | 9 | 85% |
| trendradar/webui/routes_misc.py | 118 | 97 | 28 | 1 | 15% |
| trendradar/webui/routes_pages.py | 37 | 7 | 0 | 0 | 81% |
| trendradar/webui/routes_workflow.py | 90 | 18 | 12 | 4 | 78% |

### mcp_server package

| Module | Stmts | Miss | Branch | BrPart | Cover |
|--------|-------|------|--------|--------|-------|
| mcp_server/\_\_init\_\_.py | 0 | 0 | 0 | 0 | 100% |
| mcp_server/server.py | 273 | 234 | 28 | 0 | 20% |
| mcp_server/services/\_\_init\_\_.py | 0 | 0 | 0 | 0 | 100% |
| mcp_server/services/cache_service.py | 65 | 16 | 20 | 4 | 74% |
| mcp_server/services/data_service.py | 317 | 260 | 154 | 6 | 30% |
| mcp_server/services/parser_service.py | 180 | 105 | 66 | 14 | 45% |
| mcp_server/tools/\_\_init\_\_.py | 0 | 0 | 0 | 0 | 100% |
| mcp_server/tools/analytics.py | 845 | 800 | 344 | 5 | 4% |
| mcp_server/tools/article_reader.py | 61 | 14 | 16 | 4 | 72% |
| mcp_server/tools/config_mgmt.py | 25 | 7 | 0 | 0 | 72% |
| mcp_server/tools/data_query.py | 91 | 62 | 12 | 2 | 37% |
| mcp_server/tools/search_tools.py | 319 | 277 | 144 | 3 | 5% |
| mcp_server/tools/storage_sync.py | 207 | 174 | 56 | 4 | 12% |
| mcp_server/tools/system.py | 208 | 184 | 64 | 3 | 10% |
| mcp_server/utils/\_\_init\_\_.py | 0 | 0 | 0 | 0 | 100% |
| mcp_server/utils/date_parser.py | 50 | 43 | 24 | 0 | 10% |
| mcp_server/utils/errors.py | 41 | 18 | 4 | 1 | 53% |
| mcp_server/utils/validators.py | 23 | 16 | 10 | 0 | 27% |

### TOTAL

| | Stmts | Miss | Branch | BrPart | Cover |
|--|-------|------|--------|--------|-------|
| **TOTAL** | **13,171** | **9,038** | **4,892** | **318** | **26.69%** |

## Modules Below 50% Coverage (Phase 3 Attention)

These modules have <50% coverage and represent the largest untested areas:

| Module | Cover | Stmts | Reason |
|--------|-------|-------|--------|
| trendradar/\_\_main\_\_.py | 20% | 476 | God object (NewsAnalyzer) -- Phase 3 decomposition target |
| trendradar/storage/sqlite_mixin.py | 5% | 510 | Heavy data layer -- no integration test coverage yet |
| trendradar/report/html_sections.py | 3% | 216 | HTML generation -- no report content tests |
| trendradar/report/rss_html.py | 0% | 48 | RSS HTML rendering -- zero coverage |
| trendradar/storage/remote.py | 12% | 404 | S3 backend -- untested (optional dep) |
| trendradar/notification/batch.py | 11% | 143 | Notification batching -- no integration tests |
| mcp_server/tools/analytics.py | 4% | 845 | Largest MCP module -- handler tests cover entry points only |
| mcp_server/tools/search_tools.py | 5% | 319 | Large MCP module -- handler tests cover entry points only |

## 80% Coverage Gate Status

**FAILED** -- Overall coverage is 26.69%, well below the 80% gate configured in pyproject.toml (`--cov-fail-under=80`).

**Root cause:** The codebase has 13,171 statements across `trendradar` and `mcp_server` packages. Phase 2 added 227 tests but the codebase volume (particularly storage, reporting, notification channels, and the main module) dwarfs what targeted tests can cover. The 80% gate was aspirational for Phase 2; achieving it requires substantial additional test investment beyond the safety-net scope.

**Impact on Phase 3:**
- The baseline IS captured and committed (the primary TEST-02 requirement)
- Phase 3 can still use `git show e0945a2c:coverage.xml` for regression comparison
- The 80% gate in pyproject.toml remains active -- it will fail on every `pytest` run until coverage improves
- Developers can run `pytest --override-ini="addopts="` or `pytest --no-cov` to skip the gate during Phase 3 work

**Recommendation:** The 80% gate should be reassessed. Options:
1. Lower to current level + margin (e.g., 30%) as a ratchet that prevents regression
2. Keep at 80% as aspirational but accept pytest exits non-zero
3. Remove fail-under and rely on manual baseline comparison

## Pre-existing Test Failure

**test_discover_finds_all_builtin_plugins** -- This test fails when run with the full suite due to CrawlerRegistry singleton state contamination from earlier tests. It passes in isolation (`pytest tests/test_crawler_registry.py::test_discover_finds_all_builtin_plugins -x`). This is NOT a regression from Phase 2 changes.

## Files Created/Modified

- `coverage.xml` -- committed as baseline at e0945a2c, then untracked (gitignored)
- `.gitignore` -- added `coverage.xml` and `.coverage` exclusions

## Decisions Made

- **Baseline number is 26.69%:** Recorded honestly. The 80% gate is a stretch target, not achievable with Phase 2's safety-net test additions alone. The codebase has ~13K statements; covering 80% would require ~10,500 exercised lines.
- **Also gitignored .coverage:** The binary coverage cache from pytest-cov was appearing as untracked. Added to .gitignore alongside coverage.xml (Rule 2: auto-add missing -- keeping generated files out of git).
- **Coverage.xml untracked after baseline commit:** Used `git rm --cached` to stop tracking coverage.xml while preserving it in git history at e0945a2c. This ensures subsequent pytest runs don't produce git churn.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added .coverage to .gitignore**
- **Found during:** Task 2 (gitignore update)
- **Issue:** The .coverage binary file (pytest-cov runtime cache) appeared as untracked after test runs
- **Fix:** Added `.coverage` to .gitignore alongside `coverage.xml`
- **Files modified:** .gitignore
- **Verification:** `git check-ignore .coverage` confirms ignored
- **Committed in:** abbdd07a (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 2 - missing .gitignore entry)
**Impact on plan:** Minimal -- added one line to .gitignore to keep generated files clean.

## Issues Encountered

- **80% coverage gate failure:** pytest exits non-zero due to `--cov-fail-under=80` with actual coverage at 26.69%. This was handled by running with `--override-ini="addopts="` to capture the baseline without the gate blocking XML generation. The gate remains in pyproject.toml as configured by Plan 01.
- **pytest-randomly + thinc seed overflow:** The `thinc` library (Anaconda environment) causes `ValueError: Seed must be between 0 and 2**32 - 1` when pytest-randomly is active. Workaround: `-p no:randomly` flag. Pre-existing environment condition.

## User Setup Required

None -- no external service configuration required.

## Next Phase Readiness

- **Coverage baseline committed:** Phase 3 can diff against `git show e0945a2c:coverage.xml`
- **Gate decision needed:** The 80% fail-under gate will block `pytest` from exiting cleanly. Phase 3 or a follow-up plan should address this (lower gate, remove gate, or add more tests).
- **Per-module table available:** Above table identifies the largest untested modules for prioritization.

## Known Stubs

None -- this plan captures a measurement and updates .gitignore. No code stubs introduced.

## Threat Flags

None -- no new network endpoints, auth paths, or schema changes. Coverage.xml contains only repo-relative file paths and line numbers (T-02-06-01 accepted per threat model).

## Self-Check: PASSED

**Files verified:**
- FOUND: .gitignore (with coverage.xml and .coverage entries)
- FOUND: 02-06-SUMMARY.md
- FOUND: coverage.xml (local working copy, gitignored)

**Commits verified:**
- FOUND: e0945a2c (docs(02-06): commit coverage baseline artifact)
- FOUND: abbdd07a (chore(02-06): gitignore coverage.xml after baseline commit)

**Baseline retrievable:**
- `git show e0945a2c:coverage.xml` returns valid XML (coverage 7.13.5, 13171 lines-valid)

**Existing .gitignore entries preserved:**
- `__pycache__/` present
- `*.py[cod]` present
- All 8 original entries intact

---

*Phase: 02-test-safety-net*
*Plan: 06*
*Completed: 2026-04-14*
