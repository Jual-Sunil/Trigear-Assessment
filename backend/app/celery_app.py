"""Celery application factory.

Configures a Celery instance using the application settings for broker
and result-backend URLs.  Import this module's ``celery`` object when
declaring tasks or when starting a Celery worker::

    celery -A celery_app.celery worker --loglevel=info
"""

from __future__ import annotations

from celery import Celery

from core.config import get_settings

settings = get_settings()

celery = Celery(
    "trigear",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery.conf.update(
    task_serializer=settings.celery_task_serializer,
    result_serializer=settings.celery_result_serializer,
    accept_content=settings.celery_accept_content,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

# Explicitly include task modules so the worker registers them.
celery.conf.update(include=["tasks.sync_tasks"])
