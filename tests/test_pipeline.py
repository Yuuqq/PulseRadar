# coding=utf-8

from __future__ import annotations

from unittest.mock import MagicMock, patch


def _make_ctx(config_overrides=None):
    """Build a minimal mock AppContext for pipeline tests."""
    base_config = {
        "DISPLAY": {"REGIONS": {"STANDALONE": False}},
        "AI_ANALYSIS": {"ENABLED": False},
        "STORAGE": {"FORMATS": {"HTML": False}},
        "SHOW_VERSION_UPDATE": False,
    }
    if config_overrides:
        base_config.update(config_overrides)

    ctx = MagicMock()
    ctx.config = base_config
    ctx.display_mode = "keyword"
    ctx.weight_config = {}
    ctx.rank_threshold = 5
    return ctx


# ---------------------------------------------------------------------------
# prepare_standalone_data tests
# ---------------------------------------------------------------------------

def test_prepare_standalone_data_returns_none_when_disabled():
    from trendradar.core.pipeline import prepare_standalone_data

    ctx = _make_ctx()
    result = prepare_standalone_data(ctx, results={}, id_to_name={})
    assert result is None


def test_prepare_standalone_data_returns_none_when_no_platforms_or_rss():
    from trendradar.core.pipeline import prepare_standalone_data

    ctx = _make_ctx({
        "DISPLAY": {
            "REGIONS": {"STANDALONE": True},
            "STANDALONE": {"PLATFORMS": [], "RSS_FEEDS": [], "MAX_ITEMS": 20},
        },
    })
    result = prepare_standalone_data(ctx, results={}, id_to_name={})
    assert result is None


def test_prepare_standalone_data_extracts_platform_items():
    from trendradar.core.pipeline import prepare_standalone_data

    ctx = _make_ctx({
        "DISPLAY": {
            "REGIONS": {"STANDALONE": True},
            "STANDALONE": {"PLATFORMS": ["weibo"], "RSS_FEEDS": [], "MAX_ITEMS": 5},
        },
    })

    results = {
        "weibo": {
            "Trending Topic": {"url": "http://weibo.com/1", "ranks": [1]},
            "Hot Item": {"url": "http://weibo.com/2", "ranks": [2]},
        },
    }
    id_to_name = {"weibo": "Weibo"}

    data = prepare_standalone_data(ctx, results, id_to_name)
    assert data is not None
    assert len(data["platforms"]) == 1
    assert data["platforms"][0]["id"] == "weibo"
    assert data["platforms"][0]["name"] == "Weibo"
    assert len(data["platforms"][0]["items"]) == 2


def test_prepare_standalone_data_respects_max_items():
    from trendradar.core.pipeline import prepare_standalone_data

    ctx = _make_ctx({
        "DISPLAY": {
            "REGIONS": {"STANDALONE": True},
            "STANDALONE": {"PLATFORMS": ["src"], "RSS_FEEDS": [], "MAX_ITEMS": 1},
        },
    })

    results = {
        "src": {
            "Title A": {"url": "http://a", "ranks": [1]},
            "Title B": {"url": "http://b", "ranks": [2]},
            "Title C": {"url": "http://c", "ranks": [3]},
        },
    }

    data = prepare_standalone_data(ctx, results, {"src": "Source"})
    assert data is not None
    assert len(data["platforms"][0]["items"]) == 1


def test_prepare_standalone_data_extracts_rss_feeds():
    from trendradar.core.pipeline import prepare_standalone_data

    ctx = _make_ctx({
        "DISPLAY": {
            "REGIONS": {"STANDALONE": True},
            "STANDALONE": {"PLATFORMS": [], "RSS_FEEDS": ["feed1"], "MAX_ITEMS": 10},
        },
    })

    rss_items = [
        {"feed_id": "feed1", "feed_name": "My Feed", "title": "Article 1", "url": "http://r1", "published_at": "", "author": ""},
        {"feed_id": "feed1", "feed_name": "My Feed", "title": "Article 2", "url": "http://r2", "published_at": "", "author": ""},
        {"feed_id": "other_feed", "feed_name": "Other", "title": "Excluded", "url": "http://x", "published_at": "", "author": ""},
    ]

    data = prepare_standalone_data(ctx, results={}, id_to_name={}, rss_items=rss_items)
    assert data is not None
    assert len(data["rss_feeds"]) == 1
    assert data["rss_feeds"][0]["id"] == "feed1"
    assert len(data["rss_feeds"][0]["items"]) == 2


# ---------------------------------------------------------------------------
# run_analysis_pipeline tests
# ---------------------------------------------------------------------------

def test_run_analysis_pipeline_basic_flow():
    from trendradar.core.pipeline import run_analysis_pipeline

    ctx = _make_ctx({"STORAGE": {"FORMATS": {"HTML": False}}, "AI_ANALYSIS": {"ENABLED": False}})
    ctx.count_frequency.return_value = (
        [{"word": "test", "count": 3, "titles": []}],
        10,
    )

    mock_ai_fn = MagicMock()
    mock_strategy_fn = MagicMock()

    stats, html_file, ai_result = run_analysis_pipeline(
        ctx=ctx,
        data_source={"src1": {"title": {}}},
        mode="daily",
        title_info={},
        new_titles={},
        word_groups=[],
        filter_words=[],
        id_to_name={"src1": "Source1"},
        report_mode="current",
        update_info=None,
        run_ai_analysis_fn=mock_ai_fn,
        get_mode_strategy_fn=mock_strategy_fn,
    )

    assert stats == [{"word": "test", "count": 3, "titles": []}]
    assert html_file is None  # HTML disabled
    assert ai_result is None  # AI disabled
    ctx.count_frequency.assert_called_once()


def test_run_analysis_pipeline_with_ai_enabled():
    from trendradar.core.pipeline import run_analysis_pipeline

    ctx = _make_ctx({
        "STORAGE": {"FORMATS": {"HTML": False}},
        "AI_ANALYSIS": {"ENABLED": True},
    })
    ctx.count_frequency.return_value = (
        [{"word": "ai", "count": 5, "titles": []}],
        20,
    )
    ctx.display_mode = "keyword"

    mock_ai_result = MagicMock()
    mock_ai_fn = MagicMock(return_value=mock_ai_result)
    mock_strategy_fn = MagicMock(return_value={"report_type": "daily_report", "mode_name": "Daily"})

    stats, html_file, ai_result = run_analysis_pipeline(
        ctx=ctx,
        data_source={},
        mode="daily",
        title_info={},
        new_titles={},
        word_groups=[],
        filter_words=[],
        id_to_name={},
        report_mode="daily",
        update_info=None,
        run_ai_analysis_fn=mock_ai_fn,
        get_mode_strategy_fn=mock_strategy_fn,
    )

    assert ai_result is mock_ai_result
    mock_ai_fn.assert_called_once()


def test_run_analysis_pipeline_with_html_enabled():
    from trendradar.core.pipeline import run_analysis_pipeline

    ctx = _make_ctx({
        "STORAGE": {"FORMATS": {"HTML": True}},
        "AI_ANALYSIS": {"ENABLED": False},
        "SHOW_VERSION_UPDATE": False,
    })
    ctx.count_frequency.return_value = ([{"word": "w", "count": 1, "titles": []}], 5)
    ctx.display_mode = "keyword"
    ctx.generate_html.return_value = "/path/to/report.html"

    stats, html_file, ai_result = run_analysis_pipeline(
        ctx=ctx,
        data_source={},
        mode="current",
        title_info={},
        new_titles={},
        word_groups=[],
        filter_words=[],
        id_to_name={},
        report_mode="current",
        update_info=None,
        run_ai_analysis_fn=MagicMock(),
        get_mode_strategy_fn=MagicMock(),
    )

    assert html_file == "/path/to/report.html"
    ctx.generate_html.assert_called_once()


def test_run_analysis_pipeline_empty_stats_skips_ai():
    from trendradar.core.pipeline import run_analysis_pipeline

    ctx = _make_ctx({"STORAGE": {"FORMATS": {"HTML": False}}, "AI_ANALYSIS": {"ENABLED": True}})
    ctx.count_frequency.return_value = ([], 0)
    ctx.display_mode = "keyword"

    mock_ai_fn = MagicMock()

    stats, html_file, ai_result = run_analysis_pipeline(
        ctx=ctx,
        data_source={},
        mode="daily",
        title_info={},
        new_titles={},
        word_groups=[],
        filter_words=[],
        id_to_name={},
        report_mode="daily",
        update_info=None,
        run_ai_analysis_fn=mock_ai_fn,
        get_mode_strategy_fn=MagicMock(),
    )

    assert ai_result is None
    mock_ai_fn.assert_not_called()
