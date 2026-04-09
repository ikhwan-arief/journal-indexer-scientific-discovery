from __future__ import annotations

import json
from typing import Any

import httpx

from .config import ApiSettings
from .schemas import ALLOWED_MATCHED_FIELDS, AbstractCandidate, ProviderScoredCandidate


class ProviderRequestError(RuntimeError):
    """Raised when the upstream provider request fails."""


class ProviderTimeoutError(ProviderRequestError):
    """Raised when the upstream provider times out."""


def summarize_error_text(value: str | None, limit: int = 240) -> str:
    compact = " ".join(str(value or "").split())
    if not compact:
        return ""
    if len(compact) > limit:
        compact = compact[: max(0, limit - 1)].rstrip() + "…"
    return compact


def truncate_text(value: str | None, limit: int) -> str:
    compact = " ".join(str(value or "").split())
    if len(compact) <= limit:
        return compact
    return compact[: max(0, limit - 1)].rstrip() + "…"


def clamp_int(value: Any, minimum: int, maximum: int, default: int) -> int:
    try:
        numeric = int(float(value))
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, numeric))


def clamp_float(value: Any, minimum: float, maximum: float, default: float) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, numeric))


def compact_sentence(value: Any) -> str:
    compact = " ".join(str(value or "").split())
    if not compact:
        return ""
    if len(compact) > 220:
        compact = compact[:219].rstrip() + "…"
    if compact[-1] not in ".!?":
        compact += "."
    return compact


def normalize_matched_fields(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    matches = []
    for item in value:
        text = str(item or "").strip().lower()
        if text in ALLOWED_MATCHED_FIELDS and text not in matches:
            matches.append(text)
    return matches


def zero_scored_candidate(candidate: AbstractCandidate) -> ProviderScoredCandidate:
    return ProviderScoredCandidate(
        sourceid=candidate.sourceid,
        title=candidate.title,
        lexical_score=float(candidate.lexical_score),
        llm_score=0,
        rationale="",
        matched_fields=[],
        confidence=0.0,
    )


def normalize_provider_output(raw_content: str, candidates: list[AbstractCandidate]) -> list[ProviderScoredCandidate]:
    candidate_map = {candidate.sourceid: zero_scored_candidate(candidate) for candidate in candidates}

    try:
        payload = json.loads(raw_content)
    except json.JSONDecodeError:
        return [candidate_map[candidate.sourceid] for candidate in candidates]

    raw_items = payload.get("results")
    if not isinstance(raw_items, list):
        return [candidate_map[candidate.sourceid] for candidate in candidates]

    for raw_item in raw_items:
        if not isinstance(raw_item, dict):
            continue
        sourceid = str(raw_item.get("sourceid") or "").strip()
        if sourceid not in candidate_map:
            continue
        current = candidate_map[sourceid]
        candidate_map[sourceid] = ProviderScoredCandidate(
            sourceid=current.sourceid,
            title=current.title,
            lexical_score=current.lexical_score,
            llm_score=clamp_int(raw_item.get("llm_score"), 0, 100, 0),
            rationale=compact_sentence(raw_item.get("rationale")),
            matched_fields=normalize_matched_fields(raw_item.get("matched_fields")),
            confidence=clamp_float(raw_item.get("confidence"), 0.0, 1.0, 0.0),
        )

    return [candidate_map[candidate.sourceid] for candidate in candidates]


def build_prompt_payload(settings: ApiSettings, query_text: str, candidates: list[AbstractCandidate]) -> dict[str, Any]:
    return {
        "task": "Score journal submission fit for an abstract using only topical and scope evidence.",
        "query_text": truncate_text(query_text, settings.query_char_limit),
        "instructions": [
            "Use only title, categories, areas, and subject_area as evidence.",
            "Ignore prestige, rankings, indexing, accreditation, APC, and publisher reputation.",
            "Use lexical_score only as a tie-break when two journals appear equally aligned.",
            "Return concise one-sentence rationales.",
        ],
        "candidates": [
            {
                "sourceid": candidate.sourceid,
                "title": truncate_text(candidate.title, settings.title_char_limit),
                "categories": truncate_text(candidate.categories, settings.category_char_limit),
                "areas": truncate_text(candidate.areas, settings.area_char_limit),
                "subject_area": truncate_text(candidate.subject_area, settings.subject_area_char_limit),
                "lexical_score": round(float(candidate.lexical_score), 4),
            }
            for candidate in candidates
        ],
        "response_schema": {
            "results": [
                {
                    "sourceid": "candidate sourceid",
                    "llm_score": "integer 0-100",
                    "rationale": "one short sentence",
                    "matched_fields": list(ALLOWED_MATCHED_FIELDS),
                    "confidence": "float 0.0-1.0",
                }
            ]
        },
    }


def extract_message_content(payload: dict[str, Any]) -> str:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    message = choices[0].get("message")
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        fragments = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                fragments.append(str(item.get("text") or ""))
        return "".join(fragments)
    return ""


class OpenAICompatibleProvider:
    def __init__(self, settings: ApiSettings, client: httpx.Client | None = None) -> None:
        self.settings = settings
        self.client = client or httpx.Client(timeout=settings.provider_timeout_seconds)

    @property
    def model_name(self) -> str:
        return self.settings.provider_model

    def rerank_batch(self, query_text: str, candidates: list[AbstractCandidate]) -> list[ProviderScoredCandidate]:
        prompt_payload = build_prompt_payload(self.settings, query_text, candidates)
        headers = {
            "Authorization": f"Bearer {self.settings.provider_api_key}",
            "Content-Type": "application/json",
        }
        request_payload = {
            "model": self.settings.provider_model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You score manuscript abstract fit to journal scope. "
                        "Return JSON only with a top-level 'results' array keyed by sourceid."
                    ),
                },
                {"role": "user", "content": json.dumps(prompt_payload, ensure_ascii=False)},
            ],
        }

        endpoint = f"{self.settings.provider_base_url}/chat/completions"
        try:
            response = self.client.post(endpoint, headers=headers, json=request_payload)
            response.raise_for_status()
        except httpx.TimeoutException as error:
            raise ProviderTimeoutError("Upstream LLM provider timed out.") from error
        except httpx.HTTPStatusError as error:
            status_code = error.response.status_code if error.response is not None else None
            response_text = summarize_error_text(error.response.text if error.response is not None else "")
            detail = f"Upstream LLM provider returned HTTP {status_code or 'error'}."
            if response_text:
                detail = f"{detail} {response_text}"
            raise ProviderRequestError(detail) from error
        except httpx.HTTPError as error:
            raise ProviderRequestError("Upstream LLM provider request failed.") from error

        content = extract_message_content(response.json())
        return normalize_provider_output(content, candidates)


def build_provider(settings: ApiSettings) -> OpenAICompatibleProvider:
    if settings.provider_kind != "openai_compatible":
        raise RuntimeError(f"Unsupported LLM provider kind: {settings.provider_kind}")
    return OpenAICompatibleProvider(settings)
