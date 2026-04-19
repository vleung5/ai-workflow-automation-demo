"""Celery task definitions"""
import asyncio
import logging

from src.queue.celery_app import celery_app
from src.core.processor import processor

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="process_csv")
def process_csv_task(self, csv_content: str, job_id: str) -> dict:
    """
    Celery task to process CSV data asynchronously.

    Args:
        csv_content: Raw CSV string.
        job_id: Unique job identifier.

    Returns:
        Serialized JobResult dict.
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        job_result = loop.run_until_complete(processor.process_csv_data(csv_content, job_id))
        return job_result.dict()
    except Exception as exc:
        logger.error(f"Task {self.request.id} failed: {str(exc)}")
        raise self.retry(exc=exc, countdown=60, max_retries=3)
