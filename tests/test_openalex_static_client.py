from __future__ import annotations

import io
import json
from email.message import Message

import pytest

from journal_discovery.openalex_static.client import OpenAlexClient


class FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = json.dumps(payload).encode()
        self.headers = Message()
        self.headers["Content-Type"] = "application/json"
        self.headers["Content-Length"] = str(len(self.payload))
        self.handle = io.BytesIO(self.payload)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, size: int) -> bytes:
        return self.handle.read(size)


class FakeOpener:
    def __init__(self) -> None:
        self.url = ""

    def open(self, request, timeout):  # noqa: ANN001
        self.url = request.full_url
        return FakeResponse({"results": []})


def test_client_restricts_endpoints_and_injects_credentials_without_returning_them() -> None:
    client = OpenAlexClient(api_key="secret-value", mailto="private@example.org")
    opener = FakeOpener()
    client._opener = opener
    assert client.get_json("/sources", {"filter": "issn:2049-3630"}) == {"results": []}
    assert "api_key=secret-value" in opener.url
    assert "mailto=private%40example.org" in opener.url
    with pytest.raises(ValueError):
        client.get_json("/authors")
    with pytest.raises(ValueError):
        client.get_json("/works/../authors")
