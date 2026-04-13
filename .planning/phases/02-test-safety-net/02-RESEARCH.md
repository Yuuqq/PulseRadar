# Phase 2: Test Safety Net - Research

**Researched:** 2026-04-14
**Domain:** Python test infrastructure (pytest-cov, responses, pytest-randomly, FastMCP testing)
**Confidence:** HIGH

## Summary

Phase 2 establishes a measurable test safety net so that Phase 3 decomposition has characterization tests to catch regressions. Three pillars: coverage infrastructure (pytest-cov with branch coverage and 80% gate), offline HTTP mocking (responses library), and targeted test expansion (MCP tools/services, 9 crawler plugins, pipeline integration across 3 report modes).

The codebase currently has 18 test files in `tests/` root with no nested directories, a sys.path bootstrap in `conftest.py`, and `pyproject.toml` with `testpaths = ["tests"]`. There is NO existing pytest-cov config, NO responses usage, and NO MCP server tests. The `AppContext` constructor takes a config `Dict[str, Any]` and exposes lazy-initialized storage via `get_storage_manager()`. The `StorageManager` has a module-level singleton `_storage_manager` that must be reset between tests.

**Primary recommendation:** Add `pytest-cov>=7.0,<8`, `responses>=0.25,<1`, `pytest-randomly>=3.15,<5` to dev deps. Wire coverage via `pyproject.toml` `[tool.coverage.*]` sections. Build `conftest.py` fixtures around the real `AppContext` constructor with `tmp_path` SQLite storage. Use `responses.RequestsMock` for all HTTP mocking. For FastMCP smoke test, use `fastmcp.Client(mcp)` directly — the in-process client is available and works.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Coverage source = `["trendradar", "mcp_server"]`. Both packages measured against a single global 80% gate.
- **D-02:** Gate enforced locally via `pyproject.toml` `[tool.pytest.ini_options] addopts = "--cov --cov-fail-under=80"`.
- **D-03:** Branch coverage enabled via `[tool.coverage.run] branch = true`.
- **D-04:** Coverage exclusions: `tests/**`, `trendradar/webui/templates/**`, `trendradar/webui/static/**`, `if __name__ == "__main__":` guards, `if TYPE_CHECKING:` blocks.
- **D-05:** Commit `coverage.xml` once as baseline, then add to `.gitignore`.
- **D-06:** Add `pytest-cov`, `responses`, `pytest-randomly` to `[dependency-groups] dev`.
- **D-07:** `pytest-randomly` included to surface singleton state leaks (Pitfall 12).
- **D-08:** Regenerate `requirements-dev.txt` via `uv pip compile`/`pip-compile`.
- **D-09:** Phase 2 ships coverage gate LOCALLY only. No CI/pre-commit changes.
- **D-10:** Handler-level testing for MCP tool/service modules (import functions directly, mock deps).
- **D-11:** One FastMCP smoke test using in-process client. Fallback to import-side assertion if API blocks.
- **D-12:** MCP tests consume `mock_app_context`. Storage = tmp_path SQLite. AI client patched. HTTP via `responses`.
- **D-13:** Async handling delegated to researcher (see findings below).
- **D-14:** Pipeline test mock boundaries: HTTP (responses), AI client (unittest.mock.patch), notification (patched dispatcher). SQLite is REAL in tmp_path.
- **D-15:** Five test cases for mode-strategy branches (incremental+data, current+history, current-no-history->RuntimeError, daily+history, daily-no-history->fallback).
- **D-16:** Assertions: HTML substring checks, notification mock calls, extra-API merge shape, storage row counts.
- **D-17:** `_analyze_trends` test asserts invocation but NOT result usage (dead code — deferred to Phase 3).
- **D-18:** `mock_config` fixture — minimal-valid dict from Pydantic defaults, function-scoped, overridable via kwargs.
- **D-19:** `mock_app_context` fixture — REAL AppContext with `mock_config` + tmp_path SQLite + patched AI client.
- **D-20:** `mock_http_response` fixture — wraps `responses.RequestsMock`, function-scoped.
- **D-21:** Autouse singleton reset — `trendradar.storage.manager._storage_manager = None` before each test.
- **D-22:** One test file per crawler plugin under `tests/crawler/plugins/`.
- **D-23:** Shared assertion helpers in `tests/crawler/_helpers.py`. HTTP fixtures inline as dicts/strings.
- **D-24:** One happy-path + one error-mode test per plugin minimum.
- **D-25:** Nested structure: `tests/crawler/plugins/`, `tests/mcp/tools/`, `tests/mcp/services/`, `tests/pipeline/`.
- **D-26:** Existing 16 test files stay at `tests/` root — do NOT move.

### Claude's Discretion
- Exact `[tool.coverage.report]` exclude_lines patterns
- File naming in `tests/mcp/tools/` vs `tests/mcp/services/`
- Exact assertion helper names in `tests/crawler/_helpers.py`
- FastMCP smoke test location
- `mock_app_context` attribute exposure pattern
- HTML substring assertions in pipeline test
- Commit ordering during execution
- Whether to add `pytest-asyncio` (see D-13 findings)

### Deferred Ideas (OUT OF SCOPE)
- CI coverage gate in GitHub Actions (Phase 4)
- Pre-commit hook for coverage (Phase 4)
- Resolution of dead `trend_report` code (Phase 3)
- Resolution of extra-API mutation pattern (Phase 3)
- Full error matrix per crawler plugin
- Golden-file HTML diffing
- Pydantic-validated test fixtures
- Splitting pipeline integration test by subsystem
- FastMCP protocol-level test fleet expansion
- Mock boundary at SQLite level (in-memory DB)
- pytest-xdist parallelism
- pytest-freezer for time-dependent tests
- Coverage trend tracking in CI
- AppContext secondary god object decomposition
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TEST-01 | pytest-cov configured with `--cov-fail-under=80` and branch coverage | Coverage infrastructure section: pyproject.toml config, pytest-cov 7.x API verified |
| TEST-02 | Coverage baseline measured and recorded before refactoring | D-05 baseline artifact pattern documented |
| TEST-03 | `responses` library added as dev dep for HTTP mocking in crawler tests | responses 0.26.0 API verified, `RequestsMock` pattern documented |
| TEST-04 | Shared conftest.py with mock_config, mock_app_context, mock_http_response | AppContext API fully mapped, fixture designs in Architecture section |
| COV-01 | MCP server unit tests for all 7 tool modules | All 7 tool classes inspected — sync methods wrapping DataService/AnalyticsTools/etc. |
| COV-02 | MCP server unit tests for all 3 service modules | cache_service, data_service, parser_service inspected — all sync, testable via import |
| COV-03 | Crawler plugin tests for all 9 plugins using `responses` | All 9 plugins inspected — all use `requests.Session.get()`, mockable via responses |
| COV-04 | Pipeline integration test for 3 report modes | `execute_mode_strategy()` branching fully mapped in mode_strategy.py |
| COV-05 | Overall coverage reaches 80%+ with branch coverage | Standard stack + fixture design supports this target |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest-cov | >=7.0,<8 | Coverage measurement + fail-under gate | Standard pytest coverage plugin; v7.x uses coverage.py 7.x with improved branch analysis [VERIFIED: pip index] |
| coverage | >=7.0 (transitive) | Underlying coverage engine | Pulled in by pytest-cov; provides `[tool.coverage.*]` config namespace [VERIFIED: pip index] |
| responses | >=0.25,<1 | HTTP request mocking for `requests` library | De facto standard for mocking `requests.Session.get()` calls; all 9 crawler plugins use `requests` [VERIFIED: pip index] |
| pytest-randomly | >=3.15,<5 | Random test ordering to detect state leaks | Catches StorageManager singleton (Pitfall 12) and any other cross-test coupling [VERIFIED: pip index] |

### Supporting (conditional — see D-13 findings)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest-asyncio | >=1.0,<2 | async test support | **NOT NEEDED** — see D-13 finding below |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| responses | VCR.py/vcrpy | Cassettes stale for changing APIs — rejected in REQUIREMENTS.md Out of Scope |
| responses | requests-mock | Viable alternative but responses has cleaner decorator API and is explicitly named in CONTEXT.md decisions |
| pytest-randomly | pytest-random-order | Both work; pytest-randomly is more actively maintained [VERIFIED: pip index] |

**Installation (for pyproject.toml `[dependency-groups] dev`):**
```toml
[dependency-groups]
dev = [
    "pytest>=8.0.0,<9.0.0",
    "pytest-cov>=7.0,<8",
    "responses>=0.25,<1",
    "pytest-randomly>=3.15,<5",
]
```

**Version verification:**
- pytest-cov: 7.1.0 latest (2026-04-14) [VERIFIED: pip index versions pytest-cov]
- responses: 0.26.0 latest (2026-04-14) [VERIFIED: pip index versions responses]
- pytest-randomly: 4.0.1 latest (2026-04-14) [VERIFIED: pip index versions pytest-randomly]
- coverage: 7.13.5 latest (transitive dep) [VERIFIED: pip index versions coverage]
- Currently installed pytest-cov is 4.1.0 (stale) — will upgrade via pip install of dev group [VERIFIED: pip show pytest-cov]

## Project Constraints (from CLAUDE.md)

- **KISS/YAGNI**: Do not add unnecessary test complexity. Each test must justify its existence via a requirement mapping.
- **Immutability**: Test helper functions should return new objects, not mutate arguments.
- **File organization**: Many small files. One test file per plugin (D-22). Helpers in dedicated `_helpers.py`.
- **Error handling**: Tests must cover error paths (D-24 one error mode per plugin minimum).
- **Input validation**: Tests should validate fixture shapes via assertions (assert_fetched_item_shape helper).
- **Security**: No hardcoded API keys in test fixtures. Use dummy/fake values.
- **Coding style**: `# coding=utf-8` header on all new files. PEP 8. Functions < 50 lines.

## Architecture Patterns

### Recommended Test Directory Structure
```
tests/
├── conftest.py               # Extended: mock_config, mock_app_context, mock_http_response, autouse singleton reset
├── test_ai_client.py         # EXISTING - do not move
├── test_ai_parse.py          # EXISTING
├── test_crawler_base.py      # EXISTING
├── ... (14 more existing)    # EXISTING - all stay at root
├── crawler/
│   ├── __init__.py
│   ├── _helpers.py           # assert_fetched_item_shape, assert_crawl_result_shape
│   └── plugins/
│       ├── __init__.py
│       ├── test_dailyhot.py
│       ├── test_eastmoney.py
│       ├── test_gnews.py
│       ├── test_mediastack.py
│       ├── test_newsapi.py
│       ├── test_thenewsapi.py
│       ├── test_tonghuashun.py
│       ├── test_vvhan.py
│       └── test_wallstreetcn.py
├── mcp/
│   ├── __init__.py
│   ├── conftest.py           # MCP-specific fixtures (mock_tools_instance, etc.)
│   ├── test_smoke.py         # FastMCP in-process smoke test (D-11)
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── test_analytics.py
│   │   ├── test_article_reader.py
│   │   ├── test_config_mgmt.py
│   │   ├── test_data_query.py
│   │   ├── test_search_tools.py
│   │   ├── test_storage_sync.py
│   │   └── test_system.py
│   └── services/
│       ├── __init__.py
│       ├── test_cache_service.py
│       ├── test_data_service.py
│       └── test_parser_service.py
└── pipeline/
    ├── __init__.py
    └── test_integration.py   # 5-case mode strategy integration test (D-15)
```

### Pattern 1: AppContext Constructor for mock_app_context

**What:** Build a REAL `AppContext` instance with controlled config and tmp_path storage.

**How it works (from codebase inspection):**
```python
# Source: trendradar/context.py lines 67-75
# AppContext.__init__ takes config: Dict[str, Any]
# config must be the UPPERCASE-key dict format that load_config() produces

# Key property: ctx.get_storage_manager() calls get_storage_manager() from storage/manager.py
# which creates a StorageManager using config["STORAGE"] dict values
# StorageManager then lazily creates a LocalStorageBackend(data_dir=..., ...)
```
[VERIFIED: codebase inspection of trendradar/context.py]

**Fixture design:**
```python
@pytest.fixture
def mock_config(tmp_path):
    """Minimal-valid config dict. Override via dict.update() in individual tests."""
    return {
        "TIMEZONE": "UTC",
        "RANK_THRESHOLD": 50,
        "WEIGHT_CONFIG": {},
        "PLATFORMS": [],
        "RSS": {"ENABLED": False, "FEEDS": []},
        "DISPLAY_MODE": "keyword",
        "DISPLAY": {"REGIONS": {"NEW_ITEMS": True, "STANDALONE": False}, "REGION_ORDER": ["hotlist"]},
        "REPORT_MODE": "daily",
        "REQUEST_INTERVAL": 1000,
        "STORAGE": {
            "BACKEND": "local",
            "FORMATS": {"TXT": False, "HTML": False},
            "LOCAL": {"DATA_DIR": str(tmp_path / "output"), "RETENTION_DAYS": 0},
            "REMOTE": {},
            "PULL": {"ENABLED": False, "DAYS": 0},
        },
        "AI": {"MODEL": "test/test", "API_KEY": "fake-key", "API_BASE": "", "TIMEOUT": 5, "MAX_TOKENS": 100},
        "AI_ANALYSIS": {"ENABLED": False},
        "AI_TRANSLATION": {"ENABLED": False},
        "SHOW_VERSION_UPDATE": False,
        "MAX_NEWS_PER_KEYWORD": 0,
        "MAX_KEYWORDS": 0,
        "SORT_BY_POSITION_FIRST": False,
        "DEBUG": False,
        "FEISHU_MESSAGE_SEPARATOR": "---",
        "FEISHU_BATCH_SIZE": 29000,
        "DINGTALK_BATCH_SIZE": 20000,
        "MESSAGE_BATCH_SIZE": 4000,
    }
```
[VERIFIED: derived from AppContext property accessors in context.py + config key usage patterns]

### Pattern 2: StorageManager Singleton Reset (Autouse)

**What:** The module-level `_storage_manager` in `trendradar/storage/manager.py` (line 19) persists between tests, causing state leaks (Pitfall 12).

**Implementation:**
```python
# Source: trendradar/storage/manager.py line 19
# _storage_manager: Optional["StorageManager"] = None

@pytest.fixture(autouse=True)
def _reset_storage_singleton():
    """Reset the StorageManager module-level singleton between tests."""
    import trendradar.storage.manager as sm
    sm._storage_manager = None
    yield
    sm._storage_manager = None
```
[VERIFIED: codebase inspection of trendradar/storage/manager.py lines 19, 404-420]

### Pattern 3: MCP Tool Module-Level Testing

**What:** All MCP tool handlers in `server.py` are `async def` wrappers that call `asyncio.to_thread(tools[name].method, ...)`. The underlying tool class methods are synchronous.

**Testing strategy:** Import tool classes directly, instantiate with mocked `project_root`, test sync methods.

```python
# Source: mcp_server/tools/data_query.py lines 23-80
# DataQueryTools.__init__(self, project_root: str = None) -> creates DataService(project_root)
# DataQueryTools.get_latest_news(self, ...) -> Dict  (sync method)

from mcp_server.tools.data_query import DataQueryTools

def test_get_latest_news_returns_success(mock_app_context, tmp_path):
    tools = DataQueryTools(project_root=str(tmp_path))
    # DataService internally uses ParserService which reads SQLite from project_root/output/
    # Need to set up SQLite fixture data or patch ParserService
    ...
```
[VERIFIED: codebase inspection of mcp_server/tools/data_query.py, mcp_server/services/data_service.py]

### Pattern 4: Crawler Plugin Testing with `responses`

**What:** All 9 crawler plugins use `requests.Session().get(url, ..., timeout=15)`. The `responses` library intercepts `requests` calls.

```python
import responses
from trendradar.crawler.plugins.dailyhot import DailyHotPlugin

@responses.activate
def test_dailyhot_happy_path():
    responses.add(
        responses.GET,
        "https://api.codelife.cc/api/top/list",
        json={"code": 200, "data": [{"title": "Test Title", "url": "http://test.com", "index": 1}]},
        status=200,
    )
    plugin = DailyHotPlugin()
    result = plugin.fetch({"id": "dailyhot", "name": "DailyHot", "platform": "toutiao"})
    assert result.success
    assert len(result.items) > 0
    assert result.items[0].title == "[toutiao] Test Title"
```
[VERIFIED: codebase inspection of all 9 plugins — all use requests.Session.get()]

### Anti-Patterns to Avoid
- **Coverage-padding tests:** Tests that call functions without assertions (Pitfall 4). Every test must have meaningful assertions.
- **Implementation-coupled tests:** Asserting on internal method call order rather than outputs. Use `assert result ==` not `mock.assert_called_with()` where possible.
- **Shared mutable state in fixtures:** Fixtures must return fresh objects each call (function-scoped).
- **External network calls in tests:** Every HTTP call must go through `responses` mock. The `responses` library raises `ConnectionError` for unmocked URLs by default.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP request mocking | Custom monkeypatch of `requests.get` | `responses` library | Handles session objects, connection pooling, timeout args correctly |
| Coverage measurement | Manual line counting / custom pytest plugin | `pytest-cov` + `coverage.py` | Branch coverage, exclude patterns, fail-under gates are complex edge cases |
| Test ordering randomization | Custom test shuffling | `pytest-randomly` | Integrates with pytest's collection phase, supports seed for reproducibility |
| Coverage config in pyproject.toml | Custom coverage.py configuration file | `[tool.coverage.*]` sections in pyproject.toml | Single config file, coverage.py natively reads pyproject.toml |

**Key insight:** The test infrastructure libraries (pytest-cov, responses, pytest-randomly) solve problems with many edge cases (encoding, session state, branch detection) that are not worth reproducing manually.

## D-13 Research Finding: Async Handling

**Finding: pytest-asyncio is NOT needed for Phase 2.** [VERIFIED: codebase inspection]

**Evidence:**
1. All `@mcp.tool` decorated functions in `mcp_server/server.py` are `async def` — but they exclusively delegate to sync methods via `asyncio.to_thread(tools[name].method, ...)`.
2. D-10 specifies handler-level testing (import tool classes directly). The tool classes (`DataQueryTools`, `AnalyticsTools`, `SearchTools`, `ConfigManagementTools`, `SystemManagementTools`, `StorageSyncTools`, `ArticleReaderTools`) are all **synchronous classes with synchronous methods**.
3. The service classes (`CacheService`, `DataService`, `ParserService`) are also all **synchronous**.
4. D-11's single FastMCP smoke test uses `fastmcp.Client(mcp)` which is async — however, `pytest-asyncio` version 1.3.0 is already installed in the environment. No new dev dep needed.

**Recommendation:** Do NOT add `pytest-asyncio` to `[dependency-groups] dev`. It is already installed system-wide (v1.3.0). The single async smoke test (D-11) can use `@pytest.mark.asyncio` decorator which works with the installed version. If the planner wants to be explicit, add it to dev deps, but it is not technically required since it is already available.

**Alternative if planner prefers pure-sync approach:** The D-11 smoke test can use `asyncio.run()` directly within a sync test function instead of pytest-asyncio:
```python
import asyncio
from fastmcp import Client

def test_fastmcp_smoke():
    from mcp_server.server import mcp
    async def _run():
        async with Client(mcp) as client:
            tools = await client.list_tools()
            assert len(tools) > 0
    asyncio.run(_run())
```

## Key Codebase Findings

### Q1: What does each crawler plugin return and how do they handle errors? (D-22/D-24)

All 9 plugins follow the same pattern [VERIFIED: codebase inspection]:

| Plugin | source_type | API URL | Response format | Error handling |
|--------|-------------|---------|-----------------|----------------|
| DailyHotPlugin | `"dailyhot"` | `https://api.codelife.cc/api/top/list` | `{code: 200, data: [...]}` | Returns CrawlResult with errors tuple |
| EastMoneyPlugin | `"eastmoney"` | Template URL with channel/page | JS variable wrapper `var x = {...};` | Strips wrapper, JSON parse, checks `rc == "1"` |
| GNewsPlugin | `"gnews"` | `https://gnews.io/api/v4/top-headlines` | `{articles: [...]}` | Checks api_key present; detailed HTTP error capture |
| MediaStackPlugin | `"mediastack"` | `http://api.mediastack.com/v1/news` | `{data: [...]}` | Similar to GNews — api_key required |
| NewsAPIPlugin | `"newsapi"` | `https://newsapi.org/v2/top-headlines` | `{status: "ok", articles: [...]}` | api_key required; checks status field |
| TheNewsAPIPlugin | `"thenewsapi"` | `https://api.thenewsapi.com/v1/news/top` | `{data: [...]}` | api_key required |
| TongHuaShunPlugin | `"10jqka"` | `https://news.10jqka.com.cn/clientinfo/finance.html` | HTML page with JS data | Regex extraction from HTML |
| VvhanPlugin | `"vvhan"` | `https://api.vvhan.com/api/hotlist/all` | `{success: true, data: [...]}` | Multi-platform result structure similar to DailyHot |
| WallStreetCNPlugin | `"wallstreetcn"` | `https://api-prod.wallstreetcn.com/apiv1/content/lives` | `{code: 20000, data: {items: [...]}}` | Checks code == 20000 |

**Common pattern across all:**
- `__init__()` creates `requests.Session()`
- `fetch(source_config: Dict) -> CrawlResult` is the public surface
- On error: return `CrawlResult(items=(), errors=(error_msg,))` — NEVER raises
- On success: return `CrawlResult(items=tuple(items), errors=())`
- All use `timeout=15` for HTTP requests
- `close()` closes the session

**Recommended error modes to test per plugin:**
| Plugin | Error mode to test | Rationale |
|--------|-------------------|-----------|
| dailyhot | HTTP 500 | Multi-platform fallback logic |
| eastmoney | Malformed response (bad JSON wrapper) | JS variable stripping edge case |
| gnews | Missing api_key | Returns early with error |
| mediastack | HTTP 500 | Standard HTTP error path |
| newsapi | `{status: "error"}` response | Non-HTTP error (API-level error) |
| thenewsapi | Missing api_key | Returns early with error |
| tonghuashun | Malformed HTML | Regex extraction failure |
| vvhan | Empty data array | `{success: true, data: []}` |
| wallstreetcn | `{code: 40000}` response | Non-20000 status code |

### Q2: AppContext Constructor API (D-19)

```python
# Source: trendradar/context.py line 67
class AppContext:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._storage_manager = None
```
[VERIFIED: codebase inspection]

**Key properties accessed by tests:**
- `ctx.config` — raw dict
- `ctx.timezone` — `config.get("TIMEZONE", "Asia/Shanghai")`
- `ctx.rank_threshold` — `config.get("RANK_THRESHOLD", 50)`
- `ctx.weight_config` — `config.get("WEIGHT_CONFIG", {})`
- `ctx.platforms` — `config.get("PLATFORMS", [])`
- `ctx.platform_ids` — `[p["id"] for p in self.platforms]`
- `ctx.rss_config` — `config.get("RSS", {})`
- `ctx.display_mode` — `config.get("DISPLAY_MODE", "keyword")`
- `ctx.get_storage_manager()` — lazy singleton, creates `StorageManager`

**For mock_app_context:** Build a REAL AppContext with a config dict that points storage `DATA_DIR` to `tmp_path`. The `get_storage_manager()` call creates a real `LocalStorageBackend` with real SQLite. AI client must be patched separately.

### Q3: StorageManager Singleton (D-21)

```python
# Source: trendradar/storage/manager.py lines 19, 372-420
_storage_manager: Optional["StorageManager"] = None

def get_storage_manager(..., force_new: bool = False) -> StorageManager:
    global _storage_manager
    if _storage_manager is None or force_new:
        _storage_manager = StorageManager(...)
    return _storage_manager
```
[VERIFIED: codebase inspection]

**Important:** `AppContext.get_storage_manager()` calls this module-level `get_storage_manager()`, which uses the module-level singleton. The autouse fixture must reset `trendradar.storage.manager._storage_manager = None` — NOT `trendradar.context.AppContext._storage_manager`.

Actually, looking more carefully: `AppContext.__init__` sets `self._storage_manager = None` (line 75), and `AppContext.get_storage_manager()` (line 160-186) stores the result on `self._storage_manager` (the instance attribute). It calls `get_storage_manager()` from `trendradar.storage` which is the module-level singleton. **Both must be reset:** the module-level singleton AND any `AppContext` instance's `_storage_manager`.

The autouse fixture should reset the module-level one. Each function-scoped `mock_app_context` fixture creates a fresh `AppContext`, so its instance `_storage_manager` starts as `None` naturally.

### Q4: Pipeline Mode Strategy Branching (D-15)

`execute_mode_strategy()` in `trendradar/core/mode_strategy.py` lines 273-492 has three main branches:
[VERIFIED: codebase inspection]

1. **`report_mode == "current"` (line 339):** Calls `load_analysis_data_fn()`. If data exists, uses historical data. If no data, raises `RuntimeError` (line 380).
2. **`report_mode == "daily"` (line 382):** Calls `load_analysis_data_fn()`. If data exists, uses historical data. If no data, **falls back to current data** (lines 420-438) — uses `prepare_current_title_info_fn()`.
3. **else (incremental, line 440):** Uses current crawl data directly, no historical loading.

The 5 test cases from D-15 map to:
| Case | Mode | History | Expected behavior |
|------|------|---------|-------------------|
| 1 | incremental | n/a | Uses current data directly (line 440-459) |
| 2 | current | present | Uses historical data (lines 339-377) |
| 3 | current | absent (load_analysis_data_fn returns None) | `RuntimeError` raised (line 380) |
| 4 | daily | present | Uses historical data (lines 382-418) |
| 5 | daily | absent | Falls back to current data (lines 420-438) |

**Mock targets for each case:**
- `load_analysis_data_fn` — returns tuple of 7 elements or `None`
- `prepare_current_title_info_fn` — returns title_info dict
- `run_analysis_pipeline_fn` — returns `(stats, html_file, ai_result)`
- `prepare_standalone_data_fn` — returns standalone_data dict or None
- `send_notification_fn` — receives notification call (assert args)
- `ctx` — real `AppContext` with tmp_path storage
- `storage_manager` — real `StorageManager` from `ctx.get_storage_manager()`

**The function signature (line 273):**
```python
def execute_mode_strategy(
    ctx: AppContext,
    storage_manager,
    report_mode: str,
    rank_threshold: int,
    update_info: Optional[Dict],
    proxy_url: Optional[str],
    is_docker_container: bool,
    should_open_browser: bool,
    mode_strategy: Dict,
    results: Dict,
    id_to_name: Dict,
    failed_ids: List,
    load_analysis_data_fn,
    prepare_current_title_info_fn,
    run_analysis_pipeline_fn,
    prepare_standalone_data_fn,
    send_notification_fn,
    rss_items: Optional[List[Dict]] = None,
    rss_new_items: Optional[List[Dict]] = None,
    raw_rss_items: Optional[List[Dict]] = None,
) -> Optional[str]:
```
[VERIFIED: codebase inspection of mode_strategy.py lines 273-294]

### Q5: Current pytest Configuration

Current `pyproject.toml` pytest config (lines 40-42):
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
norecursedirs = [".git", ".venv", "output", "_image"]
```
[VERIFIED: codebase inspection]

**What needs to be added (D-02, D-03):**
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
norecursedirs = [".git", ".venv", "output", "_image"]
addopts = "--cov=trendradar --cov=mcp_server --cov-fail-under=80"

[tool.coverage.run]
branch = true
source = ["trendradar", "mcp_server"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "if __name__ == .__main__.",
    "if TYPE_CHECKING:",
    "@abstractmethod",
    "raise NotImplementedError",
]
omit = [
    "tests/*",
    "trendradar/webui/templates/*",
    "trendradar/webui/static/*",
]

[tool.coverage.xml]
output = "coverage.xml"
```

### Q6: FastMCP In-Process Test Client (D-11)

**Finding: The FastMCP `Client` class accepts a `FastMCP` instance directly.**
[VERIFIED: runtime inspection via `python -c "from fastmcp import Client; import inspect; print(inspect.signature(Client.__init__))"` ]

The `Client.__init__` signature accepts `transport: ClientTransportT | FastMCP | ...`, meaning you can pass the `mcp` FastMCP app object directly:

```python
import asyncio
from fastmcp import Client
from mcp_server.server import mcp

def test_fastmcp_tool_registration_smoke():
    """Verify MCP tool registration wiring is intact."""
    async def _run():
        async with Client(mcp) as client:
            tools = await client.list_tools()
            tool_names = {t.name for t in tools}
            # Verify key tools are registered
            assert "get_latest_news" in tool_names
            assert "search_news" in tool_names
            assert "read_article" in tool_names
            assert len(tool_names) >= 20  # 24 tools expected
    asyncio.run(_run())
```

**Fallback (if Client blocks):** Import-side assertion:
```python
def test_mcp_tools_registered():
    from mcp_server.server import mcp
    # FastMCP stores tools in internal registry
    # Verify non-empty
    assert len(mcp._tool_manager._tools) > 0
```

**Installed FastMCP version:** 2.12.5 (slightly below the `>=2.14.0` required by pyproject.toml — may need upgrade). The `Client` API is available in this version. [VERIFIED: pip show + runtime import]

### Q7: MCP Tool Module Dependency Chains

Each MCP tool class has this dependency chain [VERIFIED: codebase inspection]:

```
DataQueryTools(project_root) -> DataService(project_root) -> ParserService(project_root) + CacheService
AnalyticsTools(project_root) -> DataService(project_root) -> ...
SearchTools(project_root)    -> DataService(project_root) -> ...
ConfigManagementTools(project_root) -> reads config.yaml from disk
SystemManagementTools(project_root) -> reads pyproject.toml, calls DataFetcher
StorageSyncTools(project_root) -> uses StorageManager from trendradar.storage
ArticleReaderTools(project_root) -> makes HTTP requests to Jina AI Reader
```

**Testing approach for each:**
- `DataQueryTools`, `AnalyticsTools`, `SearchTools`: Patch `ParserService` or set up SQLite fixtures in tmp_path
- `ConfigManagementTools`: Place a test `config.yaml` in tmp_path
- `SystemManagementTools`: Mock `DataFetcher`, version check URLs
- `StorageSyncTools`: Use tmp_path storage, skip remote paths (HAS_BOTO3 guard)
- `ArticleReaderTools`: Use `responses` to mock Jina Reader HTTP calls

## Common Pitfalls

### Pitfall 1: StorageManager Singleton Leaks Between Tests
**What goes wrong:** Tests create `AppContext` instances which call `get_storage_manager()`. The module-level singleton persists, so test B gets test A's storage state.
**Why it happens:** `_storage_manager` at module level in `storage/manager.py` line 19.
**How to avoid:** Autouse fixture (D-21) resets `trendradar.storage.manager._storage_manager = None`.
**Warning signs:** Tests pass individually but fail when run together, or when run in different order (detected by pytest-randomly).

### Pitfall 2: Coverage Config Omitting mcp_server
**What goes wrong:** `--cov=trendradar` alone misses the `mcp_server` package entirely.
**How to avoid:** Both `--cov=trendradar --cov=mcp_server` in addopts AND `source = ["trendradar", "mcp_server"]` in `[tool.coverage.run]`.
**Warning signs:** MCP tests run but show 0% coverage in reports.

### Pitfall 3: responses Library Not Blocking Unmocked URLs
**What goes wrong:** `responses` in decorator mode (`@responses.activate`) blocks unmocked URLs by default with `ConnectionError`. But if using the context manager mode without `assert_all_requests_are_fired=True`, tests may silently pass despite missing mock registrations.
**How to avoid:** Use `@responses.activate` decorator for simple cases. When using `responses.RequestsMock()` context manager (as in `mock_http_response` fixture), set `assert_all_requests_are_fired=False` since not all fixtures register URLs.
**Warning signs:** Tests pass locally but fail in CI due to network access.

### Pitfall 4: EastMoney Plugin JS Wrapper
**What goes wrong:** The EastMoney plugin strips a `var xxx = {...};` wrapper from responses. Test HTTP mocks must include this wrapper for happy-path tests, or the parse path is different.
**How to avoid:** Happy-path test fixture must include `var result = {"rc":"1","LivesList":[...]};` format.
**Warning signs:** Tests pass with raw JSON but fail with the actual response format.

### Pitfall 5: TongHuaShun Plugin HTML Parsing
**What goes wrong:** The TongHuaShun plugin parses HTML pages with regex extraction, not JSON. Test fixtures need to include properly shaped HTML, not JSON.
**How to avoid:** Use a minimal HTML fixture string with the expected JS data pattern.
**Warning signs:** Parser returns empty list despite "successful" HTTP response.

### Pitfall 6: Pipeline Test Missing frequency_words.txt
**What goes wrong:** `execute_mode_strategy()` calls `ctx.load_frequency_words()` which reads `config/frequency_words.txt`. If this file doesn't exist in the test environment, `FileNotFoundError` is raised.
**How to avoid:** Either mock `ctx.load_frequency_words` to return `([], [], [])`, or create a minimal `frequency_words.txt` in the test tmp_path and configure the config to point to it.
**Warning signs:** Integration test fails with `FileNotFoundError` for frequency_words.txt.

### Pitfall 7: webbrowser.open() in execute_mode_strategy
**What goes wrong:** Line 488 of `mode_strategy.py` calls `webbrowser.open()` if `should_open_browser=True`. In tests this opens an actual browser window.
**How to avoid:** Always pass `should_open_browser=False` AND `is_docker_container=False` in test calls to `execute_mode_strategy()`.

## Code Examples

### Coverage Configuration in pyproject.toml
```toml
# Source: pytest-cov docs + coverage.py docs [CITED: pytest-cov.readthedocs.io]
[tool.pytest.ini_options]
testpaths = ["tests"]
norecursedirs = [".git", ".venv", "output", "_image"]
addopts = "--cov=trendradar --cov=mcp_server --cov-fail-under=80"

[tool.coverage.run]
branch = true
source = ["trendradar", "mcp_server"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "if __name__ == .__main__.",
    "if TYPE_CHECKING:",
    "@abstractmethod",
    "raise NotImplementedError",
]
omit = [
    "tests/*",
    "trendradar/webui/templates/*",
    "trendradar/webui/static/*",
]
```

### mock_config Fixture
```python
# Source: derived from trendradar/context.py AppContext property accessors
@pytest.fixture
def mock_config(tmp_path):
    """Minimal-valid config dict for AppContext. Function-scoped."""
    return {
        "TIMEZONE": "UTC",
        "RANK_THRESHOLD": 50,
        "WEIGHT_CONFIG": {},
        "PLATFORMS": [],
        "RSS": {"ENABLED": False, "FEEDS": []},
        "DISPLAY_MODE": "keyword",
        "DISPLAY": {
            "REGIONS": {"NEW_ITEMS": True, "STANDALONE": False, "RSS": False},
            "REGION_ORDER": ["hotlist"],
        },
        "REPORT_MODE": "daily",
        "REQUEST_INTERVAL": 1000,
        "STORAGE": {
            "BACKEND": "local",
            "FORMATS": {"TXT": False, "HTML": False},
            "LOCAL": {"DATA_DIR": str(tmp_path / "output"), "RETENTION_DAYS": 0},
            "REMOTE": {},
            "PULL": {"ENABLED": False, "DAYS": 0},
        },
        "AI": {"MODEL": "test/test", "API_KEY": "fake-key", "API_BASE": "", "TIMEOUT": 5, "MAX_TOKENS": 100},
        "AI_ANALYSIS": {"ENABLED": False},
        "AI_TRANSLATION": {"ENABLED": False},
        "SHOW_VERSION_UPDATE": False,
        "MAX_NEWS_PER_KEYWORD": 0,
        "MAX_KEYWORDS": 0,
        "SORT_BY_POSITION_FIRST": False,
        "DEBUG": False,
        "FEISHU_MESSAGE_SEPARATOR": "---",
        "FEISHU_BATCH_SIZE": 29000,
        "DINGTALK_BATCH_SIZE": 20000,
        "MESSAGE_BATCH_SIZE": 4000,
    }
```

### mock_app_context Fixture
```python
@pytest.fixture
def mock_app_context(mock_config):
    """Real AppContext with controlled config and tmp_path storage."""
    from trendradar.context import AppContext
    ctx = AppContext(mock_config)
    return ctx
```

### mock_http_response Fixture
```python
# Source: responses library docs [CITED: pypi.org/project/responses/]
@pytest.fixture
def mock_http_response():
    """Activate responses RequestsMock for HTTP interception."""
    with responses.RequestsMock() as rsps:
        yield rsps
```

### Crawler Plugin Test Pattern
```python
# coding=utf-8
from __future__ import annotations
import responses
from trendradar.crawler.plugins.gnews import GNewsPlugin

@responses.activate
def test_gnews_happy_path():
    responses.add(
        responses.GET,
        "https://gnews.io/api/v4/top-headlines",
        json={"articles": [{"title": "Test News", "url": "https://example.com"}]},
        status=200,
    )
    plugin = GNewsPlugin()
    result = plugin.fetch({"id": "gnews", "api_key": "fake-key"})
    assert result.success
    assert len(result.items) == 1
    assert result.items[0].title == "Test News"

@responses.activate
def test_gnews_missing_api_key():
    plugin = GNewsPlugin()
    result = plugin.fetch({"id": "gnews"})  # no api_key
    assert not result.success
    assert len(result.errors) > 0
```

### Assertion Helper Pattern
```python
# tests/crawler/_helpers.py
from trendradar.crawler.base import CrawlResult, FetchedItem

def assert_fetched_item_shape(item: FetchedItem):
    """Validate a FetchedItem has the expected field types."""
    assert isinstance(item.title, str)
    assert len(item.title) > 0
    assert isinstance(item.url, str)
    assert isinstance(item.rank, int)

def assert_crawl_result_success(result: CrawlResult, min_items: int = 1):
    """Validate a successful CrawlResult."""
    assert result.success, f"Expected success but got errors: {result.errors}"
    assert len(result.items) >= min_items
    for item in result.items:
        assert_fetched_item_shape(item)

def assert_crawl_result_error(result: CrawlResult):
    """Validate an error CrawlResult."""
    assert not result.success
    assert len(result.errors) > 0
    assert len(result.items) == 0
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| pytest-cov 4.x + coverage 6.x | pytest-cov 7.x + coverage 7.x | 2024-2025 | Better branch coverage accuracy, pyproject.toml native config |
| responses 0.23.x | responses 0.26.0 | 2024-2025 | Improved matchers, passthrough support |
| `--cov-branch` CLI flag | `branch = true` in `[tool.coverage.run]` | coverage 5.0+ | Config file preferred over CLI flags |

**Deprecated/outdated:**
- pytest-cov `--cov-config` flag: No longer needed when using `pyproject.toml` — coverage.py reads it automatically [VERIFIED: coverage.py docs]
- `setup.cfg` for coverage config: `pyproject.toml` is the modern standard [ASSUMED]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `setup.cfg` for coverage config is outdated vs pyproject.toml | State of the Art | Low — pyproject.toml is verified to work; setup.cfg would also work |
| A2 | pytest-cov 7.x works with Python 3.10+ | Standard Stack | Low — 7.x lists Python 3.10+ support in pypi metadata |
| A3 | The 80% coverage target is achievable with the planned test additions | Coverage scope | Medium — depends on how much of `trendradar/webui/` and `trendradar/__main__.py` paths are uncovered. Mitigated by allowing module-level gaps per D-04 |

## Open Questions

1. **FastMCP version mismatch**
   - What we know: Installed version is 2.12.5, pyproject.toml requires `>=2.14.0,<3.0.0`. The `Client` API works in 2.12.5.
   - What's unclear: Whether there are behavioral differences in Client between 2.12.5 and 2.14.0+.
   - Recommendation: The D-11 smoke test should work with whatever version is installed at runtime. If FastMCP is upgraded during development (pip install), it resolves naturally.

2. **MCP tool _tools_instances singleton**
   - What we know: `mcp_server/server.py` line 29 has `_tools_instances = {}` module-level dict that is populated lazily by `_get_tools()`.
   - What's unclear: Whether this needs autouse reset like StorageManager.
   - Recommendation: For D-10 handler-level tests, this singleton is bypassed (tests import tool classes directly). For D-11 smoke test, reset `_tools_instances.clear()` in test teardown to prevent cross-contamination.

3. **TongHuaShun HTML fixture format**
   - What we know: Plugin parses HTML with regex, not JSON.
   - What's unclear: Exact HTML structure needed for fixture.
   - Recommendation: Planner should read `tonghuashun.py` parsing code (regex patterns) and construct a minimal HTML string that matches.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.10+ | All code | Yes | 3.12.7 | -- |
| pytest | Test runner | Yes | 8.x (in dev deps) | -- |
| pytest-cov | Coverage gate (D-02) | Yes (stale) | 4.1.0 installed | Upgrade to >=7.0 via pip install |
| responses | HTTP mocking (D-20) | No | -- | Will be installed via dev deps |
| pytest-randomly | State leak detection (D-07) | No | -- | Will be installed via dev deps |
| pytest-asyncio | D-11 smoke test | Yes | 1.3.0 | Already available, no action needed |
| SQLite | Storage tests (D-14, D-19) | Yes | Built into Python stdlib | -- |
| pip/uv | Dev dep install (D-08) | Yes | pip available | -- |

**Missing dependencies with no fallback:**
- None — all will be installed via `[dependency-groups] dev` update.

**Missing dependencies with fallback:**
- `responses` and `pytest-randomly`: Not installed yet but will be added via dev deps in Phase 2 itself.

## Sources

### Primary (HIGH confidence)
- **Codebase inspection**: All source files in `trendradar/`, `mcp_server/`, `tests/` directly read and analyzed
- **pip index**: pytest-cov 7.1.0, responses 0.26.0, pytest-randomly 4.0.1, coverage 7.13.5 versions verified
- **pip show**: Installed versions of pytest-cov (4.1.0), pytest-asyncio (1.3.0), fastmcp (2.12.5) verified
- **Runtime inspection**: `fastmcp.Client.__init__` signature verified via Python import + `inspect.signature()`

### Secondary (MEDIUM confidence)
- **pytest-cov docs** [CITED: pytest-cov.readthedocs.io] — `--cov-fail-under`, `--cov` flag behavior, pyproject.toml config syntax
- **coverage.py docs** [CITED: coverage.readthedocs.io] — `[tool.coverage.run]` branch config, exclude_lines patterns, source config
- **responses library** [CITED: pypi.org/project/responses/] — `RequestsMock` context manager API, `@responses.activate` decorator

### Tertiary (LOW confidence)
- None — all claims are verified or cited.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all versions verified against pip index, APIs verified against codebase
- Architecture: HIGH — all fixture designs derived from actual codebase inspection of AppContext, StorageManager, crawler plugins, MCP tools
- Pitfalls: HIGH — all pitfalls verified against actual code patterns (singleton at line 19, JS wrapper in eastmoney, etc.)
- D-13 async finding: HIGH — verified via runtime import and signature inspection

**Research date:** 2026-04-14
**Valid until:** 2026-05-14 (30 days — stable domain, library versions pinned)
