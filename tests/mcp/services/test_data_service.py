"""Unit tests for mcp_server.services.data_service.DataService.

Strategy: patch ParserService to avoid SQLite/file I/O. Each test exercises a
public method and asserts on the return shape or cache behaviour.
"""
from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from mcp_server.services.cache_service import CacheService
from mcp_server.services.data_service import DataService
from mcp_server.utils.errors import DataNotFoundError


@pytest.fixture
def fresh_cache(monkeypatch):
    """Force DataService to use a fresh, isolated CacheService instance.

    The module-level get_cache() singleton is replaced so test state does not
    leak through subsequent test runs.
    """
    cache = CacheService()
    monkeypatch.setattr(
        "mcp_server.services.data_service.get_cache", lambda: cache
    )
    return cache


@pytest.fixture
def service(tmp_path, fresh_cache):
    """DataService with a patched ParserService that returns no data by default."""
    with patch("mcp_server.services.data_service.ParserService") as mock_parser_cls:
        mock_parser = MagicMock()
        mock_parser_cls.return_value = mock_parser
        svc = DataService(project_root=str(tmp_path))
        svc.parser = mock_parser  # belt-and-braces: reference the same instance
        yield svc


def test_get_latest_news_returns_sorted_list(service):
    service.parser.read_all_titles_for_date.return_value = (
        {
            "zhihu": {
                "Title A": {"ranks": [2], "url": "http://a", "mobileUrl": ""},
                "Title B": {"ranks": [1], "url": "http://b", "mobileUrl": ""},
            }
        },
        {"zhihu": "Zhihu"},
        {},
    )

    result = service.get_latest_news(platforms=["zhihu"], limit=10)

    assert isinstance(result, list)
    assert len(result) == 2
    # Sorted ascending by rank -> Title B (rank 1) comes first
    assert result[0]["title"] == "Title B"
    assert result[0]["rank"] == 1
    assert result[1]["rank"] == 2


def test_get_latest_news_respects_limit(service):
    service.parser.read_all_titles_for_date.return_value = (
        {
            "zhihu": {
                f"T{i}": {"ranks": [i], "url": "", "mobileUrl": ""}
                for i in range(1, 6)
            }
        },
        {"zhihu": "Zhihu"},
        {},
    )

    result = service.get_latest_news(platforms=None, limit=3)

    assert len(result) == 3


def test_get_latest_news_uses_cache_on_repeat_call(service):
    service.parser.read_all_titles_for_date.return_value = (
        {"zhihu": {"T": {"ranks": [1], "url": "", "mobileUrl": ""}}},
        {"zhihu": "Zhihu"},
        {},
    )

    service.get_latest_news(platforms=None, limit=10)
    service.get_latest_news(platforms=None, limit=10)

    # Parser should have been called exactly once — second call is cache-hit.
    assert service.parser.read_all_titles_for_date.call_count == 1


def test_search_news_by_keyword_raises_when_no_matches(service):
    # Parser returns empty titles -> no matches -> DataNotFoundError
    service.parser.read_all_titles_for_date.return_value = ({}, {}, {})

    with pytest.raises(DataNotFoundError):
        service.search_news_by_keyword(keyword="nothing")


def test_search_news_by_keyword_finds_matches(service):
    service.parser.read_all_titles_for_date.return_value = (
        {
            "zhihu": {
                "AI breakthrough in 2025": {
                    "ranks": [1], "url": "http://a", "mobileUrl": ""
                },
                "Unrelated news": {
                    "ranks": [5], "url": "http://b", "mobileUrl": ""
                },
            }
        },
        {"zhihu": "Zhihu"},
        {},
    )

    result = service.search_news_by_keyword(keyword="AI")

    assert result["total"] == 1
    assert result["results"][0]["title"].startswith("AI")
    assert result["statistics"]["platform_distribution"] == {"zhihu": 1}


def test_extract_words_from_title_filters_stopwords(service):
    words = service._extract_words_from_title("AI技术 重磅 人工智能发展")

    # Stopwords "重磅" must be filtered out
    assert "重磅" not in words
    # Meaningful tokens survive
    assert any("AI" in w or len(w) >= 2 for w in words)


def test_get_available_date_range_empty_when_no_output(service, tmp_path):
    # project_root/output does not exist
    service.parser.project_root = tmp_path  # type: ignore[attr-defined]
    earliest, latest = service.get_available_date_range()
    assert earliest is None
    assert latest is None


def test_parse_date_folder_name_supports_iso_and_chinese(service):
    iso = service._parse_date_folder_name("2025-10-11")
    chinese = service._parse_date_folder_name("2025年10月11日")
    bad = service._parse_date_folder_name("not-a-date")

    assert iso == datetime(2025, 10, 11)
    assert chinese == datetime(2025, 10, 11)
    assert bad is None
