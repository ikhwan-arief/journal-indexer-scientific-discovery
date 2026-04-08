"""Dikembangkan oleh Ikhwan Arief (ikhwan[at]unand.ac.id)
Lisensi aplikasi: Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)
"""

from __future__ import annotations

import csv
import html
import ipaddress
import json
import os
import re
import shutil
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable
from urllib.parse import quote_plus, urlparse

SEARCH_CHUNK_SIZE = 2000

ROOT_DIR = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT_DIR / "data" / "raw"
BUILD_DIR = ROOT_DIR / "build"
DOCS_DIR = ROOT_DIR / "docs"
ASSET_DIR = Path(__file__).resolve().parent / "assets"
MAIN_CSV = RAW_DIR / "scimagojr.csv"
WOS_CSV = RAW_DIR / "scimagojr_wos.csv"
DOAJ_CSV = RAW_DIR / "doaj.csv"
SINTA_CSV = RAW_DIR / "sinta.csv"
DEFAULT_SITE_URL = os.getenv("SITE_URL", "").rstrip("/")
NOT_AVAILABLE = "Not available"
INDONESIA_REGION = "Asiatic Region"
VALID_ACCREDITATIONS = {"S1", "S2", "S3", "S4", "S5", "S6"}


@dataclass(slots=True)
class JournalRecord:
    rank: int | None
    sourceid: str
    source_type: str
    title: str
    publisher: str | None
    country: str | None
    region: str | None
    issns: list[str]
    coverage: str | None
    categories: str | None
    areas: str | None
    sjr_value: float | None
    sjr_display: str | None
    sjr_quartile: str | None
    sjr_best_quartile: str | None
    h_index: int | None
    scopus_indexed: bool
    wos_indexed: bool
    doaj_indexed: bool
    accreditation: str | None
    sinta_url: str | None
    subject_area: str | None
    affiliation: str | None
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
    def runtime_profile_path(self) -> str:
        return f"journal/?sourceid={quote_plus(self.sourceid)}"

    @property
    def index_summary(self) -> str:
        labels: list[str] = []
        if self.scopus_indexed:
            labels.append("Scopus")
        if self.wos_indexed:
            labels.append("WoS")
        if self.doaj_indexed:
            labels.append("DOAJ")
        if self.sinta_url or self.accreditation or self.source_type == "sinta":
            labels.append("SINTA")
        return ", ".join(labels) if labels else NOT_AVAILABLE

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
            "source_type": self.source_type,
            "title": self.title,
            "publisher": self.publisher,
            "country": self.country,
            "categories": self.categories,
            "areas": self.areas,
            "subject_area": self.subject_area,
            "accreditation": self.accreditation,
            "affiliation": self.affiliation,
            "sjr_quartile": self.sjr_quartile,
            "scopus_indexed": self.scopus_indexed,
            "wos_indexed": self.wos_indexed,
            "doaj_indexed": self.doaj_indexed,
            "journal_url": self.journal_url,
            "sinta_url": self.sinta_url,
            "slug": self.slug,
        }

    def to_search_dict(self) -> dict[str, object]:
        return {
            "rank": self.rank,
            "sourceid": self.sourceid,
            "source_type": self.source_type,
            "title": self.title,
            "publisher": self.publisher,
            "country": self.country,
            "region": self.region,
            "issns": self.issns,
            "coverage": self.coverage,
            "categories": self.categories,
            "areas": self.areas,
            "sjr_value": self.sjr_value,
            "sjr_display": self.sjr_display,
            "sjr_quartile": self.sjr_quartile,
            "sjr_best_quartile": self.sjr_best_quartile,
            "h_index": self.h_index,
            "scopus_indexed": self.scopus_indexed,
            "wos_indexed": self.wos_indexed,
            "doaj_indexed": self.doaj_indexed,
            "accreditation": self.accreditation,
            "sinta_url": self.sinta_url,
            "subject_area": self.subject_area,
            "affiliation": self.affiliation,
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


@dataclass(slots=True)
class SintaRecord:
    profile_id: str
    title: str
    normalized_title: str
    issns: list[str]
    subject_area: str | None
    affiliation: str | None
    accreditation: str | None
    scopus_indexed: bool
    journal_url: str | None
    sinta_url: str


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


def normalize_accreditation(value: str | None) -> str | None:
    cleaned = (value or "").strip().upper()
    return cleaned if cleaned in VALID_ACCREDITATIONS else None


def parse_yes_no_bool(value: str | None) -> bool:
    return normalize_yes_no(value) == "Yes"


def parse_decimal_metric(value: str | None) -> float | None:
    cleaned = (value or "").strip()
    if not cleaned:
        return None
    normalized = cleaned.replace(".", "").replace(",", ".")
    try:
        return float(normalized)
    except ValueError:
        return None


def parse_int_metric(value: str | None) -> int | None:
    cleaned = re.sub(r"[^0-9]", "", (value or "").strip())
    if not cleaned:
        return None
    return int(cleaned)


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


def read_plain_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader)


def read_doaj_rows(path: Path) -> list[dict[str, str]]:
    return read_plain_csv_rows(path)


def read_sinta_rows(path: Path) -> list[dict[str, str]]:
    return read_plain_csv_rows(path)


def load_wos_sourceids(path: Path) -> set[str]:
    sourceids: set[str] = set()
    for row in read_csv_rows(path):
        sourceid = (row.get("Sourceid") or "").strip()
        if sourceid:
            sourceids.add(sourceid)
    return sourceids


def extract_sinta_profile_id(url: str | None) -> str | None:
    match = re.search(r"/profile/(\d+)", (url or "").strip())
    return match.group(1) if match else None


def load_sinta_records(path: Path) -> list[SintaRecord]:
    if not path.exists():
        raise FileNotFoundError(f"Missing source dataset: {path}")

    records: list[SintaRecord] = []
    for row in read_sinta_rows(path):
        title = (row.get("Journal Name") or "").strip()
        sinta_url = safe_url(row.get("Sinta URL"))
        profile_id = extract_sinta_profile_id(sinta_url)
        if not title or not sinta_url or not profile_id:
            continue

        records.append(
            SintaRecord(
                profile_id=profile_id,
                title=title,
                normalized_title=normalize_text(title),
                issns=normalize_issns(
                    ",".join(
                        value
                        for value in (
                            row.get("P-ISSN"),
                            row.get("E-ISSN"),
                        )
                        if value
                    )
                ),
                subject_area=(row.get("Subject Area") or "").strip() or None,
                affiliation=(row.get("Affiliation") or "").strip() or None,
                accreditation=normalize_accreditation(row.get("Accreditation")),
                scopus_indexed=parse_yes_no_bool(row.get("Scopus Indexed")),
                journal_url=safe_url(row.get("Website URL")),
                sinta_url=sinta_url,
            )
        )

    return records


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


def build_unique_issn_lookup(rows: Iterable[dict[str, str]]) -> dict[str, str]:
    issn_groups: dict[str, list[str]] = {}

    for row in rows:
        sourceid = (row.get("Sourceid") or "").strip()
        title = (row.get("Title") or "").strip()
        if not sourceid or not title:
            continue

        for issn in normalize_issns(row.get("Issn") or ""):
            issn_groups.setdefault(issn, []).append(sourceid)

    return {
        issn: sourceids[0]
        for issn, sourceids in issn_groups.items()
        if len(sourceids) == 1
    }


def match_scimago_sourceid(
    sinta_record: SintaRecord,
    issn_lookup: dict[str, str],
) -> tuple[str | None, str | None]:
    # Title-only SINTA merges proved too ambiguous for generic journal names
    # and could attach Indonesian metadata to unrelated Scimago records.
    for issn in sinta_record.issns:
        sourceid = issn_lookup.get(issn)
        if sourceid:
            return sourceid, "issn"

    return None, None


def accreditation_priority(value: str | None) -> int:
    if value == "S1":
        return 6
    if value == "S2":
        return 5
    if value == "S3":
        return 4
    if value == "S4":
        return 3
    if value == "S5":
        return 2
    if value == "S6":
        return 1
    return 0


def sinta_merge_preference(record: SintaRecord, match_kind: str | None) -> tuple[int, int, int, int, int]:
    return (
        1 if match_kind == "issn" else 0,
        accreditation_priority(record.accreditation),
        len(record.subject_area or ""),
        len(record.affiliation or ""),
        -int(record.profile_id),
    )


def build_records() -> list[JournalRecord]:
    if not MAIN_CSV.exists():
        raise FileNotFoundError(f"Missing source dataset: {MAIN_CSV}")
    if not WOS_CSV.exists():
        raise FileNotFoundError(f"Missing source dataset: {WOS_CSV}")
    if not SINTA_CSV.exists():
        raise FileNotFoundError(f"Missing source dataset: {SINTA_CSV}")

    scimago_rows = [row for row in read_csv_rows(MAIN_CSV) if (row.get("Type") or "").strip().lower() == "journal"]
    wos_sourceids = load_wos_sourceids(WOS_CSV)
    doaj_issn_lookup, doaj_title_lookup = load_doaj_lookups(DOAJ_CSV)
    sinta_records = load_sinta_records(SINTA_CSV)
    unique_issn_lookup = build_unique_issn_lookup(scimago_rows)

    records: list[JournalRecord] = []
    records_by_sourceid: dict[str, JournalRecord] = {}
    for row in scimago_rows:
        sourceid = (row.get("Sourceid") or "").strip()
        title = (row.get("Title") or "").strip()
        if not sourceid or not title:
            continue
        quartile = (row.get("SJR Best Quartile") or "").strip() or None
        issns = normalize_issns(row.get("Issn") or "")
        doaj_record = match_doaj_record(title, issns, doaj_issn_lookup, doaj_title_lookup)
        record = JournalRecord(
            rank=int((row.get("Rank") or "0").strip() or 0) or None,
            sourceid=sourceid,
            source_type="scimago",
            title=title,
            publisher=(row.get("Publisher") or "").strip() or None,
            country=(row.get("Country") or "").strip() or None,
            region=(row.get("Region") or "").strip() or None,
            issns=issns,
            coverage=(row.get("Coverage") or "").strip() or None,
            categories=(row.get("Categories") or "").strip() or None,
            areas=(row.get("Areas") or "").strip() or None,
            sjr_value=parse_decimal_metric(row.get("SJR")),
            sjr_display=(row.get("SJR") or "").strip() or None,
            sjr_quartile=quartile,
            sjr_best_quartile=quartile,
            h_index=parse_int_metric(row.get("H index")),
            scopus_indexed=True,
            wos_indexed=sourceid in wos_sourceids,
            doaj_indexed=doaj_record is not None,
            accreditation=None,
            sinta_url=None,
            subject_area=None,
            affiliation=None,
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
        records_by_sourceid[sourceid] = record

    selected_sinta_by_sourceid: dict[str, tuple[SintaRecord, str | None]] = {}
    unmatched_sinta_records: list[SintaRecord] = []
    for sinta_record in sinta_records:
        sourceid, match_kind = match_scimago_sourceid(sinta_record, unique_issn_lookup)
        if not sourceid:
            unmatched_sinta_records.append(sinta_record)
            continue

        current = selected_sinta_by_sourceid.get(sourceid)
        if current is None or sinta_merge_preference(sinta_record, match_kind) > sinta_merge_preference(current[0], current[1]):
            selected_sinta_by_sourceid[sourceid] = (sinta_record, match_kind)

    for sourceid, (sinta_record, _) in selected_sinta_by_sourceid.items():
        record = records_by_sourceid.get(sourceid)
        if record is None:
            continue

        record.accreditation = sinta_record.accreditation
        record.sinta_url = sinta_record.sinta_url
        record.subject_area = sinta_record.subject_area
        record.affiliation = sinta_record.affiliation
        if not record.journal_url and sinta_record.journal_url:
            record.journal_url = sinta_record.journal_url
        record.normalized_url = normalize_text(record.journal_url or "")

    for sinta_record in unmatched_sinta_records:
        doaj_record = match_doaj_record(sinta_record.title, sinta_record.issns, doaj_issn_lookup, doaj_title_lookup)
        journal_url = doaj_record.journal_url if doaj_record else sinta_record.journal_url
        record = JournalRecord(
            rank=None,
            sourceid=f"sinta-{sinta_record.profile_id}",
            source_type="sinta",
            title=sinta_record.title,
            publisher=sinta_record.affiliation,
            country="Indonesia",
            region=INDONESIA_REGION,
            issns=sinta_record.issns,
            coverage=None,
            categories=None,
            areas=None,
            sjr_value=None,
            sjr_display=None,
            sjr_quartile=None,
            sjr_best_quartile=None,
            h_index=None,
            scopus_indexed=sinta_record.scopus_indexed,
            wos_indexed=False,
            doaj_indexed=doaj_record is not None,
            accreditation=sinta_record.accreditation,
            sinta_url=sinta_record.sinta_url,
            subject_area=sinta_record.subject_area,
            affiliation=sinta_record.affiliation,
            journal_url=journal_url,
            apc_status=doaj_record.apc_status if doaj_record else None,
            license=doaj_record.license if doaj_record else None,
            author_holds_copyright=doaj_record.author_holds_copyright if doaj_record else None,
            open_access=None,
            open_access_diamond=None,
            slug=slugify(sinta_record.title, f"sinta-{sinta_record.profile_id}"),
            normalized_title=normalize_text(sinta_record.title),
            normalized_publisher=normalize_text(sinta_record.affiliation or ""),
            normalized_country=normalize_text("Indonesia"),
            normalized_url=normalize_text(journal_url or ""),
        )
        records.append(record)

    records.sort(
        key=lambda record: (
            record.rank is None,
            record.rank if record.rank is not None else 10**12,
            record.title,
        )
    )
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
    for relative in ("assets", "data", "journal", "search"):
        (DOCS_DIR / relative).mkdir(parents=True, exist_ok=True)


def legacy_redirect_page_html() -> str:
    return """<!doctype html>
<!-- Dikembangkan oleh Ikhwan Arief (ikhwan[at]unand.ac.id) -->
<!-- Lisensi aplikasi: Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0) -->
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\">
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
    <title>Legacy Journal Link | Journal Discovery</title>
    <meta name=\"robots\" content=\"noindex,nofollow\">
    <meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'self'; img-src 'self' data:; style-src 'unsafe-inline'; script-src 'unsafe-inline'; object-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'\">
    <style>
      :root {
        color-scheme: light;
        --bg: #f6f9fc;
        --paper: #ffffff;
        --ink: #17313e;
        --muted: #627381;
        --line: rgba(23, 49, 62, 0.1);
        --accent: #1976d2;
      }
      * { box-sizing: border-box; }
      body {
        margin: 0;
        min-height: 100vh;
        display: grid;
        place-items: center;
        padding: 1.5rem;
        font-family: Avenir Next, Segoe UI, sans-serif;
        color: var(--ink);
        background: radial-gradient(circle at top left, rgba(25, 118, 210, 0.08), transparent 20%), var(--bg);
      }
      .shell { width: min(100%, 760px); }
      .empty-state {
        display: flex;
        flex-direction: column;
        gap: 0.9rem;
        padding: 1.5rem;
        border: 1px solid var(--line);
        border-radius: 18px;
        background: var(--paper);
        box-shadow: 0 18px 48px rgba(23, 49, 62, 0.07);
      }
      .button {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: fit-content;
        padding: 0.9rem 1.2rem;
        border-radius: 999px;
        background: var(--accent);
        color: #fff;
        text-decoration: none;
        font-weight: 600;
      }
      .button-secondary {
        background: #fff;
        color: var(--ink);
        border: 1px solid var(--line);
      }
      strong { font-size: 1.1rem; }
      span { color: var(--muted); line-height: 1.7; }
    </style>
    <script>
      (function () {
        function normalizedPathname(pathname) {
          return (pathname || "").replace(/\\/index\\.html$/i, "").replace(/\\/+$/, "");
        }

        function inferBasePath(pathname) {
          const journalsIndex = pathname.indexOf("/journals/");
          if (journalsIndex >= 0) {
            return pathname.slice(0, journalsIndex);
          }
          if (pathname.endsWith("/404.html")) {
            return pathname.slice(0, -"/404.html".length);
          }
          return "";
        }

        function extractSourceId(pathname) {
          const match = normalizedPathname(pathname).match(/\\/journals\\/([^/]+)$/i);
          if (!match) {
            return "";
          }
          const slugMatch = (match[1] || "").match(/-(\\d+)$/);
          return slugMatch ? slugMatch[1] : "";
        }

        function renderFallback(titleText, bodyText, href, linkText, secondary) {
          const root = document.getElementById("legacy-redirect-root");
          if (!root) {
            return;
          }

          const shell = document.createElement("div");
          shell.className = "shell";

          const box = document.createElement("div");
          box.className = "empty-state";

          const title = document.createElement("strong");
          title.textContent = titleText;
          box.appendChild(title);

          const body = document.createElement("span");
          body.textContent = bodyText;
          box.appendChild(body);

          const link = document.createElement("a");
          link.className = secondary ? "button button-secondary" : "button";
          link.href = href;
          link.textContent = linkText;
          box.appendChild(link);

          shell.appendChild(box);
          root.replaceChildren(shell);
        }

        const pathname = window.location.pathname || "";
        const basePath = inferBasePath(pathname);
        const homeHref = (basePath || "") + "/";
        const sourceid = extractSourceId(pathname);

        if (!sourceid) {
          renderFallback(
            "Legacy journal link could not be resolved.",
            "Open the journal from the current search interface instead.",
            homeHref,
            "Back to home",
            true
          );
          return;
        }

        const targetUrl = (basePath || "") + "/journal/?sourceid=" + encodeURIComponent(sourceid);
        renderFallback(
          "Redirecting legacy journal link.",
          "This journal URL now uses the new runtime profile format.",
          targetUrl,
          "Open journal profile",
          false
        );
        window.location.replace(targetUrl);
      }());
    </script>
  </head>
  <body>
    <main id=\"legacy-redirect-root\"></main>
  </body>
</html>
"""


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


def parse_bool_env(name: str, default: bool) -> bool:
    value = (os.getenv(name) or "").strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    return default


def llm_api_base_url() -> str:
    return safe_url(os.getenv("LLM_API_BASE_URL")) or ""

def is_local_service_url(raw_url: str | None) -> bool:
    if not raw_url:
        return False
    parsed = urlparse(raw_url)
    hostname = (parsed.hostname or "").strip().lower()
    if not hostname:
        return False
    if hostname == "localhost":
        return True
    try:
        return ipaddress.ip_address(hostname).is_loopback
    except ValueError:
        return False


def llm_abstract_enabled() -> bool:
    api_url = llm_api_base_url()
    if not api_url:
        return False
    raw_value = (os.getenv("LLM_ABSTRACT_MATCH_ENABLED") or "").strip()
    if not raw_value:
        return True
    return parse_bool_env("LLM_ABSTRACT_MATCH_ENABLED", default=True)


def llm_timeout_ms() -> int:
    default_timeout_ms = 60000 if is_local_service_url(llm_api_base_url()) else 8000
    raw_value = (os.getenv("LLM_TIMEOUT_MS") or "").strip()
    if not raw_value:
        return default_timeout_ms
    try:
        value = int(raw_value)
    except ValueError:
        return default_timeout_ms
    return max(1000, min(120000, value))


def llm_candidate_limit() -> int:
    raw_value = (os.getenv("LLM_CANDIDATE_LIMIT") or "").strip()
    if not raw_value:
        return 50
    try:
        value = int(raw_value)
    except ValueError:
        return 50
    return max(1, min(50, value))


def llm_connect_origin() -> str:
    api_url = llm_api_base_url()
    if not api_url:
        return ""
    parsed = urlparse(api_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""
    return f"{parsed.scheme}://{parsed.netloc}"


def page_csp() -> str:
    directives = [
        "default-src 'self'",
        "img-src 'self' data:",
        "style-src 'self'",
        "script-src 'self'",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    ]
    connect_origin = llm_connect_origin()
    if connect_origin:
        directives.insert(1, f"connect-src 'self' {connect_origin}")
    return "; ".join(directives)


def runtime_body_attrs(page: str, site_root: str, data_url: str) -> str:
    attributes = {
        "data-page": page,
        "data-site-root": site_root,
        "data-data-url": data_url,
        "data-llm-abstract-enabled": "true" if llm_abstract_enabled() else "false",
        "data-llm-api-base-url": llm_api_base_url(),
        "data-llm-timeout-ms": str(llm_timeout_ms()),
        "data-llm-candidate-limit": str(llm_candidate_limit()),
    }
    return " ".join(
        f'{name}="{html.escape(value, quote=True)}"'
        for name, value in attributes.items()
    )


def version_token(summary: SiteSummary) -> str:
    return quote_plus(summary.generated_at)


def versioned_path(relative_path: str, summary: SiteSummary) -> str:
    return f"{relative_path}?v={version_token(summary)}"


def render_index_labels(record: JournalRecord) -> str:
    labels: list[str] = []
    if record.scopus_indexed:
        labels.append('<span class="label label-scopus">Scopus</span>')
    if record.wos_indexed:
        labels.append('<span class="label label-wos">WoS</span>')
    if record.doaj_indexed:
        labels.append('<span class="label label-doaj">DOAJ</span>')
    if record.sinta_url or record.accreditation or record.source_type == "sinta":
        labels.append('<span class="label label-sinta">SINTA</span>')
    if record.accreditation:
        labels.append(f'<span class="label label-accreditation">{html.escape(record.accreditation)}</span>')
    if record.sjr_best_quartile:
        labels.append(f'<span class="label label-quartile">{html.escape(record.sjr_best_quartile)}</span>')
    return "".join(labels)


def results_panel_html() -> str:
    return """<div class=\"results-panel\">
            <div class=\"results-toolbar\">
              <div class=\"results-toolbar-meta\">
                <div class=\"results-count\" id=\"results-count\">Journal profiles ready.</div>
                <div class=\"ranking-status\" id=\"ranking-status\" hidden></div>
              </div>
              <div class=\"results-toolbar-actions\">
                <div class=\"pagination pagination-inline\">
                  <div class=\"pagination-info\" id=\"search-pagination-top-info\"></div>
                  <div class=\"pagination-list\" id=\"search-pagination-top-list\"></div>
                </div>
              </div>
            </div>
            <div class=\"search-results\" id=\"search-results\"></div>
            <div class=\"pagination\">
              <div class=\"pagination-info\" id=\"search-pagination-info\"></div>
              <div class=\"pagination-list\" id=\"search-pagination-list\"></div>
            </div>
          </div>"""


def home_page_html(summary: SiteSummary) -> str:
    stylesheet_href = versioned_path("assets/styles.css", summary)
    script_src = versioned_path("assets/app.js", summary)
    data_url = versioned_path("data/search-manifest.json", summary)
    total_profiles = format(summary.total_journals, ",")
    runtime_attrs = runtime_body_attrs("home", ".", data_url)
    return f"""<!doctype html>
<!-- Dikembangkan oleh Ikhwan Arief (ikhwan[at]unand.ac.id) -->
<!-- Lisensi aplikasi: Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0) -->
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\">
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
    <title>Journal Discovery | Match journal profiles from article abstracts</title>
    <meta name=\"description\" content=\"Search journal discovery data built from Scimago, SINTA, WoS, and optional DOAJ enrichment, with abstract-to-journal matching based on journal titles, categories, areas, and SINTA subject areas.\">
    <meta name=\"robots\" content=\"index,follow\">
    <meta http-equiv=\"Content-Security-Policy\" content=\"{html.escape(page_csp(), quote=True)}\">
    {maybe_canonical('')}
    <link rel=\"stylesheet\" href=\"{html.escape(stylesheet_href, quote=True)}\">
    <script defer src=\"{html.escape(script_src, quote=True)}\"></script>
  </head>
  <body {runtime_attrs}>
    <a class=\"skip-link\" href=\"#main\">Skip to content</a>
    <header class=\"site-header\">
      <div class=\"shell\">
        <a class=\"brand\" href=\"./\">
          <span class=\"brand-mark\">Journal Discovery</span>
          <span class=\"brand-subtitle\">Journal search for abstracts, keywords, and titles</span>
        </a>
        <nav class=\"top-nav\" aria-label=\"Primary\">
          <a href=\"./\">Home</a>
          <a href=\"search/\">Search journal profiles</a>
        </nav>
      </div>
    </header>
    <main id=\"main\">
      <section class=\"hero\">
        <div class=\"shell\">
          <div class=\"hero-panel\">
            <div class=\"hero-content\">
              <h1>Find journals by title, keyword, URL fragment, or article abstract.</h1>
              <p class=\"hero-copy\">Paste an article abstract and the app will rank journals by how closely it matches each journal's <strong>Title</strong>, <strong>Categories</strong>, <strong>Areas</strong>, and <strong>SINTA Subject Area</strong> when available.</p>
              <form class=\"abstract-search-form\" id=\"search-form\" action=\"./\" method=\"get\">
                <input type=\"hidden\" id=\"scope\" name=\"scope\" value=\"abstract\">
                <label class=\"field abstract-field\" for=\"q\">
                  <span>Paste article abstract</span>
                  <textarea id=\"q\" name=\"q\" rows=\"6\" placeholder=\"Paste an article abstract. The app compares it with journal titles, categories, areas, and SINTA subject areas to suggest relevant journals.\"></textarea>
                </label>
                <p class=\"llm-privacy-note\" id=\"llm-privacy-note\" hidden>When LLM-assisted ranking is enabled, submitted abstracts are sent to the configured inference API for topical reranking.</p>
                <div class=\"field hero-sort-field\">
                  <label for=\"sort-order\">Sort results</label>
                  <select id=\"sort-order\" name=\"sort\">
                    <option value=\"default\">Default ranking</option>
                    <option value=\"fit_desc\">Highest abstract fit</option>
                  </select>
                </div>
                <div class=\"hero-actions-inline\">
                  <button type=\"submit\" class=\"button button-primary\">Find matching journals</button>
                  <a class=\"button button-secondary\" href=\"search/\">Open advanced search</a>
                </div>
              </form>
            </div>
          </div>
        </div>
      </section>
      <div class=\"shell\" id=\"app-error\"></div>
      <section class=\"section\" id=\"results-section\" hidden>
        <div class=\"shell\">
          <div class=\"section-heading section-heading-results\">
            <div>
              <p class=\"eyebrow results-eyebrow\">SEARCH RESULTS</p>
              <h2>Recommended journals</h2>
              <p class=\"table-note\">Results appear here only after you submit an abstract or keyword query. Abstract ranking uses the local scorer by default and can rerank the shortlist through the configured LLM API when enabled.</p>
            </div>
            <div class=\"table-chip\" id=\"results-summary\">{total_profiles} journal profiles ready</div>
          </div>
          {results_panel_html()}
        </div>
      </section>
    </main>
    <footer class=\"site-footer\">
      <div class=\"shell footer-grid\">
        <div class=\"footer-note\">Created by Ikhwan Arief (ikhwan[at]unand.ac.id). Available under CC BY-NC.</div>
        <div class=\"footer-note\">Data sources: Scopus, Scimago Journal Rank (SJR), SINTA, WoS, and DOAJ.</div>
      </div>
    </footer>
  </body>
</html>
"""


def search_page_html(summary: SiteSummary) -> str:
    stylesheet_href = versioned_path("../assets/styles.css", summary)
    script_src = versioned_path("../assets/app.js", summary)
    data_url = versioned_path("../data/search-manifest.json", summary)
    total_profiles = format(summary.total_journals, ",")
    runtime_attrs = runtime_body_attrs("search", "..", data_url)
    return f"""<!doctype html>
<!-- Dikembangkan oleh Ikhwan Arief (ikhwan[at]unand.ac.id) -->
<!-- Lisensi aplikasi: Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0) -->
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\">
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
    <title>Search Journal Profiles | Journal Discovery</title>
    <meta name=\"description\" content=\"Search journal profiles by abstract, keyword, full title, publisher, URL fragment, country, indexing status, accreditation, or best SJR quartile.\">
    <meta name=\"robots\" content=\"index,follow\">
    <meta http-equiv=\"Content-Security-Policy\" content=\"{html.escape(page_csp(), quote=True)}\">
    {maybe_canonical('search/')}
    <link rel=\"stylesheet\" href=\"{html.escape(stylesheet_href, quote=True)}\">
    <script defer src=\"{html.escape(script_src, quote=True)}\"></script>
  </head>
  <body {runtime_attrs}>
    <a class=\"skip-link\" href=\"#main\">Skip to content</a>
    <header class=\"site-header\">
      <div class=\"shell\">
        <a class=\"brand\" href=\"../\">
          <span class=\"brand-mark\">Journal Discovery</span>
          <span class=\"brand-subtitle\">Advanced journal search</span>
        </a>
        <nav class=\"top-nav\" aria-label=\"Primary\">
          <a href=\"../\">Home</a>
          <a href=\"./\">Search journal profiles</a>
        </nav>
      </div>
    </header>
    <main id=\"main\">
      <section class=\"hero\">
        <div class=\"shell\">
          <div class=\"hero-panel\">
            <div class=\"hero-content\">
              <h1>Search journal profiles by abstract, keyword, title, publisher, or URL.</h1>
              <p class=\"hero-copy\">Use abstract matching for recommendations, or switch scope and filters for a more precise search across journal metadata, accreditation, and indexing status.</p>
              <p class=\"llm-privacy-note\" id=\"llm-privacy-note\" hidden>When LLM-assisted ranking is enabled, submitted abstracts are sent to the configured inference API for topical reranking.</p>
            </div>
          </div>
        </div>
      </section>
      <section class=\"section\" id=\"results-section\">
        <div class=\"shell\" id=\"app-error\"></div>
        <div class=\"shell\">
          <div class=\"section-heading section-heading-results\">
            <div>
              <p class=\"eyebrow results-eyebrow\">ADVANCED SEARCH</p>
              <h2>Search journal profiles</h2>
              <p class=\"table-note\">Search by abstract, keyword, title, publisher, URL fragment, indexing status, accreditation, best quartile, or country. Choosing <strong>Highest abstract fit</strong> keeps ranking local and explanation-focused.</p>
            </div>
            <div class=\"table-chip\" id=\"results-summary\">{total_profiles} journal profiles ready</div>
          </div>
          <div class=\"filter-panel\">
            <form id=\"search-form\" action=\"./\" method=\"get\" class=\"search-form-grid\">
              <div class=\"field search-query-field\">
                <label for=\"q\">Search query</label>
                <textarea id=\"q\" name=\"q\" rows=\"8\" placeholder=\"Paste an abstract or enter a keyword, title, publisher, or URL fragment.\"></textarea>
              </div>
              <div class=\"search-filter-grid\">
                <div class=\"field\">
                  <label for=\"scope\">Search scope</label>
                  <select id=\"scope\" name=\"scope\">
                    <option value=\"all\">Keywords, titles, publishers, countries, and URLs</option>
                    <option value=\"abstract\">Abstract-to-topic matching</option>
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
                  <label for=\"accreditation-filter\">Accreditation</label>
                  <select id=\"accreditation-filter\" name=\"accreditation\">
                    <option value=\"all\">All accreditation levels</option>
                    <option value=\"S1\">S1</option>
                    <option value=\"S2\">S2</option>
                    <option value=\"S3\">S3</option>
                    <option value=\"S4\">S4</option>
                    <option value=\"S5\">S5</option>
                    <option value=\"S6\">S6</option>
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
                <div class=\"field\">
                  <label for=\"sort-order\">Sort results</label>
                  <select id=\"sort-order\" name=\"sort\">
                    <option value=\"default\">Default ranking</option>
                    <option value=\"fit_desc\">Highest abstract fit</option>
                  </select>
                </div>
              </div>
              <div class=\"hero-actions\">
                <button type=\"submit\">Search journals</button>
                <a class=\"button button-secondary\" href=\"../\">Back to home</a>
              </div>
            </form>
          </div>
          {results_panel_html()}
        </div>
      </section>
    </main>
    <footer class=\"site-footer\">
      <div class=\"shell footer-grid\">
        <div class=\"footer-note\">Created by Ikhwan Arief (ikhwan[at]unand.ac.id). Available under CC BY-NC.</div>
        <div class=\"footer-note\">Data sources: Scopus, Scimago Journal Rank (SJR), SINTA, WoS, and DOAJ.</div>
      </div>
    </footer>
  </body>
</html>
"""


def profile_page_html(summary: SiteSummary) -> str:
    stylesheet_href = versioned_path("../assets/styles.css", summary)
    script_src = versioned_path("../assets/app.js", summary)
    data_url = versioned_path("../data/profile-index.json", summary)
    runtime_attrs = runtime_body_attrs("profile", "..", data_url)
    return f"""<!doctype html>
<!-- Dikembangkan oleh Ikhwan Arief (ikhwan[at]unand.ac.id) -->
<!-- Lisensi aplikasi: Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0) -->
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\">
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
    <title>Journal Profile | Journal Discovery</title>
    <meta name=\"description\" content=\"Journal profile with indexing labels, accreditation, publisher, country, ISSN, website availability, APC status, license, SINTA metadata, and SJR best quartile.\">
    <meta name=\"robots\" content=\"index,follow\">
    <meta property=\"og:title\" content=\"Journal Profile\">
    <meta property=\"og:description\" content=\"Journal profile with indexing labels, accreditation, publisher, country, ISSN, website availability, APC status, license, SINTA metadata, and SJR best quartile.\">
    <meta property=\"og:type\" content=\"website\">
    <meta http-equiv=\"Content-Security-Policy\" content=\"{html.escape(page_csp(), quote=True)}\">
    {maybe_canonical('journal/')}
    <link rel=\"stylesheet\" href=\"{html.escape(stylesheet_href, quote=True)}\">
    <script defer src=\"{html.escape(script_src, quote=True)}\"></script>
  </head>
  <body {runtime_attrs}>
    <a class=\"skip-link\" href=\"#main\">Skip to content</a>
    <header class=\"site-header\">
      <div class=\"shell\">
        <a class=\"brand\" href=\"../\">
          <span class=\"brand-mark\">Journal Discovery</span>
          <span class=\"brand-subtitle\">Journal profile</span>
        </a>
        <nav class=\"top-nav\" aria-label=\"Primary\">
          <a href=\"../\">Home</a>
          <a href=\"../search/\">Search journal profiles</a>
        </nav>
      </div>
    </header>
    <main id=\"main\">
      <div id=\"app-error\" class=\"shell\"></div>
      <div id=\"profile-root\"></div>
    </main>
    <footer class=\"site-footer\">
      <div class=\"shell footer-grid\">
        <div class=\"footer-note\">Created by Ikhwan Arief (ikhwan[at]unand.ac.id). Available under CC BY-NC.</div>
        <div class=\"footer-note\">Data sources: Scopus, Scimago Journal Rank (SJR), SINTA, WoS, and DOAJ.</div>
      </div>
    </footer>
  </body>
</html>
"""


def write_data_json(records: list[JournalRecord], summary: SiteSummary) -> None:
    home_payload = {
        "summary": asdict(summary),
        "ui": {
            "eyebrow": "SEARCH RESULTS",
            "title": "Recommended journals",
            "description": "Results appear here after the user submits a query from the homepage.",
        },
    }
    (DOCS_DIR / "data" / "home.json").write_text(
        json.dumps(home_payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )

    chunk_dir = DOCS_DIR / "data" / "search-chunks"
    chunk_dir.mkdir(parents=True, exist_ok=True)
    chunk_paths: list[str] = []
    profile_index: dict[str, str] = {}
    title_prefix_chunks: dict[str, list[str]] = {}
    search_records = [record.to_search_dict() for record in sorted(
        records,
        key=lambda record: (
            record.normalized_title,
            record.rank is None,
            record.rank if record.rank is not None else 10**12,
            record.title,
        ),
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
        for chunk_record in chunk_records:
            sourceid = str(chunk_record.get("sourceid") or "")
            if sourceid:
                profile_index[sourceid] = chunk_relative_path
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
    (DOCS_DIR / "data" / "profile-index.json").write_text(
        json.dumps(
            {
                "summary": asdict(summary),
                "sourceid_to_chunk": profile_index,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )


def write_pages(records: list[JournalRecord], summary: SiteSummary) -> None:
    (DOCS_DIR / "index.html").write_text(
        home_page_html(summary),
        encoding="utf-8",
    )
    (DOCS_DIR / "search" / "index.html").write_text(
        search_page_html(summary),
        encoding="utf-8",
    )
    (DOCS_DIR / "journal" / "index.html").write_text(
      profile_page_html(summary),
        encoding="utf-8",
    )
    (DOCS_DIR / "404.html").write_text(
        legacy_redirect_page_html(),
        encoding="utf-8",
    )


def write_sitemap(records: list[JournalRecord]) -> None:
    if not DEFAULT_SITE_URL:
        return

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
        f"  <url><loc>{html.escape(DEFAULT_SITE_URL + '/')}</loc></url>",
        f"  <url><loc>{html.escape(DEFAULT_SITE_URL + '/search/')}</loc></url>",
        f"  <url><loc>{html.escape(DEFAULT_SITE_URL + '/journal/')}</loc></url>",
    ]

    for record in records:
        lines.append(
            f"  <url><loc>{html.escape(DEFAULT_SITE_URL + '/journal/?sourceid=' + quote_plus(record.sourceid))}</loc></url>"
        )

    lines.append("</urlset>")
    (DOCS_DIR / "sitemap.xml").write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def build_site() -> None:
    records = build_records()
    summary = build_summary(records)
    reset_output_dirs()
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
                "docs": str(DOCS_DIR),
            },
            ensure_ascii=False,
        )
    )
