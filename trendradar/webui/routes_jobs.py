"""
Job management API routes for TrendRadar Web UI.

Handles /api/jobs (list, detail, logs, cancel, retry, cleanup),
/api/status, /api/run, /api/run-log.
"""

from __future__ import annotations

from typing import Any

from flask import Blueprint, Response, jsonify, request

from trendradar.webui.helpers import (
    build_run_command_from_payload,
    get_job_manager,
    read_json_body,
    resolve_retry_command,
    serialize_job,
)

jobs_bp = Blueprint("jobs", __name__)


@jobs_bp.route("/api/jobs", methods=["GET"])
def list_jobs():
    limit = request.args.get("limit", default=50, type=int)
    page = request.args.get("page", default=1, type=int)
    page_size = request.args.get("page_size", default=20, type=int)
    page = page if isinstance(page, int) and page > 0 else 1
    page_size = page_size if isinstance(page_size, int) and page_size > 0 else 20
    status = (request.args.get("status") or "").strip().lower()
    query = (request.args.get("q") or "").strip()
    manager = get_job_manager()

    status_filters: list[str] = []
    if status:
        active_statuses: set[str] = {"queued", "running", "cancelling"}
        final_statuses: set[str] = {"success", "failed", "cancelled"}

        if status == "active":
            status_filters = sorted(active_statuses)
        elif status == "final":
            status_filters = sorted(final_statuses)
        else:
            status_filters = [item.strip() for item in status.split(",") if item.strip()]

    use_pagination = (
        request.args.get("page") is not None
        or request.args.get("page_size") is not None
        or bool(query)
    )

    if use_pagination:
        page_data = manager.list_jobs_page(
            page=page,
            page_size=page_size,
            statuses=status_filters,
            query=query,
        )
        jobs = page_data["items"]
    else:
        jobs = manager.list_jobs(limit=limit if limit else 50)

        if status_filters:
            allowed = {value.lower() for value in status_filters}
            jobs = [job for job in jobs if str(job.get("status", "")).lower() in allowed]

        if query:
            query_lower = query.lower()

            def _matches(job_item: dict[str, Any]) -> bool:
                command_text = " ".join(job_item.get("command") or [])
                return any(
                    query_lower in str(field_value).lower()
                    for field_value in (
                        job_item.get("id", ""),
                        job_item.get("status", ""),
                        job_item.get("stage", ""),
                        command_text,
                        job_item.get("error", ""),
                    )
                )

            jobs = [job for job in jobs if _matches(job)]

    queue_positions = manager.get_queue_positions()
    serialized_jobs = []
    for job in jobs:
        job_data = serialize_job(job, include_timeline=False)
        if job_data.get("status") == "queued":
            job_data["queue_position"] = queue_positions.get(str(job_data.get("id")))
        else:
            job_data["queue_position"] = None
        serialized_jobs.append(job_data)

    if use_pagination:
        return jsonify(
            {
                "items": serialized_jobs,
                "page": page_data["page"],
                "page_size": page_data["page_size"],
                "total": page_data["total"],
                "total_pages": page_data["total_pages"],
                "has_prev": page_data["page"] > 1,
                "has_next": page_data["page"] < page_data["total_pages"],
                "query": query,
            }
        )

    return jsonify(serialized_jobs)


@jobs_bp.route("/api/jobs/<job_id>", methods=["GET"])
def get_job(job_id: str):
    manager = get_job_manager()
    job = manager.get_job(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    data = serialize_job(job)
    if data.get("status") == "queued":
        data["queue_position"] = manager.get_queue_positions().get(str(data.get("id")))
    else:
        data["queue_position"] = None
    return jsonify(data)


@jobs_bp.route("/api/jobs/<job_id>/logs", methods=["GET"])
def get_job_logs(job_id: str):
    manager = get_job_manager()
    job = manager.get_job(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    tail = request.args.get("tail", type=int)
    logs = manager.get_job_logs(job_id, tail=tail)
    return jsonify({"job_id": job_id, "logs": logs})


@jobs_bp.route("/api/jobs/<job_id>/cancel", methods=["POST"])
def cancel_job(job_id: str):
    manager = get_job_manager()
    job = manager.get_job(job_id)
    if not job:
        return jsonify({"success": False, "error": "任务不存在"}), 404

    if manager.cancel_job(job_id):
        return jsonify({"success": True, "job_id": job_id})

    return jsonify({"success": False, "error": "任务已结束，无法取消"}), 409


@jobs_bp.route("/api/jobs/<job_id>/retry", methods=["POST"])
def retry_job(job_id: str):
    manager = get_job_manager()
    job = manager.get_job(job_id)
    if not job:
        return jsonify({"success": False, "error": "任务不存在"}), 404

    payload = read_json_body() or {}
    requested_strategy = str(payload.get("strategy") or "full").strip().lower()
    if requested_strategy not in {"full", "from_failed_stage"}:
        requested_strategy = "full"

    trace = manager.get_job_stage_trace(job_id)
    resolved = resolve_retry_command(
        command=job.get("command") if isinstance(job.get("command"), list) else None,
        requested_strategy=requested_strategy,
        failed_stage=trace.get("failure_stage"),
    )

    command = resolved.get("command")
    if not isinstance(command, list) or not command:
        command = None

    new_job = manager.create_job(
        command=command,
        retry_source_job_id=job_id,
        retry_strategy=str(resolved.get("strategy_applied") or "full"),
        retry_strategy_note=str(resolved.get("strategy_note") or ""),
    )
    return jsonify(
        {
            "success": True,
            "source_job_id": job_id,
            "job_id": new_job.get("id"),
            "status": new_job.get("status"),
            "strategy": resolved.get("strategy_applied"),
            "strategy_note": resolved.get("strategy_note"),
        }
    )


@jobs_bp.route("/api/jobs/cleanup", methods=["POST"])
def cleanup_jobs():
    manager = get_job_manager()
    payload = read_json_body() or {}
    keep_latest = payload.get("keep_latest", 20)
    limit = payload.get("limit", 2000)

    try:
        keep_latest_int = int(keep_latest)
        limit_int = int(limit)
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "参数格式错误"}), 400

    deleted = manager.clear_final_jobs(keep_latest=keep_latest_int, limit=limit_int)
    return jsonify(
        {
            "success": True,
            "deleted": deleted,
            "keep_latest": max(0, keep_latest_int),
        }
    )


@jobs_bp.route("/api/jobs/cleanup/preview", methods=["GET"])
def cleanup_jobs_preview():
    manager = get_job_manager()
    keep_latest = request.args.get("keep_latest", default=20, type=int)
    limit = request.args.get("limit", default=2000, type=int)

    try:
        keep_latest_int = int(keep_latest)
        limit_int = int(limit)
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "参数格式错误"}), 400

    preview = manager.get_clearable_final_jobs_count(
        keep_latest=max(0, keep_latest_int),
        limit=max(1, limit_int),
    )
    return jsonify({"success": True, **preview})


@jobs_bp.route("/api/status", methods=["GET"])
def get_status():
    job_id = request.args.get("job_id")
    return jsonify(get_job_manager().get_legacy_status(job_id=job_id))


@jobs_bp.route("/api/run", methods=["POST"])
def run_crawler():
    manager = get_job_manager()
    payload = read_json_body() or {}
    command = build_run_command_from_payload(payload)
    job = manager.create_job(command)
    return jsonify(
        {
            "success": True,
            "message": "任务已加入队列",
            "job_id": job.get("id"),
            "status": job.get("status"),
            "scope": str(payload.get("scope") or "all"),
            "command": command,
        }
    )


@jobs_bp.route("/api/run-log", methods=["GET"])
def get_run_log():
    manager = get_job_manager()
    job_id = request.args.get("job_id")
    content = manager.get_run_log_text(job_id=job_id)
    target_job_id = job_id or (manager.get_latest_job() or {}).get("id", "latest")
    filename = f"trendradar-{target_job_id}.log"
    return Response(
        content,
        content_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )
