"""
TrendRadar AI 模块

提供 AI 大模型对热点新闻的深度分析和翻译功能
"""

from .analyzer import AIAnalysisResult, AIAnalyzer
from .formatter import (
    get_ai_analysis_renderer,
    render_ai_analysis_dingtalk,
    render_ai_analysis_feishu,
    render_ai_analysis_html,
    render_ai_analysis_html_rich,
    render_ai_analysis_markdown,
    render_ai_analysis_plain,
)
from .translator import AITranslator, BatchTranslationResult, TranslationResult

__all__ = [
    "AIAnalysisResult",
    # 分析器
    "AIAnalyzer",
    # 翻译器
    "AITranslator",
    "BatchTranslationResult",
    "TranslationResult",
    # 格式化
    "get_ai_analysis_renderer",
    "render_ai_analysis_dingtalk",
    "render_ai_analysis_feishu",
    "render_ai_analysis_html",
    "render_ai_analysis_html_rich",
    "render_ai_analysis_markdown",
    "render_ai_analysis_plain",
]
