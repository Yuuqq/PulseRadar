# Architecture

## Pattern

**Pipeline-based architecture** with plugin system for data sources and channel-based notification dispatch.

The system follows a linear data pipeline:
```
Crawl → Store → Analyze → Report → Notify
```

## Core Layers

### 1. Configuration Layer
- `trendradar/core/config.py` — YAML loading, key normalization (lowercase→UPPERCASE)
- `trendradar/models/config.py` — Pydantic models with env var override validators
- `config/config.yaml` — single source of truth for all settings

### 2. Application Context
- `trendradar/context.py` (`AppContext`) — central dependency container
  - Holds config dict, timezone, platform list, storage manager
  - Provides methods for time, storage, frequency analysis, report generation
  - Eliminates global state; improves testability

### 3. Crawler Layer (Data Ingestion)
- `trendradar/crawler/base.py` — `CrawlerPlugin` ABC + `FetchedItem`/`CrawlResult` dataclasses
- `trendradar/crawler/registry.py` — `CrawlerRegistry` auto-discovers plugins via `pkgutil`
- `trendradar/crawler/plugins/*.py` — individual data source implementations (9 plugins)
- `trendradar/crawler/fetcher.py` — `DataFetcher` orchestrates crawling with proxy support
- `trendradar/crawler/pool.py` — connection pooling
- `trendradar/crawler/extra_apis.py` — concurrent extra API source crawling
- `trendradar/crawler/middleware/` — circuit breaker, rate limiter
- `trendradar/crawler/rss/` — RSS feed fetching and parsing

### 4. Storage Layer
- `trendradar/storage/base.py` — `StorageBackend` ABC + `NewsData`/`RSSData`/`NewsItem`/`RSSItem` dataclasses
- `trendradar/storage/local.py` — SQLite backend (news + RSS schemas)
- `trendradar/storage/remote.py` — S3-compatible backend via boto3
- `trendradar/storage/manager.py` — `StorageManager` auto-selects backend by environment
- `trendradar/storage/sqlite_mixin.py` — shared SQLite operations

### 5. Analysis Layer
- `trendradar/core/frequency.py` — keyword frequency counting, word group matching
- `trendradar/core/analyzer.py` — keyword↔platform stats conversion
- `trendradar/core/trend.py` — `TrendAnalyzer` compares current vs previous crawl for trend detection
- `trendradar/core/pipeline.py` — `run_analysis_pipeline()` orchestrates stats→AI→HTML
- `trendradar/core/mode_strategy.py` — report mode strategies (incremental/current/daily)

### 6. AI Layer
- `trendradar/ai/client.py` — `AIClient` wrapping LiteLLM for 100+ providers
- `trendradar/ai/analyzer.py` — AI news analysis
- `trendradar/ai/translator.py` — AI content translation
- `trendradar/ai/formatter.py` — AI result formatting

### 7. Report Layer
- `trendradar/report/generator.py` — report data preparation
- `trendradar/report/html.py` — main HTML report rendering
- `trendradar/report/html_sections.py` — section-level HTML components
- `trendradar/report/html_styles.py` — CSS styles
- `trendradar/report/html_scripts.py` — JavaScript for interactivity
- `trendradar/report/rss_html.py` — RSS-specific HTML reports
- `trendradar/report/helpers.py` — shared formatting utilities

### 8. Notification Layer
- `trendradar/notification/dispatcher.py` — `NotificationDispatcher` with channel dispatch table
- `trendradar/notification/channels/*.py` — per-channel send implementations (9 channels)
- `trendradar/notification/splitter.py` — content splitting for message size limits
- `trendradar/notification/renderer.py` — channel-specific content rendering
- `trendradar/notification/push_manager.py` — `PushRecordManager` tracks push state (once-per-day, windows)
- `trendradar/notification/batch.py` — batch message assembly

### 9. Web UI Layer
- `trendradar/webui/app.py` — Flask app factory
- `trendradar/webui/routes_*.py` — Blueprint routes (config, jobs, pages, workflow, misc)
- `trendradar/webui/job_manager.py` — background job execution
- `trendradar/webui/templates/*.html` — Jinja2 templates
- `trendradar/webui/static/` — CSS and JS assets

### 10. MCP Server Layer
- `mcp_server/server.py` — FastMCP 2.0 application with resources and tools
- `mcp_server/tools/*.py` — tool implementations (data query, analytics, search, config, system, storage sync, article reader)
- `mcp_server/services/*.py` — shared services (cache, data, parser)
- `mcp_server/utils/*.py` — date parsing, error handling, validators

## Entry Points

| Entry | Module | Purpose |
|-------|--------|---------|
| `python -m trendradar` | `trendradar/__main__.py:main()` | CLI: crawl + analyze + report + notify |
| `trendradar` | same as above | Installed script entry |
| `trendradar-mcp` | `mcp_server/server.py:run_server()` | MCP server |
| `python run_webui.py` | `trendradar/webui/app.py:create_app()` | Flask web UI |

## Data Flow

```
1. NewsAnalyzer.run()
   ├── _crawl_data()           → platforms → results dict
   ├── _crawl_rss_data()       → RSS feeds → rss_items list
   ├── _crawl_extra_apis()     → extra API sources → merged into results
   ├── _analyze_trends()       → compare current vs previous crawl
   └── _execute_mode_strategy()
       ├── _load_analysis_data()    → read today's stored data
       ├── _run_analysis_pipeline()
       │   ├── count_frequency()     → keyword stats
       │   ├── run_ai_analysis()     → AI summary (optional)
       │   └── generate_html()       → HTML report file
       └── _send_notification_if_needed()
           └── NotificationDispatcher.dispatch_all()
```

## Key Design Decisions

1. **AppContext as DI container** — all config-dependent ops flow through `AppContext`, no global state
2. **Plugin registry** — crawlers auto-discovered via `pkgutil`, registered by `source_type`
3. **Mode strategies** — 3 report modes (incremental/current/daily) determine data filtering and push behavior
4. **Multi-account notifications** — `;`-separated config values enable multiple accounts per channel
5. **Storage abstraction** — local SQLite and remote S3 share the same `StorageBackend` interface
6. **LiteLLM unification** — single AI client supports 100+ providers with fallback models
