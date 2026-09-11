# PulseRadar Code Review

This document contains a comprehensive review of the PulseRadar codebase, focusing on architecture, security, reliability, test coverage, performance, and documentation.

## HIGH

### 1. Command Injection Risk from Unvalidated `command_json` execution
- **Path:** `trendradar/webui/job_manager.py` (Line 344)
- **Impact:** The `_run_process` method uses `subprocess.Popen` to execute background jobs based on `command_json` loaded from the database. While the payload builder (`build_run_command_from_payload`) implements scope whitelisting and boolean flags, the execution engine (`_run_process`) lacks argv validation. If an attacker manages to modify the database or bypass the payload builder, arbitrary commands can be executed.
- **Fix Suggestion:** Add strict `argv` validation in `_run_process` to ensure the command being executed is strictly limited to the `sys.executable` and `-m trendradar` module.

### 2. Secrets Leakage in Job Database
- **Path:** `trendradar/webui/job_manager.py` (Line 293)
- **Impact:** When a background job is enqueued, the entire configuration file (YAML) is read and stored as plain text in the `config_snapshot` column of the database. This includes sensitive credentials like API keys, tokens, and webhooks.
- **Fix Suggestion:** Redact sensitive fields (e.g., keys containing `api_key`, `token`, `secret`, `password`, `webhook`) before saving the snapshot to the database.

### 3. Server-Side Request Forgery (SSRF) in Test Source API
- **Path:** `trendradar/webui/routes_misc.py` (Line 227)
- **Impact:** The `/api/test-source` endpoint accepts a user-provided URL for RSS testing and parses it directly using `feedparser.parse()`. There is no validation of the URL scheme, which could allow an attacker to probe internal network services or read local files (e.g., `file://`).
- **Fix Suggestion:** Validate the URL to ensure it starts with `http://` or `https://` before passing it to `feedparser`.

### 4. Unauthenticated Exposure of MCP Server and Static Web Server
- **Path:** `docker/Dockerfile.mcp`, `docker/manage.py`, `start-http.sh`, `start-http.bat`
- **Impact:** The MCP server binds to `0.0.0.0:3333` by default, exposing its functionality without built-in authentication. Similarly, `docker/manage.py` starts a static `http.server` bound to `0.0.0.0` on port 8080 without any authentication, potentially exposing generated reports to the public if the port is accessible.
- **Fix Suggestion:** Bind the MCP server to `127.0.0.1` by default in scripts and Docker files to limit exposure, and ensure the static web server is strictly documented as insecure or replaced with the authenticated Flask WebUI.

## MEDIUM

### 1. SQLite N+1 Queries and Concurrency
- **Path:** `trendradar/storage/sqlite_mixin.py`
- **Impact:** The SQLite mixin executes multiple queries inside loops. While WAL mode is enabled, executing many individual queries in loops can become a performance bottleneck.
- **Fix Suggestion:** Use `executemany` for batch inserts and updates to minimize the overhead.

### 2. Disabling Authentication Exposes Application
- **Path:** `trendradar/webui/auth.py`
- **Impact:** While authentication is enabled by default, setting the environment variable `TREND_RADAR_WEBUI_DISABLE_AUTH=1` explicitly disables it. If deployed publicly with this flag set, sensitive configuration and data are exposed.
- **Fix Suggestion:** Document the risks of using this flag clearly, especially in production environments.

## LOW

### 1. Hardcoded Timezone Fallback
- **Path:** `trendradar/utils/time.py` (Line 17)
- **Impact:** The fallback timezone is hardcoded to `Asia/Shanghai`. This may cause confusion for international users.
- **Fix Suggestion:** Use the system's local timezone as a safer fallback.

### 2. File Path Handling
- **Path:** `trendradar/webui/app.py` (Line 48)
- **Impact:** The code uses `Path(output_path) if output_path else (root_dir / "output")`. Ensuring absolute paths are used consistently across the application can prevent subtle bugs.
- **Fix Suggestion:** Call `.resolve()` when initializing paths.

## SUMMARY

The PulseRadar architecture separates concerns well. However, attention must be paid to security around user inputs, SSRF vectors, and secure defaults for network bindings (like MCP and static servers). Test coverage is intentionally ratcheted at a floor of 27% (in `pyproject.toml` Line 48), and core tests like `tests/test_analyzer.py` already exist, establishing a baseline to be improved incrementally.
