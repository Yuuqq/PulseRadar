# TrendRadar 项目架构文档

> 版本: 5.5.3 | Python 3.10+ | 生成时间: 2026-04-12

## 1. 项目定位

TrendRadar 是一个热点新闻聚合与分析平台，核心能力：
- **数据采集**: 40+ 中文平台 + 国际新闻 API + 50+ RSS 源
- **AI 分析**: 通过 LiteLLM 接入 100+ LLM 提供商，生成趋势洞察
- **多通道推送**: 9 种通知渠道（Telegram、企业微信、钉钉、飞书、Slack、邮件等）
- **报告生成**: HTML/TXT 多语言报告，含排名时间线可视化
- **WebUI 管理**: Flask 单页应用，含作业队列、配置编辑、RSS 管理
- **MCP 集成**: 通过 Model Context Protocol 供 AI 助手调用

## 2. 技术栈

| 层级 | 技术 | 用途 |
|------|------|------|
| 运行时 | Python 3.10+ | 主语言 |
| Web | Flask 3.0+ | WebUI 管理界面 |
| HTTP | requests 2.32+ | API 数据抓取 |
| 存储 | SQLite / Local FS / AWS S3 (boto3) | 多后端存储 |
| AI | LiteLLM 1.57+ | 统一 LLM 接口 |
| MCP | FastMCP 2.14+ / mcp 1.23+ | AI 助手协议 |
| RSS | feedparser 6.0+ | RSS/Atom 解析 |
| 重试 | tenacity 8.5.0 | 指数退避重试 |
| 配置 | PyYAML 6.0+ | YAML 配置解析 |
| 容器 | Docker + docker-compose | 生产部署 |
| CI/CD | GitHub Actions | 定时爬取、Docker 构建 |

## 3. 目录结构

```
TrendRadar/
├── trendradar/                     # 核心 Python 包 (~22,600 LOC)
│   ├── __main__.py                 # CLI 入口 & 编排 (1,874 行)
│   ├── __init__.py                 # 版本号导出
│   ├── context.py                  # AppContext 依赖注入 (484 行)
│   │
│   ├── core/                       # 核心数据处理
│   │   ├── analyzer.py             # 统计分析 & 权重计算 (787 行)
│   │   ├── loader.py               # 配置加载 & 环境变量覆盖 (535 行)
│   │   ├── config.py               # 多账户配置解析
│   │   ├── data.py                 # 数据 I/O
│   │   └── frequency.py            # 关键词频率分析
│   │
│   ├── crawler/                    # 数据抓取
│   │   ├── fetcher.py              # NewsNow API 爬虫 (6,787 行) ⚠️ 巨型文件
│   │   ├── extra_apis.py           # 多源 API (DailyHot/NewsAPI/GNews 等, 805 行)
│   │   └── rss/                    # RSS 抓取 & 解析
│   │       ├── fetcher.py
│   │       └── parser.py
│   │
│   ├── ai/                         # AI 分析 & 翻译
│   │   ├── analyzer.py             # AI 分析引擎 (468 行)
│   │   ├── client.py               # LiteLLM 封装
│   │   ├── formatter.py            # 结果格式化
│   │   └── translator.py           # AI 翻译
│   │
│   ├── notification/               # 多通道通知 (~5,400 LOC)
│   │   ├── dispatcher.py           # 统一调度器 (1,190 行)
│   │   ├── senders.py              # 9 种通道实现 (1,391 行)
│   │   ├── splitter.py             # 内容分批 (1,672 行) ⚠️
│   │   ├── renderer.py             # 格式渲染 (568 行)
│   │   ├── push_manager.py         # 推送记录追踪
│   │   └── batch.py                # 批次管理
│   │
│   ├── report/                     # 报告生成 (~3,600 LOC)
│   │   ├── html.py                 # HTML 报告生成 (2,460 行) ⚠️
│   │   ├── generator.py            # 报告数据准备 (261 行)
│   │   ├── formatter.py            # 数据格式化 (247 行)
│   │   ├── rss_html.py             # RSS 报告 (479 行)
│   │   └── helpers.py              # 工具函数
│   │
│   ├── storage/                    # 存储抽象层 (~3,500 LOC)
│   │   ├── manager.py              # 多后端管理器 (385 行)
│   │   ├── base.py                 # 存储接口 (593 行)
│   │   ├── local.py                # 本地文件存储 (460 行)
│   │   ├── remote.py               # S3 远程存储 (823 行)
│   │   └── sqlite_mixin.py         # SQLite 持久化 (1,308 行) ⚠️
│   │
│   ├── utils/
│   │   ├── time.py                 # 时区处理 (445 行)
│   │   └── url.py                  # URL 工具
│   │
│   └── webui/                      # Flask Web 界面 (~2,100 LOC)
│       ├── app.py                  # Flask 路由 (1,086 行) ⚠️
│       ├── job_manager.py          # 作业队列 & 持久化 (966 行)
│       ├── __main__.py             # WebUI 启动入口
│       └── templates/              # HTML 模板
│
├── mcp_server/                     # MCP 协议服务器 (~1,144+ LOC)
│   ├── server.py                   # MCP 服务实现
│   ├── services/                   # 缓存/数据/解析服务
│   └── tools/                      # MCP 工具 (config/query/search/sync/analytics)
│
├── config/
│   ├── config.yaml                 # 主配置 (~14KB)
│   ├── ai_analysis_prompt.txt      # AI 分析 prompt
│   ├── ai_translation_prompt.txt   # 翻译 prompt
│   └── frequency_words.txt         # 关键词过滤表
│
├── docker/                         # Docker 部署
├── tests/                          # 测试 (8 文件, ~1,043 LOC)
├── .github/workflows/              # CI/CD (定时爬取/清理/构建)
├── output/                         # 生成的报告 & 数据
│   ├── webui_jobs.db               # 作业持久化 (SQLite)
│   ├── html/                       # HTML 报告 (按日期)
│   └── txt/                        # TXT 快照
├── pyproject.toml                  # 项目元数据
└── requirements.txt                # 依赖声明
```

## 4. 数据流架构

```
┌─────────────────────────────────────────────────────────────┐
│  入口: CLI (python -m trendradar) / WebUI / MCP Server       │
└─────────────┬───────────────────────────────────────────────┘
              │
    ┌─────────▼──────────┐
    │   1. 配置加载        │  core/loader.py
    │   YAML + 环境变量     │  config/config.yaml
    └─────────┬──────────┘
              │
    ┌─────────▼──────────┐
    │   2. 数据采集        │  ⬅ 当前瓶颈: 串行请求, 40平台×2s≈80s
    │   ├ NewsNow API     │  crawler/fetcher.py
    │   ├ Extra APIs      │  crawler/extra_apis.py
    │   └ RSS Feeds       │  crawler/rss/
    └─────────┬──────────┘
              │
    ┌─────────▼──────────┐
    │   3. 数据分析        │
    │   ├ 权重计算         │  core/analyzer.py (rank×0.6 + freq×0.3 + hot×0.1)
    │   ├ 标题去重         │
    │   ├ 词频统计         │  core/frequency.py
    │   └ 新增检测         │
    └─────────┬──────────┘
              │
    ┌─────────▼──────────┐
    │   4. AI 分析 (可选)  │  ai/analyzer.py → LiteLLM → 100+ LLM
    │   5 大板块洞察       │  趋势/情绪/弱信号/RSS/策略
    └─────────┬──────────┘
              │
    ┌─────────▼──────────┐
    │   5. 报告生成        │  report/html.py (HTML) + generator.py
    │   HTML / TXT / RSS   │  ⬅ 2,460 行单文件, 全量内存加载
    └─────────┬──────────┘
              │
    ┌─────────▼──────────┐
    │   6. 存储持久化       │  storage/ (Local / S3 / SQLite)
    │   自动环境检测        │  GitHub Actions / Docker / Local
    └─────────┬──────────┘
              │
    ┌─────────▼──────────┐
    │   7. 通知推送        │  notification/dispatcher.py
    │   9 种通道           │  ⬅ 内容分批逻辑 1,672 行
    │   多账户支持         │  senders.py (1,391 行)
    └─────────────────────┘
```

## 5. 核心模块职责

| 模块 | 职责 | 核心类/函数 |
|------|------|------------|
| `__main__` | CLI 参数解析 + 流程编排 + 版本检查 | `main()`, `run_workflow()` |
| `context` | 依赖注入容器，统一配置访问 | `AppContext` |
| `core/loader` | YAML 配置加载 + 环境变量覆盖 | `load_config()` |
| `core/analyzer` | 新闻权重计算 + 统计分析 | `calculate_news_weight()` |
| `crawler/fetcher` | NewsNow API 数据采集 | `DataFetcher.fetch_data()` |
| `crawler/extra_apis` | 多源 API 采集 (DailyHot/NewsAPI/GNews) | 各 `fetch_*()` 函数 |
| `ai/analyzer` | AI 趋势分析 | `AIAnalyzer.analyze()` |
| `ai/client` | LiteLLM 统一 LLM 调用 | `AIClient.completion()` |
| `report/html` | HTML 报告渲染 | `generate_html_report()` |
| `notification/dispatcher` | 多通道推送调度 | `NotificationDispatcher.dispatch_all()` |
| `notification/splitter` | 内容分批 (按字符限制) | `split_content_into_batches()` |
| `notification/senders` | 9 种通道的具体发送实现 | `send_to_telegram()` 等 |
| `storage/manager` | 存储后端选择 & 管理 | `StorageManager` |
| `webui/app` | Flask 路由 & API 端点 | Flask app |
| `webui/job_manager` | SQLite 作业队列 & 进程管理 | `JobManager` |
| `mcp_server/server` | MCP 协议服务器 | FastMCP tools |

## 6. WebUI API 端点

| 方法 | 路径 | 功能 |
|------|------|------|
| GET | `/` | 首页仪表盘 |
| GET | `/workflow` | 工作流管理 |
| GET | `/config` | 配置编辑器 |
| GET | `/jobs` | 作业列表 |
| GET | `/rss` | RSS 管理 |
| POST | `/api/run` | 创建并排队作业 |
| GET | `/api/status` | 查询作业状态 |
| GET | `/api/jobs` | 作业列表 (JSON) |
| POST | `/api/cancel/<id>` | 取消作业 |
| POST | `/api/retry/<id>` | 重试失败作业 |
| GET | `/api/run/log` | 日志流 (SSE) |
| GET/PUT | `/api/config` | 配置读写 |
| POST | `/api/config/test/<channel>` | 测试通知通道 |
| GET | `/api/reports` | 报告列表 |
| POST | `/api/rss/import` | 导入 RSS |
| GET | `/api/rss/export` | 导出 RSS |

## 7. 配置体系

```yaml
# config/config.yaml 主要配置段
advanced:          # 高级参数 (批次大小/请求间隔/权重)
ai:                # LLM 配置 (model/api_key/api_base/timeout)
ai_analysis:       # AI 分析 (enabled/language/mode/prompt_file)
ai_translation:    # AI 翻译
app:               # 应用设置 (timezone/show_version_update)
display:           # 显示区域配置 (region_order/regions)
notification:      # 通知通道配置 (9 种通道各自参数)
platforms:         # 平台数据源 (40+ 平台 enabled/disabled)
rss:               # RSS 源配置 (50+ feeds)
extra_apis:        # 额外 API 源 (DailyHot/NewsAPI/GNews 等)
```

环境变量覆盖: `TIMEZONE`, `DEBUG`, `AI_API_KEY`, `AI_API_BASE`, `CRAWLER_API_URL`, `GITHUB_ACTIONS`, `DOCKER_CONTAINER`

## 8. 作业生命周期

```
queued → starting → crawl → rss → ai → report → notify → finished
                                                          ↓
                                                       failed → retry
```

SQLite 持久化 (`output/webui_jobs.db`)，支持崩溃恢复、重试追踪、日志聚合。

## 9. 关键指标

| 指标 | 数值 |
|------|------|
| 总代码行数 | ~22,600 (核心) + ~1,144 (MCP) |
| Python 文件数 | 65 (47 核心 + 18 MCP) |
| 超 1,000 行文件 | 8 个 |
| 测试覆盖率 (估) | ~4-5% |
| 数据源平台 | 40+ |
| 通知通道 | 9 种 |
| RSS 默认源 | 50+ |
| print() 调用 | 452 处 (无结构化日志) |
| 类型注解覆盖 | ~92% |
