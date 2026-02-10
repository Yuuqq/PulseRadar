# Workflow UI 变更记录（2026-02-09）

本文档用于记录本轮围绕 `Workflow + Jobs` 的改造内容，方便后续溯源、回归验证与继续修订。

## 1. 变更目标

- 将项目推进为具备 UI 工作流能力的应用。
- 打通「参数化运行 → 任务可观测 → 失败后重试策略 → 模板管理」闭环。
- 补齐可追踪信息（重试来源、重试策略、重试说明）与可维护文档。

## 2. 本轮功能清单

### 2.1 Workflow 页面与参数化运行

- 新增 `/workflow` 页面入口（导航可达）。
- `POST /api/run` 支持参数化运行：`scope`、`force_ai`、`force_push`。
- CLI 新增 `--config` 参数，支持按 scope 生成临时配置并执行。

### 2.2 Workflow 模板管理

- 新增模板持久化（SQLite）：`workflow_templates`。
- 支持模板 CRUD、导出、导入、导入预览。
- 导入预览支持：
  - Action 过滤（all/create/update/skip）
  - 名称搜索
  - 选择性导入（checkbox）

### 2.3 Jobs 页面增强

- URL 深链状态：支持 `status/q/page/page_size/job_id`。
- 选中任务分享链接打开后，自动滚动并高亮目标卡片。
- 任务详情新增阶段时间线（`queued → starting → crawl → rss → ai → report → notify → finished`）。
- 失败阶段标记与阶段级快捷重试入口。

### 2.4 重试策略（核心）

- `POST /api/jobs/<job_id>/retry` 支持策略参数：
  - `full`（全量重跑）
  - `from_failed_stage`（从失败阶段继续）
- 分段策略规则：
  - `notify` 失败：自动追加 `--force-push`
  - `ai/report` 失败：自动追加 `--force-ai`
  - 其他阶段：自动回退 `full`
- 返回并持久化策略信息：
  - `retry_source_job_id`
  - `retry_strategy`
  - `retry_strategy_note`

### 2.5 详情与列表的可视化策略信息

- 任务详情新增：重试来源 / 重试策略 / 重试说明。
- 左侧任务列表悬停 tooltip 显示策略信息。
- tooltip 长文自动截断。
- 详情说明支持「查看更多/收起」。
- 展开状态按任务维度持久化到 `localStorage`。
- 新增「清空展开状态」按钮，支持数量提示。

### 2.6 统一确认弹窗（全局能力）

- 从 jobs 私有确认逻辑重构为全局弹窗：`showConfirmDialog(options)`。
- 全局确认弹窗位于 `base.html`，可供所有页面复用。
- 交互细节：
  - 打开默认聚焦取消按钮
  - `Esc` 关闭
  - `Enter` 确认（焦点在 `textarea/contentEditable` 时忽略）

## 3. 关键文件变更索引

- CLI 与运行入口
  - `trendradar/__main__.py`
- Web UI 后端
  - `trendradar/webui/app.py`
  - `trendradar/webui/job_manager.py`
- Web UI 前端
  - `trendradar/webui/templates/base.html`
  - `trendradar/webui/templates/workflow.html`
  - `trendradar/webui/templates/jobs.html`
  - `trendradar/webui/static/js/main.js`
  - `trendradar/webui/static/css/style.css`
- 测试
  - `tests/test_webui_app_jobs.py`

## 4. 数据结构与兼容性说明

### 4.1 jobs 表新增字段

- `retry_source_job_id` (TEXT)
- `retry_strategy` (TEXT)
- `retry_strategy_note` (TEXT)

兼容策略：`JobManager` 初始化时通过 `PRAGMA table_info(jobs)` 进行增量补列（`ALTER TABLE`），避免破坏已有库。

### 4.2 workflow_templates 表

- 用于保存工作流模板（名称、scope、force 标志、时间戳）。
- 含名称大小写不敏感唯一索引与更新时间索引。

## 5. 测试与验证基线

- 本轮基线：`python -m pytest -q tests`
- 当前结果：`28 passed`

重点覆盖的场景包括：

- Workflow 页面可用性
- 模板 CRUD / 导入导出 / 预览
- 任务详情时间线与失败阶段
- 重试策略（全量 / 分段 / 回退）
- 重试策略信息在任务详情可见
- 全局确认弹窗与 jobs 页面脚本要素存在性

## 6. 后续修订建议（入口清晰）

### 6.1 若继续扩展重试策略

- 入口：`trendradar/webui/app.py` 中 retry 策略解析与命令构建逻辑。
- 建议：将策略规则表配置化，减少硬编码。

### 6.2 若继续优化确认交互

- 入口：`trendradar/webui/static/js/main.js` 的 `showConfirmDialog`。
- 建议：补充“次级文案/风险图标/倒计时确认”等可选参数。

### 6.3 若继续优化可观测性

- 入口：`trendradar/webui/job_manager.py` 阶段追踪与日志推断。
- 建议：引入更稳定的阶段事件埋点（替代纯关键字推断）。

---

维护建议：后续每次 workflow/jobs 改造都在 `docs/` 下追加一份同格式日期文档，或合并到统一 `CHANGELOG`。
