"""Tests for rate-limit client identity (spoofed API keys must not bypass limits)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from fastapi.testclient import TestClient

import main
from ratelimit import RateLimiter

client = TestClient(main.app)


@pytest.fixture(autouse=True)
def clean_slate(monkeypatch):
    monkeypatch.delenv("SNIPURL_API_KEYS", raising=False)
    for limiter in (main.shorten_limiter, main.redirect_limiter, main.stats_limiter):
        limiter.reset()


def test_invalid_keys_on_public_route_are_limited_by_ip():
    limit = main.redirect_limiter.limit
    statuses = [
        client.get("/nope", headers={"X-API-Key": f"fake-{i}"}, follow_redirects=False).status_code
        for i in range(limit + 5)
    ]
    assert statuses[-1] == 429
    assert statuses.count(429) == 5
    assert list(main.redirect_limiter._hits) == ["ip:testclient"]


def test_valid_key_is_keyed_separately_from_ip():
    limit = main.redirect_limiter.limit
    for _ in range(limit):
        client.get("/nope", follow_redirects=False)
    assert client.get("/nope", follow_redirects=False).status_code == 429
    # A valid key gets its own bucket, so it is not throttled by the IP's usage.
    resp = client.get("/nope", headers={"X-API-Key": "dev-key"}, follow_redirects=False)
    assert resp.status_code != 429
    assert "key:dev-key" in main.redirect_limiter._hits


def test_idle_keys_are_swept():
    limiter = RateLimiter(limit=1, window_seconds=10)
    limiter.SWEEP_THRESHOLD = 5
    for i in range(10):
        limiter.hit(f"ip:{i}", now=0)
    assert limiter.hit("ip:new", now=100) == 0
    assert list(limiter._hits) == ["ip:new"]
