from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
from src.core.config import settings


def get_database_url():
    return settings.test_database_url if settings.test_database_url else settings.database_url


engine = create_engine(get_database_url())
SessionLocal = sessionmaker(bind=engine)


@contextmanager
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
