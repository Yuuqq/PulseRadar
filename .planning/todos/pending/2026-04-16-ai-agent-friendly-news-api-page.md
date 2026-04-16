---
created: "2026-04-16T14:04:32.334Z"
title: "Add AI Agent-friendly news API page"
area: api
priority: high
files:
  - trendradar/webui/
  - mcp_server/
---

## Problem

TrendRadar 目前缺少一个专门为 AI Agent 设计的资讯获取页面/接口。现有的 Web UI 和 MCP Server 面向人类用户或特定 MCP 协议，但没有一个通用的、AI Agent 友好的页面来提供结构化的新闻资讯数据。

需要设计一个页面/端点，让各种 AI Agent（不仅限于 MCP 客户端）能够方便地获取、筛选和消费 TrendRadar 聚合的热点新闻和分析结果。

关键考虑：
- 结构化输出（JSON/Markdown），方便 AI 解析
- 支持按时间、分类、关键词筛选
- 包含摘要和全文两种粒度
- 考虑 token 预算友好（AI 上下文窗口有限）
- 可能需要分页、摘要优先等策略
- 与现有 MCP Server 和 Web UI 的关系需要明确

## Solution

这是一个重要功能，需要在下一个 milestone 中作为独立 phase 来规划和设计。建议：

1. 研究主流 AI Agent 的数据消费模式（OpenAI function calling, Claude tool use, LangChain, AutoGPT 等）
2. 设计 AI-friendly API 规范（考虑 OpenAPI/JSON Schema）
3. 实现专用端点或页面
4. 提供多种输出格式（JSON, Markdown, 纯文本摘要）
5. 考虑与现有 MCP Server 的整合或互补关系
