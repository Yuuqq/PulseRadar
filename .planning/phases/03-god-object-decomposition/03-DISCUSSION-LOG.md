# Phase 3: God Object Decomposition - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-15
**Phase:** 03-god-object-decomposition
**Areas discussed:** DTO boundary design, Dead code: trend analysis, Facade boundary

---

## DTO Boundary Design

### Q1: CrawlOutput scope

| Option | Description | Selected |
|--------|-------------|----------|
| Single merged DTO (Recommended) | CrawlOutput carries merged hotlist + extra APIs + RSS. One DTO crosses to AnalysisEngine. | ✓ |
| Separate hotlist + RSS DTOs | Separate CrawlOutput (hotlist+extra) and RSSOutput at boundary. More granular. | |
| You decide | Let Claude decide based on minimizing code changes. | |

**User's choice:** Single merged DTO
**Notes:** CrawlCoordinator owns all merging logic. Simpler interface.

### Q2: CrawlOutput field richness

| Option | Description | Selected |
|--------|-------------|----------|
| Fat DTO (all fields) | Carries results, id_to_name, failed_ids, rss_items, rss_new_items, raw_rss_items. Maximally explicit. | ✓ |
| Lean DTO (crawl data only) | Carries only crawl data. Analysis config loaded separately by AnalysisEngine. | |
| You decide | Let Claude decide based on cleanest boundary. | |

**User's choice:** Fat DTO (all fields)
**Notes:** Analysis config (word_groups, filter_words) loaded separately by AnalysisEngine since config-derived.

### Q3: AnalysisOutput structure

| Option | Description | Selected |
|--------|-------------|----------|
| Flat (Recommended) | Fields: stats, html_file_path, ai_result. Matches current return shape. | ✓ |
| Nested sub-DTOs | Sub-DTOs for ReportOutput, NotificationPayload. More structure, more classes. | |
| You decide | Let Claude decide based on minimizing change. | |

**User's choice:** Flat
**Notes:** Mirrors current `_run_analysis_pipeline` return shape directly.

---

## Dead Code: Trend Analysis

### Q1: What to do with unused TrendAnalyzer wiring

| Option | Description | Selected |
|--------|-------------|----------|
| Remove the dead call (Recommended) | Delete _analyze_trends() call from run(), remove import. TrendAnalyzer class stays in core/trend.py. | ✓ |
| Keep with TODO | Keep call but add TODO comment noting it's unused. | |
| Wire it into the pipeline | Wire trend_report into CrawlOutput. Adds scope but makes feature functional. | |

**User's choice:** Remove the dead call
**Notes:** TrendAnalyzer class preserved in core/trend.py for potential future use. Only the unused wiring in __main__.py is removed.

---

## Facade Boundary

### Q1: Facade vs. direct wiring

| Option | Description | Selected |
|--------|-------------|----------|
| Keep facade (Recommended) | NewsAnalyzer stays as thin facade. __init__ creates orchestrators, run() calls them. Zero import changes. | ✓ |
| Delete, wire in main() | Delete NewsAnalyzer. main() creates orchestrators directly. Simpler but breaks test. | |
| You decide | Let Claude decide based on minimum breakage. | |

**User's choice:** Keep facade
**Notes:** Research confirmed NewsAnalyzer has NO external consumers besides main() and one test. Facade preserves both.

### Q2: Orchestrator class location

| Option | Description | Selected |
|--------|-------------|----------|
| trendradar/core/ (Recommended) | New files in core/ alongside pipeline.py, mode_strategy.py. Follows existing pattern. | ✓ |
| trendradar/orchestrators/ | New top-level package. Clearer separation but new directory. | |
| Same file (__main__.py) | Everything in one file, just better organized. | |

**User's choice:** trendradar/core/
**Notes:** Consistent with existing pattern of core/ holding extracted logic.

### Q3: update_info flow

| Option | Description | Selected |
|--------|-------------|----------|
| Constructor parameter (Recommended) | main() passes update_info to constructor. No external attribute mutation after construction. | ✓ |
| Keep attribute mutation | Keep current pattern where main() sets analyzer.update_info after construction. | |
| You decide | Let Claude decide. | |

**User's choice:** Constructor parameter
**Notes:** Eliminates the only external mutation on NewsAnalyzer.

---

## Claude's Discretion

- **Callback elimination strategy:** The `_fn` callback parameters in pipeline.py, mode_strategy.py, ai_service.py, notification_service.py. Claude decides approach (inline, DI, pass data instead of functions).

## Deferred Ideas

None — discussion stayed within phase scope.
