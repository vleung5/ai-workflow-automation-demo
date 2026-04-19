"""Custom Datadog monitoring and alerting for AI Workflow Automation"""

import logging
import time
from typing import Any, Dict

from src.services.datadog_service import send_datadog_event, send_datadog_metric

logger = logging.getLogger(__name__)


class WorkflowMonitor:
    """Monitor workflow metrics and send to Datadog"""

    def __init__(self):
        self.job_times: Dict[str, Dict[str, Any]] = {}
        self.s3_operations: Dict[str, int] = {
            "read": 0,
            "write": 0,
            "delete": 0,
            "failed": 0,
        }
        self.processing_stats: Dict[str, int] = {
            "total_records": 0,
            "successful_records": 0,
            "failed_records": 0,
        }

    def track_job_start(self, job_id: str) -> None:
        """Track job start time"""
        self.job_times[job_id] = {"start_time": time.time(), "status": "processing"}

    def track_job_end(self, job_id: str, status: str, records_processed: int = 0) -> None:
        """Track job completion and send metrics"""
        if job_id not in self.job_times:
            return

        duration = time.time() - self.job_times[job_id]["start_time"]

        send_datadog_metric(
            "job.duration",
            duration,
            "gauge",
            {"job_id": job_id, "status": status},
        )

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

        self.job_times[job_id].update(
            {"end_time": time.time(), "status": status, "duration": duration}
        )

    def track_s3_operation(self, operation: str, success: bool = True, duration: float = 0) -> None:
        """Track S3 operations"""
        if not success:
            self.s3_operations["failed"] += 1
            send_datadog_metric("s3.operation.failed", 1, "increment")
        else:
            self.s3_operations[operation] = self.s3_operations.get(operation, 0) + 1
            send_datadog_metric(f"s3.operation.{operation}", 1, "increment")
            if duration > 0:
                send_datadog_metric(f"s3.operation.{operation}.duration", duration, "gauge")

    def track_record_processing(self, total: int, successful: int, failed: int) -> None:
        """Track record processing statistics"""
        self.processing_stats["total_records"] += total
        self.processing_stats["successful_records"] += successful
        self.processing_stats["failed_records"] += failed

        send_datadog_metric("records.total", self.processing_stats["total_records"], "gauge")
        send_datadog_metric(
            "records.successful", self.processing_stats["successful_records"], "gauge"
        )
        send_datadog_metric("records.failed", self.processing_stats["failed_records"], "gauge")

        if total > 0:
            success_rate = (successful / total) * 100
            send_datadog_metric("records.success_rate", success_rate, "gauge")

    def send_health_check(
        self, service_name: str, status: str, details: Dict[str, Any] = None
    ) -> None:
        """Send health check to Datadog"""
        alert_type = "success" if status == "healthy" else "warning"
        text = f"{service_name} is {status}"
        if details:
            text += f"\nDetails: {details}"
        send_datadog_event(
            title=f"{service_name} Health Check",
            text=text,
            alert_type=alert_type,
            tags=["health", "monitoring"],
        )

    def get_job_metrics(self) -> Dict[str, Any]:
        """Get aggregated job metrics"""
        if not self.job_times:
            return {}

        completed = [j for j in self.job_times.values() if j.get("status") == "completed"]
        failed = [j for j in self.job_times.values() if j.get("status") == "failed"]
        avg_duration = (
            sum(j.get("duration", 0) for j in completed) / len(completed) if completed else 0.0
        )
        total = len(self.job_times)

        return {
            "total_jobs": total,
            "completed_jobs": len(completed),
            "failed_jobs": len(failed),
            "average_duration": avg_duration,
            "success_rate": (len(completed) / total * 100) if total else 0.0,
        }

    def send_summary_report(self) -> None:
        """Send summary report to Datadog"""
        metrics = self.get_job_metrics()
        if not metrics:
            return

        summary_text = (
            f"Jobs Summary:\n"
            f"- Total Jobs: {metrics['total_jobs']}\n"
            f"- Completed: {metrics['completed_jobs']}\n"
            f"- Failed: {metrics['failed_jobs']}\n"
            f"- Average Duration: {metrics['average_duration']:.2f}s\n"
            f"- Success Rate: {metrics['success_rate']:.1f}%\n\n"
            f"Records Summary:\n"
            f"- Total: {self.processing_stats['total_records']}\n"
            f"- Successful: {self.processing_stats['successful_records']}\n"
            f"- Failed: {self.processing_stats['failed_records']}"
        )

        send_datadog_event(
            title="Workflow Summary Report",
            text=summary_text,
            alert_type="info",
            tags=["summary", "report"],
        )


# Global monitor instance
workflow_monitor = WorkflowMonitor()


def get_workflow_monitor() -> WorkflowMonitor:
    """Get the global workflow monitor instance"""
    return workflow_monitor
