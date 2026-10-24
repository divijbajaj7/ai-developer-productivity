from service import VISIT_LOG, encode_base62, record_visit


def test_encode_base62_zero():
    assert encode_base62(0) == "a"


def test_encode_base62_small_values():
    assert encode_base62(1) == "b"
    assert encode_base62(62) == "ba"


def test_record_visit_no_leak_between_explicit_logs():
    first = record_visit("abc", log=[])
    second = record_visit("xyz", log=[])
    assert first == ["abc"]
    assert second == ["xyz"]


def test_record_visit_default_log_is_bounded():
    for i in range(VISIT_LOG.maxlen + 500):
        record_visit(str(i))
    assert len(VISIT_LOG) == VISIT_LOG.maxlen
