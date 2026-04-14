# coding=utf-8
"""Unit tests for mcp_server.services.parser_service.ParserService.

Strategy: create a minimal SQLite database in tmp_path that matches the
trendradar news schema (schema.sql), then exercise ParserService against it.
No external I/O, no network.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

import pytest

from mcp_server.services.cache_service import CacheService
from mcp_server.services.parser_service import ParserService
from mcp_server.utils.errors import DataNotFoundError, FileParseError


def _create_news_db(db_path: Path) -> None:
    """Create a minimal news SQLite DB matching trendradar/storage/schema.sql."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE platforms (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE news_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            platform_id TEXT NOT NULL,
            rank INTEGER NOT NULL,
            url TEXT DEFAULT '',
            mobile_url TEXT DEFAULT '',
            first_crawl_time TEXT NOT NULL,
            last_crawl_time TEXT NOT NULL,
            crawl_count INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE rank_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            news_item_id INTEGER NOT NULL,
            rank INTEGER NOT NULL,
            crawl_time TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE crawl_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            crawl_time TEXT NOT NULL UNIQUE,
            total_items INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    cur.execute(
        "INSERT INTO platforms (id, name) VALUES (?, ?)",
        ("zhihu", "Zhihu"),
    )
    cur.execute(
        """
        INSERT INTO news_items
          (title, platform_id, rank, url, mobile_url,
           first_crawl_time, last_crawl_time, crawl_count)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ("Test Headline", "zhihu", 1, "http://example.com/1", "",
         "2025-01-01 00:00:00", "2025-01-01 00:10:00", 2),
    )
    news_id = cur.lastrowid
    cur.execute(
        "INSERT INTO rank_history (news_item_id, rank, crawl_time) VALUES (?, ?, ?)",
        (news_id, 1, "2025-01-01 00:00:00"),
    )
    cur.execute(
        "INSERT INTO rank_history (news_item_id, rank, crawl_time) VALUES (?, ?, ?)",
        (news_id, 2, "2025-01-01 00:10:00"),
    )
    cur.execute(
        """
        INSERT INTO crawl_records (crawl_time, total_items, created_at)
        VALUES (?, ?, ?)
        """,
        ("2025-01-01 00:00:00", 1, "2025-01-01 00:00:00"),
    )
    conn.commit()
    conn.close()


@pytest.fixture
def fresh_cache(monkeypatch):
    cache = CacheService()
    monkeypatch.setattr(
        "mcp_server.services.parser_service.get_cache", lambda: cache
    )
    return cache


@pytest.fixture
def service_with_data(tmp_path, fresh_cache):
    """ParserService pointed at tmp_path with a populated 2025-01-01 news DB."""
    db_path = tmp_path / "output" / "news" / "2025-01-01.db"
    _create_news_db(db_path)
    return ParserService(project_root=str(tmp_path))


def test_clean_title_collapses_whitespace():
    assert ParserService.clean_title("  hello   world  ") == "hello world"


def test_get_date_folder_name_defaults_to_today():
    svc = ParserService(project_root=".")
    name = svc.get_date_folder_name()
    # YYYY-MM-DD format
    assert len(name) == 10
    assert name[4] == "-" and name[7] == "-"


def test_get_date_folder_name_with_explicit_date():
    svc = ParserService(project_root=".")
    assert svc.get_date_folder_name(datetime(2025, 6, 15)) == "2025-06-15"


def test_read_all_titles_for_date_returns_expected_shape(service_with_data):
    target = datetime(2025, 1, 1)

    all_titles, id_to_name, timestamps = service_with_data.read_all_titles_for_date(
        date=target, platform_ids=None, db_type="news"
    )

    assert "zhihu" in all_titles
    assert "Test Headline" in all_titles["zhihu"]
    info = all_titles["zhihu"]["Test Headline"]
    assert info["ranks"] == [1, 2]
    assert info["url"] == "http://example.com/1"
    assert info["count"] == 2
    assert id_to_name["zhihu"] == "Zhihu"
    assert len(timestamps) >= 1


def test_read_all_titles_for_missing_date_raises(service_with_data):
    with pytest.raises(DataNotFoundError):
        service_with_data.read_all_titles_for_date(
            date=datetime(2099, 12, 31), platform_ids=None, db_type="news"
        )


def test_read_all_titles_filters_by_platform(service_with_data):
    target = datetime(2025, 1, 1)

    # Passing a non-matching platform returns no data -> DataNotFoundError
    with pytest.raises(DataNotFoundError):
        service_with_data.read_all_titles_for_date(
            date=target, platform_ids=["nonexistent"], db_type="news"
        )


def test_read_all_titles_uses_cache(service_with_data, fresh_cache):
    target = datetime(2025, 1, 1)
    service_with_data.read_all_titles_for_date(date=target)
    # After first call, cache must hold an entry.
    assert len(fresh_cache._cache) >= 1


def test_parse_yaml_config_raises_on_missing_file(tmp_path, fresh_cache):
    svc = ParserService(project_root=str(tmp_path))
    with pytest.raises(FileParseError):
        svc.parse_yaml_config()


def test_parse_yaml_config_reads_valid_file(tmp_path, fresh_cache):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "config.yaml").write_text(
        "timezone: UTC\nplatforms: []\n", encoding="utf-8"
    )
    svc = ParserService(project_root=str(tmp_path))

    data = svc.parse_yaml_config()

    assert data["timezone"] == "UTC"
    assert data["platforms"] == []


def test_get_available_dates_returns_sorted_descending(service_with_data, tmp_path):
    # Add a second DB file so we exercise sorting.
    _create_news_db(tmp_path / "output" / "news" / "2024-12-31.db")

    dates = service_with_data.get_available_dates(db_type="news")

    assert dates == ["2025-01-01", "2024-12-31"]


def test_get_available_dates_empty_when_dir_missing(tmp_path, fresh_cache):
    svc = ParserService(project_root=str(tmp_path))
    assert svc.get_available_dates(db_type="news") == []
