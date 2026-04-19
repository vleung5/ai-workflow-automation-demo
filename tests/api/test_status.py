"""Tests for job status endpoint"""


def test_status_not_found():
    """Returns not_found for unknown job IDs"""
    from src.api.v1.status import get_status
    import asyncio
    from unittest.mock import patch

    with patch("src.api.v1.status.processor") as mock_proc:
        mock_proc.get_job_status.return_value = None
        result = asyncio.get_event_loop().run_until_complete(get_status("nonexistent"))

    assert result["status"] == "not_found"
    assert result["job_id"] == "nonexistent"


def test_status_found():
    """Returns job data for known job IDs"""
    import asyncio
    from unittest.mock import patch, MagicMock
    from src.models.enums import JobStatus

    mock_job = MagicMock()
    mock_job.status = JobStatus.COMPLETED
    mock_job.processed_records = 5
    mock_job.total_records = 5

    from src.api.v1.status import get_status

    with patch("src.api.v1.status.processor") as mock_proc:
        mock_proc.get_job_status.return_value = mock_job
        result = asyncio.get_event_loop().run_until_complete(get_status("job_abc"))

    assert result["job_id"] == "job_abc"
    assert result["status"] == JobStatus.COMPLETED
    assert result["progress_percent"] == 100.0
