from __future__ import annotations

from journal_discovery import build


def sample_summary() -> build.SiteSummary:
    return build.SiteSummary(
        total_journals=1,
        total_scopus=1,
        total_wos=1,
        total_doaj=0,
        total_with_quartile=1,
        total_missing_websites=0,
        generated_at="2026-04-06 00:00 UTC",
    )


def test_home_page_includes_connect_src_and_runtime_config(monkeypatch) -> None:
    monkeypatch.setenv("LLM_API_BASE_URL", "https://api.example.com")
    monkeypatch.setenv("LLM_TIMEOUT_MS", "9000")
    monkeypatch.setenv("LLM_ABSTRACT_MATCH_ENABLED", "true")

    html = build.home_page_html(sample_summary())

    assert "connect-src" in html
    assert "https://api.example.com" in html
    assert 'data-llm-api-base-url="https://api.example.com"' in html
    assert 'data-llm-abstract-enabled="true"' in html
    assert 'data-llm-timeout-ms="9000"' in html


def test_home_page_omits_external_connect_src_without_llm(monkeypatch) -> None:
    monkeypatch.delenv("LLM_API_BASE_URL", raising=False)
    monkeypatch.delenv("LLM_TIMEOUT_MS", raising=False)
    monkeypatch.delenv("LLM_ABSTRACT_MATCH_ENABLED", raising=False)

    html = build.home_page_html(sample_summary())

    assert "connect-src" not in html
    assert 'data-llm-abstract-enabled="false"' in html
