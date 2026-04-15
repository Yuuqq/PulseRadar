"""GNewsPlugin tests — happy path + missing api_key error mode."""

from __future__ import annotations

import responses

from tests.crawler._helpers import (
    assert_crawl_result_error,
    assert_crawl_result_success,
)
from trendradar.crawler.plugins.gnews import GNewsPlugin

_GNEWS_URL = "https://gnews.io/api/v4/top-headlines"


@responses.activate
def test_gnews_happy_path():
    """Mocked 200 response with `articles` array produces 1 FetchedItem whose
    title matches the response article title."""
    responses.add(
        responses.GET,
        _GNEWS_URL,
        json={"articles": [{"title": "Test News", "url": "https://example.com"}]},
        status=200,
    )
    plugin = GNewsPlugin()
    try:
        result = plugin.fetch({"id": "gnews", "api_key": "fake-key"})
    finally:
        plugin.close()

    assert_crawl_result_success(result)
    assert result.items[0].title == "Test News"
    assert result.items[0].url == "https://example.com"


@responses.activate
def test_gnews_missing_api_key():
    """No api_key in source_config -> fetch() early-returns CrawlResult with
    errors BEFORE any HTTP call (no URL registration needed)."""
    plugin = GNewsPlugin()
    try:
        result = plugin.fetch({"id": "gnews"})
    finally:
        plugin.close()

    assert_crawl_result_error(result)
