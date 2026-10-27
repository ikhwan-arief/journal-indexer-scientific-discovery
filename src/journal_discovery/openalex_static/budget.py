from __future__ import annotations

import math
from datetime import UTC, datetime

from .database import OpenAlexDatabase

CREDIT_USD = 0.0001
FREE_DAILY_BUDGET_USD = 1.0


class DailyBudgetExceeded(RuntimeError):
    pass


class DailyBudgetLedger:
    """Atomic UTC-day credit ledger persisted in the private SQLite database."""

    def __init__(self, database: OpenAlexDatabase, *, max_usd: float = FREE_DAILY_BUDGET_USD) -> None:
        if not 0 < max_usd <= FREE_DAILY_BUDGET_USD:
            raise ValueError("Daily OpenAlex budget must be greater than zero and at most US$1.")
        self.database = database
        self.max_credits = int(math.floor(max_usd / CREDIT_USD + 1e-9))

    @staticmethod
    def _date_and_time() -> tuple[str, str]:
        now = datetime.now(UTC)
        return now.date().isoformat(), now.isoformat(timespec="seconds")

    def reserve(self, estimated_credits: int) -> None:
        credits = max(0, int(estimated_credits))
        usage_date, updated_at = self._date_and_time()
        with self.database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT credits_used FROM api_usage_daily WHERE usage_date_utc = ?", (usage_date,)
            ).fetchone()
            used = int(row["credits_used"]) if row else 0
            if used + credits > self.max_credits:
                connection.rollback()
                raise DailyBudgetExceeded("OpenAlex daily US$1 budget guard reached.")
            connection.execute(
                """INSERT INTO api_usage_daily(usage_date_utc, credits_used, request_count, updated_at)
                   VALUES (?, ?, 1, ?)
                   ON CONFLICT(usage_date_utc) DO UPDATE SET
                       credits_used = credits_used + excluded.credits_used,
                       request_count = request_count + 1,
                       updated_at = excluded.updated_at""",
                (usage_date, credits, updated_at),
            )
            connection.commit()

    def reconcile(self, estimated_credits: int, actual_credits: int) -> None:
        difference = int(actual_credits) - max(0, int(estimated_credits))
        if difference == 0:
            return
        usage_date, updated_at = self._date_and_time()
        with self.database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT credits_used FROM api_usage_daily WHERE usage_date_utc = ?", (usage_date,)
            ).fetchone()
            used = int(row["credits_used"]) if row else 0
            next_used = max(0, used + difference)
            if next_used > self.max_credits:
                connection.rollback()
                raise DailyBudgetExceeded("OpenAlex actual request cost exceeded the daily US$1 budget guard.")
            connection.execute(
                "UPDATE api_usage_daily SET credits_used = ?, updated_at = ? WHERE usage_date_utc = ?",
                (next_used, updated_at, usage_date),
            )
            connection.commit()

    def release(self, estimated_credits: int) -> None:
        self.reconcile(estimated_credits, 0)

    def usage(self) -> dict[str, int | float | str]:
        usage_date, _ = self._date_and_time()
        with self.database.connect(readonly=True) as connection:
            row = connection.execute(
                "SELECT credits_used, request_count FROM api_usage_daily WHERE usage_date_utc = ?", (usage_date,)
            ).fetchone()
        credits = int(row["credits_used"]) if row else 0
        requests = int(row["request_count"]) if row else 0
        return {
            "usage_date_utc": usage_date,
            "credits_used": credits,
            "request_count": requests,
            "estimated_usd": round(credits * CREDIT_USD, 4),
            "max_credits": self.max_credits,
        }
