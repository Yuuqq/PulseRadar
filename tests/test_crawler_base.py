# coding=utf-8

from __future__ import annotations

from datetime import datetime


def test_fetched_item_creation():
    from trendradar.crawler.base import FetchedItem

    item = FetchedItem(title="Test Title", url="http://example.com", rank=1)
    assert item.title == "Test Title"
    assert item.url == "http://example.com"
    assert item.rank == 1


def test_fetched_item_defaults():
    from trendradar.crawler.base import FetchedItem

    item = FetchedItem(title="Only Title")
    assert item.url == ""
    assert item.mobile_url == ""
    assert item.rank == 0


def test_fetched_item_frozen_immutability():
    from trendradar.crawler.base import FetchedItem
    import pytest

    item = FetchedItem(title="Frozen", url="http://x.com", rank=5)
    with pytest.raises(AttributeError):
        item.title = "Modified"
    with pytest.raises(AttributeError):
        item.rank = 99


def test_crawl_result_success_with_items_and_no_errors():
    from trendradar.crawler.base import CrawlResult, FetchedItem

    result = CrawlResult(
        source_id="src1",
        source_name="Source 1",
        items=(FetchedItem(title="A", url="http://a.com", rank=1),),
        fetched_at=datetime.now(),
    )
    assert result.success is True


def test_crawl_result_failure_when_empty_items():
    from trendradar.crawler.base import CrawlResult

    result = CrawlResult(
        source_id="src1",
        source_name="Source 1",
        items=(),
        fetched_at=datetime.now(),
    )
    assert result.success is False


def test_crawl_result_failure_when_has_errors():
    from trendradar.crawler.base import CrawlResult, FetchedItem

    result = CrawlResult(
        source_id="src1",
        source_name="Source 1",
        items=(FetchedItem(title="A"),),
        fetched_at=datetime.now(),
        errors=("something went wrong",),
    )
    assert result.success is False


def test_crawl_result_failure_when_both_empty_and_errors():
    from trendradar.crawler.base import CrawlResult

    result = CrawlResult(
        source_id="src1",
        source_name="Source 1",
        items=(),
        fetched_at=datetime.now(),
        errors=("timeout",),
    )
    assert result.success is False


def test_crawl_result_frozen_immutability():
    from trendradar.crawler.base import CrawlResult, FetchedItem
    import pytest

    result = CrawlResult(
        source_id="src1",
        source_name="Source 1",
        items=(FetchedItem(title="A"),),
        fetched_at=datetime.now(),
    )
    with pytest.raises(AttributeError):
        result.source_id = "modified"
