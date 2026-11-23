# PulseRadar 项目架构文档

> 运行时: Python 3.10+。Python 包和 CLI 保留 `trendradar` 名称。

## 1. 项目定位

PulseRadar 聚合热榜、RSS 和额外新闻 API，按关键词筛选和统计热点，生成 HTML 报告。可选能力包括 AI 分析和翻译、九种通知通道、Flask 管理界面，以及供 AI 客户端查询采集数据的 MCP 服务。

## 2. 技术栈

| 层级 | 技术 | 用途 |
|------|------|------|
| 运行时 | Python 3.10+ | CLI、Web UI 和 MCP |
| Web | Flask 3.0+ | 管理界面和作业 API |
| 采集 | requests 2.32.5+ / feedparser 6.0+ | 热榜、API 和 RSS/Atom |
| 存储 | SQLite / 本地文件 / S3 兼容存储 | `boto3` 通过 `s3` 可选依赖安装 |
| AI | LiteLLM 1.57+ / tenacity 9.x | 模型调用和重试 |
| MCP | FastMCP 2.14+ / mcp 1.23+ | STDIO 和 HTTP 接入 |
| 配置与日志 | PyYAML、Pydantic、structlog | 配置解析和结构化日志 |
| 部署 | Docker Compose / GitHub Actions | 定时采集、报告更新、镜像构建 |

依赖和命令入口以 [pyproject.toml](../pyproject.toml) 为准。使用 S3 后端时，可在本地运行 `python -m pip install -e '.[s3]'`。

## 3. 目录结构

```text
PulseRadar/
├── trendradar/
│   ├── __main__.py           # CLI 入口和 NewsAnalyzer 门面
│   ├── context.py            # AppContext：配置、存储和报告等共享能力
│   ├── core/                 # 配置加载、采集编排、模式策略、分析管线
│   ├── crawler/              # 热榜和 RSS 抓取、额外 API 插件、限流与熔断
│   ├── ai/                   # 模型调用、分析和翻译
│   ├── models/               # 配置和新闻模型
│   ├── notification/         # 推送调度、各渠道实现、消息渲染与分批
│   ├── report/               # HTML 报告、报告清单和 GitHub Pages 首页
│   ├── storage/              # 本地 SQLite 和 S3 兼容存储
│   └── webui/                # Flask 工厂、Blueprint、后台作业和页面
├── mcp_server/               # FastMCP 服务、查询/分析工具及共享数据服务
├── config/                   # config.yaml、关键词规则和 AI 提示词
├── docker/                   # 镜像构建、Compose 和静态报告服务器
├── scripts/                  # 历史报告迁移脚本
├── tests/                    # 核心、爬虫、MCP 和 Web UI 测试
├── output/                   # 本地报告、SQLite 数据及作业数据库
├── reports/                  # GitHub Pages 报告快照、最新报告和清单
└── .github/workflows/        # 定时采集/报告提交、镜像构建
```

## 4. 数据流架构

```text
CLI (python -m trendradar) ← Web UI 后台作业启动子进程
  │
  ├─ load_config() → AppContext
  ├─ CrawlCoordinator.crawl_all()
  │    ├─ 热榜抓取和存储
  │    ├─ RSS 抓取、过滤和存储
  │    └─ 并发调用额外 API，并将结果合并到热榜数据
  │         ↓ CrawlOutput / RSSOutput
  └─ AnalysisEngine.analyze()
       └─ execute_mode_strategy()
            ├─ 选择 current、daily 或 incremental
            ├─ 关键词统计、可选 AI 分析和 HTML 报告生成
            └─ 按推送配置分发通知

MCP 客户端 → FastMCP → 查询/分析采集数据（独立于 HTML 报告）
```

`storage.backend: auto` 在本地及 Docker 默认使用本地存储；GitHub Actions 配齐 S3 端点、桶名和访问凭据时使用远程存储，否则回退到本地。默认本地 SQLite 快照位于 `output/news/` 和 `output/rss/`，HTML 报告默认开启，TXT 快照默认关闭。

## 5. 核心模块职责

| 模块 | 职责 | 核心类/函数 |
|------|------|------------|
| `trendradar/__main__.py` | CLI 参数解析、版本检查、编排入口 | `main()`、`NewsAnalyzer.run()` |
| `trendradar/core/loader.py` | YAML 加载和环境变量覆盖 | `load_config()` |
| `trendradar/core/crawl_coordinator.py` | 编排热榜、RSS 和额外 API | `CrawlCoordinator` |
| `trendradar/crawler/{registry,extra_apis}.py` | 发现插件并并发采集额外 API | `CrawlerRegistry`、`crawl_extra_sources_concurrent()` |
| `trendradar/core/{analysis_engine,mode_strategy,pipeline}.py` | 模式选择、关键词分析、AI、报告和推送 | `AnalysisEngine`、`execute_mode_strategy()`、`run_analysis_pipeline()` |
| `trendradar/report/{generator,html}.py` | 报告生成和 HTML 渲染 | `generate_html_report()` |
| `trendradar/notification/dispatcher.py`、`channels/` | 按渠道渲染和发送通知 | `NotificationDispatcher` |
| `trendradar/webui/{app,job_manager}.py` | 注册 Blueprint、持久化和运行作业 | `create_app()`、`JobManager` |
| `mcp_server/server.py` | 暴露 FastMCP 资源和工具 | `run_server()` |

## 6. Web UI API 端点

使用 `python -m trendradar.webui` 启动管理界面，默认监听 `127.0.0.1:5000`。页面包括 `/`、`/platforms`、`/rss`、`/extra-apis`、`/notifications`、`/ai`、`/reports`、`/workflow`、`/jobs`、`/trends` 和 `/settings`。

| 方法 | 路径 | 功能 |
|------|------|------|
| POST | `/api/run` | 创建并排队作业 |
| GET | `/api/status` | 获取兼容格式的作业状态 |
| GET | `/api/jobs` | 分页查询作业 |
| GET | `/api/jobs/<job_id>` | 获取作业详情 |
| GET | `/api/jobs/<job_id>/logs` | 读取作业日志（JSON，可指定 `tail`） |
| POST | `/api/jobs/<job_id>/cancel` | 取消作业 |
| POST | `/api/jobs/<job_id>/retry` | 重试作业 |
| GET | `/api/jobs/cleanup/preview` | 预览可清理的已结束作业 |
| POST | `/api/jobs/cleanup` | 清理已结束作业 |
| GET | `/api/run-log` | 下载纯文本日志，可传 `job_id` |
| GET / POST | `/api/config`、`/api/config/<section>` | 读写完整配置或指定配置段 |
| GET / POST | `/api/platforms`、`/api/rss`、`/api/extra-apis` | 读写数据源配置 |
| POST | `/api/test-source` | 测试数据源 |
| GET / POST | `/api/workflow-templates` | 列出或创建工作流模板 |
| PUT / DELETE | `/api/workflow-templates/<template_id>` | 更新或删除模板 |
| GET | `/api/workflow-templates/export` | 导出模板 |
| POST | `/api/workflow-templates/import/preview`、`/api/workflow-templates/import` | 预览导入或导入模板 |
| GET | `/api/reports`、`/reports/<date>/<filename>` | 列出或查看报告 |
| GET | `/artifacts/<path:relative_path>` | 查看输出文件 |
| GET | `/api/trends`、`/api/history/search` | 查询趋势和搜索历史数据 |

## 7. 配置体系

主配置为 [config/config.yaml](../config/config.yaml)。CLI 优先使用 `--config`，其次是 `CONFIG_PATH`，最后使用默认文件。

| 配置键 | 用途 |
|--------|------|
| `platforms.sources`、`rss.feeds`、`extra_apis.sources` | 热榜、RSS 和额外 API 数据源 |
| `report.mode`、`report.display_mode`、`display.regions` | 报告模式、分组方式和显示区域 |
| `ai`、`ai_analysis`、`ai_translation` | 共享模型配置，分别控制分析和翻译 |
| `notification.enabled`、`notification.channels`、`notification.push_window` | 推送开关、凭据和推送窗口 |
| `storage.backend`、`storage.formats`、`storage.local`、`storage.remote` | 存储后端、格式、目录和保留期限 |

常用环境变量覆盖项：`TIMEZONE`、`DEBUG`、`CRAWLER_API_URL`、`AI_MODEL`、`AI_API_BASE`、`AI_API_KEY` 及各渠道凭据，例如 `TELEGRAM_BOT_TOKEN` 和 `TELEGRAM_CHAT_ID`。不要把凭据提交到仓库。

## 8. 作业生命周期

`JobManager` 将队列、作业日志和工作流模板持久化在 `output/webui_jobs.db`。状态从 `queued` 变为 `running`，结束时为 `success`、`failed` 或 `cancelled`；运行中的任务可先进入 `cancelling`。界面根据日志追踪 `starting`、`crawl`、`rss`、`ai`、`report`、`notify` 等阶段，阶段和状态是不同字段。

## 9. 报告与发布

- **本地报告**：默认按日期保存到 `output/html/<日期>/<时间>.html`；各模式的最新报告为 `output/html/latest/<mode>.html`，公共入口文件为 `output/html/index.html`。
- **Docker 静态报告服务**：`ENABLE_WEBSERVER=true` 时，主容器托管 `output/html/`，默认端口为 8080。可选的 [Caddy 报告查看器](../docker/docker-compose-public-viewer.yml) 只读挂载 `output/html/`，默认端口为 18080，不提供管理 API。
- **GitHub Pages**：采集工作流额外写入 `reports/<日期>/<时间>.html`、`reports/latest/<mode>.html` 和 `reports/manifest.json`，并将根目录 `index.html` 生成报告索引。工作流只提交根目录的入口和 `reports/`，不会提交采集数据库。
- **历史迁移**：如需把 `output/html/` 中的旧快照补入 Pages 索引，在仓库根目录运行 `python scripts/migrate_reports_to_hub.py`。脚本更新 `reports/manifest.json` 并重写根目录 `index.html`，不属于日常采集流程。
