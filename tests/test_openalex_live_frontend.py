from __future__ import annotations

from pathlib import Path

from journal_discovery import build


ROOT = Path(__file__).resolve().parents[1]
APP_JS = ROOT / "src/journal_discovery/assets/app.js"


def test_pages_enable_only_anonymous_openalex_live_access(monkeypatch) -> None:
    monkeypatch.delenv("LLM_API_BASE_URL", raising=False)
    monkeypatch.delenv("LLM_ABSTRACT_MATCH_ENABLED", raising=False)
    csp = build.page_csp()
    assert "connect-src 'self' https://api.openalex.org" in csp
    assert "openrouter.ai" not in csp
    assert "onrender.com" not in csp


def test_live_client_has_privacy_and_resource_controls() -> None:
    source = APP_JS.read_text(encoding="utf-8")
    assert 'credentials: "omit"' in source
    assert 'cache: "no-store"' in source
    assert 'referrerPolicy: "no-referrer"' in source
    assert "OPENALEX_SEMANTIC_MAX_CHARS = 2000" in source
    assert "OPENALEX_SEMANTIC_LIMIT = 50" in source
    assert "OPENALEX_MIN_INTERVAL_MS = 1000" in source
    assert 'url.searchParams.set("search.semantic", effectiveQuery)' in source
    assert "api_key" not in source.lower()
