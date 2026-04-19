"""Job status endpoints"""
import logging

from fastapi import APIRouter

from src.core.processor import processor
from src.services.datadog_service import send_datadog_metric

router = APIRouter(tags=["status"])
logger = logging.getLogger(__name__)


@router.get("/status/{job_id}")
async def get_status(job_id: str):
    """Get job processing status"""
    job = processor.get_job_status(job_id)
    if not job:
        send_datadog_metric("job.not_found", 1, "increment")
        return {"job_id": job_id, "status": "not_found", "message": "Job not found"}

    progress_percent = (
        (job.processed_records / job.total_records * 100) if job.total_records > 0 else 0
    )
    send_datadog_metric(
        "job.progress",
        progress_percent,
        "gauge",
        {"job_id": job_id, "status": job.status.value},
    )
    return {
        "job_id": job_id,
        "status": job.status.value,
        "processed_records": job.processed_records,
        "total_records": job.total_records,
        "progress_percent": progress_percent,
        "estimated_remaining_seconds": None,
    }
