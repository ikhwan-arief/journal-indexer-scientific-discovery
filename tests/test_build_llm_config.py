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


def test_home_page_uses_longer_default_timeout_for_local_llm(monkeypatch) -> None:
    monkeypatch.setenv("LLM_API_BASE_URL", "http://127.0.0.1:8000")
    monkeypatch.delenv("LLM_TIMEOUT_MS", raising=False)
    monkeypatch.delenv("LLM_ABSTRACT_MATCH_ENABLED", raising=False)

    html = build.home_page_html(sample_summary())

    assert 'data-llm-abstract-enabled="true"' in html
    assert 'data-llm-timeout-ms="60000"' in html


def test_home_page_uses_render_aware_timeout_default(monkeypatch) -> None:
    monkeypatch.setenv("LLM_API_BASE_URL", "https://journal-discovery-llm-api.onrender.com")
    monkeypatch.delenv("LLM_TIMEOUT_MS", raising=False)
    monkeypatch.delenv("LLM_ABSTRACT_MATCH_ENABLED", raising=False)
    monkeypatch.delenv("LLM_CANDIDATE_LIMIT", raising=False)

    html = build.home_page_html(sample_summary())

    assert 'data-llm-abstract-enabled="true"' in html
    assert 'data-llm-timeout-ms="90000"' in html
    assert 'data-llm-candidate-limit="20"' in html


def test_home_page_omits_external_connect_src_without_llm(monkeypatch) -> None:
    monkeypatch.delenv("LLM_API_BASE_URL", raising=False)
    monkeypatch.delenv("LLM_TIMEOUT_MS", raising=False)
    monkeypatch.delenv("LLM_ABSTRACT_MATCH_ENABLED", raising=False)

    html = build.home_page_html(sample_summary())

    assert "connect-src" not in html
    assert 'data-llm-abstract-enabled="false"' in html


def test_home_page_keeps_remote_timeout_default_without_override(monkeypatch) -> None:
    monkeypatch.setenv("LLM_API_BASE_URL", "https://api.example.com")
    monkeypatch.delenv("LLM_TIMEOUT_MS", raising=False)
    monkeypatch.delenv("LLM_ABSTRACT_MATCH_ENABLED", raising=False)

    html = build.home_page_html(sample_summary())

    assert 'data-llm-timeout-ms="8000"' in html
