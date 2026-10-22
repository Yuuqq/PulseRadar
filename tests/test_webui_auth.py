"""Tests for trendradar.webui.auth and routes_auth."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from trendradar.webui.app import create_app
from trendradar.webui.auth import (
    AUTH_FILE_NAME,
    AuthStore,
    MIN_PASSWORD_LEN,
)
from trendradar.webui.job_manager import JobManager


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MIN_CONFIG = """
platforms:
  enabled: true
  sources: []
rss:
  enabled: false
  feeds: []
extra_apis:
  enabled: false
  sources: []
""".strip() + "\n"


def _make_app(tmp_path: Path, monkeypatch, *, init_admin: bool = True):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(MIN_CONFIG, encoding="utf-8")
    output_dir = tmp_path / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    auth_file = tmp_path / AUTH_FILE_NAME

    if init_admin:
        store = AuthStore(auth_file)
        store.set_credentials("admin", "correct-horse-battery-staple")

    monkeypatch.setattr(JobManager, "_start_dispatcher", lambda self: None)
    monkeypatch.delenv("TREND_RADAR_WEBUI_DISABLE_AUTH", raising=False)

    app = create_app(
        config_path=str(config_file),
        output_path=str(output_dir),
        auth_path=str(auth_file),
    )
    app.config["TESTING"] = True
    # 让 url_for 能生成 absolute url
    app.config["SERVER_NAME"] = "localhost.localdomain"
    return app


@pytest.fixture()
def authed_app(tmp_path, monkeypatch):
    return _make_app(tmp_path, monkeypatch, init_admin=True)


@pytest.fixture()
def fresh_app(tmp_path, monkeypatch):
    """未初始化管理员账户的 app。"""
    return _make_app(tmp_path, monkeypatch, init_admin=False)


# ---------------------------------------------------------------------------
# AuthStore 单元测试
# ---------------------------------------------------------------------------


class TestAuthStore:
    def test_initial_state(self, tmp_path):
        store = AuthStore(tmp_path / "auth.json")
        assert not store.is_initialized()
        assert store.username is None

    def test_set_and_verify_credentials(self, tmp_path):
        store = AuthStore(tmp_path / "auth.json")
        store.set_credentials("admin", "longenoughpwd")
        assert store.is_initialized()
        assert store.username == "admin"
        assert store.verify("admin", "longenoughpwd")
        assert not store.verify("admin", "wrong")
        assert not store.verify("other", "longenoughpwd")

    def test_password_min_length_enforced(self, tmp_path):
        store = AuthStore(tmp_path / "auth.json")
        with pytest.raises(ValueError):
            store.set_credentials("admin", "a" * (MIN_PASSWORD_LEN - 1))

    def test_username_required(self, tmp_path):
        store = AuthStore(tmp_path / "auth.json")
        with pytest.raises(ValueError):
            store.set_credentials("   ", "longenoughpwd")

    def test_persist_across_instances(self, tmp_path):
        path = tmp_path / "auth.json"
        AuthStore(path).set_credentials("admin", "longenoughpwd")
        store2 = AuthStore(path)
        assert store2.is_initialized()
        assert store2.verify("admin", "longenoughpwd")

    def test_secret_key_persisted(self, tmp_path):
        path = tmp_path / "auth.json"
        store = AuthStore(path)
        key1 = store.secret_key()
        assert key1
        # 重新加载后 secret 不应改变
        key2 = AuthStore(path).secret_key()
        assert key1 == key2

    def test_corrupt_file_treated_as_uninitialized(self, tmp_path):
        path = tmp_path / "auth.json"
        path.write_text("not json", encoding="utf-8")
        store = AuthStore(path)
        assert not store.is_initialized()


# ---------------------------------------------------------------------------
# 路由 / 中间件集成测试
# ---------------------------------------------------------------------------


class TestAuthGate:
    def test_unauthed_html_redirects_to_login(self, authed_app):
        client = authed_app.test_client()
        resp = client.get("/")
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]

    def test_unauthed_api_returns_401_json(self, authed_app):
        client = authed_app.test_client()
        resp = client.get("/api/config")
        assert resp.status_code == 401
        body = resp.get_json()
        assert body["success"] is False
        assert "未登录" in body["error"]

    def test_uninitialized_redirects_to_setup(self, fresh_app):
        client = fresh_app.test_client()
        resp = client.get("/")
        assert resp.status_code == 302
        assert "/setup" in resp.headers["Location"]

    def test_uninitialized_api_returns_setup_required(self, fresh_app):
        client = fresh_app.test_client()
        resp = client.get("/api/config")
        assert resp.status_code == 401
        body = resp.get_json()
        assert body.get("setup_required") is True

    def test_static_assets_public(self, authed_app):
        client = authed_app.test_client()
        # static endpoint 不应被拦截
        resp = client.get("/static/js/main.js")
        # 文件存在 -> 200；任何情况下不应是 302/401
        assert resp.status_code not in (302, 401)

    def test_login_page_public(self, authed_app):
        client = authed_app.test_client()
        resp = client.get("/login")
        assert resp.status_code == 200
        assert b"\xe7\x99\xbb\xe5\xbd\x95" in resp.data  # "登录"


class TestLoginFlow:
    def test_login_with_valid_credentials_form(self, authed_app):
        client = authed_app.test_client()
        resp = client.post(
            "/login",
            data={"username": "admin", "password": "correct-horse-battery-staple"},
            headers={
                "X-Requested-With": "XMLHttpRequest",
                "Origin": "http://localhost.localdomain",
            },
        )
        assert resp.status_code == 302
        assert resp.headers["Location"].endswith("/")

    def test_login_with_valid_credentials_json(self, authed_app):
        client = authed_app.test_client()
        resp = client.post(
            "/login",
            data=json.dumps(
                {"username": "admin", "password": "correct-horse-battery-staple"}
            ),
            content_type="application/json",
            headers={
                "X-Requested-With": "XMLHttpRequest",
                "Origin": "http://localhost.localdomain",
            },
        )
        assert resp.status_code == 200
        assert resp.get_json()["success"] is True

    def test_login_with_invalid_credentials(self, authed_app):
        client = authed_app.test_client()
        resp = client.post(
            "/login",
            data=json.dumps({"username": "admin", "password": "wrong"}),
            content_type="application/json",
            headers={
                "X-Requested-With": "XMLHttpRequest",
                "Origin": "http://localhost.localdomain",
            },
        )
        assert resp.status_code == 401
        assert resp.get_json()["success"] is False

    def test_authed_request_succeeds_after_login(self, authed_app):
        client = authed_app.test_client()
        client.post(
            "/login",
            data=json.dumps(
                {"username": "admin", "password": "correct-horse-battery-staple"}
            ),
            content_type="application/json",
            headers={
                "X-Requested-With": "XMLHttpRequest",
                "Origin": "http://localhost.localdomain",
            },
        )
        resp = client.get("/api/config")
        assert resp.status_code == 200

    def test_logout_clears_session(self, authed_app):
        client = authed_app.test_client()
        client.post(
            "/login",
            data=json.dumps(
                {"username": "admin", "password": "correct-horse-battery-staple"}
            ),
            content_type="application/json",
            headers={
                "X-Requested-With": "XMLHttpRequest",
                "Origin": "http://localhost.localdomain",
            },
        )
        resp = client.post(
            "/logout",
            headers={
                "X-Requested-With": "XMLHttpRequest",
                "Origin": "http://localhost.localdomain",
            },
        )
        assert resp.status_code in (200, 302)
        # 退出后 API 应再次返回 401
        resp2 = client.get("/api/config")
        assert resp2.status_code == 401

    def test_login_open_redirect_blocked(self, authed_app):
        client = authed_app.test_client()
        resp = client.post(
            "/login",
            data={
                "username": "admin",
                "password": "correct-horse-battery-staple",
                "next": "//evil.example.com/x",
            },
            headers={
                "X-Requested-With": "XMLHttpRequest",
                "Origin": "http://localhost.localdomain",
            },
        )
        assert resp.status_code == 302
        # 应跳回站内根，而不是 //evil...
        assert "evil.example.com" not in resp.headers["Location"]


class TestSetupFlow:
    def test_setup_creates_admin_and_logs_in(self, fresh_app):
        client = fresh_app.test_client()
        resp = client.post(
            "/setup",
            data=json.dumps(
                {
                    "username": "owner",
                    "password": "longenoughpwd",
                    "password_confirm": "longenoughpwd",
                }
            ),
            content_type="application/json",
            headers={
                "X-Requested-With": "XMLHttpRequest",
                "Origin": "http://localhost.localdomain",
            },
        )
        assert resp.status_code == 200
        assert resp.get_json()["success"] is True
        # setup 完成后应该已经登录
        resp2 = client.get("/api/config")
        assert resp2.status_code == 200

    def test_setup_rejects_short_password(self, fresh_app):
        client = fresh_app.test_client()
        resp = client.post(
            "/setup",
            data=json.dumps(
                {"username": "owner", "password": "short", "password_confirm": "short"}
            ),
            content_type="application/json",
            headers={
                "X-Requested-With": "XMLHttpRequest",
                "Origin": "http://localhost.localdomain",
            },
        )
        assert resp.status_code == 400

    def test_setup_rejects_password_mismatch(self, fresh_app):
        client = fresh_app.test_client()
        resp = client.post(
            "/setup",
            data=json.dumps(
                {
                    "username": "owner",
                    "password": "longenoughpwd",
                    "password_confirm": "different",
                }
            ),
            content_type="application/json",
            headers={
                "X-Requested-With": "XMLHttpRequest",
                "Origin": "http://localhost.localdomain",
            },
        )
        assert resp.status_code == 400

    def test_setup_blocked_after_initialized(self, authed_app):
        client = authed_app.test_client()
        resp = client.post(
            "/setup",
            data=json.dumps(
                {
                    "username": "newadmin",
                    "password": "longenoughpwd",
                    "password_confirm": "longenoughpwd",
                }
            ),
            content_type="application/json",
            headers={
                "X-Requested-With": "XMLHttpRequest",
                "Origin": "http://localhost.localdomain",
            },
        )
        assert resp.status_code == 409


class TestCsrfProtection:
    def _login(self, client):
        client.post(
            "/login",
            data=json.dumps(
                {"username": "admin", "password": "correct-horse-battery-staple"}
            ),
            content_type="application/json",
            headers={
                "X-Requested-With": "XMLHttpRequest",
                "Origin": "http://localhost.localdomain",
            },
        )

    def test_post_without_xrw_header_blocked(self, authed_app):
        client = authed_app.test_client()
        self._login(client)
        resp = client.post(
            "/api/config",
            data=json.dumps({}),
            content_type="application/json",
        )
        assert resp.status_code == 403

    def test_post_with_cross_origin_blocked(self, authed_app):
        client = authed_app.test_client()
        self._login(client)
        resp = client.post(
            "/api/config",
            data=json.dumps({}),
            content_type="application/json",
            headers={
                "X-Requested-With": "XMLHttpRequest",
                "Origin": "http://evil.example.com",
            },
        )
        assert resp.status_code == 403

    def test_post_with_valid_csrf_passes(self, authed_app):
        client = authed_app.test_client()
        self._login(client)
        resp = client.post(
            "/api/config",
            data=json.dumps({"timezone": "UTC"}),
            content_type="application/json",
            headers={
                "X-Requested-With": "XMLHttpRequest",
                "Origin": "http://localhost.localdomain",
            },
        )
        # 任何不是 403/401 的响应都说明 CSRF 校验通过（具体业务返回 2xx/5xx 取决于 save_config）
        assert resp.status_code not in (401, 403)


class TestAuthDisabledBypass:
    def test_disable_env_var_skips_auth(self, tmp_path, monkeypatch):
        config_file = tmp_path / "config.yaml"
        config_file.write_text(MIN_CONFIG, encoding="utf-8")
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        monkeypatch.setattr(JobManager, "_start_dispatcher", lambda self: None)
        monkeypatch.setenv("TREND_RADAR_WEBUI_DISABLE_AUTH", "1")

        app = create_app(
            config_path=str(config_file),
            output_path=str(output_dir),
            auth_path=str(tmp_path / AUTH_FILE_NAME),
        )
        app.config["TESTING"] = True
        client = app.test_client()
        resp = client.get("/api/config")
        # 鉴权关闭：未登录也应能访问
        assert resp.status_code == 200


class TestAuthStatusEndpoint:
    def test_status_when_not_initialized(self, fresh_app):
        client = fresh_app.test_client()
        resp = client.get("/api/auth/status")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["initialized"] is False
        assert body["authenticated"] is False

    def test_status_after_login(self, authed_app):
        client = authed_app.test_client()
        client.post(
            "/login",
            data=json.dumps(
                {"username": "admin", "password": "correct-horse-battery-staple"}
            ),
            content_type="application/json",
            headers={
                "X-Requested-With": "XMLHttpRequest",
                "Origin": "http://localhost.localdomain",
            },
        )
        resp = client.get("/api/auth/status")
        body = resp.get_json()
        assert body["initialized"] is True
        assert body["authenticated"] is True
        assert body["username"] == "admin"
