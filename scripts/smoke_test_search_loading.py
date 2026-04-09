"""Dikembangkan oleh Ikhwan Arief (ikhwan[at]unand.ac.id)
Lisensi aplikasi: Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)
"""

from __future__ import annotations

import contextlib
import json
import re
import socketserver
import sys
import threading
import time
from collections import Counter
from functools import partial
from http.server import SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urljoin, urlparse

try:
    from playwright.sync_api import sync_playwright
except ImportError as error:
    raise SystemExit(
        "Playwright is not installed. Run: \n"
        '  python -m pip install -r requirements-dev.txt\n'
        '  python -m playwright install chromium'
    ) from error


REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = REPO_ROOT / "docs"
MANIFEST_PATH = DOCS_DIR / "data" / "search-manifest.json"
LONG_ABSTRACT_FIT_QUERY = " ".join(
    [f"syntheticterm{i:03d}" for i in range(1, 401)]
    + ["machine", "learning", "neural", "network", "ophthalmology", "fundus", "imaging", "diabetic", "retinopathy"]
)


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


def path_from_url(url: str) -> str:
    return urlparse(url).path.lstrip("/")


def normalize_text(value: str) -> str:
    lowered = (value or "").strip().lower()
    lowered = re.sub(r"[^a-z0-9]+", " ", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def load_all_records(manifest: dict[str, object]) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for relative_path in manifest.get("chunk_paths", []):
        payload = json.loads((DOCS_DIR / str(relative_path)).read_text(encoding="utf-8"))
        records.extend(payload.get("records", []))
    return records


def pick_subject_area_candidate(records: list[dict[str, object]]) -> dict[str, object] | None:
    sinta_records = [record for record in records if record.get("source_type") == "sinta" and record.get("subject_area")]
    counts = Counter(normalize_text(str(record.get("subject_area") or "")) for record in sinta_records)

    for record in sinta_records:
        subject_area = normalize_text(str(record.get("subject_area") or ""))
        if not subject_area:
            continue
        if counts[subject_area] != 1:
            continue
        if subject_area == normalize_text(str(record.get("title") or "")):
            continue
        return record

    return sinta_records[0] if sinta_records else None


def wait_for_chunk_set(page, observed_paths: list[str], expected_paths: set[str], timeout_seconds: float = 8.0) -> set[str]:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        current = {path for path in observed_paths if path.startswith("data/search-chunks/")}
        if current == expected_paths:
            return current
        page.wait_for_timeout(200)
    return {path for path in observed_paths if path.startswith("data/search-chunks/")}


def wait_for_results(page) -> None:
    page.wait_for_function(
        """() => {
            const text = document.querySelector('#results-count')?.textContent || '';
            return text.includes('matches found.');
        }""",
        timeout=20000,
    )


def configure_llm_runtime(page, llm_url: str, candidate_depth: int = 5, timeout_ms: int = 5000) -> None:
    config = json.dumps(
        {
            "llmApiBaseUrl": llm_url,
            "llmTimeoutMs": timeout_ms,
            "llmAbstractEnabled": True,
            "llmCandidateLimit": candidate_depth,
        }
    )
    page.add_init_script(
        script=f"""
            window.__JD_RUNTIME_CONFIG__ = {{
                ...(window.__JD_RUNTIME_CONFIG__ || {{}}),
                ...{config}
            }};
        """
    )


def disable_llm_runtime(page) -> None:
    config = json.dumps(
        {
            "llmApiBaseUrl": "",
            "llmTimeoutMs": 5000,
            "llmAbstractEnabled": False,
            "llmCandidateLimit": 50,
        }
    )
    page.add_init_script(
        script=f"""
            window.__JD_RUNTIME_CONFIG__ = {{
                ...(window.__JD_RUNTIME_CONFIG__ || {{}}),
                ...{config}
            }};
        """
    )


def new_smoke_page(browser):
    page = browser.new_page()
    disable_llm_runtime(page)
    return page


def fulfill_mock_llm_route(route, recorded_requests: list[dict[str, object]], mode: str) -> None:
    payload = json.loads(route.request.post_data or "{}")
    recorded_requests.append(
        {
            "path": urlparse(route.request.url).path,
            "payload": payload,
        }
    )

    if mode == "error":
        route.fulfill(
            status=503,
            content_type="application/json",
            body=json.dumps({"detail": "Mock LLM failure."}),
        )
        return

    if mode == "retry_success" and len(recorded_requests) == 1:
        route.fulfill(
            status=503,
            content_type="application/json",
            body=json.dumps({"detail": "Mock LLM cold start."}),
        )
        return

    candidates = list(payload.get("candidates", []))
    ranked = []
    for index, candidate in enumerate(reversed(candidates), start=1):
        ranked.append(
            {
                "sourceid": str(candidate.get("sourceid") or ""),
                "rank": index,
                "llm_score": max(0, 100 - index),
                "rationale": f"{candidate.get('title') or 'This journal'} aligns with the abstract scope.",
                "matched_fields": ["title", "areas"],
                "confidence": 0.84,
            }
        )

    route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps(
            {
                "mode": "llm_assisted",
                "model": "mock-llm",
                "latency_ms": 12,
                "ranked": ranked,
            }
        ),
    )


def submit_search(page, query: str, scope: str | None = None, sort: str | None = None) -> None:
    if scope is not None:
        page.select_option("#scope", scope)
    if sort is not None and page.locator("#sort-order").count():
        page.wait_for_function(
            """() => {
                const sortSelect = document.querySelector('#sort-order');
                return Boolean(sortSelect) && !sortSelect.disabled;
            }""",
            timeout=5000,
        )
        page.select_option("#sort-order", sort)
    page.fill("#q", query)
    page.click('button[type="submit"]')
    wait_for_results(page)


def parse_sjr(summary_text: str) -> float:
    match = re.search(r"SJR:\s*([0-9][0-9,]*)", summary_text)
    if not match:
        raise AssertionError(f"Could not parse SJR from summary text: {summary_text}")
    return float(match.group(1).replace(",", "."))


def main() -> int:
    if not MANIFEST_PATH.exists():
        raise SystemExit("Build output is missing. Run scripts/build_site.py first.")

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    all_records = load_all_records(manifest)
    first_chunk_path = DOCS_DIR / str((manifest.get("chunk_paths") or [""])[0])
    if not first_chunk_path.exists():
        raise SystemExit("Manifest does not contain a readable first chunk for legacy redirect testing.")
    first_record = next(
        (record for record in all_records if record.get("source_type") == "scimago"),
        {},
    )
    legacy_slug = str(first_record.get("slug") or "")
    legacy_sourceid = str(first_record.get("sourceid") or "")
    legacy_title = str(first_record.get("title") or "")

    expected_all = set(manifest.get("chunk_paths", []))
    prefix_paths = manifest.get("title_prefix_chunks", {})
    expected_a = set(prefix_paths.get("a", []))
    expected_j = set(prefix_paths.get("j", []))
    merged_indonesia_record = next(
        (
            record
            for record in all_records
            if record.get("source_type") == "scimago"
            and record.get("country") == "Indonesia"
            and record.get("accreditation")
            and record.get("scopus_indexed") is True
        ),
        None,
    )
    sinta_only_record = next(
        (
            record
            for record in all_records
            if record.get("source_type") == "sinta"
            and record.get("sinta_url")
            and record.get("subject_area")
        ),
        None,
    )
    subject_area_candidate = pick_subject_area_candidate(all_records)
    forbidden_public_keys = {
        "garuda_indexed",
        "sinta_impact",
        "sinta_h5_index",
        "sinta_citations_5yr",
        "sinta_citations_total",
    }
    if any(forbidden_public_keys & set(record) for record in all_records):
        raise SystemExit("Generated public search records expose forbidden SINTA metric or Garuda keys.")
    if not expected_all or not expected_a or not expected_j or not legacy_slug or not legacy_sourceid:
        raise SystemExit("Manifest does not contain the expected title-prefix shard mappings.")
    if not merged_indonesia_record:
        raise SystemExit("Expected at least one merged Indonesia record with accreditation and Scopus indexing.")
    if not sinta_only_record:
        raise SystemExit("Expected at least one SINTA-only record with subject area metadata.")
    if not subject_area_candidate:
        raise SystemExit("Expected at least one SINTA-only record suitable for subject-area abstract matching checks.")

    with static_server(DOCS_DIR) as base_url, sync_playwright() as playwright:
        browser = playwright.chromium.launch()

        home_page = new_smoke_page(browser)
        home_requests: list[str] = []
        home_page.on("requestfinished", lambda request: home_requests.append(path_from_url(request.url)))

        home_page.goto(f"{base_url}/", wait_until="networkidle")
        home_page.wait_for_selector("#search-form")
        home_page.wait_for_function(
            """() => document.querySelector('#results-section')?.hidden === true""",
            timeout=10000,
        )

        idle_home_chunks = {path for path in home_requests if path.startswith("data/search-chunks/")}
        if idle_home_chunks:
            raise AssertionError(f"Expected no shard requests on homepage idle load, got: {sorted(idle_home_chunks)}")
        if "data/search-manifest.json" not in home_requests:
            raise AssertionError("Expected the search manifest to load on homepage open.")
        if home_page.locator(".search-card").count() != 0:
            raise AssertionError("Expected homepage to start without rendered journal result cards.")

        home_page.fill("#q", "geotechnical geophysics environmental engineering water science")
        home_page.click('button[type="submit"]')
        wait_for_results(home_page)
        home_page.wait_for_function(
            """() => document.querySelector('#results-section')?.hidden === false""",
            timeout=10000,
        )
        if home_page.locator("#sort-order").count() != 1:
            raise AssertionError("Expected homepage abstract form to expose a sort control.")
        home_request_set = wait_for_chunk_set(home_page, home_requests, expected_all)
        if home_request_set != expected_all:
            raise AssertionError(
                f"Expected homepage abstract search to load all shards {sorted(expected_all)}, got {sorted(home_request_set)}"
            )
        if home_page.locator(".search-card").count() == 0:
            raise AssertionError("Expected homepage search to render at least one result card.")

        stopword_page = new_smoke_page(browser)
        stopword_requests: list[str] = []
        stopword_page.on("requestfinished", lambda request: stopword_requests.append(path_from_url(request.url)))

        stopword_page.goto(f"{base_url}/", wait_until="networkidle")
        stopword_page.wait_for_selector("#search-form")
        stopword_page.fill("#q", "the and of yang dan di")
        stopword_page.click('button[type="submit"]')
        stopword_page.wait_for_function(
            """() => {
                const text = document.querySelector('.empty-state')?.textContent || '';
                return text.includes('specific search terms');
            }""",
            timeout=10000,
        )
        stopword_chunks = {path for path in stopword_requests if path.startswith("data/search-chunks/")}
        if stopword_chunks:
            raise AssertionError(
                f"Expected stop-word-only homepage query to avoid shard requests, got: {sorted(stopword_chunks)}"
            )

        title_page = new_smoke_page(browser)
        title_requests: list[str] = []

        title_page.on("requestfinished", lambda request: title_requests.append(path_from_url(request.url)))

        title_page.goto(f"{base_url}/search/", wait_until="networkidle")
        title_page.wait_for_selector("#search-form")
        title_page.wait_for_function(
            """() => {
                const countryOptions = document.querySelectorAll('#country-filter option');
                return countryOptions.length > 1;
            }""",
            timeout=10000,
        )

        idle_chunks = {path for path in title_requests if path.startswith("data/search-chunks/")}
        if idle_chunks:
            raise AssertionError(f"Expected no shard requests on idle load, got: {sorted(idle_chunks)}")
        if "data/search-manifest.json" not in title_requests:
            raise AssertionError("Expected the search manifest to load on page open.")

        title_page.select_option("#scope", "title")
        title_page.wait_for_timeout(500)
        scope_only_chunks = {path for path in title_requests if path.startswith("data/search-chunks/")}
        if scope_only_chunks:
            raise AssertionError(
                f"Expected no shard requests after scope-only change, got: {sorted(scope_only_chunks)}"
            )

        submit_search(title_page, "acs")
        first_request_set = wait_for_chunk_set(title_page, title_requests, expected_a)
        if first_request_set != expected_a:
            raise AssertionError(
                f"Expected only prefix 'a' shards {sorted(expected_a)}, got {sorted(first_request_set)}"
            )

        before_second_query = set(first_request_set)
        submit_search(title_page, "journal")
        combined_expected = before_second_query | expected_j
        second_request_set = wait_for_chunk_set(title_page, title_requests, combined_expected)
        new_requests = second_request_set - before_second_query
        if new_requests != expected_j:
            raise AssertionError(
                f"Expected only prefix 'j' shards {sorted(expected_j)} on second search, got {sorted(new_requests)}"
            )

        metric_page = new_smoke_page(browser)
        metric_page.goto(f"{base_url}/search/", wait_until="networkidle")
        metric_page.wait_for_selector("#search-form")
        submit_search(metric_page, "cancer", scope="all")
        metric_page.wait_for_selector(".search-card", timeout=20000)
        metric_title = metric_page.locator(".search-card h3 a").first.inner_text().strip()
        if "cancer" not in metric_title.lower():
            raise AssertionError(f"Expected relevance-first cancer search to start with a cancer-titled journal, got: {metric_title}")

        filter_page = new_smoke_page(browser)
        filter_requests: list[str] = []

        filter_page.on("requestfinished", lambda request: filter_requests.append(path_from_url(request.url)))

        filter_page.goto(f"{base_url}/search/?index=doaj", wait_until="networkidle")
        filter_page.wait_for_selector("#search-form")
        wait_for_results(filter_page)
        full_request_set = wait_for_chunk_set(filter_page, filter_requests, expected_all)
        if full_request_set != expected_all:
            raise AssertionError(
                f"Expected deep-linked DOAJ filter to load all shards {sorted(expected_all)}, got {sorted(full_request_set)}"
            )

        results_count = filter_page.locator("#results-count").inner_text()
        if "matches found." not in results_count:
            raise AssertionError(f"Expected match count text after deep-linked filter load, got: {results_count}")

        accreditation_page = new_smoke_page(browser)
        accreditation_requests: list[str] = []
        accreditation_page.on("requestfinished", lambda request: accreditation_requests.append(path_from_url(request.url)))
        accreditation_page.goto(f"{base_url}/search/?accreditation=S1", wait_until="networkidle")
        accreditation_page.wait_for_selector("#search-form")
        wait_for_results(accreditation_page)
        accreditation_request_set = wait_for_chunk_set(accreditation_page, accreditation_requests, expected_all)
        if accreditation_request_set != expected_all:
            raise AssertionError(
                f"Expected deep-linked S1 accreditation filter to load all shards {sorted(expected_all)}, got {sorted(accreditation_request_set)}"
            )
        if accreditation_page.locator("#accreditation-filter").input_value() != "S1":
            raise AssertionError("Expected accreditation deep link to hydrate the accreditation filter.")

        submit_search(
            filter_page,
            "geotechnical geophysics environmental engineering water science",
            scope="abstract",
        )
        filter_page.wait_for_selector(".match-insight", timeout=20000)
        first_title = filter_page.locator(".search-card h3 a").first.inner_text()
        if not first_title.strip():
            raise AssertionError("Expected abstract search to render at least one result title.")

        long_lexical_page = new_smoke_page(browser)
        long_lexical_page.goto(f"{base_url}/search/", wait_until="networkidle")
        long_lexical_page.wait_for_selector("#search-form")
        submit_search(long_lexical_page, LONG_ABSTRACT_FIT_QUERY, scope="abstract")
        long_lexical_first_title = long_lexical_page.locator(".search-card h3 a").first.inner_text().strip()
        if not long_lexical_first_title:
            raise AssertionError("Expected long abstract lexical search to render a first result.")

        llm_success_page = new_smoke_page(browser)
        llm_success_requests: list[dict[str, object]] = []
        configure_llm_runtime(llm_success_page, base_url, candidate_depth=5)
        llm_success_page.route("**/v1/abstract-match", lambda route: fulfill_mock_llm_route(route, llm_success_requests, "success"))
        llm_success_page.goto(f"{base_url}/search/", wait_until="networkidle")
        llm_success_page.wait_for_selector("#search-form")
        if llm_success_page.locator("#llm-privacy-note").count() != 1 or llm_success_page.locator("#llm-privacy-note").is_hidden():
            raise AssertionError("Expected LLM-enabled runtime config to reveal the privacy note.")
        submit_search(
            llm_success_page,
            LONG_ABSTRACT_FIT_QUERY,
            scope="abstract",
        )
        llm_success_page.wait_for_selector(".llm-insight", timeout=20000)
        llm_status_text = llm_success_page.locator("#ranking-status").inner_text()
        if "LLM-assisted ranking" not in llm_status_text:
            raise AssertionError(f"Expected LLM success status, got: {llm_status_text}")
        llm_first_title = llm_success_page.locator(".search-card h3 a").first.inner_text().strip()
        if not llm_success_requests:
            raise AssertionError("Expected successful LLM rerank page to call the mock API.")
        if llm_first_title == long_lexical_first_title:
            raise AssertionError("Expected successful LLM rerank to reorder the first result relative to lexical ranking.")

        llm_fallback_page = new_smoke_page(browser)
        llm_error_requests: list[dict[str, object]] = []
        configure_llm_runtime(llm_fallback_page, base_url, candidate_depth=5)
        llm_fallback_page.route("**/v1/abstract-match", lambda route: fulfill_mock_llm_route(route, llm_error_requests, "error"))
        llm_fallback_page.goto(f"{base_url}/search/", wait_until="networkidle")
        llm_fallback_page.wait_for_selector("#search-form")
        submit_search(
            llm_fallback_page,
            LONG_ABSTRACT_FIT_QUERY,
            scope="abstract",
        )
        fallback_status_text = llm_fallback_page.locator("#ranking-status").inner_text()
        if "Lexical fallback" not in fallback_status_text:
            raise AssertionError(f"Expected lexical fallback status when the LLM API fails, got: {fallback_status_text}")
        if llm_fallback_page.locator(".llm-insight").count() != 0:
            raise AssertionError("Expected no LLM rationale cards when fallback ranking is used.")
        fallback_first_title = llm_fallback_page.locator(".search-card h3 a").first.inner_text().strip()
        if fallback_first_title != long_lexical_first_title:
            raise AssertionError("Expected fallback ranking to preserve the lexical first result.")
        if not llm_error_requests:
            raise AssertionError("Expected failing LLM rerank page to still attempt the mock API request.")

        llm_retry_page = new_smoke_page(browser)
        llm_retry_requests: list[dict[str, object]] = []
        configure_llm_runtime(llm_retry_page, base_url, candidate_depth=5, timeout_ms=12000)
        llm_retry_page.route("**/v1/abstract-match", lambda route: fulfill_mock_llm_route(route, llm_retry_requests, "retry_success"))
        llm_retry_page.goto(f"{base_url}/search/", wait_until="networkidle")
        llm_retry_page.wait_for_selector("#search-form")
        submit_search(
            llm_retry_page,
            LONG_ABSTRACT_FIT_QUERY,
            scope="abstract",
        )
        llm_retry_page.wait_for_selector(".llm-insight", timeout=20000)
        llm_retry_status_text = llm_retry_page.locator("#ranking-status").inner_text()
        if "LLM-assisted ranking" not in llm_retry_status_text:
            raise AssertionError(f"Expected retrying LLM rerank to recover successfully, got: {llm_retry_status_text}")
        if len(llm_retry_requests) != 2:
            raise AssertionError(f"Expected exactly two LLM API attempts for retry recovery, got: {len(llm_retry_requests)}")

        short_query_page = new_smoke_page(browser)
        configure_llm_runtime(short_query_page, base_url, candidate_depth=5)
        short_query_page.route("**/v1/abstract-match", lambda route: fulfill_mock_llm_route(route, llm_success_requests, "success"))
        short_query_page.goto(f"{base_url}/search/", wait_until="networkidle")
        short_query_page.wait_for_selector("#search-form")
        before_short_requests = len(llm_success_requests)
        submit_search(short_query_page, "machine learning water", scope="abstract")
        short_status_text = short_query_page.locator("#ranking-status").inner_text()
        if "Lexical fallback" not in short_status_text:
            raise AssertionError(f"Expected lexical fallback status for short abstract queries, got: {short_status_text}")
        if len(llm_success_requests) != before_short_requests:
            raise AssertionError("Expected short abstract queries to skip the LLM API.")

        merged_title_page = new_smoke_page(browser)
        merged_title_page.goto(f"{base_url}/search/", wait_until="networkidle")
        merged_title_page.wait_for_selector("#search-form")
        submit_search(merged_title_page, str(merged_indonesia_record["title"]), scope="title")
        merged_title_page.wait_for_selector(".search-card", timeout=20000)
        merged_result_title = merged_title_page.locator(".search-card h3 a").first.inner_text().strip()
        if merged_result_title != str(merged_indonesia_record["title"]):
            raise AssertionError(
                f"Expected merged Indonesia title search to start with {merged_indonesia_record['title']}, got: {merged_result_title}"
            )
        badge_text = merged_title_page.locator(".search-card .label-row").first.inner_text()
        if str(merged_indonesia_record["accreditation"]) not in badge_text:
            raise AssertionError(
                f"Expected merged Indonesia search result to show accreditation badge {merged_indonesia_record['accreditation']}, got: {badge_text!r}"
            )

        sort_switch_page = new_smoke_page(browser)
        sort_switch_page.goto(f"{base_url}/search/", wait_until="networkidle")
        sort_switch_page.wait_for_selector("#search-form")
        sort_switch_page.select_option("#sort-order", "fit_desc")
        sort_switch_page.wait_for_function(
            """() => {
                const scope = document.querySelector('#scope');
                const sort = document.querySelector('#sort-order');
                return scope?.value === 'abstract' && sort?.value === 'fit_desc';
            }""",
            timeout=10000,
        )

        long_fit_page = new_smoke_page(browser)
        long_fit_page.goto(f"{base_url}/search/", wait_until="networkidle")
        long_fit_page.wait_for_selector("#search-form")
        submit_search(long_fit_page, LONG_ABSTRACT_FIT_QUERY, scope="abstract")
        long_fit_page.wait_for_selector(".match-insight strong", timeout=20000)
        long_fit_page.select_option("#sort-order", "fit_desc")
        long_fit_page.wait_for_function(
            """() => new URLSearchParams(window.location.search).get('sort') === 'fit_desc'""",
            timeout=10000,
        )
        top_fit_labels = [text.strip() for text in long_fit_page.locator(".match-insight strong").all_inner_texts()[:5]]
        if not top_fit_labels:
            raise AssertionError("Expected long abstract search to render fit labels.")
        top_fit_values = []
        for label in top_fit_labels:
            match = re.search(r"Abstract fit:\s*(\d+)%", label)
            if not match:
                raise AssertionError(f"Expected a parsable fit label, got: {label}")
            top_fit_values.append(int(match.group(1)))
        if max(top_fit_values) <= 2:
            raise AssertionError(
                f"Expected long abstract top matches to exceed 2% fit, got labels: {top_fit_labels}"
            )
        if top_fit_values != sorted(top_fit_values, reverse=True):
            raise AssertionError(
                f"Expected fit-sorted abstract results to be ordered by descending fit percentage, got labels: {top_fit_labels}"
            )

        profile_href = filter_page.locator(".search-card h3 a").first.get_attribute("href")
        if not profile_href or "journal/?sourceid=" not in profile_href:
            raise AssertionError(f"Expected dynamic journal profile link, got: {profile_href}")

        profile_page = new_smoke_page(browser)
        profile_page.goto(urljoin(f"{base_url}/search/", profile_href), wait_until="networkidle")
        profile_page.wait_for_selector("h1", timeout=20000)
        profile_heading = profile_page.locator("h1").inner_text()
        if not profile_heading.strip() or profile_heading == "Journal Profile":
            raise AssertionError(f"Expected resolved journal profile title, got: {profile_heading}")

        merged_profile_page = new_smoke_page(browser)
        merged_profile_page.goto(
            f"{base_url}/journal/?sourceid={merged_indonesia_record['sourceid']}",
            wait_until="networkidle",
        )
        merged_profile_page.wait_for_selector("h1", timeout=20000)
        merged_profile_text = merged_profile_page.locator("#profile-root").inner_text()
        if f"Accredited at {merged_indonesia_record['accreditation']}" not in merged_profile_text:
            raise AssertionError("Expected merged Indonesia profile to render the accreditation/index highlight.")
        if "Indexed in Scopus" not in merged_profile_text:
            raise AssertionError("Expected merged Indonesia profile highlight to mention Scopus indexing.")

        sinta_profile_page = new_smoke_page(browser)
        sinta_profile_page.goto(
            f"{base_url}/journal/?sourceid={sinta_only_record['sourceid']}",
            wait_until="networkidle",
        )
        sinta_profile_page.wait_for_selector("h1", timeout=20000)
        sinta_profile_text = sinta_profile_page.locator("#profile-root").inner_text()
        if str(sinta_only_record["sourceid"]) not in sinta_profile_text or str(sinta_only_record["subject_area"]) not in sinta_profile_text:
            raise AssertionError("Expected SINTA-only profile to render non-metric SINTA details.")
        for forbidden_label in ("Garuda", "H5-index", "Citations 5yr", "Citations", "Impact"):
            if forbidden_label in sinta_profile_text:
                raise AssertionError(f"Expected SINTA-only profile to hide forbidden metric label: {forbidden_label}")

        subject_area_page = new_smoke_page(browser)
        subject_area_page.goto(f"{base_url}/search/", wait_until="networkidle")
        subject_area_page.wait_for_selector("#search-form")
        submit_search(subject_area_page, str(subject_area_candidate["subject_area"]), scope="abstract", sort="fit_desc")
        subject_titles = [text.strip() for text in subject_area_page.locator(".search-card h3 a").all_inner_texts()]
        if str(subject_area_candidate["title"]).strip() not in subject_titles:
            raise AssertionError(
                "Expected abstract matching over SINTA subject area to surface the selected SINTA-only journal on the first page."
            )

        legacy_page = new_smoke_page(browser)
        legacy_page.goto(f"{base_url}/journals/{legacy_slug}/", wait_until="networkidle")
        legacy_page.wait_for_url(f"**/journal/?sourceid={legacy_sourceid}", timeout=20000)
        legacy_heading = legacy_page.locator("h1").inner_text()
        if legacy_heading.strip() != legacy_title:
            raise AssertionError(
                f"Expected legacy journal URL to redirect to {legacy_title}, got: {legacy_heading}"
            )

        browser.close()

    print(
        "Smoke test passed: homepage stayed search-first on idle load, homepage abstract search rendered results, the homepage exposed abstract-fit sorting, stop-word-only homepage queries avoided shard loads, scope-only changes on the advanced search page avoided shard loads, title searches fetched only the expected shards, relevance-first keyword ranking surfaced a cancer-titled journal, deep-linked index and accreditation filters loaded the full dataset, merged Indonesia results showed accreditation badges, abstract matching rendered insight UI, successful LLM reranking changed the first result and showed rationale/status UI, failed LLM reranking fell back cleanly to lexical ranking, short abstract queries skipped the LLM API, advanced search auto-switched to abstract scope when fit sorting was selected, long abstract top matches exceeded 2% fit labels and respected descending fit sorting after re-sorting, merged Indonesia and SINTA-only profiles rendered the expected non-metric status details, SINTA subject area influenced abstract matching, the dynamic journal profile page resolved correctly, and legacy journal URLs redirected to the new runtime profile path."
    )
    print(f"Prefix 'a' shards: {sorted(expected_a)}")
    print(f"Prefix 'j' shards: {sorted(expected_j)}")
    print(f"All shards for filter-based loading: {sorted(expected_all)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
