from typing import Generator

import pytest
from unittest.mock import patch
from redis import Redis

from src.celery.tasks import increment_click_count
from src.core.database import SQLBase
from src.core.security import AuthManager
from src.models.url import Url
from src.tests.base import engine, client, TestingSessionLocal

redis_ = Redis.from_url("redis://redis:6379", encoding="utf-8", decode_responses=True)


@pytest.fixture(autouse=True)
def prepare_and_cleanup_db() -> Generator[None, None, None]:
    """
    A pytest fixture to set up the database before each test and clean up after.
    It also clears client cookies and headers to ensure a clean state for HTTP requests.
    """
    try:
        SQLBase.metadata.create_all(bind=engine)
        redis_.flushall()
        yield
    finally:
        SQLBase.metadata.drop_all(bind=engine)
        client.cookies.pop(AuthManager.cookie_name, None)
        client.headers.pop(AuthManager.header_name, None)


@pytest.fixture()
def mock_increment_click_count():
    def _mock(shortened_url):
        with TestingSessionLocal() as session:
            url = Url.objects(session).get(Url.shortened_url == shortened_url)
            url.clicks += 1
            session.commit()
            return url.clicks

    with patch.object(increment_click_count, 'delay', side_effect=_mock):
        yield
