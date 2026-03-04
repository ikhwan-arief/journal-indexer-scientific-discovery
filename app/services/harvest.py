from __future__ import annotations

import json
from urllib.parse import quote
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

from app.models.article import Article


def _text(el: ET.Element | None) -> str:
    return (el.text or "").strip() if el is not None else ""


def _fetch(url: str) -> str:
    req = Request(url, headers={"User-Agent": "ScientificDiscoveryHarvester/1.0", "Accept": "application/xml,text/xml,*/*"})
    with urlopen(req, timeout=40) as response:
        return response.read().decode("utf-8", errors="replace")


def build_list_records_url(base_url: str, metadata_prefix: str, resumption_token: str | None = None) -> str:
    sep = "&" if "?" in base_url else "?"
    if resumption_token:
        return f"{base_url}{sep}verb=ListRecords&resumptionToken={quote(resumption_token)}"
    return f"{base_url}{sep}verb=ListRecords&metadataPrefix={quote(metadata_prefix)}"


def build_identify_url(base_url: str) -> str:
    sep = "&" if "?" in base_url else "?"
    return f"{base_url}{sep}verb=Identify"


def build_list_formats_url(base_url: str) -> str:
    sep = "&" if "?" in base_url else "?"
    return f"{base_url}{sep}verb=ListMetadataFormats"


def parse_identify(base_url: str) -> dict:
    xml = _fetch(build_identify_url(base_url))
    root = ET.fromstring(xml)
    repo_name = ""
    admin_email = ""
    earliest = ""
    deleted_record = "persistent"
    granularity = "YYYY-MM-DDThh:mm:ssZ"

    for node in root.iter():
        tag = node.tag.split("}")[-1]
        if tag == "repositoryName" and not repo_name:
            repo_name = _text(node)
        elif tag == "adminEmail" and not admin_email:
            admin_email = _text(node)
        elif tag == "earliestDatestamp" and not earliest:
            earliest = _text(node)
        elif tag == "deletedRecord" and deleted_record == "persistent":
            deleted_record = _text(node) or deleted_record
        elif tag == "granularity" and granularity == "YYYY-MM-DDThh:mm:ssZ":
            granularity = _text(node) or granularity

    return {
        "repository_name": repo_name,
        "admin_email": admin_email,
        "earliest_datestamp": earliest,
        "deleted_record": deleted_record,
        "granularity": granularity,
    }


def parse_metadata_formats(base_url: str) -> list[str]:
    try:
        xml = _fetch(build_list_formats_url(base_url))
        root = ET.fromstring(xml)
        formats: list[str] = []
        for node in root.iter():
            if node.tag.split("}")[-1] == "metadataPrefix":
                value = _text(node)
                if value and value not in formats:
                    formats.append(value)
        return formats or ["oai_dc"]
    except Exception:
        return ["oai_dc"]


def parse_harvested_articles(endpoint_id: int, oai_url: str, metadata_prefix: str = "oai_dc", max_pages: int = 20) -> list[Article]:
    articles: list[Article] = []
    token: str | None = None

    for _ in range(max_pages):
        xml = _fetch(build_list_records_url(oai_url, metadata_prefix, token))
        root = ET.fromstring(xml)

        for rec in root.iter():
            if rec.tag.split("}")[-1] != "record":
                continue

            header = None
            metadata = None
            for child in list(rec):
                tag = child.tag.split("}")[-1]
                if tag == "header":
                    header = child
                elif tag == "metadata":
                    metadata = child

            if header is None or metadata is None:
                continue
            if header.attrib.get("status") == "deleted":
                continue

            oai_identifier = ""
            datestamp = ""
            set_specs: list[str] = []
            for h in header.iter():
                tag = h.tag.split("}")[-1]
                if tag == "identifier" and not oai_identifier:
                    oai_identifier = _text(h)
                elif tag == "datestamp" and not datestamp:
                    datestamp = _text(h)
                elif tag == "setSpec":
                    val = _text(h)
                    if val:
                        set_specs.append(val)

            titles: list[str] = []
            creators: list[str] = []
            descriptions: list[str] = []
            dates: list[str] = []
            identifiers: list[str] = []
            languages: list[str] = []
            rights: list[str] = []

            for m in metadata.iter():
                tag = m.tag.split("}")[-1]
                val = _text(m)
                if not val:
                    continue
                if tag == "title":
                    titles.append(val)
                elif tag == "creator":
                    creators.append(val)
                elif tag == "description":
                    descriptions.append(val)
                elif tag == "date":
                    dates.append(val)
                elif tag == "identifier":
                    identifiers.append(val)
                elif tag == "language":
                    languages.append(val)
                elif tag == "rights":
                    rights.append(val)

            title = titles[0] if titles else "Untitled record"
            year = 0
            if dates:
                for ch in dates[0]:
                    pass
                year_digits = "".join(c for c in dates[0] if c.isdigit())
                year = int(year_digits[:4]) if len(year_digits) >= 4 else 0

            article_url = next((v for v in identifiers if v.startswith("http://") or v.startswith("https://")), "")
            doi = next((v for v in identifiers if "10." in v and "/" in v), "")

            article = Article(
                endpoint_id=endpoint_id,
                title=title,
                authors_json=json.dumps(creators or ["Unknown"], ensure_ascii=False),
                abstract="\n\n".join(descriptions),
                doi=doi,
                article_url=article_url,
                year=year,
                language=languages[0] if languages else "",
                rights=rights[0] if rights else "",
                oai_identifier=oai_identifier or f"{endpoint_id}:{title}",
                datestamp=datestamp,
                set_spec_json=json.dumps(set_specs, ensure_ascii=False),
                identifiers_json=json.dumps(identifiers, ensure_ascii=False),
            )
            articles.append(article)

        next_token = ""
        for node in root.iter():
            if node.tag.split("}")[-1] == "resumptionToken":
                next_token = _text(node)
                break

        if not next_token:
            break
        token = next_token

    return articles
