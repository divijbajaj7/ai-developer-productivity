"""Starter tests for SnipURL.

One test passes today. Two are marked xfail because they document the
*planted* bugs this repo ships with for the masterclass — the debugging
and review demos are expected to find and fix these, flipping xfail -> pass.
"""
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


@pytest.mark.xfail(reason="planted bug: increment_clicks discards count+1", strict=True)
def test_click_counter_increments():
    store = Storage()
    store.save("abc", "https://example.com")
    store.increment_clicks("abc")
    store.increment_clicks("abc")
    assert store.get_clicks("abc") == 2  # currently returns 0


@pytest.mark.xfail(reason="planted bug: encode_base62(0) returns empty string", strict=True)
def test_encode_base62_handles_zero():
    assert encode_base62(0) != ""  # currently returns ""
