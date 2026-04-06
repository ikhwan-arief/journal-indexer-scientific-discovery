from __future__ import annotations

from journal_discovery_llm_api.config import get_settings


def test_local_provider_defaults_to_longer_timeout(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER_BASE_URL", "http://127.0.0.1:11434/v1")
    monkeypatch.setenv("LLM_PROVIDER_API_KEY", "ollama")
    monkeypatch.setenv("LLM_PROVIDER_MODEL", "qwen2.5:1.5b")
    monkeypatch.delenv("LLM_PROVIDER_TIMEOUT_SECONDS", raising=False)
    get_settings.cache_clear()

    try:
        settings = get_settings()
        assert settings.provider_timeout_seconds == 120.0
    finally:
        get_settings.cache_clear()


def test_remote_provider_keeps_default_timeout(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER_BASE_URL", "https://api.example.com/v1")
    monkeypatch.setenv("LLM_PROVIDER_API_KEY", "secret")
    monkeypatch.setenv("LLM_PROVIDER_MODEL", "gpt-4.1-mini")
    monkeypatch.delenv("LLM_PROVIDER_TIMEOUT_SECONDS", raising=False)
    get_settings.cache_clear()

    try:
        settings = get_settings()
        assert settings.provider_timeout_seconds == 30.0
    finally:
        get_settings.cache_clear()
