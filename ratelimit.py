# In-memory, per-process sliding-window limiter. Swap for a Redis-backed
# limiter when running more than one instance in production.
import math
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request


class RateLimiter:
    def __init__(self, limit, window_seconds):
        self.limit = limit
        self.window = window_seconds
        self._hits = defaultdict(deque)

    def hit(self, key, now=None):
        """Record a request. Returns 0 if allowed, else seconds until a slot frees."""
        if now is None:
            now = time.monotonic()
        hits = self._hits[key]
        while hits and hits[0] <= now - self.window:
            hits.popleft()
        if len(hits) >= self.limit:
            return hits[0] + self.window - now
        hits.append(now)
        return 0

    def reset(self):
        self._hits.clear()


def client_identity(request: Request):
    # Authenticated callers are limited per key, anonymous ones per client IP.
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return "key:" + api_key
    if request.client:
        return "ip:" + request.client.host
    return "ip:unknown"


def rate_limit(limiter):
    def dependency(request: Request):
        wait = limiter.hit(client_identity(request))
        if wait:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded",
                headers={"Retry-After": str(max(1, math.ceil(wait)))},
            )

    return dependency
