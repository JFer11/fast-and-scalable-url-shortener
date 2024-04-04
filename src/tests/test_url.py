import time
from typing import Any, Dict, Generator
from unittest.mock import MagicMock, patch
import pytest

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from src.celery.tasks import increment_click_count
from src.tests.base import BASE_URL
from src.models import Url, User
from src.core.security import PasswordManager


class TestURL:
    URL_ENDPOINT = f"{BASE_URL}/urls"
    REDIRECT_ENDPOINT = f"{BASE_URL}/redirect"

    VALID_URL = "https://example.com"
    INVALID_URL = "http://invalid_url"
    
    TEST_USER_EMAIL = "test@test.com"
    TEST_USER_PASSWORD = "password"

    @classmethod
    async def setup_user(cls, session: AsyncSession, email: str = TEST_USER_EMAIL, password: str = TEST_USER_PASSWORD) -> None:
        hashed_password = PasswordManager.get_password_hash(password)
        user_data = {
            "email": email,
            "password": hashed_password,
            "is_active": True,
            "is_superuser": False,
        }
        await User.objects(session).create(user_data)

    @classmethod
    async def authenticate(cls, client: AsyncClient, email: str = TEST_USER_EMAIL, password: str = TEST_USER_PASSWORD) -> None:
        response = await client.post(f"{BASE_URL}/users/login", json={"email": email, "password": password})
        token = response.json()["access_token"]
        client.headers.update({"Authorization": f"Bearer {token}"})
        
    async def logout(self, client: AsyncClient) -> None:
        client.cookies.clear()
        client.headers.pop("Authorization", None)

    async def create_url(self, client: AsyncClient, url: str = VALID_URL, deactivate: bool = False) -> str:
        create_response = await client.post(self.URL_ENDPOINT, json={"original_url": url})
        short_url = create_response.json()["shortened_url"]
        if deactivate:
            await client.delete(f"{self.URL_ENDPOINT}/{short_url}")
        return short_url

    @pytest.fixture(autouse=True)
    async def authenticate_test_client(self, client: AsyncClient, session: AsyncSession) -> Generator:
        await self.setup_user(session)
        await self.authenticate(client)
        yield
        await self.logout(client)


@pytest.mark.anyio
class TestCreateUrl(TestURL):
    async def test_create_shortened_url(self, client, session):
        response = await client.post(self.URL_ENDPOINT, json={"original_url": self.VALID_URL})
        assert response.status_code == 201
        data = response.json()
        assert "shortened_url" in data
        assert data["original_url"] == self.VALID_URL
        url = await Url.objects(session).get(Url.original_url == self.VALID_URL)
        assert url is not None
        assert url.is_active is True
        assert url.clicks == 0

    async def test_handling_invalid_url(self, client):
        response = await client.post(self.URL_ENDPOINT, json={"original_url": self.INVALID_URL})
        assert response.status_code == 422
        assert "detail" in response.json()
        
    async def test_create_shortened_url_with_custom_alias(self, client):
        custom_alias = "zapiaai"
        response = await client.post(self.URL_ENDPOINT, params={"alias": custom_alias}, json={"original_url": self.VALID_URL})
        assert response.status_code == 201
        data = response.json()
        assert data["shortened_url"] == custom_alias

    async def test_create_shortened_url_with_duplicate_alias(self, client):
        custom_alias = "zapiaai"
        await client.post(self.URL_ENDPOINT, params={"alias": custom_alias}, json={"original_url": self.VALID_URL})
        response_duplicated_alias = await client.post(self.URL_ENDPOINT, params={"alias": custom_alias}, json={"original_url": self.VALID_URL + "/dup"})
        assert response_duplicated_alias.status_code == 409
        assert "detail" in response_duplicated_alias.json()
        assert response_duplicated_alias.json()["detail"] == "The provided alias is already in use."

    @pytest.mark.parametrize(
        "invalid_alias",
        [
            "little",  # Invalid because the alias is too short. Aliases must be at least 7 characters long.
            "!nv@lid",  # Invalid because of special characters. Only alphanumeric characters are allowed.
        ]
    )
    async def test_create_shortened_url_with_invalid_aliases(self, invalid_alias, client):
        response = await client.post(self.URL_ENDPOINT, params={"alias": invalid_alias}, json={"original_url": self.VALID_URL})
        assert response.status_code == 400
        assert "detail" in response.json()
        assert response.json()["detail"] == "Alias must be at least 7 characters long and only contain alphanumeric characters."


@pytest.mark.anyio
class TestRetrieveUrlData(TestURL):
    ERROR_MESSAGE = "URL not found or you do not have permission to modify it."
    
    async def validate_payload_response(self, session: AsyncSession, short_url: str, data: Dict[str, Any], is_active: bool):
        assert data["original_url"] == self.VALID_URL
        assert data["is_active"] == is_active
        assert data["clicks"] == 0
        url = await Url.objects(session).get(Url.shortened_url == short_url)
        assert str(url.owner_id) == data["owner_id"]
        
    async def test_retrieve_shortened_url_data(self, client, session):
        short_url = await self.create_url(client)
        response = await client.get(f"{self.URL_ENDPOINT}/{short_url}")
        assert response.status_code == 200
        data = response.json()
        await self.validate_payload_response(session, short_url, data, is_active=True)

    async def test_error_for_nonexistent_url(self, client):
        response = await client.get(f"{self.URL_ENDPOINT}/nonexistenturl")
        assert response.status_code == 404
        assert "detail" in response.json()
        assert response.json()["detail"] == self.ERROR_MESSAGE

    async def test_retrieve_deactivated_url(self, client, session):
        short_url = await self.create_url(client, deactivate=True)
        response = await client.get(f"{self.URL_ENDPOINT}/{short_url}")
        assert response.status_code == 200
        data = response.json()
        await self.validate_payload_response(session, short_url, data, is_active=False)


@pytest.mark.anyio
class TestRetrieveUrls(TestURL):
    async def test_retrieve_active_urls_only(self, client):
        await self.create_url(client)
        short_url_deactivated = await self.create_url(client, self.VALID_URL + "/deactivated", deactivate=True)
        response = await client.get(self.URL_ENDPOINT)
        assert response.status_code == 200
        urls = response.json()["items"]
        assert all(url["is_active"] for url in urls)
        assert all(short_url_deactivated not in url["shortened_url"] for url in urls)        
        assert len(urls) == 1
        
    async def test_retrieve_including_deactivated_urls(self, client):
        await self.create_url(client)
        await self.create_url(client, self.VALID_URL + "/deactivated", deactivate=True)
        response = await client.get(f"{self.URL_ENDPOINT}", params={"include_deleted": True})
        assert response.status_code == 200
        urls = response.json()["items"]
        assert any(url["is_active"] == False for url in urls)
        assert any(url["is_active"] == True for url in urls)
        assert len(urls) == 2

    async def test_retrieve_urls_for_authenticated_user_only(self, client, session):
        await self.create_url(client)
        await self.logout(client)
        await self.setup_user(session, email="new-user@test.com", password="new-password")
        await self.authenticate(client, email="new-user@test.com", password="new-password")
        response = await client.get(self.URL_ENDPOINT)
        assert response.status_code == 200
        urls = response.json()["items"]
        assert len(urls) == 0


@pytest.mark.anyio
class TestDeleteUrl(TestURL):
    ERROR_MESSAGE = "URL not found or you do not have permission to modify it."
    
    async def test_deactivate_shortened_url(self, client, session):
        short_url = await self.create_url(client)
        deactivate_response = await client.delete(f"{self.URL_ENDPOINT}/{short_url}")
        assert deactivate_response.status_code == 202
        url = await Url.objects(session).get(Url.shortened_url == short_url)
        assert url.is_active == False

    async def test_try_deactivate_shortened_url_twice(self, client):
        short_url = await self.create_url(client)
        first_deactivate_response = await client.delete(f"{self.URL_ENDPOINT}/{short_url}")
        assert first_deactivate_response.status_code == 202
        second_deactivate_response = await client.delete(f"{self.URL_ENDPOINT}/{short_url}")
        assert second_deactivate_response.status_code == 404
        assert "detail" in second_deactivate_response.json()
        assert self.ERROR_MESSAGE in second_deactivate_response.json()["detail"]

    async def test_unauthorized_url_deactivation(self, client, session):
        short_url = await self.create_url(client)
        await self.logout(client)
        await self.setup_user(session, email="new-user@test.com", password="new-password")
        await self.authenticate(client, email="new-user@test.com", password="new-password")
        deactivate_response = await client.delete(f"{self.URL_ENDPOINT}/{short_url}")
        assert deactivate_response.status_code == 404
        assert "detail" in deactivate_response.json()
        assert self.ERROR_MESSAGE in deactivate_response.json()["detail"]


@pytest.mark.anyio
class TestRedirectUrl(TestURL):
    ERROR_MESSAGE = "URL not found."

    async def test_redirect_to_original_url(self, client, mock_increment_click_count):
        short_url = await self.create_url(client)
        response = await client.get(f"{self.REDIRECT_ENDPOINT}/{short_url}", follow_redirects=False)
        assert response.status_code == 302
        assert response.headers["location"] == self.VALID_URL

    async def test_redirect_to_nonexistent_url(self, client):
        nonexistent_short_url = "nonexistent"
        response = await client.get(f"{self.REDIRECT_ENDPOINT}/{nonexistent_short_url}", follow_redirects=False)
        assert response.status_code == 404
        assert "detail" in response.json()
        assert response.json()["detail"] == self.ERROR_MESSAGE
        
    async def test_redirect_to_deactivated_url(self, client):
        short_url = await self.create_url(client, deactivate=True)
        response = await client.get(f"{self.REDIRECT_ENDPOINT}/{short_url}", follow_redirects=False)
        assert response.status_code == 404
        assert "detail" in response.json()
        assert response.json()["detail"] == self.ERROR_MESSAGE
        

@pytest.mark.anyio
class TestURLIntegration(TestURL):
    async def test_url_lifecycle(self, client, mock_increment_click_count):
        """
        Test the complete lifecycle of a URL: creation, retrieval,
        redirection, verifying click count, deactivation, and access post-deactivation.
        """
        # Step 1: Create a new URL
        create_response = await client.post(f"{BASE_URL}/urls", json={"original_url": self.VALID_URL})
        assert create_response.status_code == 201, "Failed to create URL"
        create_data = create_response.json()
        assert "shortened_url" in create_data, "Shortened URL key missing in response"
        short_url = create_data["shortened_url"].split('/')[-1]

        # Step 2: Retrieve the created URL's data
        retrieve_response = await client.get(f"{BASE_URL}/urls/{short_url}")
        assert retrieve_response.status_code == 200, "Failed to retrieve URL data"
        url_data = retrieve_response.json()
        assert url_data["original_url"] == self.VALID_URL, "Original URL does not match"
        assert url_data["is_active"], "URL should be active"
        initial_clicks = url_data["clicks"]
        assert initial_clicks == 0, "Initial click count should be 0"

        # Step 3: Redirect to the URL
        redirect_response = await client.get(f"{BASE_URL}/redirect/{short_url}", follow_redirects=False)
        assert redirect_response.status_code == 302, "Redirection failed"
        assert redirect_response.headers["Location"] == self.VALID_URL, "Redirection URL mismatch"

        # Step 4: Deactivate the URL
        deactivate_response = await client.delete(f"{BASE_URL}/urls/{short_url}")
        assert deactivate_response.status_code == 202, "URL deactivation failed"

        # Step 5: Verify the URL is deactivated
        post_deactivate_retrieve_response = await client.get(f"{BASE_URL}/urls/{short_url}")
        assert post_deactivate_retrieve_response.status_code == 200, "Failed to retrieve URL data after deactivation"
        post_deactivate_url_data = post_deactivate_retrieve_response.json()
        assert not post_deactivate_url_data["is_active"], "URL should be deactivated"

        # Step 6: Attempt to redirect to the deactivated URL and verify failure
        redirect_post_deactivate_response = await client.get(f"{BASE_URL}/redirect/{short_url}", follow_redirects=False)
        assert redirect_post_deactivate_response.status_code == 404, "Redirection to deactivated URL should fail"
