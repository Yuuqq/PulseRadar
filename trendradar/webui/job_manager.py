"""
TrendRadar Web UI 任务管理器

为 Web UI 提供任务队列、日志和状态持久化能力。
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
import sqlite3
import subprocess
import sys
import threading
import time
import uuid
from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


FINAL_STATUSES = {"success", "failed", "cancelled"}
ACTIVE_STATUSES = {"queued", "running", "cancelling"}
WORKFLOW_SCOPES = {"all", "platforms", "rss", "extra_apis"}
JOB_STAGE_SEQUENCE = ("queued", "starting", "crawl", "rss", "ai", "report", "notify", "finished")
JOB_UPDATE_FIELDS = {
    "status",
    "stage",
    "command_json",
    "config_snapshot",
    "report_paths_json",
    "created_at",
    "started_at",
    "finished_at",
    "duration_seconds",
    "exit_code",
    "error",
    "retry_source_job_id",
    "retry_strategy",
    "retry_strategy_note",
    "updated_at",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        return datetime.fromisoformat(value)
    except ValueError:
        return None


class JobManager:
    """Web UI 任务管理器。"""

    def __init__(self, root_dir: Path, output_dir: Path, config_file: Path):
        self.root_dir = Path(root_dir)
        self.output_dir = Path(output_dir)
        self.config_file = Path(config_file)

        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.output_dir / "webui_jobs.db"

        self._lock = threading.RLock()
        self._processes: dict[str, subprocess.Popen] = {}
        self._dispatcher_started = False

        self._init_db()
        self._recover_stale_active_jobs()
        self._start_dispatcher()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    command_json TEXT NOT NULL,
                    config_snapshot TEXT,
                    report_paths_json TEXT,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    finished_at TEXT,
                    duration_seconds REAL,
                    exit_code INTEGER,
                    error TEXT,
                    retry_source_job_id TEXT,
                    retry_strategy TEXT,
                    retry_strategy_note TEXT,
                    updated_at TEXT NOT NULL
                )
                """
            )
            self._ensure_jobs_table_columns(conn)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS job_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL,
                    line_no INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (job_id) REFERENCES jobs(id)
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at DESC)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_stage ON jobs(stage)")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_jobs_status_created ON jobs(status, created_at DESC)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_job_logs_job_id_line_no ON job_logs(job_id, line_no)"
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS workflow_templates (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    scope TEXT NOT NULL,
                    force_ai INTEGER NOT NULL DEFAULT 0,
                    force_push INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_workflow_templates_name_nocase ON workflow_templates(LOWER(name))"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_workflow_templates_updated_at ON workflow_templates(updated_at DESC)"
            )

    # Whitelist of columns that may be added via ALTER TABLE (prevents SQL injection)
    _ALLOWED_MIGRATION_COLUMNS: dict[str, str] = {
        "retry_source_job_id": "TEXT",
        "retry_strategy": "TEXT",
        "retry_strategy_note": "TEXT",
    }

    def _ensure_jobs_table_columns(self, conn: sqlite3.Connection) -> None:
        rows = conn.execute("PRAGMA table_info(jobs)").fetchall()
        existing = {str(row["name"]).strip().lower() for row in rows}
        for column_name, column_type in self._ALLOWED_MIGRATION_COLUMNS.items():
            if column_name in existing:
                continue
            if column_name not in self._ALLOWED_MIGRATION_COLUMNS:
                raise ValueError(f"Column not in migration whitelist: {column_name}")
            if column_type not in ("TEXT", "INTEGER", "REAL", "BLOB"):
                raise ValueError(f"Invalid SQLite column type: {column_type}")
            conn.execute(f"ALTER TABLE jobs ADD COLUMN {column_name} {column_type}")

    def _start_dispatcher(self) -> None:
        with self._lock:
            if self._dispatcher_started:
                return
            self._dispatcher_started = True
        thread = threading.Thread(target=self._dispatch_loop, daemon=True)
        thread.start()

    def _dispatch_loop(self) -> None:
        while True:
            try:
                self._recover_stale_active_jobs()
                if not self.get_running_job_id():
                    next_job = self._get_next_queued_job()
                    if next_job:
                        self._start_job(next_job["id"], next_job["command"])
            except Exception:
                logger.exception("dispatch loop error")
            time.sleep(0.5)

    def _recover_stale_active_jobs(self, stale_seconds: int = 300) -> int:
        """Recover orphaned active jobs left by process restart/crash.

        Jobs in `running`/`cancelling` with no heartbeat updates for `stale_seconds`
        are marked finished so they no longer block the queue.
        """
        safe_stale = max(1, int(stale_seconds))
        now_dt = datetime.now(timezone.utc)

        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, status, stage, created_at, started_at, updated_at
                FROM jobs
                WHERE status IN ('running', 'cancelling')
                """
            ).fetchall()

        recovered = 0
        for row in rows:
            job_id = str(row["id"])
            status = str(row["status"] or "").strip().lower()
            stage = str(row["stage"] or "").strip().lower()

            with self._lock:
                process = self._processes.get(job_id)
            if process is not None:
                try:
                    if process.poll() is None:
                        continue
                except Exception:
                    continue

            last_ts = (
                _parse_ts(row["updated_at"])
                or _parse_ts(row["started_at"])
                or _parse_ts(row["created_at"])
            )
            if last_ts is None:
                is_stale = True
            else:
                is_stale = (now_dt - last_ts) >= timedelta(seconds=safe_stale)

            if not is_stale:
                continue

            final_status = "cancelled" if status == "cancelling" else "failed"
            final_stage = stage if stage in JOB_STAGE_SEQUENCE else "starting"
            now_text = _utc_now()

            self._update_job(
                job_id,
                status=final_status,
                stage=final_stage,
                finished_at=now_text,
                exit_code=-999,
                error="Recovered stale active job after webui restart",
            )
            self._append_log(job_id, "[job] recovered stale active job")
            recovered += 1

        return recovered

    def _get_next_queued_job(self) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, command_json
                FROM jobs
                WHERE status = 'queued'
                ORDER BY created_at ASC
                LIMIT 1
                """
            ).fetchone()
        if not row:
            return None
        try:
            command = json.loads(row["command_json"])
        except (TypeError, json.JSONDecodeError):
            command = [sys.executable, "-m", "trendradar"]
        return {"id": row["id"], "command": command}

    def create_job(
        self,
        command: list[str] | None = None,
        retry_source_job_id: str | None = None,
        retry_strategy: str | None = None,
        retry_strategy_note: str | None = None,
    ) -> dict[str, Any]:
        job_id = uuid.uuid4().hex[:12]
        now = _utc_now()
        command_list = command or [sys.executable, "-m", "trendradar"]
        command_json = json.dumps(command_list, ensure_ascii=False)
        safe_retry_source_job_id = str(retry_source_job_id or "").strip() or None
        safe_retry_strategy = str(retry_strategy or "").strip() or None
        safe_retry_strategy_note = str(retry_strategy_note or "").strip() or None

        try:
            config_snapshot = self.config_file.read_text(encoding="utf-8")
        except Exception:
            config_snapshot = ""

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO jobs (
                    id, status, stage, command_json, config_snapshot,
                    created_at, retry_source_job_id, retry_strategy,
                    retry_strategy_note, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    "queued",
                    "queued",
                    command_json,
                    config_snapshot,
                    now,
                    safe_retry_source_job_id,
                    safe_retry_strategy,
                    safe_retry_strategy_note,
                    now,
                ),
            )
        self._append_log(job_id, "[job] queued")
        return self.get_job(job_id) or {"id": job_id, "status": "queued"}

    def enqueue_default_job(self) -> dict[str, Any]:
        return self.create_job([sys.executable, "-m", "trendradar"])

    def _start_job(self, job_id: str, command: list[str]) -> None:
        self._update_job(
            job_id, status="running", stage="starting", started_at=_utc_now(), error=""
        )
        thread = threading.Thread(
            target=self._run_process,
            args=(job_id, command),
            daemon=True,
        )
        thread.start()

    def _run_process(self, job_id: str, command: list[str]) -> None:
        env = {**os.environ, "PYTHONUTF8": "1", "PYTHONUNBUFFERED": "1"}
        command_str = " ".join(command)
        self._append_log(job_id, f"[job] start: {command_str}")

        process: subprocess.Popen | None = None
        return_code = -1
        try:
            process = subprocess.Popen(
                command,
                cwd=self.root_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
            )
            with self._lock:
                self._processes[job_id] = process

            if process.stdout is not None:
                for raw_line in process.stdout:
                    line = raw_line.rstrip("\r\n")
                    if line:
                        self._append_log(job_id, line)
                        stage = self._infer_stage(line)
                        if stage:
                            self._update_job(job_id, stage=stage)

            return_code = process.wait()
        except Exception as exc:
            self._append_log(job_id, f"[job] error: {exc}")
            return_code = -1
        finally:
            with self._lock:
                self._processes.pop(job_id, None)

        job = self.get_job(job_id)
        cancelled = bool(job and job.get("status") == "cancelled")
        status = "cancelled" if cancelled else ("success" if return_code == 0 else "failed")

        previous_stage = str((job or {}).get("stage") or "").strip().lower()
        if status == "success":
            final_stage = "finished"
        elif status == "failed" and previous_stage in JOB_STAGE_SEQUENCE:
            final_stage = previous_stage
        else:
            final_stage = status

        now = _utc_now()
        duration_seconds = None
        if job:
            started_at = _parse_ts(job.get("started_at"))
            finished_at = _parse_ts(now)
            if started_at and finished_at:
                duration_seconds = round((finished_at - started_at).total_seconds(), 3)

        error = ""
        if status == "failed":
            error = f"Process exited with code {return_code}"
            self._append_log(job_id, f"[job] failed: {error}")
        elif status == "success":
            self._append_log(job_id, "[job] success")

        self._update_job(
            job_id,
            status=status,
            stage=final_stage,
            finished_at=now,
            duration_seconds=duration_seconds,
            exit_code=return_code,
            error=error,
            report_paths_json=json.dumps(self._collect_report_paths(), ensure_ascii=False),
        )

    def _infer_stage(self, line: str) -> str | None:
        text = line.lower()
        if "rss" in text:
            return "rss"
        if "ai" in text:
            return "ai"
        if "html" in text or "report" in text:
            return "report"
        if "通知" in line or "push" in text:
            return "notify"
        if "爬" in line or "crawl" in text or "fetch" in text:
            return "crawl"
        return None

    def _collect_report_paths(self) -> list[str]:
        report_paths: list[str] = []
        latest_dir = self.output_dir / "html" / "latest"
        if latest_dir.exists():
            for file in sorted(latest_dir.glob("*.html")):
                report_paths.append(str(file))
        index_file = self.output_dir / "index.html"
        if index_file.exists():
            report_paths.append(str(index_file))
        return report_paths

    def _append_log(self, job_id: str, content: str) -> None:
        now = _utc_now()
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COALESCE(MAX(line_no), 0) + 1 AS next_line FROM job_logs WHERE job_id = ?",
                (job_id,),
            ).fetchone()
            line_no = int(row["next_line"]) if row else 1
            conn.execute(
                """
                INSERT INTO job_logs (job_id, line_no, content, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (job_id, line_no, content, now),
            )

    def _update_job(self, job_id: str, **fields: Any) -> None:
        if not fields:
            return
        fields["updated_at"] = _utc_now()
        invalid_keys = sorted({key for key in fields if key not in JOB_UPDATE_FIELDS})
        if invalid_keys:
            raise ValueError(f"Unsupported job fields: {', '.join(invalid_keys)}")
        keys = list(fields.keys())
        assignments = ", ".join([f'"{key}" = ?' for key in keys])
        values = [fields[key] for key in keys]
        values.append(job_id)
        with self._connect() as conn:
            conn.execute(
                f"UPDATE jobs SET {assignments} WHERE id = ?",
                values,
            )

    def _row_to_job(self, row: sqlite3.Row) -> dict[str, Any]:
        command: list[str] = []
        report_paths: list[str] = []
        try:
            command = json.loads(row["command_json"] or "[]")
        except (TypeError, json.JSONDecodeError):
            command = []
        try:
            report_paths = json.loads(row["report_paths_json"] or "[]")
        except (TypeError, json.JSONDecodeError):
            report_paths = []

        return {
            "id": row["id"],
            "status": row["status"],
            "stage": row["stage"],
            "command": command,
            "created_at": row["created_at"],
            "started_at": row["started_at"],
            "finished_at": row["finished_at"],
            "duration_seconds": row["duration_seconds"],
            "exit_code": row["exit_code"],
            "error": row["error"] or "",
            "retry_source_job_id": row.get("retry_source_job_id", None),
            "retry_strategy": row.get("retry_strategy", None),
            "retry_strategy_note": row.get("retry_strategy_note", None),
            "report_paths": report_paths,
            "updated_at": row["updated_at"],
        }

    def _row_to_workflow_template(self, row: sqlite3.Row) -> dict[str, Any]:
        scope_raw = str(row["scope"] or "all").strip().lower()
        scope = scope_raw if scope_raw in WORKFLOW_SCOPES else "all"
        return {
            "id": str(row["id"]),
            "name": str(row["name"]),
            "scope": scope,
            "force_ai": bool(row["force_ai"]),
            "force_push": bool(row["force_push"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def list_workflow_templates(self, limit: int = 20) -> list[dict[str, Any]]:
        safe_limit = max(1, min(int(limit), 100))
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM workflow_templates
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (safe_limit,),
            ).fetchall()
        return [self._row_to_workflow_template(row) for row in rows]

    def get_workflow_template(self, template_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM workflow_templates WHERE id = ?",
                (template_id,),
            ).fetchone()
        if not row:
            return None
        return self._row_to_workflow_template(row)

    def save_workflow_template(
        self,
        name: str,
        scope: str = "all",
        force_ai: bool = False,
        force_push: bool = False,
        template_id: str | None = None,
    ) -> dict[str, Any]:
        safe_name = str(name or "").strip()[:48]
        if not safe_name:
            raise ValueError("template name is required")

        scope_raw = str(scope or "all").strip().lower()
        safe_scope = scope_raw if scope_raw in WORKFLOW_SCOPES else "all"
        safe_force_ai = 1 if force_ai else 0
        safe_force_push = 1 if force_push else 0
        now = _utc_now()

        with self._connect() as conn:
            target_id = str(template_id or "").strip()
            if target_id:
                row = conn.execute(
                    "SELECT id FROM workflow_templates WHERE id = ?",
                    (target_id,),
                ).fetchone()
                if row:
                    conn.execute(
                        """
                        UPDATE workflow_templates
                        SET name = ?, scope = ?, force_ai = ?, force_push = ?, updated_at = ?
                        WHERE id = ?
                        """,
                        (safe_name, safe_scope, safe_force_ai, safe_force_push, now, target_id),
                    )
                else:
                    target_id = ""

            if not target_id:
                existing = conn.execute(
                    "SELECT id FROM workflow_templates WHERE LOWER(name) = LOWER(?)",
                    (safe_name,),
                ).fetchone()
                if existing:
                    target_id = str(existing["id"])
                    conn.execute(
                        """
                        UPDATE workflow_templates
                        SET scope = ?, force_ai = ?, force_push = ?, updated_at = ?
                        WHERE id = ?
                        """,
                        (safe_scope, safe_force_ai, safe_force_push, now, target_id),
                    )
                else:
                    target_id = uuid.uuid4().hex[:12]
                    conn.execute(
                        """
                        INSERT INTO workflow_templates (
                            id, name, scope, force_ai, force_push, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            target_id,
                            safe_name,
                            safe_scope,
                            safe_force_ai,
                            safe_force_push,
                            now,
                            now,
                        ),
                    )

            overflow_rows = conn.execute(
                """
                SELECT id
                FROM workflow_templates
                ORDER BY updated_at DESC
                LIMIT -1 OFFSET 50
                """
            ).fetchall()
            overflow_ids = [str(row["id"]) for row in overflow_rows]
            if overflow_ids:
                placeholders = ", ".join(["?"] * len(overflow_ids))
                conn.execute(
                    f"DELETE FROM workflow_templates WHERE id IN ({placeholders})",
                    overflow_ids,
                )

        result = self.get_workflow_template(target_id)
        if not result:
            raise RuntimeError("failed to save workflow template")
        return result

    def delete_workflow_template(self, template_id: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id FROM workflow_templates WHERE id = ?",
                (template_id,),
            ).fetchone()
            if not row:
                return False
            conn.execute(
                "DELETE FROM workflow_templates WHERE id = ?",
                (template_id,),
            )
        return True

    def clear_workflow_templates(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS total FROM workflow_templates").fetchone()
            total = int(row["total"]) if row else 0
            conn.execute("DELETE FROM workflow_templates")
        return total

    def list_jobs(self, limit: int = 50) -> list[dict[str, Any]]:
        safe_limit = max(1, min(int(limit), 200))
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM jobs
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (safe_limit,),
            ).fetchall()
        return [self._row_to_job(row) for row in rows]

    def list_jobs_page(
        self,
        page: int = 1,
        page_size: int = 20,
        statuses: Sequence[str] | None = None,
        query: str | None = None,
    ) -> dict[str, Any]:
        safe_page = max(1, int(page))
        safe_page_size = max(1, min(int(page_size), 200))
        offset = (safe_page - 1) * safe_page_size

        where_clauses: list[str] = []
        params: list[Any] = []

        normalized_statuses = [
            str(status).strip().lower() for status in (statuses or []) if str(status).strip()
        ]
        if normalized_statuses:
            placeholders = ", ".join(["?"] * len(normalized_statuses))
            where_clauses.append(f"LOWER(status) IN ({placeholders})")
            params.extend(normalized_statuses)

        keyword = (query or "").strip()
        if keyword:
            like = f"%{keyword.lower()}%"
            where_clauses.append(
                "("
                "LOWER(id) LIKE ? OR "
                "LOWER(status) LIKE ? OR "
                "LOWER(stage) LIKE ? OR "
                "LOWER(command_json) LIKE ? OR "
                "LOWER(error) LIKE ?"
                ")"
            )
            params.extend([like, like, like, like, like])

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        with self._connect() as conn:
            total_row = conn.execute(
                f"SELECT COUNT(*) AS total FROM jobs {where_sql}",
                params,
            ).fetchone()
            total = int(total_row["total"]) if total_row else 0

            rows = conn.execute(
                f"""
                SELECT *
                FROM jobs
                {where_sql}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                [*params, safe_page_size, offset],
            ).fetchall()

        total_pages = max(1, (total + safe_page_size - 1) // safe_page_size) if total else 1
        items = [self._row_to_job(row) for row in rows]
        return {
            "items": items,
            "total": total,
            "page": safe_page,
            "page_size": safe_page_size,
            "total_pages": total_pages,
        }

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM jobs WHERE id = ?",
                (job_id,),
            ).fetchone()
        if not row:
            return None
        return self._row_to_job(row)

    def get_job_stage_trace(self, job_id: str) -> dict[str, Any]:
        job = self.get_job(job_id)
        if not job:
            return {
                "stage_timestamps": {},
                "latest_stage": None,
                "failure_stage": None,
            }

        stage_timestamps: dict[str, str] = {}
        created_at = str(job.get("created_at") or "").strip()
        started_at = str(job.get("started_at") or "").strip()
        finished_at = str(job.get("finished_at") or "").strip()

        if created_at:
            stage_timestamps["queued"] = created_at
        if started_at:
            stage_timestamps["starting"] = started_at

        latest_inferred: str | None = None
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT content, created_at
                FROM job_logs
                WHERE job_id = ?
                ORDER BY line_no ASC
                """,
                (job_id,),
            ).fetchall()

        for row in rows:
            content = str(row["content"] or "")
            inferred = self._infer_stage(content)
            if not inferred:
                continue
            latest_inferred = inferred
            if inferred not in stage_timestamps:
                stage_timestamps[inferred] = str(row["created_at"] or "")

        status = str(job.get("status") or "").strip().lower()
        stage_raw = str(job.get("stage") or "").strip().lower()

        latest_stage = stage_raw if stage_raw in JOB_STAGE_SEQUENCE else None
        if not latest_stage:
            latest_stage = latest_inferred or ("starting" if started_at else "queued")

        if status == "success" and finished_at:
            stage_timestamps["finished"] = finished_at

        failure_stage: str | None = None
        if status == "failed":
            failure_stage = (
                latest_stage
                if latest_stage in JOB_STAGE_SEQUENCE and latest_stage != "finished"
                else None
            )
            if not failure_stage:
                failure_stage = latest_inferred or ("starting" if started_at else "queued")

        return {
            "stage_timestamps": stage_timestamps,
            "latest_stage": latest_stage,
            "failure_stage": failure_stage,
        }

    def get_job_logs(self, job_id: str, tail: int | None = None) -> list[str]:
        with self._connect() as conn:
            if tail is not None:
                safe_tail = max(1, min(int(tail), 5000))
                rows = conn.execute(
                    """
                    SELECT content
                    FROM (
                        SELECT content, line_no
                        FROM job_logs
                        WHERE job_id = ?
                        ORDER BY line_no DESC
                        LIMIT ?
                    )
                    ORDER BY line_no ASC
                    """,
                    (job_id, safe_tail),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT content FROM job_logs WHERE job_id = ? ORDER BY line_no ASC",
                    (job_id,),
                ).fetchall()
        return [row["content"] for row in rows]

    def get_run_log_text(self, job_id: str | None = None) -> str:
        target = job_id
        if not target:
            latest = self.get_latest_job()
            target = latest["id"] if latest else None
        if not target:
            return ""
        return "\n".join(self.get_job_logs(target))

    def get_latest_job(self) -> dict[str, Any] | None:
        jobs = self.list_jobs(limit=1)
        return jobs[0] if jobs else None

    def get_running_job_id(self) -> str | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id
                FROM jobs
                WHERE status = 'running'
                ORDER BY started_at DESC
                LIMIT 1
                """
            ).fetchone()
        if not row:
            return None
        return str(row["id"])

    def get_queue_positions(self) -> dict[str, int]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id
                FROM jobs
                WHERE status = 'queued'
                ORDER BY created_at ASC
                """
            ).fetchall()

        positions: dict[str, int] = {}
        for index, row in enumerate(rows, start=1):
            positions[str(row["id"])] = index
        return positions

    def clear_final_jobs(self, keep_latest: int = 20, limit: int = 2000) -> int:
        safe_keep = max(0, int(keep_latest))
        safe_limit = max(1, min(int(limit), 10000))
        statuses = sorted(FINAL_STATUSES)

        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id
                FROM jobs
                WHERE status IN (?, ?, ?)
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                (statuses[0], statuses[1], statuses[2], safe_limit, safe_keep),
            ).fetchall()

            job_ids = [str(row["id"]) for row in rows]
            if not job_ids:
                return 0

            placeholders = ", ".join(["?"] * len(job_ids))
            conn.execute(
                f"DELETE FROM job_logs WHERE job_id IN ({placeholders})",
                job_ids,
            )
            conn.execute(
                f"DELETE FROM jobs WHERE id IN ({placeholders})",
                job_ids,
            )

        return len(job_ids)

    def get_clearable_final_jobs_count(
        self, keep_latest: int = 20, limit: int = 2000
    ) -> dict[str, int]:
        safe_keep = max(0, int(keep_latest))
        safe_limit = max(1, min(int(limit), 10000))
        statuses = sorted(FINAL_STATUSES)

        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS total
                FROM jobs
                WHERE status IN (?, ?, ?)
                """,
                (statuses[0], statuses[1], statuses[2]),
            ).fetchone()

        total_final = int(row["total"]) if row else 0
        clearable = max(0, total_final - safe_keep)
        planned = min(clearable, safe_limit)
        return {
            "total_final": total_final,
            "clearable": clearable,
            "planned": planned,
            "keep_latest": safe_keep,
            "limit": safe_limit,
        }

    def cancel_job(self, job_id: str) -> bool:
        job = self.get_job(job_id)
        if not job:
            return False
        if job["status"] in FINAL_STATUSES:
            return False

        if job["status"] == "queued":
            self._update_job(job_id, status="cancelled", stage="cancelled", finished_at=_utc_now())
            self._append_log(job_id, "[job] cancelled before start")
            return True

        self._update_job(job_id, status="cancelling", stage="cancelling")
        process = None
        with self._lock:
            process = self._processes.get(job_id)

        if process is not None:
            try:
                process.terminate()
                process.wait(timeout=5)
            except Exception:
                with contextlib.suppress(Exception):
                    process.kill()

        self._update_job(job_id, status="cancelled", stage="cancelled", finished_at=_utc_now())
        self._append_log(job_id, "[job] cancelled")
        return True

    def get_legacy_status(self, job_id: str | None = None) -> dict[str, Any]:
        target_job: dict[str, Any] | None = None
        if job_id:
            target_job = self.get_job(job_id)

        if not target_job:
            running_id = self.get_running_job_id()
            if running_id:
                target_job = self.get_job(running_id)

        if not target_job:
            target_job = self.get_latest_job()

        if not target_job:
            return {
                "running": False,
                "last_run": None,
                "log": [],
                "job_id": None,
                "status": None,
            }

        target_id = target_job["id"]
        logs = self.get_job_logs(target_id, tail=50)
        last_run = (
            target_job.get("finished_at")
            or target_job.get("started_at")
            or target_job.get("created_at")
        )
        return {
            "running": target_job.get("status") in ACTIVE_STATUSES,
            "last_run": last_run,
            "log": logs,
            "job_id": target_id,
            "status": target_job.get("status"),
            "stage": target_job.get("stage"),
        }
