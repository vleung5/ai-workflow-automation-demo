"""S3 polling status and trigger endpoints"""
import logging

from fastapi import APIRouter

from src.services.s3_service import get_s3_polling_service
from src.services.datadog_service import send_datadog_metric, send_datadog_event
from src.core.processor import processor

router = APIRouter(prefix="/s3", tags=["s3"])
logger = logging.getLogger(__name__)


@router.get("/status")
async def get_s3_polling_status():
    """Get S3 polling service status"""
    s3_service = get_s3_polling_service()
    if not s3_service:
        return {"enabled": False, "message": "S3 polling service not initialized"}
    stats = await s3_service.get_processing_stats()
    return {
        "enabled": True,
        "status": "running" if s3_service.is_running else "stopped",
        "statistics": stats,
    }


@router.get("/pending")
async def get_pending_s3_files():
    """Get pending S3 files"""
    s3_service = get_s3_polling_service()
    if not s3_service:
        return {"pending_files": [], "message": "S3 polling service not initialized"}
    pending_files = await s3_service.get_pending_files()
    send_datadog_metric("s3.pending_files", len(pending_files), "gauge")
    return {"pending_files": pending_files, "count": len(pending_files)}


@router.post("/process")
async def trigger_s3_processing():
    """Manually trigger S3 processing"""
    s3_service = get_s3_polling_service()
    if not s3_service:
        return {"success": False, "message": "S3 polling service not initialized"}

    try:
        pending_files = await s3_service.get_pending_files()
        if not pending_files:
            return {"success": False, "message": "No pending files to process"}

        file_key = pending_files[0]["key"]
        csv_content = await s3_service.read_file_from_s3(file_key)

        if csv_content:
            job_id = file_key.replace("/", "_").replace(".csv", "")
            send_datadog_metric("s3.file.processing_started", 1, "increment")
            job_result = await processor.process_csv_data(csv_content, job_id)
            results_key = await s3_service.upload_results_to_s3(job_result.dict(), job_id)
            await s3_service.mark_file_as_processed(file_key, "success")
            send_datadog_event(
                title="File Processed Successfully",
                text=f"Job {job_id} completed processing {file_key}",
                alert_type="success",
                tags=["s3", "processing"],
            )
            return {
                "success": True,
                "job_id": job_id,
                "file_key": file_key,
                "results_key": results_key,
                "message": "File processing triggered",
            }
        else:
            await s3_service.mark_file_as_processed(file_key, "failed")
            send_datadog_metric("s3.file.processing_failed", 1, "increment")
            return {"success": False, "message": "Failed to read file from S3"}

    except Exception as e:
        logger.error(f"Error triggering S3 processing: {str(e)}")
        send_datadog_metric("s3.file.processing_error", 1, "increment")
        return {"success": False, "message": f"Error: {str(e)}"}
