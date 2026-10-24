# In-memory, per-process sliding-window limiter. Swap for a Redis-backed
# limiter when running more than one instance in production.
import math
import secrets
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

from auth import load_api_keys


class RateLimiter:
    SWEEP_THRESHOLD = 1000

    def __init__(self, limit, window_seconds):
        self.limit = limit
        self.window = window_seconds
        self._hits = defaultdict(deque)

    def hit(self, key, now=None):
        """Record a request. Returns 0 if allowed, else seconds until a slot frees."""
        if now is None:
            now = time.monotonic()
        if len(self._hits) > self.SWEEP_THRESHOLD:
            self._sweep(now)
        hits = self._hits[key]
        while hits and hits[0] <= now - self.window:
            hits.popleft()
        if len(hits) >= self.limit:
            return hits[0] + self.window - now
        hits.append(now)
        return 0

    def _sweep(self, now):
        # Drop keys whose hits have all expired so idle clients don't pile up.
        for k in [k for k, h in self._hits.items() if not h or h[-1] <= now - self.window]:
            del self._hits[k]

    def reset(self):
        self._hits.clear()


def client_identity(request: Request):
    # Valid keys are limited per key; anything else (including unknown keys sent
    # to bypass the limit) is limited per client IP.
    api_key = request.headers.get("X-API-Key")
    if api_key:
        for valid_key in load_api_keys():
            if secrets.compare_digest(api_key, valid_key):
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
