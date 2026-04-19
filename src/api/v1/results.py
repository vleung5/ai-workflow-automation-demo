"""Results endpoints"""

import logging

from fastapi import APIRouter

from src.core.processor import processor
from src.models.enums import JobStatus
from src.services.datadog_service import send_datadog_metric

router = APIRouter(tags=["results"])
logger = logging.getLogger(__name__)


@router.get("/results/{job_id}")
async def get_results(job_id: str):
    """Get job processing results"""
    job = processor.get_job_status(job_id)
    if not job:
        return {"job_id": job_id, "status": "not_found", "message": "Job not found"}

    if job.status == JobStatus.PROCESSING:
        return {"job_id": job_id, "status": "processing", "message": "Job still processing"}

    if job.status == JobStatus.FAILED:
        send_datadog_metric("job.failed", 1, "increment")
        return {
            "job_id": job_id,
            "status": "failed",
            "message": f"Job failed: {job.error_message}",
        }

    send_datadog_metric("job.completed", 1, "increment")
    return {
        "job_id": job_id,
        "status": job.status.value,
        "summary": {
            "total_records": job.total_records,
            "processed_records": job.processed_records,
            "failed_records": job.failed_records,
            "success_rate": (
                (job.processed_records / job.total_records * 100) if job.total_records > 0 else 0
            ),
        },
        "statistics": job.statistics,
        "results": [
            {
                "id": r.id,
                "original_data": r.original_data,
                "validation": r.validation.dict(),
                "classification": r.classification.dict(),
                "summary": r.summary,
                "processing_time_ms": r.processing_time_ms,
            }
            for r in job.results
        ],
        "processing_duration_seconds": (
            (job.completed_at - job.started_at).total_seconds() if job.completed_at else None
        ),
    }


@router.get("/metrics")
async def get_metrics():
    """Get application metrics"""
    import time
    from src.services.s3_service import get_s3_polling_service

    jobs = processor.jobs
    s3_service = get_s3_polling_service()
    pending_files = await s3_service.get_pending_files() if s3_service else []

    return {
        "timestamp": int(time.time()),
        "metrics": {
            "jobs": {
                "total": len(jobs),
                "active": sum(1 for j in jobs.values() if j.status == JobStatus.PROCESSING),
                "completed": sum(1 for j in jobs.values() if j.status == JobStatus.COMPLETED),
                "failed": sum(1 for j in jobs.values() if j.status == JobStatus.FAILED),
            },
            "s3": {
                "pending_files": len(pending_files),
                "polling_enabled": s3_service is not None,
            },
        },
    }
