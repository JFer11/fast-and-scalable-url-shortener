from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_pagination import Page, paginate
from redis.asyncio import Redis

from src.api.dependencies import db_session, get_redis, get_user
from src.api.v1.schemas import Url, UrlCreate
from src.controllers import UrlController
from src.core.database import AsyncSession
from src.models import User
from src import models

router = APIRouter()


@router.get("", response_model=Page[Url])
async def get_shortened_urls(
    include_deleted : bool = False, user: User = Depends(get_user), session: AsyncSession = Depends(db_session)
) -> Any:
    urls = await user.get_urls(session=session, include_deleted=include_deleted)
    return paginate(urls)


@router.get("/{shortened_url}", response_model=Url)
async def get_shortened_url_data(
    shortened_url : str,
    user: User = Depends(get_user),
    session: AsyncSession = Depends(db_session)
) -> Any:
    url = await models.Url.objects(session).get(models.Url.shortened_url == shortened_url, models.Url.owner_id == user.id)
    if not url:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="URL not found or you do not have permission to modify it.")
    return url


@router.post("", response_model=Url, status_code=status.HTTP_201_CREATED)
async def create_shortened_url(
    url_data: UrlCreate,
    alias: str | None = None,
    user: User = Depends(get_user),
    session: AsyncSession = Depends(db_session),
) -> Any:
    return await UrlController.create(url_data=url_data, owner_id=user.id, alias=alias, session=session)


@router.delete("/{shortened_url}", response_model=Url, status_code=status.HTTP_202_ACCEPTED)
async def delete_shortened_url(
    shortened_url : str,
    user: User = Depends(get_user),
    redis: Redis = Depends(get_redis),
    session: AsyncSession = Depends(db_session),
) -> Any:
    url = await UrlController.deactivate(shortened_url=shortened_url, owner_id=user.id, session=session)
    await redis.delete(f"url:{shortened_url}")
    return url
