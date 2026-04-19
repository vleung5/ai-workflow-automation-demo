"""Data models for the workflow automation pipeline"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field

class PriorityLevel(str, Enum):
    URGENT = "urgent"
    NORMAL = "normal"
    LOW = "low"

class SentimentType(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"

class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

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
