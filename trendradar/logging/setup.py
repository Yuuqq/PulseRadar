# coding=utf-8
"""
结构化日志配置

提供统一的日志初始化和获取接口，替代全局 print()。
"""

import logging
import sys
from typing import Optional

import structlog


def configure_logging(debug: bool = False, json_output: bool = False) -> None:
    """
    配置全局结构化日志。

    Args:
        debug: 是否启用 DEBUG 级别
        json_output: 是否输出 JSON 格式（适合生产环境日志聚合）
    """
    level = logging.DEBUG if debug else logging.INFO

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if json_output:
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer(
            ensure_ascii=False
        )
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=sys.stderr.isatty())

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
        foreign_pre_chain=shared_processors,
    )

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    # 降低第三方库的日志噪音
    for noisy in ("urllib3", "botocore", "boto3", "litellm", "httpx"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: Optional[str] = None) -> structlog.stdlib.BoundLogger:
    """
    获取结构化日志实例。

    Args:
        name: 日志器名称，通常传 __name__

    Returns:
        绑定的结构化日志实例
    """
    return structlog.get_logger(name)
