"""Tests for Pydantic schemas"""

from datetime import datetime

import pytest

from src.models.enums import JobStatus, PriorityLevel, SentimentType
from src.models.schemas import JobResult, RecordClassification, ValidationResult


def test_validation_result_valid():
    result = ValidationResult(is_valid=True)
    assert result.is_valid is True
    assert result.errors == []
    assert result.warnings == []


def test_record_classification_confidence_bounds():
    with pytest.raises(Exception):
        RecordClassification(
            priority=PriorityLevel.NORMAL,
            confidence=1.5,  # Out of range
            sentiment=SentimentType.NEUTRAL,
            category="inquiry",
        )


def test_job_result_defaults():
    job = JobResult(
        job_id="test",
        status=JobStatus.PENDING,
        total_records=0,
        processed_records=0,
        failed_records=0,
        results=[],
        started_at=datetime.now(),
    )
    assert job.completed_at is None
    assert job.error_message is None
    assert job.statistics == {}
