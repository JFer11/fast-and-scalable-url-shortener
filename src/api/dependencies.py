from typing import AsyncGenerator

from fastapi import Depends, Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession


from src.core.database import AsyncSessionLocal
from src.core.security import AuthManager
from src.core.config import settings
from src.models import User


async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


async def get_redis() -> AsyncGenerator[Redis, None]:
    async with Redis.from_url(
        f"redis://{settings.redis_host}:{settings.redis_port}",
        encoding="utf-8", decode_responses=True
    ) as redis_:
        yield redis_


async def get_user(request: Request, session: AsyncSession = Depends(db_session)) -> User:
    manager = AuthManager()
    return await manager(request=request, session=session)
