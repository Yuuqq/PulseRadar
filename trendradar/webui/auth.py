"""
Web UI 鉴权模块

提供轻量、零额外依赖（仅依赖 Flask 自带的 werkzeug）的本地管理界面鉴权：

- 单管理员账户，凭据保存在独立的 ``config/webui_auth.json``（避免被
  ``/api/config`` 暴露）；密码使用 ``werkzeug.security.generate_password_hash``
  做带盐哈希
- 基于 Flask session（cookie 签名）的会话状态，会话密钥从同一文件持久化，
  确保进程重启后 session 不失效
- 通过 ``before_request`` 钩子拦截未登录请求：HTML 页面 302 到 ``/login``，
  ``/api/*`` 请求直接 401 + JSON
- CSRF 防护：对非安全方法 (POST/PUT/PATCH/DELETE) 强制要求
  ``X-Requested-With: XMLHttpRequest`` 头并校验 ``Origin`` / ``Referer``，
  阻断浏览器经由表单/链接发起的跨站请求
- 通过环境变量 ``TREND_RADAR_WEBUI_DISABLE_AUTH=1`` 可临时关闭鉴权
  （仅供本地开发与现有自动化脚本兼容使用，会在启动日志中打印 WARN）
"""

from __future__ import annotations

import json
import os
import secrets
from collections.abc import Iterable
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
from typing import Any

from flask import (
    Flask,
    abort,
    current_app,
    g,
    jsonify,
    redirect,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

from trendradar.logging import get_logger

logger = get_logger(__name__)

# Flask app 扩展键 & session 键
EXT_KEY = "trendradar_auth_store"
SESSION_USER_KEY = "_tr_user"
SESSION_LOGIN_AT_KEY = "_tr_login_at"

# 不需要鉴权的端点（路径前缀匹配）
PUBLIC_PREFIXES: tuple[str, ...] = (
    "/login",
    "/logout",
    "/setup",
    "/static/",
    "/healthz",
)

# 写操作 HTTP 方法
UNSAFE_METHODS: frozenset[str] = frozenset({"POST", "PUT", "PATCH", "DELETE"})

# 凭据文件名（位于 config 目录下）
AUTH_FILE_NAME = "webui_auth.json"

# 用户名/密码长度限制
MIN_PASSWORD_LEN = 8
MAX_PASSWORD_LEN = 256
MAX_USERNAME_LEN = 64


class AuthStore:
    """凭据 + secret_key 持久化存储。

    文件格式 (``config/webui_auth.json``)::

        {
          "username": "admin",
          "password_hash": "scrypt:...",
          "secret_key": "<urlsafe random>",
          "created_at": "2026-05-03T10:00:00+00:00",
          "updated_at": "2026-05-03T10:00:00+00:00"
        }
    """

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._data: dict[str, Any] | None = None
        self._load()

    # ---------------------------- I/O ---------------------------- #

    def _load(self) -> None:
        if not self.path.exists():
            self._data = None
            return
        try:
            self._data = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.error(
                "无法读取鉴权凭据文件，将视为未初始化",
                path=str(self.path),
                error=str(exc),
            )
            self._data = None

    def _save(self) -> None:
        if self._data is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, self.path)
        # 收紧文件权限（POSIX 平台）
        try:
            os.chmod(self.path, 0o600)
        except (OSError, NotImplementedError):
            pass

    # ---------------------------- 状态查询 ---------------------------- #

    def is_initialized(self) -> bool:
        return bool(self._data and self._data.get("password_hash"))

    @property
    def username(self) -> str | None:
        if not self._data:
            return None
        return self._data.get("username")

    def secret_key(self) -> str:
        """返回 Flask session 用的 SECRET_KEY；不存在则生成并持久化。"""
        if not self._data:
            self._data = {}
        if not self._data.get("secret_key"):
            self._data["secret_key"] = secrets.token_urlsafe(48)
            self._save()
        return self._data["secret_key"]

    # ---------------------------- 凭据管理 ---------------------------- #

    def set_credentials(self, username: str, password: str) -> None:
        username = (username or "").strip()
        if not username or len(username) > MAX_USERNAME_LEN:
            raise ValueError(f"用户名长度必须在 1-{MAX_USERNAME_LEN} 之间")
        if not password or len(password) < MIN_PASSWORD_LEN or len(password) > MAX_PASSWORD_LEN:
            raise ValueError(f"密码长度必须在 {MIN_PASSWORD_LEN}-{MAX_PASSWORD_LEN} 之间")

        now = datetime.now(timezone.utc).isoformat()
        if not self._data:
            self._data = {}
        if "secret_key" not in self._data:
            self._data["secret_key"] = secrets.token_urlsafe(48)
        if "created_at" not in self._data:
            self._data["created_at"] = now
        self._data["username"] = username
        self._data["password_hash"] = generate_password_hash(password)
        self._data["updated_at"] = now
        self._save()

    def verify(self, username: str, password: str) -> bool:
        if not self.is_initialized():
            return False
        if (username or "") != self._data.get("username", ""):
            return False
        return check_password_hash(self._data["password_hash"], password or "")


# ============================================================================
# Session 操作
# ============================================================================


def login_user(username: str) -> None:
    session.clear()
    session[SESSION_USER_KEY] = username
    session[SESSION_LOGIN_AT_KEY] = datetime.now(timezone.utc).isoformat()
    session.permanent = True


def logout_user() -> None:
    session.clear()


def current_user() -> str | None:
    return session.get(SESSION_USER_KEY)


def is_authenticated() -> bool:
    return current_user() is not None


# ============================================================================
# CSRF / Origin 校验
# ============================================================================


def _is_same_origin(req) -> bool:
    """校验 Origin / Referer 是否与 Host 一致。

    都缺失时（如非浏览器 client）保守地视作通过——X-Requested-With 头会兜底。
    """
    host = req.headers.get("Host", "")
    if not host:
        return False

    origin = req.headers.get("Origin")
    if origin:
        # Origin 是 "scheme://host[:port]"
        if origin.endswith("//" + host) or origin.split("//", 1)[-1] == host:
            return True
        return False

    referer = req.headers.get("Referer")
    if referer:
        try:
            from urllib.parse import urlparse

            parsed = urlparse(referer)
            return parsed.netloc == host
        except Exception:
            return False

    # 都没有：通常是非浏览器请求，X-Requested-With 校验已经能阻断 CSRF
    return True


def _check_csrf(req) -> tuple[bool, str]:
    """对非安全方法做 CSRF 校验。返回 (ok, reason)。"""
    if req.method not in UNSAFE_METHODS:
        return True, ""
    # XHR/fetch 强制要求 X-Requested-With 头
    if req.headers.get("X-Requested-With", "").lower() != "xmlhttprequest":
        return False, "missing X-Requested-With"
    if not _is_same_origin(req):
        return False, "cross-origin request blocked"
    return True, ""


# ============================================================================
# 装饰器
# ============================================================================


def login_required(func):
    """API 端点登录保护装饰器。未登录返回 401 JSON。"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        if _auth_disabled():
            return func(*args, **kwargs)
        if not is_authenticated():
            return jsonify({"success": False, "error": "未登录"}), 401
        return func(*args, **kwargs)

    return wrapper


# ============================================================================
# Flask app 集成
# ============================================================================


def _auth_disabled() -> bool:
    return os.environ.get("TREND_RADAR_WEBUI_DISABLE_AUTH", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _is_public_path(path: str) -> bool:
    return any(path == p or path.startswith(p) for p in PUBLIC_PREFIXES)


def _wants_json(req) -> bool:
    if req.path.startswith("/api/"):
        return True
    accept = req.headers.get("Accept", "")
    return "application/json" in accept and "text/html" not in accept


def install_auth(app: Flask, auth_store: AuthStore) -> None:
    """把鉴权钩子安装到 Flask app 上。

    - 设置 ``SECRET_KEY`` (从 ``AuthStore`` 读取，确保跨重启稳定)
    - 注册 ``before_request`` 钩子做：未初始化重定向 /setup、未登录重定向 /login、CSRF 校验
    """
    app.extensions[EXT_KEY] = auth_store

    # 优先环境变量，其次持久化的 secret_key
    env_secret = os.environ.get("TREND_RADAR_WEBUI_SECRET", "").strip()
    app.secret_key = env_secret or auth_store.secret_key()

    # session cookie 安全选项
    app.config.setdefault("SESSION_COOKIE_HTTPONLY", True)
    app.config.setdefault("SESSION_COOKIE_SAMESITE", "Lax")
    # 默认 7 天有效期
    from datetime import timedelta

    app.config.setdefault("PERMANENT_SESSION_LIFETIME", timedelta(days=7))

    if _auth_disabled():
        logger.warning(
            "Web UI 鉴权已被环境变量禁用",
            env_var="TREND_RADAR_WEBUI_DISABLE_AUTH",
        )

    @app.before_request
    def _auth_gate():  # noqa: ANN202
        # 暴露给模板：当前用户 / 是否需要鉴权
        g.current_user = current_user()
        g.auth_disabled = _auth_disabled()

        if _auth_disabled():
            return None

        path = request.path

        # CSRF 校验（即便未登录也校验，阻断登录端点的跨站重放）
        if request.method in UNSAFE_METHODS and not _is_public_path(path):
            ok, reason = _check_csrf(request)
            if not ok:
                logger.warning(
                    "CSRF 校验失败", path=path, method=request.method, reason=reason
                )
                if _wants_json(request):
                    return jsonify({"success": False, "error": "CSRF check failed"}), 403
                abort(403)

        # 公开路径放行
        if _is_public_path(path):
            return None

        # 未初始化：所有非公开路径强制走 /setup
        store: AuthStore = current_app.extensions[EXT_KEY]
        if not store.is_initialized():
            if _wants_json(request):
                return jsonify({"success": False, "error": "未初始化", "setup_required": True}), 401
            return redirect(url_for("auth.setup_page"))

        # 未登录
        if not is_authenticated():
            if _wants_json(request):
                return jsonify({"success": False, "error": "未登录"}), 401
            next_path = path if request.method == "GET" else None
            return redirect(url_for("auth.login_page", next=next_path))

        return None

    @app.context_processor
    def _inject_auth_ctx():  # noqa: ANN202
        return {
            "current_user": current_user(),
            "auth_disabled": _auth_disabled(),
        }


__all__: Iterable[str] = (
    "AUTH_FILE_NAME",
    "AuthStore",
    "EXT_KEY",
    "MIN_PASSWORD_LEN",
    "current_user",
    "install_auth",
    "is_authenticated",
    "login_required",
    "login_user",
    "logout_user",
)
