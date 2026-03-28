from __future__ import annotations

import importlib.util
import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = REPO_ROOT / "docs"

SEARCH_STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "being", "by", "for", "from", "in", "into", "is", "it", "its", "of", "on", "onto",
    "or", "that", "the", "their", "this", "to", "with", "using", "used", "use", "we", "our", "was", "were", "which", "while", "within",
    "without", "can", "may", "than", "then", "these", "those", "there", "here", "where", "when", "whose", "who", "whom", "what", "how",
    "about", "after", "before", "between", "during", "through", "across", "over", "under", "such", "also", "other", "others", "more",
    "most", "some", "many", "much", "each", "any", "all", "both", "either", "neither", "per", "via", "yet", "still",
    "yang", "dan", "atau", "di", "ke", "dari", "untuk", "pada", "dengan", "dalam", "sebagai", "karena", "bahwa", "ini", "itu", "tersebut",
    "adalah", "oleh", "juga", "agar", "antara", "dapat", "tidak", "serta", "para", "kami", "kita", "anda", "mereka", "sebuah", "suatu",
    "terhadap", "melalui", "hingga", "setelah", "sebelum", "tanpa", "secara", "telah", "belum", "yakni", "yaitu", "guna", "maka", "namun",
    "tetapi", "selain", "saat", "ketika", "jika", "bila", "sehingga", "dalamnya", "atas", "bawah", "lebih", "kurang", "masih", "sudah",
    "lagi", "ialah", "yakinkan", "karna", "nya",
}

ENGLISH_SUFFIX_RULES = [
    ("ization", 8),
    ("isation", 8),
    ("ational", 8),
    ("fulness", 8),
    ("ousness", 8),
    ("iveness", 8),
    ("lessly", 8),
    ("ingly", 6),
    ("edly", 6),
    ("ments", 6),
    ("ment", 6),
    ("ation", 6),
    ("ities", 6),
    ("ings", 5),
    ("ness", 6),
    ("ions", 5),
    ("ion", 5),
    ("ers", 5),
    ("ing", 5),
    ("er", 5),
    ("ed", 4),
    ("ly", 4),
    ("es", 4),
    ("s", 4),
]

INDONESIAN_SUFFIX_RULES = [
    ("kannya", 8),
    ("annya", 7),
    ("kanlah", 8),
    ("kan", 5),
    ("nya", 5),
    ("lah", 5),
    ("kah", 5),
    ("pun", 5),
    ("tah", 5),
    ("an", 5),
]

FIELD_WEIGHTS = {"title": 1.0, "categories": 2.2, "areas": 1.6}
FIELD_B = {"title": 0.75, "categories": 0.70, "areas": 0.65}
BM25F_K1 = 1.2


def load_script_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module {name} from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ABSTRACT_BENCHMARK = load_script_module("benchmark_abstract_matching_module", REPO_ROOT / "scripts" / "benchmark_abstract_matching.py")
DOAJ_BENCHMARK = load_script_module("benchmark_doaj_relevance_module", REPO_ROOT / "scripts" / "benchmark_doaj_relevance.py")


def normalize_text(value: str) -> str:
    lowered = (value or "").strip().lower()
    lowered = re.sub(r"[^a-z0-9]+", " ", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def stem_token(token: str) -> str:
    value = token
    for suffix, min_length in ENGLISH_SUFFIX_RULES:
        if value.endswith(suffix) and len(value) >= min_length:
            value = value[: -len(suffix)]
            break
    for suffix, min_length in INDONESIAN_SUFFIX_RULES:
        if value.endswith(suffix) and len(value) >= min_length:
            value = value[: -len(suffix)]
            break
    return value or token


def tokenize(text: str) -> list[str]:
    tokens = []
    for raw in re.findall(r"[a-z0-9]+", normalize_text(text)):
        if raw in SEARCH_STOP_WORDS:
            continue
        token = stem_token(raw)
        if len(token) < 2 or token in SEARCH_STOP_WORDS:
            continue
        tokens.append(token)
    return tokens


def query_term_weight(term_frequency: int) -> float:
    return 1.0 + math.log(term_frequency) if term_frequency > 0 else 0.0


@dataclass
class IndexedRecord:
    sourceid: str
    title: str
    categories: str
    areas: str
    normalized_title: str
    field_tokens: dict[str, Counter[str]]
    field_lengths: dict[str, int]
    tfidf_weights: dict[str, float]
    tfidf_norm: float
    raw_record: dict[str, Any]


class SparseBaselineIndex:
    def __init__(self, records: list[IndexedRecord], document_frequency: Counter[str], average_lengths: dict[str, float]) -> None:
        self.records = records
        self.document_frequency = document_frequency
        self.average_lengths = average_lengths
        self.record_lookup = {record.normalized_title: record for record in records}
        self.total_documents = len(records)

    @classmethod
    def build(cls) -> "SparseBaselineIndex":
        payload_records: list[dict[str, Any]] = []
        for path in sorted((DOCS_DIR / "data" / "search-chunks").glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload_records.extend(payload.get("records", []))

        document_frequency: Counter[str] = Counter()
        field_length_totals = {"title": 0, "categories": 0, "areas": 0}
        indexed_records: list[IndexedRecord] = []
        document_vectors: list[tuple[dict[str, Counter[str]], dict[str, int], dict[str, Any]]] = []

        for raw_record in payload_records:
            field_tokens = {
                "title": Counter(tokenize(str(raw_record.get("title", "")))),
                "categories": Counter(tokenize(str(raw_record.get("categories", "")))),
                "areas": Counter(tokenize(str(raw_record.get("areas", "")))),
            }
            field_lengths = {field: sum(counter.values()) for field, counter in field_tokens.items()}
            for field, length in field_lengths.items():
                field_length_totals[field] += length

            union_terms = set()
            for counter in field_tokens.values():
                union_terms.update(counter.keys())
            document_frequency.update(union_terms)
            document_vectors.append((field_tokens, field_lengths, raw_record))

        total_documents = max(1, len(document_vectors))
        average_lengths = {
            field: (field_length_totals[field] / total_documents) if total_documents else 0.0
            for field in field_length_totals
        }

        for field_tokens, field_lengths, raw_record in document_vectors:
            tfidf_weights: dict[str, float] = {}
            for field, counter in field_tokens.items():
                field_weight = FIELD_WEIGHTS[field]
                for term, count in counter.items():
                    idf = math.log((1 + total_documents) / (1 + document_frequency[term])) + 1.0
                    tfidf_weights[term] = tfidf_weights.get(term, 0.0) + ((1.0 + math.log(count)) * idf * field_weight)
            tfidf_norm = math.sqrt(sum(weight * weight for weight in tfidf_weights.values()))

            indexed_records.append(
                IndexedRecord(
                    sourceid=str(raw_record.get("sourceid", "")),
                    title=str(raw_record.get("title", "")),
                    categories=str(raw_record.get("categories", "")),
                    areas=str(raw_record.get("areas", "")),
                    normalized_title=normalize_text(str(raw_record.get("title", ""))),
                    field_tokens=field_tokens,
                    field_lengths=field_lengths,
                    tfidf_weights=tfidf_weights,
                    tfidf_norm=tfidf_norm,
                    raw_record=dict(raw_record),
                )
            )

        return cls(indexed_records, document_frequency, average_lengths)

    def bm25f_rank(self, query: str, max_rank: int) -> list[tuple[float, IndexedRecord]]:
        query_counter = Counter(tokenize(query))
        if not query_counter:
            return []

        ranked: list[tuple[float, IndexedRecord]] = []
        for record in self.records:
            score = 0.0
            for term, qtf in query_counter.items():
                df = self.document_frequency.get(term, 0)
                if df <= 0:
                    continue
                idf = math.log(((self.total_documents - df + 0.5) / (df + 0.5)) + 1.0)
                weighted_tf = 0.0
                for field, counter in record.field_tokens.items():
                    tf = counter.get(term, 0)
                    if tf <= 0:
                        continue
                    avg_len = self.average_lengths[field] or 1.0
                    field_norm = (1.0 - FIELD_B[field]) + FIELD_B[field] * (record.field_lengths[field] / avg_len)
                    weighted_tf += FIELD_WEIGHTS[field] * (tf / field_norm)
                if weighted_tf <= 0:
                    continue
                score += idf * ((weighted_tf * (BM25F_K1 + 1.0)) / (weighted_tf + BM25F_K1)) * query_term_weight(qtf)

            if score > 0:
                ranked.append((score, record))

        ranked.sort(key=lambda item: (-item[0], item[1].title.lower()))
        return ranked[:max_rank]

    def tfidf_rank(self, query: str, max_rank: int) -> list[tuple[float, IndexedRecord]]:
        query_counter = Counter(tokenize(query))
        if not query_counter:
            return []

        query_weights: dict[str, float] = {}
        for term, count in query_counter.items():
            df = self.document_frequency.get(term, 0)
            if df <= 0:
                continue
            idf = math.log((1 + self.total_documents) / (1 + df)) + 1.0
            query_weights[term] = (1.0 + math.log(count)) * idf

        query_norm = math.sqrt(sum(weight * weight for weight in query_weights.values()))
        if query_norm <= 0:
            return []

        ranked: list[tuple[float, IndexedRecord]] = []
        for record in self.records:
            if record.tfidf_norm <= 0:
                continue
            dot = 0.0
            for term, query_weight in query_weights.items():
                dot += query_weight * record.tfidf_weights.get(term, 0.0)
            if dot <= 0:
                continue
            cosine = dot / (query_norm * record.tfidf_norm)
            ranked.append((cosine, record))

        ranked.sort(key=lambda item: (-item[0], item[1].title.lower()))
        return ranked[:max_rank]


def load_exact_source_cases(refs_dir: Path, pdf_text_limit: int) -> list[dict[str, Any]]:
    dataset_titles = set()
    for path in sorted((DOCS_DIR / "data" / "search-chunks").glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        for record in payload.get("records", []):
            dataset_titles.add(normalize_text(str(record.get("title", ""))))
    return ABSTRACT_BENCHMARK.build_case_inputs(refs_dir, dataset_titles, max_chars=pdf_text_limit)


def load_doaj_cases(
    dataset_lookup: dict[str, IndexedRecord],
    cases_per_profile: int,
    page_size: int,
    max_pages: int,
    min_abstract_chars: int,
) -> tuple[list[dict[str, Any]], list[str]]:
    adapted_lookup: dict[str, dict[str, Any]] = {}
    for normalized_title, record in dataset_lookup.items():
        adapted_lookup[normalized_title] = {
            **record.raw_record,
            "_normalized_title": record.normalized_title,
            "_normalized_text": normalize_text(" ".join([record.title, record.categories, record.areas])),
        }
    return DOAJ_BENCHMARK.build_cases(
        dataset_lookup=adapted_lookup,
        cases_per_profile=cases_per_profile,
        page_size=page_size,
        max_pages=max_pages,
        min_abstract_chars=min_abstract_chars,
    )


def exact_source_metrics(results: list[dict[str, Any]], max_rank: int) -> dict[str, float]:
    total = max(1, len(results))
    found_ranks = [int(result["rank"]) for result in results if isinstance(result.get("rank"), int)]
    return {
        "recall_at_1": sum(1 for rank in found_ranks if rank <= 1) / total,
        "recall_at_5": sum(1 for rank in found_ranks if rank <= 5) / total,
        "recall_at_10": sum(1 for rank in found_ranks if rank <= 10) / total,
        f"recall_at_{max_rank}": sum(1 for rank in found_ranks if rank <= max_rank) / total,
        "mrr": sum((1.0 / rank) for rank in found_ranks) / total,
        "mean_rank_found": (sum(found_ranks) / len(found_ranks)) if found_ranks else math.inf,
    }


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


def relevance_metrics(results: list[dict[str, Any]], max_rank: int) -> dict[str, float]:
    total = max(1, len(results))
    relevant_ranks = [int(result["first_relevant_rank"]) for result in results if isinstance(result.get("first_relevant_rank"), int)]
    exact_source_ranks = [int(result["exact_source_rank"]) for result in results if isinstance(result.get("exact_source_rank"), int)]
    return {
        "hit_at_5": sum(1 for rank in relevant_ranks if rank <= 5) / total,
        "hit_at_10": sum(1 for rank in relevant_ranks if rank <= 10) / total,
        f"hit_at_{max_rank}": sum(1 for rank in relevant_ranks if rank <= max_rank) / total,
        "mrr": sum((1.0 / rank) for rank in relevant_ranks) / total,
        "ndcg_at_10": ndcg_at_k(results, 10),
        f"exact_source_recall_at_{max_rank}": sum(1 for rank in exact_source_ranks if rank <= max_rank) / total,
    }


def evaluate_exact_source(index: SparseBaselineIndex, cases: list[dict[str, Any]], method: str, max_rank: int) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for case in cases:
        query = str(case["abstract"])
        ranked = index.bm25f_rank(query, max_rank=max_rank) if method == "bm25f" else index.tfidf_rank(query, max_rank=max_rank)
        ranked_titles = [record.title for _, record in ranked]
        expected = normalize_text(str(case["journal"]))
        rank = None
        for idx, title in enumerate(ranked_titles, start=1):
            if normalize_text(title) == expected:
                rank = idx
                break
        results.append(
            {
                "journal": case["journal"],
                "pdf_path": str(case["pdf_path"]),
                "rank": rank,
                "first_page_titles": ranked_titles[:5],
                "titles_seen": ranked_titles,
                "abstract_length": len(query),
            }
        )
    return results


def evaluate_relevance(index: SparseBaselineIndex, cases: list[dict[str, Any]], method: str, max_rank: int) -> list[dict[str, Any]]:
    profiles_by_id = {profile["id"]: profile for profile in DOAJ_BENCHMARK.DOMAIN_PROFILES}
    results: list[dict[str, Any]] = []
    for case in cases:
        query = str(case["abstract"])
        ranked = index.bm25f_rank(query, max_rank=max_rank) if method == "bm25f" else index.tfidf_rank(query, max_rank=max_rank)
        profile = profiles_by_id[str(case["profile_id"])]

        ranked_results = []
        first_relevant_rank = None
        exact_source_rank = None
        for idx, (_, record) in enumerate(ranked, start=1):
            adapted_record = {
                **record.raw_record,
                "_normalized_title": record.normalized_title,
                "_normalized_text": normalize_text(" ".join([record.title, record.categories, record.areas])),
            }
            grade, primary_hits, secondary_hits = DOAJ_BENCHMARK.grade_record_relevance(adapted_record, profile, str(case["journal"]))
            if grade >= 2 and first_relevant_rank is None:
                first_relevant_rank = idx
            if record.normalized_title == normalize_text(str(case["journal"])) and exact_source_rank is None:
                exact_source_rank = idx
            ranked_results.append(
                {
                    "rank": idx,
                    "title": record.title,
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
    return results
