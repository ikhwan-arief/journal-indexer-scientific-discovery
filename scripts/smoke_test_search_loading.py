from __future__ import annotations

import contextlib
import json
import re
import socketserver
import sys
import threading
import time
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
    first_chunk_path = DOCS_DIR / str((manifest.get("chunk_paths") or [""])[0])
    if not first_chunk_path.exists():
        raise SystemExit("Manifest does not contain a readable first chunk for legacy redirect testing.")
    first_chunk = json.loads(first_chunk_path.read_text(encoding="utf-8"))
    first_record = (first_chunk.get("records") or [{}])[0]
    legacy_slug = str(first_record.get("slug") or "")
    legacy_sourceid = str(first_record.get("sourceid") or "")
    legacy_title = str(first_record.get("title") or "")

    expected_all = set(manifest.get("chunk_paths", []))
    prefix_paths = manifest.get("title_prefix_chunks", {})
    expected_a = set(prefix_paths.get("a", []))
    expected_j = set(prefix_paths.get("j", []))
    if not expected_all or not expected_a or not expected_j or not legacy_slug or not legacy_sourceid:
        raise SystemExit("Manifest does not contain the expected title-prefix shard mappings.")

    with static_server(DOCS_DIR) as base_url, sync_playwright() as playwright:
        browser = playwright.chromium.launch()

        home_page = browser.new_page()
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

        stopword_page = browser.new_page()
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

        title_page = browser.new_page()
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

        metric_page = browser.new_page()
        metric_page.goto(f"{base_url}/search/", wait_until="networkidle")
        metric_page.wait_for_selector("#search-form")
        submit_search(metric_page, "cancer", scope="all")
        metric_page.wait_for_selector(".search-card", timeout=20000)
        metric_title = metric_page.locator(".search-card h3 a").first.inner_text().strip()
        if metric_title != "Ca-A Cancer Journal for Clinicians":
            raise AssertionError(f"Expected metric-sorted cancer search to start with Ca-A Cancer Journal for Clinicians, got: {metric_title}")
        first_summary = metric_page.locator(".result-summary").nth(0).inner_text()
        second_summary = metric_page.locator(".result-summary").nth(1).inner_text()
        if parse_sjr(first_summary) < parse_sjr(second_summary):
            raise AssertionError(
                f"Expected descending SJR order for cancer search, got first two summaries: {first_summary!r} and {second_summary!r}"
            )

        filter_page = browser.new_page()
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

        submit_search(
            filter_page,
            "geotechnical geophysics environmental engineering water science",
            scope="abstract",
        )
        filter_page.wait_for_selector(".match-insight", timeout=20000)
        first_title = filter_page.locator(".search-card h3 a").first.inner_text()
        if not first_title.strip():
            raise AssertionError("Expected abstract search to render at least one result title.")

        sort_switch_page = browser.new_page()
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

        long_fit_page = browser.new_page()
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

        profile_page = browser.new_page()
        profile_page.goto(urljoin(f"{base_url}/search/", profile_href), wait_until="networkidle")
        profile_page.wait_for_selector("h1", timeout=20000)
        profile_heading = profile_page.locator("h1").inner_text()
        if not profile_heading.strip() or profile_heading == "Journal Profile":
            raise AssertionError(f"Expected resolved journal profile title, got: {profile_heading}")

        legacy_page = browser.new_page()
        legacy_page.goto(f"{base_url}/journals/{legacy_slug}/", wait_until="networkidle")
        legacy_page.wait_for_url(f"**/journal/?sourceid={legacy_sourceid}", timeout=20000)
        legacy_heading = legacy_page.locator("h1").inner_text()
        if legacy_heading.strip() != legacy_title:
            raise AssertionError(
                f"Expected legacy journal URL to redirect to {legacy_title}, got: {legacy_heading}"
            )

        browser.close()

    print(
        "Smoke test passed: homepage stayed search-first on idle load, homepage abstract search rendered results, the homepage exposed abstract-fit sorting, stop-word-only homepage queries avoided shard loads, scope-only changes on the advanced search page avoided shard loads, title searches fetched only the expected shards, metric-based sorting ordered cancer results by descending SJR, deep-linked filters loaded the full dataset, abstract matching rendered insight UI, advanced search auto-switched to abstract scope when fit sorting was selected, long abstract top matches exceeded 2% fit labels and respected descending fit sorting after re-sorting, the dynamic journal profile page resolved correctly, and legacy journal URLs redirected to the new runtime profile path."
    )
    print(f"Prefix 'a' shards: {sorted(expected_a)}")
    print(f"Prefix 'j' shards: {sorted(expected_j)}")
    print(f"All shards for filter-based loading: {sorted(expected_all)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
