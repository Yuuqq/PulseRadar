"""
报告生成模块

提供报告生成和格式化功能，包括：
- HTML 报告生成
- 标题格式化工具
- Hub 页面生成
- Manifest 管理

模块结构：
- helpers: 报告辅助函数（清理、转义、格式化）
- formatter: 平台标题格式化
- html: HTML 报告渲染
- generator: 报告生成器
- manifest: 报告清单管理
- hub: Hub 聚合页面
"""

from trendradar.report.formatter import format_title_for_platform
from trendradar.report.generator import (
    generate_html_report,
    prepare_report_data,
)
from trendradar.report.helpers import (
    clean_title,
    format_rank_display,
    html_escape,
)
from trendradar.report.html import render_html_content
from trendradar.report.hub import generate_hub_html
from trendradar.report.manifest import (
    add_report_entry,
    build_report_entry,
    load_manifest,
    save_manifest,
)

__all__ = [
    "add_report_entry",
    "build_report_entry",
    "clean_title",
    "format_rank_display",
    "format_title_for_platform",
    "generate_html_report",
    "generate_hub_html",
    "html_escape",
    "load_manifest",
    "prepare_report_data",
    "render_html_content",
    "save_manifest",
]
