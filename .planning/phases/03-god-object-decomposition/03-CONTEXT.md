# Phase 3: God Object Decomposition - Context

**Gathered:** 2026-04-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Extract `CrawlCoordinator` and `AnalysisEngine` from `NewsAnalyzer` behind a thin facade, using frozen DTOs at stage boundaries. Every external caller (CLI, MCP server, Web UI, Docker) keeps working exactly as before. No new features — pure structural decomposition.

</domain>

<decisions>
## Implementation Decisions

### DTO Boundary Design
- **D-01:** Single merged DTO — `CrawlOutput` carries ALL crawl results (hotlist + extra APIs + RSS) as one frozen dataclass. `CrawlCoordinator` owns all merging logic.
- **D-02:** Fat DTO — `CrawlOutput` carries all crawl-produced data fields: results (merged), id_to_name, failed_ids, rss_items, rss_new_items, raw_rss_items. Analysis config (word_groups, filter_words) is loaded separately by `AnalysisEngine`.
- **D-03:** Flat `AnalysisOutput` — mirrors current `_run_analysis_pipeline` return shape: stats, html_file_path, ai_result. No nested sub-DTOs.
- **D-04:** `RSSOutput` exists as a separate frozen dataclass but is carried WITHIN `CrawlOutput` (not a separate boundary crossing).

### Dead Code: Trend Analysis
- **D-05:** Remove the dead `_analyze_trends()` call from `run()`. Delete the `TrendAnalyzer` import from `__main__.py`. The `TrendAnalyzer` class in `core/trend.py` stays intact — just the unused wiring is removed.

### Facade Boundary
- **D-06:** `NewsAnalyzer` stays as a thin facade class. `__init__` creates `CrawlCoordinator` + `AnalysisEngine`, `run()` calls them in sequence. `main()` still does `NewsAnalyzer(config).run()`.
- **D-07:** `CrawlCoordinator` and `AnalysisEngine` live in `trendradar/core/` (new files: `crawl_coordinator.py`, `analysis_engine.py`). Follows existing pattern of `core/` holding extracted logic.
- **D-08:** `update_info` becomes a constructor parameter to `NewsAnalyzer` (or passed via a setter before `run()`). No external attribute mutation after construction. `main()` computes version info first, then passes it in.

### Callback Elimination (Claude's Discretion)
- The `_fn` callback parameters in `pipeline.py`, `mode_strategy.py`, `ai_service.py`, `notification_service.py` will be eliminated. Claude has discretion on strategy (inline the logic, pass data instead of functions, or use method references on the new orchestrator classes).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Architecture & Research
- `.planning/research/ARCHITECTURE.md` — Detailed decomposition plan, callback coupling analysis, step-by-step extraction strategy, target file layout
- `.planning/research/PITFALLS.md` — 7 specific risks for this phase: callback signature breakage, update_info silent failure, dead code in trend analysis, AppContext bloat
- `.planning/research/SUMMARY.md` — Research summary confirming NewsAnalyzer has NO external consumers

### Requirements
- `.planning/REQUIREMENTS.md` — REFACTOR-01 through REFACTOR-06 define success criteria
- `.planning/ROADMAP.md` §Phase 3 — Success criteria with 6 checkboxes

### Codebase Maps
- `.planning/codebase/ARCHITECTURE.md` — Current data flow diagram showing NewsAnalyzer.run() pipeline
- `.planning/codebase/CONCERNS.md` — Documents the god object concern and callback coupling

### Phase 2 Context (Test Safety Net)
- `.planning/phases/02-test-safety-net/02-CONTEXT.md` — Test infrastructure decisions that Phase 3 must preserve
- `tests/pipeline/test_analyze_trends_dead_code.py` — Dead code lock test that imports NewsAnalyzer; must be updated when removing _analyze_trends call

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `trendradar/core/pipeline.py` — Already-extracted `run_analysis_pipeline()` and `prepare_standalone_data()`. These become methods on `AnalysisEngine`.
- `trendradar/core/mode_strategy.py` — Already-extracted `execute_mode_strategy()`, `process_rss_data_by_mode()`, `convert_rss_items_to_list()`. These feed into `AnalysisEngine`.
- `trendradar/core/notification_service.py` — Already-extracted `send_notification_if_needed()` and `has_notification_configured()`.
- `trendradar/core/ai_service.py` — Already-extracted `prepare_ai_analysis_data()` and `run_ai_analysis()`.
- `trendradar/core/rss_crawler.py` — Already-extracted `crawl_rss_data()`. Becomes part of `CrawlCoordinator`.
- `trendradar/context.py` (`AppContext`) — Central DI container. New orchestrator classes receive it via constructor injection.

### Established Patterns
- **Pure function extraction with `_fn` callbacks:** Prior refactor extracted functions but threaded `NewsAnalyzer` methods back in via callback params. Phase 3 breaks this coupling.
- **`AppContext` as DI container:** All config-dependent ops flow through `AppContext`. New classes follow this pattern.
- **Frozen dataclasses:** `FetchedItem`, `CrawlResult`, `NewsData`, `RSSData` already use `@dataclass(frozen=True)`. New DTOs follow suit.

### Integration Points
- `trendradar/__main__.py:main()` — Composition root. Creates `NewsAnalyzer`, sets `update_info`, calls `run()`.
- `tests/pipeline/test_analyze_trends_dead_code.py` — Inspects `NewsAnalyzer` class structure. Must be updated.
- `tests/pipeline/test_pipeline_integration.py` — Pipeline integration tests that must pass unchanged.
- MCP server imports from `trendradar.core.*`, `trendradar.storage.*`, `trendradar.crawler.*` — NOT affected by decomposition.
- Web UI imports from `trendradar.webui.*` — NOT affected by decomposition.

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches following the research architecture document's decomposition plan.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 03-god-object-decomposition*
*Context gathered: 2026-04-15*
