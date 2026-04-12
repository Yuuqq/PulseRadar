# coding=utf-8
"""
TrendRadar Web UI - Flask application factory.

Provides local web management capabilities:
- configuration management
- job execution and status tracking
- data source connectivity testing
- historical report browsing
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

from flask import Flask

from trendradar.webui.job_manager import JobManager
from trendradar.webui.routes_config import config_bp
from trendradar.webui.routes_jobs import jobs_bp
from trendradar.webui.routes_misc import misc_bp
from trendradar.webui.routes_pages import pages_bp
from trendradar.webui.routes_workflow import workflow_bp
from trendradar.logging import get_logger

logger = get_logger(__name__)


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

    app.register_blueprint(pages_bp)
    app.register_blueprint(config_bp)
    app.register_blueprint(jobs_bp)
    app.register_blueprint(workflow_bp)
    app.register_blueprint(misc_bp)

    return app


def run_server(host: str = "127.0.0.1", port: int = 5000, debug: bool = False) -> None:
    """Run Web server."""

    app = create_app()
    logger.info("TrendRadar Web UI 已启动", host=host, port=port)
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    debug_env = os.environ.get("TREND_RADAR_WEBUI_DEBUG", "").strip().lower()
    debug = debug_env in {"1", "true", "yes", "on"}
    run_server(debug=debug)
