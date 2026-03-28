from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

from sparse_baseline_support import (
    DOAJ_BENCHMARK,
    SparseBaselineIndex,
    evaluate_exact_source,
    evaluate_relevance,
    exact_source_metrics,
    load_doaj_cases,
    load_exact_source_cases,
    relevance_metrics,
)


def print_exact_summary(method: str, results: list[dict[str, object]], max_rank: int) -> None:
    metrics = exact_source_metrics(results, max_rank=max_rank)
    print(f"=== Exact-source benchmark | method={method} ===")
    print(f"Benchmark cases used: {len(results)}")
    print(f"Recall@1: {metrics['recall_at_1']:.3f}")
    print(f"Recall@5: {metrics['recall_at_5']:.3f}")
    print(f"Recall@10: {metrics['recall_at_10']:.3f}")
    print(f"Recall@{max_rank}: {metrics[f'recall_at_{max_rank}']:.3f}")
    print(f"MRR: {metrics['mrr']:.3f}")
    if math.isfinite(metrics["mean_rank_found"]):
        print(f"Mean rank (found cases): {metrics['mean_rank_found']:.2f}")
    for result in results:
        rank_text = str(result["rank"]) if result["rank"] is not None else f">{max_rank}"
        print(
            f"- {result['journal']}: rank {rank_text} | abstract chars {result['abstract_length']} | "
            f"pdf {Path(str(result['pdf_path'])).name}"
        )
        print(f"  Top results: {', '.join(result['first_page_titles'])}")


def print_relevance_summary(method: str, results: list[dict[str, object]], skipped_profiles: list[str], max_rank: int) -> None:
    metrics = relevance_metrics(results, max_rank=max_rank)
    print(f"=== DOAJ relevance benchmark | method={method} ===")
    print(f"DOAJ relevance cases used: {len(results)}")
    print(f"Relevant Hit@5: {metrics['hit_at_5']:.3f}")
    print(f"Relevant Hit@10: {metrics['hit_at_10']:.3f}")
    if max_rank not in {5, 10}:
        print(f"Relevant Hit@{max_rank}: {metrics[f'hit_at_{max_rank}']:.3f}")
    print(f"Relevant MRR: {metrics['mrr']:.3f}")
    print(f"nDCG@10: {metrics['ndcg_at_10']:.3f}")
    print(f"Exact source Recall@{max_rank}: {metrics[f'exact_source_recall_at_{max_rank}']:.3f}")
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
        top_results = []
        for entry in result["ranked_results"][:5]:
            top_results.append(f"{entry['title']} [g{entry['grade']}]")
        print(f"  Top results: {', '.join(top_results)}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate BM25F and TF-IDF baselines on the current sparse journal metadata benchmarks.")
    parser.add_argument("--refs-dir", type=Path, default=Path.home() / "Documents" / "Disertasi" / "refs", help="Directory containing benchmark PDF references.")
    parser.add_argument("--pdf-text-limit", type=int, default=24000, help="Maximum number of PDF characters to extract before parsing the abstract.")
    parser.add_argument("--max-rank", type=int, default=30, help="Maximum rank depth to score.")
    parser.add_argument("--cases-per-profile", type=int, default=1, help="Maximum number of DOAJ cases to keep per profile.")
    parser.add_argument("--page-size", type=int, default=20, help="Number of DOAJ search results to fetch per request.")
    parser.add_argument("--max-pages", type=int, default=2, help="Maximum DOAJ result pages to inspect per query.")
    parser.add_argument("--min-abstract-chars", type=int, default=DOAJ_BENCHMARK.DEFAULT_MIN_ABSTRACT_CHARS, help="Minimum abstract length required for a DOAJ case.")
    parser.add_argument("--methods", nargs="+", choices=["bm25f", "tfidf"], default=["bm25f", "tfidf"], help="Baseline methods to evaluate.")
    parser.add_argument("--output-json", type=Path, help="Optional path to write structured benchmark results as JSON.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.refs_dir.exists():
        raise SystemExit(f"Refs directory not found: {args.refs_dir}")

    index = SparseBaselineIndex.build()
    exact_cases = load_exact_source_cases(args.refs_dir, pdf_text_limit=args.pdf_text_limit)
    if not exact_cases:
        raise SystemExit("No exact-source benchmark cases could be constructed from the available PDF references.")

    doaj_cases, skipped_profiles = load_doaj_cases(
        dataset_lookup=index.record_lookup,
        cases_per_profile=args.cases_per_profile,
        page_size=args.page_size,
        max_pages=args.max_pages,
        min_abstract_chars=args.min_abstract_chars,
    )
    if not doaj_cases:
        raise SystemExit("No DOAJ benchmark cases could be constructed from the configured profiles.")

    collected_output: dict[str, object] = {"exact_source": {}, "doaj_relevance": {}, "skipped_profiles": skipped_profiles}
    for method in args.methods:
        exact_results = evaluate_exact_source(index, exact_cases, method=method, max_rank=args.max_rank)
        doaj_results = evaluate_relevance(index, doaj_cases, method=method, max_rank=args.max_rank)
        print_exact_summary(method, exact_results, max_rank=args.max_rank)
        print_relevance_summary(method, doaj_results, skipped_profiles=skipped_profiles, max_rank=args.max_rank)
        collected_output["exact_source"][method] = {"metrics": exact_source_metrics(exact_results, max_rank=args.max_rank), "results": exact_results}
        collected_output["doaj_relevance"][method] = {"metrics": relevance_metrics(doaj_results, max_rank=args.max_rank), "results": doaj_results}

    if args.output_json:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(json.dumps(collected_output, indent=2), encoding="utf-8")

    return 0


if __name__ == "__main__":
    sys.exit(main())
