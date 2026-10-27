from __future__ import annotations

import pytest

from journal_discovery.openalex_static.security import (
    bounded_text,
    normalize_doi,
    normalize_issn,
    openalex_short_id,
    safe_identifier,
    safe_public_url,
)


@pytest.mark.parametrize("value", ["javascript:alert(1)", "data:text/html,x", "file:///etc/passwd", "https://user:pass@example.org"])
def test_safe_public_url_rejects_unsafe_urls(value: str) -> None:
    assert safe_public_url(value) is None


def test_safe_public_url_allows_only_explicit_https_host() -> None:
    assert safe_public_url("https://api.openalex.org/works", allowed_hosts={"api.openalex.org"})
    assert safe_public_url("https://example.org/works", allowed_hosts={"api.openalex.org"}) is None


def test_identifiers_and_external_text_are_bounded() -> None:
    assert openalex_short_id("https://openalex.org/S123", "S") == "S123"
    assert openalex_short_id("https://evil.example/S123", "S") is None
    assert safe_identifier("__proto__") is None
    assert safe_identifier("../../etc/passwd") is None
    assert bounded_text("a\x00b", limit=2) == "ab"


def test_normalizers_validate_checksums_and_shapes() -> None:
    assert normalize_issn("2049-3630") == "2049-3630"
    assert normalize_issn("2049-3631") is None
    assert normalize_doi("https://doi.org/10.1234/Example") == "10.1234/example"
    assert normalize_doi("not-a-doi") is None
