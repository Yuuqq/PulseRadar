"""Handler-level tests for ConfigManagementTools.

Strategy: patch DataService to return a controlled config dict. The public
surface is a single method: get_current_config(section=...).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from mcp_server.tools.config_mgmt import ConfigManagementTools


def _make_tools(tmp_path, config_return):
    with patch("mcp_server.tools.config_mgmt.DataService") as mock_cls:
        mock_svc = MagicMock()
        mock_svc.get_current_config.return_value = config_return
        mock_cls.return_value = mock_svc
        return ConfigManagementTools(project_root=str(tmp_path))


def test_get_current_config_all_returns_success(tmp_path):
    tools = _make_tools(
        tmp_path,
        config_return={
            "crawler": {"platforms": ["zhihu"]},
            "push": {},
            "keywords": {"word_groups": []},
            "weights": {"rank_weight": 0.6},
        },
    )

    result = tools.get_current_config(section="all")

    assert result["success"] is True
    assert result["config"]["crawler"]["platforms"] == ["zhihu"]
    assert result["section"] == "all"


def test_get_current_config_section_crawler(tmp_path):
    tools = _make_tools(tmp_path, config_return={"platforms": ["zhihu", "weibo"]})

    result = tools.get_current_config(section="crawler")

    assert result["success"] is True
    assert result["section"] == "crawler"
    assert result["config"]["platforms"] == ["zhihu", "weibo"]


def test_get_current_config_invalid_section_returns_error(tmp_path):
    """validate_config_section rejects unknown sections."""
    tools = _make_tools(tmp_path, config_return={})

    result = tools.get_current_config(section="not_a_valid_section")

    assert result["success"] is False
    assert result["error"]["code"] == "INVALID_PARAMETER"


def test_get_current_config_none_defaults_to_all(tmp_path):
    tools = _make_tools(tmp_path, config_return={"any": "value"})

    result = tools.get_current_config(section=None)

    assert result["success"] is True
    # validate_config_section replaces None with "all"
    assert result["section"] == "all"
