"""
报告模式策略表 (Task 6 — 单一权威定义)

历史上 ``MODE_STRATEGIES`` 作为类属性挂在 ``AnalysisEngine`` 上，并被作为
``dict`` 透传给 ``mode_strategy.execute_mode_strategy`` 与
``notification_service.send_notification_if_needed``。这导致：

1. 字典 key/value 的 schema 完全靠口头约定，无类型保护
2. 模式名（"daily"/"current"/"incremental"）以裸字符串散落在多处
3. 调用方拿到的是 ``dict``，IDE 与 mypy 无法给出补全/校验

本模块把策略定义抽成模块级常量 + ``TypedDict``，并提供类型化的
``ReportMode`` Literal 与 ``get_mode_strategy()`` 查询函数，作为唯一
权威来源。``AnalysisEngine`` 与 ``mode_strategy.py`` 等模块从此处导入。
"""

from __future__ import annotations

from typing import Literal, TypedDict

# 报告模式名称 — 用 Literal 替代裸字符串，调用方可在签名中使用
ReportMode = Literal["incremental", "current", "daily"]


class ModeStrategy(TypedDict):
    """单个报告模式的策略元数据。

    Fields:
        mode_name: 模式中文短名（用于日志/通知标题）
        description: 模式行为说明（用于日志）
        report_type: 报告头部展示的类型字符串
        should_send_notification: 是否在该模式下推送通知
    """

    mode_name: str
    description: str
    report_type: str
    should_send_notification: bool


# 全局唯一的模式策略表
MODE_STRATEGIES: dict[ReportMode, ModeStrategy] = {
    "incremental": {
        "mode_name": "增量模式",
        "description": "增量模式（只关注新增新闻，无新增时不推送）",
        "report_type": "增量分析",
        "should_send_notification": True,
    },
    "current": {
        "mode_name": "当前榜单模式",
        "description": "当前榜单模式（当前榜单匹配新闻 + 新增新闻区域 + 按时推送）",
        "report_type": "当前榜单",
        "should_send_notification": True,
    },
    "daily": {
        "mode_name": "全天汇总模式",
        "description": "全天汇总模式（所有匹配新闻 + 新增新闻区域 + 按时推送）",
        "report_type": "全天汇总",
        "should_send_notification": True,
    },
}

# 当配置中传入未知模式时使用的兜底
DEFAULT_REPORT_MODE: ReportMode = "daily"


def get_mode_strategy(report_mode: str) -> ModeStrategy:
    """根据模式名取出策略字典；未知模式回退到 DEFAULT_REPORT_MODE。

    Args:
        report_mode: 配置中的模式字符串（来源不可信，可能是任意值）

    Returns:
        对应的 ``ModeStrategy``，永远非 ``None``
    """
    if report_mode in MODE_STRATEGIES:
        return MODE_STRATEGIES[report_mode]  # type: ignore[index]
    return MODE_STRATEGIES[DEFAULT_REPORT_MODE]
