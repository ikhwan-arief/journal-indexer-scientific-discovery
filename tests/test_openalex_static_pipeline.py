from __future__ import annotations

from journal_discovery.openalex_static.database import OpenAlexDatabase
from journal_discovery.openalex_static.pipeline import OpenAlexIngestionPipeline


class FixtureClient:
    operation_count = 0

    def get_json(self, path: str, params: dict[str, object] | None = None) -> dict[str, object]:
        self.operation_count += 1
        if path == "/sources":
            return {
                "results": [{
                    "id": "https://openalex.org/S123",
                    "display_name": "Safe Journal",
                    "issn_l": "2049-3630",
                    "issn": ["2049-3630"],
                    "host_organization_name": "Publisher",
                    "country_code": "ID",
                }]
            }
        if path == "/works":
            return {
                "results": [{
                    "id": "https://openalex.org/W456",
                    "doi": "https://doi.org/10.1234/example",
                    "title": "<script>alert(1)</script> Machine learning evidence",
                    "publication_year": 2026,
                    "cited_by_count": 3,
                    "primary_location": {"source": {"id": "https://openalex.org/S123"}},
                    "topics": [{
                        "id": "https://openalex.org/T789",
                        "display_name": "Machine Learning",
                        "score": 0.9,
                        "subfield": {"display_name": "AI"},
                        "field": {"display_name": "Computer Science"},
                        "domain": {"display_name": "Physical Sciences"},
                    }],
                }]
            }
        raise AssertionError(f"Unexpected path: {path}")


def test_pipeline_builds_static_enrichment_from_validated_fixture(tmp_path) -> None:
    database = OpenAlexDatabase(tmp_path / "openalex.sqlite3")
    pipeline = OpenAlexIngestionPipeline(database, FixtureClient())
    result = pipeline.refresh(
        [{
            "legacy_sourceid": "123",
            "title": "Safe Journal",
            "publisher": "Publisher",
            "country": "Indonesia",
            "issns": ["2049-3630"],
        }],
        max_journals=1,
        works_per_journal=5,
    )
    assert result == {"matched_journals": 1, "works_saved": 1, "operations": 2}
    public = database.public_enrichment()["123"]
    assert public["openalex_source_id"] == "S123"
    assert public["openalex_topics"][0]["id"] == "T789"
    assert public["openalex_evidence"][0]["openalex_work_id"] == "W456"
