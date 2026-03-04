import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import db_session, require_curator_or_admin
from app.models.article import Article
from app.models.endpoint import Endpoint
from app.models.journal_profile import JournalProfile
from app.schemas.common import MessageResponse
from app.schemas.endpoint import EndpointBatchUpload, EndpointCreate, EndpointRead
from app.services.harvest import parse_harvested_articles, parse_identify, parse_metadata_formats

router = APIRouter(prefix="/endpoints", tags=["endpoints"])


def _to_read_model(endpoint: Endpoint) -> EndpointRead:
    return EndpointRead(
        id=endpoint.id,
        journal_name=endpoint.journal_name,
        category=endpoint.category,
        oai_url=endpoint.oai_url,
        repository_name=endpoint.repository_name,
        metadata_prefix=endpoint.metadata_prefix,
        admin_email=endpoint.admin_email,
        metadata_formats=json.loads(endpoint.metadata_formats_json or "[]"),
        created_at=endpoint.created_at,
    )


@router.get("", response_model=list[EndpointRead])
def list_endpoints(db: Session = Depends(db_session), _: object = Depends(require_curator_or_admin)) -> list[EndpointRead]:
    rows = db.scalars(select(Endpoint).order_by(Endpoint.id.desc())).all()
    return [_to_read_model(row) for row in rows]


@router.post("", response_model=EndpointRead)
def create_endpoint(
    payload: EndpointCreate,
    db: Session = Depends(db_session),
    _: object = Depends(require_curator_or_admin),
) -> EndpointRead:
    exists = db.scalar(select(Endpoint).where(Endpoint.oai_url == str(payload.oai_url)))
    if exists:
        raise HTTPException(status_code=400, detail="Endpoint already exists")

    endpoint = Endpoint(
        journal_name=payload.journal_name,
        category=payload.category,
        oai_url=str(payload.oai_url),
        repository_name="",
        metadata_prefix="oai_dc",
        admin_email="",
        metadata_formats_json="[]",
    )
    db.add(endpoint)
    db.commit()
    db.refresh(endpoint)
    return _to_read_model(endpoint)


@router.post("/batch", response_model=MessageResponse)
def batch_upload_endpoints(
    payload: EndpointBatchUpload,
    db: Session = Depends(db_session),
    _: object = Depends(require_curator_or_admin),
) -> MessageResponse:
    added = 0
    for url in payload.urls:
        exists = db.scalar(select(Endpoint).where(Endpoint.oai_url == str(url)))
        if exists:
            continue
        endpoint = Endpoint(
            journal_name="",
            category="Uncategorized",
            oai_url=str(url),
            repository_name="",
            metadata_prefix="oai_dc",
            admin_email="",
            metadata_formats_json="[]",
        )
        db.add(endpoint)
        added += 1

    db.commit()
    return MessageResponse(message=f"Batch upload completed. Added {added} endpoint(s)")


@router.post("/{endpoint_id}/sync", response_model=EndpointRead)
def sync_endpoint_profile(
    endpoint_id: int,
    db: Session = Depends(db_session),
    _: object = Depends(require_curator_or_admin),
) -> EndpointRead:
    endpoint = db.get(Endpoint, endpoint_id)
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")

    identify = parse_identify(endpoint.oai_url)
    formats = parse_metadata_formats(endpoint.oai_url)

    endpoint.repository_name = identify.get("repository_name") or endpoint.repository_name
    endpoint.admin_email = identify.get("admin_email") or endpoint.admin_email
    endpoint.metadata_formats_json = json.dumps(formats, ensure_ascii=False)
    endpoint.metadata_prefix = "oai_dc" if "oai_dc" in formats else formats[0]
    endpoint.journal_name = endpoint.journal_name or endpoint.repository_name or endpoint.oai_url

    profile = db.scalar(select(JournalProfile).where(JournalProfile.endpoint_id == endpoint.id))
    if not profile:
        profile = JournalProfile(
            endpoint_id=endpoint.id,
            category=endpoint.category,
            accreditation_rank="Unaccredited",
            indexes_json=json.dumps(["Unindexed"], ensure_ascii=False),
            publisher=endpoint.repository_name,
            issn="",
            is_deleted="false",
        )
        db.add(profile)

    db.commit()
    db.refresh(endpoint)
    return _to_read_model(endpoint)


@router.post("/{endpoint_id}/harvest", response_model=MessageResponse)
def harvest_endpoint(
    endpoint_id: int,
    db: Session = Depends(db_session),
    _: object = Depends(require_curator_or_admin),
) -> MessageResponse:
    endpoint = db.get(Endpoint, endpoint_id)
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")

    db.query(Article).filter(Article.endpoint_id == endpoint_id).delete()

    articles = parse_harvested_articles(
        endpoint_id=endpoint_id,
        oai_url=endpoint.oai_url,
        metadata_prefix=endpoint.metadata_prefix or "oai_dc",
    )
    for article in articles:
        db.add(article)

    db.commit()
    return MessageResponse(message=f"Harvest completed. Saved {len(articles)} article(s)")


@router.delete("/{endpoint_id}", response_model=MessageResponse)
def delete_endpoint(
    endpoint_id: int,
    db: Session = Depends(db_session),
    _: object = Depends(require_curator_or_admin),
) -> MessageResponse:
    endpoint = db.get(Endpoint, endpoint_id)
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")

    db.delete(endpoint)
    db.commit()
    return MessageResponse(message="Endpoint deleted")
