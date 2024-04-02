from src.celery.utils import db_session
from src.celery.worker import celery
from src.models import Url


@celery.task
def increment_click_count(shortened_url: str) -> int:
    with db_session() as db:
        url = db.query(Url).filter(Url.shortened_url == shortened_url).first()
        if url:
            url.clicks += 1
            db.commit()
        return url.clicks
