# Concerns & Technical Debt

## Security

### Medium: Default Credentials in Config
`config/config.yaml` contains placeholder credentials:
- `ai.api_key: whoisyourai` (line 31)
- `ai.api_base: http://127.0.0.1:8317/v1` (line 32)
- Various empty webhook URLs and tokens

**Risk:** Users may forget to change defaults. The placeholder `whoisyourai` could be mistaken for a real key.

### Medium: No Input Sanitization on Web UI
`trendradar/webui/routes_config.py` handles config updates from web forms. No evidence of CSRF protection or input validation beyond Pydantic models.

### Low: No Authentication on Web UI
The Flask web UI (`trendradar/webui/app.py`) has no authentication. Bound to `127.0.0.1` by default, but Docker exposes the port.

## Architecture

### Large Main Module
`trendradar/__main__.py` is 835 lines. The `NewsAnalyzer` class (lines 45-660) has many methods and orchestrates the entire pipeline. While methods have been extracted to `core/pipeline.py` and `core/mode_strategy.py`, the class still acts as a god object.

### Mutable Config Dict
Despite Pydantic models existing in `trendradar/models/config.py`, the runtime still passes a mutable `Dict` through `AppContext`. The Pydantic models are used for validation but converted back to dicts via `to_dict()`. This creates two parallel config representations.

### Storage Manager Singleton
`trendradar/storage/manager.py:19` has a module-level `_storage_manager` singleton pattern that could cause issues in testing or multi-context scenarios.

## Code Quality

### Inconsistent Language
- Code comments and docstrings are in Chinese
- Some module docstrings are in English (e.g., `trendradar/webui/app.py`)
- `AGENTS.md` and `README-EN.md` are in English
- Mixed language makes onboarding harder for non-Chinese speakers

### Inline HTML Generation
`trendradar/report/html.py`, `html_sections.py`, `html_styles.py`, `html_scripts.py` generate HTML by string concatenation. No templating engine (Jinja2 is only used for web UI). This makes report HTML fragile to edit.

### Config Key Case Transformation
Config keys are lowercase in YAML but UPPERCASE in Python. This transformation happens in `trendradar/core/config.py` and creates a non-obvious mapping that must be remembered.

## Performance

### Sequential Crawling
The main crawler (`trendradar/crawler/fetcher.py`) appears to crawl platforms sequentially with `request_interval` delays. Extra APIs use concurrent crawling (`crawl_extra_sources_concurrent`), but the primary hotlist crawl is serial.

### SQLite for Storage
Using SQLite as the primary local storage backend. Fine for single-process access but could be a bottleneck if multiple processes (e.g., web UI + crawler) access simultaneously.

## Testing Gaps

### No Coverage Measurement
No `pytest-cov` or coverage configuration. Actual test coverage is unknown.

### No MCP Server Tests
`mcp_server/` has no test files. All 7 tool modules and the server are untested.

### No E2E Pipeline Tests
No test exercises the full `crawl → store → analyze → report → notify` pipeline.

### Minimal Mocking
Test files don't appear to use extensive mocking for external services (HTTP calls, AI APIs). Tests may require network access or fail silently.

## Dependencies

### Pinned tenacity
`tenacity==8.5.0` is pinned to exact version while all other deps use ranges. This could cause resolution conflicts.

### Heavy boto3 Dependency
`boto3>=1.35.0` is a runtime dependency even when S3 storage is not used. Could be made optional.

### requirements.txt vs pyproject.toml Drift
`requirements.txt` lists 11 packages while `pyproject.toml` lists 13 (missing `structlog` and `pydantic` from requirements.txt). Users installing via `pip install -r requirements.txt` won't get all dependencies.

## Fragile Areas

### Report HTML Generation
String-based HTML construction in `trendradar/report/` is fragile. Any change to CSS classes, section ordering, or JavaScript requires careful manual coordination across 4-5 files.

### Config Loading Pipeline
The YAML → dict → UPPERCASE → Pydantic → dict chain has many transformation steps. Bugs in key mapping are hard to trace.

### Push Window Logic
`trendradar/notification/push_manager.py` manages once-per-day push state and time windows. Complex state logic with timezone-aware comparisons is error-prone.
