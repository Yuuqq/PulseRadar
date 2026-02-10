# coding=utf-8
"""
HTML 报告渲染模块

提供 HTML 格式的热点新闻报告生成功能
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Callable

from trendradar.report.helpers import html_escape
from trendradar.utils.time import convert_time_for_display
from trendradar.ai.formatter import render_ai_analysis_html_rich


def render_html_content(
    report_data: Dict,
    total_titles: int,
    mode: str = "daily",
    update_info: Optional[Dict] = None,
    *,
    region_order: Optional[List[str]] = None,
    get_time_func: Optional[Callable[[], datetime]] = None,
    rss_items: Optional[List[Dict]] = None,
    rss_new_items: Optional[List[Dict]] = None,
    display_mode: str = "keyword",
    standalone_data: Optional[Dict] = None,
    ai_analysis: Optional[Any] = None,
    show_new_section: bool = True,
    alternate_report_data: Optional[Dict] = None,
    alternate_display_mode: Optional[str] = None,
) -> str:
    """渲染HTML内容

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
    # 默认区域顺序
    default_region_order = ["hotlist", "rss", "new_items", "standalone", "ai_analysis"]
    if region_order is None:
        region_order = default_region_order

    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>热点新闻分析</title>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js" integrity="sha512-BNaRQnYJYiPSqHHDb58B0yaPfCu+Wgds8Gp/gU33kqBtgNS4tSPHuGibyoeqMV/TJlSKda6FXzoEyYGjTe+vXA==" crossorigin="anonymous" referrerpolicy="no-referrer"></script>
        <style>
            * { box-sizing: border-box; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
                margin: 0;
                padding: 16px;
                background: #f4f6fb;
                color: #111827;
                line-height: 1.65;
                font-size: 15px;
            }

            .container {
                max-width: 1060px;
                width: 96%;
                margin: 0 auto;
                background: white;
                border-radius: 16px;
                overflow: hidden;
                border: 1px solid #e5e7eb;
                box-shadow: 0 4px 6px rgba(15, 23, 42, 0.04), 0 16px 40px rgba(15, 23, 42, 0.08);
            }

            .header {
                background: linear-gradient(135deg, #1d4ed8 0%, #0f766e 100%);
                color: white;
                padding: 36px 28px;
                text-align: center;
                position: relative;
            }

            .save-buttons {
                position: absolute;
                top: 16px;
                right: 16px;
                display: flex;
                gap: 8px;
            }

            .save-btn {
                background: rgba(255, 255, 255, 0.2);
                border: 1px solid rgba(255, 255, 255, 0.3);
                color: white;
                padding: 8px 16px;
                border-radius: 6px;
                cursor: pointer;
                font-size: 13px;
                font-weight: 500;
                transition: all 0.2s ease;
                backdrop-filter: blur(10px);
                white-space: nowrap;
            }

            .save-btn:hover {
                background: rgba(255, 255, 255, 0.3);
                border-color: rgba(255, 255, 255, 0.5);
                transform: translateY(-1px);
            }

            .save-btn:active {
                transform: translateY(0);
            }

            .save-btn:disabled {
                opacity: 0.6;
                cursor: not-allowed;
            }

            .save-btn.theme-toggle {
                padding: 8px 10px;
                min-width: 36px;
            }

            .header-title {
                font-size: 26px;
                font-weight: 700;
                margin: 0 0 24px 0;
                letter-spacing: -0.3px;
            }

            .header-info {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 16px;
                font-size: 13px;
                opacity: 0.95;
            }

            .info-item {
                text-align: center;
            }

            .info-label {
                display: block;
                font-size: 12px;
                opacity: 0.8;
                margin-bottom: 4px;
            }

            .info-value {
                font-weight: 700;
                font-size: 18px;
            }

            .content {
                padding: 32px 36px;
            }

            .controls {
                display: flex;
                flex-wrap: wrap;
                gap: 12px;
                align-items: center;
                justify-content: space-between;
                margin: 4px 0 16px;
            }

            .controls-left,
            .controls-right {
                display: flex;
                flex-wrap: wrap;
                gap: 8px;
                align-items: center;
            }

            .view-toggle {
                display: flex;
                gap: 6px;
                background: #e2e8f0;
                padding: 4px;
                border-radius: 999px;
            }

            .view-btn {
                border: none;
                background: transparent;
                color: #1f2937;
                font-size: 12px;
                font-weight: 600;
                padding: 6px 12px;
                border-radius: 999px;
                cursor: pointer;
                transition: all 0.15s ease;
            }

            .view-btn.active {
                background: #111827;
                color: #ffffff;
            }

            .search-input {
                border: 1px solid #e2e8f0;
                border-radius: 999px;
                padding: 8px 14px;
                font-size: 13px;
                width: 240px;
                outline: none;
                background: #ffffff;
                color: #0f172a;
            }

            .search-input::placeholder {
                color: #94a3b8;
            }

            .section-tabs {
                position: sticky;
                top: 0;
                z-index: 6;
                background: linear-gradient(to bottom, #ffffff 85%, rgba(255, 255, 255, 0));
                margin: -8px -4px 24px;
                padding: 14px 4px 12px;
                display: flex;
                flex-wrap: wrap;
                gap: 8px;
                border-bottom: 2px solid #e2e8f0;
            }

            .section-tab {
                border: 1px solid #e2e8f0;
                background: #ffffff;
                color: #0f172a;
                border-radius: 999px;
                padding: 9px 18px;
                font-size: 13px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.15s ease;
                white-space: nowrap;
            }

            .section-tab:hover {
                transform: translateY(-1px);
                box-shadow: 0 6px 16px rgba(15, 23, 42, 0.12);
            }

            .section-tab.active {
                background: #111827;
                color: #ffffff;
                border-color: #111827;
            }

            .topic-tabs {
                position: sticky;
                top: 52px;
                z-index: 5;
                background: linear-gradient(to bottom, #ffffff 85%, rgba(255, 255, 255, 0));
                margin: -4px 0 24px;
                padding: 14px 0 12px;
                display: flex;
                flex-wrap: wrap;
                gap: 10px;
                overflow-x: auto;
                -webkit-overflow-scrolling: touch;
                border-bottom: 1px solid #e2e8f0;
            }

            .topic-tabs::after {
                content: "";
                flex: 0 0 8px;
            }

            .topic-tab {
                border: none;
                background: linear-gradient(135deg, #f3f4f6 0%, #e5e7eb 100%);
                color: #4b5563;
                border-radius: 12px;
                padding: 10px 18px;
                font-size: 13px;
                font-weight: 600;
                cursor: pointer;
                white-space: nowrap;
                transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
                display: inline-flex;
                align-items: center;
                gap: 8px;
            }

            .topic-tab:hover {
                background: linear-gradient(135deg, #e5e7eb 0%, #d1d5db 100%);
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            }

            .topic-tab .topic-count {
                background: rgba(0, 0, 0, 0.08);
                padding: 2px 8px;
                border-radius: 8px;
                font-size: 12px;
                font-weight: 700;
                color: #6b7280;
            }

            .topic-tab.active {
                background: linear-gradient(135deg, #2563eb 0%, #0f766e 100%);
                color: #ffffff;
                box-shadow: 0 4px 14px rgba(37, 99, 235, 0.35);
            }

            .topic-tab.active:hover {
                background: linear-gradient(135deg, #1d4ed8 0%, #0d9488 100%);
                box-shadow: 0 6px 20px rgba(15, 118, 110, 0.4);
            }

            .topic-tab.active .topic-count {
                background: rgba(255, 255, 255, 0.25);
                color: #ffffff;
            }

            .report-section[data-hidden="true"] {
                display: none;
            }

            .word-group[data-hidden="true"],
            .word-group[data-filtered="true"] {
                display: none;
            }

            .word-group {
                margin-bottom: 28px;
                background: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 14px;
                padding: 20px 22px 12px;
                box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04), 0 4px 12px rgba(15, 23, 42, 0.03);
                transition: box-shadow 0.2s ease;
            }

            .word-group:hover {
                box-shadow: 0 2px 6px rgba(15, 23, 42, 0.06), 0 8px 24px rgba(15, 23, 42, 0.06);
            }

            .word-group:first-child {
                margin-top: 0;
            }

            .word-header {
                display: flex;
                align-items: center;
                justify-content: space-between;
                margin-bottom: 16px;
                padding-bottom: 12px;
                border-bottom: 2px solid #f1f5f9;
            }

            .word-info {
                display: flex;
                align-items: center;
                gap: 12px;
            }

            .word-name {
                font-size: 18px;
                font-weight: 600;
                color: #0f172a;
            }

            .word-count {
                color: #1d4ed8;
                font-size: 12px;
                font-weight: 600;
                background: #dbeafe;
                padding: 2px 8px;
                border-radius: 999px;
            }

            .word-count.hot { color: #b91c1c; background: #fee2e2; }
            .word-count.warm { color: #c2410c; background: #ffedd5; }

            .word-index {
                color: #94a3b8;
                font-size: 12px;
            }

            .news-item {
                margin-bottom: 4px;
                padding: 14px 8px;
                border-bottom: 1px solid #f1f5f9;
                position: relative;
                display: flex;
                gap: 12px;
                align-items: center;
                border-radius: 8px;
                transition: background 0.15s ease;
            }

            .news-item:hover {
                background: #f8fafc;
            }

            .news-item:last-child {
                border-bottom: none;
                margin-bottom: 0;
            }

            .news-item.new::after {
                content: "NEW";
                position: absolute;
                top: 12px;
                right: 0;
                background: #fde047;
                color: #92400e;
                font-size: 9px;
                font-weight: 700;
                padding: 3px 6px;
                border-radius: 4px;
                letter-spacing: 0.5px;
            }

            .news-number {
                color: #475569;
                font-size: 12px;
                font-weight: 600;
                min-width: 20px;
                text-align: center;
                flex-shrink: 0;
                background: #e2e8f0;
                border-radius: 50%;
                width: 24px;
                height: 24px;
                display: flex;
                align-items: center;
                justify-content: center;
                align-self: flex-start;
                margin-top: 8px;
            }

            .news-content {
                flex: 1;
                min-width: 0;
                padding-right: 40px;
            }

            .news-item.new .news-content {
                padding-right: 50px;
            }

            .news-header {
                display: flex;
                align-items: center;
                gap: 6px;
                margin-bottom: 6px;
                flex-wrap: wrap;
            }

            .source-name {
                color: #64748b;
                font-size: 12px;
                font-weight: 500;
            }

            .keyword-tag {
                color: #0369a1;
                font-size: 12px;
                font-weight: 500;
                background: #e0f2fe;
                padding: 2px 6px;
                border-radius: 4px;
            }

            .rank-num {
                color: #fff;
                background: #94a3b8;
                font-size: 10px;
                font-weight: 700;
                padding: 2px 6px;
                border-radius: 10px;
                min-width: 18px;
                text-align: center;
            }

            .rank-num.top { background: #ef4444; }
            .rank-num.high { background: #f97316; }

            .time-info {
                color: #94a3b8;
                font-size: 11px;
            }

            .count-info {
                color: #059669;
                font-size: 11px;
                font-weight: 500;
            }

            .news-title {
                font-size: 16px;
                line-height: 1.55;
                color: #0f172a;
                margin: 0;
            }

            .news-link {
                color: #1d4ed8;
                text-decoration: none;
            }

            .news-link:hover {
                text-decoration: underline;
            }

            .news-link:visited {
                color: #0f766e;
            }

            /* 通用区域分割线样式 */
            .section-divider {
                margin-top: 36px;
                padding-top: 28px;
                border-top: 3px solid #e2e8f0;
            }

            /* 热榜统计区样式 */
            .hotlist-section {
                /* 默认无边框，由 section-divider 动态添加 */
            }

            .new-section {
                margin-top: 36px;
                padding-top: 28px;
            }

            .new-section-title {
                color: #0f172a;
                font-size: 18px;
                font-weight: 700;
                margin: 0 0 24px 0;
            }

            .new-source-group {
                margin-bottom: 28px;
                background: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 14px;
                padding: 20px 22px;
                box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04), 0 4px 12px rgba(15, 23, 42, 0.03);
            }

            .new-source-title {
                color: #475569;
                font-size: 14px;
                font-weight: 600;
                margin: 0 0 14px 0;
                padding-bottom: 10px;
                border-bottom: 2px solid #f1f5f9;
            }

            .new-item {
                display: flex;
                align-items: center;
                gap: 12px;
                padding: 12px 8px;
                border-bottom: 1px solid #f1f5f9;
                border-radius: 8px;
                transition: background 0.15s ease;
            }

            .new-item:hover {
                background: #f8fafc;
            }

            .new-item:last-child {
                border-bottom: none;
            }

            .new-item-number {
                color: #475569;
                font-size: 12px;
                font-weight: 600;
                min-width: 18px;
                text-align: center;
                flex-shrink: 0;
                background: #e2e8f0;
                border-radius: 50%;
                width: 20px;
                height: 20px;
                display: flex;
                align-items: center;
                justify-content: center;
            }

            .new-item-rank {
                color: #fff;
                background: #94a3b8;
                font-size: 10px;
                font-weight: 700;
                padding: 3px 6px;
                border-radius: 8px;
                min-width: 20px;
                text-align: center;
                flex-shrink: 0;
            }

            .new-item-rank.top { background: #ef4444; }
            .new-item-rank.high { background: #f97316; }

            .new-item-content {
                flex: 1;
                min-width: 0;
            }

            .new-item-title {
                font-size: 15px;
                line-height: 1.5;
                color: #0f172a;
                margin: 0;
            }

            .error-section {
                background: #fef2f2;
                border: 1px solid #fecaca;
                border-radius: 8px;
                padding: 16px;
                margin-bottom: 24px;
            }

            .error-title {
                color: #dc2626;
                font-size: 14px;
                font-weight: 600;
                margin: 0 0 8px 0;
            }

            .error-list {
                list-style: none;
                padding: 0;
                margin: 0;
            }

            .error-item {
                color: #991b1b;
                font-size: 13px;
                padding: 2px 0;
                font-family: 'SF Mono', Consolas, monospace;
            }

            .footer {
                margin-top: 40px;
                padding: 24px 32px;
                background: #f8fafc;
                border-top: 2px solid #e2e8f0;
                text-align: center;
            }

            .footer-content {
                font-size: 13px;
                color: #64748b;
                line-height: 1.6;
            }

            .footer-link {
                color: #2563eb;
                text-decoration: none;
                font-weight: 500;
                transition: color 0.2s ease;
            }

            .footer-link:hover {
                color: #0f766e;
                text-decoration: underline;
            }

            .project-name {
                font-weight: 600;
                color: #374151;
            }

            @media (max-width: 480px) {
                body { padding: 8px; }
                .header { padding: 28px 20px; }
                .content { padding: 20px 16px; }
                .footer { padding: 20px; }
                .header-info { grid-template-columns: 1fr; gap: 12px; }
                .controls { gap: 10px; }
                .controls-left, .controls-right { width: 100%; }
                .view-toggle { width: 100%; justify-content: center; }
                .search-input { width: 100%; }
                .topic-tab { font-size: 11px; padding: 6px 10px; }
                .news-header { gap: 6px; }
                .news-content { padding-right: 45px; }
                .news-item { gap: 8px; padding: 12px 4px; }
                .new-item { gap: 8px; padding: 10px 4px; }
                .news-number { width: 20px; height: 20px; font-size: 12px; }
                .word-group { padding: 16px 14px 8px; border-radius: 10px; }
                .feed-group { padding: 16px 14px; border-radius: 10px; }
                .new-source-group { padding: 16px 14px; border-radius: 10px; }
                .ai-section { padding: 20px 16px; }
                .ai-block { padding: 16px; }
                .save-buttons {
                    position: static;
                    margin-bottom: 16px;
                    display: flex;
                    gap: 8px;
                    justify-content: center;
                    flex-direction: column;
                    width: 100%;
                }
                .save-btn {
                    width: 100%;
                }
            }

            /* RSS 订阅内容样式 */
            .rss-section {
                margin-top: 36px;
                padding-top: 28px;
            }

            .rss-section-header {
                display: flex;
                align-items: center;
                justify-content: space-between;
                margin-bottom: 24px;
            }

            .rss-section-title {
                font-size: 20px;
                font-weight: 700;
                color: #0f766e;
            }

            .rss-section-count {
                color: #64748b;
                font-size: 14px;
                font-weight: 500;
            }

            .feed-group {
                margin-bottom: 28px;
                background: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 14px;
                padding: 20px 22px;
                box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04), 0 4px 12px rgba(15, 23, 42, 0.03);
            }

            .feed-group:last-child {
                margin-bottom: 0;
            }

            .feed-header {
                display: flex;
                align-items: center;
                justify-content: space-between;
                margin-bottom: 16px;
                padding-bottom: 12px;
                border-bottom: 2px solid #0d9488;
            }

            .feed-name {
                font-size: 16px;
                font-weight: 700;
                color: #0f766e;
            }

            .feed-count {
                color: #64748b;
                font-size: 13px;
                font-weight: 500;
            }

            .rss-item {
                margin-bottom: 12px;
                padding: 16px;
                background: #f0fdfa;
                border-radius: 10px;
                border: 1px solid #ccfbf1;
                border-left: 4px solid #0d9488;
                transition: transform 0.15s ease, box-shadow 0.15s ease;
            }

            .rss-item:hover {
                transform: translateY(-1px);
                box-shadow: 0 4px 12px rgba(15, 23, 42, 0.06);
            }

            .rss-item:last-child {
                margin-bottom: 0;
            }

            .rss-meta {
                display: flex;
                align-items: center;
                gap: 12px;
                margin-bottom: 6px;
                flex-wrap: wrap;
            }

            .rss-time {
                color: #64748b;
                font-size: 12px;
            }

            .rss-author {
                color: #0f766e;
                font-size: 12px;
                font-weight: 500;
            }

            .rss-title {
                font-size: 15px;
                line-height: 1.5;
                margin-bottom: 6px;
            }

            .rss-link {
                color: #0f172a;
                text-decoration: none;
                font-weight: 500;
            }

            .rss-link:hover {
                color: #0f766e;
                text-decoration: underline;
            }

            .rss-summary {
                font-size: 13px;
                color: #64748b;
                line-height: 1.5;
                margin: 0;
                display: -webkit-box;
                -webkit-line-clamp: 2;
                -webkit-box-orient: vertical;
                overflow: hidden;
            }

            /* 独立展示区样式 - 复用热点词汇统计区样式 */
            .standalone-section {
                margin-top: 32px;
                padding-top: 24px;
            }

            .standalone-section-header {
                display: flex;
                align-items: center;
                justify-content: space-between;
                margin-bottom: 20px;
            }

            .standalone-section-title {
                font-size: 18px;
                font-weight: 600;
                color: #1d4ed8;
            }

            .standalone-section-count {
                color: #64748b;
                font-size: 14px;
            }

            .standalone-group {
                margin-bottom: 40px;
            }

            .standalone-group:last-child {
                margin-bottom: 0;
            }

            .standalone-header {
                display: flex;
                align-items: center;
                justify-content: space-between;
                margin-bottom: 20px;
                padding-bottom: 8px;
                border-bottom: 1px solid #f0f0f0;
            }

            .standalone-name {
                font-size: 17px;
                font-weight: 600;
                color: #1a1a1a;
            }

            .standalone-count {
                color: #666;
                font-size: 13px;
                font-weight: 500;
            }

            /* AI 分析区块样式 */
            .ai-section {
                margin-top: 36px;
                padding: 28px;
                background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 50%, #f0f9ff 100%);
                border-radius: 16px;
                border: 1px solid #bae6fd;
            }

            .ai-section-header {
                display: flex;
                align-items: center;
                gap: 10px;
                margin-bottom: 24px;
            }

            .ai-section-title {
                font-size: 20px;
                font-weight: 700;
                color: #0369a1;
            }

            .ai-section-badge {
                background: linear-gradient(135deg, #0ea5e9, #0369a1);
                color: white;
                font-size: 11px;
                font-weight: 700;
                padding: 4px 10px;
                border-radius: 6px;
                letter-spacing: 0.5px;
            }

            .ai-block {
                margin-bottom: 16px;
                padding: 20px;
                background: white;
                border-radius: 12px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.05), 0 4px 12px rgba(3, 105, 161, 0.04);
            }

            .ai-block:last-child {
                margin-bottom: 0;
            }

            .ai-block-title {
                font-size: 14px;
                font-weight: 600;
                color: #0369a1;
                margin-bottom: 8px;
            }

            .ai-block-content {
                font-size: 14px;
                line-height: 1.6;
                color: #334155;
                white-space: pre-wrap;
            }

            .ai-error {
                padding: 16px;
                background: #fef2f2;
                border: 1px solid #fecaca;
                border-radius: 8px;
                color: #991b1b;
                font-size: 14px;
            }

            /* Dark mode */
            body[data-theme="dark"] {
                background: #0f172a;
                color: #e2e8f0;
            }

            body[data-theme="dark"] .container {
                background: #0b1220;
                border-color: #1f2937;
                box-shadow: 0 12px 30px rgba(0, 0, 0, 0.35);
            }

            body[data-theme="dark"] .header {
                background: linear-gradient(135deg, #1e293b 0%, #0f766e 100%);
            }

            body[data-theme="dark"] .save-btn {
                background: rgba(255, 255, 255, 0.12);
                border-color: rgba(255, 255, 255, 0.2);
            }

            body[data-theme="dark"] .save-btn:hover {
                background: rgba(255, 255, 255, 0.18);
            }

            body[data-theme="dark"] .controls {
                color: #e2e8f0;
            }

            body[data-theme="dark"] .view-toggle {
                background: #1f2937;
            }

            body[data-theme="dark"] .view-btn {
                color: #e2e8f0;
            }

            body[data-theme="dark"] .view-btn.active {
                background: #2563eb;
            }

            body[data-theme="dark"] .search-input {
                background: #0f172a;
                border-color: #334155;
                color: #e2e8f0;
            }

            body[data-theme="dark"] .section-tabs {
                background: linear-gradient(to bottom, #0b1220 85%, rgba(11, 18, 32, 0));
                border-bottom: 1px solid #1f2937;
            }

            body[data-theme="dark"] .section-tab {
                background: #0f172a;
                color: #e2e8f0;
                border-color: #1f2937;
                box-shadow: none;
            }

            body[data-theme="dark"] .section-tab:hover {
                box-shadow: none;
                background: #111827;
            }

            body[data-theme="dark"] .section-tab.active {
                background: #2563eb;
                border-color: #2563eb;
                color: #ffffff;
            }

            body[data-theme="dark"] .topic-tabs {
                background: linear-gradient(to bottom, #0b1220 85%, rgba(11, 18, 32, 0));
                border-bottom: 1px solid #1f2937;
            }

            body[data-section-tabs="true"] .topic-tabs {
                top: 52px;
            }

            body[data-theme="dark"] .topic-tab {
                background: #1f2937;
                color: #e2e8f0;
                box-shadow: none;
            }

            body[data-theme="dark"] .topic-tab:hover {
                background: #334155;
                box-shadow: none;
            }

            body[data-theme="dark"] .topic-tab.active {
                background: #2563eb;
                color: #ffffff;
                box-shadow: none;
            }

            body[data-theme="dark"] .topic-tab.active:hover {
                background: #1d4ed8;
            }

            body[data-theme="dark"] .topic-tab .topic-count {
                background: rgba(255, 255, 255, 0.12);
                color: #cbd5f5;
            }

            body[data-theme="dark"] .word-group {
                background: #0f172a;
                border-color: #1f2937;
            }

            body[data-theme="dark"] .word-header {
                border-bottom-color: #1f2937;
            }

            body[data-theme="dark"] .word-name {
                color: #e2e8f0;
            }

            body[data-theme="dark"] .word-count {
                background: #1e293b;
                color: #93c5fd;
            }

            body[data-theme="dark"] .word-count.hot {
                background: #3f1d1d;
                color: #fca5a5;
            }

            body[data-theme="dark"] .word-count.warm {
                background: #3b2616;
                color: #fdba74;
            }

            body[data-theme="dark"] .news-item {
                border-bottom-color: #1f2937;
            }

            body[data-theme="dark"] .news-number {
                background: #1f2937;
                color: #94a3b8;
            }

            body[data-theme="dark"] .source-name,
            body[data-theme="dark"] .time-info {
                color: #94a3b8;
            }

            body[data-theme="dark"] .keyword-tag {
                background: #1e3a8a;
                color: #bfdbfe;
            }

            body[data-theme="dark"] .news-title,
            body[data-theme="dark"] .new-item-title,
            body[data-theme="dark"] .rss-link {
                color: #e2e8f0;
            }

            body[data-theme="dark"] .news-link {
                color: #60a5fa;
            }

            body[data-theme="dark"] .news-link:visited {
                color: #a78bfa;
            }

            body[data-theme="dark"] .new-source-title,
            body[data-theme="dark"] .new-section-title {
                color: #e2e8f0;
            }

            body[data-theme="dark"] .new-item {
                border-bottom-color: #1f2937;
            }

            body[data-theme="dark"] .new-item-number,
            body[data-theme="dark"] .new-item-rank,
            body[data-theme="dark"] .rank-num {
                background: #1f2937;
            }

            body[data-theme="dark"] .rss-item {
                background: #0f172a;
                border-color: #134e4a;
            }

            body[data-theme="dark"] .rss-summary,
            body[data-theme="dark"] .rss-time,
            body[data-theme="dark"] .rss-section-count {
                color: #94a3b8;
            }

            body[data-theme="dark"] .rss-section-title,
            body[data-theme="dark"] .feed-name,
            body[data-theme="dark"] .rss-link:hover {
                color: #5eead4;
            }

            body[data-theme="dark"] .feed-header {
                border-bottom-color: #0f766e;
            }

            body[data-theme="dark"] .ai-section {
                background: linear-gradient(135deg, #0b1220 0%, #111827 100%);
                border-color: #1e3a8a;
            }

            body[data-theme="dark"] .ai-section-title,
            body[data-theme="dark"] .ai-block-title {
                color: #7dd3fc;
            }

            body[data-theme="dark"] .ai-block {
                background: #0f172a;
                box-shadow: none;
                border: 1px solid #1f2937;
            }

            body[data-theme="dark"] .ai-block-content {
                color: #e2e8f0;
            }

            body[data-theme="dark"] .footer {
                background: #0f172a;
                border-top-color: #1f2937;
            }

            body[data-theme="dark"] .footer-content {
                color: #94a3b8;
            }

            body[data-theme="dark"] .error-section,
            body[data-theme="dark"] .ai-error {
                background: #3f1d1d;
                border-color: #7f1d1d;
                color: #fecaca;
            }
        </style>
    </head>
    <body data-default-view=""" + display_mode + """>
        <div class="container">
            <div class="header">
                <div class="save-buttons">
                    <button class="save-btn" onclick="saveAsImage()">保存为图片</button>
                    <button class="save-btn" onclick="saveAsMultipleImages()">分段保存</button>
                    <button class="save-btn theme-toggle" id="theme-toggle" onclick="toggleTheme()" aria-label="切换主题">🌙</button>
                </div>
                <div class="header-title">热点新闻分析</div>
                <div class="header-info">
                    <div class="info-item">
                        <span class="info-label">报告类型</span>
                        <span class="info-value">"""

    # 处理报告类型显示（根据 mode 直接显示）
    if mode == "current":
        html += "当前榜单"
    elif mode == "incremental":
        html += "增量分析"
    else:
        html += "全天汇总"

    html += """</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">新闻总数</span>
                        <span class="info-value">"""

    html += f"{total_titles} 条"

    # 计算筛选后的热点新闻数量
    hot_news_count = sum(len(stat["titles"]) for stat in report_data["stats"])

    html += """</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">热点新闻</span>
                        <span class="info-value">"""

    html += f"{hot_news_count} 条"

    html += """</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">生成时间</span>
                        <span class="info-value">"""

    # 使用提供的时间函数或默认 datetime.now
    if get_time_func:
        now = get_time_func()
    else:
        now = datetime.now()
    html += now.strftime("%m-%d %H:%M")

    html += """</span>
                    </div>
                </div>
            </div>

            <div class="content">"""

    # 处理失败ID错误信息
    if report_data["failed_ids"]:
        html += """
                <div class="error-section">
                    <div class="error-title">⚠️ 请求失败的平台</div>
                    <ul class="error-list">"""
        for id_value in report_data["failed_ids"]:
            html += f'<li class="error-item">{html_escape(id_value)}</li>'
        html += """
                    </ul>
                </div>"""

    def build_hotlist_view(stats: List[Dict], view_mode: str) -> str:
        """构建热榜视图（关键词/平台）"""
        if not stats:
            return ""

        total_count = len(stats)
        view_news_count = sum(len(stat["titles"]) for stat in stats)
        tabs = []
        stats_html = ""

        for i, stat in enumerate(stats, 1):
            count = stat["count"]

            # 确定热度等级
            if count >= 10:
                count_class = "hot"
            elif count >= 5:
                count_class = "warm"
            else:
                count_class = ""

            escaped_word = html_escape(stat["word"])
            tabs.append({"word": escaped_word, "count": count})

            stats_html += f"""
                <div class="word-group" data-topic="{escaped_word}">
                    <div class="word-header">
                        <div class="word-info">
                            <div class="word-name">{escaped_word}</div>
                            <div class="word-count {count_class}">{count} 条</div>
                        </div>
                        <div class="word-index">{i}/{total_count}</div>
                    </div>"""

            # 处理每个词组下的新闻标题，给每条新闻标上序号
            for j, title_data in enumerate(stat["titles"], 1):
                is_new = title_data.get("is_new", False)
                new_class = "new" if is_new else ""
                source_name = html_escape(title_data.get("source_name", ""))
                matched_keyword = title_data.get("matched_keyword", "")
                keyword_label = html_escape(matched_keyword) if matched_keyword else escaped_word

                search_blob = f"{title_data.get('title', '')} {title_data.get('source_name', '')} {matched_keyword} {stat['word']}"
                search_attr = html_escape(search_blob.lower())

                stats_html += f"""
                    <div class="news-item {new_class}" data-search="{search_attr}">
                        <div class="news-number">{j}</div>
                        <div class="news-content">
                            <div class="news-header">"""

                if view_mode == "keyword":
                    stats_html += f'<span class="source-name">{source_name}</span>'
                else:
                    if matched_keyword:
                        stats_html += f'<span class="keyword-tag">[{html_escape(matched_keyword)}]</span>'
                    else:
                        stats_html += f'<span class="keyword-tag">[{escaped_word}]</span>'

                # 处理排名显示
                ranks = title_data.get("ranks", [])
                if ranks:
                    min_rank = min(ranks)
                    max_rank = max(ranks)
                    rank_threshold = title_data.get("rank_threshold", 10)

                    # 确定排名等级
                    if min_rank <= 3:
                        rank_class = "top"
                    elif min_rank <= rank_threshold:
                        rank_class = "high"
                    else:
                        rank_class = ""

                    if min_rank == max_rank:
                        rank_text = str(min_rank)
                    else:
                        rank_text = f"{min_rank}-{max_rank}"

                    stats_html += f'<span class="rank-num {rank_class}">{rank_text}</span>'

                # 处理时间显示
                time_display = title_data.get("time_display", "")
                if time_display:
                    simplified_time = (
                        time_display.replace(" ~ ", "~")
                        .replace("[", "")
                        .replace("]", "")
                    )
                    stats_html += f'<span class="time-info">{html_escape(simplified_time)}</span>'

                # 处理出现次数
                count_info = title_data.get("count", 1)
                if count_info > 1:
                    stats_html += f'<span class="count-info">{count_info}次</span>'

                stats_html += """
                            </div>
                            <div class="news-title">"""

                # 处理标题和链接
                escaped_title = html_escape(title_data["title"])
                link_url = title_data.get("mobile_url") or title_data.get("url", "")

                if link_url:
                    escaped_url = html_escape(link_url)
                    stats_html += f'<a href="{escaped_url}" target="_blank" class="news-link">{escaped_title}</a>'
                else:
                    stats_html += escaped_title

                stats_html += """
                            </div>
                        </div>
                    </div>"""

            stats_html += """
                </div>"""

        tabs_html = ""
        if len(tabs) > 1:
            tabs_html = f"""
                <div class="topic-tabs" role="tablist" aria-label="主题切换">
                    <button class="topic-tab active" data-topic="all">
                        全部 <span class="topic-count">{view_news_count}</span>
                    </button>"""
            for tab in tabs:
                tabs_html += f"""
                    <button class="topic-tab" data-topic="{tab['word']}">
                        {tab['word']} <span class="topic-count">{tab['count']}</span>
                    </button>"""
            tabs_html += """
                </div>"""

        return f"""
                <div class="hotlist-view" data-view="{view_mode}">
                    {tabs_html}{stats_html}
                </div>"""

    # 生成热点词汇统计部分的HTML（支持关键词/平台切换）
    stats_html = ""
    if report_data["stats"]:
        view_options = [display_mode]
        if alternate_report_data and alternate_display_mode and alternate_display_mode not in view_options:
            view_options.append(alternate_display_mode)

        view_toggle_html = ""
        if len(view_options) > 1:
            labels = {"keyword": "关键词", "platform": "平台"}
            view_order = [v for v in ["keyword", "platform"] if v in view_options]
            view_toggle_html = '<div class="view-toggle" role="tablist">'
            for view in view_order:
                view_toggle_html += f'<button class="view-btn" data-view="{view}">{labels.get(view, view)}</button>'
            view_toggle_html += "</div>"

        controls_html = f"""
                <div class="controls">
                    <div class="controls-left">
                        {view_toggle_html}
                    </div>
                    <div class="controls-right">
                        <input id="search-input" class="search-input" type="search" placeholder="搜索标题/来源/关键词">
                    </div>
                </div>"""

        main_view_html = build_hotlist_view(report_data["stats"], display_mode)
        alternate_view_html = ""
        if alternate_report_data and alternate_display_mode:
            alternate_view_html = build_hotlist_view(alternate_report_data.get("stats", []), alternate_display_mode)

        stats_html = f"""
                <div class="hotlist-section">
                    {controls_html}
                    {main_view_html}
                    {alternate_view_html}
                    <div id="search-empty" style="display:none; color:#94a3b8; font-size:13px; margin-top:8px;">无匹配结果</div>
                </div>"""

    # 生成新增新闻区域的HTML
    new_titles_html = ""
    if show_new_section and report_data["new_titles"]:
        new_titles_html += f"""
                <div class="new-section">
                    <div class="new-section-title">本次新增热点 (共 {report_data['total_new_count']} 条)</div>"""

        for source_data in report_data["new_titles"]:
            escaped_source = html_escape(source_data["source_name"])
            titles_count = len(source_data["titles"])

            new_titles_html += f"""
                    <div class="new-source-group">
                        <div class="new-source-title">{escaped_source} · {titles_count}条</div>"""

            # 为新增新闻也添加序号
            for idx, title_data in enumerate(source_data["titles"], 1):
                ranks = title_data.get("ranks", [])

                # 处理新增新闻的排名显示
                rank_class = ""
                if ranks:
                    min_rank = min(ranks)
                    if min_rank <= 3:
                        rank_class = "top"
                    elif min_rank <= title_data.get("rank_threshold", 10):
                        rank_class = "high"

                    if len(ranks) == 1:
                        rank_text = str(ranks[0])
                    else:
                        rank_text = f"{min(ranks)}-{max(ranks)}"
                else:
                    rank_text = "?"

                new_titles_html += f"""
                        <div class="new-item">
                            <div class="new-item-number">{idx}</div>
                            <div class="new-item-rank {rank_class}">{rank_text}</div>
                            <div class="new-item-content">
                                <div class="new-item-title">"""

                # 处理新增新闻的链接
                escaped_title = html_escape(title_data["title"])
                link_url = title_data.get("mobile_url") or title_data.get("url", "")

                if link_url:
                    escaped_url = html_escape(link_url)
                    new_titles_html += f'<a href="{escaped_url}" target="_blank" class="news-link">{escaped_title}</a>'
                else:
                    new_titles_html += escaped_title

                new_titles_html += """
                                </div>
                            </div>
                        </div>"""

            new_titles_html += """
                    </div>"""

        new_titles_html += """
                </div>"""

    # 生成 RSS 统计内容
    def render_rss_stats_html(stats: List[Dict], title: str = "RSS 订阅更新") -> str:
        """渲染 RSS 统计区块 HTML

        Args:
            stats: RSS 分组统计列表，格式与热榜一致：
                [
                    {
                        "word": "关键词",
                        "count": 5,
                        "titles": [
                            {
                                "title": "标题",
                                "source_name": "Feed 名称",
                                "time_display": "12-29 08:20",
                                "url": "...",
                                "is_new": True/False
                            }
                        ]
                    }
                ]
            title: 区块标题

        Returns:
            渲染后的 HTML 字符串
        """
        if not stats:
            return ""

        # 计算总条目数
        total_count = sum(stat.get("count", 0) for stat in stats)
        if total_count == 0:
            return ""

        rss_html = f"""
                <div class="rss-section">
                    <div class="rss-section-header">
                        <div class="rss-section-title">{title}</div>
                        <div class="rss-section-count">{total_count} 条</div>
                    </div>"""

        # 按关键词分组渲染（与热榜格式一致）
        for stat in stats:
            keyword = stat.get("word", "")
            titles = stat.get("titles", [])
            if not titles:
                continue

            keyword_count = len(titles)

            rss_html += f"""
                    <div class="feed-group">
                        <div class="feed-header">
                            <div class="feed-name">{html_escape(keyword)}</div>
                            <div class="feed-count">{keyword_count} 条</div>
                        </div>"""

            for title_data in titles:
                item_title = title_data.get("title", "")
                url = title_data.get("url", "")
                time_display = title_data.get("time_display", "")
                source_name = title_data.get("source_name", "")
                is_new = title_data.get("is_new", False)

                rss_html += """
                        <div class="rss-item">
                            <div class="rss-meta">"""

                if time_display:
                    rss_html += f'<span class="rss-time">{html_escape(time_display)}</span>'

                if source_name:
                    rss_html += f'<span class="rss-author">{html_escape(source_name)}</span>'

                if is_new:
                    rss_html += '<span class="rss-author" style="color: #dc2626;">NEW</span>'

                rss_html += """
                            </div>
                            <div class="rss-title">"""

                escaped_title = html_escape(item_title)
                if url:
                    escaped_url = html_escape(url)
                    rss_html += f'<a href="{escaped_url}" target="_blank" class="rss-link">{escaped_title}</a>'
                else:
                    rss_html += escaped_title

                rss_html += """
                            </div>
                        </div>"""

            rss_html += """
                    </div>"""

        rss_html += """
                </div>"""
        return rss_html

    # 生成独立展示区内容
    def render_standalone_html(data: Optional[Dict]) -> str:
        """渲染独立展示区 HTML（复用热点词汇统计区样式）

        Args:
            data: 独立展示数据，格式：
                {
                    "platforms": [
                        {
                            "id": "zhihu",
                            "name": "知乎热榜",
                            "items": [
                                {
                                    "title": "标题",
                                    "url": "链接",
                                    "rank": 1,
                                    "ranks": [1, 2, 1],
                                    "first_time": "08:00",
                                    "last_time": "12:30",
                                    "count": 3,
                                }
                            ]
                        }
                    ],
                    "rss_feeds": [
                        {
                            "id": "hacker-news",
                            "name": "Hacker News",
                            "items": [
                                {
                                    "title": "标题",
                                    "url": "链接",
                                    "published_at": "2025-01-07T08:00:00",
                                    "author": "作者",
                                }
                            ]
                        }
                    ]
                }

        Returns:
            渲染后的 HTML 字符串
        """
        if not data:
            return ""

        platforms = data.get("platforms", [])
        rss_feeds = data.get("rss_feeds", [])

        if not platforms and not rss_feeds:
            return ""

        # 计算总条目数
        total_platform_items = sum(len(p.get("items", [])) for p in platforms)
        total_rss_items = sum(len(f.get("items", [])) for f in rss_feeds)
        total_count = total_platform_items + total_rss_items

        if total_count == 0:
            return ""

        standalone_html = f"""
                <div class="standalone-section">
                    <div class="standalone-section-header">
                        <div class="standalone-section-title">独立展示区</div>
                        <div class="standalone-section-count">{total_count} 条</div>
                    </div>"""

        # 渲染热榜平台（复用 word-group 结构）
        for platform in platforms:
            platform_name = platform.get("name", platform.get("id", ""))
            items = platform.get("items", [])
            if not items:
                continue

            standalone_html += f"""
                    <div class="standalone-group">
                        <div class="standalone-header">
                            <div class="standalone-name">{html_escape(platform_name)}</div>
                            <div class="standalone-count">{len(items)} 条</div>
                        </div>"""

            # 渲染每个条目（复用 news-item 结构）
            for j, item in enumerate(items, 1):
                title = item.get("title", "")
                url = item.get("url", "") or item.get("mobileUrl", "")
                rank = item.get("rank", 0)
                ranks = item.get("ranks", [])
                first_time = item.get("first_time", "")
                last_time = item.get("last_time", "")
                count = item.get("count", 1)

                standalone_html += f"""
                        <div class="news-item">
                            <div class="news-number">{j}</div>
                            <div class="news-content">
                                <div class="news-header">"""

                # 排名显示（复用 rank-num 样式，无 # 前缀）
                if ranks:
                    min_rank = min(ranks)
                    max_rank = max(ranks)

                    # 确定排名等级
                    if min_rank <= 3:
                        rank_class = "top"
                    elif min_rank <= 10:
                        rank_class = "high"
                    else:
                        rank_class = ""

                    if min_rank == max_rank:
                        rank_text = str(min_rank)
                    else:
                        rank_text = f"{min_rank}-{max_rank}"

                    standalone_html += f'<span class="rank-num {rank_class}">{rank_text}</span>'
                elif rank > 0:
                    if rank <= 3:
                        rank_class = "top"
                    elif rank <= 10:
                        rank_class = "high"
                    else:
                        rank_class = ""
                    standalone_html += f'<span class="rank-num {rank_class}">{rank}</span>'

                # 时间显示（复用 time-info 样式，将 HH-MM 转换为 HH:MM）
                if first_time and last_time and first_time != last_time:
                    first_time_display = convert_time_for_display(first_time)
                    last_time_display = convert_time_for_display(last_time)
                    standalone_html += f'<span class="time-info">{html_escape(first_time_display)}~{html_escape(last_time_display)}</span>'
                elif first_time:
                    first_time_display = convert_time_for_display(first_time)
                    standalone_html += f'<span class="time-info">{html_escape(first_time_display)}</span>'

                # 出现次数（复用 count-info 样式）
                if count > 1:
                    standalone_html += f'<span class="count-info">{count}次</span>'

                standalone_html += """
                                </div>
                                <div class="news-title">"""

                # 标题和链接（复用 news-link 样式）
                escaped_title = html_escape(title)
                if url:
                    escaped_url = html_escape(url)
                    standalone_html += f'<a href="{escaped_url}" target="_blank" class="news-link">{escaped_title}</a>'
                else:
                    standalone_html += escaped_title

                standalone_html += """
                                </div>
                            </div>
                        </div>"""

            standalone_html += """
                    </div>"""

        # 渲染 RSS 源（复用相同结构）
        for feed in rss_feeds:
            feed_name = feed.get("name", feed.get("id", ""))
            items = feed.get("items", [])
            if not items:
                continue

            standalone_html += f"""
                    <div class="standalone-group">
                        <div class="standalone-header">
                            <div class="standalone-name">{html_escape(feed_name)}</div>
                            <div class="standalone-count">{len(items)} 条</div>
                        </div>"""

            for j, item in enumerate(items, 1):
                title = item.get("title", "")
                url = item.get("url", "")
                published_at = item.get("published_at", "")
                author = item.get("author", "")

                standalone_html += f"""
                        <div class="news-item">
                            <div class="news-number">{j}</div>
                            <div class="news-content">
                                <div class="news-header">"""

                # 时间显示（格式化 ISO 时间）
                if published_at:
                    try:
                        from datetime import datetime as dt
                        if "T" in published_at:
                            dt_obj = dt.fromisoformat(published_at.replace("Z", "+00:00"))
                            time_display = dt_obj.strftime("%m-%d %H:%M")
                        else:
                            time_display = published_at
                    except:
                        time_display = published_at

                    standalone_html += f'<span class="time-info">{html_escape(time_display)}</span>'

                # 作者显示
                if author:
                    standalone_html += f'<span class="source-name">{html_escape(author)}</span>'

                standalone_html += """
                                </div>
                                <div class="news-title">"""

                escaped_title = html_escape(title)
                if url:
                    escaped_url = html_escape(url)
                    standalone_html += f'<a href="{escaped_url}" target="_blank" class="news-link">{escaped_title}</a>'
                else:
                    standalone_html += escaped_title

                standalone_html += """
                                </div>
                            </div>
                        </div>"""

            standalone_html += """
                    </div>"""

        standalone_html += """
                </div>"""
        return standalone_html

    # 生成 RSS 统计和新增 HTML
    rss_stats_html = render_rss_stats_html(rss_items, "RSS 订阅更新") if rss_items else ""
    rss_new_html = render_rss_stats_html(rss_new_items, "RSS 新增更新") if rss_new_items else ""

    # 生成独立展示区 HTML
    standalone_html = render_standalone_html(standalone_data)

    # 生成 AI 分析 HTML
    ai_html = render_ai_analysis_html_rich(ai_analysis) if ai_analysis else ""

    # 准备各区域内容映射
    region_contents = {
        "hotlist": stats_html,
        "rss": rss_stats_html,
        "new_items": (new_titles_html, rss_new_html),  # 元组，分别处理
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

    available_sections = []
    for region in region_order:
        content = region_contents.get(region, "")
        if region == "new_items":
            new_html, rss_new = content
            if new_html or rss_new:
                available_sections.append(region)
        elif content:
            available_sections.append(region)

    if len(available_sections) > 1:
        section_tabs_html = """
                <div class="section-tabs" role="tablist" aria-label="区域切换">
                    <button class="section-tab active" data-section="all">全部</button>"""
        for region in available_sections:
            label = section_labels.get(region, region)
            section_tabs_html += f"""
                    <button class="section-tab" data-section="{region}">{label}</button>"""
        section_tabs_html += """
                </div>"""
        html += section_tabs_html

    def add_section_divider(content: str) -> str:
        """为内容的外层 div 添加 section-divider 类"""
        if not content or 'class="' not in content:
            return content
        first_class_pos = content.find('class="')
        if first_class_pos != -1:
            insert_pos = first_class_pos + len('class="')
            return content[:insert_pos] + "section-divider " + content[insert_pos:]
        return content

    def wrap_section(region: str, content: str) -> str:
        return f'<section class="report-section" data-section="{region}">{content}</section>'

    # 按 region_order 顺序组装内容，动态添加分割线
    has_previous_content = False
    for region in region_order:
        content = region_contents.get(region, "")
        if region == "new_items":
            # 特殊处理 new_items 区域（包含热榜新增和 RSS 新增两部分）
            new_html, rss_new = content
            section_content = ""
            if new_html:
                if has_previous_content:
                    new_html = add_section_divider(new_html)
                section_content += new_html
            if rss_new:
                if section_content:
                    rss_new = add_section_divider(rss_new)
                elif has_previous_content:
                    rss_new = add_section_divider(rss_new)
                section_content += rss_new
            if section_content:
                html += wrap_section(region, section_content)
                has_previous_content = True
        elif content:
            if has_previous_content:
                content = add_section_divider(content)
            html += wrap_section(region, content)
            has_previous_content = True

    html += """
            </div>

            <div class="footer">
                <div class="footer-content">
                    由 <span class="project-name">TrendRadar</span> 生成 ·
                    <a href="https://github.com/sansan0/TrendRadar" target="_blank" class="footer-link">
                        GitHub 开源项目
                    </a>"""

    if update_info:
        html += f"""
                    <br>
                    <span style="color: #ea580c; font-weight: 500;">
                        发现新版本 {update_info['remote_version']}，当前版本 {update_info['current_version']}
                    </span>"""

    html += """
                </div>
            </div>
        </div>

        <script>
            async function saveAsImage() {
                const button = event.target;
                const originalText = button.textContent;
                const isDark = document.body.dataset.theme === 'dark';
                const backgroundColor = isDark ? '#0b1220' : '#ffffff';

                try {
                    button.textContent = '生成中...';
                    button.disabled = true;
                    window.scrollTo(0, 0);

                    // 等待页面稳定
                    await new Promise(resolve => setTimeout(resolve, 200));

                    // 截图前隐藏按钮
                    const buttons = document.querySelector('.save-buttons');
                    buttons.style.visibility = 'hidden';

                    // 再次等待确保按钮完全隐藏
                    await new Promise(resolve => setTimeout(resolve, 100));

                    const container = document.querySelector('.container');

                    const canvas = await html2canvas(container, {
                        backgroundColor: backgroundColor,
                        scale: 1.5,
                        useCORS: true,
                        allowTaint: false,
                        imageTimeout: 10000,
                        removeContainer: false,
                        foreignObjectRendering: false,
                        logging: false,
                        width: container.offsetWidth,
                        height: container.offsetHeight,
                        x: 0,
                        y: 0,
                        scrollX: 0,
                        scrollY: 0,
                        windowWidth: window.innerWidth,
                        windowHeight: window.innerHeight
                    });

                    buttons.style.visibility = 'visible';

                    const link = document.createElement('a');
                    const now = new Date();
                    const filename = `TrendRadar_热点新闻分析_${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}_${String(now.getHours()).padStart(2, '0')}${String(now.getMinutes()).padStart(2, '0')}.png`;

                    link.download = filename;
                    link.href = canvas.toDataURL('image/png', 1.0);

                    // 触发下载
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);

                    button.textContent = '保存成功!';
                    setTimeout(() => {
                        button.textContent = originalText;
                        button.disabled = false;
                    }, 2000);

                } catch (error) {
                    const buttons = document.querySelector('.save-buttons');
                    buttons.style.visibility = 'visible';
                    button.textContent = '保存失败';
                    setTimeout(() => {
                        button.textContent = originalText;
                        button.disabled = false;
                    }, 2000);
                }
            }

            async function saveAsMultipleImages() {
                const button = event.target;
                const originalText = button.textContent;
                const container = document.querySelector('.container');
                const scale = 1.5;
                const maxHeight = 5000 / scale;
                const isDark = document.body.dataset.theme === 'dark';
                const backgroundColor = isDark ? '#0b1220' : '#ffffff';

                try {
                    button.textContent = '分析中...';
                    button.disabled = true;

                    // 获取所有可能的分割元素
                    const newsItems = Array.from(container.querySelectorAll('.news-item'));
                    const wordGroups = Array.from(container.querySelectorAll('.word-group'));
                    const newSection = container.querySelector('.new-section');
                    const errorSection = container.querySelector('.error-section');
                    const header = container.querySelector('.header');
                    const footer = container.querySelector('.footer');

                    // 计算元素位置和高度
                    const containerRect = container.getBoundingClientRect();
                    const elements = [];

                    // 添加header作为必须包含的元素
                    elements.push({
                        type: 'header',
                        element: header,
                        top: 0,
                        bottom: header.offsetHeight,
                        height: header.offsetHeight
                    });

                    // 添加错误信息（如果存在）
                    if (errorSection) {
                        const rect = errorSection.getBoundingClientRect();
                        elements.push({
                            type: 'error',
                            element: errorSection,
                            top: rect.top - containerRect.top,
                            bottom: rect.bottom - containerRect.top,
                            height: rect.height
                        });
                    }

                    // 按word-group分组处理news-item
                    wordGroups.forEach(group => {
                        const groupRect = group.getBoundingClientRect();
                        const groupNewsItems = group.querySelectorAll('.news-item');

                        // 添加word-group的header部分
                        const wordHeader = group.querySelector('.word-header');
                        if (wordHeader) {
                            const headerRect = wordHeader.getBoundingClientRect();
                            elements.push({
                                type: 'word-header',
                                element: wordHeader,
                                parent: group,
                                top: groupRect.top - containerRect.top,
                                bottom: headerRect.bottom - containerRect.top,
                                height: headerRect.height
                            });
                        }

                        // 添加每个news-item
                        groupNewsItems.forEach(item => {
                            const rect = item.getBoundingClientRect();
                            elements.push({
                                type: 'news-item',
                                element: item,
                                parent: group,
                                top: rect.top - containerRect.top,
                                bottom: rect.bottom - containerRect.top,
                                height: rect.height
                            });
                        });
                    });

                    // 添加新增新闻部分
                    if (newSection) {
                        const rect = newSection.getBoundingClientRect();
                        elements.push({
                            type: 'new-section',
                            element: newSection,
                            top: rect.top - containerRect.top,
                            bottom: rect.bottom - containerRect.top,
                            height: rect.height
                        });
                    }

                    // 添加footer
                    const footerRect = footer.getBoundingClientRect();
                    elements.push({
                        type: 'footer',
                        element: footer,
                        top: footerRect.top - containerRect.top,
                        bottom: footerRect.bottom - containerRect.top,
                        height: footer.offsetHeight
                    });

                    // 计算分割点
                    const segments = [];
                    let currentSegment = { start: 0, end: 0, height: 0, includeHeader: true };
                    let headerHeight = header.offsetHeight;
                    currentSegment.height = headerHeight;

                    for (let i = 1; i < elements.length; i++) {
                        const element = elements[i];
                        const potentialHeight = element.bottom - currentSegment.start;

                        // 检查是否需要创建新分段
                        if (potentialHeight > maxHeight && currentSegment.height > headerHeight) {
                            // 在前一个元素结束处分割
                            currentSegment.end = elements[i - 1].bottom;
                            segments.push(currentSegment);

                            // 开始新分段
                            currentSegment = {
                                start: currentSegment.end,
                                end: 0,
                                height: element.bottom - currentSegment.end,
                                includeHeader: false
                            };
                        } else {
                            currentSegment.height = potentialHeight;
                            currentSegment.end = element.bottom;
                        }
                    }

                    // 添加最后一个分段
                    if (currentSegment.height > 0) {
                        currentSegment.end = container.offsetHeight;
                        segments.push(currentSegment);
                    }

                    button.textContent = `生成中 (0/${segments.length})...`;

                    // 隐藏保存按钮
                    const buttons = document.querySelector('.save-buttons');
                    buttons.style.visibility = 'hidden';

                    // 为每个分段生成图片
                    const images = [];
                    for (let i = 0; i < segments.length; i++) {
                        const segment = segments[i];
                        button.textContent = `生成中 (${i + 1}/${segments.length})...`;

                        // 创建临时容器用于截图
                        const tempContainer = document.createElement('div');
                        tempContainer.style.cssText = `
                            position: absolute;
                            left: -9999px;
                            top: 0;
                            width: ${container.offsetWidth}px;
                            background: ${backgroundColor};
                        `;
                        tempContainer.className = 'container';

                        // 克隆容器内容
                        const clonedContainer = container.cloneNode(true);

                        // 移除克隆内容中的保存按钮
                        const clonedButtons = clonedContainer.querySelector('.save-buttons');
                        if (clonedButtons) {
                            clonedButtons.style.display = 'none';
                        }

                        tempContainer.appendChild(clonedContainer);
                        document.body.appendChild(tempContainer);

                        // 等待DOM更新
                        await new Promise(resolve => setTimeout(resolve, 100));

                        // 使用html2canvas截取特定区域
                        const canvas = await html2canvas(clonedContainer, {
                            backgroundColor: backgroundColor,
                            scale: scale,
                            useCORS: true,
                            allowTaint: false,
                            imageTimeout: 10000,
                            logging: false,
                            width: container.offsetWidth,
                            height: segment.end - segment.start,
                            x: 0,
                            y: segment.start,
                            windowWidth: window.innerWidth,
                            windowHeight: window.innerHeight
                        });

                        images.push(canvas.toDataURL('image/png', 1.0));

                        // 清理临时容器
                        document.body.removeChild(tempContainer);
                    }

                    // 恢复按钮显示
                    buttons.style.visibility = 'visible';

                    // 下载所有图片
                    const now = new Date();
                    const baseFilename = `TrendRadar_热点新闻分析_${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}_${String(now.getHours()).padStart(2, '0')}${String(now.getMinutes()).padStart(2, '0')}`;

                    for (let i = 0; i < images.length; i++) {
                        const link = document.createElement('a');
                        link.download = `${baseFilename}_part${i + 1}.png`;
                        link.href = images[i];
                        document.body.appendChild(link);
                        link.click();
                        document.body.removeChild(link);

                        // 延迟一下避免浏览器阻止多个下载
                        await new Promise(resolve => setTimeout(resolve, 100));
                    }

                    button.textContent = `已保存 ${segments.length} 张图片!`;
                    setTimeout(() => {
                        button.textContent = originalText;
                        button.disabled = false;
                    }, 2000);

                } catch (error) {
                    console.error('分段保存失败:', error);
                    const buttons = document.querySelector('.save-buttons');
                    buttons.style.visibility = 'visible';
                    button.textContent = '保存失败';
                    setTimeout(() => {
                        button.textContent = originalText;
                        button.disabled = false;
                    }, 2000);
                }
            }

            const THEME_KEY = 'trendradar_theme';
            const VIEW_KEY = 'trendradar_view';
            const SECTION_KEY = 'trendradar_section';

            function setTheme(theme) {
                document.body.dataset.theme = theme;
                localStorage.setItem(THEME_KEY, theme);
                const btn = document.getElementById('theme-toggle');
                if (btn) {
                    btn.textContent = theme === 'dark' ? '☀️' : '🌙';
                }
            }

            function toggleTheme() {
                const current = document.body.dataset.theme || 'light';
                setTheme(current === 'dark' ? 'light' : 'dark');
            }

            function getActiveView() {
                const views = Array.from(document.querySelectorAll('.hotlist-view'));
                return views.find(view => view.style.display !== 'none') || views[0] || null;
            }

            function setSection(section) {
                const tabs = Array.from(document.querySelectorAll('.section-tab'));
                if (!tabs.length) {
                    return;
                }
                const available = tabs.map(t => t.dataset.section);
                let target = available.includes(section) ? section : 'all';
                if (!available.includes(target)) {
                    target = available[0];
                }

                document.querySelectorAll('.report-section').forEach(sec => {
                    const match = target === 'all' || sec.dataset.section === target;
                    sec.dataset.hidden = match ? "false" : "true";
                });

                tabs.forEach(tab => {
                    tab.classList.toggle('active', tab.dataset.section === target);
                });

                localStorage.setItem(SECTION_KEY, target);

                if (target === 'all' || target === 'hotlist') {
                    applySearchFilter();
                }
            }

            function setView(view) {
                const views = Array.from(document.querySelectorAll('.hotlist-view'));
                if (!views.length) {
                    return;
                }
                const available = views.map(v => v.dataset.view);
                const targetView = available.includes(view) ? view : available[0];
                views.forEach(v => {
                    v.style.display = v.dataset.view === targetView ? '' : 'none';
                });
                document.querySelectorAll('.view-btn').forEach(btn => {
                    btn.classList.toggle('active', btn.dataset.view === targetView);
                });
                localStorage.setItem(VIEW_KEY, targetView);
                applySearchFilter();
            }

            function initSectionTabs() {
                const tabs = document.querySelectorAll('.section-tab');
                if (!tabs.length) {
                    return;
                }
                document.body.dataset.sectionTabs = 'true';
                tabs.forEach(tab => {
                    tab.addEventListener('click', () => setSection(tab.dataset.section));
                });
                const saved = localStorage.getItem(SECTION_KEY) || 'all';
                setSection(saved);
            }

            function initViewToggle() {
                const viewButtons = document.querySelectorAll('.view-btn');
                if (!viewButtons.length) {
                    return;
                }
                viewButtons.forEach(btn => {
                    btn.addEventListener('click', () => setView(btn.dataset.view));
                });
                const defaultView = document.body.dataset.defaultView || 'keyword';
                const savedView = localStorage.getItem(VIEW_KEY);
                setView(savedView || defaultView);
            }

            function initTopicTabs() {
                document.querySelectorAll('.hotlist-view').forEach(view => {
                    const tabs = Array.from(view.querySelectorAll('.topic-tab'));
                    if (!tabs.length) {
                        return;
                    }
                    const groups = Array.from(view.querySelectorAll('.word-group'));
                    const storageKey = `trendradar_topic_${view.dataset.view}`;

                    const setActive = (topic) => {
                        let found = false;
                        tabs.forEach(tab => {
                            if (tab.dataset.topic === topic) {
                                found = true;
                                tab.classList.add('active');
                            } else {
                                tab.classList.remove('active');
                            }
                        });
                        const target = found ? topic : 'all';
                        groups.forEach(group => {
                            const match = target === 'all' || group.dataset.topic === target;
                            group.dataset.hidden = match ? "false" : "true";
                        });
                        localStorage.setItem(storageKey, target);
                        applySearchFilter();
                    };

                    tabs.forEach(tab => {
                        tab.addEventListener('click', () => setActive(tab.dataset.topic));
                    });

                    const saved = localStorage.getItem(storageKey) || 'all';
                    setActive(saved);
                });
            }

            function applySearchFilter() {
                const input = document.getElementById('search-input');
                if (!input) {
                    return;
                }
                const query = input.value.trim().toLowerCase();
                const view = getActiveView();
                if (!view) {
                    return;
                }

                let anyVisible = false;
                const groups = Array.from(view.querySelectorAll('.word-group'));
                groups.forEach(group => {
                    const isHidden = group.dataset.hidden === "true";
                    let visibleCount = 0;
                    group.querySelectorAll('.news-item').forEach(item => {
                        const hay = (item.dataset.search || '').toLowerCase();
                        const match = !query || hay.includes(query);
                        item.style.display = match ? '' : 'none';
                        if (match) {
                            visibleCount += 1;
                        }
                    });
                    if (isHidden) {
                        group.dataset.filtered = "true";
                        return;
                    }
                    group.dataset.filtered = visibleCount === 0 ? "true" : "false";
                    if (visibleCount > 0) {
                        anyVisible = true;
                    }
                });

                const empty = document.getElementById('search-empty');
                if (empty) {
                    empty.style.display = anyVisible ? 'none' : 'block';
                }
            }

            function initSearch() {
                const input = document.getElementById('search-input');
                if (!input) {
                    return;
                }
                input.addEventListener('input', applySearchFilter);
            }

            document.addEventListener('DOMContentLoaded', function() {
                window.scrollTo(0, 0);
                setTheme(localStorage.getItem(THEME_KEY) || 'light');
                initSectionTabs();
                initViewToggle();
                initTopicTabs();
                initSearch();
            });
        </script>
    </body>
    </html>
    """

    return html
