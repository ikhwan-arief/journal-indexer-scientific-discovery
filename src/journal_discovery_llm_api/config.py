from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from ipaddress import ip_address
from urllib.parse import urlparse


DEFAULT_ALLOW_ORIGIN_REGEX = r"(^https://[A-Za-z0-9-]+\.github\.io$)|(^https?://(localhost|127\.0\.0\.1)(:\d+)?$)"


def env_bool(name: str, default: bool) -> bool:
    value = (os.getenv(name) or "").strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    return default


def env_int(name: str, default: int) -> int:
    value = (os.getenv(name) or "").strip()
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def env_float(name: str, default: float) -> float:
    value = (os.getenv(name) or "").strip()
    if not value:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def parse_origins(raw_value: str | None) -> tuple[str, ...]:
    if not raw_value:
        return ()
    values = []
    for item in raw_value.split(","):
        cleaned = item.strip().rstrip("/")
        if cleaned:
            values.append(cleaned)
    return tuple(dict.fromkeys(values))


def is_local_service_url(raw_value: str | None) -> bool:
    if not raw_value:
        return False
    parsed = urlparse(raw_value)
    hostname = (parsed.hostname or "").strip().lower()
    if not hostname:
        return False
    if hostname == "localhost":
        return True
    try:
        return ip_address(hostname).is_loopback
    except ValueError:
        return False


def is_openrouter_service_url(raw_value: str | None) -> bool:
    if not raw_value:
        return False
    parsed = urlparse(raw_value)
    hostname = (parsed.hostname or "").strip().lower()
    return hostname in {"openrouter.ai", "www.openrouter.ai"}


@dataclass(frozen=True, slots=True)
class ApiSettings:
    provider_kind: str
    provider_base_url: str
    provider_api_key: str
    provider_model: str
    provider_timeout_seconds: float
    batch_size: int
    max_candidates: int
    default_top_n: int
    query_char_limit: int
    title_char_limit: int
    category_char_limit: int
    area_char_limit: int
    subject_area_char_limit: int
    lexical_score_limit: float
    body_limit_bytes: int
    rate_limit_window_seconds: int
    rate_limit_max_requests: int
    result_cache_ttl_seconds: int
    result_cache_max_entries: int
    allow_origins: tuple[str, ...]
    allow_origin_regex: str
    enable_docs: bool

    @property
    def provider_configured(self) -> bool:
        return bool(self.provider_base_url and self.provider_model and self.provider_api_key)


@lru_cache(maxsize=1)
def get_settings() -> ApiSettings:
    provider_base_url = (os.getenv("LLM_PROVIDER_BASE_URL") or "").strip().rstrip("/")
    default_provider_timeout = 120.0 if is_local_service_url(provider_base_url) else 60.0 if is_openrouter_service_url(provider_base_url) else 30.0
    return ApiSettings(
        provider_kind=(os.getenv("LLM_PROVIDER_KIND") or "openai_compatible").strip().lower(),
        provider_base_url=provider_base_url,
        provider_api_key=(os.getenv("LLM_PROVIDER_API_KEY") or "").strip(),
        provider_model=(os.getenv("LLM_PROVIDER_MODEL") or "").strip(),
        provider_timeout_seconds=max(1.0, env_float("LLM_PROVIDER_TIMEOUT_SECONDS", default_provider_timeout)),
        batch_size=max(1, min(10, env_int("LLM_BATCH_SIZE", 10))),
        max_candidates=max(1, min(50, env_int("LLM_MAX_CANDIDATES", 50))),
        default_top_n=max(1, min(50, env_int("LLM_DEFAULT_TOP_N", 50))),
        query_char_limit=max(200, env_int("LLM_QUERY_CHAR_LIMIT", 3000)),
        title_char_limit=max(80, env_int("LLM_TITLE_CHAR_LIMIT", 240)),
        category_char_limit=max(120, env_int("LLM_CATEGORY_CHAR_LIMIT", 480)),
        area_char_limit=max(120, env_int("LLM_AREA_CHAR_LIMIT", 420)),
        subject_area_char_limit=max(80, env_int("LLM_SUBJECT_AREA_CHAR_LIMIT", 240)),
        lexical_score_limit=max(10.0, env_float("LLM_LEXICAL_SCORE_LIMIT", 1000000.0)),
        body_limit_bytes=max(4096, env_int("LLM_BODY_LIMIT_BYTES", 250000)),
        rate_limit_window_seconds=max(1, env_int("LLM_RATE_LIMIT_WINDOW_SECONDS", 60)),
        rate_limit_max_requests=max(1, env_int("LLM_RATE_LIMIT_MAX_REQUESTS", 30)),
        result_cache_ttl_seconds=max(0, env_int("LLM_RESULT_CACHE_TTL_SECONDS", 21600)),
        result_cache_max_entries=max(0, env_int("LLM_RESULT_CACHE_MAX_ENTRIES", 256)),
        allow_origins=parse_origins(os.getenv("LLM_CORS_ORIGINS")),
        allow_origin_regex=(os.getenv("LLM_CORS_ALLOW_ORIGIN_REGEX") or DEFAULT_ALLOW_ORIGIN_REGEX).strip(),
        enable_docs=env_bool("LLM_API_ENABLE_DOCS", False),
    )
