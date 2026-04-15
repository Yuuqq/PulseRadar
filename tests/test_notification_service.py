from __future__ import annotations

from unittest.mock import MagicMock


def _make_ctx_with_channels(**overrides):
    """Build a mock AppContext with notification channel config."""
    defaults = {
        "FEISHU_WEBHOOK_URL": "",
        "DINGTALK_WEBHOOK_URL": "",
        "WEWORK_WEBHOOK_URL": "",
        "TELEGRAM_BOT_TOKEN": "",
        "TELEGRAM_CHAT_ID": "",
        "EMAIL_FROM": "",
        "EMAIL_PASSWORD": "",
        "EMAIL_TO": "",
        "NTFY_SERVER_URL": "",
        "NTFY_TOPIC": "",
        "BARK_URL": "",
        "SLACK_WEBHOOK_URL": "",
        "GENERIC_WEBHOOK_URL": "",
    }
    defaults.update(overrides)

    ctx = MagicMock()
    ctx.config = defaults
    return ctx


# ---------------------------------------------------------------------------
# has_notification_configured
# ---------------------------------------------------------------------------


def test_has_notification_configured_returns_false_when_no_channels():
    from trendradar.core.notification_service import has_notification_configured

    ctx = _make_ctx_with_channels()
    assert has_notification_configured(ctx) is False


def test_has_notification_configured_returns_true_for_feishu():
    from trendradar.core.notification_service import has_notification_configured

    ctx = _make_ctx_with_channels(FEISHU_WEBHOOK_URL="https://feishu.example.com/hook")
    assert has_notification_configured(ctx) is True


def test_has_notification_configured_returns_true_for_dingtalk():
    from trendradar.core.notification_service import has_notification_configured

    ctx = _make_ctx_with_channels(DINGTALK_WEBHOOK_URL="https://dingtalk.example.com/hook")
    assert has_notification_configured(ctx) is True


def test_has_notification_configured_returns_true_for_telegram():
    from trendradar.core.notification_service import has_notification_configured

    ctx = _make_ctx_with_channels(
        TELEGRAM_BOT_TOKEN="bot123:ABC",
        TELEGRAM_CHAT_ID="-100123456",
    )
    assert has_notification_configured(ctx) is True


def test_has_notification_configured_returns_false_for_partial_telegram():
    from trendradar.core.notification_service import has_notification_configured

    # Only token, no chat_id
    ctx = _make_ctx_with_channels(TELEGRAM_BOT_TOKEN="bot123:ABC")
    assert has_notification_configured(ctx) is False


def test_has_notification_configured_returns_true_for_email():
    from trendradar.core.notification_service import has_notification_configured

    ctx = _make_ctx_with_channels(
        EMAIL_FROM="from@example.com",
        EMAIL_PASSWORD="secret",
        EMAIL_TO="to@example.com",
    )
    assert has_notification_configured(ctx) is True


def test_has_notification_configured_returns_true_for_ntfy():
    from trendradar.core.notification_service import has_notification_configured

    ctx = _make_ctx_with_channels(
        NTFY_SERVER_URL="https://ntfy.sh",
        NTFY_TOPIC="my-topic",
    )
    assert has_notification_configured(ctx) is True


def test_has_notification_configured_returns_true_for_bark():
    from trendradar.core.notification_service import has_notification_configured

    ctx = _make_ctx_with_channels(BARK_URL="https://bark.example.com/push")
    assert has_notification_configured(ctx) is True


def test_has_notification_configured_returns_true_for_slack():
    from trendradar.core.notification_service import has_notification_configured

    ctx = _make_ctx_with_channels(SLACK_WEBHOOK_URL="https://hooks.slack.com/T/B/X")
    assert has_notification_configured(ctx) is True


def test_has_notification_configured_returns_true_for_generic_webhook():
    from trendradar.core.notification_service import has_notification_configured

    ctx = _make_ctx_with_channels(GENERIC_WEBHOOK_URL="https://webhook.example.com")
    assert has_notification_configured(ctx) is True


def test_has_notification_configured_returns_true_for_wework():
    from trendradar.core.notification_service import has_notification_configured

    ctx = _make_ctx_with_channels(WEWORK_WEBHOOK_URL="https://qyapi.weixin.qq.com/hook")
    assert has_notification_configured(ctx) is True


# ---------------------------------------------------------------------------
# has_valid_content
# ---------------------------------------------------------------------------


def test_has_valid_content_incremental_with_nonzero_counts():
    from trendradar.core.notification_service import has_valid_content

    stats = [{"count": 3}, {"count": 0}]
    assert has_valid_content("incremental", stats) is True


def test_has_valid_content_incremental_with_zero_counts():
    from trendradar.core.notification_service import has_valid_content

    stats = [{"count": 0}, {"count": 0}]
    assert has_valid_content("incremental", stats) is False


def test_has_valid_content_current_mode():
    from trendradar.core.notification_service import has_valid_content

    stats = [{"count": 5}]
    assert has_valid_content("current", stats) is True


def test_has_valid_content_current_mode_empty():
    from trendradar.core.notification_service import has_valid_content

    stats = [{"count": 0}]
    assert has_valid_content("current", stats) is False


def test_has_valid_content_daily_mode_with_stats():
    from trendradar.core.notification_service import has_valid_content

    stats = [{"count": 2}]
    assert has_valid_content("daily", stats) is True


def test_has_valid_content_daily_mode_with_new_titles_only():
    from trendradar.core.notification_service import has_valid_content

    stats = [{"count": 0}]
    new_titles = {"src1": ["New Headline"]}
    assert has_valid_content("daily", stats, new_titles) is True


def test_has_valid_content_daily_mode_neither_stats_nor_new():
    from trendradar.core.notification_service import has_valid_content

    stats = [{"count": 0}]
    new_titles = {"src1": []}
    assert has_valid_content("daily", stats, new_titles) is False


def test_has_valid_content_daily_mode_none_new_titles():
    from trendradar.core.notification_service import has_valid_content

    stats = [{"count": 0}]
    assert has_valid_content("daily", stats, None) is False
