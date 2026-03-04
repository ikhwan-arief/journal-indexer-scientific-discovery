from datetime import datetime

from pydantic import BaseModel, HttpUrl


class EndpointCreate(BaseModel):
    journal_name: str
    category: str = "Uncategorized"
    oai_url: HttpUrl


class EndpointRead(BaseModel):
    id: int
    journal_name: str
    category: str
    oai_url: str
    repository_name: str
    metadata_prefix: str
    admin_email: str
    metadata_formats: list[str]
    created_at: datetime

    class Config:
        from_attributes = True


class EndpointBatchUpload(BaseModel):
    urls: list[HttpUrl]
