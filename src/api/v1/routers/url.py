from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
from redis.asyncio import Redis

from src.api.dependencies import db_session, get_redis, get_user
from src.api.v1.schemas import Url, UrlCreate
from src.controllers import UrlController
from src.core.database import Session
from src.models import User
from src import models

router = APIRouter()


@router.get("", response_model=Page[Url])
def get_shortened_urls(
    include_deleted : bool = False, user: User = Depends(get_user), session: Session = Depends(db_session)
) -> Any:
    return paginate(session, user.get_urls(include_deleted))


@router.get("/{shortened_url}", response_model=Url)
def get_shortened_url_data(
    shortened_url : str,
    user: User = Depends(get_user),
    session: Session = Depends(db_session)
) -> Any:
    url = models.Url.objects(session).get(models.Url.shortened_url == shortened_url, models.Url.owner_id == user.id)
    if not url:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="URL not found or you do not have permission to modify it.")
    return url


@router.post("", response_model=Url, status_code=status.HTTP_201_CREATED)
def create_shortened_url(
    url_data: UrlCreate,
    alias: str | None = None,
    user: User = Depends(get_user),
    session: Session = Depends(db_session),
) -> Any:
    return UrlController.create(url_data=url_data, owner_id=user.id, alias=alias, session=session)


@router.delete("/{shortened_url}", response_model=Url, status_code=status.HTTP_202_ACCEPTED)
async def delete_shortened_url(
    shortened_url : str,
    user: User = Depends(get_user),
    redis: Redis = Depends(get_redis),
    session: Session = Depends(db_session),
) -> Any:
    url = UrlController.deactivate(shortened_url=shortened_url, owner_id=user.id, session=session)
    await redis.delete(f"url:{shortened_url}")
    return url
