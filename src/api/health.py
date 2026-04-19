"""Health check endpoints"""
import logging

from fastapi import APIRouter

from src.config import config
from src.services.s3_service import get_s3_polling_service
from src.services.datadog_service import initialize_datadog

router = APIRouter(tags=["health"])
logger = logging.getLogger(__name__)


@router.get("/health")
async def health_check():
    """Application health check"""
    s3_service = get_s3_polling_service()
    return {
        "status": "healthy",
        "service": config.DD_SERVICE,
        "environment": config.ENV,
        "s3_polling": "enabled" if s3_service else "disabled",
        "version": config.DD_VERSION,
        "datadog": "enabled" if config.DATADOG_ENABLED else "disabled",
    }
