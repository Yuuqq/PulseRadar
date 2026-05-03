"""HTML 报告脚本加载器

JS 内容存放于 ``trendradar/report/templates/report.js``，本模块作为
向后兼容的薄加载器在导入时一次性读取该文件并暴露 ``REPORT_JS`` 常量，
避免在 Python 源码中维护大段 JavaScript 字符串。
"""

from __future__ import annotations

from importlib import resources


def _load_js() -> str:
    return resources.files("trendradar.report.templates").joinpath("report.js").read_text(encoding="utf-8")


REPORT_JS: str = _load_js()

__all__ = ["REPORT_JS"]
