"""
Dead code removal verification for _analyze_trends (D-05).

Phase 3 removed the dead _analyze_trends() call and TrendAnalyzer import
from __main__.py. This test verifies the removal is complete.
"""

from __future__ import annotations

import inspect


def test_analyze_trends_removed_from_news_analyzer():
    """Verify D-05: _analyze_trends is removed from NewsAnalyzer."""
    from trendradar.__main__ import NewsAnalyzer

    # _analyze_trends method must NOT exist
    assert not hasattr(
        NewsAnalyzer, "_analyze_trends"
    ), "NewsAnalyzer must NOT have _analyze_trends method (D-05: dead code removed)"


def test_trend_analyzer_not_imported_in_main():
    """Verify D-05: TrendAnalyzer is not imported in __main__.py."""
    import trendradar.__main__ as main_module

    source = inspect.getsource(main_module)
    assert (
        "TrendAnalyzer" not in source
    ), "__main__.py must not import or reference TrendAnalyzer (D-05)"
    assert "trend_report" not in source, "__main__.py must not contain trend_report variable (D-05)"


def test_news_analyzer_is_thin_facade():
    """Verify REFACTOR-04: NewsAnalyzer is under 150 lines."""
    from trendradar.__main__ import NewsAnalyzer

    source = inspect.getsource(NewsAnalyzer)
    line_count = source.count("\n")
    assert line_count < 150, f"NewsAnalyzer must be under 150 lines (REFACTOR-04), got {line_count}"


def test_news_analyzer_delegates_to_orchestrators():
    """Verify D-06: NewsAnalyzer delegates to CrawlCoordinator and AnalysisEngine."""
    from trendradar.__main__ import NewsAnalyzer

    source = inspect.getsource(NewsAnalyzer)
    assert "CrawlCoordinator" in source, "NewsAnalyzer must reference CrawlCoordinator (D-06)"
    assert "AnalysisEngine" in source, "NewsAnalyzer must reference AnalysisEngine (D-06)"
    assert "crawl_all" in source, "NewsAnalyzer.run must call crawl_coordinator.crawl_all()"


def test_update_info_is_constructor_parameter():
    """Verify D-08: update_info is a constructor parameter."""
    from trendradar.__main__ import NewsAnalyzer

    sig = inspect.signature(NewsAnalyzer.__init__)
    assert (
        "update_info" in sig.parameters
    ), "NewsAnalyzer.__init__ must accept update_info parameter (D-08)"
