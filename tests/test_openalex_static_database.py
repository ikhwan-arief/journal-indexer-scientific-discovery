from __future__ import annotations

from journal_discovery.openalex_static.database import OpenAlexDatabase


def test_database_initializes_and_exports_public_enrichment(tmp_path) -> None:
    database = OpenAlexDatabase(tmp_path / "openalex.sqlite3")
    database.initialize()
    with database.connect() as connection:
        connection.execute(
            "INSERT INTO journals VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("jd-test", "123", "S123", "Journal", "2049-3630", "Publisher", "ID", "2026-10-27T00:00:00+00:00"),
        )
        connection.execute(
            "INSERT INTO works VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("W123", "10.1234/example", "<script>alert(1)</script>", 2026, "S123", 0, "2026-10-27T00:00:00+00:00"),
        )
        connection.execute(
            "INSERT INTO topics VALUES (?, ?, ?, ?, ?)",
            ("T123", "Machine Learning", "AI", "Computer Science", "Physical Sciences"),
        )
        connection.execute("INSERT INTO work_topics VALUES (?, ?, ?)", ("W123", "T123", 0.9))
        connection.execute("INSERT INTO journal_topic_statistics VALUES (?, ?, ?, ?)", ("jd-test", "T123", 0.9, 1))
        connection.execute("INSERT INTO recommendation_evidence VALUES (?, ?, ?, ?)", ("jd-test", "W123", 1.0, "recent"))
        connection.commit()

    database.integrity_check()
    exported = database.public_enrichment()["123"]
    assert exported["openalex_source_id"] == "S123"
    assert exported["openalex_topics"][0]["name"] == "Machine Learning"
    assert exported["openalex_evidence"][0]["title"] == "<script>alert(1)</script>"
