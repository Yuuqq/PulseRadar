"""
Shared helpers for TrendRadar Web UI blueprints.

All functions here use `current_app` so they work inside any request context
regardless of which blueprint is active.
"""

from __future__ import annotations

import copy
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

import yaml
from flask import current_app, request

from trendradar.webui.job_manager import JobManager

# ---------------------------------------------------------------------------
# Job manager accessor
# ---------------------------------------------------------------------------

def get_job_manager() -> JobManager:
    manager = current_app.extensions.get("trendradar_job_manager")
    if manager is None:
        raise RuntimeError("JobManager is not initialized")
    return manager


# ---------------------------------------------------------------------------
# Config I/O
# ---------------------------------------------------------------------------

def load_config() -> dict[str, Any]:
    """Load YAML config file."""
    try:
        with open(current_app.config["CONFIG_FILE"], encoding="utf-8") as file:
            data = yaml.safe_load(file) or {}
        return data if isinstance(data, dict) else {}
    except Exception as exc:
        return {"error": str(exc)}


def save_config(config: dict[str, Any]) -> bool:
    """Save YAML config file."""
    try:
        with open(current_app.config["CONFIG_FILE"], "w", encoding="utf-8") as file:
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


# ---------------------------------------------------------------------------
# Request helpers
# ---------------------------------------------------------------------------

def read_json_body() -> dict[str, Any] | None:
    body = request.get_json(silent=True)
    return body if isinstance(body, dict) else None


def to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    text = str(value or "").strip().lower()
    return text in {"1", "true", "yes", "on"}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


# ---------------------------------------------------------------------------
# Workflow scope helpers
# ---------------------------------------------------------------------------

def normalize_workflow_scope(value: Any) -> str:
    scope_raw = str(value or "all").strip().lower()
    if scope_raw in {"all", "platforms", "rss", "extra_apis"}:
        return scope_raw
    return "all"


def build_scoped_config(base_config: dict[str, Any], scope: str) -> dict[str, Any]:
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


def build_run_command_from_payload(payload: dict[str, Any] | None) -> list[str]:
    data = payload or {}
    scope_raw = str(data.get("scope") or "all").strip().lower()
    scope = scope_raw if scope_raw in {"all", "platforms", "rss", "extra_apis"} else "all"

    force_ai = bool(data.get("force_ai"))
    force_push = bool(data.get("force_push"))

    command: list[str] = [
        str(current_app.config.get("PYTHON_EXECUTABLE") or "python"),
        "-m",
        "trendradar",
    ]

    if scope != "all":
        base_config = load_config()
        scoped = build_scoped_config(base_config, scope)
        run_config_dir = Path(current_app.config["OUTPUT_DIR"]) / "webui_run_configs"
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


# ---------------------------------------------------------------------------
# Retry command helpers
# ---------------------------------------------------------------------------

def append_flag_once(command: list[str], flag: str) -> list[str]:
    items = [str(part) for part in command]
    if flag not in items:
        items.append(flag)
    return items


def resolve_retry_command(
    command: list[str] | None,
    requested_strategy: str,
    failed_stage: str | None,
) -> dict[str, Any]:
    base = command if isinstance(command, list) and command else [
        str(current_app.config.get("PYTHON_EXECUTABLE") or "python"),
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
            "command": append_flag_once(normalized, "--force-push"),
            "strategy_applied": "from_failed_stage",
            "strategy_note": "add_force_push_for_notify_stage",
        }

    if stage in {"ai", "report"}:
        return {
            "command": append_flag_once(normalized, "--force-ai"),
            "strategy_applied": "from_failed_stage",
            "strategy_note": "add_force_ai_for_ai_or_report_stage",
        }

    return {
        "command": normalized,
        "strategy_applied": "full",
        "strategy_note": "fallback_to_full_for_stage",
    }


# ---------------------------------------------------------------------------
# Output path safety helpers
# ---------------------------------------------------------------------------

def is_path_in_output(target_path: Path) -> bool:
    output_root = Path(current_app.config["OUTPUT_DIR"]).resolve()
    try:
        resolved = target_path.resolve()
    except Exception:
        return False
    return resolved == output_root or output_root in resolved.parents


def report_path_to_url(path_str: str) -> str | None:
    if not path_str:
        return None

    output_root = Path(current_app.config["OUTPUT_DIR"]).resolve()
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


# ---------------------------------------------------------------------------
# Job serialization helpers
# ---------------------------------------------------------------------------

def build_stage_timeline(
    stage_timestamps: dict[str, Any],
    latest_stage: str | None,
    failure_stage: str | None,
) -> list[dict[str, Any]]:
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

    timeline: list[dict[str, Any]] = []
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


def serialize_job(job: dict[str, Any], include_timeline: bool = True) -> dict[str, Any]:
    data = dict(job)
    report_paths = data.get("report_paths") or []
    report_links: list[dict[str, str]] = []

    for raw_path in report_paths:
        url = report_path_to_url(str(raw_path))
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
    data["timeline"] = build_stage_timeline(
        trace.get("stage_timestamps") or {},
        data.get("latest_stage"),
        data.get("failure_stage"),
    )
    return data


# ---------------------------------------------------------------------------
# Workflow template import plan
# ---------------------------------------------------------------------------

def build_workflow_template_import_plan(items: Any, replace_existing: bool) -> dict[str, Any]:
    if not isinstance(items, list):
        raise ValueError("items must be an array")

    manager = get_job_manager()
    existing_by_name: dict[str, dict[str, Any]] = {}
    if not replace_existing:
        for template in manager.list_workflow_templates(limit=100):
            name = str(template.get("name") or "").strip()
            if not name:
                continue
            existing_by_name[name.casefold()] = template

    received_total = len(items)
    considered_items = items[:100]
    overflow_skipped = max(0, received_total - len(considered_items))

    seen_names: set[str] = set()
    entries: list[dict[str, Any]] = []
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

        scope = normalize_workflow_scope(raw.get("scope"))
        force_ai = to_bool(raw.get("force_ai"))
        force_push = to_bool(raw.get("force_push"))
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
