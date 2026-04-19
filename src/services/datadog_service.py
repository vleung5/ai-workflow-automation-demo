"""Datadog monitoring and APM service"""

import logging
import time
from typing import Any, Dict, List, Optional

from src.config import config

logger = logging.getLogger(__name__)


def initialize_datadog() -> bool:
    """Initialize Datadog APM and monitoring"""
    if not config.DATADOG_ENABLED:
        logger.info("Datadog monitoring disabled")
        return False

    logger.info("Initializing Datadog APM and Monitoring...")

    try:
        from datadog import initialize  # noqa: F401

        if config.DATADOG_API_KEY and config.DATADOG_APP_KEY:
            initialize(
                api_key=config.DATADOG_API_KEY,
                app_key=config.DATADOG_APP_KEY,
            )
            logger.info("Datadog API initialized")

        from ddtrace import config as dd_config
        from ddtrace import patch

        patch(fastapi=True, boto3=True, botocore=True)

        dd_config.analytics_enabled = True
        dd_config.analytics_sample_rate = config.DD_SAMPLE_RATE

        logger.info(
            "Datadog APM initialized",
            extra={
                "service": config.DD_SERVICE,
                "environment": config.DD_ENV,
                "version": config.DD_VERSION,
                "agent": f"{config.DATADOG_AGENT_HOST}:{config.DATADOG_AGENT_PORT}",
            },
        )
        return True

    except ImportError:
        logger.warning("ddtrace/datadog packages not installed; APM disabled")
        return False
    except Exception as e:
        logger.error(f"Failed to initialize Datadog: {str(e)}")
        return False


def get_datadog_tags(
    additional_tags: Optional[Dict[str, str]] = None,
) -> Dict[str, str]:
    """Return merged Datadog tags dictionary"""
    tags = config.get_datadog_tags()
    if additional_tags:
        tags.update(additional_tags)
    return tags


def send_datadog_event(
    title: str,
    text: str,
    alert_type: str = "info",
    tags: Optional[List[str]] = None,
) -> None:
    """Send an event to Datadog"""
    if not config.DATADOG_ENABLED or not config.DATADOG_API_KEY:
        logger.debug(f"Datadog event (not sent): {title}")
        return
    try:
        from datadog import api

        event_tags = list(tags or [])
        event_tags.extend([f"{k}:{v}" for k, v in config.get_datadog_tags().items()])
        api.Event.create(
            title=title,
            text=text,
            alert_type=alert_type,
            tags=event_tags,
            priority="normal",
        )
        logger.debug(f"Datadog event sent: {title}")
    except Exception as e:
        logger.error(f"Failed to send Datadog event: {str(e)}")


def send_datadog_metric(
    metric_name: str,
    value: float,
    metric_type: str = "gauge",
    tags: Optional[Dict[str, str]] = None,
) -> None:
    """Send a custom metric to Datadog"""
    if not config.DATADOG_ENABLED or not config.DATADOG_API_KEY:
        return
    try:
        from datadog import api

        metric_tags = get_datadog_tags(tags)
        tag_list = [f"{k}:{v}" for k, v in metric_tags.items()]
        api.Metric.send(
            metric=f"{config.DD_METRICS_NAMESPACE}.{metric_name}",
            points=value,
            metric_type=metric_type,
            tags=tag_list,
        )
    except Exception as e:
        logger.error(f"Failed to send Datadog metric: {str(e)}")


class WorkflowMonitor:
    """Track workflow metrics and forward to Datadog"""

    def __init__(self):
        self._job_times: Dict[str, Dict[str, Any]] = {}
        self._s3_ops: Dict[str, int] = {"read": 0, "write": 0, "delete": 0, "failed": 0}
        self._record_stats: Dict[str, int] = {
            "total": 0,
            "successful": 0,
            "failed": 0,
        }

    def track_job_start(self, job_id: str) -> None:
        self._job_times[job_id] = {"start_time": time.time(), "status": "processing"}

    def track_job_end(self, job_id: str, status: str, records_processed: int = 0) -> None:
        if job_id not in self._job_times:
            return
        duration = time.time() - self._job_times[job_id]["start_time"]
        send_datadog_metric("job.duration", duration, "gauge", {"job_id": job_id, "status": status})
        if records_processed > 0 and duration > 0:
            send_datadog_metric(
                "job.throughput",
                records_processed / duration,
                "gauge",
                {"job_id": job_id, "unit": "records_per_second"},
            )
        alert_type = "success" if status == "completed" else "error"
        send_datadog_event(
            title=f"Job {status.title()}",
            text=f"Job {job_id} {status} in {duration:.2f}s",
            alert_type=alert_type,
            tags=["job", status],
        )
        self._job_times[job_id].update(
            {"end_time": time.time(), "status": status, "duration": duration}
        )

    def track_s3_operation(self, operation: str, success: bool = True, duration: float = 0) -> None:
        if not success:
            self._s3_ops["failed"] += 1
            send_datadog_metric("s3.operation.failed", 1, "increment")
        else:
            self._s3_ops[operation] = self._s3_ops.get(operation, 0) + 1
            send_datadog_metric(f"s3.operation.{operation}", 1, "increment")
            if duration > 0:
                send_datadog_metric(f"s3.operation.{operation}.duration", duration, "gauge")

    def track_record_processing(self, total: int, successful: int, failed: int) -> None:
        self._record_stats["total"] += total
        self._record_stats["successful"] += successful
        self._record_stats["failed"] += failed
        send_datadog_metric("records.total", self._record_stats["total"], "gauge")
        send_datadog_metric("records.successful", self._record_stats["successful"], "gauge")
        send_datadog_metric("records.failed", self._record_stats["failed"], "gauge")
        if total > 0:
            send_datadog_metric("records.success_rate", (successful / total) * 100, "gauge")

    def get_job_metrics(self) -> Dict[str, Any]:
        if not self._job_times:
            return {}
        completed = [j for j in self._job_times.values() if j.get("status") == "completed"]
        failed = [j for j in self._job_times.values() if j.get("status") == "failed"]
        avg_duration = (
            sum(j.get("duration", 0) for j in completed) / len(completed) if completed else 0.0
        )
        total = len(self._job_times)
        return {
            "total_jobs": total,
            "completed_jobs": len(completed),
            "failed_jobs": len(failed),
            "average_duration": avg_duration,
            "success_rate": (len(completed) / total * 100) if total else 0.0,
        }


# Module-level singleton
workflow_monitor = WorkflowMonitor()


def get_workflow_monitor() -> WorkflowMonitor:
    """Get the global workflow monitor instance"""
    return workflow_monitor
