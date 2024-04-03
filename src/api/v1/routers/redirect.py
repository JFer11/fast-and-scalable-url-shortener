import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from redis.asyncio import Redis

from src.api.dependencies import db_session, get_redis
from src.core.database import Session
from src.models import Url
from src.celery.tasks import increment_click_count

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{shortened_url}", status_code=status.HTTP_302_FOUND, include_in_schema=False)
async def redirect(
    shortened_url: str,
    redis: Redis = Depends(get_redis),
    session: Session = Depends(db_session)
) -> RedirectResponse:
    logger.info(f"Retrieving original URL for shortened URL '{shortened_url}' from Redis cache.")  # Log Redis retrieval for demo purposes, showcasing cache usage.
    original_url = await redis.get(f"url:{shortened_url}")
    if original_url is None:
        logger.info(f"Original URL for shortened URL '{shortened_url}' not found in Redis cache. Attempting to retrieve from database.")  # Log Redis retrieval for demo purposes, showcasing cache usage.
        url = Url.objects(session).get(Url.shortened_url == shortened_url, Url.is_active == True)
        if not url:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="URL not found.")
        original_url = url.original_url
        await redis.set(f"url:{shortened_url}", original_url, ex=3600)
    else:
        logger.info(f"Found original URL '{original_url}' for shortened URL '{shortened_url}' in Redis cache.")  # Log Redis retrieval for demo purposes, showcasing cache usage.
    increment_click_count.delay(shortened_url)
    return RedirectResponse(url=original_url, status_code=status.HTTP_302_FOUND)
