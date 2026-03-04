from pydantic import BaseModel


class JournalProfileUpdate(BaseModel):
    category: str
    accreditation_rank: str
    indexes: list[str]


class JournalProfileRead(BaseModel):
    endpoint_id: int
    journal_name: str
    category: str
    accreditation_rank: str
    indexes: list[str]
    publisher: str
    issn: str
    is_deleted: bool
