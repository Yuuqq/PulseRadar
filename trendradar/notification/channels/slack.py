# coding=utf-8
"""Slack notification channel."""

import time
from typing import Any, Callable, Dict, Optional

import requests

from trendradar.logging import get_logger
from trendradar.notification.channels.base import (
    extract_ai_stats,
    prepare_batches,
    render_ai_content,
)
from trendradar.notification.formatters import convert_markdown_to_mrkdwn

logger = get_logger(__name__)


def send_to_slack(
    webhook_url: str,
    report_data: Dict,
    report_type: str,
    update_info: Optional[Dict] = None,
    proxy_url: Optional[str] = None,
    mode: str = "daily",
    account_label: str = "",
    *,
    batch_size: int = 4000,
    batch_interval: float = 1.0,
    split_content_func: Callable = None,
    rss_items: Optional[list] = None,
    rss_new_items: Optional[list] = None,
    ai_analysis: Any = None,
    display_regions: Optional[Dict] = None,
    standalone_data: Optional[Dict] = None,
) -> bool:
    """Send report to Slack via Incoming Webhook (batch-aware, mrkdwn).

    Signature and behaviour are identical to the original in ``senders.py``.
    """
    headers = {"Content-Type": "application/json"}
    proxies = {"http": proxy_url, "https": proxy_url} if proxy_url else None
    log_prefix = f"Slack{account_label}" if account_label else "Slack"

    ai_content = render_ai_content(ai_analysis, "slack") or None
    ai_stats = extract_ai_stats(ai_analysis)

    batches = prepare_batches(
        report_data=report_data,
        format_type="slack",
        split_content_func=split_content_func,
        update_info=update_info,
        batch_size=batch_size,
        mode=mode,
        rss_items=rss_items,
        rss_new_items=rss_new_items,
        ai_content=ai_content,
        standalone_data=standalone_data,
        ai_stats=ai_stats,
        report_type=report_type,
    )

    logger.info(
        "\u6d88\u606f\u5206\u6279\u53d1\u9001",
        channel="slack", account_label=log_prefix,
        batches=len(batches), report_type=report_type,
    )

    for i, batch_content in enumerate(batches, 1):
        # Convert standard Markdown to Slack mrkdwn
        mrkdwn_content = convert_markdown_to_mrkdwn(batch_content)
        content_size = len(mrkdwn_content.encode("utf-8"))
        logger.debug(
            "\u53d1\u9001\u6279\u6b21",
            channel="slack", account_label=log_prefix,
            batch=i, total=len(batches), size=content_size,
            report_type=report_type,
        )

        payload = {"text": mrkdwn_content}

        try:
            response = requests.post(
                webhook_url, headers=headers, json=payload,
                proxies=proxies, timeout=30,
            )
            # Slack returns literal "ok" text on success
            if response.status_code == 200 and response.text == "ok":
                logger.info(
                    "\u6279\u6b21\u53d1\u9001\u6210\u529f",
                    channel="slack", account_label=log_prefix,
                    batch=i, total=len(batches), report_type=report_type,
                )
                if i < len(batches):
                    time.sleep(batch_interval)
            else:
                error_msg = response.text if response.text else f"\u72b6\u6001\u7801\uff1a{response.status_code}"
                logger.error(
                    "\u6279\u6b21\u53d1\u9001\u5931\u8d25",
                    channel="slack", account_label=log_prefix,
                    batch=i, total=len(batches),
                    report_type=report_type, error=error_msg,
                )
                return False
        except Exception as e:
            logger.error(
                "\u6279\u6b21\u53d1\u9001\u51fa\u9519",
                channel="slack", account_label=log_prefix,
                batch=i, total=len(batches),
                report_type=report_type, error=str(e),
            )
            return False

    logger.info(
        "\u6240\u6709\u6279\u6b21\u53d1\u9001\u5b8c\u6210",
        channel="slack", account_label=log_prefix,
        batches=len(batches), report_type=report_type,
    )
    return True
