"""
Tests for frozen DTO definitions at stage boundaries.

Verifies structure, defaults, immutability, and full population of
CrawlOutput, AnalysisOutput, and RSSOutput dataclasses.
"""

import sys
from dataclasses import FrozenInstanceError

import pytest

from trendradar.core.types import AnalysisOutput, CrawlOutput, RSSOutput


class TestRSSOutput:
    """Test RSSOutput frozen dataclass."""

    def test_rss_output_default_creation(self):
        """Test 1: RSSOutput() creates frozen instance with None defaults."""
        rss = RSSOutput()
        assert rss.stats_items is None
        assert rss.new_items is None
        assert rss.raw_items is None

    def test_rss_output_with_data(self):
        """RSSOutput can be created with all fields populated."""
        rss = RSSOutput(stats_items=[{"x": 1}], new_items=[{"y": 2}], raw_items=[{"z": 3}])
        assert rss.stats_items == [{"x": 1}]
        assert rss.new_items == [{"y": 2}]
        assert rss.raw_items == [{"z": 3}]


class TestCrawlOutput:
    """Test CrawlOutput frozen dataclass."""

    def test_crawl_output_minimal_creation(self):
        """Test 2: CrawlOutput(results={}, id_to_name={}) creates instance with defaults."""
        crawl = CrawlOutput(results={}, id_to_name={})
        assert crawl.results == {}
        assert crawl.id_to_name == {}
        assert crawl.failed_ids == ()
        assert isinstance(crawl.rss, RSSOutput)
        assert crawl.rss.stats_items is None

    def test_crawl_output_immutability(self):
        """Test 4: Assigning to CrawlOutput.results raises FrozenInstanceError."""
        crawl = CrawlOutput(results={}, id_to_name={})

        # Python 3.11+ raises FrozenInstanceError, earlier versions raise AttributeError
        expected_error = FrozenInstanceError if sys.version_info >= (3, 11) else AttributeError

        with pytest.raises(expected_error):
            crawl.results = {"new": "value"}

    def test_crawl_output_full_population(self):
        """Test 5: CrawlOutput with all fields populated."""
        rss = RSSOutput(stats_items=[{"x": 1}], new_items=[{"y": 2}], raw_items=[{"z": 3}])
        crawl = CrawlOutput(
            results={"p1": {}}, id_to_name={"p1": "Platform1"}, failed_ids=("p2",), rss=rss
        )
        assert crawl.results == {"p1": {}}
        assert crawl.id_to_name == {"p1": "Platform1"}
        assert crawl.failed_ids == ("p2",)
        assert crawl.rss.stats_items == [{"x": 1}]
        assert crawl.rss.new_items == [{"y": 2}]
        assert crawl.rss.raw_items == [{"z": 3}]


class TestAnalysisOutput:
    """Test AnalysisOutput frozen dataclass."""

    def test_analysis_output_minimal_creation(self):
        """Test 3: AnalysisOutput(stats=[]) creates instance with None defaults."""
        analysis = AnalysisOutput(stats=[])
        assert analysis.stats == []
        assert analysis.html_file_path is None
        assert analysis.ai_result is None

    def test_analysis_output_full_population(self):
        """Test 6: AnalysisOutput with all fields populated."""
        ai_result_obj = object()
        analysis = AnalysisOutput(
            stats=[{"word": "test", "count": 1}],
            html_file_path="/tmp/report.html",
            ai_result=ai_result_obj,
        )
        assert analysis.stats == [{"word": "test", "count": 1}]
        assert analysis.html_file_path == "/tmp/report.html"
        assert analysis.ai_result is ai_result_obj

    def test_analysis_output_immutability(self):
        """AnalysisOutput is frozen and cannot be mutated."""
        analysis = AnalysisOutput(stats=[])

        expected_error = FrozenInstanceError if sys.version_info >= (3, 11) else AttributeError

        with pytest.raises(expected_error):
            analysis.stats = [{"new": "value"}]
