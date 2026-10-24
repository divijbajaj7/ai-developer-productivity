"""Tests for API key auth and rate limiting."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from fastapi.testclient import TestClient

import main
from ratelimit import RateLimiter

client = TestClient(main.app)
AUTH = {"X-API-Key": "dev-key"}


@pytest.fixture(autouse=True)
def clean_slate(monkeypatch):
    monkeypatch.delenv("SNIPURL_API_KEYS", raising=False)
    for limiter in (main.shorten_limiter, main.redirect_limiter, main.stats_limiter):
        limiter.reset()


def test_shorten_requires_api_key():
    resp = client.post("/shorten", json={"url": "https://example.com"})
    assert resp.status_code == 401


def test_shorten_rejects_invalid_api_key():
    resp = client.post(
        "/shorten", json={"url": "https://example.com"}, headers={"X-API-Key": "wrong"}
    )
    assert resp.status_code == 401


def test_shorten_accepts_valid_api_key():
    resp = client.post("/shorten", json={"url": "https://example.com"}, headers=AUTH)
    assert resp.status_code == 200
    assert resp.json()["code"]


def test_stats_requires_api_key():
    assert client.get("/stats/abc").status_code == 401


def test_api_keys_come_from_env(monkeypatch):
    monkeypatch.setenv("SNIPURL_API_KEYS", "alpha, beta")
    body = {"url": "https://example.com"}
    assert client.post("/shorten", json=body, headers={"X-API-Key": "beta"}).status_code == 200
    assert client.post("/shorten", json=body, headers=AUTH).status_code == 401


def test_redirect_stays_public():
    code = client.post(
        "/shorten", json={"url": "https://example.com"}, headers=AUTH
    ).json()["code"]
    resp = client.get(f"/{code}", follow_redirects=False)
    assert resp.status_code == 307
    assert resp.headers["location"] == "https://example.com"


def test_shorten_rate_limit_returns_429():
    body = {"url": "https://example.com"}
    for _ in range(main.shorten_limiter.limit):
        assert client.post("/shorten", json=body, headers=AUTH).status_code == 200
    resp = client.post("/shorten", json=body, headers=AUTH)
    assert resp.status_code == 429
    assert int(resp.headers["Retry-After"]) >= 1


def test_rate_limiter_window_slides():
    limiter = RateLimiter(limit=2, window_seconds=60)
    assert limiter.hit("k", now=100) == 0
    assert limiter.hit("k", now=101) == 0
    assert limiter.hit("k", now=102) > 0
    assert limiter.hit("k", now=161) == 0  # first hit has aged out of the window
