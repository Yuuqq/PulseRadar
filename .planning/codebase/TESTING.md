# Testing

## Framework & Setup

- **Framework:** pytest (>=8.0)
- **Config:** `pyproject.toml` `[tool.pytest.ini_options]`
  - `testpaths = ["tests"]`
  - `norecursedirs = [".git", ".venv", "output", "_image"]`
- **conftest.py:** `tests/conftest.py` — adds project root to `sys.path` for importlib mode compatibility
- **Dev deps:** `requirements-dev.txt` (separate from runtime)
- **Run:** `python -m pytest -q`

## Test Files

| File | Tests |
|------|-------|
| `tests/test_ai_client.py` | AI client (LiteLLM wrapper) |
| `tests/test_ai_parse.py` | AI response parsing |
| `tests/test_crawler_base.py` | Crawler base classes |
| `tests/test_crawler_pool.py` | Connection pooling |
| `tests/test_crawler_registry.py` | Plugin registry |
| `tests/test_dispatcher.py` | Notification dispatcher |
| `tests/test_history.py` | History/storage operations |
| `tests/test_loader.py` | Config loading |
| `tests/test_middleware.py` | Circuit breaker, rate limiter |
| `tests/test_notification_service.py` | Notification service |
| `tests/test_pipeline.py` | Analysis pipeline |
| `tests/test_pydantic_config.py` | Pydantic config models |
| `tests/test_splitter.py` | Content splitting |
| `tests/test_trend.py` | Trend analysis |
| `tests/test_webui_app_jobs.py` | Web UI app + jobs |
| `tests/test_webui_job_manager.py` | Job manager |

## Test Patterns

- **Unit-level focus:** tests target individual modules (config loading, parsing, dispatching)
- **No fixtures beyond conftest:** minimal shared fixtures, mostly inline setup
- **No mocking framework observed:** tests likely use direct assertions or unittest.mock
- **No integration/E2E tests:** no Playwright, no Docker-based tests

## Coverage

- **No coverage configuration** in `pyproject.toml`
- **No coverage tool** in dependencies (no pytest-cov)
- **16 test files** covering core subsystems

## Gaps

- No E2E tests for the full crawl→report→notify pipeline
- No coverage measurement configured
- No test fixtures for mock HTTP responses (crawler tests)
- Web UI tests exist but no browser-based testing
- MCP server has no dedicated tests
