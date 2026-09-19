# PulseRadar Code Review

This document contains a comprehensive review of the PulseRadar codebase, focusing on architecture, security, reliability, test coverage, performance, and documentation.

## CRITICAL

### 1. JobManager SQL Injection Vulnerability in Schema Migrations
- **Path:** `trendradar/webui/job_manager.py` (Lines 163-173)
- **Impact:** The `_ensure_jobs_table_columns` function uses f-strings to build an `ALTER TABLE` query. Although it checks `column_name` against a whitelist (`_ALLOWED_MIGRATION_COLUMNS`), it does not properly sanitize it or use parameterized queries where strictly possible, and more importantly, if the whitelist is ever expanded or if other similar dynamic SQL generation exists, it introduces a severe risk of SQL injection.
- **Fix Suggestion:** While `ALTER TABLE` cannot use standard parameterized `?` bindings in SQLite, ensure that `column_name` and `column_type` are strictly validated against a hardcoded set of safe characters (e.g., regex `^[a-zA-Z0-9_]+$`) and avoid f-strings for SQL query construction where possible.

## HIGH

### 1. Insufficient Test Coverage
- **Path:** `pyproject.toml` (Line 38)
- **Impact:** The project currently enforces a very low test coverage floor of 27% (`--cov-fail-under=27`). Low test coverage increases the risk of regressions and undiscovered bugs, especially in critical path features like crawler parsing and AI analysis.
- **Fix Suggestion:** Write unit tests for core modules (like `trendradar/core/analyzer.py`, `trendradar/core/frequency.py`, and `trendradar/webui/job_manager.py`). Gradually increase the `--cov-fail-under` threshold to at least 70-80% as coverage improves.

### 2. Insecure Subprocess Execution in JobManager
- **Path:** `trendradar/webui/job_manager.py` (Line 344)
- **Impact:** The `_run_process` method uses `subprocess.Popen` to execute background jobs. While `shell=True` is not used, the `command` argument is built dynamically from user payloads in the Web UI (`build_run_command_from_payload` in `trendradar/webui/helpers.py`). If the payload structure is not strictly validated, it could lead to arbitrary command execution.
- **Fix Suggestion:** Strictly validate and sanitize all elements of the `command` list built in `build_run_command_from_payload`. Ensure that only predefined, safe arguments can be passed to the python executable.

## MEDIUM

### 1. SQLite N+1 Queries and Concurrency
- **Path:** `trendradar/storage/sqlite_mixin.py`
- **Impact:** The SQLite mixin executes multiple queries inside loops (e.g., fetching platform IDs and inserting records). While WAL mode is enabled and helps with concurrency, executing many individual queries in loops can become a performance bottleneck as the dataset grows.
- **Fix Suggestion:** Use `executemany` for batch inserts and updates to minimize the overhead of individual query executions.

### 2. Missing Authentication by Default
- **Path:** `trendradar/webui/app.py`
- **Impact:** The Web UI has an authentication system (`trendradar/webui/auth.py`), but it can be disabled via environment variables (`TREND_RADAR_WEBUI_DISABLE_AUTH`). If users deploy this publicly without properly configuring the initial setup or accidentally disabling auth, their configuration and data could be exposed.
- **Fix Suggestion:** Add a strong warning in the documentation about the risks of disabling authentication. Ensure that the default deployment mode strictly enforces the initial `/setup` flow.

## LOW

### 1. Hardcoded Timezone Fallback
- **Path:** `trendradar/utils/time.py` (Line 15)
- **Impact:** The fallback timezone is hardcoded to `Asia/Shanghai`. While acceptable for a predominantly Chinese-speaking user base, it may cause confusion for international users if their configuration is missing or invalid.
- **Fix Suggestion:** Use the system's local timezone (e.g., via `tzlocal` package or `datetime.now().astimezone().tzinfo`) as a safer and more universal fallback.

### 2. File Path Handling
- **Path:** `trendradar/webui/app.py` (Line 35)
- **Impact:** The code uses `Path(output_path) if output_path else (root_dir / "output")`. While `Path` handles cross-platform paths well, ensuring absolute paths are used consistently across the application can prevent subtle bugs when the working directory changes.
- **Fix Suggestion:** Always call `.resolve()` when initializing paths for configuration directories, output directories, and SQLite databases to ensure they are absolute.

## SUMMARY

The PulseRadar architecture is generally well-designed, with a clear separation of concerns between crawling, storage, and presentation. The introduction of the Web UI is a great addition but requires careful handling of user inputs and background processes. Expanding test coverage should be the primary focus for future development to ensure long-term maintainability.
