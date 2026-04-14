# Deferred Items - Phase 02

## Pre-existing Test Isolation Issue

**Test:** `tests/test_crawler_registry.py::test_discover_finds_all_builtin_plugins`
**Behavior:** Passes in isolation, fails when run after other tests in deterministic order (`-p no:randomly`). Gets 0 plugins instead of >= 9.
**Root Cause:** Likely test pollution of the crawler registry singleton or import state from preceding tests.
**Impact:** Does not affect coverage measurement (coverage is 28% with or without this test). Does cause pytest to exit non-zero when running the full suite.
**Discovered during:** Plan 02-07 execution.
