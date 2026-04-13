# Coding Conventions

## Language & Style

- **Python version:** 3.10+ (uses `list[...]` type hints, `match` not observed)
- **Style:** PEP 8, 4-space indentation
- **Type hints:** used in function signatures and dataclass fields; `from __future__ import annotations` in newer modules
- **Encoding header:** `# coding=utf-8` at top of most files
- **Docstrings:** Chinese language docstrings throughout (project targets Chinese users)

## Code Patterns

### Dataclasses with Immutability
Crawler data models use frozen/slots dataclasses:
```python
@dataclass(frozen=True, slots=True)
class FetchedItem:
    title: str
    url: str = ""
    rank: int = 0
```
See: `trendradar/crawler/base.py:9-15`

### Pydantic Models with Env Overrides
Config models use `model_validator(mode="after")` to apply env var overrides:
```python
class CrawlerConfig(BaseModel):
    model_config = ConfigDict(extra="allow")
    api_url: str = Field(default="")

    @model_validator(mode="after")
    def _apply_env(self) -> "CrawlerConfig":
        override = _env_str("CRAWLER_API_URL")
        if override is not None:
            self.api_url = override
        return self
```
See: `trendradar/models/config.py:56-76`

### Plugin Registry Pattern
Crawlers register via decorator/class method, auto-discovered by pkgutil:
```python
CrawlerRegistry.register(MyPlugin)  # or as decorator
CrawlerRegistry.discover()  # auto-import all plugins/*
```
See: `trendradar/crawler/registry.py`

### AppContext as DI Container
All config-dependent operations flow through `AppContext` instead of global state:
```python
ctx = AppContext(config)
now = ctx.get_time()
storage = ctx.get_storage_manager()
```
See: `trendradar/context.py:45-65`

### Channel Dispatch Table
Notification channels defined as data-driven dispatch table (list of dicts):
```python
_SIMPLE_CHANNELS = [
    {"name": "feishu", "send_func": send_to_feishu, "config_key": "FEISHU_WEBHOOK_URL", ...},
    ...
]
```
See: `trendradar/notification/dispatcher.py:54-80`

### Pure Functions Extracted from Classes
Pipeline functions extracted as module-level functions with explicit parameters (no `self`):
```python
def run_analysis_pipeline(ctx, data_source, mode, ...) -> Tuple[...]:
```
See: `trendradar/core/pipeline.py:161-270`

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
