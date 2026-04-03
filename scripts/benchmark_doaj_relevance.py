"""Dikembangkan oleh Ikhwan Arief (ikhwan[at]unand.ac.id)
Lisensi aplikasi: Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)
"""

from __future__ import annotations

import argparse
import contextlib
import json
import math
import re
import socketserver
import sys
import threading
from functools import partial
from html import unescape
from http.server import SimpleHTTPRequestHandler
from pathlib import Path
from typing import Any
from urllib.parse import quote, quote_plus
from urllib.request import Request, urlopen

try:
    from playwright.sync_api import sync_playwright
except ImportError as error:
    raise SystemExit(
        "Playwright is not installed in the current interpreter. Run with the repo virtualenv, for example:\n"
        "  ./.venv/bin/python scripts/benchmark_doaj_relevance.py\n"
    ) from error


REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = REPO_ROOT / "docs"
MANIFEST_PATH = DOCS_DIR / "data" / "search-manifest.json"
DEFAULT_CASES_PER_PROFILE = 1
DEFAULT_PAGE_SIZE = 20
DEFAULT_MAX_PAGES = 2
DEFAULT_MAX_RANK = 10
DEFAULT_MIN_ABSTRACT_CHARS = 500
DOAJ_API_BASE = "https://doaj.org/api/v4/search/articles/"
DOAJ_USER_AGENT = "journal-discovery-benchmark/1.0"

DOMAIN_PROFILES = [
    {
        "id": "ai_ml",
        "label": "AI and Machine Learning",
        "queries": ["machine learning", "artificial intelligence"],
        "article_primary": [
            "machine learning",
            "artificial intelligence",
            "deep learning",
            "neural network",
            "feature selection",
            "predictive model",
        ],
        "article_secondary": [
            "classification",
            "prediction",
            "dataset",
            "algorithm",
            "model performance",
        ],
        "journal_primary": [
            "machine learning",
            "artificial intelligence",
            "computer science",
            "data science",
            "informatics",
            "intelligent systems",
        ],
        "journal_secondary": [
            "information systems",
            "knowledge systems",
            "autonomous",
            "analytics",
            "computing",
        ],
    },
    {
        "id": "operations_supply_chain",
        "label": "Operations and Supply Chain",
        "queries": ["supply chain", "operations management"],
        "article_primary": [
            "supply chain",
            "logistics",
            "inventory",
            "operations management",
            "production planning",
        ],
        "article_secondary": [
            "manufacturing",
            "procurement",
            "distribution",
            "supplier",
            "operational",
        ],
        "journal_primary": [
            "supply chain",
            "operations",
            "logistics",
            "production",
            "industrial engineering",
            "manufacturing",
        ],
        "journal_secondary": [
            "innovation",
            "decision",
            "engineering management",
            "inventory",
            "quality",
        ],
    },
    {
        "id": "public_health",
        "label": "Public and Community Health",
        "queries": ["public health", "community health"],
        "article_primary": [
            "public health",
            "community health",
            "health equity",
            "health care",
            "health promotion",
        ],
        "article_secondary": [
            "public aspects of medicine",
            "family health",
            "community resilience",
            "health services",
            "wellbeing",
        ],
        "journal_primary": [
            "public health",
            "community health",
            "health care",
            "health policy",
            "medicine",
            "epidemiology",
        ],
        "journal_secondary": [
            "social work",
            "nursing",
            "health services",
            "equity in health",
            "care and support",
        ],
    },
    {
        "id": "environment_sustainability",
        "label": "Environment and Sustainability",
        "queries": ["environmental sustainability", "sustainability"],
        "article_primary": [
            "environmental sustainability",
            "sustainability",
            "green development",
            "ecological",
            "climate",
        ],
        "article_secondary": [
            "environmental",
            "carbon",
            "pollution",
            "conservation",
            "renewable",
        ],
        "journal_primary": [
            "environmental",
            "sustainability",
            "ecology",
            "climate",
            "conservation",
            "green",
        ],
        "journal_secondary": [
            "hydrobiology",
            "environmental economics",
            "energy",
            "water",
            "earth sciences",
        ],
    },
    {
        "id": "agriculture_food",
        "label": "Agriculture and Food Systems",
        "queries": ["agriculture innovation", "plant science"],
        "article_primary": [
            "agriculture",
            "plant science",
            "crop",
            "agronomy",
            "food system",
        ],
        "article_secondary": [
            "farming",
            "soil",
            "rice",
            "seed",
            "horticulture",
        ],
        "journal_primary": [
            "agriculture",
            "agronomy",
            "crop science",
            "plant science",
            "food science",
            "horticulture",
        ],
        "journal_secondary": [
            "soil",
            "fisheries",
            "animal science",
            "forestry",
            "rural",
        ],
    },
    {
        "id": "finance_management",
        "label": "Finance and Financial Management",
        "queries": ["financial management", "banking finance"],
        "article_primary": [
            "financial management",
            "finance",
            "working capital",
            "accounting",
            "budgeting",
        ],
        "article_secondary": [
            "financing",
            "banking",
            "financial reporting",
            "capital budgeting",
            "enterprise performance",
        ],
        "journal_primary": [
            "financial management",
            "finance",
            "accounting",
            "banking",
            "economics",
            "budgeting",
        ],
        "journal_secondary": [
            "business",
            "management",
            "policy",
            "property and construction",
            "risk",
        ],
    },
]


class QuietRequestHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        return

    def send_head(self):
        requested_path = Path(self.translate_path(self.path))
        if requested_path.exists():
            return super().send_head()

        fallback = Path(self.directory or DOCS_DIR) / "404.html"
        if fallback.exists():
            handle = fallback.open("rb")
            self.send_response(404)
            self.send_header("Content-type", self.guess_type(str(fallback)))
            self.send_header("Content-Length", str(fallback.stat().st_size))
            self.end_headers()
            return handle

        return super().send_head()


class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True


@contextlib.contextmanager
def static_server(root: Path):
    handler = partial(QuietRequestHandler, directory=str(root))
    with ReusableTCPServer(("127.0.0.1", 0), handler) as httpd:
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        try:
            yield f"http://127.0.0.1:{httpd.server_address[1]}"
        finally:
            httpd.shutdown()
            thread.join(timeout=5)


def normalize_text(value: str) -> str:
    lowered = unescape((value or "").strip().lower())
    lowered = re.sub(r"<[^>]+>", " ", lowered)
    lowered = re.sub(r"[^a-z0-9]+", " ", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def compact_text(value: str) -> str:
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", value or ""))).strip()


def load_dataset_records() -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    records: list[dict[str, Any]] = []
    lookup: dict[str, dict[str, Any]] = {}
    for path in sorted((DOCS_DIR / "data" / "search-chunks").glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        for record in payload.get("records", []):
            entry = dict(record)
            entry["_normalized_title"] = normalize_text(str(record.get("title", "")))
            entry["_normalized_text"] = normalize_text(
                " ".join(
                    [
                        str(record.get("title", "")),
                        str(record.get("categories", "")),
                        str(record.get("areas", "")),
                    ]
                )
            )
            records.append(entry)
            lookup.setdefault(str(entry["_normalized_title"]), entry)
    return records, lookup


def fetch_doaj_page(query: str, page: int, page_size: int) -> dict[str, Any]:
    encoded_query = quote(query, safe="")
    url = f"{DOAJ_API_BASE}{encoded_query}?page={page}&pageSize={page_size}"
    request = Request(url, headers={"Accept": "application/json", "User-Agent": DOAJ_USER_AGENT})
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def phrase_hits(text: str, phrases: list[str]) -> set[str]:
    return {phrase for phrase in phrases if phrase in text}


def article_match_score(article: dict[str, Any], profile: dict[str, Any]) -> tuple[int, set[str], set[str]]:
    combined_text = normalize_text(
        " ".join(
            [
                str(article.get("title", "")),
                str(article.get("abstract", "")),
                " ".join(article.get("keywords", [])),
                " ".join(article.get("subjects", [])),
            ]
        )
    )
    primary = phrase_hits(combined_text, profile["article_primary"])
    secondary = phrase_hits(combined_text, profile["article_secondary"])
    query_hits = phrase_hits(combined_text, [normalize_text(query) for query in profile["queries"]])

    if not query_hits and not primary:
        return 0, primary, secondary

    score = (4 * len(query_hits)) + (3 * len(primary)) + len(secondary)
    return score, primary | query_hits, secondary


def grade_domain_relevance(record: dict[str, Any] | None, profile: dict[str, Any]) -> tuple[int, set[str], set[str]]:
    if not record:
        return 0, set(), set()

    record_text = str(record.get("_normalized_text", ""))
    primary_hits = phrase_hits(record_text, profile["journal_primary"])
    secondary_hits = phrase_hits(record_text, profile["journal_secondary"])

    if len(primary_hits) >= 2 or (len(primary_hits) >= 1 and len(secondary_hits) >= 1):
        return 2, primary_hits, secondary_hits
    if primary_hits or len(secondary_hits) >= 2:
        return 1, primary_hits, secondary_hits
    return 0, primary_hits, secondary_hits


def grade_record_relevance(record: dict[str, Any] | None, profile: dict[str, Any], source_title: str) -> tuple[int, set[str], set[str]]:
    if record and str(record.get("_normalized_title", "")) == normalize_text(source_title):
        return 3, {"exact-source-journal"}, set()
    return grade_domain_relevance(record, profile)


def build_cases(
    dataset_lookup: dict[str, dict[str, Any]],
    cases_per_profile: int,
    page_size: int,
    max_pages: int,
    min_abstract_chars: int,
) -> tuple[list[dict[str, Any]], list[str]]:
    cases: list[dict[str, Any]] = []
    skipped_profiles: list[str] = []

    for profile in DOMAIN_PROFILES:
        candidates: list[dict[str, Any]] = []
        seen_article_titles: set[str] = set()

        for query in profile["queries"]:
            for page in range(1, max_pages + 1):
                payload = fetch_doaj_page(query=query, page=page, page_size=page_size)
                for result in payload.get("results", []):
                    bibjson = result.get("bibjson", {})
                    journal = bibjson.get("journal", {})
                    article = {
                        "profile_id": profile["id"],
                        "profile_label": profile["label"],
                        "query": query,
                        "title": compact_text(str(bibjson.get("title", ""))),
                        "abstract": compact_text(str(bibjson.get("abstract", ""))),
                        "journal": compact_text(str(journal.get("title", ""))),
                        "keywords": [compact_text(str(keyword)) for keyword in bibjson.get("keywords", []) if str(keyword).strip()],
                        "subjects": [
                            compact_text(str(subject.get("term", "")))
                            for subject in bibjson.get("subject", [])
                            if str(subject.get("term", "")).strip()
                        ],
                    }

                    if len(article["abstract"]) < min_abstract_chars or not article["title"] or not article["journal"]:
                        continue

                    normalized_article_title = normalize_text(article["title"])
                    if normalized_article_title in seen_article_titles:
                        continue

                    match_score, primary_hits, secondary_hits = article_match_score(article, profile)
                    if match_score <= 0:
                        continue

                    source_record = dataset_lookup.get(normalize_text(article["journal"]))
                    source_domain_grade, _, _ = grade_domain_relevance(source_record, profile)
                    seen_article_titles.add(normalized_article_title)
                    article["match_score"] = match_score
                    article["matched_article_primary"] = sorted(primary_hits)
                    article["matched_article_secondary"] = sorted(secondary_hits)
                    article["source_in_dataset"] = source_record is not None
                    article["source_domain_grade"] = source_domain_grade
                    candidates.append(article)

        candidates.sort(
            key=lambda item: (
                -int(item["source_domain_grade"]),
                -int(item["match_score"]),
                -len(str(item["abstract"])),
                str(item["title"]).lower(),
            )
        )

        if not candidates:
            skipped_profiles.append(profile["label"])
            continue

        cases.extend(candidates[:cases_per_profile])

    return cases, skipped_profiles


def wait_for_results(page) -> None:
    page.wait_for_function(
        """() => {
            const text = document.querySelector('#results-count')?.textContent || '';
            return text.includes('matches found.');
        }""",
        timeout=30000,
    )


def collect_ranked_titles(page, max_rank: int) -> list[str]:
    titles_seen: list[str] = []

    while len(titles_seen) < max_rank:
        page.wait_for_selector(".search-card", timeout=30000)
        page_titles = [text.strip() for text in page.locator(".search-card h3 a").all_inner_texts() if text.strip()]
        if not page_titles:
            break

        for title in page_titles:
            titles_seen.append(title)
            if len(titles_seen) >= max_rank:
                return titles_seen[:max_rank]

        next_button = page.locator(".pagination-list button").filter(has_text="Next").first
        if next_button.count() == 0 or next_button.is_disabled():
            break

        previous_titles = " || ".join(page_titles)
        next_button.click()
        page.wait_for_function(
            """previous => {
                const titles = Array.from(document.querySelectorAll('.search-card h3 a'))
                    .map(node => node.textContent?.trim() || '')
                    .join(' || ');
                return Boolean(titles) && titles !== previous;
            }""",
            arg=previous_titles,
            timeout=15000,
        )

    return titles_seen[:max_rank]


def evaluate_cases(
    base_url: str,
    cases: list[dict[str, Any]],
    dataset_lookup: dict[str, dict[str, Any]],
    max_rank: int,
    sort_order: str,
) -> list[dict[str, Any]]:
    profiles_by_id = {profile["id"]: profile for profile in DOMAIN_PROFILES}
    results: list[dict[str, Any]] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()

        for case in cases:
            search_url = f"{base_url}/search/?scope=abstract&q={quote_plus(str(case['abstract']))}"
            if sort_order != "default":
                search_url += f"&sort={quote_plus(sort_order)}"

            page.goto(search_url, wait_until="networkidle")
            wait_for_results(page)
            ranked_titles = collect_ranked_titles(page, max_rank=max_rank)

            profile = profiles_by_id[str(case["profile_id"])]
            ranked_results: list[dict[str, Any]] = []
            first_relevant_rank: int | None = None
            exact_source_rank: int | None = None

            for index, title in enumerate(ranked_titles, start=1):
                record = dataset_lookup.get(normalize_text(title))
                grade, primary_hits, secondary_hits = grade_record_relevance(record, profile, str(case["journal"]))
                if grade >= 2 and first_relevant_rank is None:
                    first_relevant_rank = index
                if normalize_text(title) == normalize_text(str(case["journal"])) and exact_source_rank is None:
                    exact_source_rank = index
                ranked_results.append(
                    {
                        "rank": index,
                        "title": title,
                        "grade": grade,
                        "matched_primary": sorted(primary_hits),
                        "matched_secondary": sorted(secondary_hits),
                    }
                )

            results.append(
                {
                    **case,
                    "ranked_results": ranked_results,
                    "first_relevant_rank": first_relevant_rank,
                    "exact_source_rank": exact_source_rank,
                }
            )

        browser.close()

    return results


def ndcg_at_k(results: list[dict[str, Any]], k: int) -> float:
    if not results:
        return 0.0

    total = 0.0
    for result in results:
        observed = [int(entry["grade"]) for entry in result["ranked_results"][:k]]
        ideal = sorted(observed, reverse=True)
        dcg = sum(((2**grade) - 1) / math.log2(index + 2) for index, grade in enumerate(observed) if grade > 0)
        idcg = sum(((2**grade) - 1) / math.log2(index + 2) for index, grade in enumerate(ideal) if grade > 0)
        total += (dcg / idcg) if idcg else 0.0
    return total / len(results)


def print_summary(results: list[dict[str, Any]], skipped_profiles: list[str], max_rank: int, sort_order: str) -> int:
    if not results:
        raise SystemExit("No DOAJ benchmark cases could be constructed from the configured profiles.")

    relevant_ranks = [int(result["first_relevant_rank"]) for result in results if isinstance(result.get("first_relevant_rank"), int)]
    exact_source_ranks = [int(result["exact_source_rank"]) for result in results if isinstance(result.get("exact_source_rank"), int)]
    hit_at_5 = sum(1 for rank in relevant_ranks if rank <= 5) / len(results)
    hit_at_10 = sum(1 for rank in relevant_ranks if rank <= 10) / len(results)
    hit_at_max = sum(1 for rank in relevant_ranks if rank <= max_rank) / len(results)
    mrr_relevant = sum((1 / rank) for rank in relevant_ranks) / len(results)
    exact_source_recall = sum(1 for rank in exact_source_ranks if rank <= max_rank) / len(results)

    print(f"DOAJ relevance cases used: {len(results)}")
    print(f"Sort order: {sort_order}")
    print(f"Relevant Hit@5: {hit_at_5:.3f}")
    print(f"Relevant Hit@10: {hit_at_10:.3f}")
    if max_rank not in {5, 10}:
        print(f"Relevant Hit@{max_rank}: {hit_at_max:.3f}")
    print(f"Relevant MRR: {mrr_relevant:.3f}")
    print(f"nDCG@10: {ndcg_at_k(results, 10):.3f}")
    print(f"Exact source Recall@{max_rank}: {exact_source_recall:.3f}")
    if skipped_profiles:
        print(f"Skipped profiles: {', '.join(skipped_profiles)}")

    for result in results:
        relevant_rank_text = str(result["first_relevant_rank"]) if result["first_relevant_rank"] is not None else f">{max_rank}"
        source_rank_text = str(result["exact_source_rank"]) if result["exact_source_rank"] is not None else f">{max_rank}"
        print(
            f"- {result['profile_label']} | query {result['query']} | relevant rank {relevant_rank_text} | "
            f"source rank {source_rank_text} | source in dataset {result['source_in_dataset']} | "
            f"source domain grade {result['source_domain_grade']}"
        )
        print(f"  Article: {result['title']}")
        print(f"  Source journal: {result['journal']}")
        print(
            f"  Article signals: primary={', '.join(result['matched_article_primary']) or '-'}; "
            f"secondary={', '.join(result['matched_article_secondary']) or '-'}"
        )
        top_results = []
        for entry in result["ranked_results"][:5]:
            label = f"{entry['title']} [g{entry['grade']}]"
            top_results.append(label)
        print(f"  Top results: {', '.join(top_results)}")

    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark abstract-to-journal recommendations against DOAJ article abstracts with domain-oriented relevance metrics.")
    parser.add_argument("--cases-per-profile", type=int, default=DEFAULT_CASES_PER_PROFILE, help="Maximum number of article cases to keep per domain profile.")
    parser.add_argument("--page-size", type=int, default=DEFAULT_PAGE_SIZE, help="Number of DOAJ search results to fetch per request.")
    parser.add_argument("--max-pages", type=int, default=DEFAULT_MAX_PAGES, help="Maximum DOAJ result pages to inspect per query.")
    parser.add_argument("--max-rank", type=int, default=DEFAULT_MAX_RANK, help="Maximum search-result depth to score.")
    parser.add_argument("--min-abstract-chars", type=int, default=DEFAULT_MIN_ABSTRACT_CHARS, help="Minimum abstract length required for a DOAJ case.")
    parser.add_argument("--sort", choices=["default", "fit_desc"], default="default", help="Result ordering to evaluate.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not MANIFEST_PATH.exists():
        raise SystemExit("Build output is missing. Run scripts/build_site.py first.")

    _, dataset_lookup = load_dataset_records()
    cases, skipped_profiles = build_cases(
        dataset_lookup=dataset_lookup,
        cases_per_profile=args.cases_per_profile,
        page_size=args.page_size,
        max_pages=args.max_pages,
        min_abstract_chars=args.min_abstract_chars,
    )
    if not cases:
        raise SystemExit("No DOAJ benchmark cases could be constructed from the configured profiles.")

    with static_server(DOCS_DIR) as base_url:
        results = evaluate_cases(
            base_url=base_url,
            cases=cases,
            dataset_lookup=dataset_lookup,
            max_rank=args.max_rank,
            sort_order=args.sort,
        )

    return print_summary(results, skipped_profiles=skipped_profiles, max_rank=args.max_rank, sort_order=args.sort)


if __name__ == "__main__":
    sys.exit(main())
