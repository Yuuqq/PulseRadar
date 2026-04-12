# coding=utf-8
"""熔断器 — 防止对持续失败的数据源反复请求"""
import time
import threading
from typing import Dict
from trendradar.logging import get_logger

logger = get_logger(__name__)

class CircuitBreaker:
    """
    简单熔断器

    连续失败 N 次后开路（跳过请求），冷却后自动半开尝试。

    States:
        CLOSED -> 正常请求
        OPEN -> 跳过请求（熔断中）
        HALF_OPEN -> 冷却后尝试一次
    """

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

    def __init__(self, failure_threshold: int = 3, cooldown_seconds: float = 60.0):
        self._failure_threshold = failure_threshold
        self._cooldown = cooldown_seconds
        self._states: Dict[str, str] = {}
        self._failure_counts: Dict[str, int] = {}
        self._last_failure_time: Dict[str, float] = {}
        self._lock = threading.Lock()

    def allow_request(self, key: str) -> bool:
        """检查是否允许请求"""
        with self._lock:
            state = self._states.get(key, self.CLOSED)

            if state == self.CLOSED:
                return True

            if state == self.OPEN:
                elapsed = time.monotonic() - self._last_failure_time.get(key, 0)
                if elapsed >= self._cooldown:
                    self._states[key] = self.HALF_OPEN
                    logger.info("熔断器半开", source=key)
                    return True
                return False

            # HALF_OPEN: 允许一次尝试
            return True

    def record_success(self, key: str) -> None:
        """记录成功"""
        with self._lock:
            self._states[key] = self.CLOSED
            self._failure_counts[key] = 0

    def record_failure(self, key: str) -> None:
        """记录失败"""
        with self._lock:
            count = self._failure_counts.get(key, 0) + 1
            self._failure_counts[key] = count
            self._last_failure_time[key] = time.monotonic()

            if count >= self._failure_threshold:
                self._states[key] = self.OPEN
                logger.warning("熔断器开路", source=key, failures=count, cooldown_seconds=self._cooldown)
