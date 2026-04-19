"""FastAPI entry point"""

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

from src.config import config
from src.logging_config import setup_logging
from src.services.datadog_service import initialize_datadog, send_datadog_event, send_datadog_metric
from src.services.s3_service import initialize_s3_polling, get_s3_polling_service
from src.core.processor import processor
from src.api.middleware import DatadogAPMMiddleware, add_cors_middleware
from src.api.health import router as health_router
from src.api.v1.router import router as v1_router

# Configure logging first
setup_logging()
logger = logging.getLogger(__name__)

# Initialize Datadog APM
initialize_datadog()

# Ensure upload directory exists
Path(config.UPLOAD_DIR).mkdir(exist_ok=True)
Path("templates").mkdir(exist_ok=True)

# Background polling task handle
_polling_task: asyncio.Task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan with startup/shutdown hooks"""
    global _polling_task

    logger.info("Starting application...")
    await processor.initialize()

    send_datadog_event(
        title="Application Startup",
        text=f"AI Workflow Automation started in {config.ENV} environment",
        alert_type="success",
        tags=[f"environment:{config.ENV}"],
    )

    if config.S3_BUCKET:
        logger.info(f"Initializing S3 polling for bucket: {config.S3_BUCKET}")
        s3_service = initialize_s3_polling(
            bucket_name=config.S3_BUCKET,
            prefix=config.S3_PREFIX,
            region=config.AWS_REGION,
        )
        s3_service.polling_interval = config.S3_POLLING_INTERVAL
        _polling_task = asyncio.create_task(s3_service.start_polling(processor))
        send_datadog_metric("polling_service.started", 1, "increment")
        logger.info("S3 polling service started")

    logger.info("Application initialized")
    yield

    # Shutdown
    logger.info("Shutting down application...")
    send_datadog_event(
        title="Application Shutdown",
        text="AI Workflow Automation shutting down",
        alert_type="info",
        tags=[f"environment:{config.ENV}"],
    )
    s3_service = get_s3_polling_service()
    if s3_service:
        await s3_service.stop_polling()
    if _polling_task and not _polling_task.done():
        _polling_task.cancel()
    logger.info("Application shutdown complete")


app = FastAPI(
    title="AI Workflow Automation Demo",
    description="End-to-end example of replacing manual workflows with AI-assisted pipelines",
    version=config.DD_VERSION,
    lifespan=lifespan,
)

# Middleware
add_cors_middleware(app)
app.add_middleware(DatadogAPMMiddleware)

# Routers
app.include_router(health_router)
app.include_router(v1_router)


@app.get("/")
async def root():
    """Serve the web UI"""
    return FileResponse("templates/index.html")


# Legacy routes (kept for backward compatibility)
@app.get("/status/{job_id}")
async def legacy_status(job_id: str):
    from src.api.v1.status import get_status

    return await get_status(job_id)


@app.get("/results/{job_id}")
async def legacy_results(job_id: str):
    from src.api.v1.results import get_results

    return await get_results(job_id)


@app.get("/s3/status")
async def legacy_s3_status():
    from src.api.v1.s3_routes import get_s3_polling_status

    return await get_s3_polling_status()


@app.get("/s3/pending")
async def legacy_s3_pending():
    from src.api.v1.s3_routes import get_pending_s3_files

    return await get_pending_s3_files()


@app.post("/s3/process")
async def legacy_s3_process():
    from src.api.v1.s3_routes import trigger_s3_processing

    return await trigger_s3_processing()


@app.get("/jobs")
async def legacy_jobs():
    from src.api.v1.csv_ingestion import list_jobs

    return await list_jobs()


@app.get("/metrics")
async def legacy_metrics():
    from src.api.v1.results import get_metrics

    return await get_metrics()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=config.API_HOST,
        port=config.API_PORT,
        log_level=config.LOG_LEVEL.lower(),
    )
