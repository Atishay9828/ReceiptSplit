from __future__ import annotations

import hashlib
import re

TAG_RE = re.compile(r"<[^>]*>")


def fingerprint(value: str | None, *, length: int = 16) -> str | None:
    if not value:
        return None
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:length]


def sanitize_text(value: str | None, *, max_length: int = 500) -> str | None:
    if value is None:
        return None
    cleaned = TAG_RE.sub("", value.replace("\x00", ""))
    cleaned = " ".join(cleaned.split())
    if not cleaned:
        return None
    return cleaned[:max_length]
