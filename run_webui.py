#!/usr/bin/env python
# coding=utf-8
"""
TrendRadar Web UI 启动脚本

运行: python run_webui.py
访问: http://127.0.0.1:5000
"""

import os

from trendradar.webui.app import run_server

if __name__ == "__main__":
    debug_env = os.environ.get("TREND_RADAR_WEBUI_DEBUG", "").strip().lower()
    debug = debug_env in {"1", "true", "yes", "on"}
    run_server(debug=debug)
