"""Pydantic request/response models"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from src.models.enums import JobStatus, PriorityLevel, SentimentType


class ValidationResult(BaseModel):
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class RecordClassification(BaseModel):
    priority: PriorityLevel
    confidence: float = Field(ge=0.0, le=1.0)
    sentiment: SentimentType
    category: str


class ProcessedRecord(BaseModel):
    id: int
    original_data: Dict[str, Any]
    validation: ValidationResult
    classification: RecordClassification
    summary: str
    processing_time_ms: float


class JobResult(BaseModel):
    job_id: str
    status: JobStatus
    total_records: int
    processed_records: int
    failed_records: int
    results: List[ProcessedRecord]
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    statistics: Dict[str, Any] = Field(default_factory=dict)


class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    processed_records: int
    total_records: int
    progress_percent: float
    estimated_remaining_seconds: Optional[float] = None


class CSVUploadResponse(BaseModel):
    job_id: str
    status: str
    message: str
    total_records: int = 0


class HealthResponse(BaseModel):
    status: str
    service: str
    environment: str
    s3_polling: str
    version: str
    datadog: str
