# coding=utf-8
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def pipeline_config(mock_config, tmp_path):
    """Extend mock_config for pipeline integration tests.

    Enables HTML report generation and TXT saving so execute_mode_strategy
    exercises the real ctx.save_titles and HTML file creation paths.
    """
    config = {**mock_config}
    config["STORAGE"] = {
        **mock_config["STORAGE"],
        "FORMATS": {"TXT": True, "HTML": True},
        "LOCAL": {
            "DATA_DIR": str(tmp_path / "output"),
            "RETENTION_DAYS": 0,
        },
    }
    return config


@pytest.fixture
def pipeline_ctx(pipeline_config):
    """Real AppContext with pipeline-specific config.

    Patches ONLY load_frequency_words (Pitfall 6 -- reads config/frequency_words.txt
    from disk which does not exist in test environment). All other AppContext
    methods are REAL and exercised against tmp_path storage.
    """
    from trendradar.context import AppContext
    ctx = AppContext(pipeline_config)
    # Patch load_frequency_words to avoid file I/O (Pitfall 6)
    ctx.load_frequency_words = lambda frequency_file=None: ([], [], [])
    return ctx


@pytest.fixture
def sample_results():
    """Minimal crawl results dict matching the shape execute_mode_strategy expects."""
    return {
        "test_platform": {
            "Test News Title": {
                "ranks": [1],
                "url": "http://test.com/news1",
                "mobileUrl": "",
            },
            "Another News Item": {
                "ranks": [2],
                "url": "http://test.com/news2",
                "mobileUrl": "",
            },
        }
    }


@pytest.fixture
def sample_id_to_name():
    """Platform ID to display name mapping."""
    return {"test_platform": "Test Platform"}


@pytest.fixture
def html_report_factory(tmp_path):
    """Factory that creates an HTML report file with known content markers.

    Returns a callable that accepts report_mode and creates a file
    with stable substring markers for assertion.
    """
    def _create(report_mode: str = "incremental") -> str:
        html_dir = tmp_path / "output" / "html"
        html_dir.mkdir(parents=True, exist_ok=True)
        html_file = str(html_dir / f"report_{report_mode}.html")
        content = (
            f"<html><head><title>TrendRadar Report</title></head>"
            f"<body>"
            f'<div class="report-header">TrendRadar Analysis</div>'
            f'<div class="report-mode">{report_mode}</div>'
            f'<div class="platform-section">Test Platform</div>'
            f'<div class="news-item">Test News Title</div>'
            f"</body></html>"
        )
        with open(html_file, "w", encoding="utf-8") as f:
            f.write(content)
        return html_file
    return _create


@pytest.fixture
def mock_callbacks(html_report_factory):
    """Create the callback function mocks for execute_mode_strategy.

    Returns a dict of callback names to MagicMock/callable objects.
    Each callback returns structurally correct data matching the real
    function contracts.
    """
    mock_send = MagicMock(name="send_notification_fn")

    def make_run_pipeline(mode="incremental"):
        """Create a run_analysis_pipeline_fn mock that writes a real HTML file."""
        html_file = html_report_factory(mode)

        def _run(*args, **kwargs):
            return (
                [{"keyword": "test", "count": 1}],  # stats
                html_file,                            # html_file path
                None,                                 # ai_result
            )
        return MagicMock(side_effect=_run, name="run_analysis_pipeline_fn")

    return {
        "load_analysis_data_fn": MagicMock(name="load_analysis_data_fn"),
        "prepare_current_title_info_fn": MagicMock(
            name="prepare_current_title_info_fn",
            return_value={
                "test_platform": {
                    "Test News Title": {"first_seen": "2026-04-14"},
                },
            },
        ),
        "run_analysis_pipeline_fn_factory": make_run_pipeline,
        "prepare_standalone_data_fn": MagicMock(
            name="prepare_standalone_data_fn",
            return_value=None,
        ),
        "send_notification_fn": mock_send,
    }
