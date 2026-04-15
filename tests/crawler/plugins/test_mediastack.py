"""MediaStackPlugin tests — happy path + HTTP 500 error mode."""
from __future__ import annotations

import responses

from tests.crawler._helpers import (
    assert_crawl_result_error,
    assert_crawl_result_success,
)
from trendradar.crawler.plugins.mediastack import MediaStackPlugin

_MEDIASTACK_URL = "http://api.mediastack.com/v1/news"


@responses.activate
def test_mediastack_happy_path():
    """Mocked 200 response with `data` array produces 1 FetchedItem."""
    responses.add(
        responses.GET,
        _MEDIASTACK_URL,
        json={"data": [{"title": "MS News", "url": "http://ms.com"}]},
        status=200,
    )
    plugin = MediaStackPlugin()
    try:
        result = plugin.fetch({"id": "mediastack", "api_key": "fake-key"})
    finally:
        plugin.close()

    assert_crawl_result_success(result)
    assert result.items[0].title == "MS News"


@responses.activate
def test_mediastack_http_500():
    """HTTP 500 -> raise_for_status raises -> fetch() returns errors tuple."""
    responses.add(
        responses.GET,
        _MEDIASTACK_URL,
        json={},
        status=500,
    )
    plugin = MediaStackPlugin()
    try:
        result = plugin.fetch({"id": "mediastack", "api_key": "fake-key"})
    finally:
        plugin.close()

    assert_crawl_result_error(result)
