from enum import Enum

from pydantic import BaseSettings, PostgresDsn


class LogLevel(str, Enum):
    critical = "CRITICAL"
    error = "ERROR"
    warning = "WARNING"
    info = "INFO"
    debug = "DEBUG"


class Settings(BaseSettings):
    # TODO: Pollish this into a better .env file
    database_url: PostgresDsn
    test_database_url: PostgresDsn | None
    log_level: LogLevel = LogLevel.debug
    server_url: str
    redis_host: str = "127.0.0.1"
    redis_port: int = 6379
    celery_broker_url: str = 'amqp://guest:guest@rabbitmq:5672/vhost'

    # Auth
    access_token_expire_minutes: float
    jwt_signing_key: str
    accept_cookie: bool = True
    accept_token: bool = True


settings = Settings()
