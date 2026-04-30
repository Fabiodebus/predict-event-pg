from celery import Celery

from app.config import settings

celery_app = Celery(
    "predict",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks.base"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_default_queue="default",
    timezone="UTC",
    enable_utc=True,
    imports=("app.tasks",),
)
