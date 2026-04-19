"""Report creation from processed job results"""

import logging
from typing import Dict, Any, List
from datetime import datetime

from src.models.schemas import JobResult, ProcessedRecord
from src.models.enums import JobStatus

logger = logging.getLogger(__name__)


def generate_job_report(job: JobResult) -> Dict[str, Any]:
    """
    Generate a human-readable report dictionary from a completed job.

    Args:
        job: Completed JobResult object.

    Returns:
        Report dictionary suitable for JSON serialization or display.
    """
    if job.status not in (JobStatus.COMPLETED, JobStatus.FAILED):
        return {
            "job_id": job.job_id,
            "status": job.status.value,
            "message": "Job is not yet complete",
        }

    duration_seconds: float = 0.0
    if job.completed_at and job.started_at:
        duration_seconds = (job.completed_at - job.started_at).total_seconds()

    success_rate = (
        (job.processed_records / job.total_records * 100) if job.total_records > 0 else 0.0
    )

    return {
        "job_id": job.job_id,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "status": job.status.value,
        "summary": {
            "total_records": job.total_records,
            "processed_records": job.processed_records,
            "failed_records": job.failed_records,
            "success_rate_pct": round(success_rate, 2),
            "duration_seconds": round(duration_seconds, 3),
        },
        "statistics": job.statistics,
        "highlights": _extract_highlights(job.results),
        "error_message": job.error_message,
    }


def _extract_highlights(results: List[ProcessedRecord]) -> Dict[str, Any]:
    """Extract notable records from results"""
    negative = [r for r in results if r.classification.sentiment.value == "negative"]
    urgent = [r for r in results if r.classification.priority.value == "urgent"]

    return {
        "negative_feedback_count": len(negative),
        "urgent_items_count": len(urgent),
        "sample_urgent": [{"id": r.id, "summary": r.summary} for r in urgent[:5]],
        "sample_negative": [{"id": r.id, "summary": r.summary} for r in negative[:5]],
    }
