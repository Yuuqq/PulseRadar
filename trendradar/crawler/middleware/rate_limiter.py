"""自适应限速器"""
import threading
import time
from collections import defaultdict

from trendradar.logging import get_logger

logger = get_logger(__name__)

class RateLimiter:
    """
    令牌桶限速器

    每个 domain/source_type 独立限速。
    """

    def __init__(self, default_rps: float = 2.0):
        """
        Args:
            default_rps: 默认每秒请求数
        """
        self._default_rps = default_rps
        self._last_request: dict[str, float] = defaultdict(float)
        self._lock = threading.Lock()

    def wait(self, key: str, rps: float | None = None) -> None:
        """
        等待直到可以发送请求

        Args:
            key: 限速键（通常是 source_type 或 domain）
            rps: 每秒请求数（None 则使用默认值）
        """
        effective_rps = rps or self._default_rps
        min_interval = 1.0 / effective_rps

        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_request[key]
            if elapsed < min_interval:
                sleep_time = min_interval - elapsed
                time.sleep(sleep_time)
            self._last_request[key] = time.monotonic()
