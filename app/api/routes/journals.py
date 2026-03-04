import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import db_session, require_curator_or_admin
from app.models.endpoint import Endpoint
from app.models.journal_profile import JournalProfile
from app.schemas.journal import JournalProfileRead, JournalProfileUpdate

router = APIRouter(prefix="/journals", tags=["journals"])


@router.get("", response_model=list[JournalProfileRead])
def list_journals(db: Session = Depends(db_session), _: object = Depends(require_curator_or_admin)) -> list[JournalProfileRead]:
    rows = db.execute(
        select(Endpoint, JournalProfile)
        .join(JournalProfile, JournalProfile.endpoint_id == Endpoint.id, isouter=True)
        .order_by(Endpoint.journal_name)
    ).all()

    items: list[JournalProfileRead] = []
    for endpoint, profile in rows:
        indexes = json.loads(profile.indexes_json) if profile and profile.indexes_json else []
        items.append(
            JournalProfileRead(
                endpoint_id=endpoint.id,
                journal_name=endpoint.journal_name,
                category=profile.category if profile else endpoint.category,
                accreditation_rank=profile.accreditation_rank if profile else "Unaccredited",
                indexes=indexes,
                publisher=profile.publisher if profile else endpoint.repository_name,
                issn=profile.issn if profile else "",
                is_deleted=(profile.is_deleted == "true") if profile else False,
            )
        )
    return items


@router.put("/{endpoint_id}", response_model=JournalProfileRead)
def update_journal_profile(
    endpoint_id: int,
    payload: JournalProfileUpdate,
    db: Session = Depends(db_session),
    _: object = Depends(require_curator_or_admin),
) -> JournalProfileRead:
    endpoint = db.get(Endpoint, endpoint_id)
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")

    profile = db.scalar(select(JournalProfile).where(JournalProfile.endpoint_id == endpoint_id))
    if not profile:
        profile = JournalProfile(endpoint_id=endpoint_id)
        db.add(profile)

    profile.category = payload.category
    profile.accreditation_rank = payload.accreditation_rank
    profile.indexes_json = json.dumps(payload.indexes, ensure_ascii=False)

    db.commit()
    db.refresh(profile)

    return JournalProfileRead(
        endpoint_id=endpoint.id,
        journal_name=endpoint.journal_name,
        category=profile.category,
        accreditation_rank=profile.accreditation_rank,
        indexes=json.loads(profile.indexes_json),
        publisher=profile.publisher,
        issn=profile.issn,
        is_deleted=profile.is_deleted == "true",
    )
