---
created: "2026-04-16T14:04:32.334Z"
updated: "2026-04-17T00:00:00.000Z"
title: "Add AI Agent-friendly news API page"
area: api
priority: high
files:
  - trendradar/webui/
  - mcp_server/
  - trendradar/report/
  - reports/api/
---

## Problem

TrendRadar 目前缺少一个专门为 AI Agent 设计的资讯获取接口。现有的 Web UI 和 MCP Server 面向人类用户或特定 MCP 协议客户端，但没有一个通用的、AI Agent 友好的数据端点来提供结构化的新闻资讯。

需要设计一个接口，让各种 AI Agent（不仅限于 MCP 客户端）能够方便地获取、筛选和消费 TrendRadar 聚合的热点新闻和分析结果。

## Design Decisions (2026-04-17 探索讨论)

### 定位
- **独立的定时摘要服务** — 与 MCP Server 形成互补，不替代
- MCP：面向实时交互式查询（Claude Desktop、Cline 等）
- 新 API：面向定时批量拉取（通用 AI Agent 框架如 LangChain、CrewAI、AutoGPT 等）

### 使用场景
- **主场景**：AI Agent 定时拉取（如每日早晨获取昨日热点摘要）
- **核心用途**：
  1. 趋势分析（今日 vs 昨日热度变化、新增/消失话题）
  2. 回答用户提问（AI 基于数据回答"今天 XX 领域有什么大事"）

### 技术架构

**拉模式（Pull）** — 完全契合现有无后端架构：
- GitHub Actions 爬虫运行时生成静态 JSON 文件
- 发布到 GitHub Pages（与现有 `reports/` hub 架构一致）
- 无状态、无订阅管理、无认证复杂度

**按关键词组切分** — 复用 `frequency_words.txt` 现有配置：
```
reports/api/daily/
  ├── _index.json         # 元数据：可用词组列表 + 更新时间
  ├── ai.json             # "AI"词组匹配到的所有热点
  ├── 股市.json            # "股市"词组匹配到的所有热点
  └── ...
```

AI Agent 使用流程：
1. 拉 `_index.json` 看可用词组
2. 按需拉取感兴趣的 `{词组}.json`

### JSON Schema（建议）

```json
{
  "keyword_group": "AI",
  "date": "2026-04-17",
  "generated_at": "2026-04-17T08:00:00Z",
  "summary": "今日 AI 相关热点共 25 条，相比昨日 +8。主要聚焦在 GPT-5 发布和国产大模型竞赛。",
  "trend": {
    "total_today": 25,
    "total_yesterday": 17,
    "change": "+8",
    "direction": "rising",
    "new_topics": ["GPT-5 发布", "Claude Opus 5"],
    "declining_topics": ["..."]
  },
  "items": [
    {
      "title": "OpenAI 发布 GPT-5",
      "platforms": [
        {"name": "微博", "rank": 1, "url": "..."},
        {"name": "知乎", "rank": 3, "url": "..."}
      ],
      "first_seen": "2026-04-17T06:30:00Z",
      "ai_summary": "...",
      "matched_keywords": ["GPT-5", "OpenAI"],
      "heat_trend": "new"
    }
  ]
}
```

**设计要点：**
- 顶层 `summary`：极简概括，AI Agent 只看这个就能回答"今天有什么大事"
- `trend` 块：专门支撑趋势分析场景
- `items` 跨平台聚合：同一条新闻在多平台出现时合并，避免重复
- `heat_trend` 字段：每条新闻自身的趋势标记（new/rising/stable/falling）

## Open Questions

- 现有 `trendradar/core/frequency.py` 和 `analyzer.py` 是否能直接输出跨平台聚合结构？还是需要新增聚合层？
- `trend` 对比的"昨日"数据来源 — SQLite 本地存储 vs 历史 manifest？
- `ai_summary` 字段的生成策略 — 沿用现有 AI 分析结果 vs 新增专用摘要 prompt？
- 是否需要 `weekly.json` / `monthly.json` 等更长周期的聚合？

## Solution

作为下一个 milestone（v1.1）的独立 phase 来规划和实现：

1. **研究**：现有 `frequency.py` / `trend.py` / `analyzer.py` 的输出结构，评估复用方案
2. **设计**：最终确定 JSON Schema 字段，产出 OpenAPI/JSON Schema 规范
3. **实现**：
   - 新增 `trendradar/report/api_builder.py`（或类似模块）生成 JSON 文件
   - 在 `generate_html_report()` 或 pipeline 尾部 hook 进去
   - 与 GitHub Pages 发布流程整合（类似现有 `github_pages_dir` 逻辑）
4. **文档**：编写 AI Agent 接入指南（示例 curl、Python、LangChain 集成）
5. **互补定位**：明确与 MCP Server 的分工，在 README 中说明

## Implementation Hints

- 入口点：`trendradar/context.py:generate_html()` 已有 `github_pages_dir` 判定分支，可在同处新增 `api_dir`
- 数据源：`trendradar/core/pipeline.py:run_analysis_pipeline()` 已经产出 stats + trend 数据
- 复用：`trendradar/report/manifest.py` 的 load/save 模式可作为 JSON 文件写入的参考范式
