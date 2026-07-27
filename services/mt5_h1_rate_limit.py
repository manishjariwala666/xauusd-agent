"""Small in-process rate limiter for MT5 ingestion.

PostgreSQL/Redis rate limiting can replace this later without changing
the ingestion contract.
"""

from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from threading import Lock


class MT5RateLimiter:
    def __init__(
        self,
        *,
        max_requests: int = 30,
        window: timedelta = timedelta(minutes=1),
    ) -> None:
        self.max_requests = max_requests
        self.window = window
        self._lock = Lock()
        self._requests: dict[str, deque[datetime]] = defaultdict(deque)

    def allow(
        self,
        key: str,
        *,
        now: datetime | None = None,
    ) -> bool:
        current = now or datetime.now(timezone.utc)
        cutoff = current - self.window
        normalized = key.strip() or "unknown"

        with self._lock:
            requests = self._requests[normalized]

            while requests and requests[0] <= cutoff:
                requests.popleft()

            if len(requests) >= self.max_requests:
                return False

            requests.append(current)
            return True

    def reset(self) -> None:
        with self._lock:
            self._requests.clear()
