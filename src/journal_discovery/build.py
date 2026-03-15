from __future__ import annotations

import csv
import html
import json
import os
import re
import shutil
import sqlite3
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable
from urllib.parse import quote_plus

SEARCH_CHUNK_SIZE = 2000

ROOT_DIR = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT_DIR / "data" / "raw"
BUILD_DIR = ROOT_DIR / "build"
DOCS_DIR = ROOT_DIR / "docs"
ASSET_DIR = Path(__file__).resolve().parent / "assets"
MAIN_CSV = RAW_DIR / "scimagojr 2024.csv"
WOS_CSV = RAW_DIR / "scimagojr 2024_WoS.csv"
DOAJ_CSV = RAW_DIR / "doaj.csv"
DEFAULT_SITE_URL = os.getenv("SITE_URL", "").rstrip("/")


@dataclass(slots=True)
class JournalRecord:
    rank: int
    sourceid: str
    title: str
    publisher: str | None
    country: str | None
    region: str | None
    issns: list[str]
    coverage: str | None
    categories: str | None
    areas: str | None
    sjr_quartile: str | None
    sjr_best_quartile: str | None
    scopus_indexed: bool
    wos_indexed: bool
    doaj_indexed: bool
    journal_url: str | None
    apc_status: str | None
    license: str | None
    author_holds_copyright: str | None
    open_access: str | None
    open_access_diamond: str | None
    slug: str
    normalized_title: str
    normalized_publisher: str
    normalized_country: str
    normalized_url: str

    @property
    def profile_path(self) -> str:
        return f"journals/{self.slug}/"

    @property
    def index_summary(self) -> str:
        labels: list[str] = []
        if self.scopus_indexed:
            labels.append("Scopus")
        if self.wos_indexed:
            labels.append("WoS")
        if self.doaj_indexed:
            labels.append("DOAJ")
        return ", ".join(labels) if labels else "Tidak tersedia"

    @property
    def search_text(self) -> str:
        parts = [
            self.normalized_title,
            self.normalized_publisher,
            self.normalized_country,
            self.normalized_url,
            normalize_text(self.index_summary),
            normalize_text(self.categories or ""),
            normalize_text(self.areas or ""),
            normalize_text(" ".join(self.issns)),
        ]
        return " ".join(part for part in parts if part).strip()

    def to_home_dict(self) -> dict[str, object]:
        return {
            "rank": self.rank,
            "sourceid": self.sourceid,
            "title": self.title,
            "publisher": self.publisher,
            "country": self.country,
        "categories": self.categories,
        "areas": self.areas,
            "sjr_quartile": self.sjr_quartile,
            "wos_indexed": self.wos_indexed,
            "doaj_indexed": self.doaj_indexed,
            "journal_url": self.journal_url,
            "slug": self.slug,
        }

    def to_search_dict(self) -> dict[str, object]:
        return {
            "rank": self.rank,
            "sourceid": self.sourceid,
            "title": self.title,
            "publisher": self.publisher,
            "country": self.country,
            "region": self.region,
            "issns": self.issns,
            "coverage": self.coverage,
            "categories": self.categories,
            "areas": self.areas,
            "sjr_quartile": self.sjr_quartile,
            "sjr_best_quartile": self.sjr_best_quartile,
            "wos_indexed": self.wos_indexed,
            "doaj_indexed": self.doaj_indexed,
            "journal_url": self.journal_url,
            "apc_status": self.apc_status,
            "license": self.license,
            "author_holds_copyright": self.author_holds_copyright,
            "open_access": self.open_access,
            "open_access_diamond": self.open_access_diamond,
            "slug": self.slug,
        }


@dataclass(slots=True)
class SiteSummary:
    total_journals: int
    total_scopus: int
    total_wos: int
    total_doaj: int
    total_with_quartile: int
    total_missing_websites: int
    generated_at: str


@dataclass(slots=True)
class SearchManifest:
  summary: SiteSummary
  countries: list[str]
  chunk_paths: list[str]
  title_prefix_chunks: dict[str, list[str]]


@dataclass(slots=True)
class DoajRecord:
    title: str
    normalized_title: str
    issns: list[str]
    journal_url: str | None
    apc_status: str | None
    license: str | None
    author_holds_copyright: str | None


def normalize_text(value: str) -> str:
    lowered = (value or "").strip().lower()
    lowered = re.sub(r"[^a-z0-9]+", " ", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def search_prefix(value: str) -> str:
  normalized = normalize_text(value)
  return normalized[0] if normalized else "#"


def normalize_issns(raw_value: str) -> list[str]:
    values: list[str] = []
    for part in (raw_value or "").split(","):
        cleaned = re.sub(r"[^0-9xX]", "", part)
        if cleaned:
            values.append(cleaned.upper())
    return sorted(dict.fromkeys(values))


def slugify(title: str, sourceid: str) -> str:
    base = normalize_text(title).replace(" ", "-")
    base = re.sub(r"-+", "-", base).strip("-") or "journal"
    return f"{base}-{sourceid}"


def safe_url(raw_url: str | None) -> str | None:
    value = (raw_url or "").strip()
    if not value:
        return None
    if value.startswith("http://") or value.startswith("https://"):
        return value
    return None


def normalize_yes_no(value: str | None) -> str | None:
    cleaned = (value or "").strip().lower()
    if cleaned == "yes":
        return "Yes"
    if cleaned == "no":
        return "No"
    return (value or "").strip() or None


def build_apc_status(value: str | None, amount: str | None) -> str | None:
    apc_value = normalize_yes_no(value)
    apc_amount = (amount or "").strip()
    if apc_value == "No":
        return "No APC"
    if apc_value == "Yes":
        return f"APC charged ({apc_amount})" if apc_amount else "APC charged"
    return None


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=";")
        return list(reader)


def read_doaj_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader)


def load_wos_sourceids(path: Path) -> set[str]:
    sourceids: set[str] = set()
    for row in read_csv_rows(path):
        sourceid = (row.get("Sourceid") or "").strip()
        if sourceid:
            sourceids.add(sourceid)
    return sourceids


def load_doaj_lookups(path: Path) -> tuple[dict[str, DoajRecord], dict[str, DoajRecord]]:
    if not path.exists():
        return {}, {}

    issn_lookup: dict[str, DoajRecord] = {}
    title_groups: dict[str, list[DoajRecord]] = {}

    for row in read_doaj_rows(path):
        title = (row.get("Journal title") or "").strip()
        normalized_title = normalize_text(title)
        issns = normalize_issns(
            ",".join(
                value
                for value in (
                    row.get("Journal ISSN (print version)"),
                    row.get("Journal EISSN (online version)"),
                )
                if value
            )
        )
        if not normalized_title and not issns:
            continue

        doaj_record = DoajRecord(
            title=title,
            normalized_title=normalized_title,
            issns=issns,
            journal_url=safe_url(row.get("Journal URL")),
            apc_status=build_apc_status(row.get("APC"), row.get("APC amount")),
            license=(row.get("Journal license") or "").strip() or None,
            author_holds_copyright=normalize_yes_no(
                row.get("Author holds copyright without restrictions")
            ),
        )

        for issn in issns:
            issn_lookup.setdefault(issn, doaj_record)

        if normalized_title:
            title_groups.setdefault(normalized_title, []).append(doaj_record)

    unique_title_lookup = {
        normalized_title: records[0]
        for normalized_title, records in title_groups.items()
        if len(records) == 1
    }
    return issn_lookup, unique_title_lookup


def match_doaj_record(
  title: str,
  issns: list[str],
  issn_lookup: dict[str, DoajRecord],
  title_lookup: dict[str, DoajRecord],
) -> DoajRecord | None:
  for issn in issns:
    match = issn_lookup.get(issn)
    if match:
      return match
  return title_lookup.get(normalize_text(title))


def build_records() -> list[JournalRecord]:
    if not MAIN_CSV.exists():
        raise FileNotFoundError(f"Missing source dataset: {MAIN_CSV}")
    if not WOS_CSV.exists():
        raise FileNotFoundError(f"Missing source dataset: {WOS_CSV}")

    wos_sourceids = load_wos_sourceids(WOS_CSV)
    doaj_issn_lookup, doaj_title_lookup = load_doaj_lookups(DOAJ_CSV)
    records: list[JournalRecord] = []
    for row in read_csv_rows(MAIN_CSV):
        if (row.get("Type") or "").strip().lower() != "journal":
            continue
        sourceid = (row.get("Sourceid") or "").strip()
        title = (row.get("Title") or "").strip()
        if not sourceid or not title:
            continue
        quartile = (row.get("SJR Best Quartile") or "").strip() or None
        issns = normalize_issns(row.get("Issn") or "")
        doaj_record = match_doaj_record(title, issns, doaj_issn_lookup, doaj_title_lookup)
        record = JournalRecord(
            rank=int((row.get("Rank") or "0").strip() or 0),
            sourceid=sourceid,
            title=title,
            publisher=(row.get("Publisher") or "").strip() or None,
            country=(row.get("Country") or "").strip() or None,
            region=(row.get("Region") or "").strip() or None,
          issns=issns,
            coverage=(row.get("Coverage") or "").strip() or None,
            categories=(row.get("Categories") or "").strip() or None,
            areas=(row.get("Areas") or "").strip() or None,
            sjr_quartile=quartile,
            sjr_best_quartile=quartile,
            scopus_indexed=True,
            wos_indexed=sourceid in wos_sourceids,
          doaj_indexed=doaj_record is not None,
          journal_url=doaj_record.journal_url if doaj_record else None,
          apc_status=doaj_record.apc_status if doaj_record else None,
          license=doaj_record.license if doaj_record else None,
          author_holds_copyright=doaj_record.author_holds_copyright if doaj_record else None,
            open_access=(row.get("Open Access") or "").strip() or None,
            open_access_diamond=(row.get("Open Access Diamond") or "").strip() or None,
            slug=slugify(title, sourceid),
            normalized_title=normalize_text(title),
            normalized_publisher=normalize_text((row.get("Publisher") or "")),
            normalized_country=normalize_text((row.get("Country") or "")),
          normalized_url=normalize_text(doaj_record.journal_url or "") if doaj_record else "",
        )
        records.append(record)

    records.sort(key=lambda record: (record.rank, record.title))
    return records


def build_summary(records: Iterable[JournalRecord]) -> SiteSummary:
    record_list = list(records)
    return SiteSummary(
        total_journals=len(record_list),
        total_scopus=sum(1 for record in record_list if record.scopus_indexed),
        total_wos=sum(1 for record in record_list if record.wos_indexed),
        total_doaj=sum(1 for record in record_list if record.doaj_indexed),
        total_with_quartile=sum(1 for record in record_list if record.sjr_quartile),
        total_missing_websites=sum(1 for record in record_list if not record.journal_url),
        generated_at=datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
    )


def reset_output_dirs() -> None:
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    if DOCS_DIR.exists():
        shutil.rmtree(DOCS_DIR)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    for relative in ("assets", "data", "journals", "search"):
        (DOCS_DIR / relative).mkdir(parents=True, exist_ok=True)


def init_database(records: Iterable[JournalRecord]) -> Path:
    database_path = BUILD_DIR / "journal_discovery.db"
    if database_path.exists():
        database_path.unlink()

    connection = sqlite3.connect(database_path)
    try:
        connection.executescript(
            """
            CREATE TABLE journals (
                sourceid TEXT PRIMARY KEY,
                rank INTEGER NOT NULL,
                title TEXT NOT NULL,
                slug TEXT NOT NULL,
                publisher TEXT,
                country TEXT,
                region TEXT,
                issns TEXT,
                coverage TEXT,
                categories TEXT,
                areas TEXT,
                sjr_quartile TEXT,
                sjr_best_quartile TEXT,
                scopus_indexed INTEGER NOT NULL,
                wos_indexed INTEGER NOT NULL,
                doaj_indexed INTEGER NOT NULL,
                journal_url TEXT,
                apc_status TEXT,
                license TEXT,
                author_holds_copyright TEXT,
                open_access TEXT,
                open_access_diamond TEXT,
                normalized_title TEXT,
                normalized_publisher TEXT,
                normalized_country TEXT,
                normalized_url TEXT,
                search_text TEXT NOT NULL
            );
            CREATE INDEX idx_journals_rank ON journals(rank);
            CREATE INDEX idx_journals_title ON journals(normalized_title);
            CREATE INDEX idx_journals_country ON journals(normalized_country);
            CREATE INDEX idx_journals_wos ON journals(wos_indexed);
            """
        )
        connection.executemany(
            """
            INSERT INTO journals (
                sourceid, rank, title, slug, publisher, country, region, issns, coverage,
                categories, areas, sjr_quartile, sjr_best_quartile, scopus_indexed,
                wos_indexed, doaj_indexed, journal_url, apc_status, license,
                author_holds_copyright, open_access, open_access_diamond,
                normalized_title, normalized_publisher, normalized_country,
                normalized_url, search_text
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    record.sourceid,
                    record.rank,
                    record.title,
                    record.slug,
                    record.publisher,
                    record.country,
                    record.region,
                    ", ".join(record.issns),
                    record.coverage,
                    record.categories,
                    record.areas,
                    record.sjr_quartile,
                    record.sjr_best_quartile,
                    int(record.scopus_indexed),
                    int(record.wos_indexed),
                    int(record.doaj_indexed),
                    record.journal_url,
                    record.apc_status,
                    record.license,
                    record.author_holds_copyright,
                    record.open_access,
                    record.open_access_diamond,
                    record.normalized_title,
                    record.normalized_publisher,
                    record.normalized_country,
                    record.normalized_url,
                    record.search_text,
                )
                for record in records
            ],
        )
        connection.commit()
    finally:
        connection.close()
    return database_path


def copy_assets() -> None:
    shutil.copy2(ASSET_DIR / "styles.css", DOCS_DIR / "assets" / "styles.css")
    shutil.copy2(ASSET_DIR / "app.js", DOCS_DIR / "assets" / "app.js")
    (DOCS_DIR / ".nojekyll").write_text("", encoding="utf-8")


def relative_href(site_root: str, relative_path: str) -> str:
    if site_root == ".":
        return relative_path
    return f"{site_root}/{relative_path}"


def page_url(site_root: str, relative_path: str) -> str:
    target = relative_href(site_root, relative_path)
    return html.escape(target, quote=True)


def maybe_canonical(relative_path: str) -> str:
    if not DEFAULT_SITE_URL:
        return ""
    full_url = f"{DEFAULT_SITE_URL}/{relative_path.lstrip('/')}"
    return f'<link rel="canonical" href="{html.escape(full_url, quote=True)}">'


def render_index_labels(record: JournalRecord) -> str:
    labels: list[str] = []
    if record.scopus_indexed:
        labels.append('<span class="label label-scopus">Scopus</span>')
    if record.wos_indexed:
        labels.append('<span class="label label-wos">WoS</span>')
    if record.doaj_indexed:
        labels.append('<span class="label label-doaj">DOAJ</span>')
    if record.sjr_best_quartile:
        labels.append(f'<span class="label label-quartile">{html.escape(record.sjr_best_quartile)}</span>')
    return "".join(labels)


def render_initial_rows(records: list[JournalRecord]) -> str:
    rows: list[str] = []
    for record in records[:10]:
        href = record.journal_url or record.profile_path
        external_attrs = ' target="_blank" rel="noopener noreferrer"' if record.journal_url else ""
        index_labels = ['<span class="label label-scopus">Scopus</span>']
        if record.wos_indexed:
            index_labels.append('<span class="label label-wos">WoS</span>')
        if record.doaj_indexed:
            index_labels.append('<span class="label label-doaj">DOAJ</span>')
        rows.append(
            f"""
            <tr>
              <td>
                <div class=\"table-title\">
                  <a href=\"{html.escape(href, quote=True)}\"{external_attrs}>{html.escape(record.title)}</a>
                </div>
              </td>
              <td>
                <div class=\"table-publisher\" title=\"{html.escape(record.publisher or 'Not available', quote=True)}\">{html.escape(record.publisher or 'Not available')}</div>
                <div class=\"mini-meta\" title=\"{html.escape(record.country or 'Country not available', quote=True)}\">{html.escape(record.country or 'Country not available')}</div>
              </td>
              <td>
                <div class=\"topic-stack\">
                  <div class=\"topic-primary\" title=\"{html.escape(record.areas or 'Area not available', quote=True)}\">{html.escape(record.areas or 'Area not available')}</div>
                  <div class=\"topic-secondary\" title=\"{html.escape(record.categories or 'Categories not available', quote=True)}\">{html.escape(record.categories or 'Categories not available')}</div>
                </div>
              </td>
              <td><div class=\"status-row\">{''.join(index_labels)}</div></td>
              <td><span class=\"pill pill-quartile\">{html.escape(record.sjr_quartile or '—')}</span></td>
              <td><a class=\"table-action-link\" href=\"{html.escape(record.profile_path, quote=True)}\" title=\"Open journal profile for {html.escape(record.title, quote=True)}\">View profile</a></td>
            </tr>
            """.strip()
        )
    return "\n".join(rows)


def home_page_html(records: list[JournalRecord], summary: SiteSummary) -> str:
    return f"""<!doctype html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\">
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
    <title>Journal Discovery | Match journal profiles from article abstracts</title>
    <meta name=\"description\" content=\"Search and browse journal discovery data built from Scimago Journal Rank 2024, with abstract-to-journal matching based on journal categories and areas.\">
    <meta name=\"robots\" content=\"index,follow\">
    <meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'\">
    {maybe_canonical('')}
    <link rel=\"stylesheet\" href=\"assets/styles.css\">
    <script defer src=\"assets/app.js\"></script>
  </head>
  <body data-page=\"home\" data-site-root=\".\" data-data-url=\"data/home.json\">
    <a class=\"skip-link\" href=\"#main\">Skip to content</a>
    <header class=\"site-header\">
      <div class=\"shell\">
        <a class=\"brand\" href=\"./\">
          <span class=\"brand-mark\">Journal Discovery</span>
          <span class=\"brand-subtitle\">Journal explorer based on abstract and keyword search</span>
        </a>
        <nav class=\"top-nav\" aria-label=\"Primary\">
          <a href=\"./\">Browse journals</a>
          <a href=\"search/\">Search profiles</a>
        </nav>
      </div>
    </header>
    <main id=\"main\">
      <section class=\"hero\">
        <div class=\"shell\">
          <div class=\"hero-panel\">
            <h1>Find journals by title, keyword, URL fragment, or article abstract.</h1>
              <p class=\"hero-copy\">Paste an article abstract below and the app will rank journals by how closely the abstract aligns with the journal <strong>Categories</strong> and <strong>Areas</strong>.</p>
            <form class=\"abstract-search-form\" action=\"search/\" method=\"get\">
              <input type=\"hidden\" name=\"scope\" value=\"abstract\">
              <label class=\"field abstract-field\" for=\"abstract-query\">
                <span>Paste article abstract</span>
                <textarea id=\"abstract-query\" name=\"q\" rows=\"8\" placeholder=\"Paste the article's abstract here. The app will match it to journal categories and areas, then suggest the suitable journals based on the abstract's words and sentences.\"></textarea>
              </label>
              <div class=\"hero-actions\">
                <button type=\"submit\">Find matching journals</button>
                <a class=\"button button-secondary\" href=\"search/\">Open advanced search</a>
              </div>
            </form>
            <div class=\"hero-actions\">
              <a class=\"button button-primary\" href=\"search/\">Open search experience</a>
              <a class=\"button button-secondary\" href=\"#journal-table\">Browse all journals</a>
            </div>
          </div>
        </div>
      </section>
      <section class=\"section\">
        <div class=\"shell\" id=\"app-error\"></div>
        <div class=\"shell\">
          <div class="section-heading section-heading-results">
            <div>
              <p class="eyebrow results-eyebrow">Journal directory</p>
              <h2>Browse verified journal profiles</h2>
              <p class=\"table-note\">The check symbols mark whether the journal exists in the Scopus, the WoS, and the DOAJ when available. The SJR column uses the available <strong>SJR Best Quartile</strong> field from the source dataset.</p>
            </div>
            <div class=\"table-chip\" id=\"home-summary\">Preparing journal table…</div>
          </div>
          <div class=\"table-card\">
            <div class=\"table-controls\">
              <div class="table-filter-pills">
                <span class="table-pill">Scopus baseline</span>
                <span class="table-pill">WoS cross-check</span>
                <span class="table-pill">DOAJ flag when available</span>
              </div>
              <a class="button button-secondary table-cta-button" href="search/">Open advanced search</a>
              <div class=\"table-chip\"><strong>10 journals</strong> per page</div>
            </div>
            <div class=\"table-wrap\">
              <table id=\"journal-table\">
                <thead>
                  <tr>
                    <th>Journal title</th>
                    <th>Publisher</th>
                    <th>Focus areas</th>
                    <th>Indexed in</th>
                    <th>SJR quartile</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody id=\"journal-table-body\">
                  {render_initial_rows(records)}
                </tbody>
              </table>
            </div>
            <div class=\"pagination\">
              <div class=\"pagination-info\" id=\"pagination-info\">Loading pagination…</div>
              <div class=\"pagination-list\" id=\"pagination-list\"></div>
            </div>
          </div>
        </div>
      </section>
    </main>
    <footer class=\"site-footer\">
      <div class=\"shell footer-grid\">
        <div class=\"footer-note\">Created by Ikhwan Arief (ikhwan@eng.unand.ac.id). Licensed for use under CC BY-NC.</div>
        <div class=\"footer-note\">Data sources: Scopus, Scimago Journal Rank (SJR), and DOAJ.</div>
      </div>
    </footer>
  </body>
</html>
"""


def search_page_html(summary: SiteSummary) -> str:
    return f"""<!doctype html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\">
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
    <title>Search Journal Profiles | Journal Discovery</title>
    <meta name=\"description\" content=\"Search journal profiles by abstract, keyword, full title, publisher, URL fragment, country, indexing status, or SJR quartile.\">
    <meta name=\"robots\" content=\"index,follow\">
    <meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'\">
    {maybe_canonical('search/')}
    <link rel=\"stylesheet\" href=\"../assets/styles.css\">
    <script defer src=\"../assets/app.js\"></script>
  </head>
  <body data-page=\"search\" data-site-root=\"..\" data-data-url=\"../data/search-manifest.json\">
    <a class=\"skip-link\" href=\"#main\">Skip to content</a>
    <header class=\"site-header\">
      <div class=\"shell\">
        <a class=\"brand\" href=\"../\">
          <span class=\"brand-mark\">Journal Discovery</span>
          <span class=\"brand-subtitle\">Search-first journal profile explorer</span>
        </a>
        <nav class=\"top-nav\" aria-label=\"Primary\">
          <a href=\"../\">Browse journals</a>
          <a href=\"./\">Search profiles</a>
        </nav>
      </div>
    </header>
    <main id=\"main\">
      <section class=\"hero\">
        <div class=\"shell\">
          <div class=\"hero-panel\">
            <p class=\"eyebrow\">Profile search</p>
            <h1>Search journal profiles with filters that match how users actually ask.</h1>
            <p class=\"hero-copy\">Use a full article abstract, free keywords, an exact title, a fragment of a journal URL, or narrow the result set by quartile, country, and indexing labels. Abstract matching is scored specifically from each journal's <strong>Categories</strong> and <strong>Areas</strong>.</p>
            <div class=\"stats-grid\">
              <div class=\"stat-card\">
                <p class=\"stat-label\">Journals indexed</p>
                <p class=\"stat-value\">{summary.total_journals:,}</p>
              </div>
              <div class=\"stat-card\">
                <p class=\"stat-label\">WoS matches</p>
                <p class=\"stat-value\">{summary.total_wos:,}</p>
              </div>
              <div class=\"stat-card\">
                <p class=\"stat-label\">DOAJ matches</p>
                <p class=\"stat-value\">{summary.total_doaj:,}</p>
              </div>
              <div class=\"stat-card\">
                <p class=\"stat-label\">Missing external websites</p>
                <p class=\"stat-value\">{summary.total_missing_websites:,}</p>
              </div>
            </div>
          </div>
        </div>
      </section>
      <section class=\"section\">
        <div class=\"shell\" id=\"app-error\"></div>
        <div class=\"shell\">
          <div class=\"filter-panel\">
            <form id=\"search-form\">
              <div class=\"search-form-grid\">
                <div class=\"field search-query-field\">
                  <label for=\"q\">Query</label>
                  <textarea id=\"q\" name=\"q\" rows=\"7\" placeholder=\"Paste an article abstract, or enter a title, keyword, publisher name, or URL fragment.\"></textarea>
                </div>
                <div class=\"search-filter-grid\">
                  <div class=\"field\">
                    <label for=\"scope\">Search scope</label>
                    <select id=\"scope\" name=\"scope\">
                      <option value=\"all\">Keyword, title, publisher, country, URL</option>
                      <option value=\"abstract\">Article abstract to journal topic fit</option>
                      <option value=\"title\">Title only</option>
                      <option value=\"publisher\">Publisher only</option>
                      <option value=\"url\">URL only</option>
                    </select>
                  </div>
                  <div class=\"field\">
                    <label for=\"index-filter\">Index filter</label>
                    <select id=\"index-filter\" name=\"index\">
                      <option value=\"all\">All indices</option>
                      <option value=\"scopus\">Scopus only</option>
                      <option value=\"wos\">WoS only</option>
                      <option value=\"doaj\">DOAJ only</option>
                    </select>
                  </div>
                  <div class=\"field\">
                    <label for=\"quartile-filter\">Best quartile</label>
                    <select id=\"quartile-filter\" name=\"quartile\">
                      <option value=\"all\">All quartiles</option>
                      <option value=\"Q1\">Q1</option>
                      <option value=\"Q2\">Q2</option>
                      <option value=\"Q3\">Q3</option>
                      <option value=\"Q4\">Q4</option>
                    </select>
                  </div>
                  <div class=\"field\">
                    <label for=\"country-filter\">Country</label>
                    <select id=\"country-filter\" name=\"country\">
                      <option value=\"all\">All countries</option>
                    </select>
                  </div>
                </div>
              </div>
              <div class=\"hero-actions\">
                <button type=\"submit\">Search journals</button>
                <a class=\"button button-secondary\" href=\"../\">Back to front page</a>
              </div>
            </form>
          </div>
          <div class=\"results-toolbar\">
            <div class=\"results-count\" id=\"results-count\">Loading profiles…</div>
            <div class=\"table-chip\">Public runtime: static JSON only</div>
          </div>
          <div class=\"search-results\" id=\"search-results\"></div>
          <div class=\"pagination\">
            <div class=\"pagination-info\" id=\"search-pagination-info\">Loading pagination…</div>
            <div class=\"pagination-list\" id=\"search-pagination-list\"></div>
          </div>
        </div>
      </section>
    </main>
    <footer class=\"site-footer\">
      <div class=\"shell footer-grid\">
        <div class=\"footer-note\">Created by Ikhwan Arief (ikhwan@eng.unand.ac.id). Licensed for use under CC BY-NC.</div>
        <div class=\"footer-note\">Data sources: Scopus, Scimago Journal Rank (SJR), and DOAJ.</div>
      </div>
    </footer>
  </body>
</html>
"""


def profile_page_html(record: JournalRecord) -> str:
    search_query = quote_plus(record.title)
    description = f"{record.title} journal profile with indexing labels, publisher, country, ISSN, website availability, APC status, license, and SJR best quartile."
    website_value = (
        f'<a href="{html.escape(record.journal_url, quote=True)}" target="_blank" rel="noopener noreferrer">{html.escape(record.journal_url)}</a>'
        if record.journal_url
        else '<span class="field-value-muted">Tidak tersedia</span>'
    )
    metadata_rows = [
        ("Publisher", record.publisher or "Tidak tersedia"),
        ("Country", record.country or "Tidak tersedia"),
        ("Region", record.region or "Tidak tersedia"),
        ("Indexed In", record.index_summary),
        ("SJR Best Quartile", record.sjr_best_quartile or "Tidak tersedia"),
        ("SJR Quartile (table view)", record.sjr_quartile or "Tidak tersedia"),
        ("APC Status", record.apc_status or "Tidak tersedia"),
        ("License", record.license or "Tidak tersedia"),
        ("Author Holds Copyright", record.author_holds_copyright or "Tidak tersedia"),
        ("ISSN", ", ".join(record.issns) or "Tidak tersedia"),
        ("Coverage", record.coverage or "Tidak tersedia"),
        ("Categories", record.categories or "Tidak tersedia"),
        ("Areas", record.areas or "Tidak tersedia"),
        ("Open Access", record.open_access or "Tidak tersedia"),
        ("Open Access Diamond", record.open_access_diamond or "Tidak tersedia"),
    ]
    detail_html = "\n".join(
        f'<div class="detail-item"><div class="field-name">{html.escape(name)}</div><div class="field-value">{html.escape(value)}</div></div>'
        for name, value in metadata_rows
    )
    return f"""<!doctype html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\">
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
    <title>{html.escape(record.title)} | Journal Discovery</title>
    <meta name=\"description\" content=\"{html.escape(description, quote=True)}\">
    <meta name=\"robots\" content=\"index,follow\">
    <meta property=\"og:title\" content=\"{html.escape(record.title, quote=True)}\">
    <meta property=\"og:description\" content=\"{html.escape(description, quote=True)}\">
    <meta property=\"og:type\" content=\"website\">
    <meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'self'; img-src 'self' data:; style-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'\">
    {maybe_canonical(record.profile_path)}
    <link rel=\"stylesheet\" href=\"../../assets/styles.css\">
  </head>
  <body>
    <a class=\"skip-link\" href=\"#main\">Skip to content</a>
    <header class=\"site-header\">
      <div class=\"shell\">
        <a class=\"brand\" href=\"../../\">
          <span class=\"brand-mark\">Journal Discovery</span>
          <span class=\"brand-subtitle\">Individual journal profile</span>
        </a>
        <nav class=\"top-nav\" aria-label=\"Primary\">
          <a href=\"../../\">Browse journals</a>
          <a href=\"../../search/\">Search profiles</a>
        </nav>
      </div>
    </header>
    <main id=\"main\">
      <section class=\"profile-hero\">
        <div class=\"shell\">
          <div class=\"breadcrumbs\">
            <a href=\"../../\">Home</a>
            <span>/</span>
            <a href=\"../../search/\">Search</a>
            <span>/</span>
            <span>{html.escape(record.title)}</span>
          </div>
          <div class=\"hero-panel\">
            <p class=\"eyebrow\">Journal profile</p>
            <h1>{html.escape(record.title)}</h1>
            <p class=\"profile-copy\">This profile is generated from the current public dataset snapshot. When a DOAJ match exists, website, APC, license, and copyright fields are filled from that source; otherwise unavailable fields are still shown instead of hidden.</p>
            <div class=\"label-row\">{render_index_labels(record)}</div>
            <div class=\"profile-links\">
              <a class=\"button button-secondary\" href=\"../../search/?q={search_query}&scope=title\">Search similar journals</a>
              <a class=\"button button-primary\" href=\"../../\">Back to front page</a>
            </div>
          </div>
        </div>
      </section>
      <section class=\"section\">
        <div class=\"shell\">
          <div class=\"profile-card\">
            <div class=\"profile-layout\">
              <div class=\"profile-main detail-grid\">
                <div class=\"detail-item\">
                  <div class=\"field-name\">Website</div>
                  <div class=\"field-value\">{website_value}</div>
                </div>
                {detail_html}
              </div>
              <aside class=\"profile-side detail-grid\">
                <div class=\"detail-item\">
                  <div class=\"field-name\">Source ID</div>
                  <div class=\"field-value\">{html.escape(record.sourceid)}</div>
                </div>
                <div class=\"detail-item\">
                  <div class=\"field-name\">Front-page quartile column</div>
                  <div class=\"field-value\">{html.escape(record.sjr_quartile or 'Tidak tersedia')}</div>
                </div>
                <div class=\"detail-item\">
                  <div class=\"field-name\">Best quartile shown on profile</div>
                  <div class=\"field-value\">{html.escape(record.sjr_best_quartile or 'Tidak tersedia')}</div>
                </div>
                <div class=\"detail-item\">
                  <div class=\"field-name\">Data note</div>
                  <div class=\"field-value\">External website, APC, license, and copyright values come from the current DOAJ snapshot when a journal match is found.</div>
                </div>
              </aside>
            </div>
          </div>
        </div>
      </section>
    </main>
    <footer class=\"site-footer\">
      <div class=\"shell footer-grid\">
        <div class=\"footer-note\">Generated static profile for secure public hosting.</div>
        <div class=\"footer-note\">Source ID {html.escape(record.sourceid)} · Rank {record.rank}</div>
      </div>
    </footer>
  </body>
</html>
"""


def write_data_json(records: list[JournalRecord], summary: SiteSummary) -> None:
  home_payload = {
    "summary": asdict(summary),
    "records": [record.to_home_dict() for record in records],
  }
  (DOCS_DIR / "data" / "home.json").write_text(
    json.dumps(home_payload, ensure_ascii=False, separators=(",", ":")),
    encoding="utf-8",
  )

  chunk_dir = DOCS_DIR / "data" / "search-chunks"
  chunk_dir.mkdir(parents=True, exist_ok=True)
  chunk_paths: list[str] = []
  title_prefix_chunks: dict[str, list[str]] = {}
  search_records = [record.to_search_dict() for record in sorted(
    records,
    key=lambda record: (record.normalized_title, record.rank, record.title),
  )]
  for index in range(0, len(search_records), SEARCH_CHUNK_SIZE):
    chunk_name = f"search-{(index // SEARCH_CHUNK_SIZE) + 1:03d}.json"
    chunk_path = chunk_dir / chunk_name
    chunk_records = search_records[index:index + SEARCH_CHUNK_SIZE]
    chunk_payload = {"records": chunk_records}
    chunk_path.write_text(
      json.dumps(chunk_payload, ensure_ascii=False, separators=(",", ":")),
      encoding="utf-8",
    )
    chunk_relative_path = f"data/search-chunks/{chunk_name}"
    chunk_paths.append(chunk_relative_path)
    for prefix in sorted({search_prefix(record.get("title", "")) for record in chunk_records}):
      title_prefix_chunks.setdefault(prefix, []).append(chunk_relative_path)

  countries = sorted({record.country for record in records if record.country})
  manifest = SearchManifest(
    summary=summary,
    countries=countries,
    chunk_paths=chunk_paths,
    title_prefix_chunks=title_prefix_chunks,
  )
  (DOCS_DIR / "data" / "search-manifest.json").write_text(
    json.dumps(
      {
        "summary": asdict(manifest.summary),
        "countries": manifest.countries,
        "chunk_paths": manifest.chunk_paths,
        "title_prefix_chunks": manifest.title_prefix_chunks,
      },
      ensure_ascii=False,
      separators=(",", ":"),
    ),
    encoding="utf-8",
  )


def write_pages(records: list[JournalRecord], summary: SiteSummary) -> None:
    (DOCS_DIR / "index.html").write_text(home_page_html(records, summary), encoding="utf-8")
    (DOCS_DIR / "search" / "index.html").write_text(search_page_html(summary), encoding="utf-8")
    journal_root = DOCS_DIR / "journals"
    for record in records:
        target_dir = journal_root / record.slug
        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / "index.html").write_text(profile_page_html(record), encoding="utf-8")


def write_sitemap(records: list[JournalRecord]) -> None:
    if not DEFAULT_SITE_URL:
        return
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
        f"  <url><loc>{html.escape(DEFAULT_SITE_URL + '/')}</loc></url>",
        f"  <url><loc>{html.escape(DEFAULT_SITE_URL + '/search/')}</loc></url>",
    ]
    for record in records:
        lines.append(f"  <url><loc>{html.escape(DEFAULT_SITE_URL + '/' + record.profile_path)}</loc></url>")
    lines.append("</urlset>")
    (DOCS_DIR / "sitemap.xml").write_text("\n".join(lines), encoding="utf-8")


def build_site() -> None:
    records = build_records()
    summary = build_summary(records)
    reset_output_dirs()
    database_path = init_database(records)
    copy_assets()
    write_data_json(records, summary)
    write_pages(records, summary)
    write_sitemap(records)
    print(
        json.dumps(
            {
                "records": summary.total_journals,
                "wos": summary.total_wos,
                "doaj": summary.total_doaj,
                "quartile_ready": summary.total_with_quartile,
                "database": str(database_path),
                "docs": str(DOCS_DIR),
            },
            ensure_ascii=False,
        )
    )
