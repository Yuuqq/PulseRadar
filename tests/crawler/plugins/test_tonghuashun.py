"""TongHuaShunPlugin tests — happy path (GBK HTML) + malformed HTML error."""
from __future__ import annotations

import responses

from tests.crawler._helpers import (
    assert_crawl_result_error,
    assert_crawl_result_success,
)
from trendradar.crawler.plugins.tonghuashun import TongHuaShunPlugin

_THS_URL = "https://news.10jqka.com.cn/clientinfo/finance.html"

_HAPPY_HTML = """<html><body>
<div class="article" id="1">
  <span class="article-time">2026-04-14</span>
  <a onclick="openbrower('http://news.10jqka.com.cn/article1')">link</a>
  <strong><a href="#">THS Test News Title</a></strong>
</div>
<div class="article" id="2">
  <span class="article-time">2026-04-14</span>
  <a onclick="openbrower('http://news.10jqka.com.cn/article2')">link</a>
  <strong><a href="#">Second THS Article</a></strong>
</div>
</body></html>"""


@responses.activate
def test_tonghuashun_happy_path():
    """Mocked GBK-encoded HTML with 2 article blocks matching the plugin's
    regex extraction produces 2 FetchedItems with expected title/url pairs."""
    responses.add(
        responses.GET,
        _THS_URL,
        body=_HAPPY_HTML.encode("gbk"),
        status=200,
        content_type="text/html; charset=gbk",
    )
    plugin = TongHuaShunPlugin()
    try:
        result = plugin.fetch({"id": "10jqka", "name": "THS"})
    finally:
        plugin.close()

    assert_crawl_result_success(result, min_items=2)
    assert len(result.items) == 2
    assert result.items[0].title == "THS Test News Title"
    assert result.items[0].url == "http://news.10jqka.com.cn/article1"


@responses.activate
def test_tonghuashun_malformed_html():
    """Mocked HTML without any `<div class="article"` block -> _parse_html
    returns [] -> fetch() returns CrawlResult with errors (lock current
    behavior: the plugin surfaces this as a failure, not empty-success)."""
    responses.add(
        responses.GET,
        _THS_URL,
        body="<html><body>no data here</body></html>".encode("gbk"),
        status=200,
        content_type="text/html; charset=gbk",
    )
    plugin = TongHuaShunPlugin()
    try:
        result = plugin.fetch({"id": "10jqka", "name": "THS"})
    finally:
        plugin.close()

    assert_crawl_result_error(result)
