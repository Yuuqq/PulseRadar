"""
Web UI 鉴权路由

- ``GET  /login``   登录页（已登录时跳转回首页）
- ``POST /login``   提交凭据（接受 form 或 JSON）
- ``POST /logout``  退出登录
- ``GET  /setup``   首次运行的初始化页（仅在未初始化时可用）
- ``POST /setup``   创建管理员（仅在未初始化时可用）
- ``GET  /api/auth/status``  返回当前登录状态（前端可用于决定 UI 显示）
"""

from __future__ import annotations

from flask import (
    Blueprint,
    current_app,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)

from trendradar.logging import get_logger
from trendradar.webui.auth import (
    EXT_KEY,
    MIN_PASSWORD_LEN,
    AuthStore,
    current_user,
    is_authenticated,
    login_user,
    logout_user,
)

logger = get_logger(__name__)

auth_bp = Blueprint("auth", __name__)


def _store() -> AuthStore:
    return current_app.extensions[EXT_KEY]


def _safe_next_url(value: str | None) -> str:
    """仅允许跳回本站根开头的相对路径，防止 open redirect。"""
    if not value or not value.startswith("/") or value.startswith("//"):
        return url_for("pages.index")
    return value


@auth_bp.route("/login", methods=["GET"])
def login_page():
    if not _store().is_initialized():
        return redirect(url_for("auth.setup_page"))
    if is_authenticated():
        return redirect(_safe_next_url(request.args.get("next")))
    return render_template(
        "login.html",
        next_url=request.args.get("next", ""),
        error=None,
    )


@auth_bp.route("/login", methods=["POST"])
def login_submit():
    store = _store()
    if not store.is_initialized():
        if request.is_json or request.path.startswith("/api/"):
            return jsonify({"success": False, "error": "未初始化", "setup_required": True}), 400
        return redirect(url_for("auth.setup_page"))

    if request.is_json:
        payload = request.get_json(silent=True) or {}
        username = (payload.get("username") or "").strip()
        password = payload.get("password") or ""
        next_url = payload.get("next")
    else:
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        next_url = request.form.get("next")

    if not store.verify(username, password):
        logger.warning("登录失败", username=username, remote_addr=request.remote_addr)
        if request.is_json:
            return jsonify({"success": False, "error": "用户名或密码错误"}), 401
        return render_template(
            "login.html",
            next_url=next_url or "",
            error="用户名或密码错误",
        ), 401

    login_user(username)
    logger.info("登录成功", username=username, remote_addr=request.remote_addr)
    if request.is_json:
        return jsonify({"success": True, "username": username})
    return redirect(_safe_next_url(next_url))


@auth_bp.route("/logout", methods=["POST"])
def logout():
    user = current_user()
    logout_user()
    if user:
        logger.info("退出登录", username=user)
    if request.is_json or request.headers.get("X-Requested-With", "").lower() == "xmlhttprequest":
        return jsonify({"success": True})
    return redirect(url_for("auth.login_page"))


@auth_bp.route("/setup", methods=["GET"])
def setup_page():
    store = _store()
    if store.is_initialized():
        return redirect(url_for("auth.login_page"))
    return render_template("setup.html", min_password_len=MIN_PASSWORD_LEN, error=None)


@auth_bp.route("/setup", methods=["POST"])
def setup_submit():
    store = _store()
    if store.is_initialized():
        # 防止重复初始化覆盖
        if request.is_json:
            return jsonify({"success": False, "error": "已初始化"}), 409
        return redirect(url_for("auth.login_page"))

    if request.is_json:
        payload = request.get_json(silent=True) or {}
        username = payload.get("username") or ""
        password = payload.get("password") or ""
        confirm = payload.get("password_confirm") or ""
    else:
        username = request.form.get("username") or ""
        password = request.form.get("password") or ""
        confirm = request.form.get("password_confirm") or ""

    if password != confirm:
        if request.is_json:
            return jsonify({"success": False, "error": "两次输入的密码不一致"}), 400
        return render_template(
            "setup.html", min_password_len=MIN_PASSWORD_LEN, error="两次输入的密码不一致"
        ), 400

    try:
        store.set_credentials(username.strip(), password)
    except ValueError as exc:
        if request.is_json:
            return jsonify({"success": False, "error": str(exc)}), 400
        return render_template(
            "setup.html", min_password_len=MIN_PASSWORD_LEN, error=str(exc)
        ), 400

    login_user(username.strip())
    logger.info("已初始化管理员账户", username=username.strip())
    if request.is_json:
        return jsonify({"success": True, "username": username.strip()})
    return redirect(url_for("pages.index"))


@auth_bp.route("/api/auth/status", methods=["GET"])
def auth_status():
    store = _store()
    return jsonify(
        {
            "authenticated": is_authenticated(),
            "username": current_user(),
            "initialized": store.is_initialized(),
        }
    )
