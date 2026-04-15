"""Bark notification channel."""

import contextlib
import time
from collections.abc import Callable
from typing import Any
from urllib.parse import urlparse

import requests

from trendradar.logging import get_logger
from trendradar.notification.channels.base import (
    extract_ai_stats,
    prepare_batches,
    render_ai_content,
)

logger = get_logger(__name__)


def send_to_bark(
    bark_url: str,
    report_data: dict,
    report_type: str,
    update_info: dict | None = None,
    proxy_url: str | None = None,
    mode: str = "daily",
    account_label: str = "",
    *,
    batch_size: int = 3600,
    batch_interval: float = 1.0,
    split_content_func: Callable | None = None,
    rss_items: list | None = None,
    rss_new_items: list | None = None,
    ai_analysis: Any = None,
    display_regions: dict | None = None,
    standalone_data: dict | None = None,
) -> bool:
    """Send report to Bark (batch-aware, reversed order).

    Signature and behaviour are identical to the original in ``senders.py``.
    """
    log_prefix = f"Bark{account_label}" if account_label else "Bark"
    proxies = {"http": proxy_url, "https": proxy_url} if proxy_url else None

    # Parse Bark URL to extract device_key and build /push endpoint
    parsed_url = urlparse(bark_url)
    device_key = parsed_url.path.strip("/").split("/")[0] if parsed_url.path else None

    if not device_key:
        logger.error(
            "URL \u683c\u5f0f\u9519\u8bef\uff0c\u65e0\u6cd5\u63d0\u53d6 device_key",
            channel="bark",
            account_label=log_prefix,
            bark_url=bark_url,
        )
        return False

    api_endpoint = f"{parsed_url.scheme}://{parsed_url.netloc}/push"

    ai_content = render_ai_content(ai_analysis, "bark") or None
    ai_stats = extract_ai_stats(ai_analysis)

    batches = prepare_batches(
        report_data=report_data,
        format_type="bark",
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

    total_batches = len(batches)
    logger.info(
        "\u6d88\u606f\u5206\u6279\u53d1\u9001",
        channel="bark",
        account_label=log_prefix,
        batches=total_batches,
        report_type=report_type,
    )

    # Reverse so that Bark (newest-first) displays in reading order
    reversed_batches = list(reversed(batches))
    logger.debug(
        "\u5c06\u6309\u53cd\u5411\u987a\u5e8f\u63a8\u9001\uff0c\u786e\u4fdd\u5ba2\u6237\u7aef\u663e\u793a\u987a\u5e8f\u6b63\u786e",
        channel="bark",
        account_label=log_prefix,
    )

    success_count = 0
    for idx, batch_content in enumerate(reversed_batches, 1):
        actual_batch_num = total_batches - idx + 1
        content_size = len(batch_content.encode("utf-8"))
        logger.debug(
            "\u53d1\u9001\u6279\u6b21",
            channel="bark",
            account_label=log_prefix,
            batch=actual_batch_num,
            total=total_batches,
            push_order=idx,
            size=content_size,
            report_type=report_type,
        )

        if content_size > 4096:
            logger.warning(
                "\u6279\u6b21\u6d88\u606f\u8fc7\u5927\uff0c\u53ef\u80fd\u88ab\u62d2\u7edd",
                channel="bark",
                account_label=log_prefix,
                batch=actual_batch_num,
                total=total_batches,
                size=content_size,
            )

        payload = {
            "title": report_type,
            "markdown": batch_content,
            "device_key": device_key,
            "sound": "default",
            "group": "TrendRadar",
            "action": "none",
        }

        try:
            response = requests.post(
                api_endpoint,
                json=payload,
                proxies=proxies,
                timeout=30,
            )

            if response.status_code == 200:
                result = response.json()
                if result.get("code") == 200:
                    logger.info(
                        "\u6279\u6b21\u53d1\u9001\u6210\u529f",
                        channel="bark",
                        account_label=log_prefix,
                        batch=actual_batch_num,
                        total=total_batches,
                        report_type=report_type,
                    )
                    success_count += 1
                    if idx < total_batches:
                        time.sleep(batch_interval)
                else:
                    logger.error(
                        "\u6279\u6b21\u53d1\u9001\u5931\u8d25",
                        channel="bark",
                        account_label=log_prefix,
                        batch=actual_batch_num,
                        total=total_batches,
                        report_type=report_type,
                        error=result.get("message", "\u672a\u77e5\u9519\u8bef"),
                    )
            else:
                logger.error(
                    "\u6279\u6b21\u53d1\u9001\u5931\u8d25",
                    channel="bark",
                    account_label=log_prefix,
                    batch=actual_batch_num,
                    total=total_batches,
                    report_type=report_type,
                    status_code=response.status_code,
                )
                with contextlib.suppress(Exception):
                    logger.debug(
                        "\u9519\u8bef\u8be6\u60c5", channel="bark", response_text=response.text
                    )

        except requests.exceptions.ConnectTimeout:
            logger.error(
                "\u6279\u6b21\u8fde\u63a5\u8d85\u65f6",
                channel="bark",
                account_label=log_prefix,
                batch=actual_batch_num,
                total=total_batches,
                report_type=report_type,
            )
        except requests.exceptions.ReadTimeout:
            logger.error(
                "\u6279\u6b21\u8bfb\u53d6\u8d85\u65f6",
                channel="bark",
                account_label=log_prefix,
                batch=actual_batch_num,
                total=total_batches,
                report_type=report_type,
            )
        except requests.exceptions.ConnectionError as e:
            logger.error(
                "\u6279\u6b21\u8fde\u63a5\u9519\u8bef",
                channel="bark",
                account_label=log_prefix,
                batch=actual_batch_num,
                total=total_batches,
                report_type=report_type,
                error=str(e),
            )
        except Exception as e:
            logger.error(
                "\u6279\u6b21\u53d1\u9001\u5f02\u5e38",
                channel="bark",
                account_label=log_prefix,
                batch=actual_batch_num,
                total=total_batches,
                report_type=report_type,
                error=str(e),
            )

    if success_count == total_batches:
        logger.info(
            "\u6240\u6709\u6279\u6b21\u53d1\u9001\u5b8c\u6210",
            channel="bark",
            account_label=log_prefix,
            batches=total_batches,
            report_type=report_type,
        )
    elif success_count > 0:
        logger.warning(
            "\u90e8\u5206\u53d1\u9001\u6210\u529f",
            channel="bark",
            account_label=log_prefix,
            success_count=success_count,
            total=total_batches,
            report_type=report_type,
        )
    else:
        logger.error(
            "\u53d1\u9001\u5b8c\u5168\u5931\u8d25",
            channel="bark",
            account_label=log_prefix,
            report_type=report_type,
        )
        return False

    return True
