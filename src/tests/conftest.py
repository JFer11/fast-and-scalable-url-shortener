import pytest
from typing import Generator

from src.core.database import SQLBase
from src.core.security import AuthManager
from src.tests.base import engine, client


@pytest.fixture(autouse=True)
def prepare_and_cleanup_db() -> Generator[None, None, None]:
    """
    A pytest fixture to set up the database before each test and clean up after.
    It also clears client cookies and headers to ensure a clean state for HTTP requests.
    """
    try:
        SQLBase.metadata.create_all(bind=engine)
        yield
    finally:
        SQLBase.metadata.drop_all(bind=engine)
        client.cookies.pop(AuthManager.cookie_name, None)
        client.headers.pop(AuthManager.header_name, None)
