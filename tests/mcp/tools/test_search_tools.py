"""Handler-level tests for SearchTools.

Strategy: patch DataService to avoid SQLite; verify the unified dispatcher
handles invalid modes and forwards valid requests.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from mcp_server.tools.search_tools import SearchTools


def _make_tools(tmp_path):
    with patch("mcp_server.tools.search_tools.DataService") as mock_cls:
        mock_cls.return_value = MagicMock()
        return SearchTools(project_root=str(tmp_path))


def test_search_news_unified_empty_query_invalid(tmp_path):
    tools = _make_tools(tmp_path)

    result = tools.search_news_unified(query="")

    assert result["success"] is False
    assert result["error"]["code"] == "INVALID_PARAMETER"


def test_search_news_unified_invalid_mode(tmp_path):
    tools = _make_tools(tmp_path)

    result = tools.search_news_unified(query="AI", search_mode="bogus_mode")

    assert result["success"] is False
    assert result["error"]["code"] == "INVALID_PARAMETER"


def test_search_news_unified_keyword_mode_no_data_returns_empty(tmp_path):
    """When data_service reports no available date range, search returns NO_DATA_AVAILABLE."""
    tools = _make_tools(tmp_path)
    # Simulate empty output directory
    tools.data_service.get_available_date_range.return_value = (None, None)

    result = tools.search_news_unified(query="AI", search_mode="keyword", limit=10)

    assert result["success"] is False
    assert result["error"]["code"] == "NO_DATA_AVAILABLE"


def test_search_news_unified_keyword_mode_with_matches(tmp_path):
    """Provide a date_range so the tool exercises _search_by_keyword_mode path."""

    tools = _make_tools(tmp_path)
    # Return minimal title data containing the query keyword
    tools.data_service.parser.read_all_titles_for_date.return_value = (
        {
            "zhihu": {
                "AI trend is rising": {
                    "ranks": [1],
                    "url": "http://example.com",
                    "mobileUrl": "",
                    "count": 1,
                }
            }
        },
        {"zhihu": "Zhihu"},
        {},
    )

    result = tools.search_news_unified(
        query="AI",
        search_mode="keyword",
        date_range={"start": "2025-01-01", "end": "2025-01-01"},
        limit=10,
    )

    assert result["success"] is True
    assert result["summary"]["search_mode"] == "keyword"
    assert result["summary"]["total_found"] >= 1
