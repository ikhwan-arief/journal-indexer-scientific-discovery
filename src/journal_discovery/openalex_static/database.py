from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

SCHEMA_VERSION = 2

SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_meta (version INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS journals (
    journal_id TEXT PRIMARY KEY,
    legacy_sourceid TEXT NOT NULL UNIQUE,
    openalex_source_id TEXT UNIQUE,
    title TEXT NOT NULL,
    issn_l TEXT,
    publisher TEXT,
    country TEXT,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS journal_identifiers (
    journal_id TEXT NOT NULL REFERENCES journals(journal_id) ON DELETE CASCADE,
    scheme TEXT NOT NULL,
    value TEXT NOT NULL,
    source TEXT NOT NULL,
    match_method TEXT NOT NULL,
    confidence REAL NOT NULL CHECK(confidence >= 0 AND confidence <= 1),
    PRIMARY KEY (scheme, value, journal_id)
);
CREATE TABLE IF NOT EXISTS journal_aliases (
    journal_id TEXT NOT NULL REFERENCES journals(journal_id) ON DELETE CASCADE,
    alias TEXT NOT NULL,
    alias_type TEXT NOT NULL,
    PRIMARY KEY (journal_id, alias, alias_type)
);
CREATE TABLE IF NOT EXISTS journal_indexes (
    journal_id TEXT NOT NULL REFERENCES journals(journal_id) ON DELETE CASCADE,
    index_name TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('indexed','not_indexed','unknown','stale')),
    source_edition TEXT,
    verified_at TEXT,
    PRIMARY KEY (journal_id, index_name)
);
CREATE TABLE IF NOT EXISTS works (
    openalex_work_id TEXT PRIMARY KEY,
    doi TEXT,
    title TEXT NOT NULL,
    publication_year INTEGER,
    primary_source_id TEXT NOT NULL,
    cited_by_count INTEGER NOT NULL DEFAULT 0,
    retrieved_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS topics (
    openalex_topic_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    subfield_name TEXT,
    field_name TEXT,
    domain_name TEXT
);
CREATE TABLE IF NOT EXISTS work_topics (
    openalex_work_id TEXT NOT NULL REFERENCES works(openalex_work_id) ON DELETE CASCADE,
    openalex_topic_id TEXT NOT NULL REFERENCES topics(openalex_topic_id) ON DELETE CASCADE,
    score REAL NOT NULL CHECK(score >= 0 AND score <= 1),
    PRIMARY KEY (openalex_work_id, openalex_topic_id)
);
CREATE TABLE IF NOT EXISTS journal_topic_statistics (
    journal_id TEXT NOT NULL REFERENCES journals(journal_id) ON DELETE CASCADE,
    openalex_topic_id TEXT NOT NULL REFERENCES topics(openalex_topic_id) ON DELETE CASCADE,
    score REAL NOT NULL CHECK(score >= 0),
    work_count INTEGER NOT NULL CHECK(work_count >= 0),
    PRIMARY KEY (journal_id, openalex_topic_id)
);
CREATE TABLE IF NOT EXISTS recommendation_evidence (
    journal_id TEXT NOT NULL REFERENCES journals(journal_id) ON DELETE CASCADE,
    openalex_work_id TEXT NOT NULL REFERENCES works(openalex_work_id) ON DELETE CASCADE,
    relevance_score REAL NOT NULL CHECK(relevance_score >= 0 AND relevance_score <= 1),
    evidence_role TEXT NOT NULL,
    PRIMARY KEY (journal_id, openalex_work_id)
);
CREATE TABLE IF NOT EXISTS source_provenance (
    provenance_id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    source_name TEXT NOT NULL,
    source_url TEXT,
    source_edition TEXT,
    retrieved_at TEXT NOT NULL,
    checksum TEXT,
    verification_status TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ingestion_runs (
    run_id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    status TEXT NOT NULL,
    operation_count INTEGER NOT NULL DEFAULT 0,
    error_summary TEXT
);
CREATE TABLE IF NOT EXISTS ingestion_checkpoints (
    checkpoint_key TEXT PRIMARY KEY,
    checkpoint_value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS entity_match_reviews (
    review_id INTEGER PRIMARY KEY AUTOINCREMENT,
    legacy_sourceid TEXT NOT NULL,
    candidate_openalex_source_id TEXT,
    reason TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS api_usage_daily (
    usage_date_utc TEXT PRIMARY KEY,
    credits_used INTEGER NOT NULL DEFAULT 0 CHECK(credits_used >= 0),
    request_count INTEGER NOT NULL DEFAULT 0 CHECK(request_count >= 0),
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_journal_issn_l ON journals(issn_l);
CREATE INDEX IF NOT EXISTS idx_work_source_year ON works(primary_source_id, publication_year);
CREATE INDEX IF NOT EXISTS idx_work_doi ON works(doi);
CREATE INDEX IF NOT EXISTS idx_provenance_entity ON source_provenance(entity_type, entity_id);
"""


class OpenAlexDatabase:
    def __init__(self, path: Path) -> None:
        self.path = path

    @contextmanager
    def connect(self, *, readonly: bool = False) -> Iterator[sqlite3.Connection]:
        if readonly:
            connection = sqlite3.connect(f"file:{self.path}?mode=ro", uri=True)
        else:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        if not readonly:
            connection.execute("PRAGMA journal_mode = WAL")
        try:
            yield connection
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(SCHEMA)
            row = connection.execute("SELECT version FROM schema_meta LIMIT 1").fetchone()
            if row is None:
                connection.execute("INSERT INTO schema_meta(version) VALUES (?)", (SCHEMA_VERSION,))
            elif int(row["version"]) > SCHEMA_VERSION:
                raise RuntimeError("Unsupported OpenAlex SQLite schema version.")
            elif int(row["version"]) < SCHEMA_VERSION:
                connection.execute("UPDATE schema_meta SET version = ?", (SCHEMA_VERSION,))
            connection.commit()

    def integrity_check(self) -> None:
        with self.connect(readonly=True) as connection:
            result = connection.execute("PRAGMA integrity_check").fetchone()[0]
            foreign_keys = connection.execute("PRAGMA foreign_key_check").fetchall()
        if result != "ok" or foreign_keys:
            raise RuntimeError("OpenAlex SQLite integrity check failed.")

    def public_enrichment(self) -> dict[str, dict[str, object]]:
        if not self.path.exists():
            return {}
        with self.connect(readonly=True) as connection:
            journals = connection.execute(
                "SELECT journal_id, legacy_sourceid, openalex_source_id, updated_at FROM journals"
            ).fetchall()
            output: dict[str, dict[str, object]] = {}
            for journal in journals:
                journal_id = str(journal["journal_id"])
                topics = [dict(row) for row in connection.execute(
                    """SELECT t.openalex_topic_id AS id, t.name, t.subfield_name, t.field_name,
                              t.domain_name, s.score, s.work_count
                       FROM journal_topic_statistics s
                       JOIN topics t ON t.openalex_topic_id = s.openalex_topic_id
                       WHERE s.journal_id = ? ORDER BY s.score DESC, t.name LIMIT 20""",
                    (journal_id,),
                )]
                evidence = [dict(row) for row in connection.execute(
                    """SELECT w.openalex_work_id, w.doi, w.title, w.publication_year,
                              e.relevance_score
                       FROM recommendation_evidence e
                       JOIN works w ON w.openalex_work_id = e.openalex_work_id
                       WHERE e.journal_id = ?
                       ORDER BY e.relevance_score DESC, w.publication_year DESC, w.title LIMIT 5""",
                    (journal_id,),
                )]
                topic_text = " ".join(str(topic["name"]) for topic in topics)
                evidence_text = " ".join(str(work["title"]) for work in evidence)
                output[str(journal["legacy_sourceid"])] = {
                    "journal_id": journal_id,
                    "openalex_source_id": journal["openalex_source_id"],
                    "openalex_topics": topics,
                    "openalex_evidence": evidence,
                    "openalex_search_text": f"{topic_text} {evidence_text}".strip(),
                    "openalex_data_as_of": journal["updated_at"],
                }
            return output

    def export_debug_summary(self) -> str:
        with self.connect(readonly=True) as connection:
            counts = {
                table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in ("journals", "works", "topics", "recommendation_evidence")
            }
        return json.dumps(counts, sort_keys=True)
