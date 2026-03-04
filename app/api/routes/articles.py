import json

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.deps import db_session, require_curator_or_admin
from app.models.article import Article
from app.schemas.article import ArticleRead, ArticleSearchResponse

router = APIRouter(prefix="/articles", tags=["articles"])


@router.get("", response_model=ArticleSearchResponse)
def list_articles(
    q: str = Query(default=""),
    endpoint_id: int | None = None,
    db: Session = Depends(db_session),
    _: object = Depends(require_curator_or_admin),
) -> ArticleSearchResponse:
    stmt = select(Article)
    if endpoint_id:
        stmt = stmt.where(Article.endpoint_id == endpoint_id)

    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(or_(Article.title.ilike(pattern), Article.authors_json.ilike(pattern)))

    rows = db.scalars(stmt.order_by(Article.id.desc())).all()
    items = [
        ArticleRead(
            id=row.id,
            endpoint_id=row.endpoint_id,
            title=row.title,
            authors=json.loads(row.authors_json or "[]"),
            abstract=row.abstract,
            doi=row.doi,
            article_url=row.article_url,
            year=row.year,
            language=row.language,
            rights=row.rights,
            oai_identifier=row.oai_identifier,
        )
        for row in rows
    ]

    return ArticleSearchResponse(total=len(items), items=items)
