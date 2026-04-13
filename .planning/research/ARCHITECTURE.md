# Architecture Patterns

**Domain:** Python god object decomposition (NewsAnalyzer, 835 lines)
**Researched:** 2026-04-13

## Current State Analysis

### What Prior Refactoring Already Accomplished

The commit `63936e15` extracted pure functions from `NewsAnalyzer` into five service modules:

| Module | Extracted Logic | Lines |
|--------|----------------|-------|
| `core/pipeline.py` | `run_analysis_pipeline()`, `prepare_standalone_data()` | ~270 |
| `core/mode_strategy.py` | `execute_mode_strategy()`, `process_rss_data_by_mode()`, `convert_rss_items_to_list()` | ~490 |
| `core/notification_service.py` | `send_notification_if_needed()`, `has_notification_configured()`, `has_valid_content()` | ~190 |
| `core/ai_service.py` | `prepare_ai_analysis_data()`, `run_ai_analysis()` | ~250 |
| `core/rss_crawler.py` | `crawl_rss_data()` | ~120 |

**However, the extraction is incomplete.** The extracted functions accept callback parameters (`load_analysis_data_fn`, `run_analysis_pipeline_fn`, `prepare_current_title_info_fn`, etc.) that point back to `NewsAnalyzer` methods. This creates a circular coupling:

```
NewsAnalyzer._execute_mode_strategy()
  --> mode_strategy.execute_mode_strategy(
        load_analysis_data_fn=self._load_analysis_data,
        run_analysis_pipeline_fn=self._run_analysis_pipeline,
        send_notification_fn=self._send_notification_if_needed,
        ...
      )
  --> These callbacks call back into NewsAnalyzer methods
  --> Those methods delegate again to other extracted functions
```

The `_fn` callback pattern was a safe first step (no behavior change), but it's a halfway point -- the functions are technically standalone but logically still coupled to the class through function injection.

### What Remains in NewsAnalyzer

After extraction, `NewsAnalyzer` (lines 45-660) contains:

1. **State initialization** (`__init__`, `_init_storage_manager`, `_setup_proxy`, `_detect_docker_environment`) -- ~60 lines
2. **Thin delegation methods** that wrap extracted functions by passing `self.*` state -- ~200 lines
3. **Data loading** (`_load_analysis_data`, `_prepare_current_title_info`) -- ~50 lines
4. **Data crawling** (`_crawl_data`, `_crawl_rss_data`, `_crawl_extra_apis`) -- ~90 lines
5. **Content filtering** (`_filter_rss_by_keywords`, `_generate_rss_html_report`, `_has_valid_content`) -- ~60 lines
6. **Version checking** (`_set_update_info_from_config`) -- ~20 lines
7. **Orchestration** (`run()`) -- ~50 lines
8. **Mode/strategy config** (`MODE_STRATEGIES` dict, `_get_mode_strategy`) -- ~25 lines

### Critical Observation: NewsAnalyzer Has No External Consumers

`NewsAnalyzer` is NOT imported by MCP server, Web UI, or any module outside `__main__.py`. The ONLY consumer is `main()` in the same file. This means:

- The class can be completely restructured without breaking any import contract
- The public interface is effectively just `NewsAnalyzer(config).run()`
- CLI compatibility is preserved by keeping `main()` intact regardless of internal changes

### AppContext Is Already a Proto-Service Locator

`AppContext` (485 lines) already provides:
- Config access (properties)
- Time operations
- Storage management (lazy singleton)
- Frequency analysis
- Report generation
- Notification dispatch creation

This is the actual dependency container. `NewsAnalyzer` is essentially a script runner that uses `AppContext` as its service layer.

## Recommended Architecture

### Pattern: Extract Class with Facade Preservation

**Why not Mediator/Command/Event patterns:** This is a linear pipeline (`crawl -> store -> analyze -> report -> notify`), not a complex interaction graph. Over-engineering with mediator or event-driven patterns would add indirection without value. The pipeline is inherently sequential with branching only at the mode strategy level.

**Why not microservices/separate processes:** This runs as a single CLI invocation or cron job. Process boundaries add latency and complexity with zero benefit.

**The correct decomposition is Extract Class**, breaking `NewsAnalyzer` into focused service classes that own their state and logic, with a thin `PipelineRunner` (or keeping `NewsAnalyzer` as a facade) that wires them together.

### Target Component Boundaries

```
                    main()
                      |
                      v
              +------------------+
              |  NewsAnalyzer    |  <-- Facade (thin, keeps backwards compat)
              |  (or renamed     |
              |   PipelineRunner)|
              +--------+---------+
                       |
          +------------+------------+
          |            |            |
          v            v            v
   +-----------+  +---------+  +----------+
   | CrawlOrch |  | Analysis|  | Notifier |
   | estrator  |  | Engine  |  |          |
   +-----------+  +---------+  +----------+
   | crawl()   |  | analyze |  | notify() |
   | crawlRss()|  | ()      |  +----------+
   | crawlApis()|  +---------+       |
   +-----------+       |             v
        |              v        AppContext
        v         AppContext    .create_notification_dispatcher()
   AppContext     .count_frequency()
   .get_storage_manager()
   DataFetcher
```

### Component Definitions

#### 1. CrawlCoordinator

**Responsibility:** Execute all data ingestion (hotlist, RSS, extra APIs), store results, return unified crawl output.

**Owns:**
- `DataFetcher` instance
- Proxy configuration
- Extra API crawling
- RSS crawling (delegates to `RSSFetcher`)
- Storage persistence of crawl results

**Consumes:**
- `AppContext` (for config, storage manager, time)
- `StorageManager` (for saving data)

**Produces:**
- `CrawlOutput` dataclass containing: `results`, `id_to_name`, `failed_ids`, `rss_items`, `rss_new_items`, `raw_rss_items`

**Current code that moves here:**
- `_crawl_data()` (lines 388-426)
- `_crawl_extra_apis()` (lines 437-474)
- `_crawl_rss_data()` (line 428-435, currently a thin wrapper)
- Extra API result merging logic from `run()` (lines 624-641)

#### 2. AnalysisEngine

**Responsibility:** Given crawl output, load historical data as needed, run frequency analysis, AI analysis, and generate HTML report.

**Owns:**
- Mode strategy configuration (`MODE_STRATEGIES`)
- Historical data loading (`_load_analysis_data`)
- Title info preparation (`_prepare_current_title_info`)
- Standalone data preparation
- Analysis pipeline execution
- Content validity checking

**Consumes:**
- `AppContext` (for frequency counting, report generation)
- `CrawlOutput` from CrawlCoordinator

**Produces:**
- `AnalysisOutput` dataclass containing: `stats`, `html_file_path`, `ai_result`, `new_titles`, `id_to_name`, `standalone_data`, `report_type`

**Current code that moves here:**
- `_get_mode_strategy()` (line 159-161)
- `_load_analysis_data()` (lines 224-261)
- `_prepare_current_title_info()` (lines 263-281)
- `_has_valid_content()` (lines 167-185)
- `_prepare_standalone_data()` (lines 283-291)
- `_run_analysis_pipeline()` (lines 293-329)
- `_prepare_ai_analysis_data()` (lines 187-201)
- `_run_ai_analysis()` (lines 203-222)
- `_execute_mode_strategy()` (lines 544-572)
- `_filter_rss_by_keywords()` (lines 490-512)
- `_generate_rss_html_report()` (lines 514-542)

#### 3. NotificationService (already mostly extracted)

**Responsibility:** Decide whether to send notifications and dispatch them.

**Owns:**
- Push window logic
- Content validity checks for notification purposes
- Notification dispatch

**Consumes:**
- `AppContext` (for creating dispatcher, push manager)
- `AnalysisOutput` from AnalysisEngine

**Current code:** `core/notification_service.py` is already nearly there. The remaining coupling is the `run_ai_analysis_fn` callback (for re-running AI analysis during notification if not done during report phase). This callback should be eliminated -- AI analysis should happen once during analysis phase, not re-triggered during notification.

#### 4. TrendDetector (already exists as `TrendAnalyzer`)

**Responsibility:** Compare current vs previous crawl data for trend detection.

**Already exists** at `core/trend.py`. Currently called from `NewsAnalyzer.run()` but the result (`trend_report`) is computed and then never used in the remainder of the `run()` method. This is either dead code or a feature-in-progress.

#### 5. EnvironmentDetector (trivial extraction)

**Responsibility:** Detect runtime environment (GitHub Actions, Docker, local).

**Current code:**
- `_detect_docker_environment()` (lines 114-125)
- `_should_open_browser()` (lines 127-129)
- `is_github_actions` flag (line 83)

This is a pure utility that can be a simple function or small class.

#### 6. VersionChecker (already mostly extracted)

**Responsibility:** Check for version updates.

**Already exists** at `core/version_check.py`. The remaining `_set_update_info_from_config()` is a thin wrapper.

### Facade: NewsAnalyzer (Preserved for Backwards Compatibility)

```python
class NewsAnalyzer:
    """Facade preserving the original public interface."""

    def __init__(self, config: Optional[Dict] = None):
        if config is None:
            config = load_config()
        self.ctx = AppContext(config)
        self.crawl_coordinator = CrawlCoordinator(self.ctx)
        self.analysis_engine = AnalysisEngine(self.ctx)
        # notification_service is stateless, used as module functions

    def run(self) -> None:
        crawl_output = self.crawl_coordinator.crawl_all()
        analysis_output = self.analysis_engine.analyze(crawl_output)
        send_notification_if_needed(self.ctx, analysis_output)
```

This preserves the `NewsAnalyzer(config).run()` contract while the internal implementation is decomposed.

## Data Flow (Target State)

```
1. main() parses CLI args, loads config
2. main() creates NewsAnalyzer(config)
3. NewsAnalyzer.run():
   |
   +--> CrawlCoordinator.crawl_all()
   |      |- crawl_hotlist() -> results, id_to_name, failed_ids
   |      |- crawl_rss()    -> rss_items, rss_new_items, raw_rss_items
   |      |- crawl_extra()  -> extra_results, extra_names, extra_failed
   |      |- merge_extra_into_results()
   |      |- save_to_storage()
   |      +- return CrawlOutput(...)
   |
   +--> TrendAnalyzer.compare_periods(crawl_output)
   |      +- return TrendReport (currently unused downstream)
   |
   +--> AnalysisEngine.analyze(crawl_output)
   |      |- determine_mode_strategy()
   |      |- load_historical_data() (for daily/current modes)
   |      |- run_frequency_analysis()
   |      |- run_ai_analysis() (if enabled)
   |      |- generate_html_report()
   |      +- return AnalysisOutput(...)
   |
   +--> send_notification_if_needed(analysis_output)
   |      |- check push window
   |      |- prepare report data
   |      |- dispatch to channels
   |      +- record push state
   |
   +--> ctx.cleanup()
```

## Intermediate Data Structures

The current code passes 10-15 individual parameters between stages. Replacing these with structured dataclasses is the single highest-impact change for readability.

### CrawlOutput

```python
@dataclass(frozen=True)
class CrawlOutput:
    results: Dict              # {platform_id: {title: title_data}}
    id_to_name: Dict           # {platform_id: display_name}
    failed_ids: List[str]      # platforms that failed to crawl
    rss_items: Optional[List[Dict]]      # RSS stats items (mode-filtered)
    rss_new_items: Optional[List[Dict]]  # RSS new items
    raw_rss_items: Optional[List[Dict]]  # RSS raw items (for standalone)
```

### AnalysisOutput

```python
@dataclass(frozen=True)
class AnalysisOutput:
    stats: List[Dict]                    # frequency analysis results
    html_file_path: Optional[str]        # generated HTML file
    ai_result: Optional[AIAnalysisResult]
    new_titles: Optional[Dict]
    id_to_name: Dict
    standalone_data: Optional[Dict]
    report_type: str
    mode: str
    failed_ids: List[str]
    rss_items: Optional[List[Dict]]
    rss_new_items: Optional[List[Dict]]
    current_results: Optional[Dict]      # for notification re-analysis
```

## Patterns to Follow

### Pattern 1: Frozen Dataclasses for Inter-Component Data

**What:** Use `@dataclass(frozen=True)` for all data passed between components.
**Why:** Eliminates mutation bugs. The current code mutates `results`, `id_to_name`, and `failed_ids` in-place during extra API merging (lines 624-641 of `__main__.py`). Frozen dataclasses force producing new objects.
**When:** Every boundary between CrawlCoordinator, AnalysisEngine, and NotificationService.

```python
from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass(frozen=True)
class CrawlOutput:
    results: Dict
    id_to_name: Dict
    failed_ids: List[str]
    rss_items: Optional[List[Dict]] = None
    rss_new_items: Optional[List[Dict]] = None
    raw_rss_items: Optional[List[Dict]] = None
```

### Pattern 2: Eliminate Callback Parameters

**What:** Replace `_fn` callback parameters with direct method calls on injected service objects.
**Why:** The current pattern where `execute_mode_strategy()` takes `load_analysis_data_fn`, `run_analysis_pipeline_fn`, `send_notification_fn`, etc. as parameters is an artifact of the intermediate extraction. It creates hidden coupling and makes the function signatures enormous (22 parameters for `execute_mode_strategy`).
**When:** During class decomposition. The `AnalysisEngine` class owns these methods directly, so callbacks become `self.method()` calls.

```python
# CURRENT (bad): 22-parameter function with callbacks
def execute_mode_strategy(
    ctx, storage_manager, report_mode, rank_threshold,
    update_info, proxy_url, is_docker_container, should_open_browser,
    mode_strategy, results, id_to_name, failed_ids,
    load_analysis_data_fn,          # <-- callback
    prepare_current_title_info_fn,  # <-- callback
    run_analysis_pipeline_fn,       # <-- callback
    prepare_standalone_data_fn,     # <-- callback
    send_notification_fn,           # <-- callback
    rss_items, rss_new_items, raw_rss_items,
): ...

# TARGET (good): class method with structured input
class AnalysisEngine:
    def analyze(self, crawl_output: CrawlOutput) -> AnalysisOutput:
        # Calls self._load_analysis_data() directly
        # Calls self._run_pipeline() directly
        # All state is on self (ctx, storage_manager, report_mode, etc.)
        ...
```

### Pattern 3: Constructor Injection for Dependencies

**What:** Pass `AppContext` and `StorageManager` to component constructors, not to each method call.
**Why:** The current code passes `ctx` and `storage_manager` as parameters to every extracted function. Since these don't change during a run, they belong as constructor parameters.
**When:** When creating `CrawlCoordinator` and `AnalysisEngine`.

```python
class CrawlCoordinator:
    def __init__(self, ctx: AppContext):
        self.ctx = ctx
        self.storage_manager = ctx.get_storage_manager()
        self.data_fetcher = self._create_data_fetcher()

    def crawl_all(self) -> CrawlOutput:
        # Uses self.ctx, self.storage_manager, self.data_fetcher
        ...
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: Event-Driven Decomposition

**What:** Replacing the linear pipeline with an event bus or pub/sub system.
**Why bad:** This is a batch pipeline that runs once per cron cycle. Events add indirection, make debugging harder, and create ordering ambiguity -- all for zero benefit since there's only one subscriber for each stage's output.
**Instead:** Keep the explicit sequential call chain in `run()`.

### Anti-Pattern 2: Abstract Base Classes for Components

**What:** Creating `CrawlerBase`, `AnalyzerBase`, `NotifierBase` ABCs.
**Why bad:** There's only one implementation of each. ABCs add indirection with no polymorphism benefit. YAGNI.
**Instead:** Concrete classes. If a second implementation is ever needed, extract an interface then.

### Anti-Pattern 3: Deep Dependency Injection Framework

**What:** Using a DI container library (like `dependency_injector` or `injector`).
**Why bad:** `AppContext` already serves as a lightweight service locator. The system has ~5 services total. A DI framework adds learning curve and magic for trivial wiring.
**Instead:** Manual constructor injection. `AppContext` already exists and works.

### Anti-Pattern 4: Premature Splitting of `mode_strategy.py`

**What:** Creating separate classes for each mode (IncrementalStrategy, CurrentStrategy, DailyStrategy) using Strategy pattern.
**Why bad:** The three modes share 80% of their logic. The differences are just data source selection (current crawl vs historical data) and notification timing. Three classes would create massive code duplication.
**Instead:** Keep mode-branching in `AnalysisEngine.analyze()` with the mode string. The `MODE_STRATEGIES` dict already parameterizes the differences cleanly.

## Suggested Refactoring Order

The order matters because of data flow dependencies.

### Step 1: Define Data Transfer Objects (CrawlOutput, AnalysisOutput)

**Dependency:** None. These are pure data definitions.
**Risk:** Low. Adding new types doesn't break existing code.
**Where:** New file `trendradar/core/types.py` (or `trendradar/models/pipeline.py`)

### Step 2: Extract CrawlCoordinator

**Dependency:** Step 1 (uses CrawlOutput).
**Risk:** Low. Moves code from `NewsAnalyzer.__init__` and `_crawl_*` methods into a new class. `NewsAnalyzer` delegates to it.
**What moves:**
- `DataFetcher` creation and proxy setup
- `_crawl_data()` including storage persistence
- `_crawl_extra_apis()` including result merging
- `_crawl_rss_data()` delegation
- Extra API result merging from `run()` (lines 624-641)

**Backwards compatibility:** `NewsAnalyzer.__init__` creates a `CrawlCoordinator`. `NewsAnalyzer.run()` calls `self.crawl_coordinator.crawl_all()`. External interface unchanged.

### Step 3: Extract AnalysisEngine

**Dependency:** Steps 1-2 (consumes CrawlOutput, produces AnalysisOutput).
**Risk:** Medium. This is the largest extraction, touching mode strategy logic.
**What moves:**
- `_load_analysis_data()`
- `_prepare_current_title_info()`
- `_has_valid_content()`
- `MODE_STRATEGIES` dict and `_get_mode_strategy()`
- `_prepare_standalone_data()` delegation
- `_run_analysis_pipeline()` delegation
- `_prepare_ai_analysis_data()` delegation
- `_run_ai_analysis()` delegation
- `_execute_mode_strategy()` delegation
- `_filter_rss_by_keywords()`
- `_generate_rss_html_report()`

**Key change:** Eliminate `_fn` callback parameters from `execute_mode_strategy()`, `run_analysis_pipeline()`, etc. These become direct method calls within `AnalysisEngine`.

**Backwards compatibility:** `NewsAnalyzer.run()` calls `self.analysis_engine.analyze(crawl_output)`. External interface unchanged.

### Step 4: Simplify Notification Service

**Dependency:** Steps 1-3 (consumes AnalysisOutput).
**Risk:** Low. `notification_service.py` already exists. The main change is removing the `run_ai_analysis_fn` callback (AI analysis moves to Step 3) and accepting `AnalysisOutput` instead of 15 individual parameters.

### Step 5: Collapse NewsAnalyzer to Thin Facade

**Dependency:** Steps 1-4 complete.
**Risk:** Low. At this point, `NewsAnalyzer` should be ~50 lines: `__init__` creates components, `run()` calls them in sequence.

### Step 6: Clean Up Extracted Modules

**Dependency:** Step 5 complete.
**Risk:** Low. Remove callback parameters from `core/pipeline.py`, `core/mode_strategy.py`, etc. since `AnalysisEngine` calls them directly.

## How to Maintain Backwards Compatibility During Decomposition

### CLI Compatibility

The `main()` function in `__main__.py` is the CLI entry point. It:
1. Parses `argparse` arguments
2. Loads config
3. Creates `NewsAnalyzer(config=config)`
4. Sets `analyzer.update_info`
5. Calls `analyzer.run()`

**Preservation strategy:** Keep `main()` exactly as-is. Let `NewsAnalyzer.__init__` and `run()` evolve internally. The `update_info` attribute is the only external mutation -- this should move to a constructor parameter or a `configure()` method, but can remain as a property setter for compatibility during migration.

### Config Compatibility

No config changes needed. All components receive config through `AppContext`, which reads `config.yaml` unchanged.

### Docker Compatibility

Docker runs `python -m trendradar`. Since `main()` is preserved, Docker compatibility is automatic.

### Import Compatibility

MCP server imports: `trendradar.core.analyzer`, `trendradar.core.frequency`, `trendradar.storage`, `trendradar.crawler`, `trendradar.utils.time` -- none of these are affected by `NewsAnalyzer` decomposition.

Web UI imports: `trendradar.storage`, `trendradar.core.trend`, `trendradar.core.history`, `trendradar.crawler` -- also unaffected.

**The only import risk:** If any test file imports `NewsAnalyzer` directly. Quick verification:

```
grep -r "NewsAnalyzer" tests/  -> Check for test files importing the class
```

Even if tests import it, the facade pattern preserves the class and its interface.

## Scalability Considerations

| Concern | Current (single process) | Future (if needed) |
|---------|-------------------------|-------------------|
| Crawl parallelism | Sequential hotlist, concurrent extra APIs | CrawlCoordinator could easily add async/concurrent hotlist crawling since it owns all crawl logic |
| Analysis speed | Synchronous pipeline | AnalysisEngine could parallelize AI analysis with report generation since they're independent after frequency counting |
| Notification throughput | Synchronous per-channel dispatch | NotificationDispatcher already has batch support; no architectural change needed |
| Memory | Entire crawl results held in memory | CrawlOutput dataclass makes it explicit what's retained; could add streaming later |

## File Layout (Target State)

```
trendradar/
  __main__.py               # main() + NewsAnalyzer facade (~100 lines, down from 835)
  context.py                 # AppContext (unchanged)
  core/
    types.py                 # CrawlOutput, AnalysisOutput dataclasses (NEW)
    crawl_coordinator.py     # CrawlCoordinator class (NEW, ~150 lines)
    analysis_engine.py       # AnalysisEngine class (NEW, ~300 lines)
    pipeline.py              # run_analysis_pipeline() (simplified, callbacks removed)
    mode_strategy.py         # execute_mode_strategy() (simplified, callbacks removed)
    notification_service.py  # send_notification_if_needed() (simplified, takes AnalysisOutput)
    ai_service.py            # run_ai_analysis() (simplified, callbacks removed)
    rss_crawler.py           # crawl_rss_data() (unchanged, called by CrawlCoordinator)
    ...existing files...
```

## Sources

- Direct codebase analysis of `trendradar/__main__.py` (835 lines)
- Direct codebase analysis of `trendradar/context.py` (485 lines)
- Direct codebase analysis of all extracted `core/*.py` service modules
- Import dependency analysis of `mcp_server/` and `trendradar/webui/`
- Established software engineering principles: Extract Class refactoring (Fowler), Facade pattern (GoF), YAGNI
