from __future__ import annotations

import json
from pathlib import Path

import pytest

from trendradar.webui.app import create_app
from trendradar.webui.job_manager import JobManager


@pytest.fixture()
def webui_client(tmp_path: Path, monkeypatch):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
platforms:
  enabled: true
  sources: []
rss:
  enabled: false
  feeds: []
extra_apis:
  enabled: false
  sources: []
""".strip()
        + "\n",
        encoding="utf-8",
    )

    output_dir = tmp_path / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(JobManager, "_start_dispatcher", lambda self: None)

    app = create_app(config_path=str(config_file), output_path=str(output_dir))
    app.config["TESTING"] = True
    client = app.test_client()

    manager = app.extensions["trendradar_job_manager"]
    manager._dispatcher_started = True

    return client, manager


def test_run_enqueues_job_and_status_supports_job_id(webui_client):
    client, manager = webui_client

    response = client.post("/api/run")
    assert response.status_code == 200

    payload = response.get_json()
    assert payload["success"] is True
    job_id = payload["job_id"]
    assert job_id

    job = manager.get_job(job_id)
    assert job is not None
    assert job["status"] == "queued"

    status_response = client.get(f"/api/status?job_id={job_id}")
    assert status_response.status_code == 200
    status_payload = status_response.get_json()
    assert status_payload["job_id"] == job_id
    assert status_payload["running"] is True


def test_run_supports_scoped_payload_and_force_flags(webui_client):
    client, manager = webui_client

    response = client.post(
        "/api/run",
        json={
            "scope": "rss",
            "force_ai": True,
            "force_push": True,
        },
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["scope"] == "rss"

    command = payload.get("command") or []
    assert "--config" in command
    assert "--force-ai" in command
    assert "--force-push" in command

    config_index = command.index("--config") + 1
    assert config_index < len(command)
    temp_config = Path(command[config_index])
    assert temp_config.exists()

    scoped_text = temp_config.read_text(encoding="utf-8")
    assert "rss:" in scoped_text
    assert "enabled: true" in scoped_text

    job = manager.get_job(payload["job_id"])
    assert job is not None
    assert job["status"] == "queued"


def test_job_detail_logs_and_cancel_flow(webui_client):
    client, manager = webui_client

    run_payload = client.post("/api/run").get_json()
    job_id = run_payload["job_id"]

    jobs_response = client.get("/api/jobs")
    assert jobs_response.status_code == 200
    jobs = jobs_response.get_json()
    assert isinstance(jobs, list)
    assert any(item["id"] == job_id for item in jobs)

    detail_response = client.get(f"/api/jobs/{job_id}")
    assert detail_response.status_code == 200
    detail = detail_response.get_json()
    assert detail["id"] == job_id

    log_response = client.get(f"/api/jobs/{job_id}/logs")
    assert log_response.status_code == 200
    logs = log_response.get_json()["logs"]
    assert any("queued" in line for line in logs)

    cancel_response = client.post(f"/api/jobs/{job_id}/cancel")
    assert cancel_response.status_code == 200
    assert cancel_response.get_json()["success"] is True

    cancelled_job = manager.get_job(job_id)
    assert cancelled_job is not None
    assert cancelled_job["status"] == "cancelled"


def test_run_log_endpoint_uses_job_id(webui_client):
    client, manager = webui_client

    job = manager.create_job(["python", "-c", "print('hello')"])
    job_id = job["id"]
    manager._append_log(job_id, "line-1")
    manager._append_log(job_id, "line-2")

    response = client.get(f"/api/run-log?job_id={job_id}")
    assert response.status_code == 200
    text = response.get_data(as_text=True)
    assert "line-1" in text
    assert "line-2" in text


def test_jobs_api_supports_status_filter(webui_client):
    client, manager = webui_client

    queued_job = manager.create_job(["python", "-c", "print('queued')"])
    success_job = manager.create_job(["python", "-c", "print('success')"])
    manager._update_job(success_job["id"], status="success", stage="finished")
    failed_job = manager.create_job(["python", "-c", "print('failed')"])
    manager._update_job(failed_job["id"], status="failed", stage="failed")

    active_response = client.get("/api/jobs?status=active")
    assert active_response.status_code == 200
    active_jobs = active_response.get_json()
    active_ids = {job["id"] for job in active_jobs}
    assert queued_job["id"] in active_ids
    assert success_job["id"] not in active_ids

    failed_response = client.get("/api/jobs?status=failed")
    assert failed_response.status_code == 200
    failed_jobs = failed_response.get_json()
    assert all(job["status"] == "failed" for job in failed_jobs)

    queued_detail = client.get(f"/api/jobs/{queued_job['id']}")
    assert queued_detail.status_code == 200
    queued_payload = queued_detail.get_json()
    assert isinstance(queued_payload["queue_position"], int)
    assert queued_payload["queue_position"] >= 1

    timeline = queued_payload.get("timeline") or []
    assert [item["key"] for item in timeline] == [
        "queued",
        "starting",
        "crawl",
        "rss",
        "ai",
        "report",
        "notify",
        "finished",
    ]
    assert all("reached" in item for item in timeline)
    assert all("failed" in item for item in timeline)


def test_failed_job_timeline_marks_failure_stage(webui_client):
    client, manager = webui_client

    job = manager.create_job(["python", "-c", "print('timeline-fail')"])
    manager.create_job(["python", "-c", "print('queued')"])
    manager._update_job(
        job["id"], status="running", stage="starting", started_at="2026-02-09T12:00:00Z"
    )
    manager._append_log(job["id"], "[info] start crawling source")
    manager._append_log(job["id"], "[info] ai analyzing content")
    manager._update_job(
        job["id"], status="failed", stage="ai", finished_at="2026-02-09T12:00:09Z", error="boom"
    )

    detail_response = client.get(f"/api/jobs/{job['id']}")
    assert detail_response.status_code == 200
    detail = detail_response.get_json()

    assert detail["failure_stage"] == "ai"
    timeline = detail.get("timeline") or []
    ai_point = next((item for item in timeline if item.get("key") == "ai"), None)
    assert ai_point is not None
    assert ai_point["failed"] is True

    report_point = next((item for item in timeline if item.get("key") == "report"), None)
    assert report_point is not None
    assert report_point["reached"] is False

    page_response = client.get("/api/jobs?page=1&page_size=2&q=queued")
    assert page_response.status_code == 200
    page_payload = page_response.get_json()
    assert isinstance(page_payload.get("items"), list)
    assert page_payload["page"] == 1
    assert page_payload["page_size"] == 2
    assert page_payload["total"] >= 1
    assert page_payload["total_pages"] >= 1


def test_job_detail_contains_report_links(webui_client):
    client, manager = webui_client

    output_dir = Path(manager.output_dir)
    report_dir = output_dir / "html" / "2026-02-08"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_file = report_dir / "12-34.html"
    report_file.write_text("<html>ok</html>", encoding="utf-8")

    job = manager.create_job(["python", "-c", "print('report')"])
    manager._update_job(
        job["id"],
        report_paths_json=json.dumps([str(report_file)]),
    )

    detail_response = client.get(f"/api/jobs/{job['id']}")
    assert detail_response.status_code == 200
    detail = detail_response.get_json()

    report_links = detail.get("report_links") or []
    assert len(report_links) == 1
    assert report_links[0]["url"].startswith("/reports/2026-02-08/")


def test_artifact_route_serves_output_files(webui_client):
    client, manager = webui_client

    artifact_file = Path(manager.output_dir) / "artifacts" / "sample.txt"
    artifact_file.parent.mkdir(parents=True, exist_ok=True)
    artifact_file.write_text("artifact-content", encoding="utf-8")

    response = client.get("/artifacts/artifacts/sample.txt")
    assert response.status_code == 200
    assert "artifact-content" in response.get_data(as_text=True)


def test_retry_job_creates_new_job_with_same_command(webui_client):
    client, manager = webui_client

    original = manager.create_job(["python", "-c", "print('retry-me')"])
    manager._update_job(original["id"], status="failed", stage="failed")

    response = client.post(f"/api/jobs/{original['id']}/retry")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["source_job_id"] == original["id"]

    new_job_id = payload["job_id"]
    assert new_job_id
    assert new_job_id != original["id"]

    original_job = manager.get_job(original["id"])
    new_job = manager.get_job(new_job_id)
    assert original_job is not None
    assert new_job is not None
    assert new_job["command"] == original_job["command"]
    assert new_job["status"] == "queued"


def test_retry_job_from_failed_stage_uses_strategy_flags(webui_client):
    client, manager = webui_client

    notify_job = manager.create_job(["python", "-m", "trendradar"])
    manager._update_job(
        notify_job["id"], status="running", stage="starting", started_at="2026-02-09T12:00:00Z"
    )
    manager._append_log(notify_job["id"], "[notify] push webhook sending")
    manager._update_job(
        notify_job["id"], status="failed", stage="notify", finished_at="2026-02-09T12:00:09Z"
    )

    notify_response = client.post(
        f"/api/jobs/{notify_job['id']}/retry",
        json={"strategy": "from_failed_stage"},
    )
    assert notify_response.status_code == 200
    notify_payload = notify_response.get_json()
    assert notify_payload["success"] is True
    assert notify_payload["strategy"] == "from_failed_stage"

    notify_retry_job = manager.get_job(notify_payload["job_id"])
    assert notify_retry_job is not None
    assert "--force-push" in (notify_retry_job.get("command") or [])

    ai_job = manager.create_job(["python", "-m", "trendradar"])
    manager._update_job(
        ai_job["id"], status="running", stage="starting", started_at="2026-02-09T13:00:00Z"
    )
    manager._append_log(ai_job["id"], "[ai] analysis begin")
    manager._update_job(
        ai_job["id"], status="failed", stage="ai", finished_at="2026-02-09T13:00:09Z"
    )

    ai_response = client.post(
        f"/api/jobs/{ai_job['id']}/retry",
        json={"strategy": "from_failed_stage"},
    )
    assert ai_response.status_code == 200
    ai_payload = ai_response.get_json()
    assert ai_payload["success"] is True
    assert ai_payload["strategy"] == "from_failed_stage"

    ai_retry_job = manager.get_job(ai_payload["job_id"])
    assert ai_retry_job is not None
    assert "--force-ai" in (ai_retry_job.get("command") or [])


def test_retry_job_from_failed_stage_falls_back_to_full(webui_client):
    client, manager = webui_client

    crawl_job = manager.create_job(["python", "-m", "trendradar"])
    manager._update_job(
        crawl_job["id"], status="running", stage="starting", started_at="2026-02-09T14:00:00Z"
    )
    manager._append_log(crawl_job["id"], "[crawl] fetch hot topics")
    manager._update_job(
        crawl_job["id"], status="failed", stage="crawl", finished_at="2026-02-09T14:00:09Z"
    )

    response = client.post(
        f"/api/jobs/{crawl_job['id']}/retry",
        json={"strategy": "from_failed_stage"},
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["strategy"] == "full"
    assert payload["strategy_note"] == "fallback_to_full_for_stage"

    new_job = manager.get_job(payload["job_id"])
    assert new_job is not None
    command = new_job.get("command") or []
    assert "--force-ai" not in command
    assert "--force-push" not in command


def test_retry_job_detail_contains_strategy_info(webui_client):
    client, manager = webui_client

    source = manager.create_job(["python", "-m", "trendradar"])
    manager._update_job(
        source["id"], status="failed", stage="notify", finished_at="2026-02-09T15:00:09Z"
    )

    retry_response = client.post(
        f"/api/jobs/{source['id']}/retry",
        json={"strategy": "from_failed_stage"},
    )
    assert retry_response.status_code == 200
    retry_payload = retry_response.get_json()
    retry_job_id = retry_payload["job_id"]

    detail_response = client.get(f"/api/jobs/{retry_job_id}")
    assert detail_response.status_code == 200
    detail = detail_response.get_json()

    assert detail["retry_source_job_id"] == source["id"]
    assert detail["retry_strategy"] in {"from_failed_stage", "full"}
    assert isinstance(detail.get("retry_strategy_note"), str)


def test_cleanup_jobs_removes_final_status_jobs(webui_client):
    client, manager = webui_client

    manager.create_job(["python", "-c", "print('keep-queued')"])

    for idx in range(3):
        done = manager.create_job(["python", "-c", f"print('done-{idx}')"])
        manager._update_job(done["id"], status="success", stage="finished")

    response = client.post("/api/jobs/cleanup", json={"keep_latest": 0})
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["deleted"] >= 3

    preview = client.get("/api/jobs/cleanup/preview?keep_latest=0")
    assert preview.status_code == 200
    preview_payload = preview.get_json()
    assert preview_payload["success"] is True
    assert preview_payload["planned"] >= 0

    jobs_after = client.get("/api/jobs").get_json()
    statuses = [item["status"] for item in jobs_after]
    assert not any(status in {"success", "failed", "cancelled"} for status in statuses)
    assert any(item["status"] == "queued" for item in jobs_after)


def test_jobs_page_is_available(webui_client):
    client, _ = webui_client

    response = client.get("/jobs")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "任务中心" in html
    assert "jobs-share-btn" in html
    assert "buildRetryTooltip" in html
    assert "RETRY_TOOLTIP_NOTE_MAX" in html
    assert "jobs-retry-note-toggle" in html
    assert "RETRY_NOTE_EXPAND_STORAGE_KEY" in html
    assert "persistRetryNoteExpanded" in html
    assert "jobs-retry-note-reset-btn" in html
    assert "clearRetryNoteExpandState" in html
    assert "Clear ${savedCount} saved retry-note expand states?" in html
    assert "showConfirmDialog" in html


def test_base_layout_contains_global_confirm_modal(webui_client):
    client, _ = webui_client

    response = client.get("/")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "global-confirm-modal" in html
    assert "global-confirm-title" in html
    assert "global-confirm-ok" in html


def test_workflow_page_is_available(webui_client):
    client, _ = webui_client

    response = client.get("/workflow")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Workflow Entry" in html
    assert "workflow-create-btn" in html
    assert "workflow-run-scope" in html
    assert "workflow-force-ai" in html
    assert "workflow-recent-list" in html
    assert "workflow-save-template-btn" in html
    assert "workflow-template-preview-btn" in html
    assert "workflow-template-preview" in html
    assert "workflow-template-import-btn" in html
    assert "workflow-template-import-file" in html


def test_workflow_templates_api_crud(webui_client):
    client, _ = webui_client

    create_response = client.post(
        "/api/workflow-templates",
        json={
            "name": "Morning RSS",
            "scope": "rss",
            "force_ai": True,
            "force_push": False,
        },
    )
    assert create_response.status_code == 200
    created_payload = create_response.get_json()
    assert created_payload["success"] is True
    item = created_payload["item"]
    template_id = item["id"]
    assert item["name"] == "Morning RSS"
    assert item["scope"] == "rss"
    assert item["force_ai"] is True
    assert item["force_push"] is False

    list_response = client.get("/api/workflow-templates")
    assert list_response.status_code == 200
    list_payload = list_response.get_json()
    assert list_payload["success"] is True
    assert any(row["id"] == template_id for row in list_payload["items"])

    update_response = client.put(
        f"/api/workflow-templates/{template_id}",
        json={
            "name": "Morning RSS+Push",
            "scope": "rss",
            "force_ai": True,
            "force_push": True,
        },
    )
    assert update_response.status_code == 200
    update_payload = update_response.get_json()
    assert update_payload["success"] is True
    assert update_payload["item"]["name"] == "Morning RSS+Push"
    assert update_payload["item"]["force_push"] is True

    delete_response = client.delete(f"/api/workflow-templates/{template_id}")
    assert delete_response.status_code == 200
    delete_payload = delete_response.get_json()
    assert delete_payload["success"] is True

    missing_response = client.delete(f"/api/workflow-templates/{template_id}")
    assert missing_response.status_code == 404


def test_workflow_templates_export_and_import(webui_client):
    client, _ = webui_client

    client.post(
        "/api/workflow-templates",
        json={
            "name": "Template A",
            "scope": "all",
            "force_ai": False,
            "force_push": False,
        },
    )
    client.post(
        "/api/workflow-templates",
        json={
            "name": "Template B",
            "scope": "rss",
            "force_ai": True,
            "force_push": False,
        },
    )

    export_response = client.get("/api/workflow-templates/export")
    assert export_response.status_code == 200
    exported = json.loads(export_response.get_data(as_text=True))
    assert exported["version"] == 1
    assert isinstance(exported.get("items"), list)
    assert any(item.get("name") == "Template A" for item in exported["items"])

    import_payload = {
        "replace": True,
        "items": [
            {
                "name": "Imported RSS",
                "scope": "rss",
                "force_ai": True,
                "force_push": True,
            },
            {
                "name": "Imported Platforms",
                "scope": "platforms",
                "force_ai": False,
                "force_push": True,
            },
        ],
    }
    import_response = client.post("/api/workflow-templates/import", json=import_payload)
    assert import_response.status_code == 200
    import_result = import_response.get_json()
    assert import_result["success"] is True
    assert import_result["replace"] is True
    assert import_result["imported"] == 2
    assert import_result["skipped"] == 0

    list_response = client.get("/api/workflow-templates")
    items = list_response.get_json()["items"]
    names = {item["name"] for item in items}
    assert names == {"Imported RSS", "Imported Platforms"}


def test_workflow_templates_import_preview(webui_client):
    client, _ = webui_client

    client.post(
        "/api/workflow-templates",
        json={
            "name": "Keep Me",
            "scope": "all",
            "force_ai": False,
            "force_push": False,
        },
    )

    preview_payload = {
        "replace": False,
        "items": [
            {"name": "Keep Me", "scope": "rss", "force_ai": True, "force_push": False},
            {"name": "New One", "scope": "platforms", "force_ai": False, "force_push": True},
            {"name": "", "scope": "all", "force_ai": False, "force_push": False},
            "invalid",
        ],
    }

    preview_response = client.post("/api/workflow-templates/import/preview", json=preview_payload)
    assert preview_response.status_code == 200
    preview = preview_response.get_json()
    assert preview["success"] is True
    assert preview["create"] == 1
    assert preview["update"] == 1
    assert preview["skip"] == 2
    assert len(preview["entries"]) == 4
    assert any(
        entry.get("action") == "update" and entry.get("name") == "Keep Me"
        for entry in preview["entries"]
    )
    assert any(
        entry.get("action") == "create" and entry.get("name") == "New One"
        for entry in preview["entries"]
    )


def test_rss_page_includes_feed_profiles(webui_client):
    client, _ = webui_client

    response = client.get("/rss")
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert "科技 + AI 模板" in html
    assert "全球宏观模板" in html
    assert "网络安全模板" in html
    assert "导出当前启用源(JSON)" in html
    assert "导入启用源(JSON)" in html
    assert "清空全部启用" in html
    assert "导入预览明细过滤" in html
    assert "rss-import-preview-action-filter" in html
    assert "rss-import-preview-action-filter-state" in html
    assert "当前过滤：全部 (all)" in html
    assert "rss-import-preview-action-filter-estimate" in html
    assert "本次导入将展示：待选择导入文件" in html
    assert "rss-import-preview-skip-summary" in html
    assert "跳过原因统计：待选择导入文件" in html
    assert "重置为全部(all)" in html

    assert "const FEED_PROFILES =" in html
    assert "async function applyFeedProfile" in html
    assert "async function clearAllEnabledFeeds" in html
    assert "function exportEnabledFeedsJson" in html
    assert "function triggerImportEnabledFeedsJson" in html
    assert "function normalizeImportedRssPayload" in html
    assert "function buildImportFeedPreview" in html
    assert "const RSS_IMPORT_PREVIEW_ACTION_FILTER_KEY" in html
    assert "const RSS_IMPORT_PREVIEW_MAX_LINES" in html
    assert "const RSS_IMPORT_SKIP_HIGHLIGHT_CLASS" in html
    assert "const RSS_IMPORT_SKIP_HIGHLIGHT_TIMEOUT_MS" in html
    assert "let lastImportFeedPreview" in html
    assert "function normalizeImportPreviewActionFilter" in html
    assert "function readImportPreviewActionFilter" in html
    assert "function renderImportPreviewActionFilterState" in html
    assert "function countImportPreviewEntriesByAction" in html
    assert "function renderImportPreviewActionEstimate" in html
    assert "function formatImportPreviewSkipReasonSummary" in html
    assert "function renderImportPreviewSkipReasonSummary" in html
    assert "function clearImportSkipHighlights" in html
    assert "function highlightFeedCardForSkip" in html
    assert "function focusFirstSkippedImportEntry" in html
    assert "function persistImportPreviewActionFilter" in html
    assert "function restoreImportPreviewActionFilter" in html
    assert "function bindImportPreviewActionFilter" in html
    assert "function initImportPreviewActionFilter" in html
    assert "function resetImportPreviewActionFilter" in html
    assert "function getImportPreviewActionFilter" in html
    assert "function formatImportPreviewDetails" in html
    assert "initImportPreviewActionFilter();" in html
    assert "async function handleImportEnabledFeedsFile" in html
    assert "导入预览明细" in html
