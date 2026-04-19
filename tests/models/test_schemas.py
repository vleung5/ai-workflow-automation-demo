"""Tests for Pydantic schemas"""
import pytest
from src.models.schemas import ValidationResult, RecordClassification, JobResult
from src.models.enums import PriorityLevel, SentimentType, JobStatus
from datetime import datetime


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
