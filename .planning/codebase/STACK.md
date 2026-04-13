# Technology Stack

## Language & Runtime

- **Language:** Python 3.10+
- **Package Manager:** pip (with `pyproject.toml` + hatchling build backend)
- **Entry Points:**
  - `trendradar` → `trendradar/__main__.py:main`
  - `trendradar-mcp` → `mcp_server/server.py:run_server`
  - `python run_webui.py` → Flask web UI

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

Key env vars override config values:
- `AI_API_KEY`, `AI_MODEL`, `AI_API_BASE` — AI provider config
- `FEISHU_WEBHOOK_URL`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` — notification channels
- `S3_ENDPOINT_URL`, `S3_BUCKET_NAME`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY` — remote storage
- `CRON_SCHEDULE`, `RUN_MODE`, `IMMEDIATE_RUN` — Docker scheduling
- `ENABLE_WEBSERVER`, `WEBSERVER_PORT` — Web UI
- `STORAGE_RETENTION_DAYS` — data retention override
- `GITHUB_ACTIONS` — CI detection
- `DOCKER_CONTAINER` — container detection

## Deployment Targets

1. **GitHub Actions** — scheduled cron workflow (`.github/workflows/crawler.yml`), 7-day trial cycle with check-in
2. **Docker** — `docker/docker-compose.yml`, images `wantcat/trendradar` and `wantcat/trendradar-mcp`
3. **Local** — direct `python -m trendradar` or `trendradar` CLI
4. **Web UI** — Flask server via `python run_webui.py`
