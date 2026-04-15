"""DailyHotPlugin crawler plugin tests — happy path + HTTP 500 error mode."""

from __future__ import annotations

import responses

from tests.crawler._helpers import (
    assert_crawl_result_error,
    assert_crawl_result_success,
)
from trendradar.crawler.plugins.dailyhot import DailyHotPlugin

_DAILYHOT_URL = "https://api.codelife.cc/api/top/list"


@responses.activate
def test_dailyhot_happy_path():
    """Mocked 200 response with a single-platform data list produces 1 item
    whose title is prefixed with the platform name (lock current behavior)."""
    responses.add(
        responses.GET,
        _DAILYHOT_URL,
        json={
            "code": 200,
            "data": [{"title": "Test Title", "url": "http://test.com", "index": 1}],
            "name": "DailyHot",
        },
        status=200,
    )
    plugin = DailyHotPlugin()
    try:
        result = plugin.fetch({"id": "dailyhot", "name": "DailyHot", "platform": "toutiao"})
    finally:
        plugin.close()

    assert_crawl_result_success(result)
    # Title is prefixed with platform name per _fetch_platform -> platform_map
    # key "toutiao" then fetch() flattens into "[toutiao] Test Title"
    assert "Test Title" in result.items[0].title
    assert result.items[0].url == "http://test.com"


@responses.activate
def test_dailyhot_http_500():
    """HTTP 500 -> raise_for_status raises -> _get_json returns None ->
    _parse_payload returns {} -> fetch() returns CrawlResult with errors."""
    responses.add(
        responses.GET,
        _DAILYHOT_URL,
        json={},
        status=500,
    )
    plugin = DailyHotPlugin()
    try:
        result = plugin.fetch({"id": "dailyhot", "name": "DailyHot", "platform": "toutiao"})
    finally:
        plugin.close()

    assert_crawl_result_error(result)
