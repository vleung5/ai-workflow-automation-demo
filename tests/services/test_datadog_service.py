"""Tests for Datadog service"""
import pytest
from unittest.mock import patch, MagicMock

from src.services.datadog_service import (
    get_datadog_tags,
    send_datadog_event,
    send_datadog_metric,
    WorkflowMonitor,
)


def test_get_datadog_tags_contains_service():
    tags = get_datadog_tags()
    assert "service" in tags
    assert "environment" in tags
    assert "version" in tags


def test_get_datadog_tags_merges_additional():
    tags = get_datadog_tags({"custom_key": "custom_val"})
    assert tags["custom_key"] == "custom_val"


def test_send_event_disabled(caplog):
    """When Datadog is disabled, event is not sent"""
    with patch("src.services.datadog_service.config") as mock_cfg:
        mock_cfg.DATADOG_ENABLED = False
        mock_cfg.DATADOG_API_KEY = ""
        mock_cfg.DD_METRICS_NAMESPACE = "ai_workflow"
        send_datadog_event("Test Event", "body")
    # No exception should be raised


def test_workflow_monitor_tracks_job():
    monitor = WorkflowMonitor()
    with patch("src.services.datadog_service.send_datadog_metric"):
        with patch("src.services.datadog_service.send_datadog_event"):
            monitor.track_job_start("job_001")
            monitor.track_job_end("job_001", "completed", records_processed=10)

    metrics = monitor.get_job_metrics()
    assert metrics["total_jobs"] == 1
    assert metrics["completed_jobs"] == 1


def test_workflow_monitor_record_tracking():
    monitor = WorkflowMonitor()
    with patch("src.services.datadog_service.send_datadog_metric"):
        monitor.track_record_processing(total=10, successful=9, failed=1)

    assert monitor._record_stats["total"] == 10
    assert monitor._record_stats["successful"] == 9
    assert monitor._record_stats["failed"] == 1
