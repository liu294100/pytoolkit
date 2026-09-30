"""多窗口滑动限流器（Riot 的限流按路由域分别计算）"""

from __future__ import annotations

import threading
import time
from collections import deque
from typing import Deque, Dict, List, Sequence, Tuple


class SlidingWindowLimiter:
    def __init__(self, limits: Sequence[Sequence[int]]):
        # limits: [[次数, 秒], ...]
        self.limits: List[Tuple[int, float]] = [(int(n), float(s)) for n, s in limits]
        self._hits: Deque[float] = deque()
        self._lock = threading.Lock()
        self._blocked_until = 0.0

    def block_for(self, seconds: float) -> None:
        with self._lock:
            self._blocked_until = max(self._blocked_until, time.monotonic() + seconds)

    def acquire(self) -> None:
        while True:
            with self._lock:
                now = time.monotonic()
                wait = self._blocked_until - now
                if wait <= 0:
                    longest = max((s for _, s in self.limits), default=1)
                    while self._hits and now - self._hits[0] > longest:
                        self._hits.popleft()
                    wait = 0.0
                    for count, span in self.limits:
                        in_window = [t for t in self._hits if now - t < span]
                        if len(in_window) >= count:
                            wait = max(wait, span - (now - in_window[-count]) + 0.01)
                    if wait <= 0:
                        self._hits.append(now)
                        return
            time.sleep(min(wait, 1.0))


class LimiterPool:
    def __init__(self, limits: Sequence[Sequence[int]]):
        self.limits = limits
        self._pool: Dict[str, SlidingWindowLimiter] = {}
        self._lock = threading.Lock()

    def for_host(self, host: str) -> SlidingWindowLimiter:
        with self._lock:
            if host not in self._pool:
                self._pool[host] = SlidingWindowLimiter(self.limits)
            return self._pool[host]
