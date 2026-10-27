from __future__ import annotations

import re
from urllib.parse import urlparse

MAX_TEXT_LENGTH = 10_000
OPENALEX_ID_RE = re.compile(r"^https://openalex\.org/([SWT])\d+$")
DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$", re.IGNORECASE)
ISSN_RE = re.compile(r"^\d{4}-?\d{3}[\dX]$", re.IGNORECASE)


def bounded_text(value: object, *, limit: int = MAX_TEXT_LENGTH) -> str:
    """Return plain, control-character-free text with a deterministic size limit."""
    text = str(value or "").replace("\x00", "")
    text = "".join(character for character in text if character in "\n\t" or ord(character) >= 32)
    return text.strip()[:limit]


def openalex_short_id(value: object, expected_prefix: str | None = None) -> str | None:
    text = bounded_text(value, limit=128)
    match = OPENALEX_ID_RE.fullmatch(text)
    if not match or (expected_prefix and match.group(1) != expected_prefix):
        return None
    return text.rsplit("/", 1)[-1]


def normalize_doi(value: object) -> str | None:
    text = bounded_text(value, limit=512).lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if text.startswith(prefix):
            text = text[len(prefix):]
            break
    return text if DOI_RE.fullmatch(text) else None


def normalize_issn(value: object) -> str | None:
    compact = bounded_text(value, limit=32).upper().replace("-", "")
    if not ISSN_RE.fullmatch(compact):
        return None
    digits = compact[:7]
    check = compact[7]
    total = sum(int(digit) * (8 - index) for index, digit in enumerate(digits))
    expected_value = (11 - (total % 11)) % 11
    expected = "X" if expected_value == 10 else str(expected_value)
    if check != expected:
        return None
    return f"{compact[:4]}-{compact[4:]}"


def safe_public_url(value: object, *, allowed_hosts: set[str] | None = None) -> str | None:
    text = bounded_text(value, limit=2048)
    if not text:
        return None
    parsed = urlparse(text)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        return None
    hostname = parsed.hostname.lower().rstrip(".")
    if allowed_hosts is not None and hostname not in allowed_hosts:
        return None
    return text


def safe_identifier(value: object, *, limit: int = 128) -> str | None:
    text = bounded_text(value, limit=limit)
    if not text or not re.fullmatch(r"[A-Za-z0-9._:-]+", text):
        return None
    if text in {"__proto__", "prototype", "constructor"}:
        return None
    return text
