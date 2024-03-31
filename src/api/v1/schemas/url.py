from uuid import UUID

from pydantic import BaseModel, HttpUrl


class UrlCreate(BaseModel):
    original_url: HttpUrl


class Url(UrlCreate):
    shortened_url: str
    is_active: bool
    clicks: int
    owner_id: UUID

    class Config:
        orm_mode = True
