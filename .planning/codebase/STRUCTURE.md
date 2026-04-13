# Directory Structure

## Top-Level Layout

```
TrendRadar/
├── trendradar/              # Core Python package
│   ├── __init__.py          # Version: 5.5.3
│   ├── __main__.py          # CLI entry point (NewsAnalyzer)
│   ├── context.py           # AppContext — central DI container
│   ├── ai/                  # AI analysis & translation
│   ├── core/                # Business logic (config, analysis, pipeline)
│   ├── crawler/             # Data ingestion (plugins, RSS, middleware)
│   ├── logging/             # structlog configuration
│   ├── models/              # Pydantic config models
│   ├── notification/        # Multi-channel notification dispatch
│   ├── report/              # HTML report generation
│   ├── storage/             # SQLite + S3 storage backends
│   ├── utils/               # Time and URL utilities
│   └── webui/               # Flask web management UI
├── mcp_server/              # MCP server (separate package)
│   ├── server.py            # FastMCP 2.0 app
│   ├── tools/               # MCP tool implementations
│   ├── services/            # Shared services (cache, data, parser)
│   └── utils/               # MCP-specific utilities
├── config/                  # Configuration files
│   ├── config.yaml          # Main config (platforms, RSS, AI, notifications, storage)
│   ├── ai_analysis_prompt.txt
│   ├── ai_translation_prompt.txt
│   └── frequency_words.txt  # Keyword matching rules
├── tests/                   # pytest test suite
├── docker/                  # Docker build and compose files
├── docs/                    # Documentation and guides
├── output/                  # Generated data (SQLite, HTML, TXT)
│   ├── news/                # Daily news SQLite databases
│   ├── rss/                 # Daily RSS SQLite databases
│   ├── html/                # Generated HTML reports
│   └── index.html           # Public report viewer
├── .github/                 # GitHub Actions workflows and issue templates
├── _image/                  # README images and assets
├── pyproject.toml           # Project metadata and dependencies
├── requirements.txt         # Runtime dependencies (flat)
├── requirements-dev.txt     # Dev dependencies
└── AGENTS.md                # AI agent guidelines
```

## Key Locations

### Configuration
- `config/config.yaml` — all runtime settings
- `trendradar/models/config.py` — Pydantic typed config models
- `trendradar/core/config.py` — config loading and normalization

### Crawler Plugins
- `trendradar/crawler/plugins/*.py` — one file per data source (9 plugins)
- `trendradar/crawler/base.py` — `CrawlerPlugin` ABC
- `trendradar/crawler/registry.py` — auto-discovery via `pkgutil`

### Notification Channels
- `trendradar/notification/channels/*.py` — one file per channel (9 channels)
- `trendradar/notification/channels/base.py` — channel base class
- `trendradar/notification/dispatcher.py` — dispatch orchestration

### Storage Schemas
- `trendradar/storage/schema.sql` — news data schema
- `trendradar/storage/rss_schema.sql` — RSS data schema

### Web UI
- `trendradar/webui/templates/*.html` — 10 Jinja2 templates
- `trendradar/webui/static/css/style.css` — UI styles
- `trendradar/webui/static/js/main.js` — UI scripts

### MCP Tools
- `mcp_server/tools/*.py` — 7 tool modules (data_query, analytics, search, config_mgmt, system, storage_sync, article_reader)

## Naming Conventions

- **Modules:** snake_case (e.g., `circuit_breaker.py`, `rate_limiter.py`)
- **Classes:** PascalCase (e.g., `NewsAnalyzer`, `AppContext`, `CrawlerPlugin`)
- **Config keys:** lowercase in YAML, UPPERCASE in Python dict after loading
- **Database files:** date-based naming (e.g., `output/news/2026-02-04.db`)
- **HTML reports:** `output/html/{date}/{time}.html`
- **Blueprint routes:** `routes_{domain}.py` (e.g., `routes_config.py`, `routes_jobs.py`)
