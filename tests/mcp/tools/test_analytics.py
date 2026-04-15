"""Handler-level tests for AnalyticsTools.

Strategy: patch DataService so the analytics tools do not hit ParserService/SQLite.
Exercises unified dispatcher and at least one concrete analysis path.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from mcp_server.tools.analytics import AnalyticsTools


def _make_tools(tmp_path):
    with patch("mcp_server.tools.analytics.DataService") as mock_cls:
        mock_cls.return_value = MagicMock()
        return AnalyticsTools(project_root=str(tmp_path))


def test_analyze_data_insights_unified_rejects_invalid_type(tmp_path):
    tools = _make_tools(tmp_path)

    result = tools.analyze_data_insights_unified(insight_type="bogus_type")

    assert result["success"] is False
    assert result["error"]["code"] == "INVALID_PARAMETER"
    assert "bogus_type" in result["error"]["message"]


def test_analyze_topic_trend_unified_rejects_invalid_analysis_type(tmp_path):
    tools = _make_tools(tmp_path)

    result = tools.analyze_topic_trend_unified(topic="AI", analysis_type="bogus")

    assert result["success"] is False
    assert result["error"]["code"] == "INVALID_PARAMETER"
    assert "bogus" in result["error"]["message"]


def test_analyze_topic_trend_unified_empty_topic_invalid(tmp_path):
    tools = _make_tools(tmp_path)

    result = tools.analyze_topic_trend_unified(topic="", analysis_type="trend")

    assert result["success"] is False
    assert result["error"]["code"] == "INVALID_PARAMETER"


def test_analyze_data_insights_unified_dispatches_to_platform_compare(tmp_path):
    """platform_compare branch should call self.compare_platforms with topic."""
    tools = _make_tools(tmp_path)

    sentinel = {"success": True, "summary": {"description": "stub"}, "data": {}}
    with patch.object(tools, "compare_platforms", return_value=sentinel) as mock_cp:
        result = tools.analyze_data_insights_unified(insight_type="platform_compare", topic="AI")

    assert result is sentinel
    mock_cp.assert_called_once()
    # Topic arg must propagate
    kwargs = mock_cp.call_args.kwargs
    assert kwargs.get("topic") == "AI"


def test_analyze_data_insights_unified_dispatches_to_keyword_cooccur(tmp_path):
    tools = _make_tools(tmp_path)

    sentinel = {"success": True, "summary": {}, "data": {}}
    with patch.object(tools, "analyze_keyword_cooccurrence", return_value=sentinel) as mock_cc:
        result = tools.analyze_data_insights_unified(
            insight_type="keyword_cooccur", min_frequency=5, top_n=15
        )

    assert result is sentinel
    mock_cc.assert_called_once_with(min_frequency=5, top_n=15)
