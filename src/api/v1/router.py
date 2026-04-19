"""API v1 router setup"""

from fastapi import APIRouter

from src.api.v1 import csv_ingestion, status, results
from src.api.v1 import s3_routes

router = APIRouter(prefix="/v1")

router.include_router(csv_ingestion.router)
router.include_router(status.router)
router.include_router(results.router)
router.include_router(s3_routes.router)
