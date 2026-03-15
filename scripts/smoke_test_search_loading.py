from __future__ import annotations

import contextlib
import json
import socketserver
import sys
import threading
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse

try:
    from playwright.sync_api import sync_playwright
except ImportError as error:
    raise SystemExit(
        "Playwright is not installed. Run: \n"
        '  "/Users/ikhwanarief/Documents/GitHub Repositories/.venv/bin/python" -m pip install -r requirements-dev.txt\n'
        '  "/Users/ikhwanarief/Documents/GitHub Repositories/.venv/bin/python" -m playwright install chromium'
    ) from error


REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = REPO_ROOT / "docs"
MANIFEST_PATH = DOCS_DIR / "data" / "search-manifest.json"


class QuietRequestHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        return


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


def submit_search(page, query: str, scope: str | None = None) -> None:
    if scope is not None:
        page.select_option("#scope", scope)
    page.fill("#q", query)
    page.click('button[type="submit"]')
    wait_for_results(page)


def main() -> int:
    if not MANIFEST_PATH.exists():
        raise SystemExit("Build output is missing. Run scripts/build_site.py first.")

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    expected_all = set(manifest.get("chunk_paths", []))
    prefix_paths = manifest.get("title_prefix_chunks", {})
    expected_a = set(prefix_paths.get("a", []))
    expected_j = set(prefix_paths.get("j", []))
    if not expected_all or not expected_a or not expected_j:
        raise SystemExit("Manifest does not contain the expected title-prefix shard mappings.")

    with static_server(DOCS_DIR) as base_url, sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        title_page = browser.new_page()
        title_requests: list[str] = []

        title_page.on("requestfinished", lambda request: title_requests.append(path_from_url(request.url)))

        title_page.goto(f"{base_url}/search/", wait_until="networkidle")
        title_page.wait_for_selector("#search-form")
        title_page.wait_for_function(
            """() => {
                const text = document.querySelector('.empty-state strong')?.textContent || '';
                return text.includes('Search dataset is ready on demand.');
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

        browser.close()

    print(
        "Smoke test passed: idle search stayed idle, scope-only changes avoided shard loads, title searches fetched only the expected shards, deep-linked filters loaded the full dataset, and abstract matching rendered insight UI."
    )
    print(f"Prefix 'a' shards: {sorted(expected_a)}")
    print(f"Prefix 'j' shards: {sorted(expected_j)}")
    print(f"All shards for filter-based loading: {sorted(expected_all)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())