# Changelog

本文件用于聚合记录 TrendRadar 的工程变更，便于溯源、回归验证与后续修订。

## 2026-04-13

### 依赖管理优化（Dependency Hygiene）

- 关键变更：
  - `boto3` 从核心依赖移至可选依赖，通过 `pip install trendradar[s3]` 安装 S3 存储支持
  - `tenacity` 版本从 `==8.5.0` 改为 `>=9.0,<10`（范围约束）
  - `requirements.txt` 改为从 `pyproject.toml` 自动生成（`uv pip compile`），补齐缺失的 `structlog` 和 `pydantic`
  - Docker 镜像（Dockerfile 和 Dockerfile.mcp）已自动包含 boto3，容器部署无需任何变更
- 影响范围：`pyproject.toml`、`requirements.txt`、`docker/Dockerfile`、`docker/Dockerfile.mcp`、`trendradar/storage/manager.py`
- 兼容性：
  - Docker 部署：完全兼容（镜像自动安装 boto3）
  - `pip install` 用户：若使用 S3 远程存储，需改用 `pip install trendradar[s3]`
  - CLI / config.yaml / 公共 API：无变化
- 验证基线：`python -m pytest -q tests`

## 2026-02-09

### Workflow UI（参数化运行 + Jobs 可观测 + 重试策略 + 模板管理）

- 详情文档：`docs/workflow_ui_change_log_2026-02-09.md`
- 关键变更：
  - 新增 `/workflow` 页面与参数化运行（`scope` / `force_ai` / `force_push`）
  - 新增工作流模板持久化与导入导出能力
  - 增强 Jobs 页面深链、阶段时间线与失败重试策略
  - 持久化重试元信息（来源任务、策略、说明）
  - 引入全局确认弹窗 `showConfirmDialog(options)`
- 验证基线：`python -m pytest -q tests`（28 passed）

### RSS 源扩充（默认配置 + UI 推荐）

- 详情文档：`docs/workflow_ui_change_log_2026-02-09.md`
- 关键变更：
  - 扩充默认 `rss.feeds`，新增多类国际/科技/AI/安全/金融源（默认 `enabled: false`）
  - 扩充 `RSS 源管理` 页面推荐源按钮，支持一键添加更多可用源
  - 新增前进行可达性校验（HTTP 200 + entries>0）并做去重检查
- 影响范围：`config/config.yaml`、`trendradar/webui/templates/rss.html`
- 配置影响：`config.config.yaml -> rss.feeds`
- 兼容性：向后兼容（仅新增可选源，不改变已有启用状态）
- 验证基线：`python -m pytest -q tests`（28 passed）

### RSS 精选启用模板（科技+AI / 全球宏观 / 网络安全）

- 详情文档：`docs/workflow_ui_change_log_2026-02-09.md`
- 关键变更：
  - 在 `RSS 源管理` 页面新增 3 套一键启用模板与“一键清空全部启用”
  - 模板自动补齐缺失源卡片并启用，已存在源仅变更启用状态
  - 操作接入全局确认弹窗 `showConfirmDialog`（无弹窗能力时回退 `confirm`）
- 影响范围：`trendradar/webui/templates/rss.html`
- 配置影响：无（仅前端交互增强）
- 兼容性：向后兼容
- 验证基线：`python -m pytest -q tests`（29 passed）

### RSS 启用源导出（JSON）

- 详情文档：`docs/workflow_ui_change_log_2026-02-09.md`
- 关键变更：
  - 在 RSS 页面新增“导出当前启用源(JSON)”按钮
  - 导出内容包含：`rss.enabled`、`freshness_filter`、当前已启用 `feeds`
  - 导出文件名含时间戳，便于多环境复用与版本留档
- 影响范围：`trendradar/webui/templates/rss.html`
- 配置影响：无（导出能力，不改后端配置结构）
- 兼容性：向后兼容
- 验证基线：`python -m pytest -q tests`（29 passed）

### RSS 启用源导入（JSON）

- 详情文档：`docs/workflow_ui_change_log_2026-02-09.md`
- 关键变更：
  - 在 RSS 页面新增“导入启用源(JSON)”按钮（文件选择 + 解析回灌）
  - 支持导入结构：`{ rss: { enabled, freshness_filter, feeds } }` 或 `{ feeds: [...] }`
  - 导入时自动新增缺失源、更新已有源名称/URL、同步启用状态
- 影响范围：`trendradar/webui/templates/rss.html`
- 配置影响：无（前端导入编辑能力）
- 兼容性：向后兼容
- 验证基线：`python -m pytest -q tests`（29 passed）

### RSS 导入预览（二次确认）

- 详情文档：`docs/workflow_ui_change_log_2026-02-09.md`
- 关键变更：
  - 导入前新增预览统计：有效数、新增数、更新数、跳过数、启用/关闭数量
  - 预览弹窗展示示例 ID，并在二次确认后才真正写入页面
- 影响范围：`trendradar/webui/templates/rss.html`
- 配置影响：无
- 兼容性：向后兼容
- 验证基线：`python -m pytest -q tests`（29 passed）

### RSS 导入预览明细（前 N 条）

- 详情文档：`docs/workflow_ui_change_log_2026-02-09.md`
- 关键变更：
  - 导入预览增加明细列表（默认展示前 10 条）
  - 明细项展示 `create/update/skip`、feed id、启用状态或跳过原因
  - 超过展示上限时追加“还有 N 条未展示”提示
- 影响范围：`trendradar/webui/templates/rss.html`
- 配置影响：无
- 兼容性：向后兼容
- 验证基线：`python -m pytest -q tests`（29 passed）

### RSS 导入预览按 Action 过滤

- 详情文档：`docs/workflow_ui_change_log_2026-02-09.md`
- 关键变更：
  - 新增导入预览过滤器：`all/create/update/skip`
  - 确认弹窗中的“导入预览明细”按所选 action 展示
  - 过滤结果为空时显示明确提示，避免误解为功能失效
- 影响范围：`trendradar/webui/templates/rss.html`
- 配置影响：无
- 兼容性：向后兼容
- 验证基线：`python -m pytest -q tests`（29 passed）

### RSS 预览过滤持久化（localStorage）

- 详情文档：`docs/workflow_ui_change_log_2026-02-09.md`
- 关键变更：
  - 导入预览 action 过滤条件持久化到 `localStorage`
  - 页面加载时自动恢复上次选择（all/create/update/skip）
  - 过滤值读取时进行规范化与兜底，避免异常值污染
- 影响范围：`trendradar/webui/templates/rss.html`
- 配置影响：无
- 兼容性：向后兼容
- 验证基线：`python -m pytest -q tests`（29 passed）

### RSS 预览过滤一键重置

- 详情文档：`docs/workflow_ui_change_log_2026-02-09.md`
- 关键变更：
  - 新增“重置为全部(all)”按钮
  - 一键恢复导入预览过滤条件到 `all` 并同步持久化
  - 重置完成后给出成功提示，便于快速回退筛选视图
- 影响范围：`trendradar/webui/templates/rss.html`
- 配置影响：无
- 兼容性：向后兼容
- 验证基线：`python -m pytest -q tests`（29 passed）

### RSS 预览过滤状态徽标

- 详情文档：`docs/workflow_ui_change_log_2026-02-09.md`
- 关键变更：
  - 新增“当前过滤”状态文案（例如：`当前过滤：仅更新 (update)`）
  - 过滤器切换、恢复、重置时实时刷新状态显示
  - 降低误操作概率，明确当前预览明细的筛选上下文
- 影响范围：`trendradar/webui/templates/rss.html`
- 配置影响：无
- 兼容性：向后兼容
- 验证基线：`python -m pytest -q tests`（29 passed）

### RSS 预览展示条数预估

- 详情文档：`docs/workflow_ui_change_log_2026-02-09.md`
- 关键变更：
  - 新增“本次导入将展示”提示，按当前 action 过滤动态显示条数
  - 未加载导入文件时显示占位提示，避免误判
  - 导入文件解析后、过滤切换后、重置后均实时刷新预估数
- 影响范围：`trendradar/webui/templates/rss.html`
- 配置影响：无
- 兼容性：向后兼容
- 验证基线：`python -m pytest -q tests`（29 passed）

### RSS 导入跳过原因统计

- 详情文档：`docs/workflow_ui_change_log_2026-02-09.md`
- 关键变更：
  - 新增“跳过原因统计”摘要（缺 id / 缺 url / 非对象 / 其他）
  - 导入预览确认文案中同步展示跳过原因分布
  - 在过滤切换、重置与导入解析后实时刷新统计显示
- 影响范围：`trendradar/webui/templates/rss.html`
- 配置影响：无
- 兼容性：向后兼容
- 验证基线：`python -m pytest -q tests`（29 passed）

### RSS 跳过项自动定位与高亮

- 详情文档：`docs/workflow_ui_change_log_2026-02-09.md`
- 关键变更：
  - 导入完成后若存在 skip 项，自动定位第一条可定位项并高亮
  - 对“缺少 url”且可定位 id 的 skip 项，自动补建卡片以便快速修正
  - 增加高亮样式与自动清除逻辑，避免常驻干扰
- 影响范围：`trendradar/webui/templates/rss.html`、`trendradar/webui/static/css/style.css`
- 配置影响：无
- 兼容性：向后兼容
- 验证基线：`python -m pytest -q tests`（29 passed）

---

维护约定：后续每次 workflow/jobs 或其他关键模块改造，均在本文件追加日期条目，并链接对应的详细设计或变更记录文档。

## 条目模板（复制使用）

```md
## YYYY-MM-DD

### 变更主题（模块/能力）

- 详情文档：`docs/xxx_change_log_YYYY-MM-DD.md`
- 关键变更：
  - 变更点 1
  - 变更点 2
  - 变更点 3
- 影响范围：`路径A`、`路径B`
- 配置影响：无 / `config.xxx`
- 兼容性：向后兼容 / 需迁移说明
- 验证基线：`python -m pytest -q tests`（X passed）
```
