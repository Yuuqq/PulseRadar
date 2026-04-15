"""
Miscellaneous routes for TrendRadar Web UI.

Handles:
- /api/reports       — report listing
- /api/test-source   — source connectivity test
- /reports/<date>/<filename>       — serve HTML reports
- /artifacts/<path>                — serve output artifacts
"""

from __future__ import annotations

from pathlib import Path

from flask import Blueprint, current_app, jsonify, send_from_directory

from trendradar.webui.helpers import is_path_in_output, load_config, read_json_body

misc_bp = Blueprint("misc", __name__)


@misc_bp.route("/api/reports", methods=["GET"])
def get_reports():
    try:
        html_dir = Path(current_app.config["OUTPUT_DIR"]) / "html"
        reports = []

        if html_dir.exists():
            for date_dir in sorted(html_dir.iterdir(), reverse=True):
                if not date_dir.is_dir() or date_dir.name == "latest":
                    continue
                for html_file in sorted(date_dir.glob("*.html"), reverse=True):
                    reports.append(
                        {
                            "date": date_dir.name,
                            "time": html_file.stem,
                            "path": f"/reports/{date_dir.name}/{html_file.name}",
                            "filename": html_file.name,
                        }
                    )
        return jsonify(reports[:100])
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@misc_bp.route("/reports/<date>/<filename>")
def serve_report(date: str, filename: str):
    html_dir = Path(current_app.config["OUTPUT_DIR"]) / "html" / date
    return send_from_directory(str(html_dir), filename)


@misc_bp.route("/artifacts/<path:relative_path>")
def serve_artifact(relative_path: str):
    output_root = Path(current_app.config["OUTPUT_DIR"]).resolve()
    target = (output_root / relative_path).resolve()
    if not is_path_in_output(target) or not target.exists() or not target.is_file():
        return jsonify({"error": "Artifact not found"}), 404
    return send_from_directory(str(target.parent), target.name)


@misc_bp.route("/api/trends", methods=["GET"])
def get_trends():
    """Get trend analysis comparing the latest two crawl cycles."""
    try:
        from trendradar.core.trend import TrendAnalyzer
        from trendradar.storage import (
            convert_news_data_to_results,
            get_storage_manager,
        )

        config = load_config()
        storage_cfg = config.get("STORAGE", {})
        timezone = config.get("TIMEZONE", "Asia/Shanghai")

        sm = get_storage_manager(
            backend_type=storage_cfg.get("BACKEND", "auto"),
            data_dir=str(Path(current_app.config["OUTPUT_DIR"])),
            enable_txt=storage_cfg.get("FORMATS", {}).get("TXT", True),
            enable_html=storage_cfg.get("FORMATS", {}).get("HTML", True),
            timezone=timezone,
        )

        latest = sm.get_latest_crawl_data()
        if latest is None:
            return jsonify({"error": "No crawl data available"}), 404

        previous = sm.get_previous_crawl_data()
        if previous is None:
            return jsonify(
                {"error": "Only one crawl cycle available, need at least two for comparison"}
            ), 404

        current_results, current_names, _ = convert_news_data_to_results(latest)
        previous_results, prev_names, _ = convert_news_data_to_results(previous)
        merged_names = {**prev_names, **current_names}

        analyzer = TrendAnalyzer()
        report = analyzer.compare_periods(
            current_results=current_results,
            previous_results=previous_results,
            id_to_name=merged_names,
            current_period_label=latest.crawl_time,
            previous_period_label=previous.crawl_time,
        )

        def _item_to_dict(item):
            return {
                "title": item.title,
                "current_rank": item.current_rank,
                "previous_rank": item.previous_rank,
                "rank_change": item.rank_change,
                "platform_count": item.platform_count,
                "platforms": list(item.platforms),
                "is_new": item.is_new,
                "is_rising": item.is_rising,
                "heat_score": item.heat_score,
            }

        return jsonify(
            {
                "current_period": report.current_period,
                "previous_period": report.previous_period,
                "generated_at": report.generated_at.isoformat(),
                "total_current": report.total_current,
                "total_previous": report.total_previous,
                "new_trends": [_item_to_dict(t) for t in report.new_trends],
                "rising_trends": [_item_to_dict(t) for t in report.rising_trends],
                "falling_trends": [_item_to_dict(t) for t in report.falling_trends],
                "stable_trends": [_item_to_dict(t) for t in report.stable_trends],
                "disappeared": report.disappeared,
                "cross_platform": [_item_to_dict(t) for t in report.cross_platform],
            }
        )
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@misc_bp.route("/api/history/search", methods=["GET"])
def search_history():
    """Search historical trends by keyword.

    Query params:
        q: search keyword (required)
        days: lookback days (default: 7, max: 30)
        limit: max results (default: 200, max: 500)
    """
    from flask import request

    from trendradar.core.history import HistorySearcher
    from trendradar.storage.manager import get_storage_manager

    keyword = request.args.get("q", "").strip()
    if not keyword:
        return jsonify({"error": "参数 q 不能为空"}), 400

    try:
        days = min(int(request.args.get("days", 7)), 30)
    except (ValueError, TypeError):
        days = 7

    try:
        limit = min(int(request.args.get("limit", 200)), 500)
    except (ValueError, TypeError):
        limit = 200

    try:
        config = load_config()
        storage_cfg = config.get("STORAGE", {})
        timezone = config.get("TIMEZONE", "Asia/Shanghai")

        sm = get_storage_manager(
            backend_type=storage_cfg.get("BACKEND", "auto"),
            data_dir=str(Path(current_app.config["OUTPUT_DIR"])),
            enable_txt=storage_cfg.get("FORMATS", {}).get("TXT", True),
            enable_html=storage_cfg.get("FORMATS", {}).get("HTML", True),
            timezone=timezone,
        )

        searcher = HistorySearcher(sm)
        result = searcher.search(keyword, days=days, limit=limit)
        return jsonify(result.to_dict())
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@misc_bp.route("/api/test-source", methods=["POST"])
def test_source():
    """Test source availability with current settings."""
    try:
        data = read_json_body() or {}
        source_type = data.get("type")
        source_config = data.get("config", {})

        if source_type == "platform":
            from trendradar.crawler.fetcher import DataFetcher

            fetcher = DataFetcher()
            result, _, _ = fetcher.fetch_data(source_config.get("id"))
            fetcher.close()
            if result:
                return jsonify({"success": True, "message": "连接成功"})
            return jsonify({"success": False, "error": "获取失败"})

        # Use crawler plugin system for extra API sources
        from trendradar.crawler.registry import CrawlerRegistry

        CrawlerRegistry.discover()
        plugin_cls = CrawlerRegistry.get(source_type)
        if plugin_cls is not None:
            plugin = plugin_cls()
            try:
                result = plugin.fetch(source_config)
                if result.success:
                    count = len(result.items)
                    sample = [{"title": item.title, "url": item.url} for item in result.items[:3]]
                    return jsonify(
                        {"success": True, "message": f"获取成功: {count} 条", "sample": sample}
                    )
                errors = "; ".join(result.errors) if result.errors else "获取失败或无数据"
                return jsonify({"success": False, "error": errors})
            finally:
                plugin.close()

        if source_type == "rss":
            import feedparser

            feed = feedparser.parse(source_config.get("url", ""))
            if feed.entries:
                return jsonify(
                    {
                        "success": True,
                        "message": f"获取成功: {len(feed.entries)} 条",
                        "sample": [{"title": item.get("title", "")} for item in feed.entries[:3]],
                    }
                )
            return jsonify({"success": False, "error": "无法获取 RSS 内容"})

        return jsonify({"success": False, "error": "未知数据源类型"})
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500
