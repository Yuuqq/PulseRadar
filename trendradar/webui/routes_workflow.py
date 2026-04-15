"""
Workflow template API routes for TrendRadar Web UI.

Handles /api/workflow-templates (list, create, update, delete, export,
import preview, import).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from flask import Blueprint, Response, jsonify, request

from trendradar.webui.helpers import (
    build_workflow_template_import_plan,
    get_job_manager,
    read_json_body,
    to_bool,
    utc_now_iso,
)

workflow_bp = Blueprint("workflow", __name__)


@workflow_bp.route("/api/workflow-templates", methods=["GET"])
def list_workflow_templates():
    manager = get_job_manager()
    limit = request.args.get("limit", default=20, type=int)
    items = manager.list_workflow_templates(limit=limit if limit else 20)
    return jsonify({"success": True, "items": items})


@workflow_bp.route("/api/workflow-templates", methods=["POST"])
def create_workflow_template():
    manager = get_job_manager()
    payload = read_json_body() or {}

    try:
        item = manager.save_workflow_template(
            name=str(payload.get("name") or ""),
            scope=str(payload.get("scope") or "all"),
            force_ai=bool(payload.get("force_ai")),
            force_push=bool(payload.get("force_push")),
        )
    except ValueError:
        return jsonify({"success": False, "error": "template name is required"}), 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500

    return jsonify({"success": True, "item": item})


@workflow_bp.route("/api/workflow-templates/<template_id>", methods=["PUT"])
def update_workflow_template(template_id: str):
    manager = get_job_manager()
    payload = read_json_body() or {}

    existing = manager.get_workflow_template(template_id)
    if not existing:
        return jsonify({"success": False, "error": "template not found"}), 404

    try:
        item = manager.save_workflow_template(
            template_id=template_id,
            name=str(payload.get("name") or existing.get("name") or ""),
            scope=str(payload.get("scope") or existing.get("scope") or "all"),
            force_ai=bool(payload.get("force_ai")),
            force_push=bool(payload.get("force_push")),
        )
    except ValueError:
        return jsonify({"success": False, "error": "template name is required"}), 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500

    return jsonify({"success": True, "item": item})


@workflow_bp.route("/api/workflow-templates/<template_id>", methods=["DELETE"])
def delete_workflow_template(template_id: str):
    manager = get_job_manager()
    deleted = manager.delete_workflow_template(template_id)
    if not deleted:
        return jsonify({"success": False, "error": "template not found"}), 404
    return jsonify({"success": True, "id": template_id})


@workflow_bp.route("/api/workflow-templates/export", methods=["GET"])
def export_workflow_templates():
    manager = get_job_manager()
    items = manager.list_workflow_templates(limit=100)
    payload = {
        "version": 1,
        "exported_at": utc_now_iso(),
        "items": items,
    }
    content = json.dumps(payload, ensure_ascii=False, indent=2)
    filename = (
        f"trendradar-workflow-templates-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}.json"
    )
    return Response(
        content,
        content_type="application/json; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )


@workflow_bp.route("/api/workflow-templates/import/preview", methods=["POST"])
def preview_import_workflow_templates():
    payload = read_json_body() or {}
    replace_existing = to_bool(payload.get("replace"))
    items = payload.get("items")

    try:
        plan = build_workflow_template_import_plan(items, replace_existing=replace_existing)
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400

    return jsonify({"success": True, **plan})


@workflow_bp.route("/api/workflow-templates/import", methods=["POST"])
def import_workflow_templates():
    payload = read_json_body() or {}
    replace_existing = to_bool(payload.get("replace"))
    items = payload.get("items")

    try:
        plan = build_workflow_template_import_plan(items, replace_existing=replace_existing)
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400

    manager = get_job_manager()

    if replace_existing:
        manager.clear_workflow_templates()

    imported = 0
    skipped = int(plan.get("skip") or 0)

    for entry in plan.get("entries", []):
        if entry.get("action") == "skip":
            continue

        name = str(entry.get("name") or "").strip()
        if not name:
            skipped += 1
            continue
        try:
            manager.save_workflow_template(
                name=name,
                scope=str(entry.get("scope") or "all"),
                force_ai=to_bool(entry.get("force_ai")),
                force_push=to_bool(entry.get("force_push")),
                template_id=str(entry.get("target_id") or "") or None,
            )
            imported += 1
        except Exception:
            skipped += 1

    latest = manager.list_workflow_templates(limit=20)
    return jsonify(
        {
            "success": True,
            "replace": replace_existing,
            "imported": imported,
            "skipped": skipped,
            "total": int(plan.get("total_considered") or 0),
            "items": latest,
        }
    )
