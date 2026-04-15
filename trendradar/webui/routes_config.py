"""
Config API routes for TrendRadar Web UI.

Handles GET/POST for /api/config, /api/config/<section>,
/api/platforms, /api/rss, /api/extra-apis.
"""

from __future__ import annotations

from flask import Blueprint, jsonify

from trendradar.webui.helpers import load_config, read_json_body, save_config

config_bp = Blueprint("config", __name__)


@config_bp.route("/api/config", methods=["GET"])
def get_config():
    return jsonify(load_config())


@config_bp.route("/api/config", methods=["POST"])
def update_config():
    new_config = read_json_body()
    if new_config is None:
        return jsonify({"success": False, "error": "请求体必须是 JSON 对象"}), 400
    if save_config(new_config):
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "保存失败"}), 500


@config_bp.route("/api/config/<section>", methods=["GET"])
def get_config_section(section: str):
    config = load_config()
    if section in config:
        return jsonify(config[section])
    return jsonify({"error": "Section not found"}), 404


@config_bp.route("/api/config/<section>", methods=["POST"])
def update_config_section(section: str):
    section_value = read_json_body()
    if section_value is None:
        return jsonify({"success": False, "error": "请求体必须是 JSON 对象"}), 400

    config = load_config()
    if not isinstance(config, dict):
        config = {}
    config[section] = section_value
    if save_config(config):
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "保存失败"}), 500


@config_bp.route("/api/platforms", methods=["GET"])
def get_platforms():
    config = load_config()
    return jsonify(config.get("platforms", {}))


@config_bp.route("/api/platforms", methods=["POST"])
def update_platforms():
    platforms = read_json_body()
    if platforms is None:
        return jsonify({"success": False, "error": "请求体必须是 JSON 对象"}), 400

    config = load_config()
    config["platforms"] = platforms
    if save_config(config):
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "保存失败"}), 500


@config_bp.route("/api/rss", methods=["GET"])
def get_rss():
    config = load_config()
    return jsonify(config.get("rss", {}))


@config_bp.route("/api/rss", methods=["POST"])
def update_rss():
    rss = read_json_body()
    if rss is None:
        return jsonify({"success": False, "error": "请求体必须是 JSON 对象"}), 400

    config = load_config()
    config["rss"] = rss
    if save_config(config):
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "保存失败"}), 500


@config_bp.route("/api/extra-apis", methods=["GET"])
def get_extra_apis():
    config = load_config()
    return jsonify(config.get("extra_apis", {}))


@config_bp.route("/api/extra-apis", methods=["POST"])
def update_extra_apis():
    extra_apis = read_json_body()
    if extra_apis is None:
        return jsonify({"success": False, "error": "请求体必须是 JSON 对象"}), 400

    config = load_config()
    config["extra_apis"] = extra_apis
    if save_config(config):
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "保存失败"}), 500
