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

### Mutable Config Dict (部分修复 — 2026-05)
**已处理**：
- `trendradar/models/config.py:TrendRadarConfig.to_legacy_dict()` 新方法把 Pydantic 模型直接序列化为 `loader.load_config` 历史返回的扁平 UPPER_CASE 字典格式，并在该方法内部统一应用 webhook 环境变量覆盖。
- 新增 `tests/test_pydantic_legacy_dict.py` 契约测试：在完整 fixture YAML 上对比两条加载路径，断言顶层键集合一致 + 关键标量/嵌套字段值一致 + webhook env override 生效。该测试将在两条路径出现新漂移时立即失败。

**仍待处理（风险较高，需独立会话评估）**：
- `loader.py:_load_*` 系列函数与 Pydantic 模型在多处默认值上漂移：
  - `report.mode`：loader 默认 `daily`，Pydantic 默认 `current`
  - `report.rank_threshold`：loader 默认 `10`，Pydantic 默认 `5`
  - `display.region_order`：loader 默认 `[hotlist, rss, new_items, ...]`，Pydantic 默认 `[new_items, hotlist, rss, ...]`
  - `ai.num_retries`：loader `2` vs Pydantic `1`；`ai.model`：loader `""` vs Pydantic `openai/gemini-3-pro-preview`
  - `ai_analysis.enabled/include_rss/include_rank_timeline/max_news_for_analysis` 多项不一致
  - `ai_translation.enabled/language` 不一致
  - `notification.batch_size.feishu/bark`：loader 用 `29000/3600` 兜底，Pydantic 用 YAML 字段默认 `30000/4000`
- 完整切换到 Pydantic 路径前，需先逐项确认哪些默认值是历史用户依赖、哪些是文档错误。
- 切换后即可删除 `loader._load_*` 系列函数，把 `load_config()` 改为 `TrendRadarConfig.from_yaml(p).to_legacy_dict()` 一行实现。

### MODE_STRATEGIES 类型化 (已完成 — 2026-05)
- 抽出到 `trendradar/core/mode_strategies.py`：`MODE_STRATEGIES`/`ModeStrategy` TypedDict/`ReportMode` Literal/`get_mode_strategy()`/`DEFAULT_REPORT_MODE`。
- `AnalysisEngine.MODE_STRATEGIES` 现为模块级表的别名（同一对象）。
- `mode_strategy.execute_mode_strategy` 参数类型从 `dict` 收紧到 `ModeStrategy`/`dict[str, ModeStrategy]`。
- `tests/test_mode_strategies.py` 覆盖：3 个规范模式存在、TypedDict 字段一致、unknown 回退到 daily、AnalysisEngine 类属性 is 同对象。

### AppContext 仍是 dict
`AppContext` 仍然包装 `dict`。`to_legacy_dict()` 已为后续切换做好接线点，但 AppContext 本身的迁移（直接持有 Pydantic 实例）尚未启动。

### Storage Manager Singleton
`trendradar/storage/manager.py:19` has a module-level `_storage_manager` singleton pattern that could cause issues in testing or multi-context scenarios.

## Code Quality

### Inconsistent Language
- Code comments and docstrings are in Chinese
- Some module docstrings are in English (e.g., `trendradar/webui/app.py`)
- `AGENTS.md` and `README-EN.md` are in English
- Mixed language makes onboarding harder for non-Chinese speakers

### Inline HTML Generation (部分修复 — 2026-05)
**已处理**：
- `html_styles.py` (1197 行 CSS 字符串) → 抽到 `trendradar/report/templates/report.css`，模块降为薄加载器
- `html_scripts.py` (578 行 JS 字符串) → 抽到 `trendradar/report/templates/report.js`，模块降为薄加载器
- `html.py` 主壳由字符串拼接改为 Jinja2 模板渲染（`templates/report.html.j2`），失败平台列表与"本次新增热点"区块也改为模板循环
- 净减少 ~1760 行 Python 字符串拼接代码

**仍待处理**：
- `html_sections.py` 内的 `build_hotlist_view`、`render_rss_stats_html`、`render_standalone_html` 等仍以字符串拼接形式构造区块 HTML（被本模块以 `Markup` 包装注入主模板）。后续可逐个改为 Jinja2 macros，但风险较高、需要逐区块对比输出验证。
- `rss_html.py` (477 行) 独立的 RSS 报告生成器尚未模板化。

### Config Key Case Transformation
Config keys are lowercase in YAML but UPPERCASE in Python. This transformation happens in `trendradar/core/config.py` and creates a non-obvious mapping that must be remembered.

## Performance

### Concurrent Crawling (已修复)
主热榜爬取 `trendradar/crawler/fetcher.py:crawl_websites` 已改为基于 `ThreadPoolExecutor`（最多 10 路并发）+ 20ms 提交错峰。`request_interval` 参数保留为兼容旧调用方但实际未再使用，已在 docstring 中说明。文档此前的"sequential"描述已过期。

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
