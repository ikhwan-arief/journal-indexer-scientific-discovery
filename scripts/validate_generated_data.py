from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from journal_discovery.build import normalize_text, search_prefix


DOCS_DIR = ROOT / "docs"
HOME_PATH = DOCS_DIR / "data" / "home.json"
MANIFEST_PATH = DOCS_DIR / "data" / "search-manifest.json"
PROFILE_INDEX_PATH = DOCS_DIR / "data" / "profile-index.json"
LEGACY_REDIRECT_PATH = DOCS_DIR / "404.html"

REQUIRED_HOME_KEYS = {"sourceid", "title", "slug"}
REQUIRED_SEARCH_KEYS = {"sourceid", "title", "slug", "categories", "areas"}


def load_json(path: Path) -> dict[str, object]:
    if not path.exists():
        raise SystemExit(f"Missing generated file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_keys(record: dict[str, object], required_keys: set[str], label: str) -> None:
    missing = sorted(key for key in required_keys if key not in record)
    if missing:
        raise SystemExit(f"{label} record is missing required keys: {missing}")


def record_key(record: dict[str, object]) -> tuple[str, str]:
    return str(record.get("sourceid") or ""), str(record.get("slug") or "")


def main() -> int:
    if not LEGACY_REDIRECT_PATH.exists():
        raise SystemExit("Missing generated file: docs/404.html")

    home_payload = load_json(HOME_PATH)
    manifest = load_json(MANIFEST_PATH)
    profile_index = load_json(PROFILE_INDEX_PATH)

    summary = manifest.get("summary") or {}
    expected_total = int(summary.get("total_journals") or 0)
    if expected_total <= 0:
        raise SystemExit("search-manifest.json has an invalid total_journals summary.")

    home_records = home_payload.get("records") or []
    if not isinstance(home_records, list) or not home_records:
        raise SystemExit("home.json does not contain any records.")
    if len(home_records) != expected_total:
        raise SystemExit(
            f"home.json record count {len(home_records)} does not match summary total_journals {expected_total}."
        )
    ensure_keys(home_records[0], REQUIRED_HOME_KEYS, "home.json")

    chunk_paths = manifest.get("chunk_paths") or []
    if not isinstance(chunk_paths, list) or not chunk_paths:
        raise SystemExit("search-manifest.json does not contain chunk_paths.")

    title_prefix_chunks = manifest.get("title_prefix_chunks") or {}
    if not isinstance(title_prefix_chunks, dict) or not title_prefix_chunks:
        raise SystemExit("search-manifest.json does not contain title_prefix_chunks.")

    sourceid_to_chunk = profile_index.get("sourceid_to_chunk") or {}
    if not isinstance(sourceid_to_chunk, dict) or not sourceid_to_chunk:
        raise SystemExit("profile-index.json does not contain sourceid_to_chunk.")

    search_records: list[dict[str, object]] = []
    records_by_chunk: dict[str, list[dict[str, object]]] = {}
    seen_search_keys: set[tuple[str, str]] = set()

    for relative_path in chunk_paths:
        chunk_file = DOCS_DIR / str(relative_path)
        if not chunk_file.exists():
            raise SystemExit(f"Manifest chunk path does not exist: {relative_path}")
        payload = load_json(chunk_file)
        records = payload.get("records") or []
        if not isinstance(records, list) or not records:
            raise SystemExit(f"Chunk {relative_path} does not contain any records.")
        ensure_keys(records[0], REQUIRED_SEARCH_KEYS, relative_path)
        records_by_chunk[str(relative_path)] = records
        search_records.extend(records)

        for record in records:
            key = record_key(record)
            if not all(key):
                raise SystemExit(f"Chunk {relative_path} contains a record without sourceid or slug.")
            if key in seen_search_keys:
                raise SystemExit(f"Duplicate search record detected for sourceid/slug pair: {key}")
            seen_search_keys.add(key)

    if len(search_records) != expected_total:
        raise SystemExit(
            f"Combined search chunk record count {len(search_records)} does not match summary total_journals {expected_total}."
        )

    home_keys = {record_key(record) for record in home_records}
    if len(home_keys) != len(home_records):
        raise SystemExit("Duplicate sourceid/slug pairs detected in home.json.")
    if home_keys != seen_search_keys:
        raise SystemExit("home.json and search chunk records do not describe the same journal set.")

    search_sourceids = {str(record.get("sourceid") or "") for record in search_records}
    if set(sourceid_to_chunk) != search_sourceids:
        raise SystemExit("profile-index.json source IDs do not match the generated search dataset.")

    for chunk_path, records in records_by_chunk.items():
        for record in records:
            sourceid = str(record.get("sourceid") or "")
            mapped_chunk = sourceid_to_chunk.get(sourceid)
            if mapped_chunk != chunk_path:
                raise SystemExit(
                    f"profile-index.json maps sourceid {sourceid} to {mapped_chunk}, expected {chunk_path}."
                )

    computed_countries = sorted(
        {
            str(record.get("country"))
            for record in search_records
            if record.get("country")
        }
    )
    manifest_countries = manifest.get("countries") or []
    if manifest_countries != computed_countries:
        raise SystemExit("Manifest countries list does not match countries present in search records.")

    valid_chunk_paths = set(str(path) for path in chunk_paths)
    for prefix, mapped_chunks in title_prefix_chunks.items():
        if prefix != normalize_text(prefix):
            raise SystemExit(f"Title prefix mapping key is not normalized: {prefix}")
        if not isinstance(mapped_chunks, list) or not mapped_chunks:
            raise SystemExit(f"Title prefix {prefix} does not map to any chunk.")
        unknown_chunks = sorted(set(mapped_chunks) - valid_chunk_paths)
        if unknown_chunks:
            raise SystemExit(f"Title prefix {prefix} references unknown chunk paths: {unknown_chunks}")

        matched_any = False
        for chunk_path in mapped_chunks:
            for record in records_by_chunk[chunk_path]:
                if search_prefix(str(record.get("title") or "")) == prefix:
                    matched_any = True
                    break
            if matched_any:
                break
        if not matched_any:
            raise SystemExit(f"Title prefix {prefix} does not point to any chunk containing that prefix.")

    for chunk_path, records in records_by_chunk.items():
        prefixes_in_chunk = {
            search_prefix(str(record.get("title") or ""))
            for record in records
        }
        for prefix in prefixes_in_chunk:
            mapped_chunks = title_prefix_chunks.get(prefix)
            if not mapped_chunks or chunk_path not in mapped_chunks:
                raise SystemExit(
                    f"Chunk {chunk_path} contains prefix {prefix} titles but is missing from title_prefix_chunks."
                )

    print(
        "Generated data validation passed: home/search totals match, shard files exist, the 404 legacy redirect page exists, profile index mappings are consistent, title-prefix mappings are consistent, and country metadata matches the chunk dataset."
    )
    print(f"Validated journals: {expected_total}")
    print(f"Validated shard files: {len(chunk_paths)}")
    print(f"Validated profile index entries: {len(sourceid_to_chunk)}")
    print(f"Validated title prefixes: {len(title_prefix_chunks)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())