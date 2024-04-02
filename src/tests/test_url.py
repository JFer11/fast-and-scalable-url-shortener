from typing import Any, Dict
import pytest

from src.tests.base import BASE_URL, client, TestingSessionLocal
from src.models import Url, User
from src.core.security import PasswordManager


class TestURL:
    URL_ENDPOINT = f"{BASE_URL}/urls"
    REDIRECT_ENDPOINT = f"{BASE_URL}/redirect"

    VALID_URL = "https://example.com"
    INVALID_URL = "http://invalid_url"
    
    TEST_USER_EMAIL = "test@test.com"
    TEST_USER_PASSWORD = "password"

    def setup_user(self, email: str = TEST_USER_EMAIL, password: str = TEST_USER_PASSWORD) -> None:
        with TestingSessionLocal() as session:
            hashed_password = PasswordManager.get_password_hash(password)
            user_data = {
                "email": email,
                "password": hashed_password,
                "is_active": True,
                "is_superuser": False,
            }
            User.objects(session).create(user_data)

    def authenticate(self, email: str = TEST_USER_EMAIL, password: str = TEST_USER_PASSWORD) -> None:
        response = client.post(f"{BASE_URL}/users/login", json={"email": email, "password": password})
        token = response.json()["access_token"]
        client.headers.update({"Authorization": f"Bearer {token}"})
        
    def logout(self) -> None:
        client.cookies.clear()
        client.headers.pop("Authorization", None)

    def create_url(self, url: str = VALID_URL, deactivate: bool = False) -> str:
        create_response = client.post(self.URL_ENDPOINT, json={"original_url": url})
        short_url = create_response.json()["shortened_url"]
        if deactivate:
            client.delete(f"{self.URL_ENDPOINT}/{short_url}")
        return short_url

    @pytest.fixture(autouse=True)
    def authenticate_test_client(self) -> None:
        self.setup_user()
        self.authenticate()


class TestCreateUrl(TestURL):
    def test_create_shortened_url(self):
        response = client.post(self.URL_ENDPOINT, json={"original_url": self.VALID_URL})
        assert response.status_code == 201
        data = response.json()
        assert "shortened_url" in data
        assert data["original_url"] == self.VALID_URL
        with TestingSessionLocal() as session:
            url = Url.objects(session).get(Url.original_url == self.VALID_URL)
            assert url is not None
            assert url.is_active is True
            assert url.clicks == 0

    def test_handling_invalid_url(self):
        response = client.post(self.URL_ENDPOINT, json={"original_url": self.INVALID_URL})
        assert response.status_code == 422
        assert "detail" in response.json()
        
    def test_create_shortened_url_with_custom_alias(self):
        custom_alias = "zapiaai"
        response = client.post(self.URL_ENDPOINT, params={"alias": custom_alias}, json={"original_url": self.VALID_URL})
        assert response.status_code == 201
        data = response.json()
        assert data["shortened_url"] == custom_alias

    def test_create_shortened_url_with_duplicate_alias(self):
        custom_alias = "zapiaai"
        client.post(self.URL_ENDPOINT, params={"alias": custom_alias}, json={"original_url": self.VALID_URL})
        response_duplicated_alias = client.post(self.URL_ENDPOINT, params={"alias": custom_alias}, json={"original_url": self.VALID_URL + "/dup"})
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
    def test_create_shortened_url_with_invalid_aliases(self, invalid_alias):
        response = client.post(self.URL_ENDPOINT, params={"alias": invalid_alias}, json={"original_url": self.VALID_URL})
        assert response.status_code == 400
        assert "detail" in response.json()
        assert response.json()["detail"] == "Alias must be at least 7 characters long and only contain alphanumeric characters."


class TestRetrieveUrlData(TestURL):
    ERROR_MESSAGE = "URL not found or you do not have permission to modify it."
    
    def validate_payload_response(self, short_url: str, data: Dict[str, Any], is_active: bool):
        assert data["original_url"] == self.VALID_URL
        assert data["is_active"] == is_active
        assert data["clicks"] == 0
        with TestingSessionLocal() as session:
            url = Url.objects(session).get(Url.shortened_url == short_url)
            assert str(url.owner_id) == data["owner_id"]
        
    def test_retrieve_shortened_url_data(self):
        short_url = self.create_url()
        response = client.get(f"{self.URL_ENDPOINT}/{short_url}")
        assert response.status_code == 200
        data = response.json()
        self.validate_payload_response(short_url, data, is_active=True)

    def test_error_for_nonexistent_url(self):
        response = client.get(f"{self.URL_ENDPOINT}/nonexistenturl")
        assert response.status_code == 404
        assert "detail" in response.json()
        assert response.json()["detail"] == self.ERROR_MESSAGE

    def test_retrieve_deactivated_url(self):
        short_url = self.create_url(deactivate=True)
        response = client.get(f"{self.URL_ENDPOINT}/{short_url}")
        assert response.status_code == 200
        data = response.json()
        self.validate_payload_response(short_url, data, is_active=False)


class TestRetrieveUrls(TestURL):
    def test_retrieve_active_urls_only(self):
        self.create_url()
        short_url_deactivated = self.create_url(self.VALID_URL + "/deactivated", deactivate=True)
        response = client.get(self.URL_ENDPOINT)
        assert response.status_code == 200
        urls = response.json()["items"]
        assert all(url["is_active"] for url in urls)
        assert all(short_url_deactivated not in url["shortened_url"] for url in urls)        
        assert len(urls) == 1
        
    def test_retrieve_including_deactivated_urls(self):
        self.create_url()
        self.create_url(self.VALID_URL + "/deactivated", deactivate=True)
        response = client.get(f"{self.URL_ENDPOINT}", params={"include_deleted": True})
        assert response.status_code == 200
        urls = response.json()["items"]
        assert any(url["is_active"] == False for url in urls)
        assert any(url["is_active"] == True for url in urls)
        assert len(urls) == 2

    def test_retrieve_urls_for_authenticated_user_only(self):
        self.create_url()
        self.logout()
        self.setup_user(email="new-user@test.com", password="new-password")
        self.authenticate(email="new-user@test.com", password="new-password")
        response = client.get(self.URL_ENDPOINT)
        assert response.status_code == 200
        urls = response.json()["items"]
        assert len(urls) == 0


class TestDeleteUrl(TestURL):
    ERROR_MESSAGE = "URL not found or you do not have permission to modify it."
    
    def test_deactivate_shortened_url(self):
        short_url = self.create_url()
        deactivate_response = client.delete(f"{self.URL_ENDPOINT}/{short_url}")
        assert deactivate_response.status_code == 202
        with TestingSessionLocal() as session:
            url = Url.objects(session).get(Url.shortened_url == short_url)
            assert url.is_active == False

    def test_try_deactivate_shortened_url_twice(self):
        short_url = self.create_url()
        first_deactivate_response = client.delete(f"{self.URL_ENDPOINT}/{short_url}")
        assert first_deactivate_response.status_code == 202
        second_deactivate_response = client.delete(f"{self.URL_ENDPOINT}/{short_url}")
        assert second_deactivate_response.status_code == 404
        assert "detail" in second_deactivate_response.json()
        assert self.ERROR_MESSAGE in second_deactivate_response.json()["detail"]

    def test_unauthorized_url_deactivation(self):
        short_url = self.create_url()
        self.logout()
        self.setup_user(email="new-user@test.com", password="new-password")
        self.authenticate(email="new-user@test.com", password="new-password")
        deactivate_response = client.delete(f"{self.URL_ENDPOINT}/{short_url}")
        assert deactivate_response.status_code == 404
        assert "detail" in deactivate_response.json()
        assert self.ERROR_MESSAGE in deactivate_response.json()["detail"]


class TestRedirectUrl(TestURL):
    ERROR_MESSAGE = "URL not found."
    
    def test_redirect_to_original_url(self, mock_increment_click_count):
        short_url = self.create_url()
        response = client.get(f"{self.REDIRECT_ENDPOINT}/{short_url}", follow_redirects=False)
        assert response.status_code == 302
        assert response.headers["location"] == self.VALID_URL

    def test_redirect_to_nonexistent_url(self):
        nonexistent_short_url = "nonexistent"
        response = client.get(f"{self.REDIRECT_ENDPOINT}/{nonexistent_short_url}", follow_redirects=False)
        assert response.status_code == 404
        assert "detail" in response.json()
        assert response.json()["detail"] == self.ERROR_MESSAGE
        
    def test_redirect_to_deactivated_url(self):
        short_url = self.create_url(deactivate=True)
        response = client.get(f"{self.REDIRECT_ENDPOINT}/{short_url}", follow_redirects=False)
        assert response.status_code == 404
        assert "detail" in response.json()
        assert response.json()["detail"] == self.ERROR_MESSAGE
        
    def test_increment_click_on_redirect_to_original_url(self, mock_increment_click_count):
        short_url = self.create_url()
        client.get(f"{self.REDIRECT_ENDPOINT}/{short_url}", follow_redirects=False)
        with TestingSessionLocal() as session:
            url = Url.objects(session).get(Url.shortened_url == short_url)
            assert url.clicks == 1


class TestURLIntegration(TestURL):
    def test_url_lifecycle(self, mock_increment_click_count):
        """
        Test the complete lifecycle of a URL: creation, retrieval,
        redirection, verifying click count, deactivation, and access post-deactivation.
        """
        # Step 1: Create a new URL
        create_response = client.post(f"{BASE_URL}/urls", json={"original_url": self.VALID_URL})
        assert create_response.status_code == 201, "Failed to create URL"
        create_data = create_response.json()
        assert "shortened_url" in create_data, "Shortened URL key missing in response"
        short_url = create_data["shortened_url"].split('/')[-1]

        # Step 2: Retrieve the created URL's data
        retrieve_response = client.get(f"{BASE_URL}/urls/{short_url}")
        assert retrieve_response.status_code == 200, "Failed to retrieve URL data"
        url_data = retrieve_response.json()
        assert url_data["original_url"] == self.VALID_URL, "Original URL does not match"
        assert url_data["is_active"], "URL should be active"
        initial_clicks = url_data["clicks"]
        assert initial_clicks == 0, "Initial click count should be 0"

        # Step 3: Redirect to the URL and verify click count increments
        redirect_response = client.get(f"{BASE_URL}/redirect/{short_url}", follow_redirects=False)
        assert redirect_response.status_code == 302, "Redirection failed"
        assert redirect_response.headers["Location"] == self.VALID_URL, "Redirection URL mismatch"

        # Verify click count incremented by 1
        post_redirect_retrieve_response = client.get(f"{BASE_URL}/urls/{short_url}")
        assert post_redirect_retrieve_response.status_code == 200, "Failed to retrieve URL data after redirect"
        post_redirect_url_data = post_redirect_retrieve_response.json()
        assert post_redirect_url_data["clicks"] == initial_clicks + 1, "Click count did not increment correctly after redirect"

        # Step 4: Deactivate the URL
        deactivate_response = client.delete(f"{BASE_URL}/urls/{short_url}")
        assert deactivate_response.status_code == 202, "URL deactivation failed"

        # Step 5: Verify the URL is deactivated
        post_deactivate_retrieve_response = client.get(f"{BASE_URL}/urls/{short_url}")
        assert post_deactivate_retrieve_response.status_code == 200, "Failed to retrieve URL data after deactivation"
        post_deactivate_url_data = post_deactivate_retrieve_response.json()
        assert not post_deactivate_url_data["is_active"], "URL should be deactivated"

        # Step 6: Attempt to redirect to the deactivated URL and verify failure
        redirect_post_deactivate_response = client.get(f"{BASE_URL}/redirect/{short_url}", follow_redirects=False)
        assert redirect_post_deactivate_response.status_code == 404, "Redirection to deactivated URL should fail"
