"""Celery application factory.

Configures a Celery instance using the application settings for broker
and result-backend URLs.  Import this module's ``celery`` object when
declaring tasks or when starting a Celery worker::

    celery -A celery_app.celery worker --loglevel=info
"""

from __future__ import annotations

import logging

from celery import Celery
from celery.signals import worker_init

from core.config import get_settings

logger = logging.getLogger(__name__)

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


@worker_init.connect
def _prewarm_models(**kwargs: object) -> None:
    """Pre-load heavy ML models at worker startup so the first task is fast."""
    try:
        from infrastructure.ai.classification.zero_shot_classifier import (
            ZeroShotClassifier,
        )
        ZeroShotClassifier().load()
        logger.info("pre-warmed zero-shot classification model")
    except Exception:
        logger.warning("failed to pre-warm classification model", exc_info=True)

    try:
        from infrastructure.ai.embeddings.embedding_service import EmbeddingService
        _ = EmbeddingService().model
        logger.info("pre-warmed sentence-transformer embedding model")
    except Exception:
        logger.warning("failed to pre-warm embedding model", exc_info=True)
