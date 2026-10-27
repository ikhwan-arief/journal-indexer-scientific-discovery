from __future__ import annotations

import pytest

from journal_discovery.openalex_static.budget import DailyBudgetExceeded, DailyBudgetLedger
from journal_discovery.openalex_static.client import OpenAlexClient
from journal_discovery.openalex_static.database import OpenAlexDatabase


def test_daily_budget_is_persisted_and_stops_before_limit(tmp_path) -> None:
    database = OpenAlexDatabase(tmp_path / "openalex.sqlite3")
    database.initialize()
    ledger = DailyBudgetLedger(database, max_usd=0.0002)
    ledger.reserve(1)
    ledger.reserve(1)
    with pytest.raises(DailyBudgetExceeded):
        ledger.reserve(1)

    usage = ledger.usage()
    assert usage["credits_used"] == 2
    assert usage["request_count"] == 2
    assert usage["estimated_usd"] == 0.0002


def test_budget_reconciliation_uses_actual_credits(tmp_path) -> None:
    database = OpenAlexDatabase(tmp_path / "openalex.sqlite3")
    database.initialize()
    ledger = DailyBudgetLedger(database, max_usd=0.001)
    ledger.reserve(10)
    ledger.reconcile(10, 1)
    assert ledger.usage()["credits_used"] == 1


@pytest.mark.parametrize(
    ("path", "params", "expected"),
    [
        ("/sources/S123", {}, 0),
        ("/sources", {"filter": "issn:2049-3630"}, 1),
        ("/works", {"search": "machine learning"}, 10),
        ("/works", {"search.semantic": "machine learning"}, 10),
        ("/works", {"search": "machine learning", "rerank": "true"}, 20),
    ],
)
def test_credit_estimates_match_openalex_rate_card(path, params, expected) -> None:
    assert OpenAlexClient.estimate_credits(path, params) == expected
