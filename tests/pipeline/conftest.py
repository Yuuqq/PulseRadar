from __future__ import annotations

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
def pipeline_ctx(pipeline_config, tmp_path):
    """Real AppContext with pipeline-specific config.

    Patches load_frequency_words (Pitfall 6 -- reads config/frequency_words.txt
    from disk which does not exist in test environment) and save_titles /
    get_output_path (which hardcode a relative 'output' path that would write
    outside tmp_path). All other AppContext methods are REAL and exercised
    against tmp_path storage.
    """
    from trendradar.context import AppContext

    ctx = AppContext(pipeline_config)
    # Patch load_frequency_words to avoid file I/O (Pitfall 6)
    ctx.load_frequency_words = lambda frequency_file=None: ([], [], [])

    # Patch get_output_path to use tmp_path instead of hardcoded relative 'output'
    _original_get_output_path = ctx.get_output_path

    def _patched_get_output_path(subfolder: str, filename: str) -> str:
        output_dir = tmp_path / "output" / subfolder / ctx.format_date()
        output_dir.mkdir(parents=True, exist_ok=True)
        return str(output_dir / filename)

    ctx.get_output_path = _patched_get_output_path
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
def mock_callbacks(monkeypatch, html_report_factory):
    """Patch the module-level collaborators execute_mode_strategy calls.

    execute_mode_strategy imports its collaborators by name, so they are
    resolved from the mode_strategy module globals at call time. Patching
    those globals is what isolates the test from real storage, HTML rendering
    and notification delivery.

    The returned dict gives tests handles on the individual mocks.
    """
    mock_send = MagicMock(name="send_notification_if_needed")

    def _run_pipeline(*args, **kwargs):
        """Write a real HTML file, tagged with the report mode under test."""
        mode = kwargs.get("mode", "incremental")
        return (
            [{"keyword": "test", "count": 1}],  # stats
            html_report_factory(mode),  # html_file path
            None,  # ai_result
        )

    callbacks = {
        "load_analysis_data_fn": MagicMock(name="_load_analysis_data"),
        "prepare_current_title_info_fn": MagicMock(
            name="_prepare_current_title_info",
            return_value={
                "test_platform": {
                    "Test News Title": {"first_seen": "2026-04-14"},
                },
            },
        ),
        "run_analysis_pipeline_fn": MagicMock(
            side_effect=_run_pipeline, name="run_analysis_pipeline"
        ),
        "prepare_standalone_data_fn": MagicMock(
            name="prepare_standalone_data",
            return_value=None,
        ),
        "send_notification_fn": mock_send,
    }

    monkeypatch.setattr(
        "trendradar.core.mode_strategy._load_analysis_data",
        callbacks["load_analysis_data_fn"],
    )
    monkeypatch.setattr(
        "trendradar.core.mode_strategy._prepare_current_title_info",
        callbacks["prepare_current_title_info_fn"],
    )
    monkeypatch.setattr(
        "trendradar.core.mode_strategy.run_analysis_pipeline",
        callbacks["run_analysis_pipeline_fn"],
    )
    monkeypatch.setattr(
        "trendradar.core.mode_strategy.prepare_standalone_data",
        callbacks["prepare_standalone_data_fn"],
    )
    monkeypatch.setattr(
        "trendradar.core.mode_strategy.send_notification_if_needed",
        callbacks["send_notification_fn"],
    )
    return callbacks
