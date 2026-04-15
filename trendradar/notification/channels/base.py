"""
Shared helpers for notification channels.

Provides:
- ``render_ai_content``: call the AI formatter for a given channel
- ``extract_ai_stats``: pull stat fields from an AI analysis result
- ``prepare_batches``: split + add batch headers in one call
"""

from collections.abc import Callable
from typing import Any

from trendradar.logging import get_logger
from trendradar.notification.batch import add_batch_headers, get_max_batch_header_size

logger = get_logger(__name__)


def render_ai_content(ai_analysis: Any, channel: str) -> str:
    """Render AI analysis into the format expected by *channel*.

    Returns an empty string when *ai_analysis* is falsy or the formatter
    is not installed.
    """
    if not ai_analysis:
        return ""
    try:
        from trendradar.ai.formatter import get_ai_analysis_renderer

        renderer = get_ai_analysis_renderer(channel)
        return renderer(ai_analysis)
    except ImportError:
        return ""


def extract_ai_stats(ai_analysis: Any) -> dict | None:
    """Return a stats dict if AI analysis succeeded, else ``None``."""
    if not ai_analysis or not getattr(ai_analysis, "success", False):
        return None
    return {
        "total_news": getattr(ai_analysis, "total_news", 0),
        "analyzed_news": getattr(ai_analysis, "analyzed_news", 0),
        "max_news_limit": getattr(ai_analysis, "max_news_limit", 0),
        "hotlist_count": getattr(ai_analysis, "hotlist_count", 0),
        "rss_count": getattr(ai_analysis, "rss_count", 0),
        "ai_mode": getattr(ai_analysis, "ai_mode", ""),
    }


def prepare_batches(
    report_data: dict,
    format_type: str,
    split_content_func: Callable,
    update_info: dict | None,
    batch_size: int,
    mode: str,
    rss_items: list | None,
    rss_new_items: list | None,
    ai_content: str | None,
    standalone_data: dict | None,
    ai_stats: dict | None,
    report_type: str,
    *,
    header_format_type: str | None = None,
    template_overhead: int = 0,
) -> list[str]:
    """Split report content into batches and prepend batch headers.

    Parameters
    ----------
    format_type:
        The channel format key passed to ``split_content_func``.
    header_format_type:
        If the batch-header format differs from *format_type* (e.g. wework
        text mode), pass it here.  Defaults to *format_type*.
    template_overhead:
        Extra bytes to subtract from *batch_size* before splitting (used by
        the generic webhook channel for its JSON envelope).
    """
    hdr_fmt = header_format_type or format_type
    header_reserve = get_max_batch_header_size(hdr_fmt)
    effective_limit = batch_size - header_reserve - template_overhead

    batches = split_content_func(
        report_data,
        format_type,
        update_info,
        max_bytes=effective_limit,
        mode=mode,
        rss_items=rss_items,
        rss_new_items=rss_new_items,
        ai_content=ai_content,
        standalone_data=standalone_data,
        ai_stats=ai_stats,
        report_type=report_type,
    )

    return add_batch_headers(batches, hdr_fmt, batch_size)
