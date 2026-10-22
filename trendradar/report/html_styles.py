"""HTML 报告样式加载器

CSS 内容存放于 ``trendradar/report/templates/report.css``，本模块作为
向后兼容的薄加载器在导入时一次性读取该文件并暴露 ``REPORT_CSS`` 常量，
避免在 Python 源码中维护大段 CSS 字符串。
"""

from __future__ import annotations

from importlib import resources


def _load_css() -> str:
    return resources.files("trendradar.report.templates").joinpath("report.css").read_text(encoding="utf-8")


REPORT_CSS: str = _load_css()

__all__ = ["REPORT_CSS"]
