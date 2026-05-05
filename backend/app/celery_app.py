from celery import Celery

from app.config import settings

celery_app = Celery(
    "predict",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
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
)

# Feature WOs put their Celery tasks at `app/<feature>/tasks.py`.
# autodiscover_tasks(packages=[...]) loads the task module from each listed
# package at worker boot. Add new feature packages here as they land.
AUTODISCOVER_PACKAGES = ["app.cwg"]
celery_app.autodiscover_tasks(packages=AUTODISCOVER_PACKAGES)
