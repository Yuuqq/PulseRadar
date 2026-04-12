# coding=utf-8
"""
TrendRadar Web UI 启动脚本

用法:
    python -m trendradar.webui
    或
    python run_webui.py
"""

import argparse
from trendradar.webui.app import run_server


def main():
    parser = argparse.ArgumentParser(description="TrendRadar Web UI")
    parser.add_argument("--host", default="127.0.0.1", help="绑定地址 (默认: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=5000, help="端口号 (默认: 5000)")
    parser.add_argument("--debug", action="store_true", help="调试模式")

    args = parser.parse_args()

    from trendradar.logging import configure_logging
    configure_logging(debug=args.debug)

    run_server(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
