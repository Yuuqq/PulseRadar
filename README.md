# PulseRadar

多源新闻聚合引擎 — 捕获全网热点脉搏，筛选、分析、一步直达

> 基于 [TrendRadar](https://github.com/sansan0/TrendRadar) 二次开发

[![License](https://img.shields.io/badge/license-GPL--3.0-blue.svg?style=flat-square)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)

## 与 TrendRadar 的区别

| | PulseRadar | TrendRadar |
|---|---|---|
| **定位** | 个人定制的新闻聚合引擎 | 通用热点助手 |
| **架构** | 解耦编排器 (CrawlCoordinator + AnalysisEngine) | 单体 NewsAnalyzer (835行) |
| **报告布局** | 瀑布流多列卡片 | 单列线性排列 |
| **代码质量** | Ruff 全量检查 + pre-commit hooks | 无 lint 门控 |
| **AI 分析** | LongCat-Flash-Lite (预配置) | 需自行配置 |

## 核心能力

- **20+ 数据源** — 今日头条、微博、知乎、B站、36氪、Hacker News、Product Hunt、GitHub Trending 等
- **60+ RSS 订阅** — 自定义 RSS 源聚合
- **AI 智能分析** — 基于 LiteLLM 对接 100+ AI 模型，自动生成热点解读
- **9 通道推送** — 企业微信、Telegram、飞书、钉钉、邮件、Slack、Bark、ntfy、Webhook
- **关键词雷达** — 频率词匹配 + 权重排序，只推你关心的内容
- **瀑布流报告** — 多列卡片布局，紧凑高效
- **MCP 协议** — 接入 Claude Desktop 等 AI 客户端直接查询

## 快速开始

```bash
# 克隆
git clone https://github.com/Yuuqq/PulseRadar.git
cd PulseRadar

# 安装依赖
pip install -r requirements.txt

# 配置
cp config/config.yaml.example config/config.yaml
# 编辑 config/config.yaml 设置平台、关键词、推送通道

# 运行
python -m trendradar
```

### Docker 部署

```bash
docker compose up -d
```

## 配置

主配置文件 `config/config.yaml`，核心项：

```yaml
# 监控平台
platforms:
  - id: toutiao
    name: 今日头条
  - id: weibo
    name: 微博

# AI 分析
ai:
  model: openai/LongCat-Flash-Lite
  api_key: your-key
  api_base: https://api.longcat.chat/openai/v1

# 关键词过滤
frequency_words: config/frequency_words.txt

# 推送通道 (按需启用)
notification:
  feishu:
    enabled: true
    webhook_url: https://...
```

详细配置说明参考上游 [TrendRadar 文档](https://github.com/sansan0/TrendRadar)。

## 技术架构

```
数据源 → CrawlCoordinator → 冻结DTO → AnalysisEngine → HTML报告/推送
           ├─ 热榜爬虫                    ├─ 模式策略
           ├─ RSS 抓取                    ├─ AI 分析
           └─ Extra API                   └─ 通知分发
```

| 模块 | 位置 | 职责 |
|---|---|---|
| CrawlCoordinator | `trendradar/core/crawl_coordinator.py` | 编排所有爬虫，返回 CrawlOutput |
| AnalysisEngine | `trendradar/core/analysis_engine.py` | 模式策略 + 分析管线 + AI |
| NewsAnalyzer | `trendradar/__main__.py` | 薄门面 (~80行)，串联两个编排器 |
| MCP Server | `mcp_server/server.py` | FastMCP 2.0 协议接口 |

## 上游关系

本项目基于 [TrendRadar v5.5.3](https://github.com/sansan0/TrendRadar) 二次开发，主要改动：

1. **God Object 分解** — NewsAnalyzer 从 835 行拆分为 CrawlCoordinator + AnalysisEngine + 80 行门面
2. **回调消除** — 5 个核心模块的 `_fn` 回调参数全部替换为直接调用
3. **冻结 DTO** — CrawlOutput / AnalysisOutput / RSSOutput 作为阶段边界数据契约
4. **瀑布流报告** — 多列 masonry 布局替代单列线性布局
5. **质量门控** — Ruff lint + format + pre-commit hooks
6. **品牌重命名** — TrendRadar → PulseRadar

## License

GPL-3.0 — 继承上游 [TrendRadar](https://github.com/sansan0/TrendRadar) 协议
