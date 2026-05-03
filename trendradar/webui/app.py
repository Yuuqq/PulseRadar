"""
TrendRadar Web UI - Flask application factory.

Provides local web management capabilities:
- configuration management
- job execution and status tracking
- data source connectivity testing
- historical report browsing
- 管理员鉴权（详见 ``trendradar.webui.auth``）
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from flask import Flask

from trendradar.logging import get_logger
from trendradar.webui.auth import AUTH_FILE_NAME, AuthStore, install_auth
from trendradar.webui.job_manager import JobManager
from trendradar.webui.routes_auth import auth_bp
from trendradar.webui.routes_config import config_bp
from trendradar.webui.routes_jobs import jobs_bp
from trendradar.webui.routes_misc import misc_bp
from trendradar.webui.routes_pages import pages_bp
from trendradar.webui.routes_workflow import workflow_bp

logger = get_logger(__name__)


def create_app(
    config_path: str | None = None,
    output_path: str | None = None,
    auth_path: str | None = None,
) -> Flask:
    """Create Flask app instance.

    Args:
        config_path: 主配置文件路径
        output_path: 输出目录
        auth_path: 鉴权凭据文件路径，默认 ``<config_dir>/webui_auth.json``
    """

    root_dir = Path(__file__).resolve().parents[2]
    config_dir = root_dir / "config"
    output_dir = Path(output_path) if output_path else (root_dir / "output")
    config_file = Path(config_path) if config_path else config_dir / "config.yaml"
    # 鉴权凭据文件就近放在主配置同目录
    auth_file = Path(auth_path) if auth_path else config_file.parent / AUTH_FILE_NAME

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
    app.config["AUTH_FILE"] = str(auth_file)

    # 鉴权（必须在注册其他蓝图前安装，确保 before_request 钩子生效）
    auth_store = AuthStore(auth_file)
    install_auth(app, auth_store)

    job_manager = JobManager(root_dir=root_dir, output_dir=output_dir, config_file=config_file)
    app.extensions["trendradar_job_manager"] = job_manager

    app.register_blueprint(auth_bp)
    app.register_blueprint(pages_bp)
    app.register_blueprint(config_bp)
    app.register_blueprint(jobs_bp)
    app.register_blueprint(workflow_bp)
    app.register_blueprint(misc_bp)

    if not auth_store.is_initialized() and not os.environ.get("TREND_RADAR_WEBUI_DISABLE_AUTH"):
        logger.info(
            "Web UI 尚未初始化管理员账户，首次访问将引导至 /setup",
            auth_file=str(auth_file),
        )

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
