"""
HTML 报告渲染模块

基于 Jinja2 模板渲染 HTML 报告。
模板文件位于 ``trendradar/report/templates/``：
- ``report.html.j2``      —— 主壳（DOCTYPE/head/body/footer/section_tabs）
- ``_new_titles.html.j2`` —— "本次新增热点" 区块
- ``report.css``          —— 内联 CSS 资源
- ``report.js``           —— 内联 JS 资源

各 section 的复杂构件（hotlist/rss/standalone/ai_analysis）仍由
``html_sections.py`` 中的纯函数返回 HTML 字符串，本模块在传入模板前
统一用 ``Markup`` 包装以避免双重转义。
"""

from collections.abc import Callable
from datetime import datetime
from functools import lru_cache
from typing import Any

from jinja2 import Environment, PackageLoader, StrictUndefined, select_autoescape
from markupsafe import Markup

from trendradar.ai.formatter import render_ai_analysis_html_rich
from trendradar.report.helpers import html_escape
from trendradar.report.html_scripts import REPORT_JS
from trendradar.report.html_sections import (
    add_section_divider,
    build_hotlist_view,
    render_rss_stats_html,
    render_standalone_html,
    wrap_section,
)
from trendradar.report.html_styles import REPORT_CSS


@lru_cache(maxsize=1)
def _get_env() -> Environment:
    """构建并缓存 Jinja2 环境（启用对 .html/.html.j2 的自动转义）。"""
    return Environment(
        loader=PackageLoader("trendradar.report", "templates"),
        autoescape=select_autoescape(("html", "htm", "xml", "j2")),
        undefined=StrictUndefined,
        trim_blocks=False,
        lstrip_blocks=False,
        keep_trailing_newline=False,
    )


_SECTION_LABELS_EN = {
    "hotlist": "Hot",
    "rss": "RSS",
    "new_items": "New",
    "standalone": "Standalone",
    "ai_analysis": "AI Analysis",
}


def _build_section_tabs_html(available_sections: list[str], section_labels: dict[str, str]) -> Markup:
    """构造 section 切换 tab 的 HTML（少于 2 个时返回空 Markup）。"""
    if len(available_sections) <= 1:
        return Markup("")
    parts = [
        """
                <div class="section-tabs" role="tablist" aria-label="区域切换">
                    <button class="section-tab active" data-section="all" data-i18n-en="All" data-i18n-zh="全部">All</button>"""
    ]
    for region in available_sections:
        label_zh = section_labels.get(region, region)
        label_en = _SECTION_LABELS_EN.get(region, label_zh)
        parts.append(
            f"""
                    <button class="section-tab" data-section="{region}" data-i18n-en="{label_en}" data-i18n-zh="{label_zh}">{label_en}</button>"""
        )
    parts.append(
        """
                </div>"""
    )
    return Markup("".join(parts))


def _build_hotlist_section(
    report_data: dict,
    display_mode: str,
    alternate_report_data: dict | None,
    alternate_display_mode: str | None,
) -> Markup:
    """构造热榜区域（含视图切换 + 搜索框）。"""
    if not report_data.get("stats"):
        return Markup("")

    view_options = [display_mode]
    if (
        alternate_report_data
        and alternate_display_mode
        and alternate_display_mode not in view_options
    ):
        view_options.append(alternate_display_mode)

    view_toggle_html = ""
    if len(view_options) > 1:
        labels_en = {"keyword": "Keyword", "platform": "Platform"}
        labels_zh = {"keyword": "关键词", "platform": "平台"}
        view_order = [v for v in ["keyword", "platform"] if v in view_options]
        view_toggle_html = '<div class="view-toggle" role="tablist">'
        for view in view_order:
            le = labels_en.get(view, view)
            lz = labels_zh.get(view, view)
            view_toggle_html += (
                f'<button class="view-btn" data-view="{view}" '
                f'data-i18n-en="{le}" data-i18n-zh="{lz}">{le}</button>'
            )
        view_toggle_html += "</div>"

    main_view_html = build_hotlist_view(report_data["stats"], display_mode)
    alternate_view_html = ""
    if alternate_report_data and alternate_display_mode:
        alternate_view_html = build_hotlist_view(
            alternate_report_data.get("stats", []), alternate_display_mode
        )

    return Markup(
        f"""
                <div class="hotlist-section">
                    <div class="controls">
                        <div class="controls-left">
                            {view_toggle_html}
                        </div>
                        <div class="controls-right">
                            <input id="search-input" class="search-input" type="search"
                                placeholder="Search title / source / keyword"
                                data-i18n-en-placeholder="Search title / source / keyword"
                                data-i18n-zh-placeholder="搜索标题/来源/关键词">
                        </div>
                    </div>
                    {main_view_html}
                    {alternate_view_html}
                    <div id="search-empty" style="display:none; color:#94a3b8; font-size:13px; margin-top:8px;"
                        data-i18n-en="No matches" data-i18n-zh="无匹配结果">No matches</div>
                </div>"""
    )


def _build_new_titles_html(report_data: dict, show_new_section: bool) -> Markup:
    """构造 "本次新增热点" 区域。"""
    if not (show_new_section and report_data.get("new_titles")):
        return Markup("")

    sources: list[dict[str, Any]] = []
    for source_data in report_data["new_titles"]:
        items = []
        for idx, title_data in enumerate(source_data["titles"], 1):
            ranks = title_data.get("ranks", [])
            rank_class = ""
            if ranks:
                min_rank = min(ranks)
                if min_rank <= 3:
                    rank_class = "top"
                elif min_rank <= title_data.get("rank_threshold", 10):
                    rank_class = "high"
                rank_text = (
                    str(ranks[0]) if len(ranks) == 1 else f"{min(ranks)}-{max(ranks)}"
                )
            else:
                rank_text = "?"

            link_url = title_data.get("mobile_url") or title_data.get("url", "")
            items.append(
                {
                    "number": idx,
                    "rank_class": rank_class,
                    "rank_text": rank_text,
                    "title": title_data["title"],  # autoescape 会处理
                    "link_url": link_url,
                }
            )
        sources.append(
            {
                "source_name": source_data["source_name"],  # autoescape 会处理
                "items": items,
            }
        )

    template = _get_env().get_template("_new_titles.html.j2")
    return Markup(
        template.render(
            total_new_count=report_data["total_new_count"],
            sources=sources,
        )
    )


def _assemble_section_blocks(
    region_order: list[str],
    region_contents: dict[str, Any],
) -> list[Markup]:
    """按 region_order 顺序组装各区块（含 wrap_section 与分割线）。"""
    blocks: list[Markup] = []
    has_previous_content = False
    for region in region_order:
        content = region_contents.get(region, "")
        if region == "new_items":
            new_html, rss_new = content
            section_content = ""
            if new_html:
                if has_previous_content:
                    new_html = add_section_divider(new_html)
                section_content += new_html
            if rss_new:
                if section_content or has_previous_content:
                    rss_new = add_section_divider(rss_new)
                section_content += rss_new
            if section_content:
                blocks.append(Markup(wrap_section(region, section_content)))
                has_previous_content = True
        elif content:
            if has_previous_content:
                content = add_section_divider(content)
            blocks.append(Markup(wrap_section(region, content)))
            has_previous_content = True
    return blocks


def render_html_content(
    report_data: dict,
    total_titles: int,
    mode: str = "daily",
    update_info: dict | None = None,
    *,
    region_order: list[str] | None = None,
    get_time_func: Callable[[], datetime] | None = None,
    rss_items: list[dict] | None = None,
    rss_new_items: list[dict] | None = None,
    display_mode: str = "keyword",
    standalone_data: dict | None = None,
    ai_analysis: Any | None = None,
    show_new_section: bool = True,
    alternate_report_data: dict | None = None,
    alternate_display_mode: str | None = None,
) -> str:
    """渲染 HTML 报告内容（基于 Jinja2 模板）。

    Args:
        report_data: 报告数据字典，包含 stats, new_titles, failed_ids, total_new_count
        total_titles: 新闻总数
        mode: 报告模式 ("daily", "current", "incremental")
        update_info: 更新信息（可选）
        region_order: 区域显示顺序列表
        get_time_func: 获取当前时间的函数（可选，默认使用 datetime.now）
        rss_items: RSS 统计条目列表（可选）
        rss_new_items: RSS 新增条目列表（可选）
        display_mode: 显示模式 ("keyword"=按关键词分组, "platform"=按平台分组)
        standalone_data: 独立展示区数据（可选），包含 platforms 和 rss_feeds
        ai_analysis: AI 分析结果对象（可选），AIAnalysisResult 实例
        show_new_section: 是否显示新增热点区域
        alternate_report_data: 备用报告数据（可选，用于关键词/平台切换）
        alternate_display_mode: 备用显示模式 (keyword/platform)

    Returns:
        渲染后的 HTML 字符串
    """
    if region_order is None:
        region_order = ["hotlist", "rss", "new_items", "standalone", "ai_analysis"]

    # —— 计算顶部信息 ——
    mode_label = {
        "current": "当前榜单",
        "incremental": "增量分析",
    }.get(mode, "全天汇总")
    hot_news_count = sum(len(stat["titles"]) for stat in report_data["stats"])
    now = get_time_func() if get_time_func else datetime.now()
    time_str = now.strftime("%m-%d %H:%M")

    # —— 失败平台列表（已 escape）——
    failed_ids = [html_escape(fid) for fid in (report_data.get("failed_ids") or [])]

    # —— 各区块 HTML（均为 Markup，已转义/由内部确保安全） ——
    stats_html = _build_hotlist_section(
        report_data, display_mode, alternate_report_data, alternate_display_mode
    )
    new_titles_html = _build_new_titles_html(report_data, show_new_section)
    rss_stats_html = (
        Markup(render_rss_stats_html(rss_items, "RSS 订阅更新")) if rss_items else Markup("")
    )
    rss_new_html = (
        Markup(render_rss_stats_html(rss_new_items, "RSS 新增更新"))
        if rss_new_items
        else Markup("")
    )
    standalone_html = Markup(render_standalone_html(standalone_data))
    ai_html = Markup(render_ai_analysis_html_rich(ai_analysis)) if ai_analysis else Markup("")

    region_contents: dict[str, Any] = {
        "hotlist": stats_html,
        "rss": rss_stats_html,
        "new_items": (new_titles_html, rss_new_html),
        "standalone": standalone_html,
        "ai_analysis": ai_html,
    }
    section_labels = {
        "hotlist": "热榜",
        "rss": "RSS",
        "new_items": "新增",
        "standalone": "独立",
        "ai_analysis": "AI分析",
    }

    available_sections: list[str] = []
    for region in region_order:
        content = region_contents.get(region, "")
        if region == "new_items":
            new_html, rss_new = content
            if new_html or rss_new:
                available_sections.append(region)
        elif content:
            available_sections.append(region)

    section_tabs_html = _build_section_tabs_html(available_sections, section_labels)
    section_blocks = _assemble_section_blocks(region_order, region_contents)

    # —— 通过 Jinja2 渲染主壳 ——
    template = _get_env().get_template("report.html.j2")
    return template.render(
        css=Markup(REPORT_CSS),  # CSS 不需要 HTML 转义
        js=Markup(REPORT_JS),  # JS 不需要 HTML 转义
        display_mode=display_mode,
        mode_label=mode_label,
        total_titles=total_titles,
        hot_news_count=hot_news_count,
        time_str=time_str,
        failed_ids=[Markup(fid) for fid in failed_ids],  # 已经手动 escape 过
        section_tabs_html=section_tabs_html,
        section_blocks=section_blocks,
        update_info=update_info,
    )
