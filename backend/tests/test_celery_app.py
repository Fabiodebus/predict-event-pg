from app.celery_app import celery_app
from app.config import settings


def test_celery_app_uses_configured_broker():
    assert celery_app.conf.broker_url == settings.celery_broker_url


def test_celery_app_uses_configured_result_backend():
    assert celery_app.conf.result_backend == settings.celery_result_backend


def test_celery_app_main_name():
    assert celery_app.main == "predict"


def test_celery_app_task_serializer_is_json():
    assert celery_app.conf.task_serializer == "json"
    assert celery_app.conf.result_serializer == "json"
    assert celery_app.conf.accept_content == ["json"]


def test_celery_app_acks_late_for_idempotency():
    # acks_late + reject_on_worker_lost is required so a worker SIGKILL
    # redelivers the task instead of silently dropping it.
    assert celery_app.conf.task_acks_late is True
    assert celery_app.conf.task_reject_on_worker_lost is True


def test_celery_app_autodiscovers_tasks_module():
    # Tasks live under app.tasks.*; importing celery_app must register them.
    assert "app.tasks" in celery_app.conf.imports or any(
        t.startswith("app.tasks.") for t in celery_app.tasks.keys()
    )
