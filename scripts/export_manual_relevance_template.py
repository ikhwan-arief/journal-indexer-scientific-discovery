from __future__ import annotations

"""Dikembangkan oleh Ikhwan Arief (ikhwan[at]unand.ac.id)
Lisensi aplikasi: Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)
"""

import argparse
import csv
import sys
from pathlib import Path

from sparse_baseline_support import DOAJ_BENCHMARK, SparseBaselineIndex, load_doaj_cases


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export a manual relevance labeling template from current app results, BM25F, and TF-IDF candidate pools.")
    parser.add_argument("--output", type=Path, default=Path("paper/manual_relevance_benchmark_template.csv"), help="Output CSV path.")
    parser.add_argument("--cases-per-profile", type=int, default=1, help="Maximum number of DOAJ cases to keep per profile.")
    parser.add_argument("--page-size", type=int, default=20, help="Number of DOAJ search results to fetch per request.")
    parser.add_argument("--max-pages", type=int, default=2, help="Maximum DOAJ result pages to inspect per query.")
    parser.add_argument("--min-abstract-chars", type=int, default=DOAJ_BENCHMARK.DEFAULT_MIN_ABSTRACT_CHARS, help="Minimum abstract length required for a DOAJ case.")
    parser.add_argument("--candidate-depth", type=int, default=10, help="Maximum rank depth to collect from each ranking method.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    index = SparseBaselineIndex.build()
    doaj_cases, skipped_profiles = load_doaj_cases(
        dataset_lookup=index.record_lookup,
        cases_per_profile=args.cases_per_profile,
        page_size=args.page_size,
        max_pages=args.max_pages,
        min_abstract_chars=args.min_abstract_chars,
    )
    if not doaj_cases:
        raise SystemExit("No DOAJ benchmark cases could be constructed from the configured profiles.")

    profile_lookup = {profile["id"]: profile for profile in DOAJ_BENCHMARK.DOMAIN_PROFILES}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with DOAJ_BENCHMARK.static_server(DOAJ_BENCHMARK.DOCS_DIR) as base_url:
        app_results = DOAJ_BENCHMARK.evaluate_cases(
            base_url=base_url,
            cases=doaj_cases,
            dataset_lookup={
                normalized_title: {
                    **record.raw_record,
                    "_normalized_title": record.normalized_title,
                    "_normalized_text": " ".join([record.title.lower(), record.categories.lower(), record.areas.lower()]),
                }
                for normalized_title, record in index.record_lookup.items()
            },
            max_rank=args.candidate_depth,
            sort_order="default",
        )

    app_lookup = {
        (str(case["profile_id"]), str(case["title"]), str(case["journal"])): case
        for case in app_results
    }

    rows: list[dict[str, str]] = []
    for case_number, case in enumerate(doaj_cases, start=1):
        bm25f_ranked = index.bm25f_rank(str(case["abstract"]), max_rank=args.candidate_depth)
        tfidf_ranked = index.tfidf_rank(str(case["abstract"]), max_rank=args.candidate_depth)
        app_case = app_lookup[(str(case["profile_id"]), str(case["title"]), str(case["journal"]))]
        profile = profile_lookup[str(case["profile_id"])]

        candidate_map: dict[str, dict[str, object]] = {}
        for entry in app_case["ranked_results"]:
            candidate_map.setdefault(
                str(entry["title"]),
                {
                    "app_rank": str(entry["rank"]),
                    "bm25f_rank": "",
                    "tfidf_rank": "",
                    "profile_grade_hint": str(entry["grade"]),
                },
            )
        for rank, (_, record) in enumerate(bm25f_ranked, start=1):
            candidate_map.setdefault(record.title, {"app_rank": "", "bm25f_rank": "", "tfidf_rank": "", "profile_grade_hint": ""})
            candidate_map[record.title]["bm25f_rank"] = str(rank)
        for rank, (_, record) in enumerate(tfidf_ranked, start=1):
            candidate_map.setdefault(record.title, {"app_rank": "", "bm25f_rank": "", "tfidf_rank": "", "profile_grade_hint": ""})
            candidate_map[record.title]["tfidf_rank"] = str(rank)

        for candidate_title, scores in sorted(
            candidate_map.items(),
            key=lambda item: (
                min(
                    [
                        int(value)
                        for value in [item[1]["app_rank"], item[1]["bm25f_rank"], item[1]["tfidf_rank"]]
                        if str(value).isdigit()
                    ]
                    or [999]
                ),
                item[0].lower(),
            ),
        ):
            rows.append(
                {
                    "case_id": f"MR-{case_number:02d}",
                    "profile_id": str(case["profile_id"]),
                    "profile_label": str(case["profile_label"]),
                    "seed_query": str(case["query"]),
                    "source_article_title": str(case["title"]),
                    "source_journal": str(case["journal"]),
                    "source_in_dataset": str(case["source_in_dataset"]),
                    "source_domain_grade_hint": str(case["source_domain_grade"]),
                    "profile_primary_terms": "; ".join(profile["journal_primary"]),
                    "profile_secondary_terms": "; ".join(profile["journal_secondary"]),
                    "abstract": str(case["abstract"]),
                    "candidate_journal": candidate_title,
                    "app_default_rank": str(scores["app_rank"]),
                    "bm25f_rank": str(scores["bm25f_rank"]),
                    "tfidf_rank": str(scores["tfidf_rank"]),
                    "auto_grade_hint": str(scores["profile_grade_hint"]),
                    "manual_grade": "",
                    "manual_decision": "",
                    "manual_notes": "",
                }
            )

    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "case_id",
                "profile_id",
                "profile_label",
                "seed_query",
                "source_article_title",
                "source_journal",
                "source_in_dataset",
                "source_domain_grade_hint",
                "profile_primary_terms",
                "profile_secondary_terms",
                "abstract",
                "candidate_journal",
                "app_default_rank",
                "bm25f_rank",
                "tfidf_rank",
                "auto_grade_hint",
                "manual_grade",
                "manual_decision",
                "manual_notes",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    if skipped_profiles:
        print(f"Skipped profiles: {', '.join(skipped_profiles)}")
    print(f"Wrote {len(rows)} labeling rows to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
