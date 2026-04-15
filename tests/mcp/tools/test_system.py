"""Handler-level tests for SystemManagementTools.

Strategy: patch DataService + external HTTP; verify get_system_status shape and
check_version handles HTTP failures gracefully.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from mcp_server.tools.system import SystemManagementTools


def _make_tools(tmp_path):
    with patch("mcp_server.tools.system.DataService") as mock_cls:
        mock_svc = MagicMock()
        mock_cls.return_value = mock_svc
        return SystemManagementTools(project_root=str(tmp_path))


def test_get_system_status_returns_success_shape(tmp_path):
    tools = _make_tools(tmp_path)
    tools.data_service.get_system_status.return_value = {
        "system": {"version": "1.0.0", "project_root": str(tmp_path)},
        "data": {"total_storage": "0.00 MB", "oldest_record": None, "latest_record": None},
        "cache": {"total_entries": 0, "oldest_entry_age": 0, "newest_entry_age": 0},
        "health": "healthy",
    }

    result = tools.get_system_status()

    assert result["success"] is True
    assert result["data"]["health"] == "healthy"
    assert result["data"]["system"]["version"] == "1.0.0"


def test_get_system_status_handles_data_service_failure(tmp_path):
    tools = _make_tools(tmp_path)
    tools.data_service.get_system_status.side_effect = RuntimeError("db unavailable")

    result = tools.get_system_status()

    assert result["success"] is False
    assert result["error"]["code"] == "INTERNAL_ERROR"
    assert "db unavailable" in result["error"]["message"]


def test_check_version_missing_config_returns_error(tmp_path):
    """No config.yaml under project_root -> CONFIG_NOT_FOUND error code."""
    tools = _make_tools(tmp_path)
    # tmp_path is empty — config/config.yaml does NOT exist

    result = tools.check_version()

    assert result["success"] is False
    assert result["error"]["code"] == "CONFIG_NOT_FOUND"


def test_html_escape_basic(tmp_path):
    tools = _make_tools(tmp_path)

    escaped = tools._html_escape('<script>alert("x")</script>')

    assert "<" not in escaped
    assert "&lt;" in escaped
    assert "&quot;" in escaped or "&#x27;" in escaped or "&amp;" in escaped
