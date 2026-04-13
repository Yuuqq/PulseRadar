<!-- GSD:project-start source:PROJECT.md -->
## Project

**TrendRadar — Tech Debt Milestone**

TrendRadar is a news aggregation and analysis tool that crawls 20+ Chinese and international hot list platforms, 60+ RSS feeds, and extra API sources, then produces HTML reports with AI-powered analysis and delivers notifications via 9 channels. This milestone focuses on reducing accumulated technical debt: extracting the god object, building comprehensive test coverage, and cleaning up dependency management.

**Core Value:** Reduce technical debt without breaking any existing user-facing behavior — all CLI arguments, config.yaml files, and Docker deployments must continue working identically.

### Constraints

- **CLI compatibility**: `python -m trendradar` and all CLI arguments must keep working
- **Config compatibility**: Existing `config/config.yaml` files must work without migration
- **Docker compatibility**: Docker images and docker-compose files must keep working
- **Import compatibility**: Public imports used by MCP server and Web UI must not break
<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->
## Technology Stack

## Language & Runtime
- **Language:** Python 3.10+
- **Package Manager:** pip (with `pyproject.toml` + hatchling build backend)
- **Entry Points:**
## Core Dependencies
| Package | Version | Purpose |
|---------|---------|---------|
| requests | >=2.32.5,<3 | HTTP client for crawlers |
| PyYAML | >=6.0.3,<7 | Config file parsing (`config/config.yaml`) |
| pydantic | >=2.0,<3 | Typed config models (`trendradar/models/config.py`) |
| flask | >=3.0,<4 | Web UI server (`trendradar/webui/`) |
| litellm | >=1.57,<2 | Unified AI model client (100+ providers) |
| feedparser | >=6.0,<7 | RSS feed parsing |
| boto3 | >=1.35,<2 | S3-compatible remote storage |
| structlog | >=24.0,<26 | Structured logging |
| fastmcp | >=2.14,<3 | MCP server framework |
| mcp | >=1.23,<2 | MCP protocol support |
| websockets | >=15.0.1,<16 | WebSocket support for MCP |
| pytz | >=2025.2,<2026 | Timezone handling |
| tenacity | ==8.5.0 | Retry logic |
## Dev Dependencies
| Package | Version | Purpose |
|---------|---------|---------|
| pytest | >=8.0,<9 | Test framework |
## Build System
- **Build Backend:** hatchling
- **Wheel Packages:** `trendradar`, `mcp_server`
- **Config:** `pyproject.toml` (PEP 621)
## Configuration
- **Primary Config:** `config/config.yaml` (YAML)
- **Pydantic Models:** `trendradar/models/config.py` — typed config with env var overrides
- **Config Loader:** `trendradar/core/config.py` — loads YAML, normalizes keys to UPPERCASE
- **AI Prompts:** `config/ai_analysis_prompt.txt`, `config/ai_translation_prompt.txt`
- **Frequency Words:** `config/frequency_words.txt` — keyword matching rules
## Environment Variables
- `AI_API_KEY`, `AI_MODEL`, `AI_API_BASE` — AI provider config
- `FEISHU_WEBHOOK_URL`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` — notification channels
- `S3_ENDPOINT_URL`, `S3_BUCKET_NAME`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY` — remote storage
- `CRON_SCHEDULE`, `RUN_MODE`, `IMMEDIATE_RUN` — Docker scheduling
- `ENABLE_WEBSERVER`, `WEBSERVER_PORT` — Web UI
- `STORAGE_RETENTION_DAYS` — data retention override
- `GITHUB_ACTIONS` — CI detection
- `DOCKER_CONTAINER` — container detection
## Deployment Targets
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

## Language & Style
- **Python version:** 3.10+ (uses `list[...]` type hints, `match` not observed)
- **Style:** PEP 8, 4-space indentation
- **Type hints:** used in function signatures and dataclass fields; `from __future__ import annotations` in newer modules
- **Encoding header:** `# coding=utf-8` at top of most files
- **Docstrings:** Chinese language docstrings throughout (project targets Chinese users)
## Code Patterns
### Dataclasses with Immutability
### Pydantic Models with Env Overrides
### Plugin Registry Pattern
### AppContext as DI Container
### Channel Dispatch Table
### Pure Functions Extracted from Classes
## Error Handling
- **Try/except with structured logging:** errors logged via `structlog` with context fields
- **Graceful degradation:** failures in individual crawlers/channels don't halt the pipeline
- **Circuit breaker:** `trendradar/crawler/middleware/circuit_breaker.py` — auto-opens after N consecutive failures
- **Rate limiter:** `trendradar/crawler/middleware/rate_limiter.py`
- **Retry via tenacity:** available but not heavily used in main code
## Logging
- **Framework:** structlog (`trendradar/logging/setup.py`)
- **Pattern:** `logger = get_logger(__name__)` per module
- **Output:** console renderer (colored when TTY) or JSON for production
- **Context:** key-value pairs in log calls: `logger.info("message", key=value)`
## Configuration Key Convention
- YAML uses lowercase snake_case: `ai.api_key`, `advanced.crawler.request_interval`
- Python dict uses UPPERCASE after loading: `config["AI"]["API_KEY"]`
- Environment variables use UPPERCASE with underscores: `AI_API_KEY`
## File Organization
- Feature-based package structure (crawler, notification, storage, report, ai)
- One file per channel/plugin where practical
- Shared utilities in per-package `utils/` or top-level `trendradar/utils/`
- `__init__.py` re-exports key symbols for convenience
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

## Pattern
```
```
## Core Layers
### 1. Configuration Layer
- `trendradar/core/config.py` — YAML loading, key normalization (lowercase→UPPERCASE)
- `trendradar/models/config.py` — Pydantic models with env var override validators
- `config/config.yaml` — single source of truth for all settings
### 2. Application Context
- `trendradar/context.py` (`AppContext`) — central dependency container
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
```
## Key Design Decisions
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, or `.github/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
