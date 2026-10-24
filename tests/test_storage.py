import threading

from storage import Storage


def test_increment_clicks():
    s = Storage()
    s.save("abc", "https://example.com")
    assert s.increment_clicks("abc") == 1
    assert s.increment_clicks("abc") == 2
    assert s.get_clicks("abc") == 2


def test_increment_unknown_code_returns_zero_and_creates_nothing():
    s = Storage()
    assert s.increment_clicks("nope") == 0
    assert "nope" not in s._clicks
    assert s.get_clicks("nope") == 0


def test_next_id_concurrent_unique():
    s = Storage()
    results = []

    def worker():
        ids = [s.next_id() for _ in range(500)]
        results.extend(ids)  # list.extend is atomic under the GIL

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(results) == 4000
    assert len(set(results)) == 4000
