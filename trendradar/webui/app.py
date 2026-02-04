# coding=utf-8
"""
TrendRadar Web UI - Flask 应用

提供本地 Web 管理界面：
- 配置管理（数据源、通知渠道等）
- 运行状态监控
- 手动执行抓取
- 查看历史报告
"""

import os
import sys
import json
import yaml
import subprocess
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

from flask import Flask, render_template, request, jsonify, send_from_directory


def create_app(config_path: Optional[str] = None) -> Flask:
    """创建 Flask 应用"""

    # 获取项目根目录
    root_dir = Path(__file__).parent.parent.parent
    config_dir = root_dir / "config"
    output_dir = root_dir / "output"

    if config_path:
        config_file = Path(config_path)
    else:
        config_file = config_dir / "config.yaml"

    app = Flask(
        __name__,
        template_folder=str(Path(__file__).parent / "templates"),
        static_folder=str(Path(__file__).parent / "static"),
    )

    app.config["CONFIG_FILE"] = str(config_file)
    app.config["CONFIG_DIR"] = str(config_dir)
    app.config["OUTPUT_DIR"] = str(output_dir)
    app.config["ROOT_DIR"] = str(root_dir)

    # 运行状态
    app.config["RUNNING"] = False
    app.config["LAST_RUN"] = None
    app.config["RUN_LOG"] = []

    def load_config() -> Dict:
        """加载配置文件"""
        try:
            with open(app.config["CONFIG_FILE"], "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except Exception as e:
            return {"error": str(e)}

    def save_config(config: Dict) -> bool:
        """保存配置文件"""
        try:
            with open(app.config["CONFIG_FILE"], "w", encoding="utf-8") as f:
                yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
            return True
        except Exception:
            return False

    # =========================================================================
    # 页面路由
    # =========================================================================

    @app.route("/")
    def index():
        """主页 - 仪表盘"""
        config = load_config()
        return render_template("index.html", config=config)

    @app.route("/platforms")
    def platforms_page():
        """热榜平台管理页"""
        config = load_config()
        return render_template("platforms.html", config=config)

    @app.route("/rss")
    def rss_page():
        """RSS 源管理页"""
        config = load_config()
        return render_template("rss.html", config=config)

    @app.route("/extra-apis")
    def extra_apis_page():
        """额外 API 数据源管理页"""
        config = load_config()
        return render_template("extra_apis.html", config=config)

    @app.route("/notifications")
    def notifications_page():
        """通知渠道管理页"""
        config = load_config()
        return render_template("notifications.html", config=config)

    @app.route("/ai")
    def ai_page():
        """AI 配置页"""
        config = load_config()
        return render_template("ai.html", config=config)

    @app.route("/reports")
    def reports_page():
        """历史报告页"""
        return render_template("reports.html")

    @app.route("/settings")
    def settings_page():
        """高级设置页"""
        config = load_config()
        return render_template("settings.html", config=config)

    # =========================================================================
    # API 路由
    # =========================================================================

    @app.route("/api/config", methods=["GET"])
    def get_config():
        """获取完整配置"""
        return jsonify(load_config())

    @app.route("/api/config", methods=["POST"])
    def update_config():
        """更新配置"""
        try:
            new_config = request.json
            if save_config(new_config):
                return jsonify({"success": True})
            else:
                return jsonify({"success": False, "error": "保存失败"}), 500
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/config/<section>", methods=["GET"])
    def get_config_section(section: str):
        """获取配置的某个部分"""
        config = load_config()
        if section in config:
            return jsonify(config[section])
        return jsonify({"error": "Section not found"}), 404

    @app.route("/api/config/<section>", methods=["POST"])
    def update_config_section(section: str):
        """更新配置的某个部分"""
        try:
            config = load_config()
            config[section] = request.json
            if save_config(config):
                return jsonify({"success": True})
            else:
                return jsonify({"success": False, "error": "保存失败"}), 500
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/platforms", methods=["GET"])
    def get_platforms():
        """获取热榜平台配置"""
        config = load_config()
        return jsonify(config.get("platforms", {}))

    @app.route("/api/platforms", methods=["POST"])
    def update_platforms():
        """更新热榜平台配置"""
        try:
            config = load_config()
            config["platforms"] = request.json
            if save_config(config):
                return jsonify({"success": True})
            return jsonify({"success": False, "error": "保存失败"}), 500
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/rss", methods=["GET"])
    def get_rss():
        """获取 RSS 配置"""
        config = load_config()
        return jsonify(config.get("rss", {}))

    @app.route("/api/rss", methods=["POST"])
    def update_rss():
        """更新 RSS 配置"""
        try:
            config = load_config()
            config["rss"] = request.json
            if save_config(config):
                return jsonify({"success": True})
            return jsonify({"success": False, "error": "保存失败"}), 500
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/extra-apis", methods=["GET"])
    def get_extra_apis():
        """获取额外 API 配置"""
        config = load_config()
        return jsonify(config.get("extra_apis", {}))

    @app.route("/api/extra-apis", methods=["POST"])
    def update_extra_apis():
        """更新额外 API 配置"""
        try:
            config = load_config()
            config["extra_apis"] = request.json
            if save_config(config):
                return jsonify({"success": True})
            return jsonify({"success": False, "error": "保存失败"}), 500
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/reports", methods=["GET"])
    def get_reports():
        """获取历史报告列表"""
        try:
            html_dir = Path(app.config["OUTPUT_DIR"]) / "html"
            reports = []

            if html_dir.exists():
                for date_dir in sorted(html_dir.iterdir(), reverse=True):
                    if date_dir.is_dir() and date_dir.name != "latest":
                        for html_file in sorted(date_dir.glob("*.html"), reverse=True):
                            reports.append({
                                "date": date_dir.name,
                                "time": html_file.stem,
                                "path": f"/reports/{date_dir.name}/{html_file.name}",
                                "filename": html_file.name,
                            })

            return jsonify(reports[:100])  # 最多返回 100 个
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/reports/<date>/<filename>")
    def serve_report(date: str, filename: str):
        """提供报告文件"""
        html_dir = Path(app.config["OUTPUT_DIR"]) / "html" / date
        return send_from_directory(str(html_dir), filename)

    @app.route("/api/status", methods=["GET"])
    def get_status():
        """获取运行状态"""
        return jsonify({
            "running": app.config["RUNNING"],
            "last_run": app.config["LAST_RUN"],
            "log": app.config["RUN_LOG"][-50:],  # 最近 50 条日志
        })

    @app.route("/api/run", methods=["POST"])
    def run_crawler():
        """运行爬虫"""
        if app.config["RUNNING"]:
            return jsonify({"success": False, "error": "已有任务在运行中"}), 400

        def run_task():
            app.config["RUNNING"] = True
            app.config["RUN_LOG"] = []

            try:
                # 运行 trendradar 模块
                process = subprocess.Popen(
                    [sys.executable, "-m", "trendradar"],
                    cwd=app.config["ROOT_DIR"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    env={**os.environ, "PYTHONUTF8": "1"},
                )

                for line in process.stdout:
                    app.config["RUN_LOG"].append(line.strip())

                process.wait()
                app.config["LAST_RUN"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            except Exception as e:
                app.config["RUN_LOG"].append(f"错误: {str(e)}")
            finally:
                app.config["RUNNING"] = False

        thread = threading.Thread(target=run_task)
        thread.daemon = True
        thread.start()

        return jsonify({"success": True, "message": "任务已启动"})

    @app.route("/api/test-source", methods=["POST"])
    def test_source():
        """测试数据源"""
        try:
            data = request.json
            source_type = data.get("type")
            source_config = data.get("config", {})

            # 导入并测试
            if source_type == "platform":
                from trendradar.crawler.fetcher import DataFetcher
                fetcher = DataFetcher()
                result, _, _ = fetcher.fetch_data(source_config.get("id"))
                fetcher.close()
                if result:
                    return jsonify({"success": True, "message": "连接成功"})
                return jsonify({"success": False, "error": "获取失败"})

            elif source_type in ["vvhan", "dailyhot", "newsapi", "gnews", "mediastack", "thenewsapi"]:
                from trendradar.crawler.extra_apis import ExtraAPIFetcher
                fetcher = ExtraAPIFetcher()

                if source_type == "vvhan":
                    items = fetcher.fetch_vvhan_hotlist(source_config.get("platform", "weibo"))
                elif source_type == "dailyhot":
                    items = fetcher.fetch_dailyhot(source_config.get("platform"))
                elif source_type == "newsapi":
                    items = fetcher.fetch_newsapi(
                        api_key=source_config.get("api_key", ""),
                        country=source_config.get("country", "us"),
                    )
                elif source_type == "gnews":
                    items = fetcher.fetch_gnews(
                        api_key=source_config.get("api_key", ""),
                        country=source_config.get("country", "us"),
                    )
                elif source_type == "mediastack":
                    items = fetcher.fetch_mediastack(
                        api_key=source_config.get("api_key", ""),
                        countries=source_config.get("countries", "us"),
                    )
                elif source_type == "thenewsapi":
                    items = fetcher.fetch_thenewsapi(
                        api_key=source_config.get("api_key", ""),
                    )

                fetcher.close()

                if items:
                    return jsonify({
                        "success": True,
                        "message": f"获取成功: {len(items) if isinstance(items, list) else sum(len(v) for v in items.values())} 条",
                        "sample": items[:3] if isinstance(items, list) else None,
                    })
                return jsonify({"success": False, "error": "获取失败或无数据"})

            elif source_type == "rss":
                import feedparser
                feed = feedparser.parse(source_config.get("url", ""))
                if feed.entries:
                    return jsonify({
                        "success": True,
                        "message": f"获取成功: {len(feed.entries)} 条",
                        "sample": [{"title": e.get("title", "")} for e in feed.entries[:3]],
                    })
                return jsonify({"success": False, "error": "无法获取 RSS 内容"})

            return jsonify({"success": False, "error": "未知数据源类型"})

        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    return app


def run_server(host: str = "127.0.0.1", port: int = 5000, debug: bool = False):
    """运行 Web 服务器"""
    app = create_app()
    print(f"\n{'='*60}")
    print(f"TrendRadar Web UI 已启动")
    print(f"访问地址: http://{host}:{port}")
    print(f"{'='*60}\n")
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    run_server(debug=True)
