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


def _manager(tmp_path, monkeypatch):
    from trendradar.webui.job_manager import JobManager

    monkeypatch.setattr(JobManager, "_start_dispatcher", lambda self: None)
    output_dir = tmp_path / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    config_file = tmp_path / "config.yaml"
    config_file.write_text("app:\n  timezone: Asia/Shanghai\n", encoding="utf-8")
    return JobManager(root_dir=Path.cwd(), output_dir=output_dir, config_file=config_file)


def test_get_legacy_status_does_not_return_another_jobs_state(tmp_path, monkeypatch):
    manager = _manager(tmp_path, monkeypatch)
    other = manager.create_job(["python", "-V"])
    manager._update_job(
        other["id"], status="running", stage="crawl", started_at="2026-01-01T00:00:00Z"
    )

    status = manager.get_legacy_status("missing-job-id")

    assert status["job_id"] == "missing-job-id"
    assert status["status"] is None
    assert status["running"] is False
    assert status["log"] == []


def test_start_job_does_not_resurrect_a_cancelled_queued_job(tmp_path, monkeypatch):
    manager = _manager(tmp_path, monkeypatch)
    job = manager.create_job(["python", "-V"])

    # Dispatcher read the queued row, then cancel wins the race.
    assert manager.cancel_job(job["id"]) is True
    manager._start_job(job["id"], job["command"])

    assert manager.get_job(job["id"])["status"] == "cancelled"


def test_cancel_job_returns_false_when_dispatcher_claimed_the_job(tmp_path, monkeypatch):
    manager = _manager(tmp_path, monkeypatch)
    job = manager.create_job(["python", "-V"])
    manager._update_job(
        job["id"], status="running", stage="starting", started_at="2026-01-01T00:00:00Z"
    )
    # Simulate cancel losing to the dispatcher's compare-and-set.
    claimed = manager._update_job(
        job["id"], status="running", error="", expected_statuses=("queued",)
    )
    assert claimed is False


def test_runner_does_not_overwrite_a_cancelled_job(tmp_path, monkeypatch):
    manager = _manager(tmp_path, monkeypatch)
    job = manager.create_job(["python", "-V"])
    manager._update_job(
        job["id"], status="running", stage="starting", started_at="2026-01-01T00:00:00Z"
    )
    manager._update_job(
        job["id"], status="cancelled", stage="cancelled", finished_at="2026-01-01T00:00:05Z"
    )

    written = manager._update_job(
        job["id"],
        status="success",
        stage="finished",
        expected_statuses=("running", "cancelling"),
    )

    assert written is False
    assert manager.get_job(job["id"])["status"] == "cancelled"


def test_update_job_returns_true_on_matching_transition(tmp_path, monkeypatch):
    manager = _manager(tmp_path, monkeypatch)
    job = manager.create_job(["python", "-V"])

    assert manager._update_job(job["id"], status="running", expected_statuses=("queued",)) is True


def test_cancel_job_is_idempotent_while_cancelling(tmp_path, monkeypatch):
    manager = _manager(tmp_path, monkeypatch)
    job = manager.create_job(["python", "-V"])
    manager._update_job(
        job["id"], status="cancelling", stage="cancelling", started_at="2026-01-01T00:00:00Z"
    )

    assert manager.cancel_job(job["id"]) is True
    assert manager.get_job(job["id"])["status"] == "cancelled"
