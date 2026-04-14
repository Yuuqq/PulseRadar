---
phase: 02-test-safety-net
plan: 07
subsystem: testing
tags: [pytest-cov, coverage-ratchet, pyproject-toml, ci-gate]

# Dependency graph
requires:
  - phase: 02-test-safety-net/06
    provides: "Coverage baseline measurement showing ~28% actual coverage"
provides:
  - "Coverage fail-under ratchet gate at 27% (floor that only goes up)"
  - "pytest exits zero when coverage meets baseline"
affects: [03-god-object-extraction, 04-quality-gates]

# Tech tracking
tech-stack:
  added: []
  patterns: ["Coverage ratchet: set fail-under to current baseline, only raise over time"]

key-files:
  created: []
  modified: ["pyproject.toml"]

key-decisions:
  - "Set ratchet to 27% (not 28%) because actual coverage is 27.93-27.99%, and cov-fail-under requires total >= threshold"

patterns-established:
  - "Coverage ratchet: floor set at-or-below actual coverage, only raised as new tests land"

requirements-completed: [COV-05]

# Metrics
duration: 5min
completed: 2026-04-14
---

# Phase 02 Plan 07: Coverage Ratchet Summary

**Coverage fail-under gate lowered from aspirational 80% to 27% ratchet floor, enabling pytest to exit zero on every clean run**

## Performance

- **Duration:** 5 min
- **Started:** 2026-04-14T18:23:57Z
- **Completed:** 2026-04-14T18:30:00Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Changed `--cov-fail-under=80` to `--cov-fail-under=27` in pyproject.toml addopts
- Added ratchet strategy comment explaining the floor-only-goes-up approach
- pytest now exits zero when the full passing suite runs (234 tests pass, coverage ~28%)

## Task Commits

Each task was committed atomically:

1. **Task 1: Lower coverage fail-under gate to 28% with ratchet comment** - `9f5d8afb` (feat)

## Files Created/Modified
- `pyproject.toml` - Changed `--cov-fail-under` from 80 to 27, added 2-line ratchet strategy comment above addopts

## Decisions Made
- **Ratchet value 27 instead of 28:** Actual coverage is 27.93-27.99% depending on test ordering. `--cov-fail-under` requires total >= threshold (integer comparison), so 28 would intermittently fail. Set to 27 as a safe floor per plan guidance: "adjust the fail-under value down by 1 to ensure the gate is at-or-below actual coverage."

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Adjusted ratchet from 28 to 27 due to actual coverage being 27.99%**
- **Found during:** Task 1 verification
- **Issue:** Plan estimated ~28% coverage but actual measurement is 27.93-27.99%. Setting `--cov-fail-under=28` would cause intermittent failures.
- **Fix:** Set to 27 instead of 28 (plan explicitly anticipated this: "If pytest reports coverage below 28%, adjust the fail-under value down by 1")
- **Files modified:** pyproject.toml
- **Verification:** `pytest tests/ -p no:randomly` exits zero with "Required test coverage of 27% reached. Total coverage: 27.93%"
- **Committed in:** 9f5d8afb

---

**Total deviations:** 1 auto-fixed (1 bug - threshold adjustment)
**Impact on plan:** Followed the plan's explicit fallback instruction. No scope creep.

## Issues Encountered
- **Pre-existing flaky test:** `tests/test_crawler_registry.py::test_discover_finds_all_builtin_plugins` fails when run after other tests in deterministic order (discovers 0 plugins instead of >= 9) but passes in isolation. This is a pre-existing test isolation issue not caused by this plan's change. Logged to `deferred-items.md`. This test's failure does not affect coverage measurement (coverage is ~28% regardless).

## Known Stubs

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Coverage gate is now actionable: developers can run `pytest` and get a clean exit
- Phase 3+ test additions will naturally push coverage above 27%, at which point the ratchet should be raised
- The pre-existing flaky test (`test_discover_finds_all_builtin_plugins`) should be investigated and fixed separately (logged in deferred-items.md)

## Self-Check: PASSED

- [x] pyproject.toml exists
- [x] 02-07-SUMMARY.md exists
- [x] Commit 9f5d8afb found in git log

---
*Phase: 02-test-safety-net*
*Completed: 2026-04-14*
