from src.core.config import settings

BASE_URL = "/api/v1"

database_url = settings.test_database_url

assert database_url is not None, "TEST_DATABASE_URL must be defined"
