"""
Main FastAPI application for workflow automation
"""
import asyncio
import uuid
import logging
from pathlib import Path
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from models import JobStatusResponse, JobStatus
from tasks import processor
from config import config

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create uploads directory
Path(config.UPLOAD_DIR).mkdir(exist_ok=True)
Path("templates").mkdir(exist_ok=True)

# Initialize FastAPI app
app = FastAPI(
    title="AI Workflow Automation Demo",
    description="End-to-end example of replacing manual workflows with AI-assisted pipelines",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Initialize processor on startup"""
    await processor.initialize()
    logger.info("✓ Application initialized")

@app.get("/")
async def root():
    """Serve the web UI"""
    return FileResponse("templates/index.html")

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload and process a CSV file"""
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")
    
    content = await file.read()
    csv_content = content.decode("utf-8")
    job_id = str(uuid.uuid4())
    
    asyncio.create_task(processor.process_csv_data(csv_content, job_id))
    logger.info(f"✓ Job {job_id} queued for processing")
    
    return {
        "job_id": job_id,
        "message": "File uploaded successfully. Processing has started.",
        "status_url": f"/status/{job_id}",
        "results_url": f"/results/{job_id}"
    }

@app.get("/status/{job_id}")
async def get_status(job_id: str):
    """Get the current status of a processing job"""
    job = processor.get_job_status(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    progress_percent = (job.processed_records / job.total_records * 100) if job.total_records > 0 else 0
    
    return JobStatusResponse(
        job_id=job_id,
        status=job.status,
        processed_records=job.processed_records,
        total_records=job.total_records,
        progress_percent=progress_percent,
        estimated_remaining_seconds=None
    )

@app.get("/results/{job_id}")
async def get_results(job_id: str):
    """Get the full results of a completed job"""
    job = processor.get_job_status(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status.value == "processing":
        raise HTTPException(status_code=202, detail="Job still processing")
    
    if job.status.value == "failed":
        raise HTTPException(status_code=500, detail=f"Job failed: {job.error_message}")
    
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

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "ai-workflow-automation-demo"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.API_HOST, port=config.API_PORT, log_level="info")
