"""Feishu (Lark) notification channel."""

import time
from collections.abc import Callable
from typing import Any

import requests

from trendradar.logging import get_logger
from trendradar.notification.channels.base import (
    extract_ai_stats,
    prepare_batches,
    render_ai_content,
)

logger = get_logger(__name__)


def send_to_feishu(
    webhook_url: str,
    report_data: dict,
    report_type: str,
    update_info: dict | None = None,
    proxy_url: str | None = None,
    mode: str = "daily",
    account_label: str = "",
    *,
    batch_size: int = 29000,
    batch_interval: float = 1.0,
    split_content_func: Callable | None = None,
    get_time_func: Callable | None = None,
    rss_items: list | None = None,
    rss_new_items: list | None = None,
    ai_analysis: Any = None,
    display_regions: dict | None = None,
    standalone_data: dict | None = None,
) -> bool:
    """Send report to Feishu via webhook (batch-aware).

    Signature and behaviour are identical to the original in ``senders.py``.
    """
    headers = {"Content-Type": "application/json"}
    proxies = {"http": proxy_url, "https": proxy_url} if proxy_url else None
    log_prefix = f"\u98de\u4e66{account_label}" if account_label else "\u98de\u4e66"

    ai_content = render_ai_content(ai_analysis, "feishu") or None
    ai_stats = extract_ai_stats(ai_analysis)

    batches = prepare_batches(
        report_data=report_data,
        format_type="feishu",
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
        channel="feishu", account_label=log_prefix,
        batches=len(batches), report_type=report_type,
    )

    for i, batch_content in enumerate(batches, 1):
        content_size = len(batch_content.encode("utf-8"))
        logger.debug(
            "\u53d1\u9001\u6279\u6b21",
            channel="feishu", account_label=log_prefix,
            batch=i, total=len(batches), size=content_size,
            report_type=report_type,
        )

        payload = {
            "msg_type": "text",
            "content": {"text": batch_content},
        }

        try:
            response = requests.post(
                webhook_url, headers=headers, json=payload,
                proxies=proxies, timeout=30,
            )
            if response.status_code == 200:
                result = response.json()
                if result.get("StatusCode") == 0 or result.get("code") == 0:
                    logger.info(
                        "\u6279\u6b21\u53d1\u9001\u6210\u529f",
                        channel="feishu", account_label=log_prefix,
                        batch=i, total=len(batches), report_type=report_type,
                    )
                    if i < len(batches):
                        time.sleep(batch_interval)
                else:
                    error_msg = result.get("msg") or result.get("StatusMessage", "\u672a\u77e5\u9519\u8bef")
                    logger.error(
                        "\u6279\u6b21\u53d1\u9001\u5931\u8d25",
                        channel="feishu", account_label=log_prefix,
                        batch=i, total=len(batches),
                        report_type=report_type, error=error_msg,
                    )
                    return False
            else:
                logger.error(
                    "\u6279\u6b21\u53d1\u9001\u5931\u8d25",
                    channel="feishu", account_label=log_prefix,
                    batch=i, total=len(batches),
                    report_type=report_type, status_code=response.status_code,
                )
                return False
        except Exception as e:
            logger.error(
                "\u6279\u6b21\u53d1\u9001\u51fa\u9519",
                channel="feishu", account_label=log_prefix,
                batch=i, total=len(batches),
                report_type=report_type, error=str(e),
            )
            return False

    logger.info(
        "\u6240\u6709\u6279\u6b21\u53d1\u9001\u5b8c\u6210",
        channel="feishu", account_label=log_prefix,
        batches=len(batches), report_type=report_type,
    )
    return True
