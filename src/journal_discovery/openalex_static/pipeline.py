from __future__ import annotations

import csv
import hashlib
import json
import uuid
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

from .client import OpenAlexClient, OpenAlexError
from .database import OpenAlexDatabase
from .security import bounded_text, normalize_doi, normalize_issn, openalex_short_id


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def canonical_journal_id(legacy_sourceid: str) -> str:
    digest = hashlib.sha256(f"journal-discovery:{legacy_sourceid}".encode()).hexdigest()[:20]
    return f"jd-{digest}"


def load_journal_seeds(scimago_path: Path, sinta_path: Path) -> list[dict[str, object]]:
    seeds: list[dict[str, object]] = []
    with scimago_path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if bounded_text(row.get("Type"), limit=32).lower() != "journal":
                continue
            sourceid = bounded_text(row.get("Sourceid"), limit=128)
            title = bounded_text(row.get("Title"), limit=500)
            if not sourceid or not title:
                continue
            issns = [item for item in (normalize_issn(value) for value in bounded_text(row.get("Issn"), limit=256).replace(",", " ").split()) if item]
            seeds.append({
                "legacy_sourceid": sourceid,
                "title": title,
                "publisher": bounded_text(row.get("Publisher"), limit=500) or None,
                "country": bounded_text(row.get("Country"), limit=200) or None,
                "issns": sorted(set(issns)),
            })
    # SINTA-only records are already resolved by the normal site builder. They are left
    # unmatched here until a stable identifier export is available from that pipeline.
    _ = sinta_path
    return seeds


class OpenAlexIngestionPipeline:
    def __init__(self, database: OpenAlexDatabase, client: OpenAlexClient) -> None:
        self.database = database
        self.client = client

    def refresh(self, seeds: list[dict[str, object]], *, max_journals: int, works_per_journal: int) -> dict[str, int]:
        self.database.initialize()
        run_id = str(uuid.uuid4())
        started_at = utc_now()
        with self.database.connect() as connection:
            connection.execute(
                "INSERT INTO ingestion_runs(run_id, started_at, status) VALUES (?, ?, 'running')",
                (run_id, started_at),
            )
            connection.commit()

        matched = 0
        works_saved = 0
        status = "completed"
        error_summary: str | None = None
        try:
            for seed in seeds[:max_journals]:
                source = self._resolve_source(seed)
                if not source:
                    continue
                matched += 1
                journal_id = self._save_source(seed, source)
                works_saved += self._refresh_works(journal_id, source, works_per_journal)
        except Exception as error:
            status = "failed"
            error_summary = type(error).__name__
            raise
        finally:
            with self.database.connect() as connection:
                connection.execute(
                    """UPDATE ingestion_runs SET completed_at = ?, status = ?, operation_count = ?,
                              error_summary = ? WHERE run_id = ?""",
                    (utc_now(), status, self.client.operation_count, error_summary, run_id),
                )
                connection.commit()
        self._rebuild_topic_statistics()
        self.database.integrity_check()
        return {"matched_journals": matched, "works_saved": works_saved, "operations": self.client.operation_count}

    def _resolve_source(self, seed: dict[str, object]) -> dict[str, object] | None:
        for issn in seed.get("issns", []):
            payload = self.client.get_json("/sources", {"filter": f"issn:{issn}", "per_page": 2})
            results = payload.get("results")
            if not isinstance(results, list):
                raise OpenAlexError("OpenAlex sources response did not contain a results array.")
            verified = [item for item in results if isinstance(item, dict) and openalex_short_id(item.get("id"), "S")]
            if len(verified) == 1:
                return verified[0]
        return None

    def _save_source(self, seed: dict[str, object], source: dict[str, object]) -> str:
        legacy_sourceid = str(seed["legacy_sourceid"])
        journal_id = canonical_journal_id(legacy_sourceid)
        source_id = openalex_short_id(source.get("id"), "S")
        if not source_id:
            raise OpenAlexError("OpenAlex source response contained an invalid identifier.")
        issn_l = normalize_issn(source.get("issn_l"))
        updated_at = utc_now()
        with self.database.connect() as connection:
            connection.execute(
                """INSERT INTO journals(journal_id, legacy_sourceid, openalex_source_id, title,
                           issn_l, publisher, country, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(journal_id) DO UPDATE SET openalex_source_id=excluded.openalex_source_id,
                       title=excluded.title, issn_l=excluded.issn_l, publisher=excluded.publisher,
                       country=excluded.country, updated_at=excluded.updated_at""",
                (
                    journal_id, legacy_sourceid, source_id,
                    bounded_text(source.get("display_name"), limit=500) or str(seed["title"]),
                    issn_l, bounded_text(source.get("host_organization_name"), limit=500) or seed.get("publisher"),
                    bounded_text(source.get("country_code"), limit=32) or seed.get("country"), updated_at,
                ),
            )
            identifiers = [("legacy_sourceid", legacy_sourceid), ("openalex", source_id)]
            if issn_l:
                identifiers.append(("issn_l", issn_l))
            for issn in source.get("issn") or []:
                normalized = normalize_issn(issn)
                if normalized:
                    identifiers.append(("issn", normalized))
            for scheme, value in identifiers:
                connection.execute(
                    """INSERT OR IGNORE INTO journal_identifiers
                       (journal_id, scheme, value, source, match_method, confidence)
                       VALUES (?, ?, ?, 'openalex', 'exact_issn', 1.0)""",
                    (journal_id, scheme, value),
                )
            connection.execute(
                """INSERT INTO source_provenance(entity_type, entity_id, source_name, source_url,
                           source_edition, retrieved_at, verification_status)
                   VALUES ('journal', ?, 'OpenAlex', ?, NULL, ?, 'verified')""",
                (journal_id, f"https://openalex.org/{source_id}", updated_at),
            )
            connection.commit()
        return journal_id

    def _refresh_works(self, journal_id: str, source: dict[str, object], limit: int) -> int:
        source_id = openalex_short_id(source.get("id"), "S")
        if not source_id:
            return 0
        payload = self.client.get_json(
            "/works",
            {
                "filter": f"primary_location.source.id:{source_id},type:article|review",
                "sort": "publication_date:desc",
                "per_page": min(100, max(5, limit)),
                "select": "id,doi,title,publication_year,cited_by_count,primary_location,topics",
            },
        )
        results = payload.get("results")
        if not isinstance(results, list):
            raise OpenAlexError("OpenAlex works response did not contain a results array.")
        saved = 0
        with self.database.connect() as connection:
            connection.execute("DELETE FROM recommendation_evidence WHERE journal_id = ?", (journal_id,))
            for rank, work in enumerate(results[:limit]):
                if not isinstance(work, dict):
                    continue
                work_id = openalex_short_id(work.get("id"), "W")
                primary = work.get("primary_location") or {}
                primary_source = primary.get("source") or {} if isinstance(primary, dict) else {}
                primary_source_id = openalex_short_id(primary_source.get("id"), "S") if isinstance(primary_source, dict) else None
                title = bounded_text(work.get("title"), limit=1000)
                if not work_id or primary_source_id != source_id or not title:
                    continue
                year = work.get("publication_year") if isinstance(work.get("publication_year"), int) else None
                cited = max(0, int(work.get("cited_by_count") or 0))
                retrieved_at = utc_now()
                connection.execute(
                    """INSERT INTO works(openalex_work_id, doi, title, publication_year,
                               primary_source_id, cited_by_count, retrieved_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)
                       ON CONFLICT(openalex_work_id) DO UPDATE SET doi=excluded.doi, title=excluded.title,
                           publication_year=excluded.publication_year, primary_source_id=excluded.primary_source_id,
                           cited_by_count=excluded.cited_by_count, retrieved_at=excluded.retrieved_at""",
                    (work_id, normalize_doi(work.get("doi")), title, year, source_id, cited, retrieved_at),
                )
                relevance = max(0.0, 1.0 - (rank / max(1, limit)))
                connection.execute(
                    """INSERT OR REPLACE INTO recommendation_evidence
                       (journal_id, openalex_work_id, relevance_score, evidence_role)
                       VALUES (?, ?, ?, 'recent_representative')""",
                    (journal_id, work_id, relevance),
                )
                for topic in (work.get("topics") or [])[:20]:
                    if not isinstance(topic, dict):
                        continue
                    topic_id = openalex_short_id(topic.get("id"), "T")
                    name = bounded_text(topic.get("display_name"), limit=500)
                    score = topic.get("score")
                    if not topic_id or not name or not isinstance(score, (int, float)):
                        continue
                    score = min(1.0, max(0.0, float(score)))
                    connection.execute(
                        """INSERT OR REPLACE INTO topics(openalex_topic_id, name, subfield_name,
                                   field_name, domain_name) VALUES (?, ?, ?, ?, ?)""",
                        (
                            topic_id, name,
                            bounded_text((topic.get("subfield") or {}).get("display_name"), limit=500) or None,
                            bounded_text((topic.get("field") or {}).get("display_name"), limit=500) or None,
                            bounded_text((topic.get("domain") or {}).get("display_name"), limit=500) or None,
                        ),
                    )
                    connection.execute(
                        "INSERT OR REPLACE INTO work_topics(openalex_work_id, openalex_topic_id, score) VALUES (?, ?, ?)",
                        (work_id, topic_id, score),
                    )
                saved += 1
            connection.commit()
        return saved

    def _rebuild_topic_statistics(self) -> None:
        with self.database.connect() as connection:
            connection.execute("DELETE FROM journal_topic_statistics")
            connection.execute(
                """INSERT INTO journal_topic_statistics(journal_id, openalex_topic_id, score, work_count)
                   SELECT e.journal_id, wt.openalex_topic_id, AVG(wt.score), COUNT(DISTINCT wt.openalex_work_id)
                   FROM recommendation_evidence e
                   JOIN work_topics wt ON wt.openalex_work_id = e.openalex_work_id
                   GROUP BY e.journal_id, wt.openalex_topic_id"""
            )
            connection.commit()
