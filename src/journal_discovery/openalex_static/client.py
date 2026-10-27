from __future__ import annotations

import json
import random
import time
from dataclasses import dataclass, field
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener

from .budget import DailyBudgetLedger

OPENALEX_HOST = "api.openalex.org"
OPENALEX_ORIGIN = f"https://{OPENALEX_HOST}"


class OpenAlexError(RuntimeError):
    """Safe OpenAlex error that never includes credentials or raw request URLs."""


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


@dataclass(slots=True)
class OpenAlexClient:
    api_key: str
    mailto: str
    timeout_seconds: float = 30.0
    max_attempts: int = 4
    max_response_bytes: int = 8_000_000
    operation_budget: int = 20_000
    daily_budget: DailyBudgetLedger | None = None
    operation_count: int = field(init=False, default=0)
    _opener: Any = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if not self.api_key.strip() or not self.mailto.strip():
            raise ValueError("OpenAlex credentials are not configured.")
        self._opener = build_opener(_NoRedirect(), HTTPSHandler())

    def get_json(self, path: str, params: dict[str, object] | None = None) -> dict[str, Any]:
        if not path.startswith("/") or ".." in path or "?" in path or "#" in path:
            raise ValueError("Invalid OpenAlex endpoint path.")
        if not path.startswith(("/sources", "/works", "/topics")):
            raise ValueError("OpenAlex endpoint is not allowlisted.")
        query: dict[str, object] = dict(params or {})
        estimated_credits = self.estimate_credits(path, query)
        query["api_key"] = self.api_key
        query["mailto"] = self.mailto
        url = f"{OPENALEX_ORIGIN}{path}?{urlencode(query, doseq=True)}"

        for attempt in range(self.max_attempts):
            if self.operation_count >= self.operation_budget:
                raise OpenAlexError("OpenAlex operation budget exhausted.")
            if self.daily_budget:
                self.daily_budget.reserve(estimated_credits)
            self.operation_count += 1
            request = Request(
                url,
                headers={"Accept": "application/json", "User-Agent": "JournalDiscoveryStatic/2.0"},
                method="GET",
            )
            try:
                with self._opener.open(request, timeout=self.timeout_seconds) as response:
                    content_type = response.headers.get_content_type()
                    if content_type != "application/json":
                        raise OpenAlexError("OpenAlex returned an unexpected content type.")
                    declared_length = int(response.headers.get("Content-Length") or 0)
                    if declared_length > self.max_response_bytes:
                        raise OpenAlexError("OpenAlex response exceeded the configured size limit.")
                    raw = response.read(self.max_response_bytes + 1)
                    if len(raw) > self.max_response_bytes:
                        raise OpenAlexError("OpenAlex response exceeded the configured size limit.")
                    payload = json.loads(raw)
                    if not isinstance(payload, dict):
                        raise OpenAlexError("OpenAlex returned an invalid JSON object.")
                    if self.daily_budget:
                        self.daily_budget.reconcile(estimated_credits, self._actual_credits(response.headers, payload, estimated_credits))
                    return payload
            except HTTPError as error:
                if self.daily_budget and error.code == 429:
                    self.daily_budget.release(estimated_credits)
                retryable = error.code == 429 or 500 <= error.code < 600
                if not retryable or attempt + 1 >= self.max_attempts:
                    raise OpenAlexError(f"OpenAlex request failed with HTTP {error.code}.") from None
                delay = self._retry_delay(error.headers.get("Retry-After"), attempt)
            except (URLError, TimeoutError, json.JSONDecodeError, ValueError):
                if attempt + 1 >= self.max_attempts:
                    raise OpenAlexError("OpenAlex request failed after bounded retries.") from None
                delay = self._retry_delay(None, attempt)
            time.sleep(delay)
        raise OpenAlexError("OpenAlex request failed.")

    @staticmethod
    def estimate_credits(path: str, params: dict[str, object]) -> int:
        if path.startswith("/content"):
            return 100
        has_search = any(str(key).startswith("search") for key in params)
        credits = 10 if has_search else 1
        if str(params.get("rerank") or "").lower() in {"1", "true", "yes"}:
            credits += 10
        if not params and path.count("/") >= 2:
            return 0
        return credits

    @staticmethod
    def _actual_credits(headers: Any, payload: dict[str, Any], fallback: int) -> int:
        raw_header = headers.get("X-RateLimit-Credits-Used")
        if raw_header is not None:
            try:
                return max(0, int(float(raw_header)))
            except (TypeError, ValueError):
                pass
        meta = payload.get("meta")
        if isinstance(meta, dict):
            raw_cost = meta.get("cost_usd", meta.get("cost"))
            if raw_cost is not None:
                try:
                    return max(0, int(round(float(raw_cost) / 0.0001)))
                except (TypeError, ValueError):
                    pass
        return fallback

    @staticmethod
    def _retry_delay(retry_after: str | None, attempt: int) -> float:
        if retry_after:
            try:
                return min(60.0, max(0.0, float(retry_after)))
            except ValueError:
                try:
                    return min(60.0, max(0.0, parsedate_to_datetime(retry_after).timestamp() - time.time()))
                except (TypeError, ValueError, OverflowError):
                    pass
        return min(30.0, (2**attempt) + random.uniform(0.0, 0.5))
