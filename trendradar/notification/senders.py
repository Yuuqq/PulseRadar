# coding=utf-8
"""
Backward-compatible re-export layer.

All channel implementations have been moved to ``trendradar.notification.channels.*``.
This module re-exports every public symbol so that existing imports such as::

    from trendradar.notification.senders import send_to_feishu

continue to work without modification.
"""

from trendradar.notification.channels.feishu import send_to_feishu
from trendradar.notification.channels.dingtalk import send_to_dingtalk
from trendradar.notification.channels.wework import send_to_wework
from trendradar.notification.channels.telegram import send_to_telegram
from trendradar.notification.channels.email import send_to_email, SMTP_CONFIGS
from trendradar.notification.channels.ntfy import send_to_ntfy
from trendradar.notification.channels.bark import send_to_bark
from trendradar.notification.channels.slack import send_to_slack
from trendradar.notification.channels.webhook import send_to_generic_webhook

__all__ = [
    "send_to_feishu",
    "send_to_dingtalk",
    "send_to_wework",
    "send_to_telegram",
    "send_to_email",
    "send_to_ntfy",
    "send_to_bark",
    "send_to_slack",
    "send_to_generic_webhook",
    "SMTP_CONFIGS",
]
