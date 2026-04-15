"""
notification.channels -- individual notification channel implementations.

Each channel lives in its own module and exposes a single public ``send_to_*``
function whose signature is identical to the original in ``senders.py``.

The ``base`` module provides shared helpers (AI stats extraction,
batch preparation) used by all webhook-based channels.
"""

from trendradar.notification.channels.bark import send_to_bark
from trendradar.notification.channels.dingtalk import send_to_dingtalk
from trendradar.notification.channels.email import SMTP_CONFIGS, send_to_email
from trendradar.notification.channels.feishu import send_to_feishu
from trendradar.notification.channels.ntfy import send_to_ntfy
from trendradar.notification.channels.slack import send_to_slack
from trendradar.notification.channels.telegram import send_to_telegram
from trendradar.notification.channels.webhook import send_to_generic_webhook
from trendradar.notification.channels.wework import send_to_wework

__all__ = [
    "SMTP_CONFIGS",
    "send_to_bark",
    "send_to_dingtalk",
    "send_to_email",
    "send_to_feishu",
    "send_to_generic_webhook",
    "send_to_ntfy",
    "send_to_slack",
    "send_to_telegram",
    "send_to_wework",
]
