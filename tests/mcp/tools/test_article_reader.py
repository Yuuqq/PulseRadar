"""Handler-level tests for ArticleReaderTools.

Strategy: use `responses` to intercept Jina Reader HTTP calls so tests never
hit the network. Also stubs the internal _throttle() so tests do not sleep.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
import responses

from mcp_server.tools.article_reader import JINA_READER_BASE, ArticleReaderTools


@pytest.fixture
def tools(tmp_path):
    # Monkey-patch throttle so tests run instantly.
    with patch.object(ArticleReaderTools, "_throttle", lambda self: None):
        yield ArticleReaderTools(project_root=str(tmp_path))


@responses.activate
def test_read_article_success(tools):
    url = "http://example.com/article"
    responses.add(
        responses.GET,
        f"{JINA_READER_BASE}/{url}",
        body="# Hello\n\nMarkdown body",
        status=200,
        content_type="text/markdown",
    )

    result = tools.read_article(url=url, timeout=5)

    assert result["success"] is True
    assert result["data"]["url"] == url
    assert result["data"]["format"] == "markdown"
    assert "Hello" in result["data"]["content"]
    assert result["data"]["content_length"] == len("# Hello\n\nMarkdown body")


@responses.activate
def test_read_article_rate_limited(tools):
    url = "http://example.com/rl"
    responses.add(
        responses.GET,
        f"{JINA_READER_BASE}/{url}",
        body="rate limit",
        status=429,
    )

    result = tools.read_article(url=url, timeout=5)

    assert result["success"] is False
    assert result["error"]["code"] == "RATE_LIMITED"


def test_read_article_invalid_url_returns_invalid_parameter(tools):
    result = tools.read_article(url="not-a-url", timeout=5)

    assert result["success"] is False
    assert result["error"]["code"] == "INVALID_PARAMETER"


@responses.activate
def test_read_articles_batch_success(tools):
    urls = ["http://a.test/1", "http://a.test/2"]
    for u in urls:
        responses.add(
            responses.GET,
            f"{JINA_READER_BASE}/{u}",
            body=f"content of {u}",
            status=200,
        )

    result = tools.read_articles_batch(urls=urls, timeout=5)

    assert result["success"] is True
    assert result["summary"]["requested"] == 2
    assert result["summary"]["processed"] == 2
    assert result["summary"]["succeeded"] == 2
    assert result["summary"]["failed"] == 0
    assert len(result["articles"]) == 2


def test_read_articles_batch_empty_list_returns_error(tools):
    result = tools.read_articles_batch(urls=[], timeout=5)

    assert result["success"] is False
    assert result["error"]["code"] == "INVALID_PARAMETER"
