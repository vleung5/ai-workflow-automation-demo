"""Enums for the workflow automation pipeline"""

from enum import Enum


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


class ProcessingState(str, Enum):
    """Fine-grained processing state for queue workers"""

    QUEUED = "queued"
    VALIDATING = "validating"
    CLASSIFYING = "classifying"
    SUMMARIZING = "summarizing"
    UPLOADING = "uploading"
    DONE = "done"
    ERROR = "error"
