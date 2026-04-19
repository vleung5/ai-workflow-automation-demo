"""Worker startup script"""
import logging

from src.queue.celery_app import celery_app
from src.logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


def start_worker():
    """Start the Celery worker"""
    logger.info("Starting Celery worker...")
    celery_app.worker_main(
        argv=[
            "worker",
            "--loglevel=info",
            "--concurrency=4",
            "--queues=default",
        ]
    )


if __name__ == "__main__":
    start_worker()
