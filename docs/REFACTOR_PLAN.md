# TrendRadar 彻底重构计划

> 目标: 功能倍增 + 效率倍增 | 基于 v5.5.3 现状分析

---

## 一、现状诊断：核心痛点

### 性能瓶颈
| 问题 | 影响 | 定位 |
|------|------|------|
| **数据采集串行** | 40 平台 × 2s = 80s+ 采集时间 | `crawler/fetcher.py` |
| **无连接池** | 每次请求创建新连接 | `crawler/fetcher.py`, `extra_apis.py` |
| **报告全量内存** | 大报告 OOM 风险 | `report/html.py` |
| **SQLite 无索引** | 作业查询随数据增长变慢 | `webui/job_manager.py` |
| **内容重复分批** | 每个通道重新计算分批 | `notification/splitter.py` |
| **无缓存层** | 重复数据不缓存 | 全局 |

### 架构债务
| 问题 | 影响 | 定位 |
|------|------|------|
| **8 个文件超 1000 行** | 维护困难、无法独立测试 | html.py/splitter.py/__main__.py 等 |
| **452 个 print()** | 无日志级别、无结构化、生产不可观测 | 全局 |
| **~5% 测试覆盖** | 重构风险极高、回归无保障 | `tests/` |
| **CLI 与业务混杂** | `__main__.py` 1,874 行混合参数解析与编排 | `__main__.py` |
| **无异步架构** | I/O 密集场景无法并发 | 全局 |
| **通知发送无抽象** | 9 个 `send_to_*` 函数复制粘贴 | `senders.py` |

### 安全问题
| 问题 | 级别 | 定位 |
|------|------|------|
| SQL 字符串拼接 ALTER TABLE | P0 严重 | `job_manager.py:160` |
| 裸 `except:` 吞异常 | P1 高 | `extra_apis.py`, `job_manager.py` |
| 错误信息可能泄露内部路径 | P2 中 | 多处 |

---

## 二、重构目标

### 效率倍增
- **采集速度**: 80s → <15s（并发采集 + 连接池）
- **报告生成**: 支持增量渲染，内存占用降 50%+
- **通知推送**: 并行多通道推送，延迟降 3x
- **作业吞吐**: SQLite 索引 + WAL 模式，并发查询性能 5x

### 功能倍增
- **实时模式**: WebSocket 推送实时热点变化
- **调度系统**: 内置 cron 调度，摆脱 GitHub Actions 依赖
- **插件架构**: 数据源 / 通知通道 / 报告格式可插拔
- **数据分析增强**: 趋势对比、历史回溯、跨平台关联
- **API 化**: RESTful API 完整化，支持第三方集成
- **可观测性**: 结构化日志 + 指标采集 + 健康检查

---

## 三、重构架构设计

### 3.1 目标架构

```
trendradar/
├── cli/                        # CLI 层 (仅参数解析 + 调用 orchestrator)
│   ├── __main__.py             # argparse → Orchestrator
│   └── commands/               # 子命令 (run/version/config)
│
├── orchestrator/               # 编排层 (协调各阶段)
│   ├── pipeline.py             # Pipeline: crawl → analyze → report → notify
│   ├── scheduler.py            # 内置 cron 调度器
│   └── hooks.py                # 生命周期钩子
│
├── crawler/                    # 数据采集层 (全异步)
│   ├── base.py                 # 抽象基类 CrawlerPlugin
│   ├── registry.py             # 插件注册表 (自动发现)
│   ├── pool.py                 # 连接池 + 并发控制
│   ├── plugins/                # 可插拔数据源
│   │   ├── newsnow.py          # NewsNow 平台
│   │   ├── dailyhot.py         # DailyHot
│   │   ├── newsapi.py          # NewsAPI
│   │   ├── gnews.py            # GNews
│   │   ├── rss.py              # RSS/Atom
│   │   └── ...                 # 新源只需加文件
│   └── middleware/              # 采集中间件
│       ├── rate_limiter.py     # 自适应限速
│       ├── retry.py            # 指数退避重试
│       ├── cache.py            # 请求缓存 (去重)
│       └── circuit_breaker.py  # 熔断器
│
├── analysis/                   # 分析层
│   ├── engine.py               # 分析引擎 (权重/去重/频率)
│   ├── trend.py                # 趋势检测 (跨周期对比)
│   ├── correlation.py          # 跨平台关联分析
│   └── models.py               # 数据模型 (dataclass / Pydantic)
│
├── ai/                         # AI 层 (基本保留, 增加流式)
│   ├── client.py               # LiteLLM 客户端 (增加流式)
│   ├── analyzer.py             # AI 分析
│   ├── translator.py           # AI 翻译
│   └── prompts/                # Prompt 模板 (Jinja2)
│
├── report/                     # 报告层 (模板引擎重写)
│   ├── engine.py               # 报告引擎 (Jinja2 模板)
│   ├── templates/              # HTML/TXT 模板 (分离样式与逻辑)
│   │   ├── base.html.j2
│   │   ├── main_report.html.j2
│   │   ├── rss_report.html.j2
│   │   └── ai_analysis.html.j2
│   ├── static/                 # CSS/JS 静态资源
│   └── renderers/              # 渲染器插件
│       ├── html.py
│       ├── markdown.py         # 新增: Markdown 输出
│       └── json.py             # 新增: JSON 结构化输出
│
├── notification/               # 通知层 (插件化)
│   ├── base.py                 # 抽象基类 NotificationChannel
│   ├── registry.py             # 通道注册表
│   ├── dispatcher.py           # 调度器 (并行推送)
│   ├── splitter.py             # 内容分批 (简化, 缓存结果)
│   └── channels/               # 可插拔通道
│       ├── telegram.py
│       ├── wework.py
│       ├── dingtalk.py
│       ├── feishu.py
│       ├── slack.py
│       ├── email.py
│       ├── bark.py
│       ├── ntfy.py
│       └── webhook.py
│
├── storage/                    # 存储层 (基本保留, 增加索引)
│   ├── base.py                 # 存储接口
│   ├── local.py                # 本地存储
│   ├── remote.py               # S3 存储
│   ├── sqlite.py               # SQLite (增加索引/WAL)
│   └── migrations/             # Schema 迁移脚本
│
├── config/                     # 配置层 (Pydantic 模型化)
│   ├── models.py               # Pydantic 配置模型 (类型安全)
│   ├── loader.py               # 加载 + 验证 + 环境覆盖
│   └── defaults.py             # 默认值
│
├── logging/                    # 日志层 (结构化)
│   ├── setup.py                # 日志初始化
│   ├── formatters.py           # JSON / 控制台格式
│   └── context.py              # 请求级上下文
│
├── webui/                      # Web 层 (Flask Blueprints)
│   ├── app.py                  # Flask 工厂函数 (精简)
│   ├── blueprints/             # 路由分组
│   │   ├── jobs.py             # /api/jobs
│   │   ├── config.py           # /api/config
│   │   ├── reports.py          # /api/reports
│   │   ├── rss.py              # /api/rss
│   │   └── health.py           # /health + /metrics
│   ├── job_manager.py          # 作业管理
│   └── templates/
│
└── models/                     # 领域模型
    ├── news.py                 # NewsItem, Platform, Source
    ├── job.py                  # Job, JobStatus, JobStage
    ├── report.py               # Report, ReportType
    └── notification.py         # NotificationResult, Channel
```

### 3.2 核心设计决策

#### 决策 1: 插件化数据源

```python
# crawler/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass(frozen=True)  # 不可变
class CrawlResult:
    source_id: str
    platform: str
    items: tuple[NewsItem, ...]
    fetched_at: datetime
    errors: tuple[str, ...] = ()

class CrawlerPlugin(ABC):
    """所有数据源实现此接口，自动注册"""

    @abstractmethod
    def source_id(self) -> str: ...

    @abstractmethod
    async def fetch(self, config: SourceConfig) -> CrawlResult: ...

    @property
    def rate_limit(self) -> float:
        return 1.0  # requests/second, 可覆盖
```

新增数据源: 创建 `plugins/xxx.py` 实现 `CrawlerPlugin` → 自动发现注册 → 零改动集成。

#### 决策 2: 并发采集引擎

```python
# crawler/pool.py
import asyncio
from concurrent.futures import ThreadPoolExecutor

class CrawlerPool:
    """并发采集，自适应限速"""

    def __init__(self, max_workers: int = 10):
        self.semaphore = asyncio.Semaphore(max_workers)
        self.session = aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(limit=20)
        )

    async def fetch_all(self, plugins: list[CrawlerPlugin]) -> list[CrawlResult]:
        """并发执行所有插件，带熔断"""
        tasks = [self._fetch_with_guard(p) for p in plugins]
        return await asyncio.gather(*tasks, return_exceptions=True)
```

效果: 40 平台从串行 80s → 并发 ~10s（10 worker, 自适应限速）。

#### 决策 3: 通知通道插件化

```python
# notification/base.py
class NotificationChannel(ABC):
    """通知通道接口"""

    @abstractmethod
    def channel_name(self) -> str: ...

    @abstractmethod
    def max_content_length(self) -> int: ...

    @abstractmethod
    async def send(self, content: str, config: ChannelConfig) -> SendResult: ...
```

消除 9 个 `send_to_*` 函数的复制粘贴，每个通道独立文件、独立测试。

#### 决策 4: Pydantic 配置模型

```python
# config/models.py
from pydantic import BaseModel, Field, validator

class AIConfig(BaseModel):
    model: str = "openai/gpt-4"
    api_key: str = Field(default="", env="AI_API_KEY")
    api_base: str = Field(default="", env="AI_API_BASE")
    timeout: int = Field(default=120, ge=10, le=600)
    temperature: float = Field(default=1.0, ge=0, le=2)
    max_tokens: int = Field(default=5000, ge=100, le=100000)
```

类型安全、自动验证、环境变量集成、错误消息友好。

#### 决策 5: Jinja2 报告模板

将 2,460 行 `html.py` 拆为:
- **模板文件** (`templates/*.html.j2`): 纯 HTML 结构 + 样式
- **渲染引擎** (`engine.py`): 数据准备 + 模板渲染 (~200 行)
- **静态资源** (`static/`): CSS/JS 分离

效果: 样式修改无需改 Python 代码，报告格式可扩展 (Markdown/JSON)。

---

## 四、分阶段执行计划

### Phase 0: 安全加固 + 基础设施（优先级 P0）

**目标**: 修复安全漏洞 + 建立日志基础设施 + 建立测试基线

| 任务 | 文件 | 说明 |
|------|------|------|
| 修复 SQL 注入 | `webui/job_manager.py:160` | ALTER TABLE 用白名单验证 |
| 消除裸 except | `extra_apis.py`, `job_manager.py` | 具体异常类型 + 日志 |
| 引入 structlog | 全局 | 替换 452 个 print() → 结构化日志 |
| SQLite 索引 | `job_manager.py` | 添加 status/created_at 索引 |
| SQLite WAL 模式 | `sqlite_mixin.py` | 并发读性能 5x |
| 测试基线 | `tests/` | 为关键路径补充测试 (覆盖率 → 40%) |

**预期效果**: 安全漏洞归零，作业查询性能 5x，可观测性从 0 到 1。

---

### Phase 1: 领域模型 + 配置重构

**目标**: 用 Pydantic 模型替代原始 dict，类型安全 + 自动验证

| 任务 | 说明 |
|------|------|
| 创建 `models/` | NewsItem, Platform, Job, Report 等 dataclass/Pydantic |
| 创建 `config/models.py` | Pydantic 配置模型 (替代 dict 传递) |
| 重写 `config/loader.py` | YAML → Pydantic 模型，自动验证 + 环境变量 |
| 迁移 `context.py` | AppContext 持有 Pydantic 配置而非 dict |

**预期效果**: 配置错误在启动时即报错 (而非运行时崩溃)，IDE 自动补全。

---

### Phase 2: 并发采集引擎

**目标**: 采集速度 80s → <15s

| 任务 | 说明 |
|------|------|
| 创建 `crawler/base.py` | CrawlerPlugin 抽象基类 |
| 创建 `crawler/registry.py` | 插件自动发现注册 |
| 创建 `crawler/pool.py` | asyncio + aiohttp 并发引擎 |
| 拆分 `fetcher.py` (6,787 行) | → `plugins/newsnow.py` + 各平台适配 |
| 拆分 `extra_apis.py` | → `plugins/dailyhot.py`, `plugins/newsapi.py` 等 |
| 创建 `middleware/` | rate_limiter + retry + cache + circuit_breaker |
| 迁移 RSS | → `plugins/rss.py` |

**预期效果**: 采集速度 5x+，新数据源零改动集成。

---

### Phase 3: 通知系统重构

**目标**: 并行推送 + 通道插件化

| 任务 | 说明 |
|------|------|
| 创建 `notification/base.py` | NotificationChannel 抽象基类 |
| 拆分 `senders.py` (1,391 行) | → `channels/telegram.py` 等 9 个文件 |
| 简化 `splitter.py` (1,672 行) | 缓存分批结果 + 策略模式 (→ ~400 行) |
| 重写 `dispatcher.py` | asyncio 并行推送 + 结果聚合 |
| 创建 `notification/registry.py` | 通道自动注册 |

**预期效果**: 推送延迟 3x 降低，新通道只需加一个文件。

---

### Phase 4: 报告系统重构

**目标**: 模板引擎化 + 多格式输出

| 任务 | 说明 |
|------|------|
| 引入 Jinja2 | 模板引擎 |
| 拆分 `html.py` (2,460 行) | → 模板文件 + 渲染引擎 (~200 行) |
| 创建 `report/templates/` | HTML 模板 (结构) + CSS (样式) 分离 |
| 创建 `report/renderers/` | HTML / Markdown / JSON 渲染器 |
| 增量渲染 | 流式生成，降低内存占用 |

**预期效果**: 内存占用降 50%+，样式修改零 Python 代码，支持 Markdown/JSON 输出。

---

### Phase 5: WebUI + 编排层重构

**目标**: Flask Blueprints 拆分 + Pipeline 编排

| 任务 | 说明 |
|------|------|
| 拆分 `app.py` (1,086 行) | → Flask Blueprints (jobs/config/reports/rss/health) |
| 重写 `__main__.py` (1,874 行) | CLI 层只做参数解析 → 调用 Orchestrator |
| 创建 `orchestrator/pipeline.py` | Pipeline: crawl → analyze → report → notify |
| 创建 `orchestrator/scheduler.py` | 内置 APScheduler，摆脱外部 cron |
| 健康检查 + 指标 | `/health` + `/metrics` 端点 |

**预期效果**: 路由文件 <200 行，内置调度无需 GitHub Actions。

---

### Phase 6: 功能增强

**目标**: 功能倍增

| 任务 | 说明 |
|------|------|
| 趋势对比 | 跨周期 (日/周) 趋势变化检测 |
| 历史回溯 | 按关键词查询历史趋势 |
| 跨平台关联 | 同一事件在不同平台的表现分析 |
| WebSocket 实时推送 | 热点变化实时通知 WebUI |
| 完整 RESTful API | OpenAPI 文档 + API Key 认证 |
| Schema 迁移系统 | `storage/migrations/` 版本化数据库变更 |

---

## 五、依赖变更

### 新增

| 包 | 用途 | 阶段 |
|----|------|------|
| `pydantic>=2.0` | 配置模型 + 数据验证 | Phase 1 |
| `structlog>=24.0` | 结构化日志 | Phase 0 |
| `aiohttp>=3.9` | 异步 HTTP 客户端 | Phase 2 |
| `jinja2>=3.1` | 报告模板引擎 | Phase 4 |
| `apscheduler>=3.10` | 内置任务调度 | Phase 5 |

### 可移除

| 包 | 原因 |
|----|------|
| `websockets` | aiohttp 内置 WebSocket |

---

## 六、风险控制

| 风险 | 缓解策略 |
|------|----------|
| 重构期间功能回归 | Phase 0 先建立测试基线 (40%+)，每阶段增量覆盖 |
| 异步迁移复杂度高 | Phase 2 先用 ThreadPoolExecutor 桥接，逐步迁移 async |
| 插件化过度设计 | 仅数据源和通知通道插件化，其他保持简单 |
| 配置格式不兼容 | Pydantic 模型兼容原 YAML 格式，零迁移成本 |
| 报告样式变化 | Jinja2 模板先 1:1 复制现有样式，再迭代改进 |

---

## 七、量化指标

| 指标 | 当前 | 目标 |
|------|------|------|
| 采集速度 (40 平台) | ~80s | <15s |
| 最大文件行数 | 6,787 行 | <500 行 |
| 超 1000 行文件数 | 8 | 0 |
| 测试覆盖率 | ~5% | >70% |
| print() 调用数 | 452 | 0 |
| 新增数据源成本 | 改 fetcher.py | 加 1 个文件 |
| 新增通知通道成本 | 改 senders.py + dispatcher | 加 1 个文件 |
| 通知推送延迟 | 串行 9 通道 | 并行 <3s |
| SQL 注入风险 | 1 处 | 0 |
| P0 安全问题 | 1 | 0 |
