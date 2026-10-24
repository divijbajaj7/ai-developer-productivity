import string

ALPHABET = string.ascii_lowercase + string.ascii_uppercase + string.digits  # 62 characters


def encode_base62(num):
    out = ""
    while num > 0:
        out = ALPHABET[num % 62] + out
        num //= 62
    return out  # BUG: encode_base62(0) returns "" instead of a valid one-character code


def record_visit(code, log=[]):  # BUG: mutable default argument is shared across all calls
    log.append(code)
    return log


def shorten(storage, long_url):
    new_id = storage.next_id()
    code = encode_base62(new_id)
    storage.save(code, long_url)
    return code
