"""VvhanPlugin tests — happy path (all-platforms) + empty data error mode."""
from __future__ import annotations

import responses

from tests.crawler._helpers import (
    assert_crawl_result_error,
    assert_crawl_result_success,
)
from trendradar.crawler.plugins.vvhan import VvhanPlugin

_VVHAN_ALL_URL = "https://api.vvhan.com/api/hotlist/all"


@responses.activate
def test_vvhan_happy_path():
    """Mocked 200 response where `data` is a dict {platform: [items]} -> the
    plugin flattens all platforms into one CrawlResult with prefixed titles."""
    responses.add(
        responses.GET,
        _VVHAN_ALL_URL,
        json={
            "success": True,
            "data": {
                "PlatformA": [
                    {"title": "VVH News", "url": "http://vvh.com"},
                ]
            },
        },
        status=200,
    )
    plugin = VvhanPlugin()
    try:
        result = plugin.fetch({"id": "vvhan", "name": "Vvhan", "platform": "all"})
    finally:
        plugin.close()

    assert_crawl_result_success(result)
    # Title prefixed with platform name per _fetch_all flattening
    assert "VVH News" in result.items[0].title
    assert result.items[0].url == "http://vvh.com"


@responses.activate
def test_vvhan_empty_data():
    """Empty `data` dict -> platform_map is {} -> all_items is empty ->
    fetch() returns CrawlResult with errors (lock current behavior: empty
    result is surfaced as a failure, NOT an empty-success)."""
    responses.add(
        responses.GET,
        _VVHAN_ALL_URL,
        json={"success": True, "data": {}},
        status=200,
    )
    plugin = VvhanPlugin()
    try:
        result = plugin.fetch({"id": "vvhan", "name": "Vvhan", "platform": "all"})
    finally:
        plugin.close()

    assert_crawl_result_error(result)
