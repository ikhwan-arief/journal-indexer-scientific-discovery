"""Refresh the private OpenAlex SQLite cache used to build public static artifacts."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from journal_discovery.openalex_static.client import OpenAlexClient, OpenAlexError
from journal_discovery.openalex_static.budget import DailyBudgetExceeded, DailyBudgetLedger
from journal_discovery.openalex_static.database import OpenAlexDatabase
from journal_discovery.openalex_static.pipeline import OpenAlexIngestionPipeline, load_journal_seeds


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refresh build-time OpenAlex data without exposing credentials.")
    parser.add_argument("--database", type=Path, default=ROOT / "build" / "private" / "openalex.sqlite3")
    parser.add_argument("--max-journals", type=int, default=100)
    parser.add_argument("--works-per-journal", type=int, default=20)
    parser.add_argument("--operation-budget", type=int, default=5000)
    parser.add_argument("--daily-budget-usd", type=float, default=1.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    api_key = (os.getenv("OPENALEX_API_KEY") or "").strip()
    mailto = (os.getenv("OPENALEX_MAILTO") or "").strip()
    if not api_key or not mailto:
        raise SystemExit("OpenAlex credentials are not configured. No refresh was attempted.")
    if not 1 <= args.max_journals <= 100_000 or not 5 <= args.works_per_journal <= 100:
        raise SystemExit("OpenAlex refresh limits are outside the allowed range.")

    database = OpenAlexDatabase(args.database.resolve())
    database.initialize()
    try:
        daily_budget = DailyBudgetLedger(database, max_usd=args.daily_budget_usd)
    except ValueError as error:
        raise SystemExit(str(error)) from None
    client = OpenAlexClient(
        api_key=api_key,
        mailto=mailto,
        operation_budget=max(1, args.operation_budget),
        daily_budget=daily_budget,
    )
    pipeline = OpenAlexIngestionPipeline(database, client)
    seeds = load_journal_seeds(ROOT / "data/raw/scimagojr.csv", ROOT / "data/raw/sinta.csv")
    try:
        result = pipeline.refresh(seeds, max_journals=args.max_journals, works_per_journal=args.works_per_journal)
    except (OpenAlexError, DailyBudgetExceeded) as error:
        raise SystemExit(str(error)) from None
    except Exception as error:
        raise SystemExit(f"OpenAlex refresh failed safely ({type(error).__name__}).") from None
    print(
        "OpenAlex refresh completed: "
        f"matched_journals={result['matched_journals']} "
        f"works_saved={result['works_saved']} operations={result['operations']}"
    )
    usage = daily_budget.usage()
    print(
        "OpenAlex UTC daily budget: "
        f"credits_used={usage['credits_used']}/{usage['max_credits']} "
        f"estimated_usd={usage['estimated_usd']:.4f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
