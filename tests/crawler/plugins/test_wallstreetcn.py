"""WallStreetCNPlugin tests — happy path + non-20000 code error mode."""
from __future__ import annotations

import responses

from tests.crawler._helpers import (
    assert_crawl_result_error,
    assert_crawl_result_success,
)
from trendradar.crawler.plugins.wallstreetcn import WallStreetCNPlugin

_WSC_URL = "https://api-prod.wallstreetcn.com/apiv1/content/lives"


@responses.activate
def test_wallstreetcn_happy_path():
    """Mocked `code=20000` response with a single live item produces 1
    FetchedItem whose URL is built from the item's `id` field."""
    responses.add(
        responses.GET,
        _WSC_URL,
        json={
            "code": 20000,
            "data": {
                "items": [
                    {
                        "title": "WSC",
                        "content_text": "body",
                        "id": 12345,
                        "display_time": 1700000000,
                    }
                ]
            },
        },
        status=200,
    )
    plugin = WallStreetCNPlugin()
    try:
        result = plugin.fetch({"id": "wallstreetcn", "name": "WallStreetCN"})
    finally:
        plugin.close()

    assert_crawl_result_success(result)
    assert result.items[0].title == "WSC"
    # URL is built from item['id'] per _parse_items
    assert "12345" in result.items[0].url


@responses.activate
def test_wallstreetcn_code_40000():
    """API-level error: HTTP 200 but `code=40000` triggers the error branch."""
    responses.add(
        responses.GET,
        _WSC_URL,
        json={"code": 40000, "message": "forbidden"},
        status=200,
    )
    plugin = WallStreetCNPlugin()
    try:
        result = plugin.fetch({"id": "wallstreetcn", "name": "WallStreetCN"})
    finally:
        plugin.close()

    assert_crawl_result_error(result)
