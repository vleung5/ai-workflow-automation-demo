"""
FastAPI application with Datadog APM integration
"""
import asyncio
import logging
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import time

from models import JobStatus
from tasks import processor
from s3_polling import initialize_s3_polling, get_s3_polling_service
from config import config
from datadog_config import (
    initialize_datadog, 
    setup_structured_logging,
    get_datadog_tags,
    send_datadog_event,
    send_datadog_metric,
    DatadogConfig
)

# Initialize Datadog
initialize_datadog()
setup_structured_logging()

# Setup logging
logging.basicConfig(
    level=config.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create directories
Path(config.UPLOAD_DIR).mkdir(exist_ok=True)
Path("templates").mkdir(exist_ok=True)

# Background polling task
polling_task: asyncio.Task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan with Datadog event tracking"""
    
    logger.info("🚀 Starting application...")
    await processor.initialize()
    
    # Send Datadog startup event
    send_datadog_event(
        title="Application Startup",
        text=f"AI Workflow Automation started in {config.ENV} environment",
        alert_type="success",
        tags=[f"environment:{config.ENV}"]
    )
    
    # Initialize S3 polling
    s3_bucket = config.S3_BUCKET
    if s3_bucket:
        logger.info(f"Initializing S3 polling service for bucket: {s3_bucket}")
        s3_service = initialize_s3_polling(
            bucket_name=s3_bucket,
            prefix=config.S3_PREFIX,
            region=config.AWS_REGION
        )
        
        s3_service.polling_interval = config.S3_POLLING_INTERVAL
        
        global polling_task
        polling_task = asyncio.create_task(
            s3_service.start_polling(processor)
        )
        
        logger.info("✓ S3 polling service started")
        send_datadog_metric("polling_service.started", 1, "increment")
    
    logger.info("✓ Application initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    
    send_datadog_event(
        title="Application Shutdown",
        text="AI Workflow Automation shutting down",
        alert_type="info",
        tags=[f"environment:{config.ENV}"]
    )
    
    s3_service = get_s3_polling_service()
    if s3_service:
        await s3_service.stop_polling()
        if polling_task and not polling_task.done():
            polling_task.cancel()
    
    logger.info("✓ Application shutdown complete")


# Initialize FastAPI
app = FastAPI(
    title="AI Workflow Automation Demo",
    description="End-to-end example of replacing manual workflows with AI-assisted pipelines",
    version="2.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Datadog APM middleware
@app.middleware("http")
async def datadog_middleware(request: Request, call_next):
    """Track request metrics with Datadog"""
    
    start_time = time.time()
    
    try:
        response = await call_next(request)
        
        # Calculate request duration
        duration = time.time() - start_time
        
        # Send metrics
        send_datadog_metric(
            f"http.request.duration",
            duration,
            "gauge",
            {
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code
            }
        )
        
        # Log request
        logger.info(
            f"{request.method} {request.url.path}",
            extra={
                "status_code": response.status_code,
                "duration_ms": duration * 1000,
                "tags": get_datadog_tags({
                    "method": request.method,
                    "path": request.url.path
                })
            }
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Request failed: {str(e)}", exc_info=True)
        send_datadog_metric("http.request.error", 1, "increment")
        raise


@app.get("/")
async def root():
    """Serve the web UI"""
    return FileResponse("templates/index.html")


@app.get("/health")
async def health_check():
    """Health check endpoint with Datadog APM"""
    
    s3_service = get_s3_polling_service()
    polling_status = "enabled" if s3_service else "disabled"
    
    return {
        "status": "healthy",
        "service": "ai-workflow-automation-demo",
        "environment": config.ENV,
        "s3_polling": polling_status,
        "version": "2.0.0",
        "datadog": "enabled" if DatadogConfig.DATADOG_ENABLED else "disabled"
    }


@app.get("/status/{job_id}")
async def get_status(job_id: str):
    """Get job status with Datadog tracing"""
    
    job = processor.get_job_status(job_id)
    
    if not job:
        send_datadog_metric("job.not_found", 1, "increment")
        return {
            "job_id": job_id,
            "status": "not_found",
            "message": "Job not found"
        }
    
    progress_percent = (job.processed_records / job.total_records * 100) if job.total_records > 0 else 0
    
    # Send metrics
    send_datadog_metric(
        "job.progress",
        progress_percent,
        "gauge",
        {"job_id": job_id, "status": job.status.value}
    )
    
    return {
        "job_id": job_id,
        "status": job.status.value,
        "processed_records": job.processed_records,
        "total_records": job.total_records,
        "progress_percent": progress_percent,
        "estimated_remaining_seconds": None
    }


@app.get("/results/{job_id}")
async def get_results(job_id: str):
    """Get job results"""
    
    job = processor.get_job_status(job_id)
    
    if not job:
        return {
            "job_id": job_id,
            "status": "not_found",
            "message": "Job not found"
        }
    
    if job.status == JobStatus.PROCESSING:
        return {
            "job_id": job_id,
            "status": "processing",
            "message": "Job still processing"
        }
    
    if job.status == JobStatus.FAILED:
        send_datadog_metric("job.failed", 1, "increment")
        return {
            "job_id": job_id,
            "status": "failed",
            "message": f"Job failed: {job.error_message}"
        }
    
    send_datadog_metric("job.completed", 1, "increment")
    
    return {
        "job_id": job_id,
        "status": job.status.value,
        "summary": {
            "total_records": job.total_records,
            "processed_records": job.processed_records,
            "failed_records": job.failed_records,
            "success_rate": (job.processed_records / job.total_records * 100) if job.total_records > 0 else 0
        },
        "statistics": job.statistics,
        "results": [
            {
                "id": r.id,
                "original_data": r.original_data,
                "validation": r.validation.dict(),
                "classification": r.classification.dict(),
                "summary": r.summary,
                "processing_time_ms": r.processing_time_ms
            }
            for r in job.results
        ],
        "processing_duration_seconds": (
            (job.completed_at - job.started_at).total_seconds()
            if job.completed_at else None
        )
    }


@app.get("/s3/status")
async def get_s3_polling_status():
    """Get S3 polling service status"""
    
    s3_service = get_s3_polling_service()
    
    if not s3_service:
        return {
            "enabled": False,
            "message": "S3 polling service not initialized"
        }
    
    stats = await s3_service.get_processing_stats()
    return {
        "enabled": True,
        "status": "running" if s3_service.is_running else "stopped",
        "statistics": stats
    }


@app.get("/s3/pending")
async def get_pending_s3_files():
    """Get pending S3 files"""
    
    s3_service = get_s3_polling_service()
    
    if not s3_service:
        return {
            "pending_files": [],
            "message": "S3 polling service not initialized"
        }
    
    pending_files = await s3_service.get_pending_files()
    
    send_datadog_metric(
        "s3.pending_files",
        len(pending_files),
        "gauge"
    )
    
    return {
        "pending_files": pending_files,
        "count": len(pending_files)
    }


@app.post("/s3/process")
async def trigger_s3_processing():
    """Manually trigger S3 processing"""
    
    s3_service = get_s3_polling_service()
    
    if not s3_service:
        return {
            "success": False,
            "message": "S3 polling service not initialized"
        }
    
    try:
        pending_files = await s3_service.get_pending_files()
        
        if not pending_files:
            return {
                "success": False,
                "message": "No pending files to process"
            }
        
        file_key = pending_files[0]['key']
        csv_content = await s3_service.read_file_from_s3(file_key)
        
        if csv_content:
            job_id = file_key.replace('/', '_').replace('.csv', '')
            
            send_datadog_metric("s3.file.processing_started", 1, "increment")
            
            job_result = await processor.process_csv_data(csv_content, job_id)
            results_key = await s3_service.upload_results_to_s3(
                job_result.dict(),
                job_id
            )
            await s3_service.mark_file_as_processed(file_key, "success")
            
            send_datadog_event(
                title="File Processed Successfully",
                text=f"Job {job_id} completed processing {file_key}",
                alert_type="success",
                tags=["s3", "processing"]
            )
            
            return {
                "success": True,
                "job_id": job_id,
                "file_key": file_key,
                "results_key": results_key,
                "message": "File processing triggered"
            }
        else:
            await s3_service.mark_file_as_processed(file_key, "failed")
            send_datadog_metric("s3.file.processing_failed", 1, "increment")
            return {
                "success": False,
                "message": "Failed to read file from S3"
            }
    
    except Exception as e:
        logger.error(f"Error triggering S3 processing: {str(e)}")
        send_datadog_metric("s3.file.processing_error", 1, "increment")
        return {
            "success": False,
            "message": f"Error: {str(e)}"
        }


@app.get("/jobs")
async def list_all_jobs():
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
                "started_at": job.started_at.isoformat()
            }
            for job_id, job in processor.jobs.items()
        ],
        "total_jobs": jobs_count
    }


@app.get("/metrics")
async def get_metrics():
    """Get application metrics for Datadog"""
    
    jobs = processor.jobs
    active_jobs = sum(1 for j in jobs.values() if j.status == JobStatus.PROCESSING)
    completed_jobs = sum(1 for j in jobs.values() if j.status == JobStatus.COMPLETED)
    failed_jobs = sum(1 for j in jobs.values() if j.status == JobStatus.FAILED)
    
    s3_service = get_s3_polling_service()
    pending_files = await s3_service.get_pending_files() if s3_service else []
    
    return {
        "timestamp": int(time.time()),
        "metrics": {
            "jobs": {
                "total": len(jobs),
                "active": active_jobs,
                "completed": completed_jobs,
                "failed": failed_jobs
            },
            "s3": {
                "pending_files": len(pending_files),
                "polling_enabled": s3_service is not None
            }
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=config.API_HOST,
        port=config.API_PORT,
        log_level=config.LOG_LEVEL.lower()
    )
