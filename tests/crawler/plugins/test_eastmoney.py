"""EastMoneyPlugin tests — happy path (JS wrapper) + malformed wrapper error."""
from __future__ import annotations

import responses

from tests.crawler._helpers import (
    assert_crawl_result_error,
    assert_crawl_result_success,
)
from trendradar.crawler.plugins.eastmoney import EastMoneyPlugin

# URL template with defaults: channel=102, page_size=50, page=1
_EASTMONEY_URL = (
    "https://newsapi.eastmoney.com/kuaixun/v1/getlist_102_ajaxResult_50_1_.html"
)


@responses.activate
def test_eastmoney_happy_path():
    """Mocked JS-wrapped response `var result = {...};` must parse correctly
    via _parse_response's wrapper stripping logic (Pitfall 4)."""
    wrapped_body = (
        'var result = {"rc":"1","LivesList":[{"title":"EastMoney Test","url_w":"http://e.com"}]};'
    )
    responses.add(
        responses.GET,
        _EASTMONEY_URL,
        body=wrapped_body,
        status=200,
        content_type="text/javascript",
    )
    plugin = EastMoneyPlugin()
    try:
        result = plugin.fetch({"id": "eastmoney", "name": "EastMoney"})
    finally:
        plugin.close()

    assert_crawl_result_success(result)
    assert "EastMoney Test" in result.items[0].title


@responses.activate
def test_eastmoney_malformed_wrapper():
    """Response without the `var x = {...};` format -> json.loads fails ->
    _parse_response returns [] -> fetch() returns CrawlResult with errors."""
    responses.add(
        responses.GET,
        _EASTMONEY_URL,
        body="this is not a js wrapper",
        status=200,
        content_type="text/javascript",
    )
    plugin = EastMoneyPlugin()
    try:
        result = plugin.fetch({"id": "eastmoney", "name": "EastMoney"})
    finally:
        plugin.close()

    assert_crawl_result_error(result)
