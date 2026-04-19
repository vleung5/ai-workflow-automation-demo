from fastapi import FastAPI
from contextlib import asynccontextmanager
from s3_polling import initialize_s3_polling, get_s3_polling_service
import asyncio

polling_task: asyncio.Task = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🚀 Starting application...")
    await processor.initialize()
    
    # Initialize S3 polling
    s3_bucket = config.S3_BUCKET
    if s3_bucket:
        logger.info(f"Initializing S3 polling service for bucket: {s3_bucket}")
        s3_service = initialize_s3_polling(
            bucket_name=s3_bucket,
            prefix=config.S3_PREFIX,
            region=config.AWS_REGION
        )
        
        if config.ENV == "dev":
            await s3_service.create_sample_file()
        
        # Set polling interval
        s3_service.polling_interval = config.S3_POLLING_INTERVAL
        
        # Start polling
        global polling_task
        polling_task = asyncio.create_task(
            s3_service.start_polling(processor)
        )
        logger.info("✓ S3 polling service started")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    s3_service = get_s3_polling_service()
    if s3_service:
        await s3_service.stop_polling()
        if polling_task and not polling_task.done():
            polling_task.cancel()
    
    logger.info("✓ Application shutdown complete")


app = FastAPI(lifespan=lifespan)

@app.get("/s3/status")
async def get_s3_polling_status():
    s3_service = get_s3_polling_service()
    if not s3_service:
        return {"enabled": False, "message": "S3 polling service not initialized"}
    
    stats = await s3_service.get_processing_stats()
    return {
        "enabled": True,
        "status": "running" if s3_service.is_running else "stopped",
        "statistics": stats
    }

@app.get("/s3/pending")
async def get_pending_s3_files():
    s3_service = get_s3_polling_service()
    if not s3_service:
        return {"pending_files": [], "message": "S3 polling service not initialized"}
    
    pending_files = await s3_service.get_pending_files()
    return {"pending_files": pending_files, "count": len(pending_files)}

@app.post("/s3/process")
async def trigger_s3_processing():
    s3_service = get_s3_polling_service()
    if not s3_service:
        return {"success": False, "message": "S3 polling service not initialized"}
    
    try:
        pending_files = await s3_service.get_pending_files()
        if not pending_files:
            return {"success": False, "message": "No pending files to process"}
        
        file_key = pending_files[0]['key']
        csv_content = await s3_service.read_file_from_s3(file_key)
        
        if csv_content:
            job_id = file_key.replace('/', '_').replace('.csv', '')
            job_result = await processor.process_csv_data(csv_content, job_id)
            results_key = await s3_service.upload_results_to_s3(
                job_result.dict(),
                job_id
            )
            await s3_service.mark_file_as_processed(file_key, "success")
            
            return {
                "success": True,
                "job_id": job_id,
                "file_key": file_key,
                "results_key": results_key,
                "message": "File processing triggered"
            }
        else:
            await s3_service.mark_file_as_processed(file_key, "failed")
            return {"success": False, "message": "Failed to read file from S3"}
    
    except Exception as e:
        logger.error(f"Error triggering S3 processing: {str(e)}")
        return {"success": False, "message": f"Error: {str(e)}"}
