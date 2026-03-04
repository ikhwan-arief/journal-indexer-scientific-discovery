from pydantic import BaseModel


class ArticleRead(BaseModel):
    id: int
    endpoint_id: int
    title: str
    authors: list[str]
    abstract: str
    doi: str
    article_url: str
    year: int
    language: str
    rights: str
    oai_identifier: str


class ArticleSearchResponse(BaseModel):
    total: int
    items: list[ArticleRead]
