"""NewsAPIPlugin tests — happy path + API-level status=error response."""
from __future__ import annotations

import responses

from tests.crawler._helpers import (
    assert_crawl_result_error,
    assert_crawl_result_success,
)
from trendradar.crawler.plugins.newsapi import NewsAPIPlugin

_NEWSAPI_URL = "https://newsapi.org/v2/top-headlines"


@responses.activate
def test_newsapi_happy_path():
    """Mocked `status=ok` + articles list produces 1 FetchedItem."""
    responses.add(
        responses.GET,
        _NEWSAPI_URL,
        json={
            "status": "ok",
            "articles": [{"title": "NA News", "url": "http://na.com"}],
        },
        status=200,
    )
    plugin = NewsAPIPlugin()
    try:
        result = plugin.fetch({"id": "newsapi", "api_key": "fake-key"})
    finally:
        plugin.close()

    assert_crawl_result_success(result)
    assert result.items[0].title == "NA News"


@responses.activate
def test_newsapi_status_error():
    """Mocked API-level error: HTTP 200 but `status=error` in body.
    raise_for_status passes; status check triggers the error branch."""
    responses.add(
        responses.GET,
        _NEWSAPI_URL,
        json={"status": "error", "message": "apiKey invalid"},
        status=200,
    )
    plugin = NewsAPIPlugin()
    try:
        result = plugin.fetch({"id": "newsapi", "api_key": "fake-key"})
    finally:
        plugin.close()

    assert_crawl_result_error(result)
