# coding=utf-8

from __future__ import annotations

from pathlib import Path

import pytest


def test_recover_stale_active_jobs_marks_orphan_running(tmp_path, monkeypatch):
    from trendradar.webui.job_manager import JobManager

    monkeypatch.setattr(JobManager, "_start_dispatcher", lambda self: None)

    root_dir = Path.cwd()
    output_dir = tmp_path / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    config_file = tmp_path / "config.yaml"
    config_file.write_text("app:\n  timezone: Asia/Shanghai\n", encoding="utf-8")

    manager = JobManager(root_dir=root_dir, output_dir=output_dir, config_file=config_file)

    # Create a running job and force it stale.
    job = manager.create_job(["python", "-V"])
    job_id = job["id"]
    manager._update_job(
        job_id,
        status="running",
        stage="starting",
        started_at="2000-01-01T00:00:00Z",
    )
    with manager._connect() as conn:
        conn.execute(
            "UPDATE jobs SET updated_at = ? WHERE id = ?",
            ("2000-01-01T00:00:00Z", job_id),
        )

    recovered = manager._recover_stale_active_jobs(stale_seconds=1)
    assert recovered >= 1

    fresh = manager.get_job(job_id)
    assert fresh is not None
    assert fresh["status"] == "failed"
    assert fresh["finished_at"]
    assert fresh["exit_code"] == -999
    assert "Recovered stale active job" in (fresh.get("error") or "")

    logs = manager.get_job_logs(job_id)
    assert any("recovered stale active job" in line for line in logs)


def test_recover_stale_active_jobs_skips_live_process(tmp_path, monkeypatch):
    from trendradar.webui.job_manager import JobManager

    monkeypatch.setattr(JobManager, "_start_dispatcher", lambda self: None)

    class _LiveProcess:
        def poll(self):
            return None

    root_dir = Path.cwd()
    output_dir = tmp_path / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    config_file = tmp_path / "config.yaml"
    config_file.write_text("app:\n  timezone: Asia/Shanghai\n", encoding="utf-8")

    manager = JobManager(root_dir=root_dir, output_dir=output_dir, config_file=config_file)

    job = manager.create_job(["python", "-V"])
    job_id = job["id"]
    manager._update_job(
        job_id,
        status="running",
        stage="starting",
        started_at="2000-01-01T00:00:00Z",
    )
    with manager._connect() as conn:
        conn.execute(
            "UPDATE jobs SET updated_at = ? WHERE id = ?",
            ("2000-01-01T00:00:00Z", job_id),
        )

    with manager._lock:
        manager._processes[job_id] = _LiveProcess()

    recovered = manager._recover_stale_active_jobs(stale_seconds=1)
    assert recovered == 0

    fresh = manager.get_job(job_id)
    assert fresh is not None
    assert fresh["status"] == "running"


def test_update_job_rejects_unknown_fields(tmp_path, monkeypatch):
    from trendradar.webui.job_manager import JobManager

    monkeypatch.setattr(JobManager, "_start_dispatcher", lambda self: None)

    root_dir = Path.cwd()
    output_dir = tmp_path / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    config_file = tmp_path / "config.yaml"
    config_file.write_text("app:\n  timezone: Asia/Shanghai\n", encoding="utf-8")

    manager = JobManager(root_dir=root_dir, output_dir=output_dir, config_file=config_file)
    job = manager.create_job(["python", "-V"])

    with pytest.raises(ValueError, match="Unsupported job fields"):
        manager._update_job(job["id"], bad_field="oops")
