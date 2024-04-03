from typing import Iterator

from fastapi import Depends, Request
import redis.asyncio as redis

from src.core.database import Session, SessionLocal
from src.core.security import AuthManager
from src.core.config import settings
from src.models import User


def db_session() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_redis():
    redis_ = redis.Redis.from_url(f"redis://{settings.redis_host}:{settings.redis_port}", encoding="utf-8", decode_responses=True)
    try:
        yield redis_
    finally:
        await redis_.close()


def get_user(request: Request, session: Session = Depends(db_session)) -> User:
    manager = AuthManager()
    return manager(request=request, session=session)
