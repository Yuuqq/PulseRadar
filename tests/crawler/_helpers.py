"""Shared assertion helpers for crawler plugin tests (Plan 02-03 / D-23)."""

from __future__ import annotations

from trendradar.crawler.base import CrawlResult, FetchedItem


def assert_fetched_item_shape(item: FetchedItem) -> None:
    """Assert a FetchedItem has the expected field types and a non-empty title."""
    assert isinstance(item, FetchedItem), f"not a FetchedItem: {type(item)!r}"
    assert isinstance(item.title, str) and len(item.title) > 0, "title must be non-empty str"
    assert isinstance(item.url, str), "url must be str"
    assert isinstance(item.rank, int), "rank must be int"


def assert_crawl_result_success(result: CrawlResult, min_items: int = 1) -> None:
    """Assert a CrawlResult represents a successful crawl with >= min_items items."""
    assert result.success, f"expected success but got errors: {result.errors}"
    assert len(result.items) >= min_items, f"expected >={min_items} items, got {len(result.items)}"
    for item in result.items:
        assert_fetched_item_shape(item)


def assert_crawl_result_error(result: CrawlResult) -> None:
    """Assert a CrawlResult represents a failed crawl (no items, >=1 error msg)."""
    assert not result.success, "expected failure but crawl was successful"
    assert len(result.errors) > 0, "expected >=1 error message"
    assert len(result.items) == 0, f"expected empty items on failure, got {len(result.items)}"
