from __future__ import annotations

import argparse
import contextlib
import json
import math
import os
import re
import socketserver
import subprocess
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import quote_plus

try:
    from playwright.sync_api import sync_playwright
except ImportError as error:
    raise SystemExit(
        "Playwright is not installed in the current interpreter. Run with the repo virtualenv, for example:\n"
        "  ./.venv/bin/python scripts/benchmark_abstract_matching.py\n"
    ) from error


REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = REPO_ROOT / "docs"
MANIFEST_PATH = DOCS_DIR / "data" / "search-manifest.json"
DEFAULT_REFS_DIR = Path.home() / "Documents" / "Disertasi" / "refs"
DEFAULT_MAX_RANK = 50
DEFAULT_PDF_TEXT_LIMIT = 24000
BENCHMARK_CASES = [
    {
        "pdf": "Generative artificial intelligence augmenting SME financial management.pdf",
        "journal": "Technovation",
    },
    {
        "pdf": "Artificial intelligence implementation in manufacturing SMEs - A resource orchestration approach.pdf",
        "journal": "International Journal of Information Management",
    },
    {
        "pdf": "68 Machine learning implementation in small and medium-sized enterprises.pdf",
        "journal": "Production Engineering",
    },
    {
        "pdf": "6 Factors influencing the adoption of artificial intelligence in e-commerce by small and medium-sized enterprises.pdf",
        "journal": "International Journal of Information Management Data Insights",
    },
    {
        "pdf": "40 Adoption paths of digital transformation in manufacturing SME.pdf",
        "journal": "International Journal of Production Economics",
    },
    {
        "pdf": "72 Testing an adoption model for Industry 4.0 and sustainability.pdf",
        "journal": "Sustainable Production and Consumption",
    },
    {
        "pdf": "59 Proposal and validation of an industry 4.0 maturity model for SMEs.pdf",
        "journal": "Journal of Industrial Engineering and Management",
    },
    {
        "pdf": "17 Drivers and Challenges of Industry 4.0 Adoption  An Empirical Study on Metal and Metal Products Manufacturing SMEs.pdf",
        "journal": "Management Systems in Production Engineering",
    },
    {
        "pdf": "82 Artificial Intelligence and Reduced SMEs Business Risks - A Dynamic Capabilities Analysis During the COVID-19 Pandemic.pdf",
        "journal": "Information Systems Frontiers",
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
    lowered = (value or "").strip().lower()
    lowered = re.sub(r"[^a-z0-9]+", " ", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def load_dataset_titles() -> set[str]:
    records: list[dict[str, object]] = []
    for path in sorted((DOCS_DIR / "data" / "search-chunks").glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        records.extend(payload.get("records", []))
    return {normalize_text(str(record.get("title", ""))) for record in records}


def extract_pdf_text(path: Path, max_chars: int) -> str:
    cache_dir = Path("/tmp/journal-discovery-swift-module-cache")
    cache_dir.mkdir(parents=True, exist_ok=True)
    swift_source = f"""
import Foundation
import PDFKit
let path = {json.dumps(str(path))}
let maxChars = {max_chars}
guard let doc = PDFDocument(url: URL(fileURLWithPath: path)) else {{
  fputs("OPEN_FAILED\\n", stderr)
  exit(1)
}}
let text = doc.string ?? ""
print(String(text.prefix(maxChars)))
"""
    environment = dict(
        **dict(os.environ),
        CLANG_MODULE_CACHE_PATH=str(cache_dir),
        SWIFT_MODULE_CACHE_PATH=str(cache_dir),
    )
    process = subprocess.run(
        ["swift", "-e", swift_source],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
        env=environment,
    )
    if process.returncode != 0:
        raise RuntimeError(f"Could not extract text from {path.name}: {process.stderr.strip() or process.stdout.strip()}")
    return process.stdout


def clean_pdf_text(text: str) -> str:
    cleaned = text.replace("\r", "\n")
    cleaned = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", cleaned)
    cleaned = re.sub(r"[ \t]+\n", "\n", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned


def extract_abstract(text: str) -> str | None:
    cleaned = clean_pdf_text(text)
    start_match = re.search(r"\bA\s*B\s*S\s*T\s*R\s*A\s*C\s*T\b[:\s-]*", cleaned, re.IGNORECASE)
    if not start_match:
        start_match = re.search(r"\bAbstract\b[:\s-]*", cleaned, re.IGNORECASE)
    if not start_match:
        return None

    remainder = cleaned[start_match.end():]
    end_candidates = []
    for pattern in (
        r"\n\s*1[\.\s]+\s*Introduction\b",
        r"\n\s*1\s*Introduction\b",
        r"\n\s*Introduction\b",
        r"\n\s*1[\.\s]+\s*[A-Z][^\n]{2,80}\n",
    ):
        match = re.search(pattern, remainder, re.IGNORECASE)
        if match and match.start() > 200:
            end_candidates.append(match.start())

    end_index = min(end_candidates) if end_candidates else min(len(remainder), 2400)
    abstract = remainder[:end_index]
    abstract = re.sub(r"\s+", " ", abstract).strip()
    if len(abstract) < 250:
        return None
    return abstract


def wait_for_results(page) -> None:
    page.wait_for_function(
        """() => {
            const text = document.querySelector('#results-count')?.textContent || '';
            return text.includes('matches found.');
        }""",
        timeout=30000,
    )


def collect_rank(page, expected_title: str, max_rank: int) -> tuple[int | None, list[str]]:
    expected = normalize_text(expected_title)
    titles_seen: list[str] = []

    while len(titles_seen) < max_rank:
        page.wait_for_selector(".search-card", timeout=30000)
        page_titles = [text.strip() for text in page.locator(".search-card h3 a").all_inner_texts() if text.strip()]
        if not page_titles:
            break

        for title in page_titles:
            titles_seen.append(title)
            if normalize_text(title) == expected:
                return len(titles_seen), titles_seen[: min(max_rank, len(titles_seen))]
            if len(titles_seen) >= max_rank:
                return None, titles_seen[:max_rank]

        next_button = page.locator(".pagination-list button").filter(has_text="Next").first
        if next_button.count() == 0 or next_button.is_disabled():
            break

        if len(titles_seen) >= max_rank:
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

    return None, titles_seen[:max_rank]


def build_case_inputs(refs_dir: Path, dataset_titles: set[str], max_chars: int) -> list[dict[str, object]]:
    cases: list[dict[str, object]] = []
    for case in BENCHMARK_CASES:
        pdf_path = refs_dir / str(case["pdf"])
        journal_title = str(case["journal"])
        if not pdf_path.exists():
            continue
        if normalize_text(journal_title) not in dataset_titles:
            continue

        try:
            pdf_text = extract_pdf_text(pdf_path, max_chars=max_chars)
            abstract = extract_abstract(pdf_text)
        except Exception as error:
            print(f"Skipping {pdf_path.name}: {error}", file=sys.stderr)
            continue
        if not abstract:
            print(f"Skipping {pdf_path.name}: abstract could not be parsed.", file=sys.stderr)
            continue

        cases.append({
            "pdf_path": pdf_path,
            "journal": journal_title,
            "abstract": abstract,
        })
    return cases


def evaluate_cases(base_url: str, cases: list[dict[str, object]], max_rank: int, sort_order: str) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()

        for case in cases:
            query = str(case["abstract"])
            search_url = f"{base_url}/search/?scope=abstract&q={quote_plus(query)}"
            if sort_order != "default":
                search_url += f"&sort={quote_plus(sort_order)}"

            page.goto(search_url, wait_until="networkidle")
            wait_for_results(page)
            page.wait_for_selector(".search-card", timeout=30000)
            first_page_titles = [text.strip() for text in page.locator(".search-card h3 a").all_inner_texts() if text.strip()]
            rank, titles_seen = collect_rank(page, str(case["journal"]), max_rank=max_rank)
            results.append({
                "journal": case["journal"],
                "pdf_path": str(case["pdf_path"]),
                "rank": rank,
                "first_page_titles": first_page_titles[:5],
                "titles_seen": titles_seen,
                "abstract_length": len(query),
            })

        browser.close()
    return results


def print_summary(results: list[dict[str, object]], max_rank: int, sort_order: str) -> int:
    found_ranks = [int(result["rank"]) for result in results if isinstance(result.get("rank"), int)]
    recall_at_1 = sum(1 for rank in found_ranks if rank <= 1) / len(results)
    recall_at_5 = sum(1 for rank in found_ranks if rank <= 5) / len(results)
    recall_at_10 = sum(1 for rank in found_ranks if rank <= 10) / len(results)
    recall_at_max = sum(1 for rank in found_ranks if rank <= max_rank) / len(results)
    mrr = sum((1 / rank) for rank in found_ranks) / len(results)
    mean_rank = sum(found_ranks) / len(found_ranks) if found_ranks else math.inf

    print(f"Benchmark cases used: {len(results)}")
    print(f"Sort order: {sort_order}")
    print(f"Recall@1: {recall_at_1:.3f}")
    print(f"Recall@5: {recall_at_5:.3f}")
    print(f"Recall@10: {recall_at_10:.3f}")
    print(f"Recall@{max_rank}: {recall_at_max:.3f}")
    print(f"MRR: {mrr:.3f}")
    if found_ranks:
        print(f"Mean rank (found cases): {mean_rank:.2f}")

    for result in results:
        rank_text = str(result["rank"]) if result["rank"] is not None else f">{max_rank}"
        print(
            f"- {result['journal']}: rank {rank_text} | abstract chars {result['abstract_length']} | "
            f"pdf {Path(str(result['pdf_path'])).name}"
        )
        print(f"  Top results: {', '.join(result['first_page_titles'])}")

    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark abstract-to-journal matching using local PDF references.")
    parser.add_argument("--refs-dir", type=Path, default=DEFAULT_REFS_DIR, help=f"Directory containing benchmark PDF references (default: {DEFAULT_REFS_DIR})")
    parser.add_argument("--max-rank", type=int, default=DEFAULT_MAX_RANK, help="Maximum rank depth to search for the target journal.")
    parser.add_argument("--sort", choices=["default", "fit_desc"], default="default", help="Result ordering to evaluate.")
    parser.add_argument("--pdf-text-limit", type=int, default=DEFAULT_PDF_TEXT_LIMIT, help="Maximum number of PDF characters to extract before parsing the abstract.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not MANIFEST_PATH.exists():
        raise SystemExit("Build output is missing. Run scripts/build_site.py first.")
    if not args.refs_dir.exists():
        raise SystemExit(f"Refs directory not found: {args.refs_dir}")

    dataset_titles = load_dataset_titles()
    cases = build_case_inputs(args.refs_dir, dataset_titles, max_chars=args.pdf_text_limit)
    if not cases:
        raise SystemExit("No benchmark cases could be constructed from the available PDF references.")

    with static_server(DOCS_DIR) as base_url:
        results = evaluate_cases(base_url, cases, max_rank=args.max_rank, sort_order=args.sort)

    return print_summary(results, max_rank=args.max_rank, sort_order=args.sort)


if __name__ == "__main__":
    sys.exit(main())
