# coding=utf-8
"""
Tests for trendradar.core.trend -- cross-cycle trend detection.

Covers:
- New topic detection
- Rising / falling / stable classification
- Cross-platform detection (3+ platforms)
- Disappeared topic detection
- Heat score calculation
- Empty / edge-case inputs
- Period label passthrough
- Legacy data format compatibility
"""

from __future__ import annotations

from trendradar.core.trend import TrendAnalyzer, TrendItem, TrendReport


# ---------------------------------------------------------------------------
# Fixtures (plain dicts -- no pytest fixtures needed for pure logic)
# ---------------------------------------------------------------------------

def _make_results(*platform_specs):
    """
    Build a crawl-results dict from compact specs.

    Each spec is (platform_id, {title: [ranks]}).
    """
    results = {}
    for platform_id, titles in platform_specs:
        results[platform_id] = {}
        for title, ranks in titles.items():
            results[platform_id][title] = {"ranks": ranks, "url": "", "mobileUrl": ""}
    return results


# ---------------------------------------------------------------------------
# TrendAnalyzer.compare_periods
# ---------------------------------------------------------------------------

class TestComparePeriods:
    """Core comparison logic."""

    def test_new_topic_detection(self):
        """Topics in current but not previous are classified as new."""
        previous = _make_results(("p1", {"Old Topic": [1]}))
        current = _make_results(
            ("p1", {"Old Topic": [2], "Brand New": [5]}),
        )

        report = TrendAnalyzer().compare_periods(current, previous)

        new_titles = [t.title for t in report.new_trends]
        assert "Brand New" in new_titles
        assert "Old Topic" not in new_titles

        for item in report.new_trends:
            assert item.is_new is True
            assert item.previous_rank is None

    def test_rising_trend(self):
        """A topic that improved rank by more than 2 is rising."""
        previous = _make_results(("p1", {"Topic A": [10]}))
        current = _make_results(("p1", {"Topic A": [3]}))

        report = TrendAnalyzer().compare_periods(current, previous)

        rising_titles = [t.title for t in report.rising_trends]
        assert "Topic A" in rising_titles

        item = report.rising_trends[0]
        assert item.rank_change == 7  # 10 - 3
        assert item.is_rising is True
        assert item.previous_rank == 10
        assert item.current_rank == 3

    def test_falling_trend(self):
        """A topic that dropped rank by more than 2 is falling."""
        previous = _make_results(("p1", {"Topic B": [2]}))
        current = _make_results(("p1", {"Topic B": [10]}))

        report = TrendAnalyzer().compare_periods(current, previous)

        falling_titles = [t.title for t in report.falling_trends]
        assert "Topic B" in falling_titles

        item = report.falling_trends[0]
        assert item.rank_change == -8  # 2 - 10
        assert item.is_rising is False

    def test_stable_trend(self):
        """A topic with rank change within [-2, 2] is stable."""
        previous = _make_results(("p1", {"Steady": [5]}))
        current = _make_results(("p1", {"Steady": [4]}))

        report = TrendAnalyzer().compare_periods(current, previous)

        stable_titles = [t.title for t in report.stable_trends]
        assert "Steady" in stable_titles
        assert len(report.rising_trends) == 0
        assert len(report.falling_trends) == 0

    def test_stable_at_exact_threshold(self):
        """Rank change of exactly +2 or -2 is still stable."""
        previous = _make_results(("p1", {"Edge Up": [5], "Edge Down": [3]}))
        current = _make_results(("p1", {"Edge Up": [3], "Edge Down": [5]}))

        report = TrendAnalyzer().compare_periods(current, previous)

        stable_titles = {t.title for t in report.stable_trends}
        assert "Edge Up" in stable_titles
        assert "Edge Down" in stable_titles
        assert len(report.rising_trends) == 0
        assert len(report.falling_trends) == 0

    def test_disappeared_topics(self):
        """Topics in previous but not current are listed as disappeared."""
        previous = _make_results(("p1", {"Gone": [1], "Remaining": [2]}))
        current = _make_results(("p1", {"Remaining": [3]}))

        report = TrendAnalyzer().compare_periods(current, previous)

        assert "Gone" in report.disappeared
        assert "Remaining" not in report.disappeared

    def test_cross_platform_detection(self):
        """Topics appearing on 3+ platforms are cross-platform."""
        current = _make_results(
            ("p1", {"Hot": [1]}),
            ("p2", {"Hot": [2]}),
            ("p3", {"Hot": [3]}),
            ("p4", {"Solo": [1]}),
        )
        previous = _make_results()

        report = TrendAnalyzer().compare_periods(current, previous)

        cross_titles = [t.title for t in report.cross_platform]
        assert "Hot" in cross_titles
        assert "Solo" not in cross_titles

        hot_item = next(t for t in report.cross_platform if t.title == "Hot")
        assert hot_item.platform_count == 3

    def test_cross_platform_exactly_two_excluded(self):
        """Topics on exactly 2 platforms do NOT qualify as cross-platform."""
        current = _make_results(
            ("p1", {"Duo": [1]}),
            ("p2", {"Duo": [2]}),
        )
        previous = _make_results()

        report = TrendAnalyzer().compare_periods(current, previous)
        assert len(report.cross_platform) == 0

    def test_totals(self):
        """total_current and total_previous count unique titles."""
        previous = _make_results(("p1", {"A": [1], "B": [2]}))
        current = _make_results(("p1", {"B": [1], "C": [3]}))

        report = TrendAnalyzer().compare_periods(current, previous)

        assert report.total_current == 2   # B, C
        assert report.total_previous == 2  # A, B

    def test_id_to_name_mapping(self):
        """Platform names come from id_to_name, falling back to raw id."""
        current = _make_results(
            ("weibo", {"Topic": [1]}),
            ("unknown_id", {"Topic": [2]}),
        )
        previous = _make_results()
        id_to_name = {"weibo": "Weibo Hot Search"}

        report = TrendAnalyzer().compare_periods(current, previous, id_to_name)

        item = report.new_trends[0]
        assert "Weibo Hot Search" in item.platforms
        assert "unknown_id" in item.platforms

    def test_period_labels(self):
        """Custom period labels pass through to the report."""
        report = TrendAnalyzer().compare_periods(
            {}, {},
            current_period_label="2024-01-15 14:00",
            previous_period_label="2024-01-15 08:00",
        )
        assert report.current_period == "2024-01-15 14:00"
        assert report.previous_period == "2024-01-15 08:00"

    def test_sorting_by_heat(self):
        """Results within each bucket are sorted by heat_score descending."""
        current = _make_results(
            ("p1", {"Low Heat": [50], "High Heat": [1]}),
            ("p2", {"High Heat": [2]}),
            ("p3", {"High Heat": [3]}),
        )
        previous = _make_results()

        report = TrendAnalyzer().compare_periods(current, previous)

        assert len(report.new_trends) == 2
        # High Heat has rank 1 + 3 platforms => highest heat
        assert report.new_trends[0].title == "High Heat"
        assert report.new_trends[1].title == "Low Heat"


# ---------------------------------------------------------------------------
# Empty / edge-case inputs
# ---------------------------------------------------------------------------

class TestEdgeCases:

    def test_both_empty(self):
        """No data in either period produces an empty report."""
        report = TrendAnalyzer().compare_periods({}, {})

        assert report.new_trends == []
        assert report.rising_trends == []
        assert report.falling_trends == []
        assert report.stable_trends == []
        assert report.disappeared == []
        assert report.cross_platform == []
        assert report.total_current == 0
        assert report.total_previous == 0

    def test_current_empty(self):
        """Empty current with non-empty previous means everything disappeared."""
        previous = _make_results(("p1", {"A": [1], "B": [2]}))
        report = TrendAnalyzer().compare_periods({}, previous)

        assert len(report.disappeared) == 2
        assert report.total_current == 0
        assert report.total_previous == 2

    def test_previous_empty(self):
        """Empty previous with non-empty current means everything is new."""
        current = _make_results(("p1", {"X": [1], "Y": [5]}))
        report = TrendAnalyzer().compare_periods(current, {})

        assert len(report.new_trends) == 2
        assert len(report.disappeared) == 0

    def test_missing_ranks_defaults_to_999(self):
        """A title with empty ranks list gets rank 999."""
        current = _make_results()
        current["p1"] = {"No Rank": {"ranks": [], "url": ""}}
        previous = _make_results()

        report = TrendAnalyzer().compare_periods(current, previous)

        item = report.new_trends[0]
        assert item.current_rank == 999

    def test_legacy_list_format(self):
        """Data in the legacy format (data is a list of ranks) works."""
        current = {"p1": {"Legacy": [1, 3, 5]}}
        previous = {}

        report = TrendAnalyzer().compare_periods(current, previous)

        item = report.new_trends[0]
        assert item.current_rank == 1

    def test_single_platform_single_title(self):
        """Minimal input: one platform, one title in each period."""
        previous = _make_results(("p1", {"Only": [3]}))
        current = _make_results(("p1", {"Only": [3]}))

        report = TrendAnalyzer().compare_periods(current, previous)

        assert len(report.stable_trends) == 1
        assert report.stable_trends[0].rank_change == 0
        assert len(report.new_trends) == 0
        assert len(report.disappeared) == 0


# ---------------------------------------------------------------------------
# _calculate_heat
# ---------------------------------------------------------------------------

class TestCalculateHeat:

    def test_rank_1_single_platform(self):
        score = TrendAnalyzer._calculate_heat(1, 1)
        assert score == 98 + 15

    def test_rank_50_single_platform(self):
        score = TrendAnalyzer._calculate_heat(50, 1)
        assert score == 0 + 15

    def test_rank_above_50_floors_to_zero(self):
        score = TrendAnalyzer._calculate_heat(100, 1)
        assert score == 0 + 15

    def test_multiple_platforms_add_score(self):
        score = TrendAnalyzer._calculate_heat(1, 5)
        assert score == 98 + 75

    def test_rank_0_edge(self):
        """Rank 0 is unusual but should not break."""
        score = TrendAnalyzer._calculate_heat(0, 1)
        assert score == 100 + 15


# ---------------------------------------------------------------------------
# _build_topic_index
# ---------------------------------------------------------------------------

class TestBuildTopicIndex:

    def test_best_rank_across_platforms(self):
        """When the same title appears on multiple platforms, keep the best rank."""
        results = _make_results(
            ("p1", {"Shared": [5]}),
            ("p2", {"Shared": [2]}),
        )
        index = TrendAnalyzer._build_topic_index(results, {})

        best_rank, platforms = index["Shared"]
        assert best_rank == 2
        assert len(platforms) == 2

    def test_best_rank_within_single_platform(self):
        """Within one platform, min of the ranks list is used."""
        results = {"p1": {"Multi Rank": {"ranks": [10, 3, 7], "url": ""}}}
        index = TrendAnalyzer._build_topic_index(results, {})

        best_rank, _ = index["Multi Rank"]
        assert best_rank == 3

    def test_empty_results(self):
        index = TrendAnalyzer._build_topic_index({}, {})
        assert index == {}


# ---------------------------------------------------------------------------
# TrendItem immutability
# ---------------------------------------------------------------------------

class TestTrendItemFrozen:

    def test_frozen(self):
        item = TrendItem(
            title="T", current_rank=1, previous_rank=None,
            rank_change=0, platform_count=1, platforms=("p",),
            is_new=True, is_rising=True, heat_score=100.0,
        )
        try:
            item.title = "changed"
            assert False, "Should raise FrozenInstanceError"
        except AttributeError:
            pass
