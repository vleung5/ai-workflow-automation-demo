"""Tests for the processing pipeline"""

import asyncio

import pytest

from src.core.processor import WorkflowProcessor


@pytest.fixture
def processor():
    p = WorkflowProcessor()
    asyncio.get_event_loop().run_until_complete(p.initialize())
    return p


def test_process_csv_data_completes(processor, sample_csv_content):
    result = asyncio.get_event_loop().run_until_complete(
        processor.process_csv_data(sample_csv_content, "test_job_001")
    )
    assert result.job_id == "test_job_001"
    assert result.total_records == 5
    assert result.processed_records > 0


def test_process_csv_empty(processor):
    result = asyncio.get_event_loop().run_until_complete(
        processor.process_csv_data("", "test_job_empty")
    )
    assert result.total_records == 0


def test_get_job_status_unknown(processor):
    result = processor.get_job_status("nonexistent_job")
    assert result is None


def test_get_job_status_after_processing(processor, sample_csv_content):
    asyncio.get_event_loop().run_until_complete(
        processor.process_csv_data(sample_csv_content, "test_job_status")
    )
    result = processor.get_job_status("test_job_status")
    assert result is not None
    assert result.job_id == "test_job_status"
