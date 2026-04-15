"""Handler-level tests for StorageSyncTools.

Strategy: use tmp_path for local storage (no real I/O to user's machine).
Remote/S3 paths are tested only for the 'unconfigured' branches so boto3 is
never required.
"""
from __future__ import annotations

from pathlib import Path

import yaml

from mcp_server.tools.storage_sync import StorageSyncTools


def _write_minimal_config(tmp_path: Path, include_remote: bool = False) -> None:
    """Write a minimal config.yaml into tmp_path/config/."""
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    config: dict = {
        "app": {"timezone": "UTC"},
        "storage": {
            "backend": "local",
            "local": {"data_dir": "output", "retention_days": 0},
            "pull": {"enabled": False, "days": 7},
        },
    }
    if include_remote:
        # Intentionally incomplete — _has_remote_config() must return False.
        config["storage"]["remote"] = {}
    (config_dir / "config.yaml").write_text(
        yaml.safe_dump(config), encoding="utf-8"
    )


def test_sync_from_remote_without_config_returns_error(tmp_path, monkeypatch):
    # Ensure env does not accidentally supply S3 creds.
    for var in [
        "S3_ENDPOINT_URL", "S3_BUCKET_NAME", "S3_ACCESS_KEY_ID",
        "S3_SECRET_ACCESS_KEY", "S3_REGION",
    ]:
        monkeypatch.delenv(var, raising=False)

    _write_minimal_config(tmp_path, include_remote=False)
    tools = StorageSyncTools(project_root=str(tmp_path))

    result = tools.sync_from_remote(days=7)

    assert result["success"] is False
    assert result["error"]["code"] == "REMOTE_NOT_CONFIGURED"


def test_get_storage_status_local_only(tmp_path, monkeypatch):
    for var in [
        "S3_ENDPOINT_URL", "S3_BUCKET_NAME", "S3_ACCESS_KEY_ID",
        "S3_SECRET_ACCESS_KEY", "S3_REGION",
    ]:
        monkeypatch.delenv(var, raising=False)

    _write_minimal_config(tmp_path, include_remote=False)

    # Create a fake news database file so _get_local_dates finds a date.
    news_dir = tmp_path / "output" / "news"
    news_dir.mkdir(parents=True)
    (news_dir / "2025-12-30.db").write_bytes(b"")  # empty file, just needs to exist

    tools = StorageSyncTools(project_root=str(tmp_path))

    result = tools.get_storage_status()

    assert result["success"] is True
    assert result["data"]["local"]["date_count"] >= 1
    assert "2025-12-30" in result["data"]["local"]["news"]["dates"]
    assert result["data"]["remote"]["configured"] is False


def test_list_available_dates_local_source(tmp_path, monkeypatch):
    for var in [
        "S3_ENDPOINT_URL", "S3_BUCKET_NAME", "S3_ACCESS_KEY_ID",
        "S3_SECRET_ACCESS_KEY", "S3_REGION",
    ]:
        monkeypatch.delenv(var, raising=False)

    _write_minimal_config(tmp_path, include_remote=False)

    rss_dir = tmp_path / "output" / "rss"
    rss_dir.mkdir(parents=True)
    (rss_dir / "2025-01-05.db").write_bytes(b"")

    tools = StorageSyncTools(project_root=str(tmp_path))

    result = tools.list_available_dates(source="local")

    assert result["success"] is True
    assert "2025-01-05" in result["data"]["local"]["rss"]["dates"]
    assert result["data"]["local"]["rss"]["count"] == 1


def test_parse_date_folder_name_supports_iso_and_chinese(tmp_path):
    tools = StorageSyncTools(project_root=str(tmp_path))

    iso = tools._parse_date_folder_name("2025-12-30")
    chinese = tools._parse_date_folder_name("2025年12月30日")
    invalid = tools._parse_date_folder_name("not-a-date")

    assert iso is not None and iso.year == 2025 and iso.month == 12 and iso.day == 30
    assert chinese is not None and chinese.year == 2025
    assert invalid is None
