"""Route-level tests for redirect, stats, URL validation and base URL."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from fastapi.testclient import TestClient

import main

client = TestClient(main.app)
AUTH = {"X-API-Key": "dev-key"}


@pytest.fixture(autouse=True)
def clean_slate(monkeypatch):
    monkeypatch.delenv("SNIPURL_API_KEYS", raising=False)
    monkeypatch.delenv("SNIPURL_BASE_URL", raising=False)
    for limiter in (main.shorten_limiter, main.redirect_limiter, main.stats_limiter):
        limiter.reset()


def test_redirect_unknown_code_404():
    resp = client.get("/nope123", follow_redirects=False)
    assert resp.status_code == 404


def test_stats_unknown_code_404():
    resp = client.get("/stats/nope123", headers=AUTH)
    assert resp.status_code == 404


def test_redirect_valid_code_307():
    code = client.post("/shorten", json={"url": "https://example.com"}, headers=AUTH).json()["code"]
    resp = client.get(f"/{code}", follow_redirects=False)
    assert resp.status_code == 307
    assert resp.headers["location"] == "https://example.com"
    stats = client.get(f"/stats/{code}", headers=AUTH)
    assert stats.status_code == 200
    assert stats.json()["long_url"] == "https://example.com"


@pytest.mark.parametrize(
    "bad", ["javascript:alert(1)", "file:///etc/passwd", "ftp://example.com", "not a url", ""]
)
def test_shorten_rejects_bad_url(bad):
    resp = client.post("/shorten", json={"url": bad}, headers=AUTH)
    assert resp.status_code == 422


def test_short_url_default_base():
    resp = client.post("/shorten", json={"url": "https://example.com"}, headers=AUTH)
    assert resp.json()["short_url"] == f"http://snip.url/{resp.json()['code']}"


def test_short_url_honors_base_url_env(monkeypatch):
    monkeypatch.setenv("SNIPURL_BASE_URL", "https://sn.ip/")
    resp = client.post("/shorten", json={"url": "https://example.com"}, headers=AUTH)
    body = resp.json()
    assert body["short_url"] == f"https://sn.ip/{body['code']}"
