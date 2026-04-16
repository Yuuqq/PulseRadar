"""
Hub 页面生成模块

生成 GitHub Pages 首页（报告聚合页），列出所有历史报告，
支持搜索、模式筛选、暗色模式、日期分组。
"""

import json
from collections import defaultdict


def generate_hub_html(manifest: dict) -> str:
    """根据 manifest 生成自包含的 Hub HTML 页面"""
    reports = sorted(
        manifest.get("reports", []),
        key=lambda r: (r.get("date", ""), r.get("time", "")),
        reverse=True,
    )

    # 按日期分组
    grouped: dict[str, list[dict]] = defaultdict(list)
    for r in reports:
        grouped[r.get("date", "unknown")].append(r)

    # 找到每种模式的最新报告
    latest_by_mode: dict[str, dict] = {}
    for r in reports:
        m = r.get("mode", "")
        if m not in latest_by_mode:
            latest_by_mode[m] = r

    manifest_json = json.dumps(manifest, ensure_ascii=False)

    cards_html = _build_cards_html(grouped)
    latest_links_html = _build_latest_links(latest_by_mode)

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PulseRadar — 报告中心</title>
<style>{_HUB_CSS}</style>
</head>
<body>
<div class="container">
  <header class="header">
    <div class="header-row">
      <h1 class="header-title">PulseRadar 报告中心</h1>
      <span class="header-count">{len(reports)} 份报告</span>
      <button class="theme-toggle" onclick="toggleTheme()" title="切换主题">🌓</button>
    </div>
  </header>
  <div class="toolbar">
    <input type="text" class="search-input" placeholder="搜索日期或模式…" oninput="onSearch(this.value)">
    <div class="mode-filters">
      <button class="mode-btn active" data-mode="all" onclick="filterMode('all')">全部</button>
      <button class="mode-btn" data-mode="current" onclick="filterMode('current')">当前榜单</button>
      <button class="mode-btn" data-mode="daily" onclick="filterMode('daily')">全天汇总</button>
      <button class="mode-btn" data-mode="incremental" onclick="filterMode('incremental')">增量分析</button>
    </div>
  </div>
  {latest_links_html}
  <main class="content">
    {cards_html}
  </main>
  <footer class="footer">
    <span class="footer-text">
      Powered by <a href="https://github.com/Banyeqidi001/PulseRadar" class="footer-link" target="_blank">PulseRadar</a>
    </span>
  </footer>
</div>
<script>
window.__MANIFEST__ = {manifest_json};
{_HUB_JS}
</script>
</body>
</html>"""


def _build_latest_links(latest_by_mode: dict[str, dict]) -> str:
    if not latest_by_mode:
        return ""
    mode_labels = {"current": "当前榜单", "daily": "全天汇总", "incremental": "增量分析"}
    links = []
    for mode, report in sorted(latest_by_mode.items()):
        label = mode_labels.get(mode, mode)
        path = report.get("path", "#")
        links.append(f'<a href="{path}" class="latest-link">{label}</a>')
    return (
        f'<div class="latest-bar"><span class="latest-label">最新报告</span>{"".join(links)}</div>'
    )


def _build_cards_html(grouped: dict[str, list[dict]]) -> str:
    sections = []
    for date in sorted(grouped.keys(), reverse=True):
        reports = grouped[date]
        cards = []
        for r in reports:
            mode = r.get("mode", "")
            mode_label = r.get("mode_label", mode)
            path = r.get("path", "#")
            time_display = r.get("time", "")
            total = r.get("total_titles", 0)
            stats = r.get("stats_count", 0)
            cards.append(
                f'<a href="{path}" class="card" data-mode="{mode}" data-date="{date}">'
                f'<div class="card-time">{time_display}</div>'
                f'<span class="card-badge mode-{mode}">{mode_label}</span>'
                f'<div class="card-stats">{total} 条新闻 · {stats} 个关键词</div>'
                f"</a>"
            )
        sections.append(
            f'<section class="date-group" data-date="{date}">'
            f'<h2 class="date-heading">{date}</h2>'
            f'<div class="card-grid">{"".join(cards)}</div>'
            f"</section>"
        )
    if not sections:
        return '<p class="empty-state">暂无报告</p>'
    return "\n".join(sections)


# ---------------------------------------------------------------------------
# Inline CSS
# ---------------------------------------------------------------------------
_HUB_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
  background: #f4f6fb;
  color: #111827;
  line-height: 1.6;
}
.container {
  max-width: 1200px;
  margin: 0 auto;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
.header {
  background: linear-gradient(135deg, #1d4ed8 0%, #0f766e 100%);
  color: white;
  padding: 24px 32px;
}
.header-row {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}
.header-title {
  font-size: 22px;
  font-weight: 700;
  letter-spacing: -0.3px;
}
.header-count {
  font-size: 14px;
  opacity: 0.85;
  background: rgba(255,255,255,0.18);
  padding: 4px 12px;
  border-radius: 6px;
}
.theme-toggle {
  margin-left: auto;
  background: rgba(255,255,255,0.2);
  border: 1px solid rgba(255,255,255,0.3);
  color: white;
  padding: 6px 10px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 16px;
}
.theme-toggle:hover { background: rgba(255,255,255,0.3); }

.toolbar {
  padding: 16px 32px;
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  align-items: center;
  background: white;
  border-bottom: 1px solid #e5e7eb;
}
.search-input {
  border: 1px solid #e2e8f0;
  border-radius: 999px;
  padding: 8px 16px;
  font-size: 14px;
  width: 260px;
  outline: none;
  background: #f8fafc;
}
.search-input:focus { border-color: #2563eb; background: white; }
.mode-filters { display: flex; gap: 6px; flex-wrap: wrap; }
.mode-btn {
  border: 1px solid #e2e8f0;
  background: white;
  color: #374151;
  padding: 6px 14px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
}
.mode-btn:hover { background: #f1f5f9; }
.mode-btn.active { background: #111827; color: white; border-color: #111827; }

.latest-bar {
  padding: 12px 32px;
  display: flex;
  gap: 10px;
  align-items: center;
  background: #eff6ff;
  border-bottom: 1px solid #dbeafe;
  flex-wrap: wrap;
}
.latest-label { font-size: 13px; font-weight: 600; color: #1d4ed8; }
.latest-link {
  font-size: 13px;
  color: #2563eb;
  text-decoration: none;
  background: white;
  padding: 4px 12px;
  border-radius: 6px;
  border: 1px solid #dbeafe;
}
.latest-link:hover { background: #dbeafe; }

.content { padding: 24px 32px; flex: 1; }
.date-group { margin-bottom: 32px; }
.date-heading {
  font-size: 16px;
  font-weight: 700;
  color: #374151;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 2px solid #e5e7eb;
}
.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 12px;
}
.card {
  display: block;
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 16px 20px;
  text-decoration: none;
  color: inherit;
  transition: all 0.2s;
}
.card:hover {
  box-shadow: 0 4px 16px rgba(15,23,42,0.1);
  transform: translateY(-2px);
  border-color: #2563eb;
}
.card-time { font-size: 20px; font-weight: 700; color: #0f172a; margin-bottom: 6px; }
.card-badge {
  display: inline-block;
  font-size: 12px;
  font-weight: 600;
  padding: 2px 10px;
  border-radius: 999px;
  margin-bottom: 8px;
}
.mode-current { background: #dbeafe; color: #1d4ed8; }
.mode-daily { background: #d1fae5; color: #065f46; }
.mode-incremental { background: #fef3c7; color: #92400e; }
.card-stats { font-size: 13px; color: #6b7280; }
.empty-state { text-align: center; color: #9ca3af; padding: 48px; font-size: 15px; }

.footer {
  padding: 20px 32px;
  text-align: center;
  background: #f8fafc;
  border-top: 1px solid #e5e7eb;
}
.footer-text { font-size: 13px; color: #6b7280; }
.footer-link { color: #2563eb; text-decoration: none; font-weight: 500; }
.footer-link:hover { text-decoration: underline; }

/* Dark mode */
body[data-theme="dark"] { background: #0f172a; color: #e2e8f0; }
body[data-theme="dark"] .header { background: linear-gradient(135deg, #1e293b 0%, #0f766e 100%); }
body[data-theme="dark"] .toolbar { background: #0b1220; border-color: #1f2937; }
body[data-theme="dark"] .search-input { background: #0f172a; border-color: #334155; color: #e2e8f0; }
body[data-theme="dark"] .mode-btn { background: #0f172a; color: #e2e8f0; border-color: #334155; }
body[data-theme="dark"] .mode-btn.active { background: #2563eb; border-color: #2563eb; }
body[data-theme="dark"] .latest-bar { background: #0b1220; border-color: #1f2937; }
body[data-theme="dark"] .latest-link { background: #0f172a; border-color: #1f2937; color: #60a5fa; }
body[data-theme="dark"] .date-heading { color: #e2e8f0; border-color: #1f2937; }
body[data-theme="dark"] .card { background: #0f172a; border-color: #1f2937; }
body[data-theme="dark"] .card:hover { border-color: #2563eb; box-shadow: 0 4px 16px rgba(0,0,0,0.3); }
body[data-theme="dark"] .card-time { color: #e2e8f0; }
body[data-theme="dark"] .card-stats { color: #94a3b8; }
body[data-theme="dark"] .footer { background: #0b1220; border-color: #1f2937; }
body[data-theme="dark"] .footer-text { color: #94a3b8; }

@media (max-width: 640px) {
  .header, .toolbar, .content, .latest-bar, .footer { padding-left: 16px; padding-right: 16px; }
  .search-input { width: 100%; }
  .card-grid { grid-template-columns: 1fr; }
}
"""

# ---------------------------------------------------------------------------
# Inline JS
# ---------------------------------------------------------------------------
_HUB_JS = """
let currentMode = 'all';
let searchTerm = '';
let debounceTimer;

function onSearch(value) {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(function() {
    searchTerm = value.toLowerCase().trim();
    applyFilters();
  }, 200);
}

function filterMode(mode) {
  currentMode = mode;
  document.querySelectorAll('.mode-btn').forEach(function(btn) {
    btn.classList.toggle('active', btn.dataset.mode === mode);
  });
  applyFilters();
}

function applyFilters() {
  document.querySelectorAll('.date-group').forEach(function(group) {
    var cards = group.querySelectorAll('.card');
    var anyVisible = false;
    cards.forEach(function(card) {
      var matchesMode = currentMode === 'all' || card.dataset.mode === currentMode;
      var text = (card.dataset.date + ' ' + card.textContent).toLowerCase();
      var matchesSearch = !searchTerm || text.indexOf(searchTerm) !== -1;
      var visible = matchesMode && matchesSearch;
      card.style.display = visible ? '' : 'none';
      if (visible) anyVisible = true;
    });
    group.style.display = anyVisible ? '' : 'none';
  });
}

function toggleTheme() {
  var body = document.body;
  var next = body.getAttribute('data-theme') === 'dark' ? '' : 'dark';
  body.setAttribute('data-theme', next);
  try { localStorage.setItem('hub-theme', next); } catch(e) {}
}

(function() {
  try {
    var saved = localStorage.getItem('hub-theme');
    if (saved) document.body.setAttribute('data-theme', saved);
  } catch(e) {}
})();
"""
