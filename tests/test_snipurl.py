"""Core tests for SnipURL."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from storage import Storage
from service import encode_base62, shorten


def test_shorten_creates_code():
    """A shortened URL gets a non-empty code and is retrievable."""
    store = Storage()
    code = shorten(store, "https://example.com")
    assert code
    assert store.get_url(code) == "https://example.com"


def test_click_counter_increments():
    store = Storage()
    store.save("abc", "https://example.com")
    store.increment_clicks("abc")
    store.increment_clicks("abc")
    assert store.get_clicks("abc") == 2


def test_encode_base62_handles_zero():
    assert encode_base62(0) != ""
