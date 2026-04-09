from __future__ import annotations

import httpx

from journal_discovery_llm_api.config import ApiSettings
from journal_discovery_llm_api.provider import (
    OpenAICompatibleProvider,
    ProviderRequestError,
    build_prompt_payload,
    normalize_provider_output,
)
from journal_discovery_llm_api.schemas import AbstractCandidate


def make_candidate(sourceid: str, title: str = "Journal Title") -> AbstractCandidate:
    return AbstractCandidate(
        sourceid=sourceid,
        title=title,
        categories="A" * 600,
        areas="B" * 600,
        subject_area="C" * 400,
        publisher="Publisher",
        country="Indonesia",
        lexical_score=12.5,
    )


def make_settings() -> ApiSettings:
    return ApiSettings(
        provider_kind="openai_compatible",
        provider_base_url="https://provider.example/v1",
        provider_api_key="secret",
        provider_model="mock-model",
        provider_timeout_seconds=30.0,
        batch_size=10,
        max_candidates=50,
        default_top_n=50,
        query_char_limit=3000,
        title_char_limit=32,
        category_char_limit=64,
        area_char_limit=48,
        subject_area_char_limit=24,
        lexical_score_limit=1_000_000.0,
        body_limit_bytes=250000,
        rate_limit_window_seconds=60,
        rate_limit_max_requests=30,
        result_cache_ttl_seconds=21600,
        result_cache_max_entries=256,
        allow_origins=(),
        allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
        enable_docs=False,
    )


def test_build_prompt_payload_truncates_long_fields() -> None:
    payload = build_prompt_payload(make_settings(), "x" * 5000, [make_candidate("c1", title="T" * 100)])
    candidate = payload["candidates"][0]

    assert len(payload["query_text"]) <= 3000
    assert len(candidate["title"]) <= 32
    assert len(candidate["categories"]) <= 64
    assert len(candidate["areas"]) <= 48
    assert len(candidate["subject_area"]) <= 24


def test_normalize_provider_output_zeroes_malformed_candidates() -> None:
    candidates = [make_candidate("c1"), make_candidate("c2")]
    normalized = normalize_provider_output(
        '{"results":[{"sourceid":"c1","llm_score":"82","rationale":"Strong topical fit","matched_fields":["title","invalid"],"confidence":"0.7"},{"sourceid":"c2","llm_score":"oops"}]}',
        candidates,
    )

    assert normalized[0].sourceid == "c1"
    assert normalized[0].llm_score == 82
    assert normalized[0].matched_fields == ["title"]
    assert normalized[1].sourceid == "c2"
    assert normalized[1].llm_score == 0
    assert normalized[1].rationale == ""


class ErroringClient:
    def post(self, *args, **kwargs):
        request = httpx.Request("POST", "https://provider.example/v1/chat/completions")
        response = httpx.Response(401, request=request, text='{"error":{"message":"Invalid API key"}}')
        raise httpx.HTTPStatusError("Unauthorized", request=request, response=response)


def test_openai_compatible_provider_exposes_upstream_status_details() -> None:
    provider = OpenAICompatibleProvider(make_settings(), client=ErroringClient())

    try:
        provider.rerank_batch("machine learning", [make_candidate("c1")])
    except ProviderRequestError as error:
        message = str(error)
    else:
        raise AssertionError("Expected ProviderRequestError to be raised")

    assert "401" in message
    assert "invalid api key" in message.lower()
