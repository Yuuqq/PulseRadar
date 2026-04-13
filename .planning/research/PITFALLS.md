# Domain Pitfalls

**Domain:** Python tech debt reduction (testing infrastructure, dependency management, class decomposition)
**Researched:** 2026-04-13

## Critical Pitfalls

Mistakes that cause rewrites, regressions, or major setbacks.

### Pitfall 1: Refactoring Without Integration Tests First

**What goes wrong:** Decomposing the NewsAnalyzer god object before establishing pipeline integration tests. Individual unit tests pass, but the pipeline breaks at boundaries between the new CrawlCoordinator, AnalysisEngine, and NotificationService classes.

**Why it happens:** Developers want to "clean up the code" before writing tests, arguing it is easier to test clean code. This inverts the correct order. Tests must prove current behavior before changing structure.

**Consequences:** Regressions in the crawl-to-notify pipeline that are invisible until production. The 3 report modes (incremental/current/daily) have subtle data-source differences that unit tests do not cover. A broken mode strategy causes missed notifications or empty reports.

**Prevention:** Establish characterization tests BEFORE any class extraction. These tests mock at external boundaries (HTTP, filesystem, AI API) but exercise the full orchestration logic. Specifically cover:
- All three modes (incremental, current, daily) with both "has data" and "no data" paths
- Notification gating (enabled/disabled, push window in/out, once_per_day)
- Extra API merging into results dict
- The daily mode fallback (uses current data when no history exists)

**Detection:** If someone proposes "extract first, test later" or "we will add tests in the next sprint", stop. The decomposition PR must include tests or must come after a testing PR.

### Pitfall 2: Breaking the `_fn` Callback Contracts During Extraction

**What goes wrong:** The extracted functions in `core/pipeline.py`, `core/mode_strategy.py`, etc. take callback parameters (`load_analysis_data_fn`, `run_analysis_pipeline_fn`, `send_notification_fn`) that point back to `NewsAnalyzer` methods. Changing these function signatures breaks the existing call sites.

**Why it happens:** The callback pattern was a safe intermediate step during the prior refactor. It works. Changing it requires updating both the caller (NewsAnalyzer) and the callee (extracted function) simultaneously. If you change one without the other, you get runtime errors (wrong number of arguments, wrong types).

**Consequences:** `TypeError` or `AttributeError` at runtime, not caught by Python's import system. If tests do not exercise these paths, the error surfaces in production.

**Prevention:** Follow the Strangler Fig sequence:
1. Create new class (e.g., `AnalysisEngine`) with methods that replicate callback behavior
2. Wire `NewsAnalyzer` to delegate to the new class
3. Verify all tests pass
4. THEN modify the extracted functions to accept the new class instead of callbacks
5. Verify again
Each step must be separately committable and testable.

**Detection:** `grep -r "_fn=" trendradar/core/` shows all callback injection sites. Each one is a contract that must be preserved or explicitly migrated.

### Pitfall 3: In-Place Mutation During Extra API Merging

**What goes wrong:** Lines 624-641 of `__main__.py` mutate `results`, `id_to_name`, and `failed_ids` in-place after extra API crawling:

```python
for source_id, items in extra_results.items():
    results[source_id] = {}          # mutating results dict
    ...
id_to_name.update(extra_names)       # mutating id_to_name dict
failed_ids.extend(extra_failed)      # mutating failed_ids list
```

If `CrawlCoordinator` returns a frozen `CrawlOutput` dataclass, this mutation pattern breaks. If it returns a mutable object, you've just moved the mutation to a different location without fixing it.

**Why it happens:** The original code was procedural -- variables were local to `run()` and mutation was fine. When moved to a class boundary, mutation becomes a coupling mechanism.

**Consequences:** Either `CrawlOutput` can't be frozen (defeating the purpose of DTOs), or the merging logic silently fails.

**Prevention:** Move the merging logic INTO `CrawlCoordinator.crawl_all()` so the merge happens before the output is frozen. The coordinator produces a single, merged `CrawlOutput` -- the caller never sees the separate extra API results.

**Detection:** Search for `.update(`, `.extend(`, `[key] =` on any object that crosses a component boundary.

### Pitfall 4: Coverage Threshold Without Meaningful Tests

**What goes wrong:** Achieving 80% coverage by testing trivial getters, setters, and internal implementation details. Coverage number looks good, but the tests do not actually validate behavior. Refactoring breaks tests instead of catching regressions.

**Why it happens:** Coverage is measured by lines executed, not by assertions made. A test that calls a function and asserts nothing counts as coverage. Teams optimize for the metric instead of the goal.

**Consequences:** High coverage number, low confidence in changes. Tests become a tax on refactoring (they break on every structural change) instead of a safety net (they break only on behavioral changes).

**Prevention:**
- Test behavior, not implementation. Assert on outputs and side effects, not on which internal methods were called.
- Use `--cov-fail-under=80` as a floor, not a target. Focus coverage effort on the untested areas (MCP server, crawlers, pipeline integration) rather than padding already-tested modules.
- Branch coverage (`branch = true`) catches untested conditional paths that line coverage misses.

**Detection:** Review tests for assertion density. A test with no assertions or only `assert True` is a coverage-padding anti-pattern.

## Moderate Pitfalls

### Pitfall 5: AppContext Becoming a Bigger God Object

**What goes wrong:** When extracting `CrawlCoordinator` and `AnalysisEngine`, the temptation is to add their creation logic to `AppContext` (e.g., `ctx.create_crawl_coordinator()`, `ctx.create_analysis_engine()`). This makes AppContext the new god object at 485 lines plus growing.

**Prevention:** `AppContext` should remain a configuration/service container. The new classes should receive `AppContext` via constructor injection, not be created by it. `NewsAnalyzer.__init__` (or `main()`) is the composition root -- it wires dependencies.

### Pitfall 6: Losing the `update_info` Side Channel

**What goes wrong:** `main()` creates `NewsAnalyzer`, then externally sets `analyzer.update_info` based on version check results. If decomposition changes the attribute access path (e.g., `update_info` lives on `AnalysisEngine` now), `main()` breaks silently -- `update_info` is `None`, and no version update warning appears in reports.

**Prevention:** Pass `update_info` as a constructor parameter or as a parameter to `run()`. Do not rely on post-construction attribute mutation.

### Pitfall 7: Mode Strategy Branching Subtleties

**What goes wrong:** The three report modes (incremental, current, daily) have subtle differences in `execute_mode_strategy()`:

- **incremental**: Uses current crawl data directly, no historical loading
- **current**: Loads historical data, uses historical title_info and new_titles; raises RuntimeError if no data found
- **daily**: Loads historical data, falls back to current data if no history exists (lines 420-438 of `mode_strategy.py`)

The daily mode fallback is easy to lose during refactoring because it's a secondary code path.

**Prevention:** Write a test for each mode's data path BEFORE extraction:
- incremental with data
- current with history
- current without history (should raise RuntimeError)
- daily with history
- daily without history (should use current data)

### Pitfall 8: `trend_report` Computed But Never Used

**What goes wrong:** In `NewsAnalyzer.run()`, line 644 calls `self._analyze_trends(results, id_to_name)` which returns a `TrendReport`, but the result is assigned to `trend_report` and never passed downstream.

If dead code, it wastes crawl time. If feature-in-progress, decomposition might accidentally remove it. If used only by Web UI (routes_misc.py imports TrendAnalyzer separately), it should be documented as a library, not part of the pipeline.

**Prevention:** Clarify before decomposition. Check if any planned work references trend_report. If unused, remove the call.

### Pitfall 9: RSS Processing Triple-Return Confusion

**What goes wrong:** RSS data flows through a complex chain returning `Tuple[Optional[List[Dict]], Optional[List[Dict]], Optional[List[Dict]]]` -- three `Optional[List[Dict]]` that are positionally distinguished (stats_items, new_items, raw_items). Swapping any two causes the wrong data to appear in the wrong report section.

**Prevention:** Replace with a named dataclass:
```python
@dataclass(frozen=True)
class RSSOutput:
    stats_items: Optional[List[Dict]] = None
    new_items: Optional[List[Dict]] = None
    raw_items: Optional[List[Dict]] = None
```

### Pitfall 10: requirements.txt / pyproject.toml Dual-Source Divergence

**What goes wrong:** Fixing the current drift (2 missing packages) without addressing the root cause. The two files will drift again after the next dependency change.

**Prevention:** Choose one canonical source. Recommended: delete `requirements.txt` entirely and use `pyproject.toml` as the single source of truth. Update Docker images to use `pip install .` instead of `pip install -r requirements.txt`. If requirements.txt must exist, generate it automatically via `uv pip compile pyproject.toml -o requirements.txt`.

### Pitfall 11: tenacity 8-to-9 Migration Breaking Retry Logic

**What goes wrong:** Upgrading tenacity from exact-pinned 8.5.0 to >=9.0 without checking the changelog. tenacity 9.x may have changed default retry behavior.

**Prevention:** Read the tenacity 8.x-to-9.x changelog before upgrading. Run existing tests with tenacity 9.x before merging.

### Pitfall 12: StorageManager Singleton Blocking Test Isolation

**What goes wrong:** The module-level `_storage_manager` singleton in `storage/manager.py` persists state across tests. Test A sets up storage state, Test B inherits it.

**Prevention:** Reset the singleton in test teardown (`conftest.py` autouse fixture). Long-term: components should call `ctx.get_storage_manager()` rather than caching a local reference.

**Detection:** Run tests with `pytest --randomly`. If tests fail when reordered, there is shared state contamination.

## Minor Pitfalls

### Pitfall 13: Windows UTF-8 Encoding Function Ordering

**What goes wrong:** `_ensure_utf8_output()` (lines 662-672 of `__main__.py`) reconfigures stdout/stderr encoding on Windows. It must run before any logging. If decomposition moves logging initialization, this function might execute too late.

**Prevention:** Keep `_ensure_utf8_output()` at the top of `main()`, before any other initialization. Do not move it into a class.

### Pitfall 14: Frozen Dataclasses with Mutable Defaults

**What goes wrong:** Creating `@dataclass(frozen=True)` with `Dict` or `List` fields that use default mutable arguments. The dataclass is "frozen" but its dict/list contents can still be mutated.

**Prevention:** Use `field(default_factory=dict)` for mutable defaults. Frozen dataclasses with mutable fields are "shallow frozen" -- acceptable if the team understands the contract. For true deep immutability, use `MappingProxyType` and `tuple`.

### Pitfall 15: Coverage Configuration Omitting mcp_server

**What goes wrong:** Configuring pytest-cov with `--cov=trendradar` but forgetting `--cov=mcp_server`. The MCP server shows 0% coverage despite having tests.

**Prevention:** Include both in config: `source = ["trendradar", "mcp_server"]`

### Pitfall 16: Optional boto3 Breaking S3 Users

**What goes wrong:** Moving boto3 to optional extras but not adding clear error messages when S3 is configured but boto3 is not installed.

**Prevention:** Guard every boto3 import with an actionable ImportError:
```python
try:
    import boto3
except ImportError:
    raise ImportError(
        "S3 storage requires boto3. Install with: pip install trendradar[s3]"
    )
```
Add this check at config validation time, not at first S3 operation.

### Pitfall 17: Adding mypy to Entire Codebase at Once

**What goes wrong:** Running `mypy --strict` on all 180 files and getting 500+ errors. Teams spend days fixing annotations in unrelated files.

**Prevention:** Incremental adoption: strict on new/extracted classes only, lenient on legacy. Use per-module mypy overrides.

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Define DTOs | Pitfall 14: frozen dataclass with mutable contents | Use `field(default_factory=...)` for Dict/List fields |
| Define DTOs | Trying to type every Dict as a class | Start with only CrawlOutput, RSSOutput, AnalysisOutput. Don't type internal dicts yet |
| Extract CrawlCoordinator | Pitfall 3: extra API mutation breaks frozen output | Include merging logic inside CrawlCoordinator before producing output |
| Extract AnalysisEngine | Pitfall 2: callback elimination breaks intermediate state | Keep callbacks during extraction, remove in separate commit |
| Extract AnalysisEngine | Pitfall 7: mode strategy branching subtleties | Write per-mode characterization tests first |
| Simplify Notification | AI re-trigger in notification_service.py | Ensure AI analysis runs once in AnalysisEngine, not re-triggered during notification |
| Collapse Facade | Pitfall 6: update_info side channel | Convert to constructor param or run() param |
| Coverage setup | Pitfall 15: omitting mcp_server | Include both packages in coverage source |
| Mock fixtures | Mocking requests internals instead of transport | Use `responses` library exclusively for HTTP mocking |
| MCP server tests | FastMCP test utilities may be underdocumented | Check FastMCP 2.0 docs for test client patterns; fall back to function-level testing |
| tenacity upgrade | Pitfall 11: breaking retry logic | Read changelog; test with new version before merging |
| Optional boto3 | Pitfall 16: unclear error for S3 users | Guard imports with actionable ImportError at config validation time |
| mypy introduction | Pitfall 17: strict on entire codebase | Incremental: strict on new code, lenient on legacy |
| Dependency sync | Pitfall 10: dual-source drift | Delete requirements.txt or auto-generate it |
| All phases | Pitfall 1: refactoring without tests | Characterization tests are mandatory before any structural change |

## Sources

- Direct codebase analysis of `trendradar/__main__.py` (all 835 lines, particularly lines 624-641 mutation, line 644 unused trend_report)
- Direct analysis of callback patterns across `core/mode_strategy.py`, `core/pipeline.py`, `core/notification_service.py`, `core/ai_service.py`
- Direct analysis of `trendradar/storage/manager.py` singleton pattern
- Direct analysis of `requirements.txt` vs `pyproject.toml` drift
- Direct analysis of RSS triple-return pattern in `core/mode_strategy.py`
- coverage.py documentation: https://coverage.readthedocs.io/
- responses library documentation: https://pypi.org/project/responses/
- tenacity changelog: https://pypi.org/project/tenacity/
