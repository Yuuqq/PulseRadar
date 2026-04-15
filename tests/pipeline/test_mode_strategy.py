"""
Pipeline integration tests for execute_mode_strategy across all 5 mode-strategy branches.

These tests call the REAL execute_mode_strategy function with a REAL AppContext and
REAL SQLite storage in tmp_path. Only external I/O boundaries are mocked:
- HTTP via responses (not directly used here -- no crawling in mode_strategy)
- AI client via patched config (AI_ANALYSIS.ENABLED = False)
- Notification channels via MagicMock send_notification_fn
- run_analysis_pipeline_fn creates real HTML files via html_report_factory

Pitfall 7: Every test passes should_open_browser=False and is_docker_container=False.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock

import pytest

from trendradar.core.mode_strategy import execute_mode_strategy


def _assert_notification_kwargs(send_notification_fn: MagicMock) -> None:
    """Shared assertion for notification callback keyword arg shapes (D-16b)."""
    assert send_notification_fn.called, "send_notification_fn should have been called"
    # send_notification_fn is called with 3 positional args + keyword args
    call_args = send_notification_fn.call_args
    # Positional: stats, report_type, report_mode
    assert len(call_args.args) >= 3, (
        f"Expected at least 3 positional args, got {len(call_args.args)}"
    )
    stats_arg = call_args.args[0]
    assert isinstance(stats_arg, list), f"stats should be a list, got {type(stats_arg)}"

    call_kwargs = call_args.kwargs
    assert "failed_ids" in call_kwargs
    assert "id_to_name" in call_kwargs
    assert "html_file_path" in call_kwargs


def _assert_html_content(html_file: str, *markers: str) -> None:
    """Shared assertion for HTML file content checks (D-16a).

    Verifies the file exists and contains all specified substring markers.
    """
    assert html_file is not None, "html_file path should not be None"
    assert os.path.isfile(html_file), f"HTML file does not exist: {html_file}"
    with open(html_file, encoding="utf-8") as f:
        content = f.read()
    for marker in markers:
        assert marker in content, (
            f"HTML file missing expected marker '{marker}'. "
            f"File: {html_file}, Content length: {len(content)}"
        )


class TestIncrementalMode:
    """Case 1: incremental with data -- uses current data directly (lines 440-459)."""

    def test_incremental_with_data(
        self,
        pipeline_ctx,
        pipeline_config,
        sample_results,
        sample_id_to_name,
        mock_callbacks,
    ):
        storage_manager = pipeline_ctx.get_storage_manager()
        run_pipeline_fn = mock_callbacks["run_analysis_pipeline_fn_factory"]("incremental")

        html_file = execute_mode_strategy(
            ctx=pipeline_ctx,
            storage_manager=storage_manager,
            report_mode="incremental",
            rank_threshold=50,
            update_info=None,
            proxy_url=None,
            is_docker_container=False,
            should_open_browser=False,
            mode_strategy={"should_send_notification": True, "report_type": "full"},
            results=sample_results,
            id_to_name=sample_id_to_name,
            failed_ids=[],
            load_analysis_data_fn=mock_callbacks["load_analysis_data_fn"],
            prepare_current_title_info_fn=mock_callbacks["prepare_current_title_info_fn"],
            run_analysis_pipeline_fn=run_pipeline_fn,
            prepare_standalone_data_fn=mock_callbacks["prepare_standalone_data_fn"],
            send_notification_fn=mock_callbacks["send_notification_fn"],
        )

        # (a) Return value is a valid file path
        assert html_file is not None
        assert os.path.isfile(html_file)

        # (b) run_analysis_pipeline_fn was called
        assert run_pipeline_fn.called

        # (c) prepare_current_title_info_fn was called (incremental uses current data)
        assert mock_callbacks["prepare_current_title_info_fn"].called

        # (d) load_analysis_data_fn was NOT called (incremental never loads history)
        assert not mock_callbacks["load_analysis_data_fn"].called

        # (e) send_notification_fn was called
        assert mock_callbacks["send_notification_fn"].called

        # (f) HTML file content check: 3+ substring markers
        _assert_html_content(html_file, "TrendRadar", "report-mode", "incremental")

        # (g) Notification callback keyword arg shapes
        _assert_notification_kwargs(mock_callbacks["send_notification_fn"])
        call_args = mock_callbacks["send_notification_fn"].call_args
        assert call_args.args[1] == "full"  # report_type
        assert call_args.args[2] == "incremental"  # report_mode


class TestCurrentMode:
    """Case 2 and 3: current mode with/without history."""

    def test_current_with_history(
        self,
        pipeline_ctx,
        pipeline_config,
        sample_results,
        sample_id_to_name,
        mock_callbacks,
    ):
        """Case 2: current with history -- uses historical data (lines 339-377)."""
        storage_manager = pipeline_ctx.get_storage_manager()
        run_pipeline_fn = mock_callbacks["run_analysis_pipeline_fn_factory"]("current")

        # Set up load_analysis_data_fn to return a 7-tuple (historical data)
        mock_callbacks["load_analysis_data_fn"].return_value = (
            {
                "hist_platform": {
                    "Hist Title": {
                        "ranks": [1],
                        "url": "http://hist.com",
                        "mobileUrl": "",
                    },
                },
            },
            {"hist_platform": "Historical Platform"},
            {"hist_platform": {"Hist Title": {"first_seen": "2026-04-13"}}},
            {"hist_platform": ["Hist Title"]},
            None,
            None,
            None,
        )

        html_file = execute_mode_strategy(
            ctx=pipeline_ctx,
            storage_manager=storage_manager,
            report_mode="current",
            rank_threshold=50,
            update_info=None,
            proxy_url=None,
            is_docker_container=False,
            should_open_browser=False,
            mode_strategy={"should_send_notification": True, "report_type": "current_report"},
            results=sample_results,
            id_to_name=sample_id_to_name,
            failed_ids=[],
            load_analysis_data_fn=mock_callbacks["load_analysis_data_fn"],
            prepare_current_title_info_fn=mock_callbacks["prepare_current_title_info_fn"],
            run_analysis_pipeline_fn=run_pipeline_fn,
            prepare_standalone_data_fn=mock_callbacks["prepare_standalone_data_fn"],
            send_notification_fn=mock_callbacks["send_notification_fn"],
        )

        # (a) Return value is not None
        assert html_file is not None

        # (b) load_analysis_data_fn was called
        assert mock_callbacks["load_analysis_data_fn"].called

        # (c) run_analysis_pipeline_fn was called with historical data
        assert run_pipeline_fn.called
        first_positional_arg = run_pipeline_fn.call_args.args[0]
        assert "hist_platform" in first_positional_arg, (
            "run_analysis_pipeline_fn should receive historical results (hist_platform)"
        )

        # (d) send_notification_fn was called
        assert mock_callbacks["send_notification_fn"].called

        # (e) HTML file content check
        _assert_html_content(html_file, "TrendRadar", "current")

        # (f) Notification kwargs
        _assert_notification_kwargs(mock_callbacks["send_notification_fn"])

    def test_current_without_history_raises(
        self,
        pipeline_ctx,
        pipeline_config,
        sample_results,
        sample_id_to_name,
        mock_callbacks,
    ):
        """Case 3: current without history -- raises RuntimeError (line 380)."""
        storage_manager = pipeline_ctx.get_storage_manager()
        run_pipeline_fn = mock_callbacks["run_analysis_pipeline_fn_factory"]("current")

        # No history data
        mock_callbacks["load_analysis_data_fn"].return_value = None

        with pytest.raises(RuntimeError, match="数据一致性检查失败"):
            execute_mode_strategy(
                ctx=pipeline_ctx,
                storage_manager=storage_manager,
                report_mode="current",
                rank_threshold=50,
                update_info=None,
                proxy_url=None,
                is_docker_container=False,
                should_open_browser=False,
                mode_strategy={"should_send_notification": True, "report_type": "full"},
                results=sample_results,
                id_to_name=sample_id_to_name,
                failed_ids=[],
                load_analysis_data_fn=mock_callbacks["load_analysis_data_fn"],
                prepare_current_title_info_fn=mock_callbacks["prepare_current_title_info_fn"],
                run_analysis_pipeline_fn=run_pipeline_fn,
                prepare_standalone_data_fn=mock_callbacks["prepare_standalone_data_fn"],
                send_notification_fn=mock_callbacks["send_notification_fn"],
            )

        # (a) RuntimeError raised (verified by pytest.raises above)

        # (b) run_analysis_pipeline_fn was NOT called
        assert not run_pipeline_fn.called

        # (c) send_notification_fn was NOT called
        assert not mock_callbacks["send_notification_fn"].called


class TestDailyMode:
    """Case 4 and 5: daily mode with/without history."""

    def test_daily_with_history(
        self,
        pipeline_ctx,
        pipeline_config,
        sample_results,
        sample_id_to_name,
        mock_callbacks,
    ):
        """Case 4: daily with history -- uses historical data (lines 382-418)."""
        storage_manager = pipeline_ctx.get_storage_manager()
        run_pipeline_fn = mock_callbacks["run_analysis_pipeline_fn_factory"]("daily")

        # Set up load_analysis_data_fn with historical data
        mock_callbacks["load_analysis_data_fn"].return_value = (
            {
                "hist_platform": {
                    "Hist Title": {
                        "ranks": [1],
                        "url": "http://hist.com",
                        "mobileUrl": "",
                    },
                },
            },
            {"hist_platform": "Historical Platform"},
            {"hist_platform": {"Hist Title": {"first_seen": "2026-04-13"}}},
            {"hist_platform": ["Hist Title"]},
            None,
            None,
            None,
        )

        html_file = execute_mode_strategy(
            ctx=pipeline_ctx,
            storage_manager=storage_manager,
            report_mode="daily",
            rank_threshold=50,
            update_info=None,
            proxy_url=None,
            is_docker_container=False,
            should_open_browser=False,
            mode_strategy={"should_send_notification": True, "report_type": "daily_report"},
            results=sample_results,
            id_to_name=sample_id_to_name,
            failed_ids=[],
            load_analysis_data_fn=mock_callbacks["load_analysis_data_fn"],
            prepare_current_title_info_fn=mock_callbacks["prepare_current_title_info_fn"],
            run_analysis_pipeline_fn=run_pipeline_fn,
            prepare_standalone_data_fn=mock_callbacks["prepare_standalone_data_fn"],
            send_notification_fn=mock_callbacks["send_notification_fn"],
        )

        # (a) Return value is not None
        assert html_file is not None

        # (b) load_analysis_data_fn was called
        assert mock_callbacks["load_analysis_data_fn"].called

        # (c) run_analysis_pipeline_fn called with historical data
        assert run_pipeline_fn.called
        first_positional_arg = run_pipeline_fn.call_args.args[0]
        assert "hist_platform" in first_positional_arg, (
            "run_analysis_pipeline_fn should receive historical results (hist_platform)"
        )

        # (d) send_notification_fn was called
        assert mock_callbacks["send_notification_fn"].called

        # (e) HTML file content check
        _assert_html_content(html_file, "TrendRadar", "daily")

        # (f) Notification kwargs
        _assert_notification_kwargs(mock_callbacks["send_notification_fn"])

    def test_daily_without_history_falls_back(
        self,
        pipeline_ctx,
        pipeline_config,
        sample_results,
        sample_id_to_name,
        mock_callbacks,
    ):
        """Case 5: daily without history -- falls back to current data (lines 420-438)."""
        storage_manager = pipeline_ctx.get_storage_manager()
        run_pipeline_fn = mock_callbacks["run_analysis_pipeline_fn_factory"]("daily")

        # No history data -> fallback to current
        mock_callbacks["load_analysis_data_fn"].return_value = None

        html_file = execute_mode_strategy(
            ctx=pipeline_ctx,
            storage_manager=storage_manager,
            report_mode="daily",
            rank_threshold=50,
            update_info=None,
            proxy_url=None,
            is_docker_container=False,
            should_open_browser=False,
            mode_strategy={"should_send_notification": True, "report_type": "daily_report"},
            results=sample_results,
            id_to_name=sample_id_to_name,
            failed_ids=[],
            load_analysis_data_fn=mock_callbacks["load_analysis_data_fn"],
            prepare_current_title_info_fn=mock_callbacks["prepare_current_title_info_fn"],
            run_analysis_pipeline_fn=run_pipeline_fn,
            prepare_standalone_data_fn=mock_callbacks["prepare_standalone_data_fn"],
            send_notification_fn=mock_callbacks["send_notification_fn"],
        )

        # (a) Return value is not None
        assert html_file is not None

        # (b) load_analysis_data_fn was called (attempted history load)
        assert mock_callbacks["load_analysis_data_fn"].called

        # (c) prepare_current_title_info_fn was called (fallback to current)
        assert mock_callbacks["prepare_current_title_info_fn"].called

        # (d) run_analysis_pipeline_fn called with CURRENT results (not historical)
        assert run_pipeline_fn.called
        first_positional_arg = run_pipeline_fn.call_args.args[0]
        assert "test_platform" in first_positional_arg, (
            "run_analysis_pipeline_fn should receive current results (test_platform) on fallback"
        )

        # (e) send_notification_fn was called
        assert mock_callbacks["send_notification_fn"].called

        # (f) HTML file content check
        _assert_html_content(html_file, "TrendRadar")

        # (g) Notification kwargs
        _assert_notification_kwargs(mock_callbacks["send_notification_fn"])
