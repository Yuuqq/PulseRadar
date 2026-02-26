# coding=utf-8
"""
TrendRadar Web UI - Flask application.

Provides local web management capabilities:
- configuration management
- job execution and status tracking
- data source connectivity testing
- historical report browsing
"""

from __future__ import annotations

import copy
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from urllib.parse import quote

import yaml
from flask import Flask, Response, jsonify, render_template, request, send_from_directory

from trendradar.webui.job_manager import JobManager


def create_app(config_path: Optional[str] = None, output_path: Optional[str] = None) -> Flask:
    """Create Flask app instance."""

    root_dir = Path(__file__).resolve().parents[2]
    config_dir = root_dir / "config"
    output_dir = Path(output_path) if output_path else (root_dir / "output")
    config_file = Path(config_path) if config_path else config_dir / "config.yaml"

    app = Flask(
        __name__,
        template_folder=str(Path(__file__).parent / "templates"),
        static_folder=str(Path(__file__).parent / "static"),
    )

    app.config["CONFIG_FILE"] = str(config_file)
    app.config["CONFIG_DIR"] = str(config_dir)
    app.config["OUTPUT_DIR"] = str(output_dir)
    app.config["ROOT_DIR"] = str(root_dir)
    app.config["PYTHON_EXECUTABLE"] = sys.executable

    job_manager = JobManager(root_dir=root_dir, output_dir=output_dir, config_file=config_file)
    app.extensions["trendradar_job_manager"] = job_manager

    def get_job_manager() -> JobManager:
        manager = app.extensions.get("trendradar_job_manager")
        if manager is None:
            raise RuntimeError("JobManager is not initialized")
        return manager

    def load_config() -> Dict[str, Any]:
        """Load YAML config file."""
        try:
            with open(app.config["CONFIG_FILE"], "r", encoding="utf-8") as file:
                data = yaml.safe_load(file) or {}
            return data if isinstance(data, dict) else {}
        except Exception as exc:
            return {"error": str(exc)}

    def save_config(config: Dict[str, Any]) -> bool:
        """Save YAML config file."""
        try:
            with open(app.config["CONFIG_FILE"], "w", encoding="utf-8") as file:
                yaml.dump(
                    config,
                    file,
                    allow_unicode=True,
                    default_flow_style=False,
                    sort_keys=False,
                )
            return True
        except Exception:
            return False

    def _read_json_body() -> Optional[Dict[str, Any]]:
        body = request.get_json(silent=True)
        return body if isinstance(body, dict) else None

    def _to_bool(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value != 0
        text = str(value or "").strip().lower()
        return text in {"1", "true", "yes", "on"}

    def _utc_now_iso() -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    def _normalize_workflow_scope(value: Any) -> str:
        scope_raw = str(value or "all").strip().lower()
        if scope_raw in {"all", "platforms", "rss", "extra_apis"}:
            return scope_raw
        return "all"

    def _build_workflow_template_import_plan(items: Any, replace_existing: bool) -> Dict[str, Any]:
        if not isinstance(items, list):
            raise ValueError("items must be an array")

        manager = get_job_manager()
        existing_by_name: Dict[str, Dict[str, Any]] = {}
        if not replace_existing:
            for template in manager.list_workflow_templates(limit=100):
                name = str(template.get("name") or "").strip()
                if not name:
                    continue
                existing_by_name[name.casefold()] = template

        received_total = len(items)
        considered_items = items[:100]
        overflow_skipped = max(0, received_total - len(considered_items))

        seen_names: Set[str] = set()
        entries: List[Dict[str, Any]] = []
        create_count = 0
        update_count = 0
        skip_count = overflow_skipped

        for index, raw in enumerate(considered_items, start=1):
            if not isinstance(raw, dict):
                skip_count += 1
                entries.append(
                    {
                        "index": index,
                        "action": "skip",
                        "reason": "invalid_item",
                    }
                )
                continue

            name = str(raw.get("name") or "").strip()
            if not name:
                skip_count += 1
                entries.append(
                    {
                        "index": index,
                        "action": "skip",
                        "reason": "empty_name",
                    }
                )
                continue

            safe_name = name[:48]
            name_key = safe_name.casefold()
            if name_key in seen_names:
                skip_count += 1
                entries.append(
                    {
                        "index": index,
                        "name": safe_name,
                        "action": "skip",
                        "reason": "duplicate_name",
                    }
                )
                continue

            seen_names.add(name_key)

            scope = _normalize_workflow_scope(raw.get("scope"))
            force_ai = _to_bool(raw.get("force_ai"))
            force_push = _to_bool(raw.get("force_push"))
            existing = existing_by_name.get(name_key)

            action = "update" if existing else "create"
            if action == "create":
                create_count += 1
            else:
                update_count += 1

            entries.append(
                {
                    "index": index,
                    "name": safe_name,
                    "scope": scope,
                    "force_ai": force_ai,
                    "force_push": force_push,
                    "action": action,
                    "target_id": str(existing.get("id")) if existing else None,
                    "reason": None,
                }
            )

        return {
            "replace": replace_existing,
            "total_received": received_total,
            "total_considered": len(considered_items),
            "overflow_skipped": overflow_skipped,
            "create": create_count,
            "update": update_count,
            "skip": skip_count,
            "entries": entries,
        }

    def _build_scoped_config(base_config: Dict[str, Any], scope: str) -> Dict[str, Any]:
        cfg = copy.deepcopy(base_config)

        platforms = cfg.get("platforms")
        rss = cfg.get("rss")
        extra_apis = cfg.get("extra_apis")

        if scope == "all":
            return cfg

        if isinstance(platforms, dict):
            platforms["enabled"] = scope in {"platforms"}
        if isinstance(rss, dict):
            rss["enabled"] = scope in {"rss"}
        if isinstance(extra_apis, dict):
            extra_apis["enabled"] = scope in {"extra_apis"}

        return cfg

    def _build_run_command_from_payload(payload: Optional[Dict[str, Any]]) -> List[str]:
        data = payload or {}
        scope_raw = str(data.get("scope") or "all").strip().lower()
        scope = scope_raw if scope_raw in {"all", "platforms", "rss", "extra_apis"} else "all"

        force_ai = bool(data.get("force_ai"))
        force_push = bool(data.get("force_push"))

        command: List[str] = [
            str(app.config.get("PYTHON_EXECUTABLE") or "python"),
            "-m",
            "trendradar",
        ]

        if scope != "all":
            base_config = load_config()
            scoped = _build_scoped_config(base_config, scope)
            run_config_dir = Path(app.config["OUTPUT_DIR"]) / "webui_run_configs"
            run_config_dir.mkdir(parents=True, exist_ok=True)

            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".yaml",
                prefix=f"{scope}-",
                encoding="utf-8",
                delete=False,
                dir=run_config_dir,
            ) as handle:
                yaml.dump(
                    scoped,
                    handle,
                    allow_unicode=True,
                    default_flow_style=False,
                    sort_keys=False,
                )
                config_path = handle.name

            command.extend(["--config", config_path])

        if force_push:
            command.append("--force-push")
        if force_ai:
            command.append("--force-ai")

        return command

    def _append_flag_once(command: List[str], flag: str) -> List[str]:
        items = [str(part) for part in command]
        if flag not in items:
            items.append(flag)
        return items

    def _resolve_retry_command(
        command: Optional[List[str]],
        requested_strategy: str,
        failed_stage: Optional[str],
    ) -> Dict[str, Any]:
        base = command if isinstance(command, list) and command else [
            str(app.config.get("PYTHON_EXECUTABLE") or "python"),
            "-m",
            "trendradar",
        ]
        normalized = [str(part) for part in base]

        if requested_strategy != "from_failed_stage":
            return {
                "command": normalized,
                "strategy_applied": "full",
                "strategy_note": "full_rerun",
            }

        stage = str(failed_stage or "").strip().lower()
        if stage == "notify":
            return {
                "command": _append_flag_once(normalized, "--force-push"),
                "strategy_applied": "from_failed_stage",
                "strategy_note": "add_force_push_for_notify_stage",
            }

        if stage in {"ai", "report"}:
            return {
                "command": _append_flag_once(normalized, "--force-ai"),
                "strategy_applied": "from_failed_stage",
                "strategy_note": "add_force_ai_for_ai_or_report_stage",
            }

        return {
            "command": normalized,
            "strategy_applied": "full",
            "strategy_note": "fallback_to_full_for_stage",
        }

    def _is_path_in_output(target_path: Path) -> bool:
        output_root = Path(app.config["OUTPUT_DIR"]).resolve()
        try:
            resolved = target_path.resolve()
        except Exception:
            return False
        return resolved == output_root or output_root in resolved.parents

    def _report_path_to_url(path_str: str) -> Optional[str]:
        if not path_str:
            return None

        output_root = Path(app.config["OUTPUT_DIR"]).resolve()
        report_path = Path(path_str)
        try:
            resolved = report_path.resolve()
        except Exception:
            return None

        if resolved != output_root and output_root not in resolved.parents:
            return None

        relative = resolved.relative_to(output_root)
        parts = relative.parts

        if len(parts) >= 3 and parts[0] == "html":
            date = quote(parts[1])
            filename = quote(parts[-1])
            return f"/reports/{date}/{filename}"

        return f"/artifacts/{quote(relative.as_posix(), safe='/')}"

    def _build_stage_timeline(
        stage_timestamps: Dict[str, Any],
        latest_stage: Optional[str],
        failure_stage: Optional[str],
    ) -> List[Dict[str, Any]]:
        stage_order = ["queued", "starting", "crawl", "rss", "ai", "report", "notify", "finished"]
        stage_labels = {
            "queued": "排队",
            "starting": "启动",
            "crawl": "抓取",
            "rss": "RSS",
            "ai": "AI",
            "report": "报告",
            "notify": "通知",
            "finished": "完成",
        }
        timestamp_map = stage_timestamps if isinstance(stage_timestamps, dict) else {}
        latest_index = stage_order.index(latest_stage) if latest_stage in stage_order else -1
        failure_key = failure_stage if failure_stage in stage_order else None

        timeline: List[Dict[str, Any]] = []
        for idx, key in enumerate(stage_order):
            timestamp = timestamp_map.get(key)
            has_timestamp = bool(timestamp)
            reached = has_timestamp or (latest_index >= 0 and idx <= latest_index)
            failed_here = failure_key == key
            timeline.append(
                {
                    "key": key,
                    "label": stage_labels.get(key, key),
                    "timestamp": timestamp,
                    "reached": reached,
                    "failed": failed_here,
                }
            )
        return timeline

    def _serialize_job(job: Dict[str, Any], include_timeline: bool = True) -> Dict[str, Any]:
        data = dict(job)
        report_paths = data.get("report_paths") or []
        report_links: List[Dict[str, str]] = []

        for raw_path in report_paths:
            url = _report_path_to_url(str(raw_path))
            if not url:
                continue
            report_links.append(
                {
                    "name": Path(str(raw_path)).name,
                    "path": str(raw_path),
                    "url": url,
                }
            )

        data["report_links"] = report_links
        if not include_timeline:
            data["failure_stage"] = None
            data["latest_stage"] = data.get("stage")
            data["timeline"] = []
            return data
        data["timeline"] = [
            {
                "key": "created",
                "label": "创建",
                "timestamp": data.get("created_at"),
            },
            {
                "key": "started",
                "label": "启动",
                "timestamp": data.get("started_at"),
            },
            {
                "key": "finished",
                "label": "结束",
                "timestamp": data.get("finished_at"),
            },
        ]
        manager = get_job_manager()
        trace = manager.get_job_stage_trace(str(data.get("id") or ""))
        data["failure_stage"] = trace.get("failure_stage")
        data["latest_stage"] = trace.get("latest_stage")
        data["timeline"] = _build_stage_timeline(
            trace.get("stage_timestamps") or {},
            data.get("latest_stage"),
            data.get("failure_stage"),
        )
        return data

    @app.route("/")
    def index():
        return render_template("index.html", config=load_config())

    @app.route("/platforms")
    def platforms_page():
        return render_template("platforms.html", config=load_config())

    @app.route("/rss")
    def rss_page():
        return render_template("rss.html", config=load_config())

    @app.route("/extra-apis")
    def extra_apis_page():
        return render_template("extra_apis.html", config=load_config())

    @app.route("/notifications")
    def notifications_page():
        return render_template("notifications.html", config=load_config())

    @app.route("/ai")
    def ai_page():
        return render_template("ai.html", config=load_config())

    @app.route("/reports")
    def reports_page():
        return render_template("reports.html")

    @app.route("/workflow")
    def workflow_page():
        return render_template("workflow.html", config=load_config())

    @app.route("/jobs")
    def jobs_page():
        return render_template("jobs.html")

    @app.route("/settings")
    def settings_page():
        return render_template("settings.html", config=load_config())

    @app.route("/api/config", methods=["GET"])
    def get_config():
        return jsonify(load_config())

    @app.route("/api/config", methods=["POST"])
    def update_config():
        new_config = _read_json_body()
        if new_config is None:
            return jsonify({"success": False, "error": "请求体必须是 JSON 对象"}), 400
        if save_config(new_config):
            return jsonify({"success": True})
        return jsonify({"success": False, "error": "保存失败"}), 500

    @app.route("/api/config/<section>", methods=["GET"])
    def get_config_section(section: str):
        config = load_config()
        if section in config:
            return jsonify(config[section])
        return jsonify({"error": "Section not found"}), 404

    @app.route("/api/config/<section>", methods=["POST"])
    def update_config_section(section: str):
        section_value = _read_json_body()
        if section_value is None:
            return jsonify({"success": False, "error": "请求体必须是 JSON 对象"}), 400

        config = load_config()
        if not isinstance(config, dict):
            config = {}
        config[section] = section_value
        if save_config(config):
            return jsonify({"success": True})
        return jsonify({"success": False, "error": "保存失败"}), 500

    @app.route("/api/platforms", methods=["GET"])
    def get_platforms():
        config = load_config()
        return jsonify(config.get("platforms", {}))

    @app.route("/api/platforms", methods=["POST"])
    def update_platforms():
        platforms = _read_json_body()
        if platforms is None:
            return jsonify({"success": False, "error": "请求体必须是 JSON 对象"}), 400

        config = load_config()
        config["platforms"] = platforms
        if save_config(config):
            return jsonify({"success": True})
        return jsonify({"success": False, "error": "保存失败"}), 500

    @app.route("/api/rss", methods=["GET"])
    def get_rss():
        config = load_config()
        return jsonify(config.get("rss", {}))

    @app.route("/api/rss", methods=["POST"])
    def update_rss():
        rss = _read_json_body()
        if rss is None:
            return jsonify({"success": False, "error": "请求体必须是 JSON 对象"}), 400

        config = load_config()
        config["rss"] = rss
        if save_config(config):
            return jsonify({"success": True})
        return jsonify({"success": False, "error": "保存失败"}), 500

    @app.route("/api/extra-apis", methods=["GET"])
    def get_extra_apis():
        config = load_config()
        return jsonify(config.get("extra_apis", {}))

    @app.route("/api/extra-apis", methods=["POST"])
    def update_extra_apis():
        extra_apis = _read_json_body()
        if extra_apis is None:
            return jsonify({"success": False, "error": "请求体必须是 JSON 对象"}), 400

        config = load_config()
        config["extra_apis"] = extra_apis
        if save_config(config):
            return jsonify({"success": True})
        return jsonify({"success": False, "error": "保存失败"}), 500

    @app.route("/api/reports", methods=["GET"])
    def get_reports():
        try:
            html_dir = Path(app.config["OUTPUT_DIR"]) / "html"
            reports = []

            if html_dir.exists():
                for date_dir in sorted(html_dir.iterdir(), reverse=True):
                    if not date_dir.is_dir() or date_dir.name == "latest":
                        continue
                    for html_file in sorted(date_dir.glob("*.html"), reverse=True):
                        reports.append(
                            {
                                "date": date_dir.name,
                                "time": html_file.stem,
                                "path": f"/reports/{date_dir.name}/{html_file.name}",
                                "filename": html_file.name,
                            }
                        )
            return jsonify(reports[:100])
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

    @app.route("/reports/<date>/<filename>")
    def serve_report(date: str, filename: str):
        html_dir = Path(app.config["OUTPUT_DIR"]) / "html" / date
        return send_from_directory(str(html_dir), filename)

    @app.route("/artifacts/<path:relative_path>")
    def serve_artifact(relative_path: str):
        output_root = Path(app.config["OUTPUT_DIR"]).resolve()
        target = (output_root / relative_path).resolve()
        if not _is_path_in_output(target) or not target.exists() or not target.is_file():
            return jsonify({"error": "Artifact not found"}), 404
        return send_from_directory(str(target.parent), target.name)

    @app.route("/api/jobs", methods=["GET"])
    def list_jobs():
        limit = request.args.get("limit", default=50, type=int)
        page = request.args.get("page", default=1, type=int)
        page_size = request.args.get("page_size", default=20, type=int)
        page = page if isinstance(page, int) and page > 0 else 1
        page_size = page_size if isinstance(page_size, int) and page_size > 0 else 20
        status = (request.args.get("status") or "").strip().lower()
        query = (request.args.get("q") or "").strip()
        manager = get_job_manager()

        status_filters: List[str] = []
        if status:
            active_statuses: Set[str] = {"queued", "running", "cancelling"}
            final_statuses: Set[str] = {"success", "failed", "cancelled"}

            if status == "active":
                status_filters = sorted(active_statuses)
            elif status == "final":
                status_filters = sorted(final_statuses)
            else:
                status_filters = [item.strip() for item in status.split(",") if item.strip()]

        use_pagination = request.args.get("page") is not None or request.args.get("page_size") is not None or bool(query)

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

                def _matches(job_item: Dict[str, Any]) -> bool:
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
            job_data = _serialize_job(job, include_timeline=False)
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

    @app.route("/api/jobs/<job_id>", methods=["GET"])
    def get_job(job_id: str):
        manager = get_job_manager()
        job = manager.get_job(job_id)
        if not job:
            return jsonify({"error": "Job not found"}), 404

        data = _serialize_job(job)
        if data.get("status") == "queued":
            data["queue_position"] = manager.get_queue_positions().get(str(data.get("id")))
        else:
            data["queue_position"] = None
        return jsonify(data)

    @app.route("/api/jobs/<job_id>/logs", methods=["GET"])
    def get_job_logs(job_id: str):
        manager = get_job_manager()
        job = manager.get_job(job_id)
        if not job:
            return jsonify({"error": "Job not found"}), 404

        tail = request.args.get("tail", type=int)
        logs = manager.get_job_logs(job_id, tail=tail)
        return jsonify({"job_id": job_id, "logs": logs})

    @app.route("/api/jobs/<job_id>/cancel", methods=["POST"])
    def cancel_job(job_id: str):
        manager = get_job_manager()
        job = manager.get_job(job_id)
        if not job:
            return jsonify({"success": False, "error": "任务不存在"}), 404

        if manager.cancel_job(job_id):
            return jsonify({"success": True, "job_id": job_id})

        return jsonify({"success": False, "error": "任务已结束，无法取消"}), 409

    @app.route("/api/jobs/<job_id>/retry", methods=["POST"])
    def retry_job(job_id: str):
        manager = get_job_manager()
        job = manager.get_job(job_id)
        if not job:
            return jsonify({"success": False, "error": "任务不存在"}), 404

        payload = _read_json_body() or {}
        requested_strategy = str(payload.get("strategy") or "full").strip().lower()
        if requested_strategy not in {"full", "from_failed_stage"}:
            requested_strategy = "full"

        trace = manager.get_job_stage_trace(job_id)
        resolved = _resolve_retry_command(
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

    @app.route("/api/jobs/cleanup", methods=["POST"])
    def cleanup_jobs():
        manager = get_job_manager()
        payload = _read_json_body() or {}
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

    @app.route("/api/jobs/cleanup/preview", methods=["GET"])
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

    @app.route("/api/status", methods=["GET"])
    def get_status():
        job_id = request.args.get("job_id")
        return jsonify(get_job_manager().get_legacy_status(job_id=job_id))

    @app.route("/api/run", methods=["POST"])
    def run_crawler():
        manager = get_job_manager()
        payload = _read_json_body() or {}
        command = _build_run_command_from_payload(payload)
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

    @app.route("/api/run-log", methods=["GET"])
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

    @app.route("/api/workflow-templates", methods=["GET"])
    def list_workflow_templates():
        manager = get_job_manager()
        limit = request.args.get("limit", default=20, type=int)
        items = manager.list_workflow_templates(limit=limit if limit else 20)
        return jsonify({"success": True, "items": items})

    @app.route("/api/workflow-templates", methods=["POST"])
    def create_workflow_template():
        manager = get_job_manager()
        payload = _read_json_body() or {}

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

    @app.route("/api/workflow-templates/<template_id>", methods=["PUT"])
    def update_workflow_template(template_id: str):
        manager = get_job_manager()
        payload = _read_json_body() or {}

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

    @app.route("/api/workflow-templates/<template_id>", methods=["DELETE"])
    def delete_workflow_template(template_id: str):
        manager = get_job_manager()
        deleted = manager.delete_workflow_template(template_id)
        if not deleted:
            return jsonify({"success": False, "error": "template not found"}), 404
        return jsonify({"success": True, "id": template_id})

    @app.route("/api/workflow-templates/export", methods=["GET"])
    def export_workflow_templates():
        manager = get_job_manager()
        items = manager.list_workflow_templates(limit=100)
        payload = {
            "version": 1,
            "exported_at": _utc_now_iso(),
            "items": items,
        }
        content = json.dumps(payload, ensure_ascii=False, indent=2)
        filename = f"trendradar-workflow-templates-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}.json"
        return Response(
            content,
            content_type="application/json; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Cache-Control": "no-store",
            },
        )

    @app.route("/api/workflow-templates/import/preview", methods=["POST"])
    def preview_import_workflow_templates():
        payload = _read_json_body() or {}
        replace_existing = _to_bool(payload.get("replace"))
        items = payload.get("items")

        try:
            plan = _build_workflow_template_import_plan(items, replace_existing=replace_existing)
        except ValueError as exc:
            return jsonify({"success": False, "error": str(exc)}), 400

        return jsonify({"success": True, **plan})

    @app.route("/api/workflow-templates/import", methods=["POST"])
    def import_workflow_templates():
        payload = _read_json_body() or {}
        replace_existing = _to_bool(payload.get("replace"))
        items = payload.get("items")

        try:
            plan = _build_workflow_template_import_plan(items, replace_existing=replace_existing)
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
                    force_ai=_to_bool(entry.get("force_ai")),
                    force_push=_to_bool(entry.get("force_push")),
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

    @app.route("/api/test-source", methods=["POST"])
    def test_source():
        """Test source availability with current settings."""
        try:
            data = _read_json_body() or {}
            source_type = data.get("type")
            source_config = data.get("config", {})

            if source_type == "platform":
                from trendradar.crawler.fetcher import DataFetcher

                fetcher = DataFetcher()
                result, _, _ = fetcher.fetch_data(source_config.get("id"))
                fetcher.close()
                if result:
                    return jsonify({"success": True, "message": "连接成功"})
                return jsonify({"success": False, "error": "获取失败"})

            if source_type in {
                "vvhan",
                "dailyhot",
                "newsapi",
                "gnews",
                "mediastack",
                "thenewsapi",
            }:
                from trendradar.crawler.extra_apis import ExtraAPIFetcher

                fetcher = ExtraAPIFetcher()
                items: Any = []

                if source_type == "vvhan":
                    items = fetcher.fetch_vvhan_hotlist(source_config.get("platform", "weibo"))
                elif source_type == "dailyhot":
                    items = fetcher.fetch_dailyhot(source_config.get("platform"))
                elif source_type == "newsapi":
                    items = fetcher.fetch_newsapi(
                        api_key=source_config.get("api_key", ""),
                        country=source_config.get("country", "us"),
                    )
                elif source_type == "gnews":
                    items = fetcher.fetch_gnews(
                        api_key=source_config.get("api_key", ""),
                        country=source_config.get("country", "us"),
                    )
                elif source_type == "mediastack":
                    items = fetcher.fetch_mediastack(
                        api_key=source_config.get("api_key", ""),
                        countries=source_config.get("countries", "us"),
                    )
                elif source_type == "thenewsapi":
                    items = fetcher.fetch_thenewsapi(
                        api_key=source_config.get("api_key", ""),
                    )

                fetcher.close()

                if items:
                    if isinstance(items, list):
                        count = len(items)
                        sample = items[:3]
                    elif isinstance(items, dict):
                        count = sum(len(value) for value in items.values() if isinstance(value, list))
                        sample = None
                    else:
                        count = 1
                        sample = None
                    return jsonify(
                        {
                            "success": True,
                            "message": f"获取成功: {count} 条",
                            "sample": sample,
                        }
                    )
                return jsonify({"success": False, "error": "获取失败或无数据"})

            if source_type == "rss":
                import feedparser

                feed = feedparser.parse(source_config.get("url", ""))
                if feed.entries:
                    return jsonify(
                        {
                            "success": True,
                            "message": f"获取成功: {len(feed.entries)} 条",
                            "sample": [{"title": item.get("title", "")} for item in feed.entries[:3]],
                        }
                    )
                return jsonify({"success": False, "error": "无法获取 RSS 内容"})

            return jsonify({"success": False, "error": "未知数据源类型"})
        except Exception as exc:
            return jsonify({"success": False, "error": str(exc)}), 500

    return app


def run_server(host: str = "127.0.0.1", port: int = 5000, debug: bool = False) -> None:
    """Run Web server."""

    app = create_app()
    print(f"\n{'=' * 60}")
    print("TrendRadar Web UI 已启动")
    print(f"访问地址: http://{host}:{port}")
    print(f"{'=' * 60}\n")
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    debug_env = os.environ.get("TREND_RADAR_WEBUI_DEBUG", "").strip().lower()
    debug = debug_env in {"1", "true", "yes", "on"}
    run_server(debug=debug)
