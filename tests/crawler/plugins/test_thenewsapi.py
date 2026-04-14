# coding=utf-8
"""TheNewsAPIPlugin tests — happy path + missing api_key error mode."""
from __future__ import annotations

import responses

from tests.crawler._helpers import (
    assert_crawl_result_error,
    assert_crawl_result_success,
)
from trendradar.crawler.plugins.thenewsapi import TheNewsAPIPlugin

_THENEWSAPI_URL = "https://api.thenewsapi.com/v1/news/top"


@responses.activate
def test_thenewsapi_happy_path():
    """Mocked 200 response with `data` array produces 1 FetchedItem."""
    responses.add(
        responses.GET,
        _THENEWSAPI_URL,
        json={"data": [{"title": "TNA News", "url": "http://tna.com"}]},
        status=200,
    )
    plugin = TheNewsAPIPlugin()
    try:
        result = plugin.fetch({"id": "thenewsapi", "api_key": "fake-key"})
    finally:
        plugin.close()

    assert_crawl_result_success(result)
    assert result.items[0].title == "TNA News"


@responses.activate
def test_thenewsapi_missing_api_key():
    """No api_key -> fetch() early-returns CrawlResult with errors."""
    plugin = TheNewsAPIPlugin()
    try:
        result = plugin.fetch({"id": "thenewsapi"})
    finally:
        plugin.close()

    assert_crawl_result_error(result)
