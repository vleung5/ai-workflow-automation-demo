"""CSV ingestion endpoints"""

import logging
import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile

from src.config import config
from src.core.processor import processor
from src.services.datadog_service import send_datadog_event, send_datadog_metric

router = APIRouter(tags=["csv-ingestion"])
logger = logging.getLogger(__name__)

MAX_FILE_SIZE = config.MAX_FILE_SIZE_MB * 1024 * 1024


@router.post("/upload")
async def upload_csv(file: UploadFile = File(...)):
    """Upload a CSV file for processing"""
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds maximum size of {config.MAX_FILE_SIZE_MB} MB",
        )

    csv_content = content.decode("utf-8", errors="replace")
    job_id = f"upload_{uuid.uuid4().hex[:12]}"

    logger.info(f"Processing uploaded CSV: {file.filename} → job {job_id}")
    send_datadog_metric("csv.upload.started", 1, "increment")

    job = await processor.process_csv_data(csv_content, job_id)

    send_datadog_metric("csv.upload.completed", 1, "increment")
    send_datadog_event(
        title="CSV Upload Processed",
        text=f"Job {job_id} processed {job.processed_records}/{job.total_records} records",
        alert_type="success",
    )

    return {
        "job_id": job_id,
        "status": job.status.value,
        "total_records": job.total_records,
        "processed_records": job.processed_records,
        "message": "CSV processed successfully",
    }


@router.get("/jobs")
async def list_jobs():
    """List all processing jobs"""
    jobs_count = len(processor.jobs)
    send_datadog_metric("jobs.total", jobs_count, "gauge")
    return {
        "jobs": [
            {
                "job_id": job_id,
                "status": job.status.value,
                "total_records": job.total_records,
                "processed_records": job.processed_records,
                "started_at": job.started_at.isoformat(),
            }
            for job_id, job in processor.jobs.items()
        ],
        "total_jobs": jobs_count,
    }
