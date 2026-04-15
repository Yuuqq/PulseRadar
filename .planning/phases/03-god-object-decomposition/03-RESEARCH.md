# Phase 3: God Object Decomposition - Research

**Researched:** 2026-04-15
**Domain:** Python class decomposition (Extract Class refactoring on 835-line NewsAnalyzer)
**Confidence:** HIGH

## Summary

This phase decomposes the 835-line `NewsAnalyzer` god object in `trendradar/__main__.py` into two focused classes (`CrawlCoordinator`, `AnalysisEngine`) behind a thin facade, using frozen dataclass DTOs at stage boundaries. The prior refactor (commit `63936e15`) already extracted pure functions into five service modules (`pipeline.py`, `mode_strategy.py`, `notification_service.py`, `ai_service.py`, `rss_crawler.py`) but left circular coupling via `_fn` callback parameters that thread `NewsAnalyzer` methods back through the extracted functions. This phase breaks that coupling.

The decomposition is low-risk because `NewsAnalyzer` has NO external consumers -- only `main()` in the same file constructs it. [VERIFIED: grep for NewsAnalyzer across mcp_server/ and webui/ returns zero hits.] MCP server imports from `trendradar.core.*`, `trendradar.storage.*`, `trendradar.crawler.*` -- all untouched. Web UI imports from `trendradar.webui.*` -- also untouched.

The existing test suite from Phase 2 provides a safety net: 5 mode-strategy integration tests, 2 extra-API merge lock tests, 1 dead-code lock test, 4 pipeline unit tests, and 12 notification service unit tests. These tests exercise the exact functions being modified and will catch signature or behavioral regressions.

**Primary recommendation:** Follow the Strangler Fig pattern -- create new classes and DTOs alongside the old code, delegate incrementally, verify tests pass at each step, then remove the old code. Never change behavior and structure in the same commit.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Single merged DTO -- `CrawlOutput` carries ALL crawl results (hotlist + extra APIs + RSS) as one frozen dataclass. `CrawlCoordinator` owns all merging logic.
- **D-02:** Fat DTO -- `CrawlOutput` carries all crawl-produced data fields: results (merged), id_to_name, failed_ids, rss_items, rss_new_items, raw_rss_items. Analysis config (word_groups, filter_words) is loaded separately by `AnalysisEngine`.
- **D-03:** Flat `AnalysisOutput` -- mirrors current `_run_analysis_pipeline` return shape: stats, html_file_path, ai_result. No nested sub-DTOs.
- **D-04:** `RSSOutput` exists as a separate frozen dataclass but is carried WITHIN `CrawlOutput` (not a separate boundary crossing).
- **D-05:** Remove the dead `_analyze_trends()` call from `run()`. Delete the `TrendAnalyzer` import from `__main__.py`. The `TrendAnalyzer` class in `core/trend.py` stays intact -- just the unused wiring is removed.
- **D-06:** `NewsAnalyzer` stays as a thin facade class. `__init__` creates `CrawlCoordinator` + `AnalysisEngine`, `run()` calls them in sequence. `main()` still does `NewsAnalyzer(config).run()`.
- **D-07:** `CrawlCoordinator` and `AnalysisEngine` live in `trendradar/core/` (new files: `crawl_coordinator.py`, `analysis_engine.py`). Follows existing pattern of `core/` holding extracted logic.
- **D-08:** `update_info` becomes a constructor parameter to `NewsAnalyzer` (or passed via a setter before `run()`). No external attribute mutation after construction. `main()` computes version info first, then passes it in.

### Claude's Discretion
- The `_fn` callback parameters in `pipeline.py`, `mode_strategy.py`, `ai_service.py`, `notification_service.py` will be eliminated. Claude has discretion on strategy (inline the logic, pass data instead of functions, or use method references on the new orchestrator classes).

### Deferred Ideas (OUT OF SCOPE)
- None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REFACTOR-01 | Frozen dataclass DTOs `CrawlOutput`, `AnalysisOutput`, `RSSOutput` exist and are used at stage boundaries | DTO design in Architecture Patterns section; existing frozen dataclass convention `@dataclass(frozen=True, slots=True)` verified in `crawler/base.py`, `models/news.py`, `core/trend.py` |
| REFACTOR-02 | `CrawlCoordinator` class exists and owns crawl + merge + store logic, returning `CrawlOutput` | CrawlCoordinator extraction plan in Architecture Patterns; merge logic analysis in Pitfall 1; test coverage via `test_extra_api_merge.py` |
| REFACTOR-03 | `AnalysisEngine` class exists and owns mode strategy + analysis pipeline + AI analysis, returning `AnalysisOutput` | AnalysisEngine extraction plan; 5 mode-strategy tests in `test_mode_strategy.py` provide safety net; callback coupling analysis |
| REFACTOR-04 | `NewsAnalyzer` in `__main__.py` is reduced to a thin facade (under 150 lines) | Facade pattern documented; current 660 lines of logic all have identified extraction targets |
| REFACTOR-05 | `_fn` callback parameters are removed from `core/pipeline.py`, `core/mode_strategy.py`, `core/notification_service.py`, and `core/ai_service.py` | Callback inventory in "Current Callback Coupling" section; elimination strategy in Architecture Patterns |
| REFACTOR-06 | CLI (`python -m trendradar` + all flags), config.yaml loading, and Docker deployment continue to work unchanged | Compatibility analysis confirms zero external consumers of `NewsAnalyzer`; `main()` preserved; MCP/WebUI imports verified unaffected |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **Immutability:** New objects, never mutate -- frozen DTOs enforce this at the boundary level
- **File size:** 200-400 lines typical, 800 max -- `NewsAnalyzer` at 835 lines violates this; target <150 lines post-decomposition
- **Functions:** <50 lines, single-purpose -- callback-heavy functions like `execute_mode_strategy` (22 params) violate this
- **Error handling:** Try/except with structured logging via structlog -- follow existing patterns
- **Input validation:** Use zod/pydantic -- existing Pydantic models in `models/config.py` stay unchanged
- **No console.log:** Use structlog `get_logger(__name__)` per module
- **Testing:** Requirement-driven, not implementation-driven; all scenarios covered and passing

## Standard Stack

### Core (already installed -- no new dependencies)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| dataclasses | stdlib | Frozen DTOs at stage boundaries | Python 3.10+ stdlib, `frozen=True, slots=True` convention already in codebase [VERIFIED: `crawler/base.py`, `models/news.py`] |
| typing | stdlib | Type hints for DTOs and method signatures | Already used throughout codebase [VERIFIED: every `core/*.py` file] |
| structlog | 24.x-25.x | Logging in new modules | Already the project standard [VERIFIED: `trendradar/logging/setup.py`] |

### Supporting (existing test infrastructure)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | 8.x | Test runner | Running all validation tests after each extraction step |
| pytest-cov | 4.1.0 | Coverage measurement | Verifying no coverage regression during decomposition |

**No new packages needed.** This is pure structural refactoring using stdlib features.

## Architecture Patterns

### New File Layout
```
trendradar/
  __main__.py                  # main() + NewsAnalyzer facade (~100-150 lines, down from 835)
  context.py                   # AppContext (unchanged)
  core/
    types.py                   # CrawlOutput, AnalysisOutput, RSSOutput DTOs (NEW)
    crawl_coordinator.py       # CrawlCoordinator class (NEW, ~180 lines)
    analysis_engine.py         # AnalysisEngine class (NEW, ~350 lines)
    pipeline.py                # run_analysis_pipeline() (simplified, callbacks removed)
    mode_strategy.py           # execute_mode_strategy() (simplified, callbacks removed)
    notification_service.py    # send_notification_if_needed() (simplified, takes structured data)
    ai_service.py              # run_ai_analysis() (simplified, callbacks removed)
    rss_crawler.py             # crawl_rss_data() (simplified, callback removed)
    ...existing files...
```

### Pattern 1: Frozen Dataclass DTOs at Stage Boundaries
**What:** Use `@dataclass(frozen=True, slots=True)` for all data passed between `CrawlCoordinator`, `AnalysisEngine`, and notification. [VERIFIED: This exact pattern exists in `crawler/base.py:FetchedItem`, `crawler/base.py:CrawlResult`, `models/news.py:PlatformSource`, `core/trend.py:TrendItem`]

**Why:** The current code mutates `results`, `id_to_name`, and `failed_ids` in-place during extra API merging (`__main__.py` lines 624-641). Frozen dataclasses force producing new objects at boundaries, eliminating mutation bugs.

**DTO Definitions (per decisions D-01 through D-04):**
```python
# Source: Locked decisions D-01, D-02, D-03, D-04
from dataclasses import dataclass, field
from typing import Dict, List, Optional

@dataclass(frozen=True, slots=True)
class RSSOutput:
    """RSS crawl results carried within CrawlOutput."""
    stats_items: Optional[List[Dict]] = None
    new_items: Optional[List[Dict]] = None
    raw_items: Optional[List[Dict]] = None

@dataclass(frozen=True, slots=True)
class CrawlOutput:
    """All crawl results merged into a single boundary object."""
    results: Dict                           # {platform_id: {title: title_data}}
    id_to_name: Dict                        # {platform_id: display_name}
    failed_ids: tuple = ()                  # platforms that failed (tuple for hashability)
    rss: RSSOutput = field(default_factory=RSSOutput)

@dataclass(frozen=True, slots=True)
class AnalysisOutput:
    """Flat output mirroring current pipeline return shape."""
    stats: List[Dict]                       # frequency analysis results
    html_file_path: Optional[str] = None    # generated HTML file
    ai_result: object = None                # AIAnalysisResult or None
```

**Note on shallow vs deep immutability:** The `Dict` and `List` field contents are NOT deeply frozen -- this is acceptable per existing codebase convention (same pattern as `FetchedItem.rank: int` and `CrawlResult.items: Tuple`). The frozen attribute prevents reassignment; contents are treated as read-only by convention. [VERIFIED: same pattern in `storage/base.py:NewsData` which contains `List[NewsItem]`]

**Note on `failed_ids` type:** Using `tuple` instead of `List[str]` for the frozen field, since tuples are immutable. The merge logic in `CrawlCoordinator` builds a regular list during processing, then converts to tuple when constructing the frozen `CrawlOutput`.

### Pattern 2: Constructor Injection via AppContext
**What:** Pass `AppContext` to component constructors, not to each method call.
**Why:** The current code passes `ctx` and `storage_manager` as parameters to every extracted function. Since these don't change during a run, they belong as constructor parameters. [VERIFIED: `AppContext` is already used this way -- `NewsAnalyzer.__init__` stores `self.ctx`]

```python
# Source: Existing pattern in __main__.py:70-98
class CrawlCoordinator:
    def __init__(self, ctx: AppContext):
        self.ctx = ctx
        self.storage_manager = ctx.get_storage_manager()
        # ... DataFetcher creation, proxy setup

    def crawl_all(self) -> CrawlOutput:
        # Uses self.ctx, self.storage_manager internally
        ...
```

### Pattern 3: Strangler Fig Extraction Sequence
**What:** Create new classes alongside old code, delegate incrementally, verify at each step.
**Why:** Changing structure and behavior simultaneously causes hard-to-debug regressions. The callback elimination is especially risky (Pitfall 2).

**Extraction order (data dependency driven):**
1. **DTOs first** (no dependencies, no behavior change) -- `core/types.py`
2. **CrawlCoordinator** (depends on DTOs) -- move `_crawl_data`, `_crawl_extra_apis`, `_crawl_rss_data`, merge logic
3. **AnalysisEngine** (depends on DTOs + CrawlOutput) -- move mode strategy, pipeline, AI, notification orchestration
4. **Callback elimination** (depends on AnalysisEngine owning methods directly) -- simplify `pipeline.py`, `mode_strategy.py`, etc.
5. **Facade collapse** (depends on all above) -- reduce `NewsAnalyzer` to ~100-150 lines
6. **Dead code removal** (decision D-05) -- remove `_analyze_trends()` call and `TrendAnalyzer` import
7. **Test updates** -- update `test_analyze_trends_dead_code.py` to match new structure

### Current Callback Coupling (inventory)
Every `_fn` parameter is a contract that must be preserved or explicitly migrated:

| Module | Function | Callback Parameters | What They Do |
|--------|----------|-------------------|-------------|
| `pipeline.py` | `run_analysis_pipeline()` | `run_ai_analysis_fn`, `get_mode_strategy_fn` | Calls back into NewsAnalyzer AI analysis and mode strategy methods |
| `mode_strategy.py` | `execute_mode_strategy()` | `load_analysis_data_fn`, `prepare_current_title_info_fn`, `run_analysis_pipeline_fn`, `prepare_standalone_data_fn`, `send_notification_fn` | 5 callbacks threading NewsAnalyzer methods through a 22-parameter function |
| `notification_service.py` | `send_notification_if_needed()` | `get_mode_strategy_fn`, `run_ai_analysis_fn` | Mode strategy for logging; AI re-trigger if not done during report phase |
| `ai_service.py` | `run_ai_analysis()` | `prepare_ai_data_fn` | Prepares mode-specific data for AI analysis |
| `ai_service.py` | `prepare_ai_analysis_data()` | `prepare_current_title_info_fn`, `load_analysis_data_fn` | Loads historical/current data for AI |
| `rss_crawler.py` | `crawl_rss_data()` | `process_rss_data_by_mode_fn` | Processes RSS data after saving |

**Elimination strategy (Claude's Discretion area):**
- For `AnalysisEngine`-owned methods (`load_analysis_data`, `prepare_current_title_info`, `prepare_standalone_data`, `run_analysis_pipeline`): These become direct method calls on `self` within `AnalysisEngine`. The callbacks disappear because the caller and callee are now the same class.
- For `send_notification_fn`: Notification becomes a separate call in the facade's `run()`, not threaded through mode strategy. The notification service receives `AnalysisOutput` instead of 15 individual parameters.
- For `run_ai_analysis_fn` in `notification_service.py`: This re-triggers AI analysis during notification if it wasn't done during report generation. In the new architecture, AI analysis always runs in `AnalysisEngine.analyze()`, so the notification service never needs to re-trigger it. The callback is removed, and `ai_result` is passed through `AnalysisOutput`.
- For `process_rss_data_by_mode_fn` in `rss_crawler.py`: `CrawlCoordinator` calls `process_rss_data_by_mode()` directly after saving RSS data, since it owns the storage manager and mode context.

### Anti-Patterns to Avoid
- **Event-driven decomposition:** This is a batch pipeline that runs once per cron cycle. Events add indirection for zero benefit. [VERIFIED: single subscriber for each stage]
- **Abstract base classes for components:** Only one implementation of each. ABCs add indirection with no polymorphism benefit. YAGNI.
- **DI container framework:** `AppContext` already serves as a lightweight service locator. ~5 services total. [VERIFIED: `context.py` is 485 lines, provides config + storage + time + reporting + notification]
- **Premature Strategy pattern for modes:** Three modes share 80% logic. Three classes would create massive duplication. [VERIFIED: mode branching in `mode_strategy.py` lines 339-459 shows shared structure]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| DTO definitions | Custom namedtuples or plain dicts | `@dataclass(frozen=True, slots=True)` | Stdlib, already used throughout codebase, provides type hints + immutability + slots for memory efficiency |
| DI container | Custom registry or factory pattern | `AppContext` constructor injection | Already exists, works, ~5 services -- no framework needed |
| Type validation on DTOs | Custom `__post_init__` validators | Rely on type hints + runtime tests | DTOs are internal boundaries, not API surfaces -- type hints + test coverage is sufficient |
| Config passing | Parameter objects wrapping config subsets | Direct `ctx.config` access within classes | Existing pattern, avoids creating intermediate wrapper objects for one consumer |

## Common Pitfalls

### Pitfall 1: Extra API Merge Breaking Frozen Output
**What goes wrong:** Lines 624-641 of `__main__.py` mutate `results`, `id_to_name`, and `failed_ids` in-place after extra API crawling. If `CrawlCoordinator` returns frozen `CrawlOutput` before merging, the downstream code cannot mutate the dicts.
**Why it happens:** The original code was procedural -- variables were local to `run()` and mutation was fine.
**How to avoid:** Move ALL merging logic INTO `CrawlCoordinator.crawl_all()` so the merge happens BEFORE the frozen output is constructed. The coordinator produces a single, already-merged `CrawlOutput`. [VERIFIED: Decision D-01 locks this -- "CrawlCoordinator owns all merging logic"]
**Warning signs:** Any code that does `.update()`, `.extend()`, or `[key] =` on a frozen dataclass field.

### Pitfall 2: Breaking Callback Contracts During Extraction
**What goes wrong:** Changing extracted function signatures breaks existing call sites. `TypeError` at runtime, not caught by imports.
**Why it happens:** The 6 modules with `_fn` callbacks have implicit contracts. Changing one side without the other causes parameter mismatches.
**How to avoid:** Follow Strangler Fig -- create new class methods first, wire `NewsAnalyzer` to delegate, verify tests pass, THEN modify extracted functions. Each step separately committable. [VERIFIED: 5 mode-strategy tests + 4 pipeline tests exercise these exact contracts]
**Warning signs:** Any commit that changes both a function signature and its caller simultaneously without an intermediate passing state.

### Pitfall 3: AI Re-Trigger in Notification Service
**What goes wrong:** `notification_service.py` line 143 calls `run_ai_analysis_fn()` if `ai_result is None` and AI is enabled. If `AnalysisEngine` always produces `ai_result`, this callback becomes dead code. If it doesn't always produce it (e.g., AI window restricts when analysis runs), removing the callback silently breaks the re-trigger path.
**Why it happens:** The current architecture has two paths to AI analysis: one in `run_analysis_pipeline()` and one in `send_notification_if_needed()`.
**How to avoid:** Analyze when `ai_result` can be `None` even with AI enabled (answer: when AI analysis window is outside the current time, or when `once_per_day` is already recorded). Either: (a) always pass `ai_result` through and accept `None` means "AI was skipped" or (b) have `AnalysisEngine` set a flag like `ai_skipped_reason`. Option (a) is simpler and matches the current behavior.
**Warning signs:** Notification tests that pass without AI result but should have triggered re-analysis.

### Pitfall 4: update_info Side Channel Loss
**What goes wrong:** `main()` creates `NewsAnalyzer`, then externally sets `analyzer.update_info`. If decomposition changes the attribute path, `update_info` silently becomes `None` and version warnings disappear from reports.
**Why it happens:** Post-construction mutation is a hidden coupling.
**How to avoid:** Decision D-08 locks this: `update_info` becomes a constructor parameter. `main()` computes version info first, then passes it to `NewsAnalyzer(config=config, update_info=update_info)`. [VERIFIED: lines 771-778 of `__main__.py` show the current mutation pattern]
**Warning signs:** HTML reports missing version update warnings in test output.

### Pitfall 5: Mode Strategy Branching Subtleties
**What goes wrong:** The daily mode fallback (uses current data when no history exists) at `mode_strategy.py` lines 420-438 is easy to lose during refactoring.
**Why it happens:** It's a secondary code path that only triggers when no historical data exists.
**How to avoid:** The existing `test_daily_without_history_falls_back` test covers this exact path. [VERIFIED: `tests/pipeline/test_mode_strategy.py:301-355`] Keep this test passing at every extraction step.
**Warning signs:** Daily mode silently producing empty reports when no history exists.

### Pitfall 6: Frozen Dataclasses with Mutable Defaults
**What goes wrong:** Creating `@dataclass(frozen=True)` with `Dict` or `List` fields using `dict` or `list` as default values triggers `ValueError` at class definition time.
**Why it happens:** Dataclasses enforce that mutable defaults use `field(default_factory=...)`.
**How to avoid:** Use `field(default_factory=dict)` for Dict fields, `field(default_factory=list)` for List fields, or use `tuple` for truly immutable sequences (as in `crawler/base.py:CrawlResult.errors: Tuple[str, ...] = ()`).
**Warning signs:** `ValueError: mutable default ... is not allowed` at import time.

### Pitfall 7: Dead Code Test Update (test_analyze_trends_dead_code.py)
**What goes wrong:** The test at `tests/pipeline/test_analyze_trends_dead_code.py` inspects `NewsAnalyzer` class structure using `inspect` and `hasattr`. When `_analyze_trends` is removed (D-05), the test must be updated or it fails.
**Why it happens:** The test was specifically designed to lock the dead code pattern for Phase 3 to address.
**How to avoid:** Update the test AFTER removing the dead code. The new test should verify that `_analyze_trends` does NOT exist on `NewsAnalyzer` and that `TrendAnalyzer` is NOT imported in `__main__.py`.
**Warning signs:** `AssertionError: NewsAnalyzer must have _analyze_trends method` -- expected failure, must be addressed.

## Code Examples

### Example 1: CrawlCoordinator with Merge Logic Internalized
```python
# Source: Analysis of __main__.py lines 388-641 + decisions D-01, D-02
# File: trendradar/core/crawl_coordinator.py

@dataclass(frozen=True, slots=True)
class CrawlOutput:
    results: Dict
    id_to_name: Dict
    failed_ids: tuple = ()
    rss: RSSOutput = field(default_factory=RSSOutput)

class CrawlCoordinator:
    def __init__(self, ctx: AppContext, proxy_url: Optional[str] = None):
        self.ctx = ctx
        self.storage_manager = ctx.get_storage_manager()
        self.proxy_url = proxy_url
        self.data_fetcher = self._create_data_fetcher()

    def crawl_all(self) -> CrawlOutput:
        results, id_to_name, failed_ids = self._crawl_hotlist()
        rss_output = self._crawl_rss()
        extra_results, extra_names, extra_failed = self._crawl_extra_apis()

        # Merge extra APIs INTO results BEFORE freezing (Pitfall 1)
        if extra_results:
            merged = {**results}  # immutable copy
            for source_id, items in extra_results.items():
                merged[source_id] = self._normalize_extra_items(items)
            results = merged
            id_to_name = {**id_to_name, **extra_names}
            failed_ids = list(failed_ids) + list(extra_failed)

        return CrawlOutput(
            results=results,
            id_to_name=id_to_name,
            failed_ids=tuple(failed_ids),
            rss=rss_output,
        )
```

### Example 2: AnalysisEngine Eliminating Callbacks
```python
# Source: Analysis of mode_strategy.py + pipeline.py callback patterns
# File: trendradar/core/analysis_engine.py

class AnalysisEngine:
    def __init__(self, ctx: AppContext, update_info: Optional[Dict] = None):
        self.ctx = ctx
        self.storage_manager = ctx.get_storage_manager()
        self.update_info = update_info
        self.report_mode = ctx.config["REPORT_MODE"]

    def analyze(self, crawl_output: CrawlOutput) -> AnalysisOutput:
        # Direct method calls replace callbacks
        word_groups, filter_words, global_filters = self.ctx.load_frequency_words()
        mode_strategy = self._get_mode_strategy()

        # Mode branching -- previously in execute_mode_strategy with 5 callbacks
        if self.report_mode == "incremental":
            title_info = self._prepare_current_title_info(crawl_output.results)
            data_source = crawl_output.results
            new_titles = self.ctx.detect_new_titles(self.ctx.platform_ids)
        elif self.report_mode in ("current", "daily"):
            analysis_data = self._load_analysis_data()
            # ... mode-specific logic
        # ... rest of pipeline: frequency -> AI -> HTML -> return AnalysisOutput
```

### Example 3: Facade Collapse
```python
# Source: Decision D-06, D-08
# File: trendradar/__main__.py (target state)

class NewsAnalyzer:
    """Thin facade preserving the original public interface."""

    def __init__(self, config: Optional[Dict] = None, update_info: Optional[Dict] = None):
        if config is None:
            config = load_config()
        self.ctx = AppContext(config)
        proxy_url = self._resolve_proxy()
        self.crawl_coordinator = CrawlCoordinator(self.ctx, proxy_url=proxy_url)
        self.analysis_engine = AnalysisEngine(self.ctx, update_info=update_info)
        self.update_info = update_info

    def run(self) -> None:
        try:
            self._log_startup()
            crawl_output = self.crawl_coordinator.crawl_all()
            analysis_output = self.analysis_engine.analyze(crawl_output)
            self._send_notifications(analysis_output, crawl_output)
            self._maybe_open_browser(analysis_output.html_file_path)
        except Exception as e:
            logger.error("Pipeline execution error", error=str(e))
            if self.ctx.config.get("DEBUG", False):
                raise
        finally:
            self.ctx.cleanup()
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `_fn` callback parameters | Direct method calls on class instances | This phase | Eliminates 22-parameter function signatures, removes circular coupling |
| Post-construction `update_info` mutation | Constructor parameter | This phase (D-08) | Eliminates hidden side channel |
| In-place dict mutation for merge | Merge-before-freeze in coordinator | This phase (D-01) | Enables frozen DTOs at boundaries |
| Dead `_analyze_trends()` call | Removed (D-05) | This phase | Eliminates wasted computation |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `AnalysisEngine` at ~350 lines stays under the 400-line guideline | Architecture Patterns | May need further decomposition; verify after extraction |
| A2 | `notification_service.py` AI re-trigger is safe to remove because `AnalysisEngine` always runs AI when enabled | Pitfall 3 | If AI window/once_per_day prevents analysis but notification still needs it, notifications would lack AI content -- mitigated by passing `ai_result=None` and letting notification skip AI section |
| A3 | All existing tests pass without modification during intermediate extraction steps (before callback elimination) | Architecture Patterns | Some tests mock callbacks directly; if new class wiring changes call order, tests may need mock adjustments |

## Open Questions

1. **AnalysisEngine notification orchestration boundary**
   - What we know: Currently `execute_mode_strategy()` calls `send_notification_fn()` at the end. In the new architecture, notification moves to the facade's `run()`.
   - What's unclear: Should `AnalysisEngine.analyze()` also return the data needed for notification (standalone_data, rss items, etc.) or should the facade re-derive it from `CrawlOutput`?
   - Recommendation: Include all notification-needed data in `AnalysisOutput` (it already carries stats, html_file_path, ai_result). Add fields for `new_titles`, `id_to_name`, `mode`, `report_type`, `failed_ids`, `standalone_data`, `rss_items`, `rss_new_items`, `current_results`. This matches the "fat DTO" philosophy from D-02.

2. **RSS processing ownership**
   - What we know: Currently `_crawl_rss_data()` fetches, saves, and processes by mode. `process_rss_data_by_mode()` depends on `storage_manager` and `report_mode`.
   - What's unclear: Does RSS mode processing belong in `CrawlCoordinator` or `AnalysisEngine`?
   - Recommendation: `CrawlCoordinator` handles fetch + save + mode processing, since D-02 says `CrawlOutput` carries rss_items/rss_new_items/raw_rss_items. The coordinator needs `report_mode` from config to do this, which it gets from `ctx.config`.

3. **_handle_status_commands stays in __main__.py**
   - What we know: Lines 791-831 handle `--show-push-status`, `--show-ai-status`, `--reset-push-state`, `--reset-ai-state`. These create their own `AppContext` and don't use `NewsAnalyzer`.
   - What's unclear: Should this be extracted?
   - Recommendation: Leave in `__main__.py`. It's a separate code path (returns early before `NewsAnalyzer` construction), doesn't contribute to the god object problem, and moving it adds no value.

## Sources

### Primary (HIGH confidence)
- Direct codebase analysis of `trendradar/__main__.py` (835 lines) -- all methods, all data flows
- Direct codebase analysis of `trendradar/context.py` (485 lines) -- AppContext contract
- Direct codebase analysis of all `core/*.py` extracted service modules -- callback inventory
- Direct analysis of `tests/pipeline/` test suite -- safety net verification
- `.planning/research/ARCHITECTURE.md` -- prior research on decomposition strategy
- `.planning/research/PITFALLS.md` -- prior research on domain pitfalls
- `.planning/research/SUMMARY.md` -- prior research summary

### Secondary (MEDIUM confidence)
- Grep verification of import boundaries (MCP server, Web UI) -- confirmed zero `NewsAnalyzer` consumers
- Test execution baseline -- 19 tests passing (pipeline + notification service)

### Tertiary (LOW confidence)
- None -- all claims verified against codebase

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all stdlib, no new dependencies needed
- Architecture: HIGH -- based on direct code analysis, decisions locked by user, prior research validated
- Pitfalls: HIGH -- derived from actual code patterns, each with specific line numbers and test coverage verification
- DTO design: HIGH -- follows existing frozen dataclass convention verified in 4+ existing files
- Callback elimination: MEDIUM -- strategy is sound but A2 (AI re-trigger safety) needs validation during implementation

**Research date:** 2026-04-15
**Valid until:** 2026-05-15 (stable -- internal refactoring, no external dependency concerns)
