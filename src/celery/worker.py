from celery import Celery

from src.core.config import settings


celery = Celery(
    __name__,
    broker=settings.celery_broker_url,
)

celery.autodiscover_tasks(['src.celery.celery'])
