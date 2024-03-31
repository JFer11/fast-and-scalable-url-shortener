from uuid import UUID

from fastapi import HTTPException

from src import models
from src.api.v1 import schemas
from src.core.database import Session
from src.models import Url
from src.core.url_shortener import generate_unique_shortened_url


class UrlController:
    @staticmethod
    def create(
        url_data: schemas.UrlCreate, owner_id: UUID, session: Session
    ) -> models.Url:
        shortened_url = generate_unique_shortened_url(session, url_data.original_url)
        url_data = schemas.Url(
            original_url=url_data.original_url,
            shortened_url=shortened_url,
            is_active=True,
            clicks=0,
            owner_id=owner_id,
        )
        url = models.Url.objects(session).create(url_data.dict())
        return url
    
    @staticmethod
    def deactivate(
        shortened_url: str, owner_id: UUID, session: Session
    ) -> models.Url:
        url = Url.objects(session).get(Url.shortened_url == shortened_url, Url.owner_id == owner_id, Url.is_active == True)
        if not url:
            raise HTTPException(status_code=404, detail="URL not found or you do not have permission to modify it.")
        url.is_active = False
        session.commit()
        return url
