"""原子写入的契约测试。

覆盖三类场景：
1. 正常写入与覆盖；
2. 写入失败时不得破坏已有文件（这条是本次改造的核心目的——
   此前 open(path, "w") 在中途失败会留下截断文件）；
3. Windows 上 os.replace 的瞬时占用可被重试吸收，持续性失败仍抛出。
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from trendradar.report.manifest import add_report_entry, load_manifest, save_manifest
from trendradar.storage.atomic import write_lines_atomic, write_text_atomic


def test_writes_and_overwrites(tmp_path: Path) -> None:
    target = tmp_path / "report.html"
    write_text_atomic(target, "<html>1</html>")
    assert target.read_text(encoding="utf-8") == "<html>1</html>"

    write_text_atomic(target, "<html>2</html>")
    assert target.read_text(encoding="utf-8") == "<html>2</html>"


def test_creates_parent_directories(tmp_path: Path) -> None:
    target = tmp_path / "a" / "b" / "c.txt"
    write_text_atomic(target, "x")
    assert target.read_text(encoding="utf-8") == "x"


def test_failed_write_preserves_previous_content(tmp_path: Path, monkeypatch) -> None:
    """A crash mid-write must leave the last good file intact.

    This is the behaviour the plain `open(path, "w")` writers lacked: they
    truncate on open, so any failure leaves a half-written report that the
    downstream "file exists" check accepts as complete.
    """
    target = tmp_path / "report.html"
    write_text_atomic(target, "GOOD")

    def exploding_body(handle):
        handle.write("PARTIAL")
        raise RuntimeError("disk full")

    with pytest.raises(RuntimeError):
        write_lines_atomic(target, exploding_body)

    assert target.read_text(encoding="utf-8") == "GOOD"


def test_leaves_no_temp_files(tmp_path: Path) -> None:
    target = tmp_path / "x.html"
    write_text_atomic(target, "x")
    assert [p.name for p in tmp_path.iterdir() if p.name.endswith(".tmp")] == []


def test_temp_cleaned_up_on_failure(tmp_path: Path) -> None:
    target = tmp_path / "x.html"

    def exploding_body(handle):
        handle.write("partial")
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        write_lines_atomic(target, exploding_body)

    assert [p.name for p in tmp_path.iterdir() if p.name.endswith(".tmp")] == []


def test_retries_transient_permission_error(tmp_path: Path, monkeypatch) -> None:
    import trendradar.storage.atomic as atomic_mod

    calls = {"n": 0}
    real_replace = os.replace

    def flaky_replace(src, dst):
        calls["n"] += 1
        if calls["n"] == 1:
            raise PermissionError(13, "held by another process", str(dst))
        return real_replace(src, dst)

    monkeypatch.setattr(atomic_mod.os, "replace", flaky_replace)
    target = tmp_path / "out.txt"
    write_text_atomic(target, "retried")

    assert calls["n"] == 2
    assert target.read_text(encoding="utf-8") == "retried"


def test_surfaces_persistent_permission_error(tmp_path: Path, monkeypatch) -> None:
    import trendradar.storage.atomic as atomic_mod

    def always_denied(src, dst):
        raise PermissionError(13, "denied", str(dst))

    monkeypatch.setattr(atomic_mod.os, "replace", always_denied)
    with pytest.raises(PermissionError):
        write_text_atomic(tmp_path / "out.txt", "nope")


class TestManifestRoundTrip:
    def test_save_and_load(self, tmp_path: Path) -> None:
        path = tmp_path / "manifest.json"
        data = {"version": 1, "generated_at": "2026-10-21", "reports": [{"path": "a.html"}]}
        save_manifest(path, data)
        assert load_manifest(path) == data

    def test_written_json_is_utf8_not_escaped(self, tmp_path: Path) -> None:
        path = tmp_path / "manifest.json"
        save_manifest(path, {"reports": [{"title": "中文报告"}]})
        assert "中文报告" in path.read_text(encoding="utf-8")

    def test_missing_manifest_returns_empty_structure(self, tmp_path: Path) -> None:
        assert load_manifest(tmp_path / "nope.json") == {
            "version": 1,
            "generated_at": "",
            "reports": [],
        }

    def test_add_entry_dedupes_by_path(self) -> None:
        manifest = {"version": 1, "reports": [{"path": "a.html", "n": 1}]}
        updated = add_report_entry(manifest, {"path": "a.html", "n": 2})
        assert len(updated["reports"]) == 1
        assert updated["reports"][0]["n"] == 2
