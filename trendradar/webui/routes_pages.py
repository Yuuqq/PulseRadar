"""
Page (template-rendering) routes for TrendRadar Web UI.
"""

from __future__ import annotations

from flask import Blueprint, render_template

from trendradar.webui.helpers import load_config

pages_bp = Blueprint("pages", __name__)


@pages_bp.route("/")
def index():
    return render_template("index.html", config=load_config())


@pages_bp.route("/platforms")
def platforms_page():
    return render_template("platforms.html", config=load_config())


@pages_bp.route("/rss")
def rss_page():
    return render_template("rss.html", config=load_config())


@pages_bp.route("/extra-apis")
def extra_apis_page():
    return render_template("extra_apis.html", config=load_config())


@pages_bp.route("/notifications")
def notifications_page():
    return render_template("notifications.html", config=load_config())


@pages_bp.route("/ai")
def ai_page():
    return render_template("ai.html", config=load_config())


@pages_bp.route("/reports")
def reports_page():
    return render_template("reports.html")


@pages_bp.route("/workflow")
def workflow_page():
    return render_template("workflow.html", config=load_config())


@pages_bp.route("/jobs")
def jobs_page():
    return render_template("jobs.html")


@pages_bp.route("/trends")
def trends_page():
    return render_template("trends.html", config=load_config())


@pages_bp.route("/settings")
def settings_page():
    return render_template("settings.html", config=load_config())
