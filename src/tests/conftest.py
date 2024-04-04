from typing import AsyncGenerator, Generator

import pytest
from unittest.mock import MagicMock, Mock, patch
from httpx import AsyncClient
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker, AsyncEngine
from sqlalchemy.exc import NoResultFound
from redis.asyncio import Redis

from src.api.dependencies import db_session
from src.core.database import SQLBase
from src.core.config import settings
from src.main import app
from src.models.url import Url


@pytest.fixture
def anyio_backend():
    return 'asyncio'


@pytest.fixture(scope="session")
def engine() -> Generator[AsyncEngine, None, None]:
    database_url = settings.test_database_url
    assert database_url is not None, "TEST_DATABASE_URL must be defined"
    engine = create_async_engine(
        database_url,
        poolclass=NullPool,
    )
    yield engine
    engine.sync_engine.dispose()


@pytest.fixture
async def reset_database(engine: AsyncEngine) -> AsyncGenerator[None, None]:
    redis_ = Redis.from_url(f"redis://{settings.redis_host}:{settings.redis_port}", encoding="utf-8", decode_responses=True)
    await redis_.flushall()
    async with engine.begin() as conn:
        await conn.run_sync(SQLBase.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(SQLBase.metadata.drop_all)


@pytest.fixture
async def session(engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    AsyncTestingSessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=AsyncSession, future=True)
    async with AsyncTestingSessionLocal() as session:
        yield session


@pytest.fixture(autouse=True)
async def override_get_db_dependency(reset_database: AsyncGenerator[None, None], session: AsyncSession) -> AsyncGenerator[None, None]:
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield session
    app.dependency_overrides[db_session] = override_get_db


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


async def _increment_click_count(shortened_url: str, session: AsyncSession):
    async with session.begin():
        url = await Url.objects.get(Url.shortened_url == shortened_url)
        if url:
            url.clicks += 1
            await session.commit()
            await session.refresh(url)
            return url.clicks
        raise NoResultFound(f"No Url found for shortened_url: {shortened_url}")


@pytest.fixture()
async def mock_increment_click_count(session: AsyncSession):
    mock_task = MagicMock()

    async def mock_delay(shortened_url):
        return await _increment_click_count(shortened_url, session)

    mock_task.delay.side_effect = mock_delay

    with patch('src.api.v1.routers.redirect.increment_click_count', new=mock_task):
        yield
