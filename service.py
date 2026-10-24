import string
from collections import deque

ALPHABET = string.ascii_lowercase + string.ascii_uppercase + string.digits  # 62 characters


VISIT_LOG = deque(maxlen=1000)  # bounded default log; oldest visits drop off


def encode_base62(num):
    if num == 0:
        return ALPHABET[0]
    out = ""
    while num > 0:
        out = ALPHABET[num % 62] + out
        num //= 62
    return out


def record_visit(code, log=None):
    if log is None:
        log = VISIT_LOG
    log.append(code)
    return log


def shorten(storage, long_url):
    new_id = storage.next_id()
    code = encode_base62(new_id)
    storage.save(code, long_url)
    return code
