"""Handler-level tests for DataQueryTools.

Strategy: patch mcp_server.tools.data_query.DataService to avoid going through
ParserService/SQLite and to keep tests fast + isolated. Exercises the public
surface directly (D-10: tool class methods, not async wrappers).
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from mcp_server.tools.data_query import DataQueryTools


def _make_tools(tmp_path) -> DataQueryTools:
    """Instantiate with patched DataService so no real disk/SQLite is touched."""
    with patch("mcp_server.tools.data_query.DataService") as mock_svc_cls:
        mock_svc_cls.return_value = MagicMock()
        tools = DataQueryTools(project_root=str(tmp_path))
    return tools


def test_get_latest_news_returns_success_shape(tmp_path):
    tools = _make_tools(tmp_path)
    tools.data_service.get_latest_news.return_value = [
        {"title": "t1", "platform": "zhihu", "rank": 1, "timestamp": "2025-01-01 00:00:00"},
        {"title": "t2", "platform": "zhihu", "rank": 2, "timestamp": "2025-01-01 00:00:00"},
    ]

    result = tools.get_latest_news(platforms=None, limit=10)

    assert result["success"] is True
    assert result["summary"]["total"] == 2
    assert result["summary"]["returned"] == 2
    assert result["data"][0]["title"] == "t1"


def test_get_latest_news_handles_data_service_exception(tmp_path):
    tools = _make_tools(tmp_path)
    tools.data_service.get_latest_news.side_effect = RuntimeError("boom")

    result = tools.get_latest_news(platforms=None, limit=10)

    assert result["success"] is False
    assert result["error"]["code"] == "INTERNAL_ERROR"
    assert "boom" in result["error"]["message"]


def test_search_news_by_keyword_empty_keyword_raises_invalid_parameter(tmp_path):
    tools = _make_tools(tmp_path)

    result = tools.search_news_by_keyword(keyword="")

    assert result["success"] is False
    assert result["error"]["code"] == "INVALID_PARAMETER"


def test_get_trending_topics_rejects_invalid_extract_mode(tmp_path):
    tools = _make_tools(tmp_path)

    result = tools.get_trending_topics(top_n=5, mode="current", extract_mode="unknown_mode")

    assert result["success"] is False
    assert result["error"]["code"] == "INVALID_PARAMETER"
    assert "unknown_mode" in result["error"]["message"]


def test_get_rss_feeds_status_success(tmp_path):
    tools = _make_tools(tmp_path)
    tools.data_service.get_rss_feeds_status.return_value = {
        "available_dates": ["2025-01-01"],
        "total_dates": 1,
        "today_feeds": {},
        "generated_at": "2025-01-01 00:00:00",
    }

    result = tools.get_rss_feeds_status()

    assert result["success"] is True
    assert result["total_dates"] == 1
