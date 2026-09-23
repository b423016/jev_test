from __future__ import annotations

import hashlib
import hmac


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hashes_match(claimed: str, data: bytes) -> bool:
    expected = sha256_hex(data)
    given = claimed.strip().lower()
    if len(given) != len(expected):
        return False
    return hmac.compare_digest(given, expected)
