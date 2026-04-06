from __future__ import annotations

from collections import defaultdict, deque
from time import monotonic


class InMemoryRateLimiter:
    def __init__(self, max_requests: int, window_seconds: int) -> None:
        self.max_requests = max(1, max_requests)
        self.window_seconds = max(1, window_seconds)
        self._events: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str, now: float | None = None) -> bool:
        timestamp = monotonic() if now is None else now
        window_start = timestamp - self.window_seconds
        bucket = self._events[key]

        while bucket and bucket[0] <= window_start:
            bucket.popleft()

        if len(bucket) >= self.max_requests:
            return False

        bucket.append(timestamp)
        return True

