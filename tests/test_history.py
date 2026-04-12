# coding=utf-8
"""
Tests for trendradar.core.history -- keyword-based history search.

Covers:
- Search with matching results
- Platform distribution calculation
- Timeline (date) aggregation
- Empty results when no matches
- Limit enforcement
- Edge cases: empty keyword handled at API level, single-day data
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from trendradar.core.history import HistoryMatch, HistoryResult, HistorySearcher


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_hits(items):
    """Build raw hit dicts matching the storage layer format."""
    return [
        {
            "title": t,
            "platform_id": pid,
            "platform_name": pname,
            "rank": rank,
            "url": url,
            "first_crawl_time": fct,
            "last_crawl_time": lct,
            "date": date,
        }
        for (t, pid, pname, rank, url, fct, lct, date) in items
    ]


SAMPLE_HITS = _make_hits([
    ("人工智能改变生活", "toutiao", "今日头条", 1, "https://example.com/1", "09:00", "10:00", "2026-04-13"),
    ("人工智能芯片突破", "baidu", "百度热搜", 3, "https://example.com/2", "08:30", "09:30", "2026-04-13"),
    ("人工智能教育应用", "weibo", "微博热搜", 5, "https://example.com/3", "07:00", "08:00", "2026-04-12"),
    ("人工智能医疗进展", "toutiao", "今日头条", 2, "https://example.com/4", "10:00", "11:00", "2026-04-11"),
])


@pytest.fixture
def mock_storage():
    """Return a mock storage manager whose search_titles returns SAMPLE_HITS."""
    sm = MagicMock()
    sm.search_titles.return_value = list(SAMPLE_HITS)
    return sm


@pytest.fixture
def searcher(mock_storage):
    return HistorySearcher(mock_storage)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestHistorySearcherSearch:
    """HistorySearcher.search() basic behavior."""

    def test_returns_all_matches(self, searcher, mock_storage):
        result = searcher.search("人工智能")
        assert result.total_count == 4
        assert len(result.matches) == 4
        mock_storage.search_titles.assert_called_once_with(
            "人工智能", days=7, limit=200,
        )

    def test_keyword_stored_in_result(self, searcher):
        result = searcher.search("人工智能")
        assert result.keyword == "人工智能"

    def test_match_fields(self, searcher):
        result = searcher.search("人工智能")
        first = result.matches[0]
        assert isinstance(first, HistoryMatch)
        assert first.title == "人工智能改变生活"
        assert first.platform == "今日头条"
        assert first.rank == 1
        assert first.url == "https://example.com/1"


class TestPlatformDistribution:
    """platform_distribution aggregation."""

    def test_counts_per_platform(self, searcher):
        result = searcher.search("人工智能")
        dist = result.platform_distribution
        assert dist["今日头条"] == 2
        assert dist["百度热搜"] == 1
        assert dist["微博热搜"] == 1

    def test_sum_equals_total(self, searcher):
        result = searcher.search("人工智能")
        assert sum(result.platform_distribution.values()) == result.total_count


class TestTimeline:
    """timeline (date -> count) aggregation."""

    def test_date_counts(self, searcher):
        result = searcher.search("人工智能")
        tl = result.timeline
        assert tl["2026-04-13"] == 2
        assert tl["2026-04-12"] == 1
        assert tl["2026-04-11"] == 1

    def test_timeline_sorted_ascending(self, searcher):
        result = searcher.search("人工智能")
        dates = list(result.timeline.keys())
        assert dates == sorted(dates)


class TestDateRange:
    """date_range tuple."""

    def test_earliest_and_latest(self, searcher):
        result = searcher.search("人工智能")
        assert result.date_range == ("2026-04-11", "2026-04-13")


class TestEmptyResults:
    """No matches scenario."""

    def test_empty_when_no_hits(self):
        sm = MagicMock()
        sm.search_titles.return_value = []
        searcher = HistorySearcher(sm)

        result = searcher.search("不存在的关键词")
        assert result.total_count == 0
        assert result.matches == []
        assert result.platform_distribution == {}
        assert result.timeline == {}
        assert result.date_range == ("", "")
        assert result.keyword == "不存在的关键词"


class TestLimitEnforcement:
    """Limits and bounds clamping."""

    def test_days_clamped_to_30(self, mock_storage):
        searcher = HistorySearcher(mock_storage)
        searcher.search("test", days=999)
        mock_storage.search_titles.assert_called_once_with("test", days=30, limit=200)

    def test_days_minimum_is_1(self, mock_storage):
        searcher = HistorySearcher(mock_storage)
        searcher.search("test", days=-5)
        mock_storage.search_titles.assert_called_once_with("test", days=1, limit=200)

    def test_limit_clamped_to_500(self, mock_storage):
        searcher = HistorySearcher(mock_storage)
        searcher.search("test", limit=9999)
        mock_storage.search_titles.assert_called_once_with("test", days=7, limit=500)

    def test_limit_minimum_is_1(self, mock_storage):
        searcher = HistorySearcher(mock_storage)
        searcher.search("test", limit=-10)
        mock_storage.search_titles.assert_called_once_with("test", days=7, limit=1)


class TestToDict:
    """HistoryResult.to_dict() serialization."""

    def test_serializable(self, searcher):
        result = searcher.search("人工智能")
        d = result.to_dict()
        assert d["keyword"] == "人工智能"
        assert d["total_count"] == 4
        assert isinstance(d["date_range"], list)
        assert len(d["date_range"]) == 2
        assert isinstance(d["matches"], list)
        assert d["matches"][0]["title"] == "人工智能改变生活"

    def test_empty_result_serializable(self):
        sm = MagicMock()
        sm.search_titles.return_value = []
        result = HistorySearcher(sm).search("nope")
        d = result.to_dict()
        assert d["total_count"] == 0
        assert d["matches"] == []


class TestSingleDayData:
    """When all results come from a single date."""

    def test_single_date_range(self):
        sm = MagicMock()
        sm.search_titles.return_value = _make_hits([
            ("AI News", "baidu", "百度", 1, "", "09:00", "10:00", "2026-04-13"),
            ("AI Update", "baidu", "百度", 2, "", "09:00", "10:00", "2026-04-13"),
        ])
        result = HistorySearcher(sm).search("AI")
        assert result.date_range == ("2026-04-13", "2026-04-13")
        assert result.timeline == {"2026-04-13": 2}
