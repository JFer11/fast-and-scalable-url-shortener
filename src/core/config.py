from enum import Enum

from pydantic import BaseSettings, PostgresDsn


class LogLevel(str, Enum):
    critical = "CRITICAL"
    error = "ERROR"
    warning = "WARNING"
    info = "INFO"
    debug = "DEBUG"


class Settings(BaseSettings):
    # Auth
    access_token_expire_minutes: float
    jwt_signing_key: str
    accept_cookie: bool = True
    accept_token: bool = True

    # Backend settings
    database_url: PostgresDsn
    test_database_url: PostgresDsn | None
    log_level: LogLevel = LogLevel.debug
    server_url: str

    # Redis settings
    redis_host: str
    redis_port: int 
    
    # RabbitMQ settings
    rabbitmq_port : int
    rabbitmq_host: str
    rabbitmq_default_vhost: str
    rabbitmq_default_user: str
    rabbitmq_default_pass: str

    # Celery settings
    @property
    def celery_broker_url(self) -> str:
        return f"amqp://{self.rabbitmq_default_user}:{self.rabbitmq_default_pass}@{self.rabbitmq_host}:{self.rabbitmq_port}/{self.rabbitmq_default_vhost}"


settings = Settings()
